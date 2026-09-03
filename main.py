import sys
import os
import math
import time
import random
import ctypes
from ctypes import wintypes
from collections import deque

from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QTransform, QPainter, QCursor, QImage

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
# IMAGE LOADER
# ============================================================

def load_image(filename):

    path = os.path.join(
        BASE_DIR,
        filename
    )

    if not os.path.exists(path):

        print()
        print("========================================")
        print("MISSING IMAGE")
        print("========================================")
        print(path)
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

    state = "idle"

    stop_screen_shake()


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

    state = "idle"

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