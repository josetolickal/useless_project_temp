import os
import sys
import time
import math
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QPixmap, QTransform, QPainter, QFont
from PySide6.QtWidgets import QApplication, QLabel, QWidget


FPS = 60
CANVAS_SIZE = 400
DOG_SIZE = 78
EAT_DOG_SIZE = 95
EAT_FRAME_COUNT = 10
EAT_FPS = 10
FEED_INTERVAL = 30.0
EATING_DURATION = 1.15
DRUMSTICK_SIZE = 72

BASE_DIR = Path(__file__).resolve().parent


class OverlayLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background: transparent;")


class FreezeOverlay(QWidget):
    def __init__(self, screen_geometry):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setGeometry(screen_geometry)
        self.message = "DOG HUNGER RAGE!"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        painter.setPen(Qt.white)
        font = QFont()
        font.setPointSize(28)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self.message)
        painter.end()


def load_pixmaps(folder: Path, prefix: str, count: int):
    frames = []
    for i in range(1, count + 1):
        path = folder / f"{prefix}{i:02d}.png"
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            raise FileNotFoundError(f"Missing asset: {path}")
        frames.append(pixmap)
    return frames


def crop_to_content(pixmap: QPixmap):
    image = pixmap.toImage().convertToFormat(pixmap.toImage().Format_RGBA8888)
    w, h = image.width(), image.height()
    left, top, right, bottom = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            if image.pixelColor(x, y).alpha() > 10:
                left = min(left, x)
                right = max(right, x)
                top = min(top, y)
                bottom = max(bottom, y)
    if right < 0:
        return QPixmap()
    return QPixmap.fromImage(image.copy(left, top, right - left + 1, bottom - top + 1))


def flip(pixmap: QPixmap):
    transform = QTransform()
    transform.scale(-1, 1)
    return pixmap.transformed(transform, Qt.FastTransformation)


