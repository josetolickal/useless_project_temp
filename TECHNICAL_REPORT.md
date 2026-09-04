# Virtual Dog (Chavalam Patti) — Complete Technical Project Report

> **Purpose:** This document is a comprehensive reference for any AI agent or developer who needs to completely understand, extend, or debug the **Chavalam Patti** Virtual Dog desktop companion project.

---

## 1. Project Identity

| Field | Value |
|---|---|
| **Project Name** | Chavalam Patti (Virtual Dog) |
| **Team Name** | SHORT CIRCUIT |
| **Team Members** | Jose T Olickal, Irwin J Thekkekara |
| **College** | Muthoot Institute of Technology and Science |
| **Event** | TinkerHub Useless Projects |
| **Repository** | `C:\Users\Jose T Olickal\Desktop\Virtual-Dog` (branch: `dogengine`) |
| **GitHub** | https://github.com/tekku11/Virtual-Dog |
| **Primary Runtime** | `.venv\Scripts\python.exe` |
| **OS Target** | Windows 10 / 11 only |

---

## 2. What the Project Does (Plain English)

Chavalam Patti is an animated, interactive dog that lives permanently on top of all Windows desktop applications as a **frameless, click-through transparent overlay**. It responds to cursor movement, keyboard commands, mouse gestures, Spotify music, and a 30-second hunger countdown. It can roll in mud, get cleaned with a shower, go Super Saiyan, spin into a tornado, dance to Spotify music, force screen time breaks, and physically pick up and drag real desktop shortcut icons across the screen.

There is **exactly one main window** (`dog`, a `QLabel`) plus several satellite overlay windows (tornado, cleaning, hunger freeze, screen break, footprints, HUD label, toys). All windows are frameless, always-on-top, and transparent to mouse events (except the hunger freeze and screen break overlays, which intentionally block clicks).

---

## 3. Technology Stack

| Category | Technology |
|---|---|
| **Language** | Python 3.10+ |
| **GUI Framework** | PySide6 / Qt6 |
| **Main GUI Classes** | `QLabel`, `QWidget`, `QPixmap`, `QPainter`, `QTransform`, `QTimer`, `QFont`, `QColor`, `QPen`, `QBrush`, `QFileIconProvider`, `QSoundEffect` |
| **Audio Backend** | `PySide6.QtMultimedia` with FFmpeg; `winsound` native Windows fallback |
| **System Integration** | `ctypes` + `wintypes` for Win32 API calls (`User32.dll`, `Gdi32.dll`, `Dwmapi.dll`) |
| **Input Hooks** | `pynput.keyboard` (global hotkeys, per-key listener), `pynput.mouse` (global click listener) |
| **Spotify Detection** | PowerShell + `GlobalSystemMediaTransportControlsSessionManager` WinRT API, streamed via `subprocess.Popen` in a daemon thread |
| **File I/O** | `QFileIconProvider`, `QFileInfo` for native Windows icon extraction; `os.startfile()` for shortcut launching |
| **Threading** | `threading.Thread` (daemon) for Spotify detection |
| **Single-Instance Guard** | `CreateMutexW("VirtualDog_SingleInstance_2026")` via `ctypes.windll.kernel32` |

---

## 4. File & Directory Structure

```
Virtual-Dog/
├── main.py                   ← Entire application (6987 lines, ~170 KB)
├── feeding_feature.py        ← Standalone feeding mini-app (533 lines)
├── README.md                 ← Project README (TinkerHub format)
├── readme.nd                 ← Identical copy of README.md
├── README.txt                ← Old feeding module docs
│
├── assets/
│   ├── dog/                  ← 8 walk frames (walk_01–08.png)
│   ├── eating/               ← 10 eating frames (eat_01–10.png)
│   ├── food/                 ← chicken_drumstick.png
│   ├── cat/                  ← cat_run_01–03.png, cat_sit.png
│   ├── toys/                 ← ball_tennis.png, ball_red.png
│   └── sounds/
│       ├── bark.wav           ← Normal bark sound
│       ├── bark_alt.wav       ← Alternate bark
│       ├── ssj.wav            ← Super Saiyan / Kamehameha sound
│       └── tornado.wav        ← Looping tornado whoosh
│
├── (root-level PNGs)         ← All loaded from root directory:
│   ├── walk_01–08.png         (8 frames, WALK_SIZE=70px)
│   ├── run_1–8.png            (8 frames, RUN_SIZE=80px)
│   ├── sleep_01–08.png        (8 frames, SLEEP_SIZE=75px)
│   ├── ssj_01–08.png          (8 frames, side-view SSJ)
│   ├── ssj_front_01–10.png    (10 frames, front-view hunger rage SSJ)
│   ├── tornado_01–10.png      (10 frames, dog+tornado composite)
│   ├── mud_roll_01–10.png     (10 frames)
│   ├── mud_walk_01–10.png     (10 frames)
│   ├── mud_run_01–10.png      (10 frames)
│   ├── eat_01–10.png          (10 frames, with chicken inside frame)
│   ├── cleaning_01–10.png     (10 frames, shower composite)
│   └── chicken_drumstick.png
│
├── feeding_standalone/       ← Isolated version of feeding feature
├── useless_project_temp/     ← Template README and scratch files
└── .venv/                    ← Python virtual environment
```

### Key Fact: Image Loading
- `load_image(filename)` searches up to 12 candidate paths in order, printing "MISSING IMAGE" and calling `sys.exit(1)` if not found.
- `prepare_frame(img, size)` scales to the given `size`, bottom-aligns to a 400×400 canvas (`CANVAS_SIZE`), and returns a `QPixmap`.
- All frames are pre-loaded at startup into Python lists. There are **no disk reads during the animation loop**.

---

## 5. Constants & Configuration

All tunable constants are defined as module-level globals at the top of `main.py`:

