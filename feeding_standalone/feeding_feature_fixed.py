import sys
import time
import math
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QTransform, QPainter, QFont
from PySide6.QtWidgets import QApplication, QLabel, QWidget


# ============================================================
# SETTINGS
# ============================================================

FPS = 60
CANVAS_SIZE = 400
DOG_SIZE = 78
EAT_DOG_SIZE = 95
EAT_FRAME_COUNT = 10
EAT_FPS = 10
FEED_INTERVAL = 30.0
EATING_DURATION = 1.20
DRUMSTICK_SIZE = 72
RAGE_DURATION = 4.0

BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# WINDOWS / OVERLAYS
# ============================================================

class OverlayLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background: transparent;")


class FreezeOverlay(QWidget):
    def __init__(self, geometry):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setGeometry(geometry)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        painter.setPen(Qt.white)

        font = QFont()
        font.setPointSize(28)
        font.setBold(True)
        painter.setFont(font)

        painter.drawText(
            self.rect(),
            Qt.AlignCenter,
            "DOG HUNGER RAGE!"
        )
        painter.end()


# ============================================================
# IMAGE HELPERS
# ============================================================

def load_pixmap(path: Path) -> QPixmap:
    """Load one image and fail with a useful message if it is missing."""
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        raise FileNotFoundError(f"Could not load image: {path}")
    return pixmap


def find_asset_dir(*parts) -> Path:
    """Find an asset directory in a few convenient standalone layouts."""
    candidates = [
        BASE_DIR.joinpath(*parts),
        BASE_DIR / "assets" / Path(*parts),
        BASE_DIR / "feeding_standalone" / "assets" / Path(*parts),
    ]

    for candidate in candidates:
        if candidate.is_dir():
            return candidate

    raise FileNotFoundError(
        "Asset folder not found. Tried:\n"
        + "\n".join(str(p) for p in candidates)
    )


def crop_to_content(pixmap: QPixmap) -> QPixmap:
    """Crop transparent borders without treating black pixels as transparency."""
    if pixmap.isNull():
        return pixmap

    image = pixmap.toImage().convertToFormat(
        pixmap.toImage().Format_RGBA8888
    )

    w = image.width()
    h = image.height()

    left = w
    top = h
    right = -1
    bottom = -1

    for y in range(h):
        for x in range(w):
            if image.pixelColor(x, y).alpha() > 10:
                if x < left:
                    left = x
                if y < top:
                    top = y
                if x > right:
                    right = x
                if y > bottom:
                    bottom = y

    if right < 0:
        return QPixmap()

    return QPixmap.fromImage(
        image.copy(
            left,
            top,
            right - left + 1,
            bottom - top + 1,
        )
    )


def flip(pixmap: QPixmap) -> QPixmap:
    transform = QTransform()
    transform.scale(-1, 1)
    return pixmap.transformed(
        transform,
        Qt.FastTransformation,
    )


def fit_dog_frame(pixmap: QPixmap, size: int) -> QPixmap:
    pixmap = crop_to_content(pixmap)
    if pixmap.isNull():
        return pixmap

    return pixmap.scaled(
        size,
        size,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )


def load_walk_frames(dog_dir: Path):
    """IMPORTANT: paths are converted to QPixmap before processing."""
    frames = []

    paths = sorted(
        dog_dir.glob("walk_*.png"),
        key=lambda p: p.name.lower(),
    )

    if not paths:
        raise FileNotFoundError(
            f"No walk_*.png files found in:\n{dog_dir}"
        )

    for path in paths:
        pixmap = load_pixmap(path)       # FIX: Path -> QPixmap
        frame = fit_dog_frame(pixmap, DOG_SIZE)
        if frame.isNull():
            raise RuntimeError(f"Empty/transparent image: {path}")
        frames.append(frame)

    return frames


