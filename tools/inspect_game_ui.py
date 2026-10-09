"""Decode original CgBI PNGs for inspection; never modify game resources."""
import io
import struct
import zlib
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def decode(path):
    raw = path.read_bytes()
    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
        return image.convert("RGBA")
    except OSError:
        pass
    pos, compressed = 8, bytearray()
    while pos < len(raw):
        length = struct.unpack_from(">I", raw, pos)[0]
        kind, data = raw[pos + 4:pos + 8], raw[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, channels = struct.unpack_from(">IIBB", data)
        if kind == b"IDAT":
            compressed.extend(data)
        pos += length + 12
    assert depth == 8 and channels == 6
    pixels = zlib.decompress(compressed, -15)
    stride, output, previous = width * 4, bytearray(), bytearray(width * 4)
    for y in range(height):
        row = bytearray(pixels[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        method = pixels[y * (stride + 1)]
        for x in range(stride):
            left = row[x - 4] if x >= 4 else 0
            up = previous[x]
            upper_left = previous[x - 4] if x >= 4 else 0
            if method == 1: value = left
            elif method == 2: value = up
            elif method == 3: value = (left + up) // 2
            elif method == 4:
                p = left + up - upper_left
                choices = [(abs(p - left), left), (abs(p - up), up), (abs(p - upper_left), upper_left)]
                value = min(enumerate(choices), key=lambda item: (item[1][0], item[0]))[1][1]
            else: value = 0
            row[x] = (row[x] + value) & 255
        previous = row
        for x in range(0, stride, 4):
            b, g, r, a = row[x:x + 4]
            output.extend((min(255, r * 255 // a) if a else 0,
                           min(255, g * 255 // a) if a else 0,
                           min(255, b * 255 // a) if a else 0, a))
    return Image.frombytes("RGBA", (width, height), bytes(output))


if __name__ == "__main__":
    import sys
    paths = [ROOT / "windows/game/MachDefense.app" / name for name in sys.argv[1:]]
    items = [(path, decode(path)) for path in paths]
    sheet = Image.new("RGB", (1100, sum(max(90, im.height) + 32 for _, im in items)), (38, 42, 46))
    draw, y = ImageDraw.Draw(sheet), 0
    for path, im in items:
        draw.text((8, y + 6), f"{path.name} {im.size}", fill="white")
        sheet.paste(im, (8, y + 26), im)
        y += max(90, im.height) + 32
    sheet.save(ROOT / "android/ui-assets-inspection.png")