```python
# Canvas & Display
CANVAS_SIZE = 400           # All dog windows are 400×400
FPS = 60                    # QTimer fires at 1000/60 ≈ 16.7ms

# Animation sizes (pixels within the 400×400 canvas)
WALK_SIZE = 70
RUN_SIZE = 80
SLEEP_SIZE = 75

# Movement speeds (pixels per frame tick)
MAX_RUN_SPEED = 5.0
MAX_WALK_SPEED = 2.5
MIN_CLOSE_SPEED = 0.7

# Distance thresholds (pixels from dog center to cursor)
RUN_DISTANCE = 350
SLOW_DISTANCE = 150
CATCH_DISTANCE = 35

# Animation frame rates (subdivided from FPS)
WALK_FPS = 8, RUN_FPS = 10, SLEEP_FPS = 5
SSJ_FPS = 8, TORNADO_FPS = 12

# Sitting: sits after being stationary for this many seconds
SIT_TIME = 3.0

# Super Saiyan
SSJ_START_SCALE = 1.0, SSJ_MAX_SCALE = 1.55
SSJ_GROWTH_SPEED = 0.012, SSJ_PADDING = 80

# Screen Shake (during SSJ)
SHAKE_AMOUNT = 6, SHAKE_SPEED = 2

# Tornado
TORNADO_FRAME_COUNT = 10, TORNADO_SIZE = 170
TORNADO_DURATION = 5.0         # seconds
TORNADO_MOTION_RADIUS = 200    # pixels radius of circular movement
TORNADO_ANGULAR_SPEED = 0.055  # radians per frame

# Tornado gesture detection
CIRCLE_HISTORY_LENGTH = 80     # cursor positions stored
TORNADO_MIN_RADIUS = 55
TORNADO_MAX_RADIUS = 700
TORNADO_REQUIRED_ANGLE = 270°  # must complete 270° arc
TORNADO_DIRECTION_THRESHOLD = 0.62
TORNADO_MIN_SPEED = 80.0       # pixels/second

# Mud Mode
MUD_ROLL/WALK/RUN_FRAME_COUNT = 10
FOOTPRINT_DISTANCE = 30.0      # pixels traveled before new footprint
MAX_FOOTPRINTS = 300

# Cleaning
CLEANING_FRAME_COUNT = 10, CLEANING_FPS = 10
CLEANING_SCALE = 0.42          # scale whole frame to match normal dog

# Feeding / Hunger
FEED_INTERVAL = 30.0           # seconds between required feeds
FEED_EFFECT_DURATION = 1.2     # seconds drumstick is visible
HUNGER_RAGE_DURATION = 5.2     # seconds of freeze overlay
EATING_FRAME_COUNT = 10, EATING_FPS = 10

# Hunger Rage SSJ (front-view)
HUNGER_SSJ_FRAME_COUNT = 10
HUNGER_SSJ_MAX_SCALE = 1.55

# Sounds
BARK_VOLUME = 0.7, SSJ_VOLUME = 0.85, TORNADO_VOLUME = 0.80
RUN_BARK_INTERVAL_MIN = 1.1, MAX = 1.5   # seconds between barks

# Screen Time Break
SCREEN_TIME_LIMIT = 60.0       # 1 minute → break triggers
BREAK_WALK_SPEED = 3.5

# Operating Modes
MODE_INTERACTIVE = "Interactive"
MODE_FREE = "Free"
MODE_FETCH = "Fetch"
INTERACTIVE_MODE_DURATION = 300.0   # 5 minutes
FREE_MODE_DURATION = 300.0          # 5 minutes
FETCH_MODE_DURATION = 300.0         # 5 minutes
```

---

## 6. Global State Variables

These are the runtime state booleans and scalars that drive every behavior:

```python
# Dog position (top-left of 400×400 canvas, in screen coordinates)
dog_x: float  # starts at screen center
dog_y: float

# Core animation state machine
state: str      # "idle" | "sitting" | "sleeping" | "walk" | "run"
                # "mud" | "mud_walk" | "mud_run" | "mud_roll"
facing: int     # 1 = right, -1 = left

# Animation frame indices and sub-frame timers
walk_index, run_index, sleep_index: int
walk_timer, run_timer, sleep_timer: float   # accumulates FPS ticks

# SSJ state
ssj_active: bool
ssj_scale: float          # current scale factor (1.0 → 1.55)
right_button_down: bool   # True while right mouse held on dog
ssj_index: int, ssj_timer: float

# Tornado state
tornado_active: bool
tornado_start_time: float
tornado_angle: float       # current orbital angle in radians
tornado_origin_x/y: float  # center point of circular orbit
tornado_direction: int     # 1 or -1
tornado_motion_radius: float

# Mud mode state
muddy_active: bool
mud_roll_playing: bool     # True during mud-roll animation (blocks other actions)
mud_roll/walk/run_index: int
mud_roll/walk/run_timer: float
mud_command: str | None    # inter-thread command queue (single slot)
last_footprint_x/y: float
footprint_side: int        # alternates -1/1 for left/right paw

# Cleaning state
cleaning_active: bool
cleaning_index: int, cleaning_timer: float

# Feeding state
feeding_active: bool        # True for FEED_EFFECT_DURATION after F pressed
feeding_end_time: float
food_deadline: float        # monotonic time by which dog must be fed
hunger_rage_active: bool
hunger_rage_end_time: float
hunger_rage_pending: bool   # prevents re-triggering same frame
eating_active: bool         # True during 10-frame eating animation
eating_index: int, eating_timer: float
hunger_ssj_index: int, hunger_ssj_timer: float, hunger_ssj_scale: float

# Run barking state
last_bark_time: float
next_bark_interval: float   # randomized between 1.1–1.5s
bark_index: int             # alternates between bark.wav / bark_alt.wav
was_running: bool

# Cursor gesture / circle detection
cursor_history: deque(maxlen=80)  # (x, y, time) tuples
last_cursor_x/y: float | None
last_cursor_time: float | None

# Screen shake (during SSJ/Hunger Rage)
shake_active: bool
shake_window: QWidget | None
shake_original_x/y: int
shake_timer: int

# Screen time break
screen_time_start: float    # monotonic, reset after each break
break_active: bool
break_stage: str            # "idle" | "walking" | "sleeping"
break_target_x/y: float

# Dance (Spotify)
dance_active: bool
dance_step_index: int
dance_step_timer: float
dance_facing: int
dance_spin_active: bool, dance_spin_angle: float, dance_spin_end_time: float
dance_notes: list           # particle note objects
dance_last_note_time: float
dance_target_x/y: float     # where dog runs to during dance
dance_target_end_time: float
dance_speed: float          # = 7.2

# Misc
kill_requested: bool        # set by Ctrl+Shift+Q → graceful shutdown
sit_start: float | None     # time dog entered sitting state
```

