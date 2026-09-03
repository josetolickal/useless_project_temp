import sys
import os
import math

from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QTransform, QPainter, QCursor


# ============================================================
# APPLICATION
# ============================================================

app = QApplication(sys.argv)


# ============================================================
# SETTINGS
# ============================================================

FPS = 20

# Size of the dog
DOG_SIZE = 65

# Transparent window around the dog
CANVAS_SIZE = 100

# Dog movement speed
DOG_SPEED = 1.8

# Animation speed
SIDE_ANIMATION_FPS = 8.0
DIAGONAL_ANIMATION_FPS = 8.0

# Distance at which dog stops near cursor
CATCH_DISTANCE = 20


# ============================================================
# IMAGE SETTINGS
# ============================================================

SIDE_PREFIX = "walk_"

DIAG_PREFIX = "diag_walk_"

FRAME_COUNT = 8


# ============================================================
# PROGRAM DIRECTORY
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# DOG WINDOW
# ============================================================

dog = QLabel()

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
# LOAD IMAGE
# ============================================================

def load_frame(filename):

    path = os.path.join(
        BASE_DIR,
        filename
    )

    if not os.path.exists(path):

        print()
        print("ERROR: Missing image:")
        print(path)
        print()

        sys.exit(1)

    pixmap = QPixmap(path)

    if pixmap.isNull():

        print()
        print("ERROR: Could not load image:")
        print(path)
        print()

        sys.exit(1)

    # --------------------------------------------------------
    # Resize dog
    # --------------------------------------------------------

    pixmap = pixmap.scaled(
        DOG_SIZE,
        DOG_SIZE,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation
    )

    # --------------------------------------------------------
    # Transparent canvas
    # --------------------------------------------------------

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
        - pixmap.width()
    ) // 2

    y = (
        CANVAS_SIZE
        - pixmap.height()
    ) // 2

    painter.drawPixmap(
        x,
        y,
        pixmap
    )

    painter.end()

    return canvas


# ============================================================
# LOAD SIDEWAYS WALKING FRAMES
# ============================================================

print()
print("Loading sideways walking animation...")
print()

side_frames = []

for i in range(1, FRAME_COUNT + 1):

    filename = (
        f"{SIDE_PREFIX}{i:02d}.png"
    )

    print(
        "Loading:",
        filename
    )

    side_frames.append(
        load_frame(filename)
    )


# ============================================================
# LOAD DIAGONAL WALKING FRAMES
# ============================================================

print()
print("Loading diagonal walking animation...")
print()

diagonal_frames = []

for i in range(1, FRAME_COUNT + 1):

    filename = (
        f"{DIAG_PREFIX}{i:02d}.png"
    )

    print(
        "Loading:",
        filename
    )

    diagonal_frames.append(
        load_frame(filename)
    )


print()
print("======================================")
print("Animation loaded successfully")
print("======================================")
print(
    "Side frames:",
    len(side_frames)
)
print(
    "Diagonal frames:",
    len(diagonal_frames)
)
print("======================================")
print()


# ============================================================
# SCREEN
# ============================================================

screen = QApplication.primaryScreen()

screen_rect = (
    screen.availableGeometry()
)


# ============================================================
# INITIAL DOG POSITION
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
# FACING
#
# 1  = RIGHT
# -1 = LEFT
# ============================================================

facing = 1


# ============================================================
# MOVEMENT TYPE
#
# "idle"
# "side"
# "diagonal"
# ============================================================

movement_type = "idle"


# ============================================================
# ANIMATION VARIABLES
# ============================================================

side_index = 0

diagonal_index = 0

side_timer = 0.0

diagonal_timer = 0.0


# ============================================================
# FLIP IMAGE HORIZONTALLY
# ============================================================

def flip_horizontal(pixmap):

    transform = QTransform()

    transform.scale(
        -1,
        1
    )

    return pixmap.transformed(
        transform,
        Qt.FastTransformation
    )


# ============================================================
# GET SIDE FRAME
# ============================================================

def get_side_frame():

    pixmap = side_frames[
        side_index
    ]

    if facing == -1:

        return flip_horizontal(
            pixmap
        )

    return pixmap


# ============================================================
# GET DIAGONAL FRAME
# ============================================================

def get_diagonal_frame():

    pixmap = diagonal_frames[
        diagonal_index
    ]

    if facing == -1:

        return flip_horizontal(
            pixmap
        )

    return pixmap


# ============================================================
# DETERMINE MOVEMENT TYPE
# ============================================================

def determine_movement(dx, dy):

    global movement_type

    abs_x = abs(dx)
    abs_y = abs(dy)

    # --------------------------------------------------------
    # Almost stopped
    # --------------------------------------------------------

    if (
        abs_x < 2
        and abs_y < 2
    ):

        movement_type = "idle"

        return

    # --------------------------------------------------------
    # DIAGONAL
    #
    # Both X and Y must have meaningful movement.
    # --------------------------------------------------------

    if (
        abs_x > 8
        and abs_y > 8
    ):

        movement_type = "diagonal"

    else:

        movement_type = "side"


# ============================================================
# MOVE DOG
# ============================================================

