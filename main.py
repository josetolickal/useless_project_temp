import sys
import os
import math

from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QTransform, QCursor


# =============================
# SETTINGS
# =============================

DOG_SIZE = 96

IDLE_SPEED = 180
WALK_ANIMATION_SPEED = 100

IDLE_DISTANCE = 100
WALK_DISTANCE = 300

WALK_SPEED = 2
RUN_SPEED = 6


# =============================
# APPLICATION
# =============================

app = QApplication(sys.argv)

dog = QLabel()

dog.setWindowFlags(
    Qt.FramelessWindowHint |
    Qt.WindowStaysOnTopHint |
    Qt.Tool
)

dog.setAttribute(Qt.WA_TranslucentBackground)

dog.setStyleSheet("""
    QLabel {
        background: transparent;
    }
""")


# =============================
# LOAD FRAMES
# =============================

def load_frames(folder, count):

    result = []

    for number in range(1, count + 1):

        filename = f"{folder}_{number:02d}.png"

        path = os.path.join(
            "assets",
            folder,
            filename
        )

        if not os.path.exists(path):
            print("MISSING:", path)
            continue

        pixmap = QPixmap(path)

        if pixmap.isNull():
            print("FAILED:", path)
            continue

        pixmap = pixmap.scaled(
            DOG_SIZE,
            DOG_SIZE,
            Qt.KeepAspectRatio,
            Qt.FastTransformation
        )

        result.append(pixmap)

        print("LOADED:", path)

    return result


idle_frames = load_frames("idle", 4)
walk_frames = load_frames("walk", 8)


if len(idle_frames) == 0:

    print("ERROR: No idle frames found.")
    sys.exit(1)


if len(walk_frames) == 0:

    print("ERROR: No walk frames found.")
    sys.exit(1)


print()
print("Idle frames:", len(idle_frames))
print("Walk frames:", len(walk_frames))
print()


# =============================
# DOG STATE
# =============================

x = 500
y = 300

direction = 1

dog_state = "idle"

current_frame = 0


# =============================
# CHANGE STATE
# =============================

def set_state(new_state):

    global dog_state
    global current_frame

    if new_state == dog_state:
        return

    dog_state = new_state

    current_frame = 0

    print("DOG STATE:", dog_state.upper())

    if dog_state == "idle":

        animation_timer.start(IDLE_SPEED)

    elif dog_state == "walk":

        animation_timer.start(WALK_ANIMATION_SPEED)


# =============================
# ANIMATION
# =============================

def animate():

    global current_frame

    if dog_state == "walk":

        current_frames = walk_frames

    else:

        current_frames = idle_frames


    if len(current_frames) == 0:
        return


    pixmap = current_frames[current_frame]


    # Turn dog around
    if direction == -1:

        pixmap = pixmap.transformed(
            QTransform().scale(-1, 1),
            Qt.FastTransformation
        )


    dog.setPixmap(pixmap)


    current_frame += 1

    if current_frame >= len(current_frames):

        current_frame = 0


# =============================
# MOVE DOG
# =============================

def move_dog():

    global x
    global y
    global direction


    mouse = QCursor.pos()

    mouse_x = mouse.x()
    mouse_y = mouse.y()


    # Dog center
    dog_center_x = x + DOG_SIZE / 2
    dog_center_y = y + DOG_SIZE / 2


    # Difference
    dx = mouse_x - dog_center_x
    dy = mouse_y - dog_center_y


    # Distance
    distance = math.sqrt(
        dx * dx +
        dy * dy
    )


    # =============================
    # STATE
    # =============================

    if distance <= IDLE_DISTANCE:

        set_state("idle")

        dog.move(int(x), int(y))

        return


    elif distance <= WALK_DISTANCE:

        set_state("walk")

        speed = WALK_SPEED


    else:

        set_state("walk")

        speed = RUN_SPEED


    # =============================
    # MOVE
    # =============================

    if distance > 0:

        x += (dx / distance) * speed
        y += (dy / distance) * speed


    # =============================
    # TURN
    # =============================

    if dx > 0:

        direction = 1

    elif dx < 0:

        direction = -1


    dog.move(int(x), int(y))


# =============================
# START DOG
# =============================

animate()

dog.move(int(x), int(y))

dog.show()


# =============================
# ANIMATION TIMER
# =============================

animation_timer = QTimer()

animation_timer.timeout.connect(animate)

animation_timer.start(IDLE_SPEED)


# =============================
# MOVEMENT TIMER
# =============================

movement_timer = QTimer()

movement_timer.timeout.connect(move_dog)

movement_timer.start(20)


# =============================
# START
# =============================

sys.exit(app.exec())