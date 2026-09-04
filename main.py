import sys
import os
import math
import time
import random
import ctypes
from ctypes import wintypes
from collections import deque
import threading
import subprocess
import base64

from PySide6.QtWidgets import QApplication, QLabel, QWidget, QMenu, QFileIconProvider
from PySide6.QtCore import Qt, QTimer, QUrl, QFileInfo
from PySide6.QtGui import QPixmap, QTransform, QPainter, QCursor, QImage, QColor, QPen, QBrush, QAction, QFont
from PySide6.QtMultimedia import QSoundEffect

try:
    import winsound
except ImportError:
    winsound = None

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
# OPERATING MODES CONFIGURATION
# ============================================================

MODE_INTERACTIVE = "Interactive"
MODE_FREE = "Free"
MODE_FETCH = "Fetch"

# Time window durations in seconds for each operating mode.
# When Free or Fetch Mode expires, it cleanly returns to Interactive Mode.
INTERACTIVE_MODE_DURATION = 300.0   # 5 minutes
FREE_MODE_DURATION = 300.0          # 5 minutes
FETCH_MODE_DURATION = 300.0         # 5 minutes

# Screen time break configuration (exceeds 1 min -> dog walks to center, sleeps, screen goes black)
SCREEN_TIME_LIMIT = 60.0    # 1 minute (60 seconds)
BREAK_WALK_SPEED = 3.5      # Smooth walk speed toward center


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
# FEEDING / HUNGER SYSTEM
# ============================================================

# Press F to feed the dog.
# The dog must be fed before this timer reaches zero.
FEED_INTERVAL = 30.0

# How long the chicken piece stays near the dog's mouth.
FEED_EFFECT_DURATION = 1.2

# When the dog is not fed in time, the dog enters a short
# automatic Super Saiyan hunger-rage and the desktop is
# visually frozen by a full-screen blocking overlay.
HUNGER_RAGE_DURATION = 5.2


# ============================================================
# HUNGER-RAGE SUPER SAIYAN ANIMATION
# ============================================================

# Front-facing 10-frame SSJ transformation used ONLY when the
# feeding timer expires and the dog enters hunger rage.
HUNGER_SSJ_FRAME_COUNT = 10
HUNGER_SSJ_FPS = 8
HUNGER_SSJ_START_SCALE = 1.0
HUNGER_SSJ_MAX_SCALE = 1.55
HUNGER_SSJ_GROWTH_SPEED = 0.012
HUNGER_SSJ_PADDING = 40


# ============================================================
# EATING ANIMATION
# ============================================================

# Ten dog-only eating frames. The chicken is drawn inside these frames,
# so there is NO separate chicken object or chicken window.
EATING_FRAME_COUNT = 10
EATING_FPS = 10

# Change ONLY this value to make the eating dog larger/smaller.
# 70 matches the normal WALK_SIZE reference.
EATING_SIZE = 70


# ============================================================
# SOUND EFFECTS SETTINGS
# ============================================================

# Periodic barking interval while running (in seconds)
RUN_BARK_INTERVAL_MIN = 1.1
RUN_BARK_INTERVAL_MAX = 1.5

# Volume for sound effects (0.0 to 1.0)
BARK_VOLUME = 0.7
SSJ_VOLUME = 0.85
TORNADO_VOLUME = 0.80


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
# HUNGER RAGE FREEZE OVERLAY
# ============================================================

class HungerFreezeOverlay(QWidget):

    def __init__(self):

        super().__init__()

        self.freeze_pixmap = None
        self.shake_offset_x = 0
        self.shake_offset_y = 0

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
        )

        self.setAttribute(
            Qt.WA_TranslucentBackground,
            False
        )

        # Accept all mouse input so windows underneath cannot
        # be clicked while the hunger-rage freeze is active.
        self.setAttribute(
            Qt.WA_TransparentForMouseEvents,
            False
        )

        self.setGeometry(
            screen.geometry()
        )

        self.hide()

    def capture_screen(self):
        self.setGeometry(screen.geometry())
        self.freeze_pixmap = screen.grabWindow(0)
        self.shake_offset_x = 0
        self.shake_offset_y = 0
        self.update()

    def set_shake_offset(self, ox, oy):
        self.shake_offset_x = ox
        self.shake_offset_y = oy
        self.update()

    def mousePressEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()

    def mouseMoveEvent(self, event):
        event.accept()

    def wheelEvent(self, event):
        event.accept()

    def keyPressEvent(self, event):
        event.accept()

    def paintEvent(self, event):

        painter = QPainter(self)

        # 1. Draw the exact frozen desktop screenshot with screen rumble offset
        if self.freeze_pixmap and not self.freeze_pixmap.isNull():
            painter.drawPixmap(
                self.shake_offset_x,
                self.shake_offset_y,
                self.freeze_pixmap
            )
            # 2. Icy cold frost tint over the frozen windows
            painter.fillRect(
                self.rect(),
                QColor(130, 205, 255, 45)
            )
        else:
            painter.fillRect(
                self.rect(),
                QColor(18, 18, 24, 180)
            )

        # 3. Frost / ice border vignette around the screen
        pen = QPen(QColor(160, 230, 255, 140), 10)
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(5, 5, -5, -5))

        # 4. Top banner showing frozen state
        banner_w = min(720, self.rect().width() - 40)
        banner_x = (self.rect().width() - banner_w) // 2
        banner_rect = self.rect()
        banner_rect.setLeft(banner_x)
        banner_rect.setWidth(banner_w)
        banner_rect.setTop(24)
        banner_rect.setHeight(64)

        painter.setPen(QPen(QColor(130, 210, 255, 180), 2))
        painter.setBrush(QBrush(QColor(12, 16, 26, 220)))
        painter.drawRoundedRect(banner_rect, 10, 10)

        font = painter.font()
        font.setPointSize(22)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 215, 50, 255)))

        text = "❄️ WINDOWS FROZEN — DOG HUNGER RAGE! ⚡"
        painter.drawText(
            banner_rect,
            Qt.AlignCenter,
            text
        )

        painter.end()


hunger_overlay = HungerFreezeOverlay()


# ============================================================
# SCREEN TIME BREAK OVERLAY
# ============================================================

screen_time_start = time.monotonic()
break_active = False
break_stage = "idle"  # "walking", "sleeping"
break_target_x = 0.0
break_target_y = 0.0


