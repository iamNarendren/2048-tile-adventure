# 2048 Tile Adventure

A desktop 2048 game built with **Python 3** and **Pygame** — sliding and
merging tiles, a hint button powered by a heuristic AI, smooth animations,
sound effects the game synthesises itself, score milestones and a local
leaderboard.

The game is split into two packages: **`core/` holds every rule** and never
imports a GUI library, while **`ui/` holds everything you see and hear**. They
communicate through small `GameEvent` objects, so the rules can be tested
without ever opening a window.

---

## Download and play (Windows)

Grab **`2048TileAdventure.exe`** from the
[latest release](../../releases/latest) and double-click it. No installation and
no Python needed — the game creates its sound files and its `leaderboard.json`
next to the `.exe` on first run.

> Windows may show *"Windows protected your PC"* because the file is not code
> signed. Click **More info → Run anyway**.

---

## Screenshots

<!-- These images come from smoke_screenshots/, created by: python smoke_test.py
     If you have not generated them, delete the two lines below. -->

![Main menu](smoke_screenshots/01_main_menu.png)
![Playing a round](smoke_screenshots/03_classic_game.png)

---

## Features

- **Classic 2048 rules** — slide in one of four directions, equal neighbouring
  tiles merge once per move, one new tile (90 % a 2, 10 % a 4) appears after
  every successful move, and the target is the 2048 tile.
- **Hint button** — press **HINT** or **H** and a one-ply heuristic solver
  simulates all four moves with the real board engine, scores each resulting
  board and shows the best direction as an arrow. It never plays the move: you
  stay in control.
- **Win prompt** — reaching 2048 pauses the round and offers *Keep Playing* or
  *End Game*.
- **Animations** — sliding tiles, merge pops, spawn scaling, a score that
  counts up, milestone toasts and screen fades.
- **Self-generated audio** — five WAV effects are synthesised with the Python
  standard library on first run. The game runs silently if no audio device is
  available.
- **Local leaderboard** — the top 10 scores and the best score, stored as
  readable JSON.
- **Tested** — 74 unit tests for the rules plus a headless end-to-end UI test
  that drives the real screens and saves screenshots.

---

## Run from source

```powershell
python -m pip install -r requirements.txt
python main.py
```

Requires **Python 3.10+** and `pygame` 2.5+ (`pygame-ce` also works).
Everything else comes from the standard library.

---

## Controls

| Input | Action |
| --- | --- |
| Arrow keys or `W` `A` `S` `D` | Move the tiles |
| `H` or the HINT button | Show / hide the suggested best move |
| `R` | Restart the round |
| `M` or `Esc` | Back to the main menu |
| `F` | Sound on / off |
| `K` / `E` | Keep playing / end game on the win prompt |
| `L` | Leaderboard from the game-over screen |
| `1` `2` `3` | Menu shortcuts: Play Classic, Leaderboard, Quit |

---

## How a round works

1. The menu offers **Play Classic**, **Leaderboard** and **Quit**.
2. You enter a name (max 12 characters; empty becomes `Player`).
3. The round starts with an empty 4×4 board and two spawned tiles.
4. Each key press asks the core for one move. A move that does not change the
   board is rejected — no tile spawns and the move counter does not change.
5. A successful move merges equal tiles once, adds the merged values to the
   score, spawns exactly one tile, fires any newly reached milestone, and then
   checks the win and game-over conditions.
6. Reaching 2048 opens the win prompt once per round.
7. The round ends when the board is full and no two neighbours are equal. The
   score is written to `leaderboard.json` exactly once.

---

## Project structure

