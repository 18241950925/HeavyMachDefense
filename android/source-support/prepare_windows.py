"""Prepare a separate copy of the supplied IPA for touchHLE on Windows."""
from pathlib import Path
import hashlib
import json
import plistlib
import struct
import zipfile

from macho import MachO

ROOT = Path(__file__).resolve().parents[1]


def table_keystream(length):
    # Darwin/BSD random(), seeded by -[QTable initWithFile:] at 0x46554.
    # touchHLE uses a different random() sequence, so prepare plaintext tables
    # instead. The original loader already accepts tables without EncTbl.
    state = [0xB27F7]
    for _ in range(1, 31):
        state.append(16807 * state[-1] % 2147483647)
    state.extend(state[:3])
    for i in range(34, 344 + length):
        state.append((state[i - 31] + state[i - 3]) & 0xFFFFFFFF)
    return bytes((value >> 1) % 227 for value in state[344:])


def patch_new_slot(app):
    path = app / "MachDefense"
    data = bytearray(path.read_bytes())
    macho = MachO(data)
    # UIAlertView.show and its text entry UI are unimplemented in touchHLE.
    # NEW therefore calls the original GlobalInfo slot creation routine with
    # the name Player, refreshes the slot and opens the original stage menu.
    code = bytes.fromhex(
        "70b5044648f64c40c0f20600006848f2c821c0f2060109684cf25062c0f20202"
        "30f0dcec054648f61c40c0f20600006847f61471c0f20601096830f0d0ec2a46"
        "4af6ac53c0f2060348f24471c0f20601096830f0c4ece06510f1010f10d0"
        "0246204647f6d071c0f20601096830f0b6ec204648f25471c0f20601096830f0aeec70bd"
    )
    start = macho.offset(0x2C5B0)
    data[start:start + len(code)] = code
    data[macho.offset(0x2C650):macho.offset(0x2C650) + 7] = b"Player\0"
    path.write_bytes(data)


def patch_obsolete_ads(app):
    path = app / "MachDefense"
    data = bytearray(path.read_bytes())
    macho = MachO(data)
    targets = {
        ("GuiBanner", "initgb"),
        ("GuiBanner", "tick"),
        ("GuiBanner", "ClickBanner"),
        ("GuiBanner", "onTap:State:ID:"),
        ("DefaultAppDelegate", "bannerTurnOn:"),
        ("DefaultAppDelegate", "bannerTurnOff:"),
    }
    for cls, _, selector, imp in macho.methods():
        if (cls, selector) in targets:
            if not imp & 1:
                raise ValueError("Expected a Thumb advertisement method")
            offset = macho.offset(imp & ~1)
            data[offset:offset + 4] = b"\0\x20\x70\x47"  # movs r0, #0; bx lr
            targets.remove((cls, selector))
    if targets:
        raise ValueError("Missing advertisement methods: " + repr(targets))
    path.write_bytes(data)


def prepare():
    ipa = next(ROOT.glob("*.ipa"))
    output = ROOT / "windows" / "game"
    with zipfile.ZipFile(ipa) as archive:
        for entry in archive.infolist():
            parts = Path(entry.filename).parts
            if ".." in parts or Path(entry.filename).is_absolute():
                raise ValueError("Unsafe archive entry: " + entry.filename)
            if not entry.filename.startswith("Payload/") or entry.is_dir():
                continue
            target = output.joinpath(*parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(entry))

    app = output / "MachDefense.app"
    if hashlib.sha256((app / "MachDefense").read_bytes()).hexdigest() != "6ec47ea094abaa31bab10058fe47bb25d46c6038b2e88a7da2629899f84af112":
        raise ValueError("This preparation script supports only the supplied 1.0.3 ARMv7 executable")
    changes = []
    tables = list(app.glob("*.tble"))
    key = table_keystream(max(path.stat().st_size - 6 for path in tables))
    for path in tables:
        encrypted = path.read_bytes()
        if not encrypted.startswith(b"EncTbl"):
            raise ValueError("Unexpected encrypted table: " + path.name)
        plain = bytes(value ^ key[i] for i, value in enumerate(encrypted[6:]))
        if path.name == "MachBuild_Parts.tble":
            if plain != (app / "MachBuild_Parts.tbl").read_bytes():
                raise ValueError("Table decryption failed known-plaintext check")
        path.write_bytes(plain)
    changes.append({"files": len(tables), "change": "Decrypt QTable resources with verified Darwin random() sequence"})
    # NIBArchive class table is the last section. Each name is length-prefixed
    # with an Apple varint, followed by an empty extras list and a C string.
    # UITextField provides UIView layout plus the delegate outlet expected
    # by the archived banner; it remains empty and never loads an ad.
    for name in ("MainWindow.nib", "MainWindow_iPhone.nib"):
        path = app / name
        data = path.read_bytes()
        old = b"\x8d\x80ADBannerView\0"
        new = b"\x8c\x80UITextField\0"
        if data.count(old) != 1:
            raise ValueError("Unexpected banner class table: " + name)
        path.write_bytes(data.replace(old, new))
        changes.append({"file": name, "change": "Decode obsolete iAd banner as an empty UITextField"})

    info_path = app / "Info.plist"
    info = plistlib.loads(info_path.read_bytes())
    info["UISupportedInterfaceOrientations"] = ["UIInterfaceOrientationPortrait"]
    info["UISupportedInterfaceOrientations~ipad"] = ["UIInterfaceOrientationPortrait"]
    info_path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_BINARY))
    changes.append({"file": "Info.plist", "change": "Use upright portrait orientation"})
    patch_new_slot(app)
    changes.append({"file": "MachDefense", "change": "NEW creates an original save slot named Player without unsupported UIAlertView text input"})
    patch_obsolete_ads(app)
    changes.append({"file": "MachDefense", "change": "Disable obsolete iAd animations and WeMade banner request/update callbacks"})
    report = {
        "input": ipa.name,
        "input_sha256": hashlib.sha256(ipa.read_bytes()).hexdigest(),
        "bundle": info["CFBundleIdentifier"],
        "version": info["CFBundleShortVersionString"],
        "minimum_ios": info["MinimumOSVersion"],
        "changes": changes,
    }
    (ROOT / "windows" / "preparation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Prepared", app)


if __name__ == "__main__":
    prepare()