class BreakOverlay(QWidget):
    """Fullscreen black window overlay for screen time breaks.
    Activated when screen time exceeds 1 minute.
    Shows dark background with 'Take a break' message while dog sleeps at center on top."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setGeometry(screen.geometry())
        self.hide()

    def mousePressEvent(self, event):
        resume_from_break()
        event.accept()

    def keyPressEvent(self, event):
        resume_from_break()
        event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Deep pure black window background
        painter.fillRect(self.rect(), QColor(5, 7, 12, 255))

        center_x = self.rect().width() / 2.0
        center_y = self.rect().height() / 2.0

        # Message Container above center dog
        banner_w = min(680, self.rect().width() - 40)
        banner_x = (self.rect().width() - banner_w) // 2
        banner_y = max(35, int(center_y - 210))

        banner_rect = self.rect()
        banner_rect.setLeft(banner_x)
        banner_rect.setWidth(banner_w)
        banner_rect.setTop(banner_y)
        banner_rect.setHeight(130)

        painter.setPen(QPen(QColor(255, 255, 255, 35), 1))
        painter.setBrush(QBrush(QColor(18, 22, 32, 235)))
        painter.drawRoundedRect(banner_rect, 16, 16)

        # Title: "☕ Take a break!"
        title_font = painter.font()
        title_font.setPointSize(24)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QPen(QColor(248, 250, 252, 255)))

        title_rect = self.rect()
        title_rect.setLeft(banner_x)
        title_rect.setWidth(banner_w)
        title_rect.setTop(banner_y + 16)
        title_rect.setHeight(40)
        painter.drawText(title_rect, Qt.AlignCenter, "☕ Take a break!")

        # Subtitle
        sub_font = painter.font()
        sub_font.setPointSize(13)
        sub_font.setBold(False)
        painter.setFont(sub_font)
        painter.setPen(QPen(QColor(148, 163, 184, 255)))

        sub_rect = self.rect()
        sub_rect.setLeft(banner_x)
        sub_rect.setWidth(banner_w)
        sub_rect.setTop(banner_y + 58)
        sub_rect.setHeight(28)
        painter.drawText(sub_rect, Qt.AlignCenter, "Screen time exceeded 1 minute. Give your eyes a rest!")

        # Resume hint
        hint_font = painter.font()
        hint_font.setPointSize(11)
        hint_font.setBold(True)
        painter.setFont(hint_font)
        painter.setPen(QPen(QColor(56, 189, 248, 240)))

        hint_rect = self.rect()
        hint_rect.setLeft(banner_x)
        hint_rect.setWidth(banner_w)
        hint_rect.setTop(banner_y + 88)
        hint_rect.setHeight(28)
        painter.drawText(hint_rect, Qt.AlignCenter, "✨ Click anywhere or press any key to resume")

        # Subtle bottom note under sleeping dog
        bottom_font = painter.font()
        bottom_font.setPointSize(12)
        bottom_font.setBold(False)
        painter.setFont(bottom_font)
        painter.setPen(QPen(QColor(100, 116, 139, 200)))
        bottom_rect = self.rect()
        bottom_rect.setLeft(0)
        bottom_rect.setWidth(self.rect().width())
        bottom_rect.setTop(int(center_y + 130))
        bottom_rect.setHeight(35)
        painter.drawText(bottom_rect, Qt.AlignCenter, "💤 Shh... your dog is resting peacefully in the center")

        painter.end()


break_overlay = BreakOverlay()


def start_screen_break():
    global break_active, break_stage, break_target_x, break_target_y, was_running

    if break_active:
        return

    # No screen break while Spotify music is playing
    if 'spotify_detector' in globals() and spotify_detector.is_music_playing():
        return

    if hunger_rage_active or eating_active or cleaning_active:
        return

    if tornado_active:
        stop_tornado()
    if ssj_active:
        stop_ssj()

    break_active = True
    break_stage = "walking"

    # Screen center coordinates for dog canvas
    break_target_x = (screen_rect.left() + screen_rect.right() - CANVAS_SIZE) / 2.0
    break_target_y = (screen_rect.top() + screen_rect.bottom() - CANVAS_SIZE) / 2.0

    # Show black window overlay
    break_overlay.setGeometry(screen.geometry())
    break_overlay.show()
    break_overlay.raise_()

    # Dog must be visible on top of the black window
    dog.show()
    dog.raise_()

    food_timer_label.hide()

    if 'mode_controller' in globals() and mode_controller:
        mode_controller.despawn_toys()

    print()
    print(">>> SCREEN TIME EXCEEDED 1 MIN: TAKE A BREAK ACTIVATED <<<")
    print()


def resume_from_break():
    global break_active, break_stage, state, screen_time_start

    if not break_active:
        return

    break_active = False
    break_stage = "idle"
    break_overlay.hide()

    state = "mud" if muddy_active else "idle"
    screen_time_start = time.monotonic()

    food_timer_label.show()
    food_timer_label.raise_()
    update_food_timer_display()

    if 'mode_controller' in globals() and mode_controller:
        if mode_controller.current_mode == MODE_FREE:
            mode_controller.enter_free_substate("idle", duration=1.5)

    print()
    print(">>> RESUMED FROM SCREEN TIME BREAK: WELCOME BACK <<<")
    print()


def update_screen_break():
    global dog_x, dog_y, facing, state, break_stage, food_deadline

    # Extend hunger deadline while on break so the dog doesn't starve during break
    food_deadline += 1.0 / FPS

    break_overlay.raise_()
    dog.show()
    dog.raise_()

    if break_stage == "walking":
        dx = break_target_x - dog_x
        dy = break_target_y - dog_y
        dist = math.hypot(dx, dy)

        if dist <= BREAK_WALK_SPEED + 1.0:
            dog_x = break_target_x
            dog_y = break_target_y
            break_stage = "sleeping"
            state = "sleeping"
        else:
            nx = dx / dist
            ny = dy / dist
            dog_x += nx * BREAK_WALK_SPEED
            dog_y += ny * BREAK_WALK_SPEED
            if abs(dx) > 1.0:
                facing = 1 if dx > 0 else -1
            state = "mud_walk" if muddy_active else "walk"

    elif break_stage == "sleeping":
        state = "sleeping"


# ============================================================
# FOOD TIMER / MODE HUD
# ============================================================

def show_mode_menu(global_pos):
    global mode_controller, muddy_active
    menu = QMenu()
    menu.setStyleSheet(
        "QMenu { "
        "background-color: #1a1d24; "
        "color: #f1f5f9; "
        "border: 1px solid #3b4252; "
        "border-radius: 8px; "
        "padding: 6px; "
        "font-size: 13px; "
        "font-family: 'Segoe UI', Arial, sans-serif; "
        "font-weight: 500; "
        "} "
        "QMenu::item { "
        "padding: 6px 20px; "
        "border-radius: 5px; "
        "} "
        "QMenu::item:selected { "
        "background-color: #2563eb; "
        "color: white; "
        "} "
        "QMenu::separator { "
        "height: 1px; "
        "background: #334155; "
        "margin: 4px 6px; "
        "}"
    )

    curr = mode_controller.current_mode if 'mode_controller' in globals() and mode_controller else MODE_INTERACTIVE

    is_dancing = spotify_detector.is_music_playing() if 'spotify_detector' in globals() else False
    act_interactive = menu.addAction(f"🎮 Interactive Mode {'✓' if curr == MODE_INTERACTIVE else '  (Key 1)'}")
    act_free = menu.addAction(f"🐾 Free Mode {'✓' if curr == MODE_FREE else '  (Key 2)'}")
    act_fetch = menu.addAction(f"🐕 Fetch Mode {'✓' if curr == MODE_FETCH else '  (Key 3)'}")
    menu.addSeparator()
    act_go_fetch = None
    if curr == MODE_FETCH:
        act_go_fetch = menu.addAction("🎾 Go Fetch Shortcut! (Space / Key 3)")
    act_dance = menu.addAction(f"🎵 Spotify Dance {'✓ (Grooving)' if is_dancing else '  (Key D)'}")
    act_cat = menu.addAction("🐱 Chase Cat (Free Mode)")
    act_balls = menu.addAction("🎾 Play with Balls (Free Mode)")
    menu.addSeparator()
    act_feed = menu.addAction("🍗 Feed Dog (Key F)")
    act_mud = menu.addAction("🧼 Clean Dog (Key C)" if muddy_active else "💩 Roll in Mud (Key M)")
    act_break = menu.addAction("☕ Take a Break Now")
    menu.addSeparator()
    act_quit = menu.addAction("❌ Quit (Ctrl+Shift+Q)")

    action = menu.exec(global_pos)
    if not action:
        return

    if action == act_interactive:
        mode_controller.set_mode(MODE_INTERACTIVE)
    elif action == act_free:
        mode_controller.set_mode(MODE_FREE)
    elif action == act_fetch:
        mode_controller.set_mode(MODE_FETCH)
    elif act_go_fetch and action == act_go_fetch:
        if mode_controller.current_mode != MODE_FETCH:
            mode_controller.set_mode(MODE_FETCH)
        mode_controller.trigger_fetch()
    elif action == act_dance:
        if 'spotify_detector' in globals():
            spotify_detector.toggle_manual()
    elif action == act_cat:
        if mode_controller.current_mode != MODE_FREE:
            mode_controller.set_mode(MODE_FREE)
        mode_controller.enter_free_substate("chase_cat")
    elif action == act_balls:
        if mode_controller.current_mode != MODE_FREE:
            mode_controller.set_mode(MODE_FREE)
        mode_controller.enter_free_substate("play_ball")
    elif action == act_feed:
        start_feeding()
    elif action == act_mud:
        if muddy_active:
            start_cleaning_mode()
        else:
            start_mud_mode()
    elif action == act_break:
        start_screen_break()
    elif action == act_quit:
        kill_dog()


class HUDLabel(QLabel):
    def __init__(self):
        super().__init__()
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
            False
        )
        self.setStyleSheet(
            "QLabel { "
            "background: rgba(20, 24, 32, 215); "
            "color: #f8fafc; "
            "padding: 7px 14px; "
            "border: 1px solid rgba(255, 255, 255, 45); "
            "border-radius: 9px; "
            "font-size: 13px; "
            "font-family: 'Segoe UI', Arial, sans-serif; "
            "font-weight: bold; "
            "} "
            "QLabel:hover { "
            "background: rgba(30, 36, 48, 240); "
            "border: 1px solid rgba(59, 130, 246, 0.75); "
            "}"
        )
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        show_mode_menu(event.globalPos())
        super().mousePressEvent(event)


food_timer_label = HUDLabel()
food_timer_label.adjustSize()
food_timer_label.move(
    screen_rect.left() + 20,
    screen_rect.top() + 20
)
food_timer_label.show()
food_timer_label.raise_()


# ============================================================
# IMAGE LOADER
# ============================================================

def load_image(filename):

    candidates = [
        os.path.join(BASE_DIR, filename),
        os.path.join(BASE_DIR, "eating", filename),
        os.path.join(BASE_DIR, "assets", filename),
        os.path.join(BASE_DIR, "assets", "cat", filename),
        os.path.join(BASE_DIR, "assets", "toys", filename),
        os.path.join(BASE_DIR, "assets", "eating", filename),
        os.path.join(BASE_DIR, "assets", "mud", filename),
        os.path.join(BASE_DIR, "assets", "ssj_front", filename),
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


# ============================================================
# LOAD FRONT-FACING HUNGER-RAGE SSJ
# ============================================================

def load_hunger_ssj_animation():

    frames = []

    for i in range(1, HUNGER_SSJ_FRAME_COUNT + 1):

        filename = f"ssj_front_{i:02d}.png"

        print(
            "Loading:",
            filename
        )

        img = load_image(filename)

        img = crop_transparent(img)

        img = add_padding(
            img,
            HUNGER_SSJ_PADDING
        )

        frames.append(img)

    return frames


hunger_ssj_frames = load_hunger_ssj_animation()

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
# LOAD EATING ANIMATION
# ============================================================

def load_eating_animation():
    frames = []

    for i in range(1, EATING_FRAME_COUNT + 1):
        filename = f"eat_{i:02d}.png"
        print(
            "Loading:",
            filename
        )

        img = load_image(filename)

        # Use the SAME prepare_frame pipeline as the normal dog so
        # EATING_SIZE is the only value controlling the eating size.
        frame = prepare_frame(
            img,
            EATING_SIZE
        )

        frames.append(frame)

    return frames


eating_frames = load_eating_animation()


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
# LOAD SOUND EFFECTS
# ============================================================

bark_sounds = []
ssj_sound = None
tornado_sound = None


def load_sound_effects():
    global bark_sounds, ssj_sound, tornado_sound

    sound_dir = os.path.join(BASE_DIR, "assets", "sounds")
    f1 = os.path.join(sound_dir, "bark.wav")
    f2 = os.path.join(sound_dir, "bark_alt.wav")
    f_ssj = os.path.join(sound_dir, "ssj.wav")
    f_tornado = os.path.join(sound_dir, "tornado.wav")
    bark_sounds = []

    for path in (f1, f2):
        if os.path.exists(path):
            try:
                sound = QSoundEffect()
                sound.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
                sound.setVolume(BARK_VOLUME)
                bark_sounds.append(sound)
                print("Loaded sound effect:", os.path.basename(path))
            except Exception as e:
                print(f"Failed to load {path}: {e}")

    if os.path.exists(f_ssj):
        try:
            ssj_sound = QSoundEffect()
            ssj_sound.setSource(QUrl.fromLocalFile(os.path.abspath(f_ssj)))
            ssj_sound.setVolume(SSJ_VOLUME)
            print("Loaded sound effect:", os.path.basename(f_ssj))
        except Exception as e:
            print(f"Failed to load {f_ssj}: {e}")

    if os.path.exists(f_tornado):
        try:
            tornado_sound = QSoundEffect()
            tornado_sound.setSource(QUrl.fromLocalFile(os.path.abspath(f_tornado)))
            tornado_sound.setVolume(TORNADO_VOLUME)
            try:
                tornado_sound.setLoopCount(QSoundEffect.Loop.Infinite.value)
            except Exception:
                tornado_sound.setLoopCount(-2)
            print("Loaded sound effect:", os.path.basename(f_tornado))
        except Exception as e:
            print(f"Failed to load {f_tornado}: {e}")


load_sound_effects()


def play_ssj_sound():
    if ssj_sound:
        try:
            ssj_sound.stop()
            ssj_sound.play()
        except Exception:
            pass

    # Windows native audio playback
    if sys.platform == "win32" and winsound:
        try:
            sound_path = os.path.join(BASE_DIR, "assets", "sounds", "ssj.wav")
            if os.path.exists(sound_path):
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass


def stop_ssj_sound():
    if ssj_sound:
        try:
            ssj_sound.stop()
        except Exception:
            pass

    if sys.platform == "win32" and winsound:
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass


def play_tornado_sound():
    if tornado_sound:
        try:
            tornado_sound.stop()
            tornado_sound.play()
        except Exception:
            pass

    if sys.platform == "win32" and winsound:
        try:
            sound_path = os.path.join(BASE_DIR, "assets", "sounds", "tornado.wav")
            if os.path.exists(sound_path):
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
        except Exception:
            pass


def stop_tornado_sound():
    if tornado_sound:
        try:
            tornado_sound.stop()
        except Exception:
            pass

    if sys.platform == "win32" and winsound:
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass


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
# FEEDING STATE
# ============================================================


feeding_active = False
feeding_end_time = 0.0

# Monotonic deadline for the next required feeding.
food_deadline = time.monotonic() + FEED_INTERVAL

# Prevent the automatic rage from starting repeatedly in the same frame.
hunger_rage_active = False
hunger_rage_end_time = 0.0
hunger_rage_pending = False

# Front-facing SSJ state used only during hunger rage.
hunger_ssj_index = 0
hunger_ssj_timer = 0.0
hunger_ssj_scale = HUNGER_SSJ_START_SCALE


# Eating animation state.
eating_active = False
eating_index = 0
eating_timer = 0.0


# ============================================================
# RUN BARK STATE
# ============================================================

last_bark_time = 0.0
next_bark_interval = 1.2
bark_index = 0
was_running = False


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
# FREE MODE COMPANIONS: CAT & BALL TOYS
# ============================================================

class FreeCatCompanion:
    """Lightweight, mouse-transparent cat overlay companion for Free Mode cat chase.
    Never blocks user mouse clicks and never duplicates the main dog window."""

    WIDTH = 72
    HEIGHT = 60

    def __init__(self):
        self.label = QLabel()
        self.label.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.label.setStyleSheet("background: transparent;")

        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.anim_frame = 0
        self.anim_timer = 0.0
        self.active = False
        self.tag_cooldown = 0.0
        self.sit_timer = 0.0

        self.load_sprites()
        self.label.hide()

    def load_sprites(self):
        try:
            raw_run = [
                load_image(f"cat_run_{i:02d}.png")
                for i in (1, 2, 3)
            ]
            raw_sit = load_image("cat_sit.png")
        except Exception:
            base_cat = os.path.join(BASE_DIR, "assets", "cat")
            raw_run = [
                QPixmap(os.path.join(base_cat, f"cat_run_{i:02d}.png"))
                for i in (1, 2, 3)
            ]
            raw_sit = QPixmap(os.path.join(base_cat, "cat_sit.png"))

        self.run_right = [
            f.scaled(self.WIDTH, self.HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            for f in raw_run
        ]
        self.sit_right = raw_sit.scaled(self.WIDTH, self.HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        flip_tr = QTransform()
        flip_tr.scale(-1, 1)
        self.run_left = [
            f.transformed(flip_tr, Qt.FastTransformation)
            for f in self.run_right
        ]
        self.sit_left = self.sit_right.transformed(flip_tr, Qt.FastTransformation)

    def spawn(self, x, y):
        min_x = screen_rect.left() + 60
        max_x = screen_rect.right() - self.WIDTH - 60
        min_y = screen_rect.top() + 60
        max_y = screen_rect.bottom() - self.HEIGHT - 60

        self.x = max(min_x, min(float(x), max_x))
        self.y = max(min_y, min(float(y), max_y))
        self.vx = random.choice([-1, 1]) * random.uniform(3.5, 5.5)
        self.vy = random.uniform(-2.5, 2.5)
        self.facing = 1 if self.vx > 0 else -1
        self.anim_frame = 0
        self.anim_timer = 0.0
        self.active = True
        self.sit_timer = 0.0
        self.tag_cooldown = time.monotonic() + 0.8

        pix = self.run_right[0] if self.facing == 1 else self.run_left[0]
        self.label.setPixmap(pix)
        self.label.resize(pix.size())
        self.label.move(round(self.x), round(self.y))
        self.label.show()
        self.label.raise_()

    def update(self, dog_cx, dog_cy):
        if not self.active:
            return

        now = time.monotonic()

        # If sitting briefly after being tagged
        if self.sit_timer > 0:
            if now < self.sit_timer:
                pix = self.sit_right if self.facing == 1 else self.sit_left
                self.label.setPixmap(pix)
                self.label.move(round(self.x), round(self.y))
                return
            else:
                self.sit_timer = 0.0
                flee_dir = 1 if self.x > dog_cx else -1
                self.vx = flee_dir * random.uniform(6.5, 9.5)
                self.vy = random.uniform(-4.0, 4.0)

        cat_cx = self.x + self.WIDTH / 2.0
        cat_cy = self.y + self.HEIGHT / 2.0
        dx = cat_cx - dog_cx
        dy = cat_cy - dog_cy
        dist = math.hypot(dx, dy)

        # Flee vector with playful evasion
        if dist < 15:
            nx = 1.0 if self.x >= dog_cx else -1.0
            ny = 0.0
        else:
            nx = dx / dist
            ny = dy / dist

        # Add lively sinusoidal lateral wiggle
        wiggle = math.sin(now * 5.0) * 0.45
        evade_x = nx - ny * wiggle
        evade_y = ny + nx * wiggle
        evade_len = math.hypot(evade_x, evade_y)
        if evade_len > 1e-5:
            evade_x /= evade_len
            evade_y /= evade_len

        cat_speed = random.uniform(4.8, 6.2)
        self.vx = self.vx * 0.82 + evade_x * cat_speed * 0.18
        self.vy = self.vy * 0.82 + evade_y * cat_speed * 0.18

        self.x += self.vx
        self.y += self.vy

        # Screen boundaries bounce
        min_x = screen_rect.left() + 50
        max_x = screen_rect.right() - self.WIDTH - 50
        min_y = screen_rect.top() + 50
        max_y = screen_rect.bottom() - self.HEIGHT - 50

        if self.x < min_x:
            self.x = min_x
            self.vx = abs(self.vx) * 1.2
        elif self.x > max_x:
            self.x = max_x
            self.vx = -abs(self.vx) * 1.2

        if self.y < min_y:
            self.y = min_y
            self.vy = abs(self.vy) * 1.2
        elif self.y > max_y:
            self.y = max_y
            self.vy = -abs(self.vy) * 1.2

        if abs(self.vx) > 0.2:
            self.facing = 1 if self.vx > 0 else -1

        # Check tag by dog
        if dist < 55.0 and now >= self.tag_cooldown:
            self.tag_cooldown = now + 1.2
            if 'play_bark_sound' in globals():
                play_bark_sound()
            if random.random() < 0.45:
                self.sit_timer = now + random.uniform(0.4, 0.8)
                self.vx = 0.0
                self.vy = 0.0
            else:
                leap_dir = 1 if self.x > dog_cx else -1
                self.vx = leap_dir * random.uniform(8.0, 12.0)
                self.vy = random.uniform(-6.0, 6.0)

        # Animation
        self.anim_timer += 9.0 / FPS
        while self.anim_timer >= 1.0:
            self.anim_timer -= 1.0
            self.anim_frame = (self.anim_frame + 1) % len(self.run_right)

        pix = self.run_right[self.anim_frame] if self.facing == 1 else self.run_left[self.anim_frame]
        self.label.setPixmap(pix)
        self.label.resize(pix.size())
        self.label.move(round(self.x), round(self.y))

    def despawn(self):
        self.active = False
        try:
            self.label.hide()
        except Exception:
            pass

    def destroy(self):
        self.active = False
        try:
            self.label.hide()
            self.label.clear()
            self.label.deleteLater()
        except Exception:
            pass


class FreeBallToy:
    """Lightweight, mouse-transparent ball overlay toy with realistic bounce & rolling physics.
    Supports kicking by dog and multi-ball play."""

    SIZE = 36

    def __init__(self, ball_type="tennis"):
        self.ball_type = ball_type
        self.label = QLabel()
        self.label.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.label.setStyleSheet("background: transparent;")

        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0
        self.active = False
        self.kick_cooldown = 0.0

        if ball_type == "tennis":
            self.restitution = 0.76
            self.gravity = 0.38
            self.image_file = "ball_tennis.png"
        else:
            self.restitution = 0.84
            self.gravity = 0.42
            self.image_file = "ball_red.png"

        self.load_sprite()
        self.label.hide()

    def load_sprite(self):
        try:
            raw = load_image(self.image_file)
        except Exception:
            base_toys = os.path.join(BASE_DIR, "assets", "toys")
            raw = QPixmap(os.path.join(base_toys, self.image_file))

        self.base_pixmap = raw.scaled(
            self.SIZE, self.SIZE,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

    def spawn(self, x, y, vx=0.0, vy=0.0):
        min_x = screen_rect.left() + 40
        max_x = screen_rect.right() - self.SIZE - 40
        min_y = screen_rect.top() + 40
        floor_y = screen_rect.bottom() - 65

        self.x = max(min_x, min(float(x), max_x))
        self.y = max(min_y, min(float(y), floor_y))
        self.vx = float(vx)
        self.vy = float(vy)
        self.angle = 0.0
        self.active = True
        self.kick_cooldown = time.monotonic() + 0.3

        self.label.setPixmap(self.base_pixmap)
        self.label.resize(self.base_pixmap.size())
        self.label.move(round(self.x), round(self.y))
        self.label.show()
        self.label.raise_()

    def update(self, dog_cx, dog_cy):
        if not self.active:
            return

        now = time.monotonic()

        # Physics: gravity and air resistance
        self.vy += self.gravity
        self.vx *= 0.991

        self.x += self.vx
        self.y += self.vy

        min_x = screen_rect.left() + 35
        max_x = screen_rect.right() - self.SIZE - 35
        min_y = screen_rect.top() + 35
        floor_y = screen_rect.bottom() - 65

        # Floor bounce
        if self.y >= floor_y:
            self.y = floor_y
            self.vy = -self.vy * self.restitution
            self.vx *= 0.95
            if abs(self.vy) < 0.7:
                self.vy = 0.0

        # Wall bounces
        if self.x <= min_x:
            self.x = min_x
            self.vx = abs(self.vx) * self.restitution
        elif self.x >= max_x:
            self.x = max_x
            self.vx = -abs(self.vx) * self.restitution

        if self.y <= min_y:
            self.y = min_y
            self.vy = abs(self.vy) * 0.7

        # Kick detection by dog
        bcx = self.x + self.SIZE / 2.0
        bcy = self.y + self.SIZE / 2.0
        dist = math.hypot(bcx - dog_cx, bcy - dog_cy)

        if dist < 54.0 and now >= self.kick_cooldown:
            self.kick_cooldown = now + 0.4
            kick_dir = 1.0 if bcx >= dog_cx else -1.0
            self.vx = kick_dir * random.uniform(7.0, 11.5)
            self.vy = -random.uniform(9.0, 14.0)
            if 'play_bark_sound' in globals():
                play_bark_sound()
            if 'muddy_active' in globals() and muddy_active and 'record_muddy_footprints' in globals():
                record_muddy_footprints()

        # Rotation animation
        self.angle = (self.angle + self.vx * 4.5) % 360.0
        tr = QTransform().rotate(self.angle)
        rot_pix = self.base_pixmap.transformed(tr, Qt.SmoothTransformation)
        self.label.setPixmap(rot_pix)
        self.label.resize(rot_pix.size())
        self.label.move(
            round(bcx - rot_pix.width() / 2.0),
            round(bcy - rot_pix.height() / 2.0)
        )

    def despawn(self):
        self.active = False
        try:
            self.label.hide()
        except Exception:
            pass

    def destroy(self):
        self.active = False
        try:
            self.label.hide()
            self.label.clear()
            self.label.deleteLater()
        except Exception:
            pass


# ============================================================
# FETCH MODE SHORTCUT SYSTEM
# ============================================================

def scan_desktop_shortcuts():
    """Scans user and public desktop directories for actual desktop shortcuts and files."""
    user_desktop = os.path.expanduser(r"~\Desktop")
    public_desktop = r"C:\Users\Public\Desktop"
    shortcuts = []
    seen = set()

    for base in [user_desktop, public_desktop]:
        if not os.path.exists(base):
            continue
        try:
            for f in os.listdir(base):
                if f.startswith("~") or f.startswith("."):
                    continue
                lower = f.lower()
                if lower.endswith((".lnk", ".url", ".exe", ".docx", ".zip", ".7z", ".pdf", ".txt", ".png", ".jpg")) or "." not in f:
                    name = os.path.splitext(f)[0]
                    if name.lower() not in seen:
                        seen.add(name.lower())
                        shortcuts.append({
                            "name": name,
                            "path": os.path.join(base, f),
                            "file": f,
                        })
        except Exception:
            pass

    if not shortcuts:
        shortcuts = [
            {"name": "VALORANT", "path": "", "file": "VALORANT.lnk"},
            {"name": "Discord", "path": "", "file": "Discord.lnk"},
            {"name": "Steam", "path": "", "file": "Steam.lnk"},
            {"name": "Antigravity IDE", "path": "", "file": "Antigravity.lnk"},
            {"name": "Chrome", "path": "", "file": "Chrome.lnk"},
        ]
    return shortcuts


def create_shortcut_badge(name, file_path=None, width=72, height=92):
    """Creates a cute, authentic Windows desktop shortcut icon badge."""
    canvas = QPixmap(width, height)
    canvas.fill(Qt.transparent)

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    icon_pix = None
    if file_path and os.path.exists(file_path):
        try:
            ip = QFileIconProvider()
            icon = ip.icon(QFileInfo(file_path))
            icon_pix = icon.pixmap(48, 48)
        except Exception:
            pass

    if not icon_pix or icon_pix.isNull():
        icon_pix = QPixmap(48, 48)
        icon_pix.fill(Qt.transparent)
        ip = QPainter(icon_pix)
        ip.setRenderHint(QPainter.Antialiasing)
        ip.setBrush(QBrush(QColor(59, 130, 246, 235)))
        ip.setPen(QPen(QColor(255, 255, 255, 190), 2))
        ip.drawRoundedRect(2, 2, 44, 44, 8, 8)
        ip.setPen(QColor(255, 255, 255))
        ip.setFont(QFont("Segoe UI", 16, QFont.Bold))
        ip.drawText(0, 0, 48, 48, Qt.AlignCenter, name[:1].upper() if name else "★")
        ip.end()

    ix = (width - 48) // 2
    iy = 4
    painter.drawPixmap(ix, iy, icon_pix)

    # Windows shortcut arrow badge
    painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
    painter.setPen(QPen(QColor(100, 116, 139, 180), 1))
    painter.drawRoundedRect(ix, iy + 34, 14, 14, 3, 3)
    painter.setPen(QColor(15, 23, 42))
    painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
    painter.drawText(ix + 2, iy + 45, "↗")

    # Name label
    painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
    disp_name = name if len(name) <= 13 else name[:11] + ".."

    painter.setPen(QColor(0, 0, 0, 230))
    painter.drawText(0, 56, width, 32, Qt.AlignHCenter | Qt.AlignTop, disp_name)
    painter.setPen(QColor(255, 255, 255, 255))
    painter.drawText(0, 55, width, 32, Qt.AlignHCenter | Qt.AlignTop, disp_name)

    painter.end()
    return canvas


def get_shortcut_desktop_pos(index, total_count):
    """Calculates typical desktop icon grid position for the given shortcut index."""
    max_rows = max(5, int((screen_rect.height() - 90) / 105))
    col = index // max_rows
    row = index % max_rows
    x = screen_rect.left() + 40 + col * 92
    y = screen_rect.top() + 40 + row * 105
    return float(x), float(y)


def get_random_desktop_dest():
    """Picks a random destination anywhere across the screen for fetched items."""
    min_x = screen_rect.left() + 140
    max_x = screen_rect.right() - CANVAS_SIZE - 140
    min_y = screen_rect.top() + 140
    max_y = screen_rect.bottom() - CANVAS_SIZE - 140
    return random.uniform(min_x, max_x), random.uniform(min_y, max_y)


class DesktopShortcutWidget(QLabel):
    """Visual draggable desktop shortcut widget that the dog fetches, drags across screen,
    and drops at random locations."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.active = False
        self.shortcut_name = ""
        self.shortcut_path = ""
        self.x = 0.0
        self.y = 0.0
        self.is_held = False

    def setup(self, name, path, x, y):
        self.shortcut_name = name
        self.shortcut_path = path
        self.x = float(x)
        self.y = float(y)
        self.is_held = False
        self.active = True
        badge = create_shortcut_badge(name, path)
        self.setPixmap(badge)
        self.resize(badge.size())
        self.move(round(self.x), round(self.y))
        self.show()
        self.raise_()

    def update_position(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.move(round(self.x), round(self.y))

    def drop(self, x, y):
        self.is_held = False
        self.update_position(x, y)
        self.show()
        self.raise_()

    def despawn(self):
        self.active = False
        self.is_held = False
        try:
            self.hide()
        except Exception:
            pass

    def destroy(self):
        self.despawn()
        try:
            self.clear()
            self.deleteLater()
        except Exception:
            pass

    def mouseDoubleClickEvent(self, event):
        if self.shortcut_path and os.path.exists(self.shortcut_path):
            try:
                os.startfile(self.shortcut_path)
            except Exception:
                pass
        super().mouseDoubleClickEvent(event)


# ============================================================
# SPOTIFY MUSIC DETECTION SERVICE
# ============================================================

_SPOTIFY_POWERSHELL_SCRIPT = """
$ProgressPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }[0]

Function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(600) | Out-Null
    return $netTask.Result
}

[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Control.GlobalSystemMediaTransportControlsSession,Windows.Media.Control,ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionPlaybackStatus,Windows.Media.Control,ContentType=WindowsRuntime] | Out-Null

$manager = $null
$lastState = ""

while ($true) {
    if ($manager -eq $null) {
        try {
            $asyncOp = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()
            $manager = Await $asyncOp ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])
        } catch {
            $manager = $null
        }
    }

    $playing = $false
    $track = ""

    if ($manager -ne $null) {
        try {
            $sessions = $manager.GetSessions()
            foreach ($s in $sessions) {
                $appId = $s.SourceAppUserModelId
                if ($appId -like '*Spotify*') {
                    $info = $s.GetPlaybackInfo()
                    if ($info -ne $null -and ([int]$info.PlaybackStatus -eq 4 -or $info.PlaybackStatus -eq 'Playing')) {
                        $playing = $true
                        try {
                            $mediaPropOp = $s.TryGetMediaPropertiesAsync()
                            $mediaProp = Await $mediaPropOp ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties])
                            if ($mediaProp -ne $null) {
                                $artist = $mediaProp.Artist
                                $title = $mediaProp.Title
                                if ($artist -and $title) {
                                    $track = "$artist - $title"
                                } elseif ($title) {
                                    $track = $title
                                } elseif ($artist) {
                                    $track = $artist
                                }
                            }
                        } catch {}
                        break
                    }
                }
            }
        } catch {
            $manager = $null
        }
    }

    if (-not $playing) {
        try {
            $spotProcs = Get-Process Spotify -ErrorAction SilentlyContinue | Where-Object {
                $_.MainWindowTitle -and $_.MainWindowTitle -notmatch '^(Spotify( Free| Premium)?|)$'
            }
            if ($spotProcs) {
                $playing = $true
                $track = $spotProcs[0].MainWindowTitle
            }
        } catch {}
    }

    $curState = if ($playing) { if ($track) { "PLAYING|$track" } else { "PLAYING" } } else { "STOPPED" }
    if ($curState -ne $lastState) {
        $lastState = $curState
        [Console]::WriteLine($curState)
        [Console]::Out.Flush()
    }
    Start-Sleep -Milliseconds 350
}
"""

class SpotifyMusicDetector:
    """Monitors Spotify music playback in real time on Windows using
    GlobalSystemMediaTransportControlsSessionManager and window title tracking.
    Runs entirely in a background daemon thread with zero CPU overhead."""

    def __init__(self):
        self.is_playing = False
        self.track_title = ""
        self.manual_override = None  # None: auto, True: forced on, False: forced off
        self._running = True
        self._process = None
        self._thread = threading.Thread(target=self._worker, daemon=True, name="SpotifyDetectorThread")
        self._thread.start()

    def _worker(self):
        encoded = base64.b64encode(_SPOTIFY_POWERSHELL_SCRIPT.encode("utf-16le")).decode("ascii")
        while self._running:
            try:
                self._process = subprocess.Popen(
                    [
                        "powershell",
                        "-NoProfile",
                        "-NonInteractive",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-EncodedCommand",
                        encoded,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                    creationflags=0x08000000 if sys.platform == "win32" else 0,
                )

                for raw_line in self._process.stdout:
                    if not self._running:
                        break
                    line = raw_line.strip()
                    if not line:
                        continue
                    if line.startswith("PLAYING"):
                        parts = line.split("|", 1)
                        self.is_playing = True
                        self.track_title = parts[1] if len(parts) > 1 else ""
                    elif line == "STOPPED":
                        self.is_playing = False
                        self.track_title = ""

                try:
                    self._process.wait(timeout=1.0)
                except Exception:
                    pass
            except Exception:
                pass

            if self._running:
                time.sleep(1.0)

    def is_music_playing(self):
        if self.manual_override is not None:
            return self.manual_override
        return self.is_playing

    def get_track_display(self):
        if self.manual_override is True and not self.track_title:
            return "Music Groove"
        return self.track_title if self.track_title else "Music Groove"

    def toggle_manual(self):
        current = self.is_music_playing()
        self.manual_override = not current
        print(f">>> SPOTIFY DANCE TOGGLED: {'ACTIVE' if self.manual_override else 'OFF'} <<<")
        return self.manual_override

    def stop(self):
        self._running = False
        if self._process:
            try:
                self._process.kill()
            except Exception:
                pass

spotify_detector = SpotifyMusicDetector()


# ============================================================
# SPOTIFY DANCING SYSTEM
# ============================================================

dance_active = False
dance_step_index = 0
dance_step_timer = 0.0
dance_facing = 1
dance_spin_active = False
dance_spin_angle = 0.0
dance_spin_end_time = 0.0
dance_notes = []
dance_last_note_time = 0.0
dance_target_x = 0.0
dance_target_y = 0.0
dance_target_end_time = 0.0
dance_speed = 7.2

NOTE_SYMBOLS = ["♪", "♫", "♬", "♩"]
NOTE_PALETTE = [
    QColor(244, 114, 182, 230),  # Rose Pink
    QColor(167, 139, 250, 230),  # Purple
    QColor(96, 165, 250, 230),   # Sky Blue
    QColor(52, 211, 153, 230),   # Mint Green
    QColor(251, 191, 36, 230),   # Gold Yellow
]

def spawn_dance_note():
    global dance_notes, dance_last_note_time
    now = time.monotonic()
    if now - dance_last_note_time < 0.22:
        return
    dance_last_note_time = now

    note = {
        "x": CANVAS_SIZE / 2.0 + random.uniform(-45, 45),
        "y": 270.0 + random.uniform(-20, 10),
        "vx": random.uniform(-1.0, 1.0),
        "vy": -random.uniform(1.8, 2.8),
        "symbol": random.choice(NOTE_SYMBOLS),
        "color": random.choice(NOTE_PALETTE),
        "size": random.randint(16, 24),
        "alpha": 1.0,
        "sway_phase": random.uniform(0, math.tau),
    }
    dance_notes.append(note)

def update_dance_notes():
    global dance_notes
    keep = []
    for n in dance_notes:
        n["y"] += n["vy"]
        n["sway_phase"] += 0.08
        n["x"] += math.sin(n["sway_phase"]) * 0.7
        n["alpha"] -= 0.016
        if n["alpha"] > 0.05 and n["y"] > 60:
            keep.append(n)
    dance_notes = keep

def pick_dance_target():
    global dog_x, dog_y
    min_x = screen_rect.left() + 50
    max_x = screen_rect.right() - CANVAS_SIZE - 50
    min_y = screen_rect.top() + 50
    max_y = screen_rect.bottom() - CANVAS_SIZE - 50

    best_tx, best_ty = random.uniform(min_x, max_x), random.uniform(min_y, max_y)
    for _ in range(8):
        tx = random.uniform(min_x, max_x)
        ty = random.uniform(min_y, max_y)
        dist = math.hypot(tx - dog_x, ty - dog_y)
        if dist > 220:
            return tx, ty
    return best_tx, best_ty

def update_dance():
    global dance_active, dance_facing, dance_step_index, dance_step_timer
    global dance_spin_active, dance_spin_angle, dance_spin_end_time
    global dance_target_x, dance_target_y, dance_target_end_time, dance_speed
    global dog_x, dog_y, state

    dance_active = True
    state = "dancing"
    now = time.monotonic()

    # Step animation (cycles running dance poses at fast energetic beat ~128-140 BPM)
    dance_step_timer += (10.0 / FPS)
    while dance_step_timer >= 1.0:
        dance_step_timer -= 1.0
        dance_step_index = (dance_step_index + 1) % 10

    # Pick or update running target
    dist_to_target = math.hypot(dance_target_x - dog_x, dance_target_y - dog_y)
    if dist_to_target < 50.0 or now >= dance_target_end_time:
        dance_target_x, dance_target_y = pick_dance_target()
        dance_target_end_time = now + random.uniform(2.0, 4.0)
        dance_speed = random.uniform(6.5, 8.5)
        # 35% chance of a celebratory spin pirouette
        if random.random() < 0.35 and not dance_spin_active:
            dance_spin_active = True
            dance_spin_angle = 0.0
            dance_spin_end_time = now + 0.60

    # Spin rotation
    if dance_spin_active:
        dance_spin_angle = (dance_spin_angle + 26.0) % 360.0
        if now >= dance_spin_end_time:
            dance_spin_active = False
            dance_spin_angle = 0.0

    # Run everywhere movement
    dx = dance_target_x - dog_x
    dy = dance_target_y - dog_y
    dist = math.hypot(dx, dy)
    if dist > 1.0:
        nx = dx / dist
        ny = dy / dist
        # Add playful rhythmic zigzag sway
        sway = math.sin(now * 7.5) * 1.5
        dog_x += nx * dance_speed + (-ny) * sway
        dog_y += ny * dance_speed + (nx) * sway
        # Facing follows run direction
        if abs(dx) > 1.0:
            dance_facing = 1 if dx > 0 else -1

    # Keep safely within screen boundaries
    dog_x = max(screen_rect.left() + 20, min(dog_x, screen_rect.right() - CANVAS_SIZE - 20))
    dog_y = max(screen_rect.top() + 20, min(dog_y, screen_rect.bottom() - CANVAS_SIZE - 20))

    # Musical notes trail
    spawn_dance_note()
    update_dance_notes()

    # Muddy dog leaves footprint trails while running everywhere
    if muddy_active and 'record_muddy_footprints' in globals():
        record_muddy_footprints()


def get_dance_pixmap():
    global dance_notes, dance_facing, dance_step_index, dance_spin_active, dance_spin_angle
    now = time.monotonic()

    # Base frame: Energetic running / breakdance frames
    if muddy_active:
        if dance_spin_active:
            base_frame = mud_roll_frames[dance_step_index % len(mud_roll_frames)]
        else:
            base_frame = mud_run_frames[dance_step_index % len(mud_run_frames)]
    else:
        base_frame = run_frames[dance_step_index % len(run_frames)]

    # Beat squash & stretch (~128 BPM, ~2.15 Hz)
    beat_phase = (now * 2.15) % 1.0
    bounce_hop = -abs(math.sin(beat_phase * math.pi)) * 16.0
    squash_x = 1.0 + 0.12 * math.sin(beat_phase * math.pi)
    squash_y = 1.0 - 0.10 * math.sin(beat_phase * math.pi)

    # Groovy tilt
    tilt_deg = math.sin(now * 8.0) * 12.0
    if dance_spin_active:
        tilt_deg = dance_spin_angle

    canvas = QPixmap(CANVAS_SIZE, CANVAS_SIZE)
    canvas.fill(Qt.transparent)

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    # Center of dog body on canvas
    cx = CANVAS_SIZE / 2.0
    cy = CANVAS_SIZE - 65.0 + bounce_hop

    tr = QTransform()
    tr.translate(cx, cy)
    tr.rotate(tilt_deg)
    tr.scale(dance_facing * squash_x, squash_y)
    tr.translate(-CANVAS_SIZE / 2.0, -(CANVAS_SIZE - 65.0))

    # Draw base dog frame
    painter.setTransform(tr)
    painter.drawPixmap(0, 0, base_frame)

    # Draw floating musical notes in upright canvas coordinates
    painter.resetTransform()
    for n in dance_notes:
        font = QFont("Segoe UI Symbol", n["size"], QFont.Bold)
        painter.setFont(font)
        col = QColor(n["color"])
        col.setAlphaF(max(0.0, min(1.0, n["alpha"])))
        painter.setPen(col)
        painter.drawText(round(n["x"]), round(n["y"]), n["symbol"])

    painter.end()
    return canvas


def update_dance_display():
    dog.resize(CANVAS_SIZE, CANVAS_SIZE)
    dog.move(round(dog_x), round(dog_y))
    dog.setPixmap(get_dance_pixmap())
    dog.show()
    dog.raise_()


# ============================================================
# OPERATING MODE CONTROLLER
# ============================================================

class ModeController:
    """Manages operating modes: Interactive and Free.
    In Free Mode:
      - Normal (clean) dog runs INFREQUENTLY (~2-4%), mostly walking, sitting, sleeping, chasing cat, or playing with balls.
      - Muddy dog runs FREQUENTLY (~60%), zooming around splashing muddy footprints everywhere.
      - Dog chases the cat companion and plays with bouncy, rolling balls.
    Handles mode transitions and autonomous behavior."""

    def __init__(self):
        self.current_mode = MODE_INTERACTIVE
        self.mode_start_time = time.monotonic()

        # Free mode autonomous state
        self.free_substate = "idle"
        self.free_substate_end_time = 0.0
        self.free_target_x = 0.0
        self.free_target_y = 0.0

        # Toys / companions for Free Mode
        self.cat = FreeCatCompanion()
        self.balls = [FreeBallToy("tennis"), FreeBallToy("red")]

        # Fetch Mode state & widget
        self.fetch_widget = DesktopShortcutWidget()
        self.fetch_state = "idle"  # "idle", "running_to_shortcut", "grabbing", "dragging", "delivering"
        self.fetch_target_shortcut = None
        self.fetch_origin_x = 0.0
        self.fetch_origin_y = 0.0
        self.fetch_dest_x = 0.0
        self.fetch_dest_y = 0.0
        self.fetch_timer = 0.0
        self.fetch_drag_speed = 6.5

    def set_mode(self, new_mode):
        if self.current_mode == new_mode:
            return

        print()
        print(f">>> SWITCHING MODE: {self.current_mode} -> {new_mode} <<<")
        print()

        self.stop_current_mode()
        self.current_mode = new_mode
        self.mode_start_time = time.monotonic()

        if new_mode == MODE_INTERACTIVE:
            self.start_interactive_mode()
        elif new_mode == MODE_FREE:
            self.start_free_mode()
        elif new_mode == MODE_FETCH:
            self.start_fetch_mode()

        update_food_timer_display()

    def despawn_toys(self):
        self.cat.despawn()
        for b in self.balls:
            b.despawn()
        self.fetch_widget.despawn()

    def stop_current_mode(self):
        global was_running
        self.despawn_toys()
        self.fetch_state = "idle"
        was_running = False

    def destroy(self):
        self.despawn_toys()
        self.cat.destroy()
        for b in self.balls:
            b.destroy()
        self.fetch_widget.destroy()

    def start_interactive_mode(self):
        global state
        self.despawn_toys()
        state = "mud" if muddy_active else "idle"

    def start_free_mode(self):
        self.despawn_toys()
        self.enter_free_substate("idle", duration=1.5)

    def start_fetch_mode(self):
        global state
        self.despawn_toys()
        self.fetch_state = "idle"
        state = "mud" if muddy_active else "sitting"
        print(">>> FETCH MODE ACTIVATED! Press [SPACE], [3], or [G] to send dog to fetch a desktop shortcut! <<<")

    def check_mode_expiration(self):
        now = time.monotonic()
        elapsed = now - self.mode_start_time

        if self.current_mode == MODE_FREE and FREE_MODE_DURATION > 0:
            if elapsed >= FREE_MODE_DURATION:
                print(">>> Free Mode duration expired. Reverting to Interactive Mode. <<<")
                self.set_mode(MODE_INTERACTIVE)

        elif self.current_mode == MODE_FETCH and FETCH_MODE_DURATION > 0:
            if elapsed >= FETCH_MODE_DURATION:
                print(">>> Fetch Mode duration expired. Reverting to Interactive Mode. <<<")
                self.set_mode(MODE_INTERACTIVE)

        elif self.current_mode == MODE_INTERACTIVE and INTERACTIVE_MODE_DURATION > 0:
            if elapsed >= INTERACTIVE_MODE_DURATION:
                self.mode_start_time = now

    def pick_free_target(self, min_dist=120, max_dist=380):
        global dog_x, dog_y
        min_x = screen_rect.left() + 70
        max_x = screen_rect.right() - CANVAS_SIZE - 70
        min_y = screen_rect.top() + 70
        max_y = screen_rect.bottom() - CANVAS_SIZE - 70

        angle = random.uniform(0, math.tau)
        if dog_x < min_x + 80:
            angle = random.uniform(-math.pi / 2.5, math.pi / 2.5)
        elif dog_x > max_x - 80:
            angle = random.uniform(math.pi / 2.5, 3 * math.pi / 2.5)

        dist = random.uniform(min_dist, max_dist)
        tx = dog_x + math.cos(angle) * dist
        ty = dog_y + math.sin(angle) * dist

        tx = max(min_x, min(tx, max_x))
        ty = max(min_y, min(ty, max_y))
        return tx, ty

    def enter_free_substate(self, substate, duration=None):
        global state, facing
        now = time.monotonic()
        self.free_substate = substate

        # Despawn previous toys if not remaining in that substate
        if substate != "chase_cat":
            self.cat.despawn()
        if substate != "play_ball":
            for b in self.balls:
                b.despawn()

        if substate == "idle":
            dur = duration if duration is not None else random.uniform(1.8, 3.8)
            self.free_substate_end_time = now + dur
            state = "mud" if muddy_active else "sitting"

        elif substate == "sleep":
            dur = duration if duration is not None else random.uniform(3.0, 5.5)
            self.free_substate_end_time = now + dur
            state = "sleeping"

        elif substate == "walk":
            dur = duration if duration is not None else random.uniform(2.5, 5.0)
            self.free_substate_end_time = now + dur
            self.free_target_x, self.free_target_y = self.pick_free_target(120, 320)
            state = "mud_walk" if muddy_active else "walk"

        elif substate == "run":
            dur = duration if duration is not None else random.uniform(1.8, 3.2)
            self.free_substate_end_time = now + dur
            self.free_target_x, self.free_target_y = self.pick_free_target(220, 480)
            state = "mud_run" if muddy_active else "run"

        elif substate == "chase_cat":
            dur = duration if duration is not None else random.uniform(6.5, 10.0)
            self.free_substate_end_time = now + dur
            dog_cx = dog_x + 200.0
            dog_cy = dog_y + 335.0
            spawn_x = dog_cx + random.choice([-1, 1]) * random.uniform(180, 300)
            spawn_y = dog_cy + random.uniform(-60, 60)
            self.cat.spawn(spawn_x, spawn_y)
            state = "mud_run" if muddy_active else "run"
            if 'play_bark_sound' in globals():
                play_bark_sound()

        elif substate == "play_ball":
            dur = duration if duration is not None else random.uniform(7.0, 11.0)
            self.free_substate_end_time = now + dur
            dog_cx = dog_x + 200.0
            dog_cy = dog_y + 335.0
            # Spawn tennis ball
            self.balls[0].spawn(
                dog_cx + facing * 85.0,
                dog_cy - 40.0,
                vx=facing * random.uniform(4.5, 7.5),
                vy=-random.uniform(6.0, 10.0)
            )
            # Spawn red ball
            self.balls[1].spawn(
                dog_cx - facing * 95.0,
                dog_cy - 50.0,
                vx=-facing * random.uniform(4.0, 7.0),
                vy=-random.uniform(7.0, 11.0)
            )
            state = "mud_run" if muddy_active else "run"
            if 'play_bark_sound' in globals():
                play_bark_sound()

        elif substate == "special":
            if muddy_active:
                start_mud_roll()
                self.free_substate_end_time = now + 1.2
            else:
                if 'play_bark_sound' in globals():
                    play_bark_sound()
                self.free_substate_end_time = now + 1.0

    def update(self):
        self.check_mode_expiration()

        if hunger_rage_active or eating_active or cleaning_active or ssj_active or tornado_active:
            self.despawn_toys()
            return

        if 'spotify_detector' in globals() and spotify_detector.is_music_playing():
            self.despawn_toys()
            update_dance()
            update_dance_display()
            return

        global dance_active, dance_notes
        if dance_active:
            dance_active = False
            dance_notes.clear()

        if self.current_mode == MODE_FREE:
            self.update_free_behavior()
        elif self.current_mode == MODE_FETCH:
            self.update_fetch_behavior()

    def update_free_behavior(self):
        global dog_x, dog_y, facing, state
        now = time.monotonic()

        if mud_roll_playing:
            return

        # Substate expiration and weighted selection
        if now >= self.free_substate_end_time:
            if muddy_active:
                # Muddy dog runs frequently! (~60% running chance)
                if self.free_substate == "idle":
                    next_st = random.choices(["run", "play_ball", "chase_cat", "walk", "special"], weights=[60, 15, 12, 8, 5])[0]
                elif self.free_substate == "run":
                    next_st = random.choices(["run", "play_ball", "chase_cat", "walk", "idle"], weights=[55, 18, 15, 7, 5])[0]
                elif self.free_substate == "walk":
                    next_st = random.choices(["run", "play_ball", "chase_cat", "idle"], weights=[65, 15, 12, 8])[0]
                elif self.free_substate == "chase_cat":
                    next_st = random.choices(["run", "play_ball", "idle"], weights=[60, 20, 20])[0]
                elif self.free_substate == "play_ball":
                    next_st = random.choices(["run", "chase_cat", "idle"], weights=[60, 20, 20])[0]
                else:
                    next_st = random.choices(["run", "play_ball", "chase_cat"], weights=[70, 15, 15])[0]
            else:
                # Normal clean dog runs INFREQUENTLY! (~2-4%), mostly walking, sleeping, ball, cat, idle
                if self.free_substate == "sleep":
                    next_st = random.choices(["idle", "walk", "play_ball", "chase_cat"], weights=[70, 20, 5, 5])[0]
                elif self.free_substate == "idle":
                    next_st = random.choices(["walk", "sleep", "play_ball", "chase_cat", "special", "run"], weights=[42, 22, 16, 14, 4, 2])[0]
                elif self.free_substate == "walk":
                    next_st = random.choices(["idle", "sleep", "play_ball", "chase_cat", "walk", "run"], weights=[45, 18, 18, 15, 2, 2])[0]
                elif self.free_substate == "run":
                    next_st = random.choices(["idle", "walk"], weights=[60, 40])[0]
                elif self.free_substate == "chase_cat":
                    next_st = random.choices(["idle", "walk", "play_ball"], weights=[45, 35, 20])[0]
                elif self.free_substate == "play_ball":
                    next_st = random.choices(["idle", "walk", "sleep"], weights=[45, 35, 20])[0]
                else:
                    next_st = random.choices(["idle", "walk"], weights=[60, 40])[0]

            self.enter_free_substate(next_st)

        dog_cx = dog_x + 200.0
        dog_cy = dog_y + 335.0

        # Substate 1: Chase Cat
        if self.free_substate == "chase_cat":
            if not self.cat.active:
                self.cat.spawn(dog_cx + 200.0, dog_cy)
            self.cat.update(dog_cx, dog_cy)

            # Dog pursues cat
            target_cx = self.cat.x + self.cat.WIDTH / 2.0
            target_cy = self.cat.y + self.cat.HEIGHT / 2.0
            tx = target_cx - 200.0
            ty = target_cy - 335.0

            dx = tx - dog_x
            dy = ty - dog_y
            dist = math.hypot(dx, dy)

            if dist > 8:
                nx = dx / max(1e-5, dist)
                ny = dy / max(1e-5, dist)
                if abs(dx) > 2:
                    facing = 1 if dx > 0 else -1
                speed = MAX_RUN_SPEED
                dog_x += nx * speed
                dog_y += ny * speed
                dog_x = max(screen_rect.left(), min(dog_x, screen_rect.right() - CANVAS_SIZE))
                dog_y = max(screen_rect.top(), min(dog_y, screen_rect.bottom() - CANVAS_SIZE))

            state = "mud_run" if muddy_active else "run"
            if muddy_active:
                record_muddy_footprints()

        # Substate 2: Play with Balls
        elif self.free_substate == "play_ball":
            for b in self.balls:
                if b.active:
                    b.update(dog_cx, dog_cy)

            active_balls = [b for b in self.balls if b.active]
            if not active_balls:
                self.enter_free_substate("idle", duration=random.uniform(1.5, 3.0))
                return

            # Target the nearest active ball
            target_ball = min(
                active_balls,
                key=lambda b: math.hypot((b.x + b.SIZE / 2.0) - dog_cx, (b.y + b.SIZE / 2.0) - dog_cy)
            )
            bcx = target_ball.x + target_ball.SIZE / 2.0
            bcy = target_ball.y + target_ball.SIZE / 2.0
            tx = bcx - 200.0
            ty = bcy - 335.0

            dx = tx - dog_x
            dy = ty - dog_y
            dist = math.hypot(dx, dy)

            if dist > 10:
                nx = dx / max(1e-5, dist)
                ny = dy / max(1e-5, dist)
                if abs(dx) > 2:
                    facing = 1 if dx > 0 else -1
                if muddy_active:
                    speed = MAX_RUN_SPEED
                    state = "mud_run"
                else:
                    speed = MAX_RUN_SPEED if dist > 140 else (MAX_WALK_SPEED + 0.8)
                    state = "run" if dist > 140 else "walk"

                dog_x += nx * speed
                dog_y += ny * speed
                dog_x = max(screen_rect.left(), min(dog_x, screen_rect.right() - CANVAS_SIZE))
                dog_y = max(screen_rect.top(), min(dog_y, screen_rect.bottom() - CANVAS_SIZE))

            if muddy_active:
                record_muddy_footprints()

        # Substate 3: Walk or Run toward waypoint
        elif self.free_substate in ("walk", "run"):
            dx = self.free_target_x - dog_x
            dy = self.free_target_y - dog_y
            dist = math.hypot(dx, dy)

            if dist < 18:
                self.enter_free_substate("idle", duration=random.uniform(1.5, 3.0))
                return

            speed = MAX_RUN_SPEED if self.free_substate == "run" else MAX_WALK_SPEED
            nx = dx / dist
            ny = dy / dist

            if abs(dx) > 2:
                facing = 1 if dx > 0 else -1

            dog_x += nx * speed
            dog_y += ny * speed

            dog_x = max(screen_rect.left(), min(dog_x, screen_rect.right() - CANVAS_SIZE))
            dog_y = max(screen_rect.top(), min(dog_y, screen_rect.bottom() - CANVAS_SIZE))

            if self.free_substate == "run":
                state = "mud_run" if muddy_active else "run"
            else:
                state = "mud_walk" if muddy_active else "walk"

            if muddy_active:
                record_muddy_footprints()

    def trigger_fetch(self):
        """Initiates a fetch sequence: scans desktop shortcuts, picks a random one,
        and commands the dog to run to it, pick it up, and drag it across the screen."""
        if self.current_mode != MODE_FETCH:
            self.set_mode(MODE_FETCH)

        if self.fetch_state in ("running_to_shortcut", "grabbing", "dragging"):
            # Already actively fetching an item
            return

        shortcuts = scan_desktop_shortcuts()
        if not shortcuts:
            return

        idx = random.randrange(len(shortcuts))
        shortcut = shortcuts[idx]
        self.fetch_target_shortcut = shortcut

        origin_x, origin_y = get_shortcut_desktop_pos(idx, len(shortcuts))
        dest_x, dest_y = get_random_desktop_dest()

        self.fetch_origin_x = origin_x
        self.fetch_origin_y = origin_y
        self.fetch_dest_x = dest_x
        self.fetch_dest_y = dest_y

        self.fetch_widget.setup(shortcut["name"], shortcut["path"], origin_x, origin_y)
        self.fetch_state = "running_to_shortcut"
        self.fetch_timer = time.monotonic()

        if 'play_bark_sound' in globals():
            play_bark_sound()

        print()
        print(f">>> FETCH: Running to grab '{shortcut['name']}' at ({origin_x:.0f}, {origin_y:.0f}) and drag to ({dest_x:.0f}, {dest_y:.0f})! <<<")
        print()
        update_food_timer_display()

    def update_fetch_behavior(self):
        """State machine for Fetch Mode:
        1. 'running_to_shortcut': Dog sprints to the desktop shortcut location.
        2. 'grabbing': Dog bites/picks up the shortcut into its mouth.
        3. 'dragging': Dog drags the shortcut across the screen to a random desktop location.
        4. 'delivering': Dog drops the shortcut, barks/celebrates, and sits proudly."""
        global dog_x, dog_y, facing, state
        now = time.monotonic()

        if mud_roll_playing:
            return

        if self.fetch_state == "running_to_shortcut":
            target_cx = self.fetch_origin_x + 36.0
            target_cy = self.fetch_origin_y + 46.0

            # Desired dog top-left so dog mouth reaches the icon
            tx = target_cx - 200.0 - facing * 25.0
            ty = target_cy - 260.0

            dx = tx - dog_x
            dy = ty - dog_y
            dist = math.hypot(dx, dy)

            if dist > 20.0 and (now - self.fetch_timer) < 14.0:
                nx = dx / max(1e-5, dist)
                ny = dy / max(1e-5, dist)
                if abs(dx) > 3.0:
                    facing = 1 if dx > 0 else -1
                speed = MAX_RUN_SPEED
                dog_x += nx * speed
                dog_y += ny * speed
                dog_x = max(screen_rect.left(), min(dog_x, screen_rect.right() - CANVAS_SIZE))
                dog_y = max(screen_rect.top(), min(dog_y, screen_rect.bottom() - CANVAS_SIZE))
                state = "mud_run" if muddy_active else "run"
                if muddy_active:
                    record_muddy_footprints()
            else:
                # Reached shortcut! Grab it!
                self.fetch_state = "grabbing"
                self.fetch_timer = now + 0.45
                state = "mud" if muddy_active else "sitting"
                self.fetch_widget.is_held = True
                dog_cx = dog_x + 200.0
                dog_cy = dog_y + 335.0
                self.fetch_widget.update_position(
                    dog_cx + facing * 25.0 - 36.0,
                    dog_cy - 75.0
                )
                if 'play_bark_sound' in globals():
                    play_bark_sound()
                update_food_timer_display()

        elif self.fetch_state == "grabbing":
            dog_cx = dog_x + 200.0
            dog_cy = dog_y + 335.0
            self.fetch_widget.update_position(
                dog_cx + facing * 25.0 - 36.0,
                dog_cy - 75.0
            )
            state = "mud" if muddy_active else "sitting"
            if now >= self.fetch_timer:
                self.fetch_state = "dragging"
                self.fetch_timer = now
                if 'play_bark_sound' in globals():
                    play_bark_sound()
                update_food_timer_display()

        elif self.fetch_state == "dragging":
            target_cx = self.fetch_dest_x + 36.0
            target_cy = self.fetch_dest_y + 46.0

            tx = target_cx - 200.0 - facing * 25.0
            ty = target_cy - 260.0

            dx = tx - dog_x
            dy = ty - dog_y
            dist = math.hypot(dx, dy)

            if dist > 20.0 and (now - self.fetch_timer) < 20.0:
                nx = dx / max(1e-5, dist)
                ny = dy / max(1e-5, dist)
                if abs(dx) > 3.0:
                    facing = 1 if dx > 0 else -1
                speed = self.fetch_drag_speed
                dog_x += nx * speed
                dog_y += ny * speed
                dog_x = max(screen_rect.left(), min(dog_x, screen_rect.right() - CANVAS_SIZE))
                dog_y = max(screen_rect.top(), min(dog_y, screen_rect.bottom() - CANVAS_SIZE))
                state = "mud_run" if muddy_active else "run"
                if muddy_active:
                    record_muddy_footprints()

                # Carry shortcut clamped to dog mouth with cute running bob
                bob = math.sin(now * 15.0) * 3.0
                dog_cx = dog_x + 200.0
                dog_cy = dog_y + 335.0
                self.fetch_widget.update_position(
                    dog_cx + facing * 25.0 - 36.0,
                    dog_cy - 75.0 + bob
                )
            else:
                # Successfully dragged to destination! Drop it!
                self.fetch_state = "delivering"
                self.fetch_timer = now + 1.2
                self.fetch_widget.drop(self.fetch_dest_x, self.fetch_dest_y)
                state = "mud" if muddy_active else "sitting"
                if 'play_bark_sound' in globals():
                    play_bark_sound()
                print()
                print(f">>> FETCH: Successfully delivered '{self.fetch_target_shortcut['name']}'! <<<")
                print()
                update_food_timer_display()

        elif self.fetch_state == "delivering":
            state = "mud" if muddy_active else "sitting"
            if now >= self.fetch_timer:
                self.fetch_state = "idle"
                update_food_timer_display()

        elif self.fetch_state == "idle":
            if state not in ("sitting", "sleeping", "walk", "mud", "mud_walk"):
                state = "mud" if muddy_active else "sitting"


mode_controller = ModeController()


def queue_mode_command(cmd):
    global mud_command
    mud_command = cmd


# ============================================================
# KEYBOARD
# ============================================================

def kill_dog():

    global kill_requested

    kill_requested = True


keyboard_listener = keyboard.GlobalHotKeys({

    "<ctrl>+<shift>+q": kill_dog,
    "<ctrl>+1": lambda: queue_mode_command("mode_interactive"),
    "<ctrl>+2": lambda: queue_mode_command("mode_free"),
    "<ctrl>+3": lambda: queue_mode_command("mode_fetch"),
    "<ctrl>+g": lambda: queue_mode_command("fetch_shortcut"),
    "<ctrl>+k": lambda: queue_mode_command("chase_cat"),
    "<ctrl>+b": lambda: queue_mode_command("play_ball"),
    "<ctrl>+d": lambda: queue_mode_command("toggle_dance"),

})

keyboard_listener.start()


def mud_key_handler(key):

    global mud_command

    # If screen time break is currently active, any key press resumes
    if 'break_active' in globals() and break_active:
        mud_command = "resume_break"
        return

    # In Fetch Mode, pressing Space, Enter, or any key triggers fetch
    if 'mode_controller' in globals() and mode_controller and mode_controller.current_mode == MODE_FETCH:
        if key in (keyboard.Key.space, keyboard.Key.enter):
            mud_command = "fetch_shortcut"
            return

    try:
        char = key.char
    except AttributeError:
        if 'mode_controller' in globals() and mode_controller and mode_controller.current_mode == MODE_FETCH:
            mud_command = "fetch_shortcut"
        return

    if not char:
        if 'mode_controller' in globals() and mode_controller and mode_controller.current_mode == MODE_FETCH:
            mud_command = "fetch_shortcut"
        return

    char = char.lower()

    if char == "m":
        mud_command = "mud"

    elif char == "c":
        mud_command = "clean"

    elif char == "f":
        mud_command = "feed"

    elif char == "1":
        mud_command = "mode_interactive"

    elif char == "2":
        mud_command = "mode_free"

    elif char == "3":
        if 'mode_controller' in globals() and mode_controller and mode_controller.current_mode == MODE_FETCH:
            mud_command = "fetch_shortcut"
        else:
            mud_command = "mode_fetch"

    elif char == "k":
        mud_command = "chase_cat"

    elif char == "b":
        mud_command = "play_ball"

    elif char == "d":
        mud_command = "toggle_dance"

    elif char == "g":
        mud_command = "fetch_shortcut"

    else:
        # Any other key clicked in Fetch Mode triggers fetch!
        if 'mode_controller' in globals() and mode_controller and mode_controller.current_mode == MODE_FETCH:
            mud_command = "fetch_shortcut"


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

    elif button == mouse.Button.left and pressed:
        if 'mode_controller' in globals() and mode_controller and mode_controller.current_mode == MODE_FETCH:
            if cursor_over_dog():
                queue_mode_command("fetch_shortcut")


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
# HUNGER-RAGE SSJ FRAME
# ============================================================

def get_hunger_ssj():

    frame = hunger_ssj_frames[
        hunger_ssj_index
    ]

    width = int(
        frame.width()
        * hunger_ssj_scale
    )

    height = int(
        frame.height()
        * hunger_ssj_scale
    )

    width = max(1, width)
    height = max(1, height)

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
# UPDATE HUNGER-RAGE SSJ ANIMATION
# ============================================================

def update_hunger_ssj():

    global hunger_ssj_index
    global hunger_ssj_timer
    global hunger_ssj_scale

    hunger_ssj_timer += (
        HUNGER_SSJ_FPS / FPS
    )

    while hunger_ssj_timer >= 1:

        hunger_ssj_timer -= 1

        if hunger_ssj_index < HUNGER_SSJ_FRAME_COUNT - 1:
            hunger_ssj_index += 1
        else:
            # Hold the final powered frames.
            hunger_ssj_index = HUNGER_SSJ_FRAME_COUNT - 2

    if hunger_ssj_scale < HUNGER_SSJ_MAX_SCALE:

        hunger_ssj_scale = min(
            HUNGER_SSJ_MAX_SCALE,
            hunger_ssj_scale
            + HUNGER_SSJ_GROWTH_SPEED
        )


# ============================================================
# DISPLAY HUNGER-RAGE SSJ
# ============================================================

def update_hunger_ssj_display():

    if not hunger_rage_active:
        return

    pixmap = get_hunger_ssj()

    dog.setPixmap(
        pixmap
    )

    dog.resize(
        pixmap.size()
    )

    # Keep the enlarged front-facing dog centered on the same
    # logical dog position used by the original SSJ mode.
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
    dog.raise_()


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

    # During hunger rage, shake the entire frozen desktop overlay!
    if hunger_rage_active:
        hunger_overlay.set_shake_offset(offset_x, offset_y)

    if (
        shake_window is not None
        and sys.platform == "win32"
    ):

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

    hunger_overlay.set_shake_offset(0, 0)

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

    play_ssj_sound()


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

    stop_ssj_sound()

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


# ============================================================
# EATING FRAME
# ============================================================

def get_eating():

    frame = eating_frames[
        eating_index
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

    if 'mode_controller' in globals() and mode_controller:
        mode_controller.despawn_toys()

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

    # The cleaning artwork is drawn facing right. Keep the dog
    # facing the same direction it was facing before cleaning.
    # Flip the complete transparent cleaning frame when the dog
    # was facing left.
    if facing == -1:
        pixmap = flip(pixmap)

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
# FEEDING / EATING SYSTEM
# ============================================================

def update_food_timer_display():

    now = time.monotonic()

    if 'break_active' in globals() and break_active:
        return

    mode_name = mode_controller.current_mode if 'mode_controller' in globals() and mode_controller else MODE_INTERACTIVE

    mode_text = f"Mode: {mode_name}"
    if mode_name == MODE_FREE and FREE_MODE_DURATION > 0 and 'mode_controller' in globals() and mode_controller:
        rem_mode = max(0, int(FREE_MODE_DURATION - (now - mode_controller.mode_start_time)))
        mins, secs = divmod(rem_mode, 60)
        mode_text += f" [{mins:02d}:{secs:02d}]"
    elif mode_name == MODE_FETCH and FETCH_MODE_DURATION > 0 and 'mode_controller' in globals() and mode_controller:
        rem_mode = max(0, int(FETCH_MODE_DURATION - (now - mode_controller.mode_start_time)))
        mins, secs = divmod(rem_mode, 60)
        mode_text += f" [{mins:02d}:{secs:02d}]"
        if mode_controller.fetch_state == "running_to_shortcut" and mode_controller.fetch_target_shortcut:
            mode_text += f" | 🐾 Fetching '{mode_controller.fetch_target_shortcut['name']}'..."
        elif mode_controller.fetch_state == "grabbing" and mode_controller.fetch_target_shortcut:
            mode_text += f" | 🦷 Grabbing '{mode_controller.fetch_target_shortcut['name']}'!"
        elif mode_controller.fetch_state == "dragging" and mode_controller.fetch_target_shortcut:
            mode_text += f" | 🐕 Dragging '{mode_controller.fetch_target_shortcut['name']}'!"
        elif mode_controller.fetch_state == "delivering" and mode_controller.fetch_target_shortcut:
            mode_text += f" | 🎉 Delivered '{mode_controller.fetch_target_shortcut['name']}'!"
        else:
            mode_text += " | 🎾 Press [SPACE] or [3] to Fetch!"
    elif mode_name == MODE_INTERACTIVE and INTERACTIVE_MODE_DURATION > 0 and 'mode_controller' in globals() and mode_controller:
        rem_mode = max(0, int(INTERACTIVE_MODE_DURATION - (now - mode_controller.mode_start_time)))
        mins, secs = divmod(rem_mode, 60)
        mode_text += f" [{mins:02d}:{secs:02d}]"

    if 'spotify_detector' in globals() and spotify_detector.is_music_playing():
        mode_text += f" | 🎵 {spotify_detector.get_track_display()}"
        food_timer_label.setText(
            f"{mode_text} | 🎵 Party Groove (Break Paused) | 🍗 Feed (F)"
        )
        food_timer_label.adjustSize()
        food_timer_label.move(
            screen_rect.left() + 20,
            screen_rect.top() + 20
        )
        food_timer_label.show()
        food_timer_label.raise_()
        return

    rem_break = max(0, int(SCREEN_TIME_LIMIT - (now - screen_time_start)))
    break_text = f"☕ Break: {rem_break}s"

    if feeding_active:
        food_timer_label.setText(
            f"{mode_text} | 🍖 Eating..."
        )
    else:
        food_timer_label.setText(
            f"{mode_text} | {break_text} | 🍖 Feed dog (F)"
        )

    food_timer_label.adjustSize()

    food_timer_label.move(
        screen_rect.left() + 20,
        screen_rect.top() + 20
    )

    food_timer_label.show()
    food_timer_label.raise_()


def start_feeding():

    global feeding_active
    global eating_active
    global eating_index
    global eating_timer
    global food_deadline
    global state

    if feeding_active or eating_active:
        return

    if hunger_rage_active:
        return

    if cleaning_active or tornado_active or ssj_active:
        return

    # Reset hunger immediately when F is pressed.
    food_deadline = (
        time.monotonic()
        + FEED_INTERVAL
    )

    feeding_active = True
    eating_active = True
    eating_index = 0
    eating_timer = 0.0
    state = "eating"

    # Stop movement while the dog eats.
    dog.show()
    dog.raise_()

    # Display frame 1 immediately.
    update_eating_display()

    if 'mode_controller' in globals() and mode_controller:
        mode_controller.despawn_toys()

    print()
    print(">>> DOG STARTED EATING <<<")
    print()


def update_eating():

    global feeding_active
    global eating_active
    global eating_index
    global eating_timer
    global state

    if not eating_active:
        return

    eating_timer += (
        EATING_FPS / FPS
    )

    while eating_timer >= 1:

        eating_timer -= 1
        eating_index += 1

        if eating_index >= EATING_FRAME_COUNT:
            finish_eating()
            return


def update_eating_display():

    if not eating_active:
        return

    pixmap = get_eating()

    dog.resize(
        CANVAS_SIZE,
        CANVAS_SIZE
    )

    dog.setPixmap(
        pixmap
    )

    # The prepared eating frame uses the same 400x400 canvas and
    # baseline as the normal dog, so the dog's feet stay anchored.
    dog.move(
        round(dog_x),
        round(dog_y)
    )

    dog.show()
    dog.raise_()


def finish_eating():

    global feeding_active
    global eating_active
    global eating_index
    global eating_timer
    global state

    if not eating_active:
        return

    feeding_active = False
    eating_active = False
    eating_index = 0
    eating_timer = 0.0

    # Let the normal movement system choose walk/run/sit/sleep again
    # on the next update. Mud remains mud when applicable.
    state = "mud" if muddy_active else "idle"

    if 'mode_controller' in globals() and mode_controller:
        if mode_controller.current_mode == MODE_FREE:
            mode_controller.enter_free_substate("idle", duration=1.0)

    print()
    print(">>> DOG FINISHED EATING <<<")
    print()


def start_hunger_rage():

    global hunger_rage_active
    global hunger_rage_end_time
    global food_deadline
    global hunger_rage_pending
    global hunger_ssj_index
    global hunger_ssj_timer
    global hunger_ssj_scale
    global state
    global eating_active
    global feeding_active

    if hunger_rage_active:
        return

    # No hunger rage while Spotify music is playing
    if 'spotify_detector' in globals() and spotify_detector.is_music_playing():
        return

    if cleaning_active or tornado_active:

        hunger_rage_pending = True
        return

    hunger_rage_pending = False

    hunger_rage_active = True

    hunger_rage_end_time = (
        time.monotonic()
        + HUNGER_RAGE_DURATION
    )

    # Give the dog another deadline after the rage finishes.
    food_deadline = (
        time.monotonic()
        + FEED_INTERVAL
    )

    # Cancel eating cleanly if the timer expires at the same moment.
    if eating_active:
        eating_active = False

    if feeding_active:
        feeding_active = False

    # Start the dedicated FRONT-FACING hunger-rage SSJ animation.
    # This is separate from the normal right-mouse SSJ mode.
    hunger_ssj_index = 0
    hunger_ssj_timer = 0.0
    hunger_ssj_scale = HUNGER_SSJ_START_SCALE
    state = "hunger_ssj"

    footprints_overlay.hide()

    if 'mode_controller' in globals() and mode_controller:
        mode_controller.despawn_toys()

    # Hide dog briefly so the screen grab captures the clean desktop
    dog.hide()
    QApplication.processEvents()

    # Capture the desktop screenshot for true window freeze
    hunger_overlay.capture_screen()
    hunger_overlay.show()
    hunger_overlay.raise_()

    # Display and raise the Super Saiyan dog on top of the frozen windows
    update_hunger_ssj_display()
    dog.show()
    dog.raise_()

    start_screen_shake()
    play_ssj_sound()
    food_timer_label.raise_()
    update_food_timer_display()

    print()
    print(">>> HUNGER RAGE: FEEDING TIMER EXPIRED — WINDOWS FROZEN (5s) <<<")
    print()


def update_hunger_rage():

    global hunger_rage_active
    global state
    global hunger_ssj_index
    global hunger_ssj_timer
    global hunger_ssj_scale

    if not hunger_rage_active:
        return

    update_hunger_ssj()
    update_hunger_ssj_display()
    update_screen_shake()

    # Ensure freeze overlay is below dog, and dog is on top!
    hunger_overlay.raise_()
    dog.raise_()
    food_timer_label.raise_()
    update_food_timer_display()

    if (
        time.monotonic()
        < hunger_rage_end_time
    ):
        return

    hunger_rage_active = False

    hunger_overlay.hide()

    stop_screen_shake()
    stop_ssj_sound()

    # Reset the dedicated hunger-rage SSJ state.
    hunger_ssj_index = 0
    hunger_ssj_timer = 0.0
    hunger_ssj_scale = HUNGER_SSJ_START_SCALE

    state = "mud" if muddy_active else "idle"

    if 'mode_controller' in globals() and mode_controller:
        if mode_controller.current_mode == MODE_FREE:
            mode_controller.enter_free_substate("idle", duration=1.5)

    if muddy_active:
        footprints_overlay.show()
        footprints_overlay.raise_()

    dog.resize(
        CANVAS_SIZE,
        CANVAS_SIZE
    )

    dog.move(
        round(dog_x),
        round(dog_y)
    )

    update_food_timer_display()

    print()
    print(">>> HUNGER RAGE ENDED <<<")
    print()


def check_food_timer():

    # Automatic hunger rage and window freezing have been disabled.
    return


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

    play_tornado_sound()

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

    stop_tornado_sound()

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

    if 'mode_controller' in globals() and mode_controller and mode_controller.current_mode != MODE_INTERACTIVE:
        return

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
# RUN BARKING SYSTEM
# ============================================================

def play_bark_sound():
    global bark_index

    if bark_sounds:
        sound = bark_sounds[bark_index % len(bark_sounds)]
        bark_index += 1
        try:
            sound.play()
            return
        except Exception:
            pass

    # Windows fallback
    if sys.platform == "win32" and winsound:
        try:
            sound_path = os.path.join(BASE_DIR, "assets", "sounds", "bark.wav")
            if os.path.exists(sound_path):
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass


def update_run_bark():
    global last_bark_time, next_bark_interval, was_running

    # Barking triggers only while actively running (clean run or mud_run)
    # and not during any special cutscene or minigame.
    is_running = (state in ("run", "mud_run")) and not (
        hunger_rage_active
        or eating_active
        or cleaning_active
        or ssj_active
        or tornado_active
    )

    if not is_running:
        was_running = False
        return

    now = time.monotonic()

    if not was_running:
        # Just entered running state: play first bark after a short natural delay (0.2s)
        was_running = True
        last_bark_time = now - (next_bark_interval - 0.20)
        return

    if now - last_bark_time >= next_bark_interval:
        last_bark_time = now
        next_bark_interval = random.uniform(
            RUN_BARK_INTERVAL_MIN,
            RUN_BARK_INTERVAL_MAX
        )
        play_bark_sound()


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

    elif command == "feed":

        # F feeds the dog and resets the hunger timer.
        start_feeding()

    elif command == "mode_interactive":
        mode_controller.set_mode(MODE_INTERACTIVE)

    elif command == "mode_free":
        mode_controller.set_mode(MODE_FREE)

    elif command == "mode_fetch":
        mode_controller.set_mode(MODE_FETCH)

    elif command == "fetch_shortcut":
        if mode_controller.current_mode != MODE_FETCH:
            mode_controller.set_mode(MODE_FETCH)
        mode_controller.trigger_fetch()

    elif command == "chase_cat":
        if mode_controller.current_mode != MODE_FREE:
            mode_controller.set_mode(MODE_FREE)
        mode_controller.enter_free_substate("chase_cat")

    elif command == "play_ball":
        if mode_controller.current_mode != MODE_FREE:
            mode_controller.set_mode(MODE_FREE)
        mode_controller.enter_free_substate("play_ball")

    elif command == "toggle_dance":
        if 'spotify_detector' in globals():
            spotify_detector.toggle_manual()

    elif command == "resume_break":
        resume_from_break()


# ============================================================
# MAIN UPDATE
# ============================================================

def update():

    global dog_x
    global dog_y
    global kill_requested
    global dance_active
    global food_deadline
    global screen_time_start
    global hunger_rage_pending
    global hunger_rage_active
    global break_active


    # ========================================================
    # KILL SWITCH
    # ========================================================

    if kill_requested:

        try:
            mode_controller.stop_current_mode()
        except Exception:
            pass

        stop_screen_shake()

        dog.hide()
        tornado_dog.hide()
        cleaning_dog.hide()
        hunger_overlay.hide()
        break_overlay.hide()
        food_timer_label.hide()
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

        stop_ssj_sound()
        stop_tornado_sound()

        try:
            if 'spotify_detector' in globals():
                spotify_detector.stop()
        except Exception:
            pass

        for s in bark_sounds:
            try:
                s.stop()
            except Exception:
                pass

        app.quit()

        return


    # ========================================================
    # FEED KEY COMMAND
    # ========================================================

    process_mud_commands()

    # ========================================================
    # MODE EXPIRATION CHECK
    # ========================================================

    if 'mode_controller' in globals() and mode_controller:
        mode_controller.check_mode_expiration()


    # ========================================================
    # SPOTIFY MUSIC PLAYBACK ACTIVE:
    # 1. No break mode
    # 2. No hunger rage mode
    # 3. Dog runs everywhere and dances in both modes
    # ========================================================
    if 'spotify_detector' in globals() and spotify_detector.is_music_playing():
        screen_time_start = time.monotonic()
        food_deadline = max(food_deadline, time.monotonic() + FEED_INTERVAL)
        hunger_rage_pending = False
        if hunger_rage_active:
            hunger_rage_active = False
            hunger_overlay.hide()
            stop_screen_shake()
            stop_ssj_sound()
        if break_active:
            resume_from_break()

    # ========================================================
    # FEEDING
    # ========================================================

    update_eating()
    update_food_timer_display()

    # ========================================================
    # FEEDING ACTIVE
    # ========================================================

    if eating_active:

        update_eating_display()
        return


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
    # SCREEN TIME BREAK (TAKE A BREAK)
    # ========================================================

    if break_active:

        update_screen_break()

        update_display()

        return

    # Check if continuous screen time exceeded 1 minute (SCREEN_TIME_LIMIT)
    if (
        not break_active
        and not hunger_rage_active
        and not eating_active
        and not cleaning_active
        and not ssj_active
        and not tornado_active
        and not ('spotify_detector' in globals() and spotify_detector.is_music_playing())
    ):

        if (
            time.monotonic() - screen_time_start
            >= SCREEN_TIME_LIMIT
        ):

            start_screen_break()

            update_screen_break()

            update_display()

            return


    if 'mode_controller' in globals() and mode_controller and mode_controller.current_mode != MODE_INTERACTIVE:

        # ========================================================
        # AUTONOMOUS MODE (FREE MODE)
        # ========================================================

        mode_controller.update()

        if not dance_active:
            update_display()

        update_run_bark()

    else:

        # ========================================================
        # INTERACTIVE MODE (MANUAL CURSOR / GESTURES / SSJ)
        # ========================================================

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
        # SPOTIFY DANCE (INTERACTIVE MODE)
        # ========================================================

        if 'spotify_detector' in globals() and spotify_detector.is_music_playing():

            update_dance()

            update_dance_display()

            update_run_bark()

            return

        if dance_active:
            dance_active = False
            dance_notes.clear()


        # ========================================================
        # NORMAL DOG
        # ========================================================

        move_dog()

        update_display()

        update_run_bark()


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
hunger_overlay.hide()
footprints_overlay.hide()
update_food_timer_display()

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
    "FEEDING"
)
print(
    "----------------------------------------"
)
print(
    "F -> Feed dog with chicken"
)
print(
    "Feed timer resets after feeding"
)
print(
    "If timer expires -> SSJ hunger rage"
)
print(
    "Desktop is visually frozen for 5 seconds"
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

if __name__ == "__main__":

    try:

        sys.exit(
            app.exec()
        )

    finally:

        try:
            mode_controller.stop_current_mode()
        except Exception:
            pass

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

        try:
            hunger_overlay.hide()
            break_overlay.hide()
            food_timer_label.hide()
        except Exception:
            pass

        try:
            stop_ssj_sound()
        except Exception:
            pass

        try:
            stop_tornado_sound()
        except Exception:
            pass

        try:
            if 'spotify_detector' in globals():
                spotify_detector.stop()
        except Exception:
            pass

        for s in bark_sounds:
            try:
                s.stop()
            except Exception:
                pass
