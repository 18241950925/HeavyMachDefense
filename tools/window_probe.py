"""Capture or send test mouse input to the touchHLE game window only."""
import argparse
import ctypes
import json
import time
from ctypes import wintypes
from pathlib import Path

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]


def find_window():
    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def callback(hwnd, _):
        title = ctypes.create_unicode_buffer(1024)
        user32.GetWindowTextW(hwnd, title, len(title))
        if "(touchHLE " in title.value:
            found.append((hwnd, title.value))
        return True

    user32.EnumWindows(callback, 0)
    if len(found) != 1:
        raise RuntimeError("Expected one visible touchHLE window, found " + str(len(found)))
    return found[0]


def client_info(hwnd):
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    pos = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pos))
    return pos.x, pos.y, rect.right, rect.bottom


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture")
    parser.add_argument("--close", action="store_true")
    clicks = parser.add_mutually_exclusive_group()
    clicks.add_argument("--click", nargs=2, type=int, metavar=("X", "Y"))
    clicks.add_argument("--game-click", nargs=2, type=int, metavar=("X", "Y"))
    args = parser.parse_args()
    hwnd, title = find_window()
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    left, top, width, height = client_info(hwnd)
    print(json.dumps({"hwnd": hwnd, "title": title, "client": [left, top, width, height]}))
    if args.close:
        user32.PostMessageW(hwnd, 0x10, 0, 0)
        return
    if args.click or args.game_click:
        if args.game_click:
            x, y = args.game_click
            if not (0 <= x < 320 and 0 <= y < 480):
                raise ValueError("Click outside logical game screen")
            factor = min(width / 320, height / 480)
            x = round((width - 320 * factor) / 2 + x * factor)
            y = round((height - 480 * factor) / 2 + y * factor)
        else:
            x, y = args.click
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError("Click outside game window")
        user32.SetCursorPos(left + x, top + y)
        time.sleep(0.15)
        position = x | (y << 16)
        user32.PostMessageW(hwnd, 0x200, 0, position)
        user32.PostMessageW(hwnd, 0x201, 1, position)
        time.sleep(0.15)
        user32.PostMessageW(hwnd, 0x202, 0, position)
    if args.capture:
        from PIL import ImageGrab
        target = Path(args.capture)
        target.parent.mkdir(parents=True, exist_ok=True)
        ImageGrab.grab(bbox=(left, top, left + width, top + height), all_screens=True).save(target)


if __name__ == "__main__":
    main()