---

## 7. Window Architecture

The application uses **multiple independent, always-on-top, frameless `QLabel`/`QWidget` windows**. They are never embedded inside each other.

```
┌─────────────────────────────────────────────────────────┐
│                   Windows Desktop                       │
│                                                         │
│  [dog: QLabel 400×400]         ← Main dog window       │
│    WA_TransparentForMouseEvents = True (click-through)  │
│                                                         │
│  [tornado_dog: QLabel 400×400] ← Only shown during     │
│    WA_TransparentForMouseEvents = True   tornado        │
│                                                         │
│  [cleaning_dog: QLabel]        ← Only shown during     │
│    WA_TransparentForMouseEvents = True   shower clean   │
│                                                         │
│  [footprints_overlay: QWidget] ← Full-screen footprint │
│    WA_TransparentForMouseEvents = True   canvas         │
│                                                         │
│  [food_timer_label: HUDLabel]  ← Top-left info bar     │
│    Clickable → opens mode context menu                  │
│                                                         │
│  [hunger_overlay: HungerFreezeOverlay] ← Full screen   │
│    WA_TransparentForMouseEvents = False (BLOCKS clicks) │
│    Captures a screenshot, displays frozen icy frame     │
│                                                         │
│  [break_overlay: BreakOverlay] ← Full screen black     │
│    WA_TransparentForMouseEvents = False (BLOCKS clicks) │
│    "☕ Take a break!" text painted via QPainter         │
│                                                         │
│  [cat.label: QLabel] (Free Mode) ← Cat companion       │
│  [balls[0].label, balls[1].label: QLabel] (Free Mode)  │
│  [fetch_widget: DesktopShortcutWidget] (Fetch Mode)     │
└─────────────────────────────────────────────────────────┘
```

**Critical Design Rule:** The main `dog` QLabel is always `WA_TransparentForMouseEvents = True` EXCEPT during SSJ, when it is temporarily set to `False` to receive right-mouse-button events. It is reset after SSJ ends.

---

## 8. All 9 Classes — Detailed Reference

### 8.1 `FootprintOverlay(QWidget)` — Lines ~377–496
- **Purpose:** Full-screen transparent canvas that paints muddy paw prints.
- **Key Fields:** `footprints: list[(x, y, side)]`
- **Key Methods:**
  - `add_footprint(x, y, side)` — appends a paw print tuple; cap at `MAX_FOOTPRINTS=300` (FIFO eviction)
  - `clear_footprints()` — wipes list and triggers repaint
  - `paintEvent()` — draws each footprint as 1 main ellipse (8×7) + 3 toe ellipses (4×4) in brown `QColor(72, 43, 27, 175)`
- **Triggered by:** `record_muddy_footprints()` when muddy dog moves, and cleared by `finish_cleaning_mode()` and `resume_from_break()`

### 8.2 `HungerFreezeOverlay(QWidget)` — Lines ~503–621
- **Purpose:** Full-screen overlay that appears when the dog's hunger timer expires. Captures a screenshot, displays it with an icy blue tint + shake offset, and blocks all mouse clicks.
- **Key Fields:** `freeze_pixmap: QPixmap | None`, `shake_offset_x/y: int`
- **Key Methods:**
  - `capture_screen()` — calls `screen.grabWindow(0)` to snapshot the desktop
  - `set_shake_offset(ox, oy)` — updates shake offset and triggers repaint
  - `paintEvent()` — draws frozen screenshot with 45-alpha blue tint, icy border pen, and "❄️ WINDOWS FROZEN" banner
- **Blocks:** All mouse events while active (`WA_TransparentForMouseEvents = False`)

### 8.3 `BreakOverlay(QWidget)` — Lines ~634–741
- **Purpose:** Full-screen pure black overlay for screen time breaks (after 60 seconds of usage).
- **paintEvent():** Draws `QColor(5, 7, 12, 255)` background, a rounded dark banner with "☕ Take a break!" title and "Your dog is tired. Press any key or click to resume." subtitle.
- **Resume:** Any `mousePressEvent` or `keyPressEvent` calls `resume_from_break()`.

### 8.4 `HUDLabel(QLabel)` — Lines ~937–983
- **Purpose:** Styled info label at top-left showing mode, timers, feeding countdown, and Spotify status.
- **Style:** Dark semi-transparent rounded rectangle (`rgba(20, 24, 32, 215)`) with blue hover border.
- **Interaction:** `mousePressEvent` calls `show_mode_menu(event.globalPos())` — opens the context menu.

### 8.5 `FreeCatCompanion` — Lines ~1830–2027
- **Purpose:** A 3-frame animated cat that flees from the dog in Free Mode chase substate.
- **Key Fields:** `x, y, vx, vy` (position + velocity), `facing`, `anim_frame`, `active`, `sit_timer`, `tag_cooldown`
- **Sprites:** `cat_run_01–03.png` (3-frame run loop) + `cat_sit.png`. Pre-flipped left/right at load time.
- **AI Behavior:**
  - Computes flee vector away from `(dog_cx, dog_cy)`
  - Adds sinusoidal lateral wiggle: `wiggle = sin(now * 5.0) * 0.45` applied perpendicular to flee direction
  - Velocity blending: `vx = vx * 0.82 + evade_x * speed * 0.18` (momentum + steering)
  - Screen boundary bounce with 1.2× speed boost on walls
  - On tag (within 55px): 45% chance to sit briefly, 55% chance to leap away at 8–12 px/frame
  - Calls `play_bark_sound()` on tag

### 8.6 `FreeBallToy` — Lines ~2029–2178
- **Purpose:** A physics-simulated ball (tennis or red) with gravity, wall-bounce, and dog kick.
- **Ball Types:**
  - Tennis: `restitution=0.76`, `gravity=0.38`
  - Red: `restitution=0.84`, `gravity=0.42`