def load_eating_frames(eating_dir: Path):
    frames = []

    for i in range(1, EAT_FRAME_COUNT + 1):
        path = eating_dir / f"eat_{i:02d}.png"
        pixmap = load_pixmap(path)
        pixmap = fit_dog_frame(pixmap, EAT_DOG_SIZE)

        if pixmap.isNull():
            raise RuntimeError(f"Empty/transparent image: {path}")

        # Put the dog into the same 400x400 coordinate space as the normal dog.
        canvas = QPixmap(CANVAS_SIZE, CANVAS_SIZE)
        canvas.fill(Qt.transparent)

        painter = QPainter(canvas)
        x = (CANVAS_SIZE - pixmap.width()) // 2
        baseline = CANVAS_SIZE - 30
        y = baseline - pixmap.height()
        painter.drawPixmap(x, y, pixmap)
        painter.end()

        frames.append(canvas)

    return frames


# ============================================================
# APPLICATION
# ============================================================

app = QApplication(sys.argv)
screen = app.primaryScreen()
screen_rect = screen.availableGeometry()

# Normal dog window.
dog = OverlayLabel()
dog.resize(CANVAS_SIZE, CANVAS_SIZE)

# Separate chicken window.
chicken = OverlayLabel()
chicken.resize(DRUMSTICK_SIZE, DRUMSTICK_SIZE)

# HUD.
timer_label = QLabel()
timer_label.setWindowFlags(
    Qt.FramelessWindowHint
    | Qt.Tool
    | Qt.WindowStaysOnTopHint
)
timer_label.setAttribute(Qt.WA_TranslucentBackground, True)
timer_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
timer_label.setStyleSheet(
    "QLabel {"
    "background: rgba(20,20,25,210);"
    "color: white;"
    "padding: 7px 11px;"
    "border-radius: 8px;"
    "font-size: 15px;"
    "font-weight: bold;"
    "}"
)

freeze = FreezeOverlay(screen.geometry())


# ============================================================
# ASSETS
# ============================================================

dog_dir = find_asset_dir("dog")
eating_dir = find_asset_dir("eating")
food_dir = find_asset_dir("food")
food_path = food_dir / "chicken_drumstick.png"

walk_frames = load_walk_frames(dog_dir)
eat_frames = load_eating_frames(eating_dir)

drumstick = load_pixmap(food_path)
drumstick = drumstick.scaled(
    DRUMSTICK_SIZE,
    DRUMSTICK_SIZE,
    Qt.KeepAspectRatio,
    Qt.SmoothTransformation,
)


# ============================================================
# STATE
# ============================================================

dog_x = screen_rect.center().x() - CANVAS_SIZE / 2
dog_y = screen_rect.center().y() - CANVAS_SIZE / 2

facing = 1
walk_index = 0
walk_timer = 0.0

feeding = False
eat_index = 0
eat_timer = 0.0
feeding_end_time = 0.0

food_deadline = time.monotonic() + FEED_INTERVAL

rage_active = False
rage_end_time = 0.0


# ============================================================
# DISPLAY
# ============================================================

def center_of_dog():
    return (
        dog_x + CANVAS_SIZE / 2,
        dog_y + CANVAS_SIZE / 2,
    )


def show_normal_dog():
    frame = walk_frames[walk_index % len(walk_frames)]

    if facing < 0:
        frame = flip(frame)

    dog.setPixmap(frame)
    dog.resize(CANVAS_SIZE, CANVAS_SIZE)
    dog.move(round(dog_x), round(dog_y))
    dog.show()
    dog.raise_()


def update_walk():
    global walk_index
    global walk_timer

    walk_timer += 8 / FPS

    while walk_timer >= 1:
        walk_timer -= 1
        walk_index = (walk_index + 1) % len(walk_frames)


def update_hud():
    if rage_active:
        text = "DOG HUNGER RAGE!"
    elif feeding:
        text = "🍗 DOG IS EATING"
    else:
        remaining = max(
            0.0,
            food_deadline - time.monotonic(),
        )
        seconds = math.ceil(remaining)
        text = f"🍗 Feed dog: {seconds}s"

    timer_label.setText(text)
    timer_label.adjustSize()
    timer_label.move(
        screen_rect.left() + 20,
        screen_rect.top() + 20,
    )
    timer_label.show()
    timer_label.raise_()


def update_chicken_position():
    """Keep the separate chicken aligned near the dog's mouth."""
    cx, cy = center_of_dog()

    if facing > 0:
        # Dog faces right.
        x = cx + 42 - chicken.width() / 2
    else:
        # Dog faces left.
        x = cx - 42 - chicken.width() / 2

    # The dog sprites sit near the bottom of the 400x400 canvas.
    y = dog_y + 248

    chicken.move(round(x), round(y))


