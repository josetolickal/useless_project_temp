import sys
import os
import math
import time
import random
import ctypes
from ctypes import wintypes
from collections import deque

from PySide6.QtWidgets import QApplication, QLabel, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QTransform, QPainter, QCursor, QImage, QColor, QPen, QBrush

from pynput import keyboard, mouse


# ============================================================
# SINGLE INSTANCE (WINDOWS)
# ============================================================
# Prevent two copies of the virtual dog from running at once.
# This avoids an older copy remaining visible on the desktop.

_instance_mutex = None

if sys.platform == "win32":

    _kernel32 = ctypes.windll.kernel32

    _instance_mutex = _kernel32.CreateMutexW(
        None,
        False,
        "VirtualDog_SingleInstance_2026"
    )

    if _kernel32.GetLastError() == 183:

        print("Virtual Dog is already running.")
        sys.exit(0)


# ============================================================
# APPLICATION
# ============================================================

app = QApplication(sys.argv)

FPS = 60

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# WINDOW
# ============================================================

CANVAS_SIZE = 400

dog = QLabel()

# Separate transparent window for the tornado animation.
# The tornado PNGs already contain the dog, so this window shows
# ONLY the tornado PNG. The normal dog window is hidden during it.
tornado_dog = QLabel()

tornado_dog.setWindowFlags(
    Qt.FramelessWindowHint
    | Qt.WindowStaysOnTopHint
    | Qt.Tool
)

tornado_dog.setAttribute(
    Qt.WA_TranslucentBackground,
    True
)

tornado_dog.setAttribute(
    Qt.WA_TransparentForMouseEvents,
    True
)

tornado_dog.setStyleSheet(
    "background: transparent;"
)

tornado_dog.hide()

# Separate transparent window for the 10-frame cleaning animation.
# The cleaning PNG already contains the shower and the dog.
cleaning_dog = QLabel()

cleaning_dog.setWindowFlags(
    Qt.FramelessWindowHint
    | Qt.WindowStaysOnTopHint
    | Qt.Tool
)

cleaning_dog.setAttribute(
    Qt.WA_TranslucentBackground,
    True
)

cleaning_dog.setAttribute(
    Qt.WA_TransparentForMouseEvents,
    True
)

cleaning_dog.setStyleSheet(
    "background: transparent;"
)

cleaning_dog.hide()


dog.setWindowFlags(
    Qt.FramelessWindowHint
    | Qt.WindowStaysOnTopHint
    | Qt.Tool
)

dog.setAttribute(
    Qt.WA_TranslucentBackground,
    True
)

dog.setAttribute(
    Qt.WA_TransparentForMouseEvents,
    True
)

dog.setStyleSheet(
    "background: transparent;"
)

dog.resize(
    CANVAS_SIZE,
    CANVAS_SIZE
)


# ============================================================
# NORMAL DOG SETTINGS
# ============================================================

WALK_SIZE = 70
RUN_SIZE = 80
SLEEP_SIZE = 75

MAX_RUN_SPEED = 5.0
MAX_WALK_SPEED = 2.5
MIN_CLOSE_SPEED = 0.7

RUN_DISTANCE = 350
SLOW_DISTANCE = 150
CATCH_DISTANCE = 35


# ============================================================
# ANIMATION SPEED
# ============================================================

WALK_FPS = 8
RUN_FPS = 10
SLEEP_FPS = 5

SSJ_FPS = 8
TORNADO_FPS = 12


# ============================================================
# SLEEP
# ============================================================

SIT_TIME = 3.0


# ============================================================
# SUPER SAIYAN
# ============================================================

SSJ_START_SCALE = 1.0

SSJ_MAX_SCALE = 1.55

SSJ_GROWTH_SPEED = 0.012

SSJ_PADDING = 80


# ============================================================
# SCREEN SHAKE
# ============================================================

SHAKE_AMOUNT = 6
SHAKE_SPEED = 2


# ============================================================
# TORNADO
# ============================================================

TORNADO_FRAME_COUNT = 10

TORNADO_SIZE = 170

TORNADO_PADDING = 55

# Tornado runs for this many seconds.
TORNADO_DURATION = 5.0

# Autonomous circular movement radius.
TORNADO_MOTION_RADIUS = 200

# Angular movement per timer frame.
TORNADO_ANGULAR_SPEED = 0.055


# ============================================================
# MUD MODE
# ============================================================

# M = enter mud mode and play the roll animation.
# C = return to the clean dog.
MUD_ROLL_FRAME_COUNT = 10
MUD_WALK_FRAME_COUNT = 10
MUD_RUN_FRAME_COUNT = 10

MUD_ROLL_FPS = 12
MUD_WALK_FPS = 8
MUD_RUN_FPS = 11

# Distance travelled before another muddy footprint is placed.
FOOTPRINT_DISTANCE = 30.0

# Safety cap for footprint count.
MAX_FOOTPRINTS = 300


# ============================================================
# CLEANING ANIMATION
# ============================================================

CLEANING_FRAME_COUNT = 10
CLEANING_FPS = 10

# The generated cleaning artwork contains a larger dog than the
# normal in-game dog. Scale the COMPLETE cleaning frame so the
# dog matches the normal dog size.
# 0.42 makes the cleaning dog approximately the same size as
# the normal 70-75 px dog.
CLEANING_SCALE = 0.42

# Position of the dog's feet inside the generated cleaning frame.
# CLEANING_FRAME_DOG_BASELINE_Y is scaled together with the frame.
CLEANING_DOG_BASELINE_Y = 370
CLEANING_FRAME_DOG_BASELINE_Y = round(470 * CLEANING_SCALE)


# ============================================================
# CIRCLE DETECTION
# ============================================================

CIRCLE_HISTORY_LENGTH = 80

TORNADO_MIN_RADIUS = 55

TORNADO_MAX_RADIUS = 700

TORNADO_REQUIRED_ANGLE = math.radians(270)

TORNADO_DIRECTION_THRESHOLD = 0.62

TORNADO_MIN_SPEED = 80.0


# ============================================================
# SCREEN
# ============================================================

screen = QApplication.primaryScreen()

screen_rect = screen.availableGeometry()


# ============================================================
# MUD FOOTPRINT OVERLAY
# ============================================================