- **Physics per tick:**
  - `vy += gravity` (gravity)
  - `vx *= 0.991` (air resistance)
  - Floor bounce: `vy = -vy * restitution`; below threshold → `vy = 0.0`
  - Wall bounce: reflect and multiply by restitution
- **Dog Kick:** If dog center within 54px and cooldown expired → `vx = ±7–11.5`, `vy = -9–14`
- **Rotation:** `angle += vx * 4.5`; pixmap rotated via `QTransform().rotate(angle)` every frame

### 8.7 `DesktopShortcutWidget(QLabel)` — Lines ~2298–2365
- **Purpose:** Visual desktop shortcut badge that the dog picks up in its mouth during Fetch Mode and drags across the screen.
- **Key Fields:** `active, shortcut_name, shortcut_path, x, y, is_held`
- **Methods:**
  - `setup(name, path, x, y)` — calls `create_shortcut_badge()`, shows widget at `(x, y)`
  - `update_position(x, y)` — moves widget (called every frame during dragging)
  - `drop(x, y)` — sets `is_held=False`, moves to final destination
  - `despawn()` — hides, clears `active`
  - `mouseDoubleClickEvent()` — calls `os.startfile(shortcut_path)` to launch the real application
- **Badge Creation** (`create_shortcut_badge()`):
  - 72×92 px transparent `QPixmap` canvas
  - Extracts real Windows app icon via `QFileIconProvider().icon(QFileInfo(path)).pixmap(48, 48)`
  - Falls back to blue rounded-rect with first letter if icon unavailable
  - Draws Windows shortcut arrow badge (`↗` in white box at bottom-left of icon)
  - Renders name label with black drop shadow at bottom

### 8.8 `SpotifyMusicDetector` — Lines ~2458–2541
- **Purpose:** Monitors Spotify playback in real time without any library dependency.
- **Architecture:** Spawns a PowerShell daemon process via `subprocess.Popen` using a base64-encoded embedded PowerShell script. Output is streamed line-by-line in a background daemon thread.
- **Detection Method 1 (Primary):** `GlobalSystemMediaTransportControlsSessionManager` WinRT API — detects any Spotify session with `PlaybackStatus == Playing` (enum value 4)
- **Detection Method 2 (Fallback):** `Get-Process Spotify` — reads window title (contains track name when playing)
- **Output Protocol:** PowerShell emits `PLAYING|Artist - Title` or `STOPPED` to stdout on state change only
- **Python Side:**
  - `is_playing: bool` — set by background thread from PowerShell output
  - `track_title: str` — current "Artist - Title" string
  - `manual_override: None | bool` — overrides detection; toggled by `D` key / `Ctrl+D`
- **`is_music_playing()`** — returns `manual_override` if set, else `is_playing`
- **`stop()`** — sets `_running=False`, kills subprocess

### 8.9 `ModeController` — Lines ~2753–3298
- **Purpose:** Manages the 3 operating modes and their autonomous behaviors.
- **Key Fields:**
  - `current_mode: str` — "Interactive" | "Free" | "Fetch"
  - `mode_start_time: float`
  - `free_substate: str` — "idle" | "sleep" | "walk" | "run" | "chase_cat" | "play_ball" | "special"
  - `free_substate_end_time: float`
  - `free_target_x/y: float`
  - `cat: FreeCatCompanion`
  - `balls: [FreeBallToy("tennis"), FreeBallToy("red")]`
  - `fetch_widget: DesktopShortcutWidget`
  - `fetch_state: str` — "idle" | "running_to_shortcut" | "grabbing" | "dragging" | "delivering"
  - `fetch_target_shortcut: dict | None`
  - `fetch_origin_x/y, fetch_dest_x/y: float`
  - `fetch_timer: float`
  - `fetch_drag_speed: float` = 6.5
- **Mode Expiration:** All modes expire after 300 seconds → revert to Interactive
- **Detailed methods documented in Section 9.3**

---

## 9. Subsystem Deep Dives

### 9.1 Main Animation Loop

```
QTimer (60 FPS, ~16.7ms interval)
    ↓ timeout signal
update() function
    ├── Kill switch check
    ├── process_mud_commands()           ← Process keyboard/mouse command queue
    ├── check_food_timer()               ← Hunger countdown
    ├── [if break_active] update_screen_break()    ← Break walk/sleep
    ├── [if hunger_rage_active] update_hunger_rage() ← SSJ freeze
    ├── [if eating_active] update_eating()
    ├── [if cleaning_active] update_cleaning()
    ├── [if tornado_active] update_tornado() + check_tornado()
    ├── [else] mode_controller.update()  ← Mode-specific behavior
    │       ├── check_mode_expiration()
    │       ├── [if spotify playing] update_dance() + update_dance_display()
    │       ├── [if MODE_FREE] update_free_behavior()
    │       └── [if MODE_FETCH] update_fetch_behavior()
    ├── [if ssj_active] update_ssj() + update_ssj_display()
    ├── [Interactive mode] move_dog() + update_display()
    └── update_food_timer_display()      ← Refresh HUD label
```

### 9.2 Interactive Mode — Cursor-Following Behavior

`move_dog()` function (~line 5769):

1. Get cursor position via `QCursor.pos()` → `(mouse_x, mouse_y)`
2. Compute cursor position relative to dog center
3. **Distance-based state transitions:**
   - `> RUN_DISTANCE (350px)` → `state = "run"`, speed = `MAX_RUN_SPEED (5.0)`
   - `> SLOW_DISTANCE (150px)` → `state = "walk"`, speed = `MAX_WALK_SPEED (2.5)`
   - `> CATCH_DISTANCE (35px)` → `state = "walk"`, speed = `MIN_CLOSE_SPEED (0.7)`
   - `<= CATCH_DISTANCE` → `state = "sitting"`, record `sit_start`
   - After `SIT_TIME (3.0s)` sitting → `state = "sleeping"`
4. Movement: `dog_x += (dx / dist) * speed` with screen boundary clamping
5. `facing` set based on sign of `dx`