def fit_dog_frame(pixmap: QPixmap):
    pixmap = crop_to_content(pixmap)
    return pixmap.scaled(DOG_SIZE, DOG_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def prepare_eat_frame(pixmap: QPixmap):
    pixmap = crop_to_content(pixmap)
    pixmap = pixmap.scaled(EAT_DOG_SIZE, EAT_DOG_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    canvas = QPixmap(CANVAS_SIZE, CANVAS_SIZE)
    canvas.fill(Qt.transparent)
    painter = QPainter(canvas)
    x = (CANVAS_SIZE - pixmap.width()) // 2
    baseline = CANVAS_SIZE - 30
    y = baseline - pixmap.height()
    painter.drawPixmap(x, y, pixmap)
    painter.end()
    return canvas


app = QApplication(sys.argv)
screen = app.primaryScreen()
screen_rect = screen.availableGeometry()

# Main dog window.
dog = OverlayLabel()
dog.resize(CANVAS_SIZE, CANVAS_SIZE)

# Separate food window. This avoids baking the chicken into the dog animation.
chicken = OverlayLabel()
chicken.resize(DRUMSTICK_SIZE, DRUMSTICK_SIZE)

# HUD.
timer_label = QLabel()
timer_label.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
timer_label.setAttribute(Qt.WA_TranslucentBackground, True)
timer_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
timer_label.setStyleSheet(
    "QLabel { background: rgba(20,20,25,210); color: white; "
    "padding: 7px 11px; border-radius: 8px; font-size: 15px; font-weight: bold; }"
)

# Freeze overlay used only when the feeding timer expires.
freeze = FreezeOverlay(screen.geometry())

# Assets.
dog_dir = BASE_DIR / "assets" / "dog"
eating_dir = BASE_DIR / "assets" / "eating"
food_path = BASE_DIR / "assets" / "food" / "chicken_drumstick.png"

walk_frames = [fit_dog_frame(p) for p in sorted(dog_dir.glob("walk_*.png"), key=lambda p: p.name)]
if not walk_frames:
    raise FileNotFoundError(f"No clean dog walk frames found in {dog_dir}")

eat_frames = load_pixmaps(eating_dir, "eat_", EAT_FRAME_COUNT)
eat_frames = [prepare_eat_frame(p) for p in eat_frames]

drumstick = QPixmap(str(food_path))
if drumstick.isNull():
    raise FileNotFoundError(f"Missing asset: {food_path}")
drumstick = drumstick.scaled(DRUMSTICK_SIZE, DRUMSTICK_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)

# State.
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


def center_of_dog():
    return dog_x + CANVAS_SIZE / 2, dog_y + CANVAS_SIZE / 2


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
    global walk_index, walk_timer
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
        seconds = max(0, math.ceil(food_deadline - time.monotonic()))
        text = f"🍗 Feed dog: {seconds}s"
    timer_label.setText(text)
    timer_label.adjustSize()
    timer_label.move(screen_rect.left() + 20, screen_rect.top() + 20)
    timer_label.show()
    timer_label.raise_()


def update_chicken_position():
    cx, cy = center_of_dog()
    # These offsets place the separately rendered drumstick near the mouth.
    side = 1 if facing > 0 else -1
    x = cx + side * 56 - chicken.width() / 2
    y = dog_y + 260
    chicken.move(round(x), round(y))


def start_feeding():
    global feeding, eat_index, eat_timer, feeding_end_time, food_deadline
    if feeding or rage_active:
        return
    feeding = True
    eat_index = 0
    eat_timer = 0.0
    feeding_end_time = time.monotonic() + EATING_DURATION
    food_deadline = time.monotonic() + FEED_INTERVAL
    chicken.show()
    chicken.raise_()
    update_chicken_position()


def update_feeding():
    global feeding, eat_index, eat_timer
    if not feeding:
        return

    update_chicken_position()
    eat_timer += EAT_FPS / FPS
    while eat_timer >= 1:
        eat_timer -= 1
        eat_index += 1
        if eat_index >= EAT_FRAME_COUNT:
            eat_index = EAT_FRAME_COUNT - 1
            break

    # Dog-only bite frames. The separate drumstick stays visually independent.
    frame = eat_frames[eat_index]
    if facing < 0:
        frame = flip(frame)
    dog.setPixmap(frame)
    dog.resize(CANVAS_SIZE, CANVAS_SIZE)
    dog.move(round(dog_x), round(dog_y))
    dog.show()
    dog.raise_()

    if time.monotonic() >= feeding_end_time:
        feeding = False
        chicken.hide()
        show_normal_dog()


def start_rage():
    global rage_active, rage_end_time, food_deadline, feeding
    if rage_active:
        return
    rage_active = True
    rage_end_time = time.monotonic() + 4.0
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


def key_press(key):
    global facing
    try:
        char = key.char.lower()
    except AttributeError:
        return
    if char == "f":
        start_feeding()
    elif char == "a":
        facing = -1
    elif char == "d":
        facing = 1


# Use pynput so F works even when another desktop window has focus.
try:
    from pynput import keyboard
    key_listener = keyboard.Listener(on_press=key_press)
    key_listener.start()
except Exception as exc:
    print("Keyboard hook unavailable:", exc)
    key_listener = None


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


# Initial state.
show_normal_dog()
update_hud()

timer = QTimer()
timer.timeout.connect(update)
timer.start(round(1000 / FPS))

print("========================================")
print("   VIRTUAL DOG - FEEDING STANDALONE")
print("========================================")
print("F -> feed dog with chicken")
print("A -> face left (testing)")
print("D -> face right (testing)")
print(f"Feed timer -> {FEED_INTERVAL:.0f} seconds")
print("Timer expiry -> 4-second hunger rage freeze")
print("Ctrl+C in the console to stop")
print("========================================")

try:
    sys.exit(app.exec())
finally:
    if key_listener is not None:
        key_listener.stop()
    chicken.hide()
    dog.hide()
    timer_label.hide()
    freeze.hide()