class FootprintOverlay(QWidget):

    def __init__(self):

        super().__init__()

        self.footprints = []

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
        )

        self.setAttribute(
            Qt.WA_TranslucentBackground,
            True
        )

        self.setAttribute(
            Qt.WA_TransparentForMouseEvents,
            True
        )

        self.setStyleSheet(
            "background: transparent;"
        )

        self.setGeometry(
            screen_rect
        )

        self.hide()

    def clear_footprints(self):

        self.footprints.clear()

        self.update()

    def add_footprint(self, x, y, side):

        self.footprints.append(
            (
                float(x),
                float(y),
                int(side)
            )
        )

        if len(self.footprints) > MAX_FOOTPRINTS:

            del self.footprints[0]

        self.update()

    def paintEvent(self, event):

        if not self.footprints:
            return

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        painter.setBrush(
            QBrush(
                QColor(72, 43, 27, 175)
            )
        )

        painter.setPen(
            QPen(Qt.NoPen)
        )

        ox = screen_rect.left()
        oy = screen_rect.top()

        for x, y, side in self.footprints:

            px = x - ox + side * 6
            py = y - oy

            # Main paw pad.
            painter.drawEllipse(
                int(px - 4),
                int(py - 2),
                8,
                7
            )

            # Three toe pads.
            painter.drawEllipse(
                int(px - 7),
                int(py - 7),
                4,
                4
            )

            painter.drawEllipse(
                int(px - 2),
                int(py - 9),
                4,
                4
            )

            painter.drawEllipse(
                int(px + 3),
                int(py - 7),
                4,
                4
            )

        painter.end()


footprints_overlay = FootprintOverlay()


# ============================================================
# IMAGE LOADER
# ============================================================

def load_image(filename):

    candidates = [
        os.path.join(BASE_DIR, filename),
        os.path.join(BASE_DIR, "assets", filename),
        os.path.join(BASE_DIR, "assets", "mud", filename),
    ]

    path = None

    for candidate in candidates:

        if os.path.exists(candidate):

            path = candidate
            break

    if path is None:

        print()
        print("========================================")
        print("MISSING IMAGE")
        print("========================================")
        print(filename)
        print("Searched:")

        for candidate in candidates:
            print(candidate)

        print()

        sys.exit(1)

    img = QPixmap(path)

    if img.isNull():

        print("FAILED TO LOAD:")
        print(path)

        sys.exit(1)

    return img


# ============================================================
# TRANSPARENT CROP
# ============================================================

def crop_transparent(img):

    if img.isNull():
        return img

    image = img.toImage()

    image = image.convertToFormat(
        QImage.Format.Format_ARGB32
    )

    width = image.width()
    height = image.height()

    left = width
    right = -1
    top = height
    bottom = -1

    for y in range(height):

        for x in range(width):

            alpha = image.pixelColor(
                x,
                y
            ).alpha()

            if alpha > 10:

                if x < left:
                    left = x

                if x > right:
                    right = x

                if y < top:
                    top = y

                if y > bottom:
                    bottom = y

    if right == -1:
        return QPixmap()

    cropped = image.copy(
        left,
        top,
        right - left + 1,
        bottom - top + 1
    )

    return QPixmap.fromImage(
        cropped
    )


# ============================================================
# ADD TRANSPARENT PADDING
# ============================================================

def add_padding(img, padding):

    if img.isNull():
        return img

    canvas = QPixmap(
        img.width() + padding * 2,
        img.height() + padding * 2
    )

    canvas.fill(
        Qt.transparent
    )

    painter = QPainter(canvas)

    painter.drawPixmap(
        padding,
        padding,
        img
    )

    painter.end()

    return canvas


# ============================================================
# NORMAL FRAME PREPARATION
# ============================================================

def prepare_frame(img, size):

    img = img.scaled(
        size,
        size,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation
    )

    canvas = QPixmap(
        CANVAS_SIZE,
        CANVAS_SIZE
    )

    canvas.fill(
        Qt.transparent
    )

    painter = QPainter(canvas)

    x = (
        CANVAS_SIZE
        - img.width()
    ) // 2

    baseline = CANVAS_SIZE - 30

    y = baseline - img.height()

    painter.drawPixmap(
        x,
        y,
        img
    )

    painter.end()

    return canvas


# ============================================================
# LOAD NORMAL 8-FRAME ANIMATION
# ============================================================

def load_animation(prefix, size):

    frames = []

    for i in range(1, 9):

        filename = (
            f"{prefix}{i:02d}.png"
        )

        print(
            "Loading:",
            filename
        )

        img = load_image(
            filename
        )

        frame = prepare_frame(
            img,
            size
        )

        frames.append(
            frame
        )

    return frames


# ============================================================
# LOAD RUN
# ============================================================

def load_run_animation():

    frames = []

    for i in range(1, 9):

        filename = (
            f"run_{i}.png"
        )

        print(
            "Loading:",
            filename
        )

        img = load_image(
            filename
        )

        frame = prepare_frame(
            img,
            RUN_SIZE
        )

        frames.append(
            frame
        )

    return frames


# ============================================================
# LOAD SSJ
# ============================================================

def load_ssj_animation():

    frames = []

    for i in range(1, 9):

        filename = (
            f"ssj_{i:02d}.png"
        )

        print(
            "Loading:",
            filename
        )

        img = load_image(
            filename
        )

        img = crop_transparent(
            img
        )

        img = add_padding(
            img,
            SSJ_PADDING
        )

        frames.append(
            img
        )

    return frames


# ============================================================
# LOAD TORNADO
# ============================================================