**SSJ Trigger (during Interactive and any mode):**
- Right mouse held on dog → `right_button_down = True` → `ssj_active = True`
- `update_ssj()`: `ssj_scale += SSJ_GROWTH_SPEED (0.012)` per frame, clamped at `SSJ_MAX_SCALE (1.55)`
- Dog temporarily loses `WA_TransparentForMouseEvents` to receive right-click

**Tornado Trigger:**
- `cursor_data()` records `(x, y, time)` to deque every frame
- `check_tornado()` analyzes last 80 cursor positions:
  - Computes centroid, measures angular coverage, checks direction consistency, verifies min speed
  - If 270° arc completed at ≥80 px/s with consistent CW/CCW → `start_tornado()`
- `start_tornado()`: hides `dog`, shows `tornado_dog`, plays tornado sound, sets `tornado_active=True`
- `update_tornado()`: orbits around `(tornado_origin_x, tornado_origin_y)` at `TORNADO_ANGULAR_SPEED`, cycling through 10 frames at `TORNADO_FPS=12`
- Auto-stops after `TORNADO_DURATION=5.0` seconds

### 9.3 Operating Mode Controller — ModeController

**`set_mode(new_mode)`:**
1. Bail if already in target mode
2. Call `stop_current_mode()` → `despawn_toys()` + reset `fetch_state`
3. Set `current_mode`, reset `mode_start_time`
4. Dispatch to `start_interactive_mode()` / `start_free_mode()` / `start_fetch_mode()`
5. Call `update_food_timer_display()` to refresh HUD

**Free Mode — Autonomous Substate Weights:**

| Current → Next | Options | Weights (Muddy / Clean) |
|---|---|---|
| idle → | run, play_ball, chase_cat, walk, special | 60/15/12/8/5 (muddy) or walk,sleep,ball,cat,special,run = 42/22/16/14/4/2 (clean) |
| run → | run, play_ball, chase_cat, walk, idle | 55/18/15/7/5 (muddy) or idle,walk = 60/40 (clean) |
| walk → | run, play_ball, chase_cat, idle | 65/15/12/8 (muddy) or idle,sleep,ball,cat,walk,run = 45/18/18/15/2/2 (clean) |
| sleep → | | idle,walk,ball,cat = 70/20/5/5 (clean only) |
| chase_cat → | run, play_ball, idle | 60/20/20 (muddy) or idle,walk,ball = 45/35/20 (clean) |
| play_ball → | run, chase_cat, idle | 60/20/20 (muddy) or idle,walk,sleep = 45/35/20 (clean) |

**Key behavioral rule:** Clean dog in Free Mode is mostly calm (idle/sleep/walk with only 2% run chance). Muddy dog in Free Mode runs ~60% of the time.

**Fetch Mode — 4-Phase State Machine:**

```
"idle"
  → trigger_fetch() called
  → scan_desktop_shortcuts() → pick random shortcut
  → compute fetch_origin (icon grid pos), fetch_dest (random screen pos)
  → call fetch_widget.setup() → shows badge at origin
  → fetch_state = "running_to_shortcut"

"running_to_shortcut"
  → Dog sprints at MAX_RUN_SPEED toward (origin_x - 200 - facing*25, origin_y - 260)
  → Timeout after 14s (fallback if can't reach)
  → On arrival (dist < 20px): fetch_state = "grabbing", fetch_timer = now + 0.45s
  → Bark sound plays

"grabbing" (0.45s duration)
  → Dog sits, widget positioned at dog mouth: (dog_cx + facing*25 - 36, dog_cy - 75)
  → fetch_widget.is_held = True
  → After 0.45s: fetch_state = "dragging", bark plays

"dragging"
  → Dog runs at fetch_drag_speed (6.5 px/frame) toward (dest_x - 200 - facing*25, dest_y - 260)
  → Widget follows with running bob: y += sin(now * 15) * 3.0
  → Muddy dog leaves footprints
  → Timeout after 20s (fallback)
  → On arrival (dist < 20px): fetch_widget.drop(dest_x, dest_y), fetch_state = "delivering"
  → Bark plays, HUD updates

"delivering" (1.2s duration)
  → Dog sits, widget stays at destination
  → After 1.2s: fetch_state = "idle"
  → Dropped widget remains visible and double-clickable to launch app
```

### 9.4 Mud Mode

- **Enter:** Press `M` → `start_mud_mode()` → play 10-frame mud roll animation → set `muddy_active=True`
- **Animation:** During mud roll, `mud_roll_playing=True` blocks all other movement
- **Muddy states:** Replace normal states: `mud`(idle), `mud_walk`, `mud_run`
- **Footprints:** `record_muddy_footprints()` called when muddy and moving. Every `FOOTPRINT_DISTANCE (30px)` traveled, alternates left/right paw, calls `footprints_overlay.add_footprint(x, y, side)`
- **Exit:** Press `C` → `start_cleaning_mode()` → 10-frame shower animation on `cleaning_dog` window → `finish_cleaning_mode()` → `muddy_active=False`, footprints cleared

### 9.5 Feeding & Hunger System

- `food_deadline = time.monotonic() + 30.0` — initialized at startup
- `check_food_timer()` runs every frame:
  - If `time.monotonic() > food_deadline` and not in rage/eating → trigger rage
  - HUD shows countdown; flashes "⚠️ FEED NOW" when ≤5 seconds
- **Feeding:**
  - Press `F` → `start_feeding()` → `eating_active=True`, play 10-frame eat animation
  - `finish_eating()` → resets `food_deadline = now + FEED_INTERVAL`
- **Hunger Rage:**
  - `start_hunger_rage()` → captures screen, shows `hunger_overlay`, plays SSJ sound, starts screen shake
  - During rage: front-facing SSJ animation (`ssj_front_01–10.png`) with scale growth
  - Auto-ends after `HUNGER_RAGE_DURATION (5.2s)` → `food_deadline` reset

**Hunger & Break are BOTH suspended when Spotify music is playing.**

### 9.6 Screen Time Break System

