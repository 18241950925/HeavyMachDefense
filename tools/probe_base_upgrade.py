"""Measure the time until the base menu is painted in the isolated game test."""
import argparse
import json
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageGrab, ImageStat
from window_probe import client_info, find_window, user32


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--capture', required=True)
    args = parser.parse_args()
    hwnd, _ = find_window()
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    left, top, width, height = client_info(hwnd)
    factor = min(width / 320, height / 480)
    offset_x = (width - 320 * factor) / 2
    offset_y = (height - 480 * factor) / 2
    # Compare a button row rather than the moving battlefield or animation.
    sample = (round(offset_x + 50 * factor), round(offset_y + 343 * factor),
              round(offset_x + 260 * factor), round(offset_y + 359 * factor))
    reference = Image.open(Path(__file__).resolve().parents[1] / 'android/zh-verified-base.png')
    reference = reference.crop(sample).convert('RGB')
    x, y = round(offset_x + 275 * factor), round(offset_y + 466 * factor)
    user32.SetCursorPos(left + x, top + y)
    position = x | (y << 16)
    user32.PostMessageW(hwnd, 0x200, 0, position)
    user32.PostMessageW(hwnd, 0x201, 1, position)
    time.sleep(0.15)
    started = time.perf_counter()
    user32.PostMessageW(hwnd, 0x202, 0, position)
    ready = False
    error = None
    for _ in range(300):
        frame = ImageGrab.grab(bbox=(left, top, left + width, top + height), all_screens=True)
        error = sum(ImageStat.Stat(ImageChops.difference(reference, frame.crop(sample).convert('RGB'))).mean) / 3
        if error < 12:
            ready = True
            break
        time.sleep(0.1)
    elapsed = time.perf_counter() - started
    frame.save(args.capture)
    result = {'seconds_to_visible_menu': elapsed, 'menu_visible': ready,
              'reference_pixel_mean_error': error, 'logical_sample': [50, 343, 260, 359]}
    Path(args.output).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
    if not ready:
        raise SystemExit('Base menu was not detected; inspect the captured screen.')


if __name__ == '__main__':
    main()
