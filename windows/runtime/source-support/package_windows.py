"""Preserve source changes and package the playable Windows folder."""
import hashlib
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "d34530b52174e8a4f1fe43178cc4fb0c99506f9f"


def package():
    source = ROOT / "reference/touchHLE"
    runtime = ROOT / "windows/runtime"
    if (source / ".git").exists():
        result = subprocess.run(["git", "diff", "--binary", BASE, "--", ".", ":!vendor/SDL"], cwd=str(source),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        (runtime / "compatibility.patch").write_bytes(result.stdout)
    else:
        # The containing repository stores a complete source snapshot rather
        # than touchHLE's upstream history; retain the exported baseline patch.
        if not (runtime / "compatibility.patch").exists():
            raise RuntimeError("Missing Windows runtime source provenance")
    support = runtime / "source-support"
    support.mkdir(exist_ok=True)
    for name in ("launcher.cpp", "launcher.rc", "game.ico", "prepare_windows.py", "macho.py",
                 "build_launcher.ps1", "build_runtime.ps1", "verify_windows.py", "package_windows.py"):
        shutil.copy2(ROOT / "tools" / name, support / name)
    output = ROOT / "HeavyMachDefense-Windows.zip"
    excluded_names = {"launcher.log", "launcher.previous.log", "touchHLE_log.txt"}
    count = 0
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted((ROOT / "windows").rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT / "windows")
            if "touchHLE_sandbox" in relative.parts or path.suffix.lower() == ".pdb":
                continue
            if path.name in excluded_names:
                continue
            archive.write(path, "HeavyMachDefense-Windows/" + relative.as_posix())
            count += 1
    with zipfile.ZipFile(output) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError("Package CRC mismatch: " + bad)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".zip.sha256").write_text(digest + "  " + output.name + "\n", encoding="ascii")
    print("Packaged", count, "files;", output.stat().st_size, "bytes")
    print("SHA-256:", digest)


if __name__ == "__main__":
    package()