- `screen_time_start = time.monotonic()` — reset after each break
- Every frame: `if now - screen_time_start > SCREEN_TIME_LIMIT (60s) → start_screen_break()`
- `start_screen_break()`:
  1. Pauses Free Mode autonomous toys
  2. Shows `break_overlay` (black fullscreen)
  3. Sets `break_stage = "walking"`
  4. Sets `break_target_x/y` = screen center
- `update_screen_break()` called during break:
  - Stage "walking": move dog toward center at `BREAK_WALK_SPEED (3.5)`, state="walk"
  - On arrival: `break_stage = "sleeping"`, state="sleeping"
- **Resume:** Any key press or click → `resume_from_break()` → hides overlay, resets `screen_time_start`, restores dog state

### 9.7 Spotify Dance System

When `spotify_detector.is_music_playing()` returns True:
1. `mode_controller.update()` early-returns after despawning toys and calling `update_dance()` + `update_dance_display()`
2. `update_dance()`:
   - Randomly picks new `dance_target_x/y` every 1.0–2.5 seconds (random points on screen)
   - Dog runs to target at `dance_speed (7.2)` continuously
   - Spawns floating note particles every 0.4s: random note symbols `♪♫🎵🎶♩`, random colors, float upward, fade out over 1.8s
   - Periodic spin: 360° rotation `dance_spin_angle += 18°/frame` for 0.6s
3. `update_dance_display()` → `get_dance_pixmap()`:
   - Renders current run frame with squash/stretch (`squash_x`, `squash_y`)
   - Applies `tilt_deg = sin(now * 8) * 12°` rotation
   - During spin: uses `dance_spin_angle`
   - Draws floating musical notes on top

**Key:** Dance mode suspends hunger timer, screen break timer, Free Mode substates, and cat/ball toys.

### 9.8 Sound System (Dual-Path Architecture)

Every sound uses two parallel playback paths for reliability:
1. **PySide6 QSoundEffect** (via Qt FFmpeg backend)
2. **`winsound.PlaySound()`** (native Windows WinMM)

| Sound | File | Trigger | Loop |
|---|---|---|---|
| `bark.wav` | Bark | Dog running (every 1.1–1.5s), fetch trigger, cat tag, ball kick | No |
| `bark_alt.wav` | Bark alternate | Alternates with bark.wav | No |
| `ssj.wav` | Kamehameha/SSJ | SSJ start, hunger rage start | No |
| `tornado.wav` | Tornado whoosh | Tornado start | Yes (infinite) |

`play_bark_sound()` alternates `bark_index` between 0 and 1 (bark.wav / bark_alt.wav).

---

## 10. Input System

### 10.1 Keyboard Listeners

Two separate pynput listeners run concurrently:

**`keyboard_listener` (GlobalHotKeys):**
```
Ctrl+Shift+Q  → kill_dog()
Ctrl+1        → queue_mode_command("mode_interactive")
Ctrl+2        → queue_mode_command("mode_free")
Ctrl+3        → queue_mode_command("mode_fetch")
Ctrl+G        → queue_mode_command("fetch_shortcut")
Ctrl+K        → queue_mode_command("chase_cat")
Ctrl+B        → queue_mode_command("play_ball")
Ctrl+D        → queue_mode_command("toggle_dance")
```

**`mud_keyboard_listener` (Listener, per-key):**
- If `break_active`: any key → `mud_command = "resume_break"`
- If in `MODE_FETCH`: Space/Enter → fetch; any letter → fetch (except reserved keys below)
- `m` → mud, `c` → clean, `f` → feed
- `1` → mode_interactive, `2` → mode_free
- `3` → mode_fetch (or fetch_shortcut if already in Fetch Mode)
- `k` → chase_cat, `b` → play_ball, `d` → toggle_dance, `g` → fetch_shortcut

**Command Queue Mechanism:**
- All key handlers write to `mud_command: str | None` (single global slot)
- `process_mud_commands()` reads and clears this slot on the main Qt thread each frame
- This safely bridges the pynput background thread to the Qt main thread without locks

### 10.2 Mouse Listeners

**`mouse_listener` (pynput global):**
- Right button press/release → `right_button_down = True/False`
- Left button press → if in Fetch Mode AND cursor is over dog → `queue_mode_command("fetch_shortcut")`

**`cursor_over_dog()`:** Returns `True` if cursor is within `dog_x ±35` / `dog_y ±35`

### 10.3 Right-Click Context Menu

`show_mode_menu(global_pos)` — triggered by clicking the HUD label or (some build variants) right-clicking the dog:
- Shows mode-switching actions with checkmarks for current mode
- "🐕 Fetch Mode ✓ / (Key 3)"
- "🎾 Go Fetch Shortcut!" (only shown when in Fetch Mode)
- Cat chase, ball play, feed, mud/clean, break, quit

---

## 11. Startup Sequence

1. **Single-Instance Guard:** `CreateMutexW("VirtualDog_SingleInstance_2026")` — exits if already running
2. **QApplication created**
3. **Window creation:** `dog`, `tornado_dog`, `cleaning_dog` QLabels configured with flags
4. **Mode constants set**
5. **Overlay widgets created:** `FootprintOverlay`, `HungerFreezeOverlay`, `BreakOverlay`
6. **Show mode context menu function defined** (`show_mode_menu`)
7. **HUDLabel created** (`food_timer_label`)
8. **Image loading pipeline:** `load_animation()`, `load_run_animation()`, `load_ssj_animation()`, `load_tornado_animation()`, `load_mud_animation()`, `load_eating_animation()`, `load_cleaning_animation()` — all frames pre-loaded into Python lists
9. **Sound effects loaded:** `load_sound_effects()` → `QSoundEffect` objects for bark, ssj, tornado
10. **Global state variables initialized** (position, state, animation indices, timers, flags)
11. **Companion classes loaded:** `FreeCatCompanion`, `FreeBallToy`×2 constructed
12. **Fetch mode classes loaded:** `DesktopShortcutWidget` created
13. **SpotifyMusicDetector started** (background daemon thread + PowerShell subprocess)
14. **ModeController instantiated** (creates cat, balls, fetch_widget internally)
15. **Keyboard & mouse listeners started**
16. **QTimer started** at 60 FPS → `update()` called every ~16.7ms
17. **Initial display:** `dog.show()`, initial HUD state, all overlays hidden
18. **`app.exec()` enters Qt event loop**

