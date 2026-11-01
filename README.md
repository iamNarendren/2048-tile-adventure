# 2048 Tile Adventure

A complete 2048 game built with **Python 3** and **Pygame**, with three game modes, a robot companion with an AI helper, animations, sound effects, achievements and local leaderboards.

## Play online
**https://iamnarendren.github.io/2048-tile-adventure/**

Open the link in Chrome, Edge or Brave on a computer with a keyboard. The first load takes a few seconds while the game engine downloads. Click the page once to start (browsers need a click before they allow sound).

## Features
- **Three game modes:** Classic, Survival and Infection
- **Robot companion** that changes colour with your score, and an **AI helper** you activate by clicking the robot 3 times
- Smooth tile sliding, merge pop and spawn animations
- Sound effects with an on/off toggle
- **Achievements** and score **milestones**
- **Local top-10 leaderboards** for each mode, plus best scores
- Player name entry

## Game modes
| Mode | Rules |
|---|---|
| **Classic** | Standard 2048. Merge equal tiles to reach 2048. After reaching 2048 you can keep playing. The game ends when no moves are left. |
| **Survival** | You have 60 seconds. Every 10 seconds a random row or column is blocked for 3 seconds. Blocked tiles are frozen and cannot move or merge. The game ends when the timer reaches zero. |
| **Infection** | One tile starts infected. After every 3 successful moves the infection spreads to neighbouring tiles. Merging two infected tiles cures the result. Merging an infected tile with a normal tile keeps the result infected. The game ends when every tile is infected. |

## Controls
| Action | Key / mouse |
|---|---|
| Move tiles | Arrow keys or W A S D |
| Restart | R |
| Back to menu | M or Esc |
| Toggle sound | F, or the sound button |
| Robot AI helper | Click the robot 3 times |

## Robot companion
The robot's colour shows your score: blue below 100, green below 500, purple below 1000, gold from 1000. Clicking it 3 times makes the AI pick and play the best move. The AI checks all four directions and scores each on empty cells, possible merges, keeping the largest tile in a corner, and an ordered, stable board. It plays one useful move, and it does not guarantee a win.

## Achievements
Score 100 · Score 500 · Score 1000 · Reach 2048 · First Merge

## Run the desktop version
1. Install Python 3.10 or newer.
2. Install the requirement:
   ```
   pip install -r requirements.txt
   ```
3. Start the game:
   ```
   python main.py
   ```

On the desktop, scores are saved in `leaderboard.json` next to the game.
On the web, scores are saved in your browser's local storage, so they stay on the same device and browser.

## Project structure
```
main.py            Entry point (desktop and web)
core/              Game logic. Plain Python, no Pygame
  board.py           Moving, merging and spawning tiles
  game_state.py      All game data in one place
  game_flow.py       Starting a game, game status, win and game over
  modes/survival.py  Survival timer and temporary blocks
  modes/infection.py Infection spread and cure rules
  ai_solver.py       Robot AI move evaluation
  robot.py           Robot colour and click counting
  achievements.py    Achievements and milestones
  leaderboard.py     Saving and loading scores
  constants.py       Settings and numbers
  events.py          Events the UI turns into animation and sound
ui/                Pygame interface only
  app.py             Window and main loop
  menu.py, screens.py, renderer.py
  animations.py, robot_view.py, sound.py
assets/sounds/     Generated sound effects
tests/             Automated tests for the core logic
docs/              Web build served by GitHub Pages
```

## Core and interface are separate
Everything in `core/` is plain Python and never imports Pygame. It receives the current time as a parameter and returns events. The `ui/` folder turns those events into drawing, animation and sound. That separation makes the logic easy to test, and it can be reused in another front-end, such as a Streamlit app.

## Run the tests
```
pip install pytest
python -m pytest
```
The tests cover movement