def load_tornado_animation():

    frames = []

    for i in range(
        1,
        TORNADO_FRAME_COUNT + 1
    ):

        filename = (
            f"tornado_{i:02d}.png"
        )

        print(
            "Loading:",
            filename
        )

        img = load_image(
            filename
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Each tornado PNG already contains the dog.
        # We only prepare the image itself.
        # ----------------------------------------------------

        img = crop_transparent(
            img
        )

        img = add_padding(
            img,
            TORNADO_PADDING
        )

        img = img.scaled(
            TORNADO_SIZE,
            TORNADO_SIZE,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        frames.append(
            img
        )

    return frames


# ============================================================
# LOAD MUD ANIMATIONS
# ============================================================

def load_mud_animation(prefix, count, size):

    frames = []

    for i in range(1, count + 1):

        filename = f"{prefix}{i:02d}.png"

        print(
            "Loading:",
            filename
        )

        img = load_image(
            filename
        )

        frames.append(
            prepare_frame(
                img,
                size
            )
        )

    return frames


# ============================================================
# LOAD ALL ANIMATIONS
# ============================================================

walk_frames = load_animation(
    "walk_",
    WALK_SIZE
)

run_frames = load_run_animation()

sleep_frames = load_animation(
    "sleep_",
    SLEEP_SIZE
)

ssj_frames = load_ssj_animation()

tornado_frames = load_tornado_animation()

mud_roll_frames = load_mud_animation(
    "mud_roll_",
    MUD_ROLL_FRAME_COUNT,
    WALK_SIZE
)

mud_walk_frames = load_mud_animation(
    "mud_walk_",
    MUD_WALK_FRAME_COUNT,
    WALK_SIZE
)

mud_run_frames = load_mud_animation(
    "mud_run_",
    MUD_RUN_FRAME_COUNT,
    RUN_SIZE
)


# ============================================================
# LOAD CLEANING ANIMATION
# ============================================================

def load_cleaning_animation():

    frames = []

    for i in range(1, CLEANING_FRAME_COUNT + 1):

        filename = f"cleaning_{i:02d}.png"

        print(
            "Loading:",
            filename
        )

        img = load_image(
            filename
        )

        # Keep the complete frame so the shower remains intact,
        # but scale the entire animation to match the normal dog size.
        scaled_width = max(1, round(img.width() * CLEANING_SCALE))
        scaled_height = max(1, round(img.height() * CLEANING_SCALE))

        img = img.scaled(
            scaled_width,
            scaled_height,
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation
        )

        frames.append(img)

    return frames


cleaning_frames = load_cleaning_animation()


# ============================================================
# POSITION
# ============================================================

dog_x = (
    screen_rect.center().x()
    - CANVAS_SIZE / 2
)

dog_y = (
    screen_rect.center().y()
    - CANVAS_SIZE / 2
)


# ============================================================
# STATE
# ============================================================

state = "idle"

facing = 1


# ============================================================
# ANIMATION INDICES
# ============================================================

walk_index = 0
run_index = 0
sleep_index = 0

ssj_index = 0
tornado_index = 0


# ============================================================
# ANIMATION TIMERS
# ============================================================

walk_timer = 0.0
run_timer = 0.0
sleep_timer = 0.0

ssj_timer = 0.0
tornado_timer = 0.0


# ============================================================
# SITTING
# ============================================================

sit_start = None


# ============================================================
# SSJ STATE
# ============================================================

ssj_active = False

ssj_scale = SSJ_START_SCALE

right_button_down = False


# ============================================================
# TORNADO STATE
# ============================================================

tornado_active = False

tornado_start_time = 0.0

tornado_angle = 0.0

tornado_origin_x = 0.0
tornado_origin_y = 0.0

tornado_direction = 1

tornado_motion_radius = (
    TORNADO_MOTION_RADIUS
)


# ============================================================
# MUD STATE
# ============================================================

muddy_active = False
mud_roll_playing = False

mud_roll_index = 0
mud_roll_timer = 0.0

mud_walk_index = 0
mud_walk_timer = 0.0

mud_run_index = 0
mud_run_timer = 0.0

mud_command = None

last_footprint_x = None
last_footprint_y = None
footprint_side = -1


# ============================================================
# CLEANING STATE
# ============================================================

cleaning_active = False
cleaning_index = 0
cleaning_timer = 0.0


# ============================================================
# KILL SWITCH
# ============================================================

kill_requested = False


# ============================================================
# CURSOR HISTORY
# ============================================================

cursor_history = deque(
    maxlen=CIRCLE_HISTORY_LENGTH
)

last_cursor_x = None
last_cursor_y = None
last_cursor_time = None


# ============================================================
# SCREEN SHAKE
# ============================================================

shake_active = False

shake_window = None

shake_original_x = 0
shake_original_y = 0

shake_timer = 0


# ============================================================
# KEYBOARD
# ============================================================

def kill_dog():

    global kill_requested

    kill_requested = True


keyboard_listener = keyboard.GlobalHotKeys({

    "<ctrl>+<shift>+q": kill_dog

})

keyboard_listener.start()


def mud_key_handler(key):

    global mud_command

    try:
        char = key.char
    except AttributeError:
        return

    if not char:
        return

    char = char.lower()

    if char == "m":
        mud_command = "mud"

    elif char == "c":
        mud_command = "clean"


mud_keyboard_listener = keyboard.Listener(
    on_press=mud_key_handler
)

mud_keyboard_listener.start()


# ============================================================
# MOUSE
# ============================================================

def mouse_callback(
    x,
    y,
    button,
    pressed
):

    global right_button_down

    if button == mouse.Button.right:

        right_button_down = pressed


mouse_listener = mouse.Listener(
    on_click=mouse_callback
)

mouse_listener.start()


# ============================================================
# CURSOR
# ============================================================

def get_cursor():

    pos = QCursor.pos()

    return (
        pos.x(),
        pos.y()
    )


# ============================================================
# CURSOR OVER DOG
# ============================================================

def cursor_over_dog():

    mouse_x, mouse_y = get_cursor()

    margin = 35

    return (

        dog_x - margin
        <= mouse_x
        <= dog_x
        + CANVAS_SIZE
        + margin

        and

        dog_y - margin
        <= mouse_y
        <= dog_y
        + CANVAS_SIZE
        + margin

    )


# ============================================================
# FLIP
# ============================================================

def flip(frame):

    transform = QTransform()

    transform.scale(
        -1,
        1
    )

    return frame.transformed(
        transform,
        Qt.FastTransformation
    )


# ============================================================
# WALK FRAME
# ============================================================

def get_walk():

    frame = walk_frames[
        walk_index
    ]

    if facing == -1:

        return flip(frame)

    return frame


# ============================================================
# RUN FRAME
# ============================================================

def get_run():

    frame = run_frames[
        run_index
    ]

    if facing == -1:

        return flip(frame)

    return frame


# ============================================================
# SLEEP FRAME
# ============================================================

def get_sleep():

    frame = sleep_frames[
        sleep_index
    ]

    if facing == -1:

        return flip(frame)

    return frame


# ============================================================
# SSJ FRAME
# ============================================================

def get_ssj():

    frame = ssj_frames[
        ssj_index
    ]

    if facing == -1:

        frame = flip(frame)

    width = int(
        frame.width()
        * ssj_scale
    )

    height = int(
        frame.height()
        * ssj_scale
    )

    frame = frame.scaled(
        width,
        height,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation
    )

    canvas_width = max(
        CANVAS_SIZE,
        frame.width() + 40
    )

    canvas_height = max(
        CANVAS_SIZE,
        frame.height() + 40
    )

    canvas = QPixmap(
        canvas_width,
        canvas_height
    )

    canvas.fill(
        Qt.transparent
    )

    painter = QPainter(canvas)

    x = (
        canvas_width
        - frame.width()
    ) // 2

    y = (
        canvas_height
        - frame.height()
        - 20
    )

    painter.drawPixmap(
        x,
        y,
        frame
    )

    painter.end()

    return canvas


# ============================================================
# SCREEN SHAKE START
# ============================================================

def start_screen_shake():

    global shake_active
    global shake_window
    global shake_original_x
    global shake_original_y
    global shake_timer

    if shake_active:
        return

    if sys.platform != "win32":
        return

    hwnd = (
        ctypes.windll.user32.GetForegroundWindow()
    )

    dog_hwnd = int(
        dog.winId()
    )

    if hwnd == 0:
        return

    if hwnd == dog_hwnd:
        return

    rect = wintypes.RECT()

    success = (
        ctypes.windll.user32.GetWindowRect(
            hwnd,
            ctypes.byref(rect)
        )
    )

    if not success:
        return

    shake_window = hwnd

    shake_original_x = rect.left
    shake_original_y = rect.top

    shake_timer = 0

    shake_active = True


# ============================================================
# SCREEN SHAKE UPDATE
# ============================================================

def update_screen_shake():

    global shake_timer

    if not shake_active:
        return

    if shake_window is None:
        return

    shake_timer += 1

    if (
        shake_timer
        % SHAKE_SPEED
        != 0
    ):

        return

    offset_x = random.randint(
        -SHAKE_AMOUNT,
        SHAKE_AMOUNT
    )

    offset_y = random.randint(
        -SHAKE_AMOUNT,
        SHAKE_AMOUNT
    )

    ctypes.windll.user32.SetWindowPos(

        shake_window,

        0,

        shake_original_x
        + offset_x,

        shake_original_y
        + offset_y,

        0,
        0,

        0x0001 | 0x0004
    )


# ============================================================
# SCREEN SHAKE STOP
# ============================================================

def stop_screen_shake():

    global shake_active
    global shake_window
    global shake_timer

    if not shake_active:
        return

    if (
        shake_window is not None
        and sys.platform == "win32"
    ):

        ctypes.windll.user32.SetWindowPos(

            shake_window,

            0,

            shake_original_x,
            shake_original_y,

            0,
            0,

            0x0001 | 0x0004
        )

    shake_active = False

    shake_window = None

    shake_timer = 0


# ============================================================
# START SSJ
# ============================================================

def start_ssj():

    global ssj_active
    global ssj_index
    global ssj_timer
    global ssj_scale
    global state

    if ssj_active:
        return

    if tornado_active:

        stop_tornado()

    tornado_dog.hide()

    ssj_active = True

    footprints_overlay.hide()

    ssj_index = 0

    ssj_timer = 0

    ssj_scale = SSJ_START_SCALE

    state = "ssj"

    dog.show()

    dog.raise_()

    start_screen_shake()


# ============================================================
# STOP SSJ
# ============================================================

def stop_ssj():

    global ssj_active
    global ssj_index
    global ssj_timer
    global ssj_scale
    global state

    if not ssj_active:
        return

    ssj_active = False

    ssj_index = 0

    ssj_timer = 0

    ssj_scale = SSJ_START_SCALE

    state = "mud" if muddy_active else "idle"

    stop_screen_shake()

    if muddy_active:

        footprints_overlay.show()
        footprints_overlay.raise_()


# ============================================================
# SSJ UPDATE
# ============================================================

def update_ssj():

    global ssj_index
    global ssj_timer
    global ssj_scale

    ssj_timer += (
        SSJ_FPS / FPS
    )

    while ssj_timer >= 1:

        ssj_timer -= 1

        if ssj_index < 7:

            ssj_index += 1

        else:

            # Frames 7 and 8 loop.
            ssj_index = 6

    if ssj_scale < SSJ_MAX_SCALE:

        ssj_scale = min(
            SSJ_MAX_SCALE,
            ssj_scale
            + SSJ_GROWTH_SPEED
        )


# ============================================================
# SSJ INPUT
# ============================================================

def check_ssj_input():

    if right_button_down:

        if cursor_over_dog():

            if not ssj_active:

                start_ssj()

            return

    if ssj_active:

        stop_ssj()


# ============================================================
# CURSOR HISTORY
# ============================================================

def update_cursor_history():

    global last_cursor_x
    global last_cursor_y
    global last_cursor_time

    x, y = get_cursor()

    now = time.monotonic()

    if last_cursor_x is None:

        last_cursor_x = x
        last_cursor_y = y
        last_cursor_time = now

        cursor_history.clear()

        cursor_history.append(
            (
                x,
                y,
                now
            )
        )

        return

    distance = math.hypot(

        x - last_cursor_x,

        y - last_cursor_y

    )

    if distance >= 2:

        cursor_history.append(
            (
                x,
                y,
                now
            )
        )

        last_cursor_x = x
        last_cursor_y = y
        last_cursor_time = now


# ============================================================
# CIRCLE DETECTION
# ============================================================

def detect_circular_motion():

    if len(cursor_history) < 18:

        return None

    points = list(
        cursor_history
    )

    # --------------------------------------------------------
    # Center
    # --------------------------------------------------------

    center_x = sum(
        p[0]
        for p in points
    ) / len(points)

    center_y = sum(
        p[1]
        for p in points
    ) / len(points)

    # --------------------------------------------------------
    # Radius
    # --------------------------------------------------------

    radii = []

    for x, y, t in points:

        radii.append(
            math.hypot(
                x - center_x,
                y - center_y
            )
        )

    average_radius = (
        sum(radii)
        / len(radii)
    )

    if (
        average_radius
        < TORNADO_MIN_RADIUS
    ):

        return None

    if (
        average_radius
        > TORNADO_MAX_RADIUS
    ):

        return None

    # --------------------------------------------------------
    # Radius consistency
    # --------------------------------------------------------

    deviation = sum(
        abs(
            r - average_radius
        )
        for r in radii
    ) / len(radii)

    normalized_deviation = (
        deviation
        / average_radius
    )

    if (
        normalized_deviation
        > 0.45
    ):

        return None

    # --------------------------------------------------------
    # Angles
    # --------------------------------------------------------

    angles = []

    for x, y, t in points:

        angles.append(
            math.atan2(
                y - center_y,
                x - center_x
            )
        )

    # --------------------------------------------------------
    # Unwrap angles
    # --------------------------------------------------------

    unwrapped = [
        angles[0]
    ]

    for angle in angles[1:]:

        previous = unwrapped[-1]

        while (
            angle - previous
            > math.pi
        ):

            angle -= math.tau

        while (
            angle - previous
            < -math.pi
        ):

            angle += math.tau

        unwrapped.append(
            angle
        )

    # --------------------------------------------------------
    # Angular deltas
    # --------------------------------------------------------

    deltas = []

    for i in range(
        1,
        len(unwrapped)
    ):

        delta = (
            unwrapped[i]
            - unwrapped[i - 1]
        )

        if abs(delta) > 0.015:

            deltas.append(
                delta
            )

    if len(deltas) < 10:

        return None

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    positive = sum(
        1
        for d in deltas
        if d > 0
    )

    negative = sum(
        1
        for d in deltas
        if d < 0
    )

    if positive > negative:

        direction = 1

        consistency = (
            positive
            / len(deltas)
        )

    else:

        direction = -1

        consistency = (
            negative
            / len(deltas)
        )

    if (
        consistency
        < TORNADO_DIRECTION_THRESHOLD
    ):

        return None

    # --------------------------------------------------------
    # Total rotation
    # --------------------------------------------------------

    total_angle = abs(
        unwrapped[-1]
        - unwrapped[0]
    )

    if (
        total_angle
        < TORNADO_REQUIRED_ANGLE
    ):

        return None

    # --------------------------------------------------------
    # Speed
    # --------------------------------------------------------

    elapsed = (
        points[-1][2]
        - points[0][2]
    )

    if elapsed <= 0:

        return None

    total_distance = 0

    for i in range(
        1,
        len(points)
    ):

        total_distance += math.hypot(

            points[i][0]
            - points[i - 1][0],

            points[i][1]
            - points[i - 1][1]
        )

    speed = (
        total_distance
        / elapsed
    )

    if (
        speed
        < TORNADO_MIN_SPEED
    ):

        return None

    return (
        center_x,
        center_y,
        direction
    )


# ============================================================
# MUD ANIMATION HELPERS
# ============================================================

def get_mud_roll():

    frame = mud_roll_frames[
        mud_roll_index
    ]

    if facing == -1:
        return flip(frame)

    return frame


def get_mud_walk():

    frame = mud_walk_frames[
        mud_walk_index
    ]

    if facing == -1:
        return flip(frame)

    return frame


def get_mud_run():

    frame = mud_run_frames[
        mud_run_index
    ]

    if facing == -1:
        return flip(frame)

    return frame


def reset_footprints():

    global last_footprint_x
    global last_footprint_y
    global footprint_side

    last_footprint_x = None
    last_footprint_y = None
    footprint_side = -1

    footprints_overlay.clear_footprints()


def record_muddy_footprints():

    global last_footprint_x
    global last_footprint_y
    global footprint_side

    if not muddy_active or mud_roll_playing:
        return

    paw_x = (
        dog_x
        + CANVAS_SIZE / 2
    )

    paw_y = (
        dog_y
        + CANVAS_SIZE
        - 38
    )

    if last_footprint_x is None:

        last_footprint_x = paw_x
        last_footprint_y = paw_y
        return

    distance = math.hypot(
        paw_x - last_footprint_x,
        paw_y - last_footprint_y
    )

    if distance < FOOTPRINT_DISTANCE:
        return

    footprint_side *= -1

    footprints_overlay.add_footprint(
        paw_x,
        paw_y,
        footprint_side
    )

    last_footprint_x = paw_x
    last_footprint_y = paw_y


def start_mud_mode():

    global muddy_active
    global mud_roll_playing
    global mud_roll_index
    global mud_roll_timer
    global state

    if muddy_active:
        return

    if tornado_active or ssj_active:
        return

    muddy_active = True
    mud_roll_playing = True
    mud_roll_index = 0
    mud_roll_timer = 0.0
    state = "mud_roll"

    reset_footprints()

    footprints_overlay.show()
    footprints_overlay.raise_()

    # The roll replaces the clean dog visually.
    dog.show()
    dog.raise_()

    print()
    print(">>> MUD MODE ACTIVATED <<<")
    print()


def stop_mud_mode():

    global cleaning_active
    global cleaning_index
    global cleaning_timer
    global muddy_active
    global mud_roll_playing
    global mud_roll_index
    global mud_roll_timer
    global mud_walk_index
    global mud_walk_timer
    global mud_run_index
    global mud_run_timer
    global state

    muddy_active = False
    mud_roll_playing = False

    cleaning_active = False
    cleaning_index = 0
    cleaning_timer = 0.0

    cleaning_dog.hide()
    cleaning_dog.clear()

    mud_roll_index = 0
    mud_roll_timer = 0.0

    mud_walk_index = 0
    mud_walk_timer = 0.0

    mud_run_index = 0
    mud_run_timer = 0.0

    state = "idle"

    footprints_overlay.hide()
    reset_footprints()

    dog.resize(
        CANVAS_SIZE,
        CANVAS_SIZE
    )

    dog.setPixmap(
        get_walk()
    )

    dog.move(
        round(dog_x),
        round(dog_y)
    )

    dog.show()
    dog.raise_()

    print()
    print(">>> MUD MODE ENDED <<<")
    print()


def update_mud_roll():

    global mud_roll_index
    global mud_roll_timer
    global mud_roll_playing
    global state

    if not mud_roll_playing:
        return

    mud_roll_timer += (
        MUD_ROLL_FPS / FPS
    )

    while mud_roll_timer >= 1:

        mud_roll_timer -= 1

        mud_roll_index += 1

        if (
            mud_roll_index
            >= MUD_ROLL_FRAME_COUNT
        ):

            mud_roll_index = (
                MUD_ROLL_FRAME_COUNT - 1
            )

            mud_roll_playing = False
            state = "mud"

            break


def update_mud_walk():

    global mud_walk_index
    global mud_walk_timer

    mud_walk_timer += (
        MUD_WALK_FPS / FPS
    )

    while mud_walk_timer >= 1:

        mud_walk_timer -= 1
        mud_walk_index += 1

        if (
            mud_walk_index
            >= MUD_WALK_FRAME_COUNT
        ):

            mud_walk_index = 0


def update_mud_run():

    global mud_run_index
    global mud_run_timer

    mud_run_timer += (
        MUD_RUN_FPS / FPS
    )

    while mud_run_timer >= 1:

        mud_run_timer -= 1
        mud_run_index += 1

        if (
            mud_run_index
            >= MUD_RUN_FRAME_COUNT
        ):

            mud_run_index = 0


def move_muddy_dog():

    global dog_x
    global dog_y
    global facing
    global state

    if mud_roll_playing:
        return

    dx, dy, distance = cursor_data()

    if distance <= CATCH_DISTANCE:

        state = "mud"
        record_muddy_footprints()
        return

    if abs(dx) > 2:

        if dx < 0:
            facing = -1
        else:
            facing = 1

    if distance >= RUN_DISTANCE:

        state = "mud_run"
        speed = MAX_RUN_SPEED

    elif distance >= SLOW_DISTANCE:

        state = "mud_walk"
        speed = MAX_WALK_SPEED

    else:

        state = "mud_walk"

        ratio = (
            distance - CATCH_DISTANCE
        ) / (
            SLOW_DISTANCE - CATCH_DISTANCE
        )

        ratio = max(
            0,
            min(ratio, 1)
        )

        ratio = (
            ratio
            * ratio
            * (
                3 - 2 * ratio
            )
        )

        speed = (
            MIN_CLOSE_SPEED
            + (
                MAX_WALK_SPEED
                - MIN_CLOSE_SPEED
            ) * ratio
        )

    if distance > 0:

        nx = dx / distance
        ny = dy / distance

    else:

        nx = 0
        ny = 0

    dog_x += nx * speed
    dog_y += ny * speed

    dog_x = max(
        screen_rect.left(),
        min(
            dog_x,
            screen_rect.right()
            - CANVAS_SIZE
        )
    )

    dog_y = max(
        screen_rect.top(),
        min(
            dog_y,
            screen_rect.bottom()
            - CANVAS_SIZE
        )
    )

    record_muddy_footprints()


def update_mud_display():

    if mud_roll_playing:

        # Animation advances here, but the dog does not move during the roll.
        update_mud_roll()

        dog.resize(
            CANVAS_SIZE,
            CANVAS_SIZE
        )

        dog.setPixmap(
            get_mud_roll()
        )

    elif state == "mud_run":

        update_mud_run()

        dog.resize(
            CANVAS_SIZE,
            CANVAS_SIZE
        )

        dog.setPixmap(
            get_mud_run()
        )

    else:

        update_mud_walk()

        dog.resize(
            CANVAS_SIZE,
            CANVAS_SIZE
        )

        dog.setPixmap(
            get_mud_walk()
        )

    dog.move(
        round(dog_x),
        round(dog_y)
    )

    dog.show()
    dog.raise_()


# ============================================================
# CLEANING ANIMATION
# ============================================================

def start_cleaning_mode():

    global cleaning_active
    global cleaning_index
    global cleaning_timer
    global state

    if cleaning_active:
        return

    if not muddy_active:
        return

    if tornado_active or ssj_active:
        return

    cleaning_active = True
    cleaning_index = 0
    cleaning_timer = 0.0
    state = "cleaning"

    # Hide the ordinary dog and footprints. The cleaning PNG
    # contains the complete shower + dog animation.
    dog.hide()
    footprints_overlay.hide()

    cleaning_dog.clear()
    cleaning_dog.show()
    cleaning_dog.raise_()

    update_cleaning_display()

    print()
    print(">>> DOG CLEANING STARTED <<<")
    print()


def update_cleaning():

    global cleaning_index
    global cleaning_timer
    global cleaning_active

    if not cleaning_active:
        return

    cleaning_timer += (
        CLEANING_FPS / FPS
    )

    while cleaning_timer >= 1:

        cleaning_timer -= 1
        cleaning_index += 1

        if cleaning_index >= CLEANING_FRAME_COUNT:

            cleaning_index = CLEANING_FRAME_COUNT - 1
            finish_cleaning_mode()
            return


def update_cleaning_display():

    if not cleaning_active:
        return

    pixmap = cleaning_frames[
        cleaning_index
    ]

    if pixmap.isNull():
        return

    cleaning_dog.setPixmap(
        pixmap
    )

    cleaning_dog.resize(
        pixmap.size()
    )

    # Keep the dog in the cleaning animation aligned with the
    # muddy dog's current position. This makes the giant shower
    # appear above the dog regardless of where it is on screen.
    dog_center_x = (
        dog_x
        + CANVAS_SIZE / 2
    )

    dog_baseline = (
        dog_y
        + CLEANING_DOG_BASELINE_Y
    )

    new_x = (
        dog_center_x
        - pixmap.width() / 2
    )

    new_y = (
        dog_baseline
        - CLEANING_FRAME_DOG_BASELINE_Y
    )

    cleaning_dog.move(
        round(new_x),
        round(new_y)
    )

    cleaning_dog.show()
    cleaning_dog.raise_()


def finish_cleaning_mode():

    global cleaning_active
    global cleaning_index
    global cleaning_timer
    global muddy_active
    global mud_roll_playing
    global state

    if not cleaning_active:
        return

    cleaning_active = False
    cleaning_index = 0
    cleaning_timer = 0.0

    # Cleaning is finished: restore the original clean dog state.
    muddy_active = False
    mud_roll_playing = False
    state = "idle"

    cleaning_dog.hide()
    cleaning_dog.clear()

    reset_footprints()
    footprints_overlay.hide()

    dog.resize(
        CANVAS_SIZE,
        CANVAS_SIZE
    )

    dog.setPixmap(
        get_walk()
    )

    dog.move(
        round(dog_x),
        round(dog_y)
    )

    dog.show()
    dog.raise_()

    print()
    print(">>> DOG CLEANED - NORMAL MODE RESTORED <<<")
    print()


# ============================================================
# START TORNADO
# ============================================================

def start_tornado(
    center_x,
    center_y,
    direction
):

    global tornado_active
    global tornado_start_time
    global tornado_angle
    global tornado_origin_x
    global tornado_origin_y
    global tornado_direction
    global tornado_index
    global tornado_timer
    global state
    global tornado_motion_radius

    if tornado_active:
        return

    if ssj_active:
        return

    tornado_active = True

    tornado_start_time = (
        time.monotonic()
    )

    # Store detected mouse-circle center.
    tornado_origin_x = center_x
    tornado_origin_y = center_y

    # Fixed autonomous radius.
    tornado_motion_radius = max(
        120,
        TORNADO_MOTION_RADIUS
    )

    tornado_direction = direction

    # Start from current cursor angle.
    mouse_x, mouse_y = get_cursor()

    tornado_angle = math.atan2(

        mouse_y - center_y,

        mouse_x - center_x
    )

    tornado_index = 0
    tornado_timer = 0.0

    state = "tornado"

    # --------------------------------------------------------
    # CRITICAL:
    #
    # Hide the normal dog.
    #
    # The tornado PNG already contains the dog.
    # No dog frame is added to the tornado.
    # --------------------------------------------------------

    dog.hide()

    tornado_dog.clear()

    tornado_dog.show()

    tornado_dog.raise_()

    # Display first tornado frame immediately.
    update_tornado_display()

    print()
    print(
        ">>> TORNADO ACTIVATED <<<"
    )
    print()


# ============================================================
# STOP TORNADO
# ============================================================

def stop_tornado():

    global tornado_active
    global tornado_index
    global tornado_timer
    global state

    if not tornado_active:
        return

    tornado_active = False

    tornado_index = 0

    tornado_timer = 0.0

    state = "mud" if muddy_active else "idle"

    # --------------------------------------------------------
    # Remove tornado window.
    # --------------------------------------------------------

    tornado_dog.hide()

    tornado_dog.clear()

    # --------------------------------------------------------
    # Restore normal dog window.
    # --------------------------------------------------------

    dog.resize(
        CANVAS_SIZE,
        CANVAS_SIZE
    )

    dog.setPixmap(
        get_walk()
    )

    dog.move(
        round(dog_x),
        round(dog_y)
    )

    dog.show()

    dog.raise_()

    if muddy_active:

        footprints_overlay.show()
        footprints_overlay.raise_()
        update_mud_display()

    # Prevent immediate retrigger.
    cursor_history.clear()

    print()
    print(
        ">>> TORNADO ENDED <<<"
    )
    print()


# ============================================================
# UPDATE TORNADO ANIMATION
# ============================================================

def update_tornado():

    global tornado_index
    global tornado_timer

    tornado_timer += (
        TORNADO_FPS / FPS
    )

    while tornado_timer >= 1:

        tornado_timer -= 1

        tornado_index += 1

        if (
            tornado_index
            >= TORNADO_FRAME_COUNT
        ):

            tornado_index = 0


# ============================================================
# MOVE TORNADO
# ============================================================

def move_tornado():

    global tornado_angle

    tornado_angle += (
        TORNADO_ANGULAR_SPEED
        * tornado_direction
    )

    tornado_angle %= math.tau


# ============================================================
# TORNADO FRAME
# ============================================================

def get_tornado_composite():

    # --------------------------------------------------------
    # Despite the old function name, there is NO COMPOSITING.
    #
    # The tornado image already contains the dog.
    # Return the tornado frame unchanged.
    # --------------------------------------------------------

    return tornado_frames[
        tornado_index
    ]


# ============================================================
# DISPLAY TORNADO
# ============================================================

def update_tornado_display():

    # The tornado PNG is already the complete animation.
    pixmap = get_tornado_composite()

    tornado_dog.setPixmap(
        pixmap
    )

    tornado_dog.resize(
        pixmap.size()
    )

    # --------------------------------------------------------
    # Circular movement.
    # --------------------------------------------------------

    center_x = (

        tornado_origin_x

        + math.cos(
            tornado_angle
        )
        * tornado_motion_radius
    )

    center_y = (

        tornado_origin_y

        + math.sin(
            tornado_angle
        )
        * tornado_motion_radius
    )

    new_x = (
        center_x
        - pixmap.width() / 2
    )

    new_y = (
        center_y
        - pixmap.height() / 2
    )

    # Do NOT independently clamp X/Y.
    # That would turn the circular movement into a square path.

    tornado_dog.move(
        round(new_x),
        round(new_y)
    )

    tornado_dog.show()

    tornado_dog.raise_()


# ============================================================
# CHECK TORNADO
# ============================================================

def check_tornado():

    if ssj_active:
        return

    if tornado_active:
        return

    detection = (
        detect_circular_motion()
    )

    if detection is None:
        return

    (
        center_x,
        center_y,
        direction
    ) = detection

    start_tornado(

        center_x,
        center_y,
        direction
    )


# ============================================================
# CURSOR DATA
# ============================================================

def cursor_data():

    mouse_x, mouse_y = get_cursor()

    center_x = (
        dog_x
        + CANVAS_SIZE / 2
    )

    center_y = (
        dog_y
        + CANVAS_SIZE / 2
    )

    dx = (
        mouse_x
        - center_x
    )

    dy = (
        mouse_y
        - center_y
    )

    distance = math.hypot(
        dx,
        dy
    )

    return (
        dx,
        dy,
        distance
    )


# ============================================================
# NORMAL DOG MOVEMENT
# ============================================================

def move_dog():

    global dog_x
    global dog_y
    global facing
    global state
    global sit_start

    if ssj_active:
        return

    if tornado_active:
        return

    if muddy_active:

        move_muddy_dog()

        return

    dx, dy, distance = (
        cursor_data()
    )

    # ========================================================
    # SLEEPING
    # ========================================================

    if state == "sleeping":

        if (
            distance
            > CATCH_DISTANCE + 60
        ):

            state = "walk"

            sit_start = None

        return


    # ========================================================
    # SITTING
    # ========================================================

    if state == "sitting":

        if (
            distance
            > CATCH_DISTANCE + 60
        ):

            state = "walk"

            sit_start = None

            return

        if sit_start is None:

            sit_start = (
                time.monotonic()
            )

        if (
            time.monotonic()
            - sit_start
            >= SIT_TIME
        ):

            state = "sleeping"

        return


    # ========================================================
    # REACHED CURSOR
    # ========================================================

    if (
        distance
        <= CATCH_DISTANCE
    ):

        state = "sitting"

        sit_start = (
            time.monotonic()
        )

        return


    # ========================================================
    # FACING
    # ========================================================

    if abs(dx) > 2:

        if dx < 0:

            facing = -1

        else:

            facing = 1


    # ========================================================
    # RUN
    # ========================================================

    if (
        distance
        >= RUN_DISTANCE
    ):

        state = "run"

        speed = MAX_RUN_SPEED


    # ========================================================
    # WALK
    # ========================================================

    elif (
        distance
        >= SLOW_DISTANCE
    ):

        state = "walk"

        speed = MAX_WALK_SPEED


    # ========================================================
    # SLOW WALK
    # ========================================================

    else:

        state = "walk"

        ratio = (

            distance
            - CATCH_DISTANCE

        ) / (

            SLOW_DISTANCE
            - CATCH_DISTANCE

        )

        ratio = max(
            0,
            min(
                ratio,
                1
            )
        )

        ratio = (
            ratio
            * ratio
            *
            (
                3
                - 2 * ratio
            )
        )

        speed = (

            MIN_CLOSE_SPEED

            +

            (
                MAX_WALK_SPEED
                - MIN_CLOSE_SPEED
            )
            * ratio

        )


    # ========================================================
    # NORMALIZE
    # ========================================================

    if distance > 0:

        nx = (
            dx / distance
        )

        ny = (
            dy / distance
        )

    else:

        nx = 0
        ny = 0


    # ========================================================
    # MOVE
    # ========================================================

    dog_x += (
        nx * speed
    )

    dog_y += (
        ny * speed
    )


    # ========================================================
    # SCREEN LIMITS
    # ========================================================

    dog_x = max(

        screen_rect.left(),

        min(

            dog_x,

            screen_rect.right()
            - CANVAS_SIZE

        )

    )

    dog_y = max(

        screen_rect.top(),

        min(

            dog_y,

            screen_rect.bottom()
            - CANVAS_SIZE

        )

    )


# ============================================================
# WALK ANIMATION
# ============================================================

def update_walk():

    global walk_index
    global walk_timer

    walk_timer += (
        WALK_FPS / FPS
    )

    while walk_timer >= 1:

        walk_timer -= 1

        walk_index += 1

        if walk_index >= 8:

            walk_index = 0


# ============================================================
# RUN ANIMATION
# ============================================================

def update_run():

    global run_index
    global run_timer

    run_timer += (
        RUN_FPS / FPS
    )

    while run_timer >= 1:

        run_timer -= 1

        run_index += 1

        if run_index >= 8:

            run_index = 0


# ============================================================
# SLEEP ANIMATION
# ============================================================

def update_sleep():

    global sleep_index
    global sleep_timer

    sleep_timer += (
        SLEEP_FPS / FPS
    )

    while sleep_timer >= 1:

        sleep_timer -= 1

        sleep_index += 1

        if sleep_index >= 8:

            # Hold final sleeping pose.
            sleep_index = 4


# ============================================================
# NORMAL DISPLAY
# ============================================================

def update_display():

    # Never overwrite tornado display.
    if tornado_active:

        return

    # Mud mode has its own animation set.
    if muddy_active:

        update_mud_display()

        return


    # ========================================================
    # SSJ
    # ========================================================

    if ssj_active:

        pixmap = get_ssj()

        dog.setPixmap(
            pixmap
        )

        dog.resize(
            pixmap.size()
        )

        center_x = (
            dog_x
            + CANVAS_SIZE / 2
        )

        center_y = (
            dog_y
            + CANVAS_SIZE / 2
        )

        new_x = (
            center_x
            - pixmap.width() / 2
        )

        new_y = (
            center_y
            - pixmap.height() / 2
        )

        dog.move(
            round(new_x),
            round(new_y)
        )

        dog.show()

        return


    # ========================================================
    # NORMAL WINDOW
    # ========================================================

    dog.resize(
        CANVAS_SIZE,
        CANVAS_SIZE
    )

    dog.move(
        round(dog_x),
        round(dog_y)
    )


    # ========================================================
    # SLEEP
    # ========================================================

    if state == "sleeping":

        update_sleep()

        dog.setPixmap(
            get_sleep()
        )

        dog.show()

        return


    # ========================================================
    # SITTING
    # ========================================================

    if state == "sitting":

        dog.setPixmap(
            get_sleep()
        )

        dog.show()

        return


    # ========================================================
    # RUN
    # ========================================================

    if state == "run":

        update_run()

        dog.setPixmap(
            get_run()
        )

        dog.show()

        return


    # ========================================================
    # WALK
    # ========================================================

    if state == "walk":

        update_walk()

        dog.setPixmap(
            get_walk()
        )

        dog.show()

        return


    # ========================================================
    # IDLE
    # ========================================================

    dog.setPixmap(
        get_walk()
    )

    dog.show()


# ============================================================
# PROCESS MUD COMMANDS
# ============================================================

def process_mud_commands():

    global mud_command

    if mud_command is None:
        return

    command = mud_command
    mud_command = None

    if command == "mud":

        if (
            not muddy_active
            and not tornado_active
            and not ssj_active
        ):

            start_mud_mode()

    elif command == "clean":

        # C starts the 10-frame shower cleaning animation.
        # The dog becomes clean only after the animation ends.
        if (
            muddy_active
            and not cleaning_active
            and not tornado_active
            and not ssj_active
        ):

            start_cleaning_mode()


# ============================================================
# MAIN UPDATE
# ============================================================

def update():

    global dog_x
    global dog_y
    global kill_requested


    # ========================================================
    # KILL SWITCH
    # ========================================================

    if kill_requested:

        stop_screen_shake()

        dog.hide()
        tornado_dog.hide()
        cleaning_dog.hide()
        footprints_overlay.hide()

        timer.stop()

        try:
            keyboard_listener.stop()
        except Exception:
            pass

        try:
            mouse_listener.stop()
        except Exception:
            pass

        app.quit()

        return


    # ========================================================
    # MUD KEY COMMANDS
    # ========================================================

    process_mud_commands()


    # ========================================================
    # CLEANING ANIMATION
    # ========================================================

    if cleaning_active:

        dog.hide()
        footprints_overlay.hide()

        update_cleaning()

        if cleaning_active:
            update_cleaning_display()

        return


    # ========================================================
    # CURSOR HISTORY
    # ========================================================

    update_cursor_history()


    # ========================================================
    # SSJ
    # ========================================================

    check_ssj_input()

    if ssj_active:

        update_ssj()

        update_screen_shake()

        update_display()

        return


    # ========================================================
    # TORNADO
    # ========================================================

    if tornado_active:

        footprints_overlay.hide()

        # ----------------------------------------------------
        # NORMAL DOG IS HIDDEN FOR ENTIRE TORNADO.
        # ----------------------------------------------------

        dog.hide()

        elapsed = (

            time.monotonic()
            - tornado_start_time
        )


        # ----------------------------------------------------
        # END TORNADO
        # ----------------------------------------------------

        if (
            elapsed
            >= TORNADO_DURATION
        ):

            stop_tornado()

            return


        # ----------------------------------------------------
        # TORNADO ANIMATION
        # ----------------------------------------------------

        update_tornado()


        # ----------------------------------------------------
        # TORNADO MOVEMENT
        # ----------------------------------------------------

        move_tornado()


        # ----------------------------------------------------
        # SHOW ONLY THE TORNADO PNG.
        # ----------------------------------------------------

        update_tornado_display()


        # ----------------------------------------------------
        # IMPORTANT:
        # Never execute normal dog movement.
        # ----------------------------------------------------

        return


    # ========================================================
    # DETECT NEW TORNADO
    # ========================================================

    check_tornado()

    if tornado_active:

        return


    # ========================================================
    # NORMAL DOG
    # ========================================================

    move_dog()

    update_display()


# ============================================================
# TIMER
# ============================================================

timer = QTimer()

timer.timeout.connect(
    update
)

timer.start(
    int(
        1000 / FPS
    )
)


# ============================================================
# START
# ============================================================

tornado_dog.hide()
cleaning_dog.hide()
footprints_overlay.hide()

dog.setPixmap(
    get_walk()
)

dog.resize(
    CANVAS_SIZE,
    CANVAS_SIZE
)

dog.move(
    round(dog_x),
    round(dog_y)
)

dog.show()

dog.raise_()


# ============================================================
# CONSOLE
# ============================================================

print()
print(
    "========================================"
)
print(
    "             VIRTUAL DOG"
)
print(
    "========================================"
)
print()

print(
    "NORMAL"
)
print(
    "----------------------------------------"
)
print(
    "Far cursor     -> RUN"
)
print(
    "Medium         -> WALK"
)
print(
    "Near cursor    -> SLOW"
)
print(
    "Reached cursor -> SIT"
)
print(
    "After 3 sec    -> SLEEP"
)
print()

print(
    "SUPER SAIYAN"
)
print(
    "----------------------------------------"
)
print(
    "Hold RIGHT MOUSE over dog"
)
print(
    "Dog grows from normal size"
)
print(
    "SSJ animation plays"
)
print(
    "Final frames loop while held"
)
print(
    "Screen shakes"
)
print()

print(
    "TORNADO"
)
print(
    "----------------------------------------"
)
print(
    "Draw a rough circle with cursor"
)
print(
    "Normal dog disappears"
)
print(
    "Tornado PNG already contains dog"
)
print(
    "Only tornado animation is shown"
)
print(
    "Tornado moves in a circle"
)
print(
    "Lasts 5 seconds"
)
print()

print(
    "MUD MODE"
)
print(
    "----------------------------------------"
)
print(
    "M -> Roll in mud and stay muddy"
)
print(
    "C -> Return to clean dog"
)
print(
    "Muddy dog leaves footprints while moving"
)
print()

print(
    "KILL SWITCH"
)
print(
    "----------------------------------------"
)
print(
    "CTRL + SHIFT + Q"
)
print()

print(
    "========================================"
)
print()


# ============================================================
# RUN
# ============================================================

try:

    sys.exit(
        app.exec()
    )

finally:

    try:
        stop_screen_shake()
    except Exception:
        pass

    try:
        keyboard_listener.stop()
    except Exception:
        pass

    try:
        mouse_listener.stop()
    except Exception:
        pass

    try:
        mud_keyboard_listener.stop()
    except Exception:
        pass