---

## 12. Shutdown Sequence

Triggered by `Ctrl+Shift+Q` → `kill_requested = True` → next `update()` call:
1. `mode_controller.stop_current_mode()` → despawn all toys and fetch widget
2. `stop_screen_shake()`
3. Hide all windows: `dog`, `tornado_dog`, `cleaning_dog`, `hunger_overlay`, `break_overlay`, `food_timer_label`, `footprints_overlay`
4. `timer.stop()` — halt 60 FPS loop
5. `keyboard_listener.stop()`, `mouse_listener.stop()`
6. `stop_ssj_sound()`, `stop_tornado_sound()`
7. `spotify_detector.stop()` — kill PowerShell subprocess
8. `app.quit()` → exits `app.exec()`
9. `finally` block: redundant cleanup of all listeners and sounds

---

## 13. Key Helper Functions Reference

| Function | Location | Purpose |
|---|---|---|
| `update()` | ~6398 | Main 60 FPS tick — dispatches all subsystems |
| `process_mud_commands()` | ~6324 | Reads `mud_command` and dispatches to mode/action functions |
| `move_dog()` | ~5769 | Cursor-following physics for Interactive Mode |
| `cursor_data()` | ~5729 | Captures cursor position+velocity for circle detection |
| `check_tornado()` | ~5696 | Analyzes cursor history for circular gesture |
| `start_tornado(cx, cy, dir)` | ~5412 | Initiates tornado: hides dog, shows tornado_dog, starts sound |
| `stop_tornado()` | ~5501 | Restores normal dog after tornado |
| `update_tornado()` | ~5571 | Orbits tornado around center, advances frames |
| `start_hunger_rage()` | ~5230 | Captures screen, shows freeze overlay, starts SSJ audio |
| `update_hunger_rage()` | ~5313 | Animates front SSJ, shake, auto-ends after 5.2s |
| `check_food_timer()` | ~5379 | Checks deadline, triggers rage if expired |
| `start_feeding()` | ~5104 | Begins 10-frame eating animation |
| `update_eating()` | ~5149 | Advances eating frames |
| `finish_eating()` | ~5201 | Resets food_deadline, returns to normal state |
| `start_mud_mode()` | ~4600 area | Plays mud roll animation, sets muddy_active |
| `start_cleaning_mode()` | ~4900 area | Shows cleaning_dog, plays 10-frame shower animation |
| `finish_cleaning_mode()` | ~4953 | Restores clean dog, clears footprints |
| `record_muddy_footprints()` | ~3400 area | Adds paw print if dog moved ≥30px since last print |
| `start_screen_break()` | ~743 | Shows break overlay, sets walking stage to center |
| `resume_from_break()` | ~787 | Hides break, resets screen_time_start |
| `update_screen_break()` | ~813 | Moves dog to center, transitions to sleeping |
| `start_ssj()` | ~3700 area | Begins SSJ growth (right mouse held on dog) |
| `stop_ssj()` | ~3750 area | Ends SSJ, restores click-through |
| `update_ssj()` | ~3780 area | Grows scale, updates HUD display |
| `update_dance()` | ~2565 area | Dance movement, note particles, spin logic |
| `update_dance_display()` | ~2741 | Renders dance frame with tilt, squash, notes |
| `scan_desktop_shortcuts()` | ~2185 | Scans `~\Desktop` + `C:\Users\Public\Desktop` for shortcuts |
| `create_shortcut_badge()` | ~2223 | Creates 72×92 badge with native icon + arrow + name |
| `get_shortcut_desktop_pos(i, n)` | ~2279 | Computes Windows icon grid coordinates for index i |
| `get_random_desktop_dest()` | ~2289 | Picks random safe drop location on screen |
| `update_food_timer_display()` | ~5006 | Updates HUD label text with mode, timers, status |
| `show_mode_menu(pos)` | ~850 | Shows right-click context menu |
| `load_image(filename)` | ~990 | Searches 12 paths, exits on failure |
| `prepare_frame(img, size)` | ~1136 | Scales + bottom-aligns on 400×400 canvas |
| `flip(frame)` | ~3260 | Returns horizontally flipped QPixmap |
| `play_bark_sound()` | ~6082 | Plays bark.wav or bark_alt.wav (alternating) |
| `play_ssj_sound()` | ~1573 | Plays ssj.wav via Qt + winsound |
| `play_tornado_sound()` | ~1605 | Plays tornado.wav looping |
| `cursor_over_dog()` | ~3417 | True if mouse within dog bounds ±35px |

---

## 14. Data Flow Diagram

```
                    ┌─────────────────────┐
  Keyboard/Mouse ──→│ pynput Listeners     │ (background threads)
                    │  mud_key_handler()   │
                    │  mouse_callback()    │
                    └────────┬────────────┘
                             │ writes mud_command (single-slot queue)
                    ┌────────▼────────────┐
                    │  QTimer 60 FPS      │
                    │  update()           │
                    └────────┬────────────┘
                             │
               ┌─────────────▼─────────────────┐
               │       process_mud_commands()   │
               │  (reads+clears mud_command)    │
               └─────────────┬─────────────────┘
                             │
        ┌────────────────────▼────────────────────┐
        │              Subsystem Dispatch           │
        │                                           │
        ├── check_food_timer() → hunger_rage         │
        ├── update_screen_break() (if active)        │
        ├── update_hunger_rage() (if active)         │
        ├── update_eating() (if active)              │
        ├── update_cleaning() (if active)            │
        ├── update_tornado() (if active)             │
        ├── mode_controller.update()                 │
        │       ├── [spotify] update_dance()         │
        │       ├── [Free] update_free_behavior()    │
        │       └── [Fetch] update_fetch_behavior()  │
        ├── update_ssj() (if right mouse on dog)     │
        ├── move_dog() (Interactive Mode)            │
        └── update_display()                         │
                                                     │
        ┌────────────────────▼──────────────────────┐
        │           Render to QLabels               │
        │  dog.setPixmap(...) / dog.move(...)       │
        │  overlay windows show/hide/move           │
        │  food_timer_label.setText(...)            │
        └───────────────────────────────────────────┘

        Background (daemon thread):
        SpotifyMusicDetector._worker()
            ↓ streams to stdout
        PowerShell (GlobalSystemMediaTransportControlsSessionManager)
            ↓ stdout line-by-line
        sets spotify_detector.is_playing, .track_title
```

