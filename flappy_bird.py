import pygame
import random
import sys
import math
import os
import sqlite3
from pathlib import Path

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 600
GRAVITY = 0.5
FLAP_STRENGTH = -6
MAX_VELOCITY = 10
ACCELERATION = 1.05  # Acceleration multiplier
PIPE_SPEED = 3
PIPE_GAP = 150
PIPE_FREQUENCY = 1500  # milliseconds
COIN_FREQUENCY = 2000  # milliseconds
COIN_VALUE = 5

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
SKY_BLUE = (135, 206, 235)

# Create the game window
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption('Flappy Bird Clone')
clock = pygame.time.Clock()

# Cache a small font to avoid recreating it every frame (performance)
SMALL_FONT = pygame.font.Font(None, 20)


# Persistence layer using SQLite stored in a per-user app data directory.
class Persistence:
    def __init__(self):
        self.db_path = self._get_db_path()
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self._init_tables()

    def _get_db_path(self):
        # Use OS-specific app data location so each user has their own DB
        home = os.path.expanduser('~')
        if sys.platform == 'darwin':
            base = os.path.join(home, 'Library', 'Application Support', 'flappy_bird_clone')
        elif sys.platform.startswith('win'):
            base = os.path.join(os.environ.get('APPDATA', home), 'flappy_bird_clone')
        else:
            base = os.path.join(home, '.local', 'share', 'flappy_bird_clone')
        Path(base).mkdir(parents=True, exist_ok=True)
        return os.path.join(base, 'game.db')

    def _init_tables(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS state (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS owned_skins (
                        skin TEXT PRIMARY KEY
                    )''')
        self.conn.commit()

    def get_state(self, key, default=None):
        c = self.conn.cursor()
        c.execute('SELECT value FROM state WHERE key=?', (key,))
        row = c.fetchone()
        return default if row is None else row[0]

    def set_state(self, key, value):
        c = self.conn.cursor()
        c.execute('INSERT OR REPLACE INTO state(key, value) VALUES(?, ?)', (key, str(value)))
        self.conn.commit()

    def add_owned_skin(self, skin_name):
        c = self.conn.cursor()
        c.execute('INSERT OR IGNORE INTO owned_skins(skin) VALUES(?)', (skin_name,))
        self.conn.commit()

    def get_owned_skins(self):
        c = self.conn.cursor()
        c.execute('SELECT skin FROM owned_skins')
        return {row[0] for row in c.fetchall()}

    def close(self):
        try:
            self.conn.close()
        except:
            pass


# Create a global persistence instance
persistence = Persistence()

class Bird:
    # Available skins with their prices
    SKINS = {
        'default': {
            'body': (255, 185, 0),    # Golden yellow
            'wing': (255, 140, 0),    # Dark orange
            'beak': (255, 69, 0),     # Red-orange
            'eye': BLACK,
            'price': 0
        },
        'blue_jay': {
            'body': (100, 149, 237),  # Cornflower blue
            'wing': (65, 105, 225),   # Royal blue
            'beak': (211, 211, 211),  # Light gray
            'eye': BLACK,
            'price': 50
        },
        'cardinal': {
            'body': (220, 20, 60),    # Crimson
            'wing': (139, 0, 0),      # Dark red
            'beak': (255, 140, 0),    # Dark orange
            'eye': BLACK,
            'price': 100
        },
        'rainbow': {
            'body': (255, 0, 255),    # Magenta
            'wing': (0, 255, 255),    # Cyan
            'beak': (255, 255, 0),    # Yellow
            'eye': WHITE,
            'price': 200
        },
        'ninja': {
            'body': (32, 32, 32),     # Dark gray
            'wing': (20, 20, 20),     # Nearly black
            'beak': (64, 64, 64),     # Medium gray
            'eye': (255, 0, 0),       # Red eyes
            'price': 150
        },
        'ghost': {
            'body': (240, 240, 255),  # Nearly white
            'wing': (200, 200, 255),  # Light blue-white
            'beak': (220, 220, 255),  # Medium blue-white
            'eye': (0, 0, 255),       # Blue eyes
            'price': 175
        },
        'phoenix': {
            'body': (255, 69, 0),     # Red-orange
            'wing': (255, 140, 0),    # Dark orange
            'beak': (255, 215, 0),    # Gold
            'eye': (255, 255, 0),     # Yellow
            'price': 250
        },
        'emerald': {
            'body': (46, 139, 87),    # Sea green
            'wing': (0, 100, 0),      # Dark green
            'beak': (32, 178, 170),   # Light sea green
            'eye': (152, 251, 152),   # Pale green
            'price': 150
        },
        'robot': {
            'body': (192, 192, 192),  # Silver
            'wing': (128, 128, 128),  # Gray
            'beak': (169, 169, 169),  # Dark gray
            'eye': (0, 255, 255),     # Cyan
            'price': 300
        }
    }

    def __init__(self):
        self.x = WINDOW_WIDTH // 3
        self.y = WINDOW_HEIGHT // 2
        self.velocity = 0
        self.size = 30
        self.angle = 0
        self.current_skin = 'default'
        self.owned_skins = {'default'}  # Start with default skin
        self.load_owned_skins()
        self.load_current_skin()
        self.apply_skin(self.current_skin)

    def save_owned_skins(self):
        # Persist owned skins to the DB
        try:
            for s in self.owned_skins:
                persistence.add_owned_skin(s)
        except:
            pass

    def load_owned_skins(self):
        try:
            skins = persistence.get_owned_skins()
            if skins:
                self.owned_skins = set(skins)
            self.owned_skins.add('default')
        except:
            self.owned_skins = {'default'}

    def save_current_skin(self):
        try:
            persistence.set_state('current_skin', self.current_skin)
        except:
            pass

    def load_current_skin(self):
        try:
            skin = persistence.get_state('current_skin', None)
            if skin and skin in self.SKINS and skin in self.owned_skins:
                self.current_skin = skin
        except:
            self.current_skin = 'default'

    def set_skin(self, skin_name):
        if skin_name in self.SKINS and skin_name in self.owned_skins:
            self.current_skin = skin_name
            self.apply_skin(skin_name)
            self.save_current_skin()

    def apply_skin(self, skin_name):
        self.colors = self.SKINS[skin_name].copy()
        del self.colors['price']

    def purchase_skin(self, skin_name, coins):
        if (skin_name in self.SKINS and 
            skin_name not in self.owned_skins and 
            coins >= self.SKINS[skin_name]['price']):
            self.owned_skins.add(skin_name)
            # persist new skin in DB
            try:
                persistence.add_owned_skin(skin_name)
            except:
                pass
            return True
        return False

    def flap(self):
        self.velocity = FLAP_STRENGTH
        self.angle = 20  # Rotate upward when flapping

    def update(self):
        # Apply acceleration only when falling (positive velocity)
        if self.velocity > 0:
            self.velocity = min(self.velocity * ACCELERATION + GRAVITY, MAX_VELOCITY)
        else:
            self.velocity += GRAVITY
        self.y += self.velocity

        # Update rotation based on velocity
        if self.velocity < 0:
            self.angle = 20
        else:
            self.angle = max(-70, self.angle - 4)  # Gradually rotate downward

# NOTE: don't clamp the bird's y here. Let the Game class detect
# collisions with the top/bottom of the screen so we can trigger
# a proper game over when the bird touches the edges.

    def draw(self):
        # Create a surface for the bird
        bird_surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        
        # Draw body (circle)
        pygame.draw.circle(bird_surface, self.colors['body'], 
                         (self.size // 2, self.size // 2), 
                         self.size // 2 - 2)
        
        # Draw wing
        wing_points = [(self.size // 2 - 2, self.size // 2),
                      (self.size // 4, self.size // 2 + 5),
                      (self.size // 2 - 2, self.size // 2 + 10)]
        pygame.draw.polygon(bird_surface, self.colors['wing'], wing_points)
        
        # Draw beak
        beak_points = [(self.size * 3 // 4, self.size // 2 - 2),
                      (self.size - 2, self.size // 2),
                      (self.size * 3 // 4, self.size // 2 + 2)]
        pygame.draw.polygon(bird_surface, self.colors['beak'], beak_points)
        
        # Draw eye
        pygame.draw.circle(bird_surface, self.colors['eye'],
                         (self.size * 5 // 8, self.size // 2 - 2),
                         2)
        
        # Rotate the bird surface
        rotated_bird = pygame.transform.rotate(bird_surface, self.angle)
        
        # Calculate position adjustment for rotation
        new_rect = rotated_bird.get_rect(center=(self.x + self.size // 2, 
                                                self.y + self.size // 2))
        
        # Draw the rotated bird
        screen.blit(rotated_bird, new_rect.topleft)

class Pipe:
    def __init__(self):
        self.gap_y = random.randint(150, WINDOW_HEIGHT - 150)
        self.x = WINDOW_WIDTH
        self.width = 80
        self.passed = False
        self.edge_width = 10  # Width of the pipe edge

    def update(self):
        self.x -= PIPE_SPEED
        return self.x > -self.width

    def draw(self):
        # Colors for more realistic pipes
        pipe_color = (40, 100, 40)  # Darker green
        edge_color = (60, 140, 60)  # Lighter green for edges
        
        # Draw top pipe
        top_height = self.gap_y - PIPE_GAP // 2
        pygame.draw.rect(screen, pipe_color, (self.x, 0, self.width, top_height))
        pygame.draw.rect(screen, edge_color, (self.x - self.edge_width, top_height - 20, 
                                            self.width + self.edge_width * 2, 20))
        
        # Draw bottom pipe
        bottom_y = self.gap_y + PIPE_GAP // 2
        bottom_height = WINDOW_HEIGHT - bottom_y
        pygame.draw.rect(screen, pipe_color, (self.x, bottom_y, self.width, bottom_height))
        pygame.draw.rect(screen, edge_color, (self.x - self.edge_width, bottom_y, 
                                            self.width + self.edge_width * 2, 20))
        
        # Add pipe details (vertical lines for texture)
        for i in range(3):
            line_x = self.x + (self.width * (i + 1) // 4)
            # Top pipe lines
            pygame.draw.line(screen, edge_color, (line_x, 0), (line_x, top_height), 2)
            # Bottom pipe lines
            pygame.draw.line(screen, edge_color, (line_x, bottom_y), 
                           (line_x, bottom_y + bottom_height), 2)

    def check_collision(self, bird):
        bird_rect = pygame.Rect(bird.x, bird.y, bird.size, bird.size)
        top_pipe = pygame.Rect(self.x, 0, self.width, self.gap_y - PIPE_GAP // 2)
        bottom_pipe = pygame.Rect(self.x, self.gap_y + PIPE_GAP // 2, 
                                self.width, WINDOW_HEIGHT - (self.gap_y + PIPE_GAP // 2))
        return bird_rect.colliderect(top_pipe) or bird_rect.colliderect(bottom_pipe)

class Coin:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 10
        self.is_special = random.random() < 0.1  # 10% chance for special coin
        self.value = 10 if self.is_special else 5
        self.color = (255, 0, 128) if self.is_special else (255, 215, 0)  # Pink for special, gold for normal
        self.glow_color = (255, 182, 193) if self.is_special else (255, 228, 181)  # Lighter version for glow
        self.collected = False
        self.bob_range = 20  # Pixels to move up and down
        self.bob_speed = 0.05
        self.start_y = y
        self.time = random.random() * 6.28  # Random start position in the bob cycle
        self.glow_size = 0  # For pulsing effect

    def update(self):
        # Move left at the same speed as pipes
        self.x -= PIPE_SPEED
        # Bob up and down
        self.time += self.bob_speed
        self.y = self.start_y + math.sin(self.time) * self.bob_range
        # Keep coin if it's still on screen
        return self.x > -self.radius * 2

    def draw(self):
        # Update glow size for pulsing effect
        self.glow_size = abs(math.sin(self.time * 2)) * 4

        # Draw glow effect
        if self.is_special:
            pygame.draw.circle(screen, self.glow_color, 
                             (int(self.x), int(self.y)), 
                             self.radius + self.glow_size)

        # Draw main coin
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        
        # Draw value (reuse cached SMALL_FONT)
        text = SMALL_FONT.render(str(self.value), True, BLACK)
        text_rect = text.get_rect(center=(int(self.x), int(self.y)))
        screen.blit(text, text_rect)

    def check_collision(self, bird):
        bird_center = (bird.x + bird.size // 2, bird.y + bird.size // 2)
        distance = ((bird_center[0] - self.x) ** 2 + (bird_center[1] - self.y) ** 2) ** 0.5
        return distance < self.radius + bird.size // 2

class Shop:
    def __init__(self, bird):
        self.bird = bird
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.active = False
        self.coins = 0
        self.button_height = 50
        self.button_width = 200
        self.margin = 10
        self.scroll_offset = 0
        self.scroll_speed = 20
        self.max_visible_items = 6
        self.load_coins()

    def save_coins(self):
        try:
            persistence.set_state('coins', self.coins)
        except:
            # DB failed or unavailable; skip saving (no file fallback)
            pass

    def load_coins(self):
        try:
            coins = persistence.get_state('coins', None)
            if coins is not None:
                self.coins = int(coins)
            else:
                self.coins = 0
        except:
            # DB failed or unavailable; default to 0
            self.coins = 0

    def draw(self):
        if not self.active:
            return

        # Draw semi-transparent background
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(128)
        screen.blit(overlay, (0, 0))

        # Create a surface for the scrollable content
        content_height = (len(self.bird.SKINS) * (self.button_height + self.margin))
        scroll_surface = pygame.Surface((WINDOW_WIDTH, content_height), pygame.SRCALPHA)

        # Draw shop title
        title = self.font.render('SHOP', True, WHITE)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 50))
        screen.blit(title, title_rect)

        # Draw coins
        coins_text = self.font.render(f'Coins: {self.coins}', True, (255, 215, 0))
        coins_rect = coins_text.get_rect(topleft=(20, 20))
        screen.blit(coins_text, coins_rect)

        # Draw scroll indicators
        if self.scroll_offset > 0:
            pygame.draw.polygon(screen, WHITE, [
                (WINDOW_WIDTH - 30, 100),
                (WINDOW_WIDTH - 20, 80),
                (WINDOW_WIDTH - 10, 100)
            ])
        if self.scroll_offset < content_height - (WINDOW_HEIGHT - 150):
            pygame.draw.polygon(screen, WHITE, [
                (WINDOW_WIDTH - 30, WINDOW_HEIGHT - 100),
                (WINDOW_WIDTH - 20, WINDOW_HEIGHT - 80),
                (WINDOW_WIDTH - 10, WINDOW_HEIGHT - 100)
            ])

        # Create a viewport surface
        viewport = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT - 150), pygame.SRCALPHA)
        
        # Draw skin options
        y_pos = 0
        for skin_name, skin_data in self.bird.SKINS.items():
            button_rect = pygame.Rect(
                (WINDOW_WIDTH - self.button_width) // 2,
                y_pos,
                self.button_width,
                self.button_height
            )
            
            # Different colors for owned/selected/locked skins
            if skin_name == self.bird.current_skin:
                color = (0, 255, 0, 128)  # Green for selected
                text_color = WHITE
            elif skin_name in self.bird.owned_skins:
                color = (100, 100, 255, 128)  # Blue for owned
                text_color = WHITE
            elif skin_data['price'] <= self.coins:
                color = (255, 215, 0, 128)  # Gold for available to purchase
                text_color = WHITE
            else:
                color = (128, 128, 128, 128)  # Gray for locked
                text_color = (200, 200, 200)

            pygame.draw.rect(scroll_surface, color, button_rect)
            
            # Draw skin name and price
            name_text = self.font.render(skin_name.replace('_', ' ').title(), True, text_color)
            price_text = self.small_font.render(f'Price: {skin_data["price"]} coins', True, text_color)
            
            scroll_surface.blit(name_text, (button_rect.centerx - name_text.get_width() // 2,
                                          button_rect.y + 5))
            scroll_surface.blit(price_text, (button_rect.centerx - price_text.get_width() // 2,
                                           button_rect.y + 30))
            
            y_pos += self.button_height + self.margin

        # Draw the visible portion of the scroll surface
        viewport.blit(scroll_surface, (0, -self.scroll_offset))
        screen.blit(viewport, (0, 100))

        # Draw exit button
        exit_text = self.font.render('Back to Game', True, WHITE)
        exit_rect = exit_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50))
        pygame.draw.rect(screen, (255, 0, 0), exit_rect.inflate(20, 10))
        screen.blit(exit_text, exit_rect)

    def handle_events(self, event):
        if not self.active:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            # Handle scrolling
            if event.button == 4:  # Mouse wheel up
                self.scroll_offset = max(0, self.scroll_offset - self.scroll_speed)
                return True
            elif event.button == 5:  # Mouse wheel down
                max_scroll = (len(self.bird.SKINS) * (self.button_height + self.margin)) - (WINDOW_HEIGHT - 150)
                self.scroll_offset = min(max_scroll, self.scroll_offset + self.scroll_speed)
                return True
            elif event.button == 1:  # Left click
                return self.handle_click(event.pos)
        return False

    def handle_click(self, pos):
        if not self.active:
            return False

        # Adjust position for scroll
        adjusted_y = pos[1] + self.scroll_offset - 100  # 100 is the top margin

        # Check skin buttons
        y_pos = 0
        for skin_name, skin_data in self.bird.SKINS.items():
            button_rect = pygame.Rect(
                (WINDOW_WIDTH - self.button_width) // 2,
                y_pos,
                self.button_width,
                self.button_height
            )
            
            # Adjust the rect for the current scroll position
            screen_rect = pygame.Rect(
                button_rect.x,
                button_rect.y - self.scroll_offset + 100,
                button_rect.width,
                button_rect.height
            )
            
            if screen_rect.collidepoint(pos):
                if skin_name in self.bird.owned_skins:
                    # If owned, just equip it
                    self.bird.set_skin(skin_name)
                elif skin_data['price'] <= self.coins:
                    # If not owned and can afford, purchase and equip
                    if self.bird.purchase_skin(skin_name, self.coins):
                        self.coins -= skin_data['price']
                        self.bird.set_skin(skin_name)
                        self.save_coins()
                return True
            
            y_pos += self.button_height + self.margin

        # Check exit button (match the drawn button rect so clicks line up)
        exit_text = self.font.render('Back to Game', True, WHITE)
        exit_rect = exit_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50))
        click_rect = exit_rect.inflate(20, 10)
        if click_rect.collidepoint(pos):
            self.active = False
            return True
        
        return False

class Game:
    def __init__(self):
        self.bird = Bird()
        self.pipes = []
        self.coins = []
        self.score = 0
        self.high_score = self.load_high_score()
        self.last_pipe = pygame.time.get_ticks()
        self.last_coin = pygame.time.get_ticks()
        self.game_over = False
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.shop = Shop(self.bird)
        self.load_saved_coins()

    def load_high_score(self):
        try:
            val = persistence.get_state('high_score', None)
            if val is not None:
                return int(val)
            return 0
        except:
            # DB failed/unavailable; return default
            return 0

    def save_high_score(self):
        if self.score > self.high_score:
            self.high_score = self.score
            try:
                persistence.set_state('high_score', int(self.high_score))
            except:
                # DB failed/unavailable; do not write file fallback
                pass

    def load_saved_coins(self):
        try:
            val = persistence.get_state('coins', None)
            if val is not None:
                self.shop.coins = int(val)
            else:
                self.shop.coins = 0
        except:
            # DB failed/unavailable; default to 0
            self.shop.coins = 0

    def save_coins(self):
        try:
            persistence.set_state('coins', int(self.shop.coins))
        except:
            # DB failed/unavailable; skip writing file fallback
            pass

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.save_coins()
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if self.game_over:
                        self.__init__()  # Reset game
                    elif not self.shop.active:
                        self.bird.flap()
                elif event.key == pygame.K_q:
                    self.save_coins()
                    return False
                elif event.key == pygame.K_s and not self.game_over:
                    self.shop.active = not self.shop.active
            elif (event.type == pygame.MOUSEBUTTONDOWN or 
                  event.type == pygame.MOUSEWHEEL) and self.shop.active:
                self.shop.handle_events(event)
        return True

    def update(self):
        if not self.game_over and not self.shop.active:
            self.bird.update()

            # Check for collisions with top/bottom of the screen
            # If the bird touches the top or the ground, trigger game over
            if self.bird.y <= 0 or (self.bird.y + self.bird.size) >= WINDOW_HEIGHT:
                self.game_over = True
                self.save_high_score()

            # Create new pipes
            now = pygame.time.get_ticks()
            if now - self.last_pipe > PIPE_FREQUENCY:
                self.pipes.append(Pipe())
                self.last_pipe = now

            # Create new coins
            if now - self.last_coin > COIN_FREQUENCY:
                # Find the rightmost pipe
                rightmost_pipe = None
                for pipe in self.pipes:
                    if not rightmost_pipe or pipe.x > rightmost_pipe.x:
                        rightmost_pipe = pipe

                # Position coin near pipe gap if there's a pipe, otherwise in a safe zone
                if rightmost_pipe and rightmost_pipe.x < WINDOW_WIDTH - 100:
                    # Place coin near the next pipe gap
                    coin_y = rightmost_pipe.gap_y + random.randint(-PIPE_GAP//4, PIPE_GAP//4)
                    coin_x = rightmost_pipe.x + rightmost_pipe.width + 50  # Place after the pipe
                else:
                    # Place coin in a generally safe area
                    coin_y = random.randint(WINDOW_HEIGHT//3, WINDOW_HEIGHT*2//3)
                    coin_x = WINDOW_WIDTH

                self.coins.append(Coin(coin_x, coin_y))
                self.last_coin = now

            # Update pipes and check collisions
            surviving_pipes = []
            for pipe in self.pipes:
                if pipe.update():
                    surviving_pipes.append(pipe)
                    if not pipe.passed and pipe.x < self.bird.x:
                        self.score += 1
                        pipe.passed = True
                    if pipe.check_collision(self.bird):
                        self.game_over = True
                        self.save_high_score()
            self.pipes = surviving_pipes

            # Update coins and check collections
            surviving_coins = []
            for coin in self.coins:
                if not coin.collected and coin.update():
                    if coin.check_collision(self.bird):
                        coin.collected = True
                        # Use coin.value so special coins give 10
                        self.shop.coins += coin.value
                        self.save_coins()
                    else:
                        surviving_coins.append(coin)
            self.coins = surviving_coins

    def draw(self):
        screen.fill(SKY_BLUE)
        
        # Draw game elements
        if not self.shop.active:
            self.bird.draw()
            for pipe in self.pipes:
                pipe.draw()
            for coin in self.coins:
                coin.draw()

            # Draw score, high score, and coins
            score_text = self.font.render(f'Score: {self.score}', True, WHITE)
            high_score_text = self.small_font.render(f'High Score: {self.high_score}', True, (255, 215, 0))
            coin_text = self.font.render(f'Coins: {self.shop.coins}', True, (255, 215, 0))
            
            screen.blit(score_text, (10, 10))
            screen.blit(high_score_text, (10, 45))
            screen.blit(coin_text, (10, 75))

            if not self.game_over:
                shop_text = self.font.render('Press S for Shop', True, WHITE)
                screen.blit(shop_text, (WINDOW_WIDTH - shop_text.get_width() - 10, 10))

            if self.game_over:
                game_over_text = self.font.render('Game Over! Space to restart', True, WHITE)
                screen.blit(game_over_text, 
                           (WINDOW_WIDTH // 2 - game_over_text.get_width() // 2, 
                            WINDOW_HEIGHT // 2))

        # Draw shop if active
        self.shop.draw()

        pygame.display.flip()

def main():
    game = Game()
    running = True
    
    while running:
        running = game.handle_events()
        game.update()
        game.draw()
        clock.tick(60)

    # Close DB connection cleanly
    try:
        persistence.close()
    except:
        pass
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()