```text
2048-tile-adventure/
├── main.py                   Entry point
├── requirements.txt          pygame
├── pytest.ini                Test configuration
├── smoke_test.py             Headless end-to-end UI test (saves screenshots)
├── 2048TileAdventure.spec    PyInstaller recipe
├── build_exe.bat             Test + package in one step
│
├── core/                     Pure Python — no Pygame, no clock reads
│   ├── constants.py          Every tunable number and the colour names
│   ├── events.py             GameEvent objects returned to the UI
│   ├── game_state.py         GameState dataclass: the whole round
│   ├── board.py              Merging, moving, spawning, move_tiles
│   ├── game_flow.py          Start, restart, score, milestones, status
│   ├── leaderboard.py        JSON save/load
│   └── ai_solver.py          Heuristic solver behind the HINT button
│
├── ui/                       Pygame front end
│   ├── app.py                GameApp: window, main loop, input routing
│   ├── renderer.py           Palette, fonts, board, HUD, hint panel
│   ├── menu.py               Main menu and name entry
│   ├── screens.py            Leaderboard, win and game-over overlays
│   ├── animations.py         Slide / pop / spawn timing and toasts
│   └── sound.py              WAV synthesis and the SoundManager
│
├── tests/                    74 unit tests (core only)
├── assets/sounds/            WAV effects, generated on first run
└── smoke_screenshots/        Output of smoke_test.py
```

---

## Architecture

**Core / UI separation.** `core/` contains all the rules and is deliberately
reusable:

- it never imports Pygame — a unit test parses every file and fails if it does;
- it never reads a clock (no `time`, no `datetime`); the UI stamps the date
  before a score is saved;
- randomness is injectable (`rng=random.Random(seed)`), so every test and the
  smoke test are reproducible.

**One move, end to end:**

```text
key press
  → GameApp._request_move(direction)
  → core.board.move_tiles(state, direction, rng)
        → apply_move_to_grid  (pure simulation on a copy)
        → spawn one tile
        → milestones
        → win / game-over check
  → list[GameEvent]
  → GameApp._process_events(...)
        → animations, sounds, toasts, overlays
```

**One engine, four directions.** `_line_coordinates` returns each row or column
*destination first*, so RIGHT, UP and DOWN reuse the same merge-to-the-left
routine instead of four copies of the logic.

**Animations never change the board.** The core commits the final board
immediately and also reports where every tile came from; the UI interpolates
positions between the old and new cells while the board is already final.

**Saving is idempotent.** `state.score_saved` guarantees a round is written to
the leaderboard at most once, however it ended.

---

## Save data

`leaderboard.json` is created next to the project (or next to the `.exe`):

```json
{
  "leaderboards": { "Classic": [] },
  "best_scores": { "Classic": 0 }
}
```

The top 10 records are kept, highest score first. Every record loaded from disk
is validated — a damaged entry is repaired or dropped — so a hand-edited or
corrupted file can never crash the game.

---

## Tests

```powershell
python -m pytest        # 74 unit tests of the rules
python smoke_test.py    # headless UI run, writes 12 screenshots
```

The smoke test uses SDL's dummy video and audio drivers, so it needs no window
and no sound card. It exercises the menu, name entry, moves, the HUD buttons,
the hint (click, toggle and `H` key), both win choices, the no-moves game over,
the game-over buttons and the leaderboard.

---

## Build the .exe yourself

```powershell
python -m pip install pyinstaller
python -m PyInstaller 2048TileAdventure.spec --noconfirm --clean
```

Or double-click **`build_exe.bat`**, which runs the unit tests and the smoke
test first and only packages the game if both pass. The result is
`dist/2048TileAdventure.exe`.

---

## Design decisions

1. **The merge rule lives in exactly one function.** `merge_row_left_detailed`
   packs a line, merges equal neighbours once and records where every tile came
   from, so the engine, the animations and the solver can never disagree.
2. **A merged tile cannot merge again in the same move** — the merge loop skips
   both source tiles (`[4,4,8,0] → [8,8,0,0]`, never `[16,0,0,0]`).
3. **The win prompt is an event, not a question inside the core.**
   `check_game_status` returns a `WON` event; the UI shows the overlay and later
   calls `resolve_win_choice`, which keeps the rules front-end independent.
4. **The hint only advises.** `get_hint` is a read-only function; the player
   still makes the move.
5. **Failures degrade instead of crashing** — no audio device means a silent
   game, an unwritable folder means the score is not saved, a damaged save file
   means an empty leaderboard.
6. **Every constant lives in `core/constants.py`**, so changing the grid size or
   the target tile is a one-line edit.

---

## Limitations

- The hint solver looks one move ahead and does not model the random spawn, so
  it can suggest a move that is bad several moves later.
- The leaderboard is local only; there is no online sync.
- The window is a fixed 900×900 and does not scale.
- There is no undo and no settings screen beyond the sound toggle.
