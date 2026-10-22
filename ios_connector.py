import subprocess
import time

import cv2
from Quartz import (CGEventCreateMouseEvent, CGEventPost, CGEventSourceCreate, CGWindowListCopyWindowInfo,
                    kCGEventLeftMouseDown, kCGEventLeftMouseUp, kCGEventMouseMoved, kCGEventSourceStateHIDSystemState,
                    kCGHIDEventTap, kCGMouseButtonLeft, kCGNullWindowID, kCGWindowListOptionOnScreenOnly)

# Works through macOS iPhone Mirroring: the window is screenshotted and taps are sent as mouse clicks.
# The terminal running this needs Screen Recording and Accessibility permissions.

image_path = "images/screen.png"

# Screenshots are scaled to this width so tiles match the ~43px radius image_processing was tuned for
# (a 350pt mirroring window captures at 700px wide with ~47px tiles)
NORMALIZED_WIDTH = 644
TAP_HOLD = 0.03
TAP_DELAY = 0.05
# "I Give Up!" / "Claim" button, as a fraction of the window size
RESTART_BUTTON = (0.451, 0.877)
# rows of the window holding the tiles (the counters and timer above keep changing)
BOARD_ROWS = (0.36, 0.83)
SETTLE_TIMEOUT = 8

window = None  # (id, x, y, width, height) in screen points, refreshed on every screenshot


def find_window():
    for info in CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID):
        if info.get("kCGWindowOwnerName") == "iPhone Mirroring" and info.get("kCGWindowLayer") == 0:
            bounds = info["kCGWindowBounds"]
            return info["kCGWindowNumber"], bounds["X"], bounds["Y"], bounds["Width"], bounds["Height"]
    raise RuntimeError("iPhone Mirroring window not found, open it and connect the phone first")


def capture_window():
    subprocess.run(["screencapture", "-x", "-o", f"-l{window[0]}", image_path], check=True)
    image = cv2.imread(image_path)
    top, bottom = (int(image.shape[0] * row) for row in BOARD_ROWS)
    return image, image[top:bottom]


def get_screenshot():
    global window
    window = find_window()
    # the mirrored screen can lag the phone by seconds after a burst of taps, so wait for the board to stop changing
    image, board = capture_window()
    deadline = time.time() + SETTLE_TIMEOUT
    while time.time() < deadline:
        time.sleep(0.4)
        previous_board = board
        image, board = capture_window()
        if board.shape == previous_board.shape and cv2.absdiff(board, previous_board).mean() < 0.5:
            break
    scale = NORMALIZED_WIDTH / image.shape[1]
    cv2.imwrite(image_path, cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA))
    # clicks only reach the phone while the mirroring window is frontmost
    subprocess.run(["open", "-a", "iPhone Mirroring"], check=True)
    time.sleep(0.3)


def click(x: float, y: float):
    # iPhone Mirroring ignores clicks posted without a HID event source
    source = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)
    for event_type in (kCGEventMouseMoved, kCGEventLeftMouseDown, kCGEventLeftMouseUp):
        CGEventPost(kCGHIDEventTap, CGEventCreateMouseEvent(source, event_type, (x, y), kCGMouseButtonLeft))
        time.sleep(TAP_HOLD)
    time.sleep(TAP_DELAY)


def tap_screen(x: int, y: int):
    # x, y are pixels of the normalized screenshot
    _, left, top, width, _ = window
    points_per_pixel = width / NORMALIZED_WIDTH
    click(left + x * points_per_pixel, top + y * points_per_pixel)


def restart_game():
    _, left, top, width, height = window
    click(left + width * RESTART_BUTTON[0], top + height * RESTART_BUTTON[1])
    time.sleep(1.5)
