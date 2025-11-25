# Flappy Bird Clone

A simple clone of the popular Flappy Bird game built with Python and Pygame.

## Features
- Simple one-button gameplay
- Pipe obstacles with random heights
- Score tracking
- Game over screen with restart option

## Controls
- Press SPACE to make the bird flap
- Press SPACE to restart when game is over
- Press Q to quit the game

## Requirements
- Python 3.x
- Pygame

## How to Run
1. Make sure you have Python installed
2. Install Pygame if you haven't already: `pip install pygame`
3. Run the game: `python flappy_bird.py`

## Persistence

The game now uses an SQLite database for persistent state (high score, owned skins, and saved coins). The DB is stored per-user in a platform-specific application data directory (macOS: ~/Library/Application Support/flappy_bird_clone, Linux: ~/.local/share/flappy_bird_clone, Windows: %APPDATA%\\flappy_bird_clone). Legacy local text fallbacks (saved_coins.txt, owned_skins.txt, current_skin.txt, high_score.txt) were removed in favor of the DB.

If the DB is unavailable for any reason the game will safely continue — it will simply skip saving state (no local text fallbacks).

## Publishing to GitHub

Below are short, copy/paste-ready steps to publish this project to GitHub. I will not push any changes for you unless you ask.

1. Initialize a git repo (if you haven't already):

```bash
git init
git add -A
git commit -m "Initial commit: flappy bird clone"
```

2. Create a remote repository on GitHub (via website or GitHub CLI). If you use GitHub CLI, run:

```bash
gh repo create <your-username>/<repo-name> --public --source=. --remote=origin
```

3. Push your main branch (if your branch is `main`):

```bash
git branch -M main
git push -u origin main
```

4. (Optional) If you'd like me to make a branch for packaging or further cleanup, tell me the name and I'll prepare changes and create a suggested branch locally.

That's it — once pushed your repository will be available on GitHub.

## Game Rules
- Control the bird to fly between the pipes
- Don't hit the pipes or the ground
- Score points by passing through pipe gaps
- Try to achieve the highest score possible!