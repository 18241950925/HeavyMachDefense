"""Check package integrity against the supplied IPA; optionally validate a save."""
import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_save(path):
    data = bytearray(path.read_bytes())
    if len(data) != 42496:
        raise ValueError("Unexpected save length")
    state = struct.unpack_from("<I", data)[0]
    for i in range(4, len(data) - 4):
        state ^= (state << 13) & 0xFFFFFFFF
        state ^= state >> 17
        state ^= (state << 5) & 0xFFFFFFFF
        state &= 0xFFFFFFFF
        data[i] ^= state & 255
    checksum = sum(value if value < 128 else value - 256 for value in data[4:-4])
    stored = struct.unpack_from("<i", data, len(data) - 4)[0]
    if checksum != stored:
        raise ValueError("Save checksum mismatch")
    return {"size": len(data), "checksum": stored, "checksum_valid": True}


def verify():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", type=Path)
    args = parser.parse_args()
    preparation = json.loads((ROOT / "windows/preparation.json").read_text())
    ipa = ROOT / preparation["input"]
    if sha256(ipa) != preparation["input_sha256"]:
        raise ValueError("Original IPA has changed")
    changed = []
    images = audio = tables = untouched = 0
    allowed = {"MachDefense", "Info.plist", "MainWindow.nib", "MainWindow_iPhone.nib"}
    with zipfile.ZipFile(ipa) as archive:
        for entry in archive.infolist():
            if entry.is_dir() or not entry.filename.startswith("Payload/MachDefense.app/"):
                continue
            relative = entry.filename[len("Payload/"):]
            original = archive.read(entry)
            prepared = (ROOT / "windows/game" / relative).read_bytes()
            suffix = Path(relative).suffix.lower()
            if suffix == ".tble":
                tables += 1
                if not original.startswith(b"EncTbl") or prepared.startswith(b"EncTbl"):
                    raise ValueError("Incorrect table state: " + relative)
            elif prepared != original:
                if Path(relative).name not in allowed:
                    raise ValueError("Unexpected resource change: " + relative)
            else:
                untouched += 1
            if prepared != original:
                changed.append(relative)
            if suffix in (".png", ".jpg", ".jpeg"):
                images += 1
                if prepared != original:
                    raise ValueError("Image modified: " + relative)
            if suffix in (".wav", ".mp3"):
                audio += 1
                if prepared != original:
                    raise ValueError("Audio modified: " + relative)
    if (tables, images, audio, len(changed)) != (94, 1109, 80, 98):
        raise ValueError("Unexpected resource inventory")
    app = ROOT / "windows/game/MachDefense.app"
    known = (app / "MachBuild_Parts.tbl").read_bytes()
    if (app / "MachBuild_Parts.tble").read_bytes() != known:
        raise ValueError("Decrypted known-plaintext table differs")
    binaries = {}
    for relative in ("HeavyMachDefense.exe", "runtime/touchHLE.exe"):
        path = ROOT / "windows" / relative
        binary = path.read_bytes()
        offset = struct.unpack_from("<I", binary, 0x3C)[0]
        if binary[:2] != b"MZ" or binary[offset:offset + 4] != b"PE\0\0":
            raise ValueError("Invalid Windows executable")
        if struct.unpack_from("<H", binary, offset + 4)[0] != 0x8664:
            raise ValueError("Expected Windows x64 executable")
        binaries[relative] = sha256(path)
    for name in ("msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll"):
        if not (ROOT / "windows/runtime" / name).is_file():
            raise ValueError("Missing runtime dependency: " + name)
    launcher = (ROOT / "windows/HeavyMachDefense.exe").read_bytes()
    if "--preferred-languages=zh,en".encode("utf-16-le") not in launcher:
        raise ValueError("Windows launcher does not enable the Chinese edition")
    fonts = {}
    for name in ("MechSansSC-Medium.ttf", "MechSansSC-Bold.ttf", "LICENSE.noto-sc"):
        bundled = ROOT / "windows/runtime/touchHLE_fonts" / name
        original = ROOT / "android/chinese-fonts" / name
        if bundled.read_bytes() != original.read_bytes():
            raise ValueError("Windows Chinese font or license differs from Android: " + name)
        fonts[name] = sha256(bundled)
    report = {
        "ipa_sha256": sha256(ipa),
        "prepared_game_sha256": sha256(app / "MachDefense"),
        "images_byte_identical": images,
        "audio_byte_identical": audio,
        "decrypted_tables": tables,
        "known_plaintext_bytes_verified": len(known),
        "unchanged_files": untouched,
        "modified_files": changed,
        "windows_x64_binaries_sha256": binaries,
        "edition": "1.0.3-zh4",
        "preferred_languages": ["zh", "en"],
        "chinese_fonts_sha256": fonts,
        "chinese_fonts_match_android": True,
    }
    (ROOT / "windows/integrity.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.save:
        report["test_save"] = check_save(args.save)
    summary = {key: value for key, value in report.items() if key != "modified_files"}
    summary["modified_files_count"] = len(changed)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    verify()
