"""Prepare static, bundled Simplified Chinese fonts from Google's OFL font."""
from pathlib import Path
import hashlib
import json
import urllib.request
from fontTools.ttLib import TTFont
from fontTools import subset
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "android/chinese-fonts"
SOURCE = ROOT / "tools/font-sources"


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    SOURCE.mkdir(parents=True, exist_ok=True)
    base = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/"
    original = SOURCE / "NotoSansSC-variable.ttf"
    license_file = OUT / "LICENSE.noto-sc"
    for name, path in [("NotoSansSC%5Bwght%5D.ttf", original), ("OFL.txt", license_file)]:
        if not path.exists():
            print("Downloading", name, flush=True)
            urllib.request.urlretrieve(base + name, path)
    # GB2312 plus every caption in the runtime, punctuation and Latin letters.
    characters = set(chr(n) for n in range(32, 127))
    for first in range(0xA1, 0xF8):
        for second in range(0xA1, 0xFF):
            try:
                characters.update(bytes([first, second]).decode("gb2312"))
            except UnicodeDecodeError:
                pass
    characters.update((ROOT / "reference/touchHLE/src/localization.rs").read_text(encoding="utf-8"))
    for weight, name in [(500, "MechSansSC-Medium.ttf"), (700, "MechSansSC-Bold.ttf")]:
        path = OUT / name
        if path.exists():
            continue
        font = TTFont(original)
        options = subset.Options()
        options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14]
        job = subset.Subsetter(options=options)
        job.populate(unicodes=[ord(c) for c in characters])
        job.subset(font)
        instantiateVariableFont(font, {"wght": weight}, inplace=True)
        # The derived static subset has its own family name.
        family = "Mech Sans SC"
        style = "Medium" if weight == 500 else "Bold"
        for record in font["name"].names:
            values = {1: family, 2: style, 3: family + " " + style,
                      4: family + " " + style, 6: "MechSansSC-" + style}
            if record.nameID in values:
                record.string = values[record.nameID].encode(record.getEncoding())
        font.save(path)
        print(name, path.stat().st_size, "bytes", flush=True)
    report = {"source": base + "NotoSansSC%5Bwght%5D.ttf",
              "source_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
              "weights": [500, 700], "coverage": "GB2312, Latin and runtime captions"}
    (OUT / "source.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    prepare()
