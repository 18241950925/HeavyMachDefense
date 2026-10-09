"""Prepare an isolated launcher test copy without modifying player save data."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare():
    source = ROOT / "windows"
    destination = ROOT / "verification-data/graphics-test"
    runtime = destination / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    for name in ("HeavyMachDefense.exe", "Display.ini"):
        shutil.copy2(source / name, destination / name)
    for name in ("touchHLE.exe", "msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll",
                 "touchHLE_default_options.txt", "touchHLE_options.txt"):
        shutil.copy2(source / "runtime" / name, runtime / name)
    for name in ("touchHLE_fonts", "touchHLE_dylibs"):
        shutil.copytree(source / "runtime" / name, runtime / name, dirs_exist_ok=True)
    shutil.copytree(source / "game", destination / "game", dirs_exist_ok=True)
    sandbox = runtime / "touchHLE_sandbox"
    if not sandbox.exists():
        shutil.copytree(ROOT / "verification-data/test-sandbox", sandbox)
    print("Isolated graphics test:", destination)


if __name__ == "__main__":
    prepare()