def move_dog():

    global dog_x
    global dog_y
    global facing

    # --------------------------------------------------------
    # Cursor
    # --------------------------------------------------------

    cursor = QCursor.pos()

    mouse_x = cursor.x()
    mouse_y = cursor.y()

    # --------------------------------------------------------
    # Target position
    # --------------------------------------------------------

    target_x = (
        mouse_x
        - CANVAS_SIZE / 2
    )

    target_y = (
        mouse_y
        - CANVAS_SIZE / 2
    )

    # --------------------------------------------------------
    # Difference
    # --------------------------------------------------------

    dx = (
        target_x
        - dog_x
    )

    dy = (
        target_y
        - dog_y
    )

    # --------------------------------------------------------
    # Distance
    # --------------------------------------------------------

    distance = math.sqrt(
        dx * dx
        + dy * dy
    )

    # --------------------------------------------------------
    # Cursor caught
    # --------------------------------------------------------

    if distance <= CATCH_DISTANCE:

        movement_type = "idle"

        return

    # --------------------------------------------------------
    # Decide animation
    # --------------------------------------------------------

    determine_movement(
        dx,
        dy
    )

    # --------------------------------------------------------
    # Direction / facing
    # --------------------------------------------------------

    if abs(dx) > 2:

        if dx > 0:

            facing = 1

        else:

            facing = -1

    # --------------------------------------------------------
    # Normalize direction
    # --------------------------------------------------------

    direction_x = (
        dx / distance
    )

    direction_y = (
        dy / distance
    )

    # --------------------------------------------------------
    # Move
    # --------------------------------------------------------

    dog_x += (
        direction_x
        * DOG_SPEED
    )

    dog_y += (
        direction_y
        * DOG_SPEED
    )

    # ========================================================
    # SCREEN LIMITS
    # ========================================================

    left_limit = (
        screen_rect.left()
    )

    right_limit = (
        screen_rect.right()
        - CANVAS_SIZE
    )

    top_limit = (
        screen_rect.top()
    )

    bottom_limit = (
        screen_rect.bottom()
        - CANVAS_SIZE
    )

    dog_x = max(
        left_limit,
        min(
            dog_x,
            right_limit
        )
    )

    dog_y = max(
        top_limit,
        min(
            dog_y,
            bottom_limit
        )
    )

    # --------------------------------------------------------
    # Move window
    # --------------------------------------------------------

    dog.move(
        int(dog_x),
        int(dog_y)
    )


# ============================================================
# UPDATE SIDE ANIMATION
# ============================================================

def update_side_animation():

    global side_index
    global side_timer

    side_timer += (
        SIDE_ANIMATION_FPS
        / FPS
    )

    while side_timer >= 1.0:

        side_timer -= 1.0

        side_index += 1

        if side_index >= FRAME_COUNT:

            side_index = 0


# ============================================================
# UPDATE DIAGONAL ANIMATION
# ============================================================

def update_diagonal_animation():

    global diagonal_index
    global diagonal_timer

    diagonal_timer += (
        DIAGONAL_ANIMATION_FPS
        / FPS
    )

    while diagonal_timer >= 1.0:

        diagonal_timer -= 1.0

        diagonal_index += 1

        if diagonal_index >= FRAME_COUNT:

            diagonal_index = 0


# ============================================================
# UPDATE DISPLAYED ANIMATION
# ============================================================

def update_animation():

    # --------------------------------------------------------
    # IDLE
    # --------------------------------------------------------

    if movement_type == "idle":

        dog.setPixmap(
            get_side_frame()
        )

        return

    # --------------------------------------------------------
    # SIDEWAYS
    # --------------------------------------------------------

    if movement_type == "side":

        update_side_animation()

        dog.setPixmap(
            get_side_frame()
        )

        return

    # --------------------------------------------------------
    # DIAGONAL
    # --------------------------------------------------------

    if movement_type == "diagonal":

        update_diagonal_animation()

        dog.setPixmap(
            get_diagonal_frame()
        )

        return


# ============================================================
# MAIN UPDATE
# ============================================================

def update():

    move_dog()

    update_animation()


# ============================================================
# TIMER
# ============================================================

timer = QTimer()

timer.timeout.connect(
    update
)

timer.start(
    int(1000 / FPS)
)


# ============================================================
# INITIAL FRAME
# ============================================================

dog.setPixmap(
    side_frames[0]
)


# ============================================================
# INITIAL POSITION
# ============================================================

dog.move(
    int(dog_x),
    int(dog_y)
)


# ============================================================
# SHOW
# ============================================================

dog.show()


# ============================================================
# CONSOLE INFO
# ============================================================

print()
print("======================================")
print("             VIRTUAL DOG")
print("======================================")
print()
print("Program FPS:        20")
print("Side frames:        8")
print("Diagonal frames:    8")
print("Side animation:     8 FPS")
print("Diagonal animation: 8 FPS")
print("Dog size:           65 px")
print("Dog speed:          1.8")
print()
print("Cursor following:   ON")
print("Side animation:     ON")
print("Diagonal animation: ON")
print("Horizontal flip:    ON")
print()
print("======================================")
print()


# ============================================================
# START APPLICATION
# ============================================================

sys.exit(
    app.exec()
)