---

## 15. Known Design Decisions & Constraints

1. **Single file architecture:** Almost all code is in `main.py` (~7000 lines). There is no module splitting. This was an intentional choice to keep deployment simple.

2. **No actual desktop icon moving:** The Fetch Mode does NOT use Win32 `SendMessage(LVM_SETITEMPOSITION)` to actually reposition real Windows desktop icons. It creates a visual `DesktopShortcutWidget` overlay — the real icons remain in place. The dropped widget is a separate always-on-top window that can be double-clicked to launch the app.

3. **Thread safety:** The `mud_command` global acts as a single-slot queue (last write wins). This is intentionally simple; the only multi-threaded communication paths are `mud_command` (pynput → Qt thread) and `spotify_detector.is_playing` (PowerShell thread → Qt thread). Both are single-value reads/writes, not requiring locks in practice.

4. **No `WA_TransparentForMouseEvents` during SSJ:** During Super Saiyan, the main `dog` QLabel needs to receive right-click events, so `WA_TransparentForMouseEvents` is temporarily set to `False`. This is the only time the dog can be interacted with by mouse.

5. **Frame pre-loading:** All animation frames are loaded at startup. The animation loop does only `setPixmap()` with pre-loaded `QPixmap` objects — zero disk I/O during runtime.

6. **Cleaning frame scale:** The cleaning PNGs were generated with a much larger dog than the game dog. `CLEANING_SCALE = 0.42` is applied to normalize the size.

7. **Tornado composites:** Each `tornado_01–10.png` already contains the dog inside the tornado artwork. There is NO separate dog drawn during tornado. The `dog` QLabel is hidden and `tornado_dog` shows the composite PNG.

8. **Hunger rage front SSJ:** The side-view SSJ (`ssj_01–08.png`) is used when the player manually triggers SSJ by holding right mouse. The front-facing SSJ (`ssj_front_01–10.png`) is used ONLY during automatic hunger rage.

---

## 16. Adding a New Feature — Agent Guide

When adding new functionality to this project:

1. **New state flag:** Add `new_feature_active = False` as a global near other state variables (~line 1700 area).
2. **New constants:** Add constants in the constants block at the top (~line 150–360).
3. **New overlay window:** Create as `QWidget` or `QLabel` with the same flags pattern as `tornado_dog` or `cleaning_dog`.
4. **New key command:** Add `char == "x": mud_command = "new_command"` in `mud_key_handler()` AND add `"<ctrl>+x": lambda: queue_mode_command("new_command")` in `keyboard_listener`.
5. **Process command:** Add `elif command == "new_command": your_function()` in `process_mud_commands()`.
6. **New mode:** Add `MODE_NEW = "NewMode"` constant, add `elif new_mode == MODE_NEW: self.start_new_mode()` in `ModeController.set_mode()`, add duration constant, add expiration check in `check_mode_expiration()`, add HUD text in `update_food_timer_display()`, add menu item in `show_mode_menu()`.
7. **Per-frame update:** Add to `update()` function in the appropriate dispatch position.
8. **Compile check:** Run `.venv\Scripts\python.exe -m py_compile main.py`
9. **Preserve:** Never remove or alter existing functionality; only add.

---

## 17. Test Infrastructure

Located in: `C:\Users\Jose T Olickal\.gemini\antigravity-cli\brain\56c5db7c-0eb1-4e3a-9a02-217d5bc268ec\scratch\`

| Test File | Coverage |
|---|---|
| `test_operating_modes.py` | Mode switching, command queue, Free Mode navigation, expiration, feeding in all modes, hunger rage, screen break — 8 tests |
| `test_spotify_dance.py` | Detector init, note particles, canvas rendering (clean + muddy), dog running everywhere, break suspension, hunger suspension — 10 tests |
| `test_screen_break.py` | Break trigger, walk-to-center, sleeping, resume via click and key — 6 tests |
| `test_fetch_mode.py` | Shortcut scanning, badge creation, widget lifecycle, mode transition, 4-phase state machine transitions — 6 tests |

Run any test with: `.venv\Scripts\python.exe <test_file.py>` from `Virtual-Dog/` directory.
All tests use `QT_QPA_PLATFORM=offscreen` for headless execution.

---

## 18. Quick Reference Card

```
Keys:
  F = Feed dog (resets 30s hunger timer)
  M = Roll in mud (enter mud mode)
  C = Clean dog (shower animation)
  1 = Interactive Mode (cursor-following)
  2 = Free Mode (autonomous: walk/sleep/cat/ball)
  3 = Fetch Mode (desktop shortcut dragging)
  K = Chase Cat (summons cat companion in Free Mode)
  B = Ball Play (spawns 2 balls in Free Mode)
  D = Toggle Spotify Dance manually
  G = Trigger fetch shortcut
  Space/Enter = Trigger fetch (in Fetch Mode)
  Ctrl+1/2/3 = Switch mode
  Ctrl+K/B/D/G = Same as above
  Ctrl+Shift+Q = Quit

Mouse:
  Right-hold on dog = Super Saiyan (hold to grow, release to end)
  Draw circle with cursor = Tornado spin (5 seconds)
  Left click HUD label = Mode context menu
  Any click during break = Resume from break
  Double-click dropped shortcut = Launch the app

States (dog.state):
  "idle"      = standing still
  "sitting"   = sitting after reaching cursor
  "sleeping"  = sleeping after 3s sitting
  "walk"      = walking toward cursor
  "run"       = running toward cursor
  "mud"       = muddy idle
  "mud_walk"  = muddy walking
  "mud_run"   = muddy running

Automatic triggers:
  30s no feed → Hunger Rage (5.2s SSJ freeze)
  60s screen time → Break (black screen, dog sleeps at center)
  Spotify playing → Dance mode (suspends hunger & break)
```