# ============================================================
# FEEDING
# ============================================================

def start_feeding():
    global feeding
    global eat_index
    global eat_timer
    global feeding_end_time
    global food_deadline

    if feeding or rage_active:
        return

    feeding = True
    eat_index = 0
    eat_timer = 0.0

    now = time.monotonic()
    feeding_end_time = now + EATING_DURATION
    food_deadline = now + FEED_INTERVAL

    chicken.setPixmap(drumstick)
    chicken.show()
    chicken.raise_()
    update_chicken_position()


def update_feeding():
    global feeding
    global eat_index
    global eat_timer

    if not feeding:
        return

    now = time.monotonic()

    # Advance the 10-frame eating animation smoothly.
    eat_timer += EAT_FPS / FPS

    while eat_timer >= 1:
        eat_timer -= 1
        eat_index += 1
        if eat_index >= EAT_FRAME_COUNT:
            eat_index = EAT_FRAME_COUNT - 1
            break

    frame = eat_frames[eat_index]

    if facing < 0:
        frame = flip(frame)

    dog.setPixmap(frame)
    dog.resize(CANVAS_SIZE, CANVAS_SIZE)
    dog.move(round(dog_x), round(dog_y))
    dog.show()
    dog.raise_()

    # Keep the external chicken visible throughout the eating animation.
    update_chicken_position()
    chicken.show()
    chicken.raise_()

    if now >= feeding_end_time:
        feeding = False
        chicken.hide()
        show_normal_dog()


# ============================================================
# HUNGER RAGE
# ============================================================

def start_rage():
    global rage_active
    global rage_end_time
    global food_deadline
    global feeding

    if rage_active:
        return

    rage_active = True
    rage_end_time = time.monotonic() + RAGE_DURATION
    food_deadline = time.monotonic() + FEED_INTERVAL
    feeding = False

    chicken.hide()
    dog.hide()

    freeze.show()
    freeze.raise_()


def update_rage():
    global rage_active

    if not rage_active:
        return

    freeze.raise_()

    if time.monotonic() >= rage_end_time:
        rage_active = False
        freeze.hide()
        show_normal_dog()


# ============================================================
# GLOBAL KEYBOARD
# ============================================================

def key_press(key):
    global facing

    try:
        char = key.char
        if char is None:
            return
        char = char.lower()
    except AttributeError:
        return

    if char == "f":
        start_feeding()
    elif char == "a":
        facing = -1
        if not feeding and not rage_active:
            show_normal_dog()
    elif char == "d":
        facing = 1
        if not feeding and not rage_active:
            show_normal_dog()


try:
    from pynput import keyboard

    key_listener = keyboard.Listener(
        on_press=key_press
    )
    key_listener.start()
except Exception as exc:
    print("Keyboard hook unavailable:", exc)
    key_listener = None


# ============================================================
# MAIN LOOP
# ============================================================

def update():
    global food_deadline

    if rage_active:
        update_rage()
        update_hud()
        return

    if feeding:
        update_feeding()
    else:
        update_walk()
        show_normal_dog()

        if time.monotonic() >= food_deadline:
            start_rage()

    update_hud()


# ============================================================
# START
# ============================================================

show_normal_dog()
update_hud()

main_timer = QTimer()
main_timer.timeout.connect(update)
main_timer.start(round(1000 / FPS))

print()
print("========================================")
print("      VIRTUAL DOG - FEEDING TEST")
print("========================================")
print("F -> Feed dog")
print("A -> Face left (testing)")
print("D -> Face right (testing)")
print(f"Feed timer -> {FEED_INTERVAL:.0f} seconds")
print(f"Eating animation -> {EAT_FRAME_COUNT} frames")
print(f"Hunger rage -> {RAGE_DURATION:.0f} seconds")
print("========================================")
print()


# ============================================================
# CLEAN EXIT
# ============================================================

try:
    sys.exit(app.exec())
finally:
    if key_listener is not None:
        key_listener.stop()

    chicken.hide()
    dog.hide()
    timer_label.hide()
    freeze.hide()
