"""Download pinned Android build dependencies into this workspace only."""
import concurrent.futures
import hashlib
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / "tools/android-sdk"
DOWNLOADS = ROOT / "tools/android-downloads"
PACKAGES = [
    ("android-ndk-r28c-windows.zip", "086bba43ff2f5eb0e387b15c8278bb4e0d89ba1d",
     "android-ndk-r28c", "ndk/28.2.13676358"),
    ("build-tools_r35_windows.zip", "af059bb67cf7786f45ee0db85e2d24985df1b4b6",
     "android-15", "build-tools/35.0.0"),
    ("platform-35_r02.zip", "0bb560a90a7a2cbd0dd8348224d518b638fe7949",
     "android-35", "platforms/android-35"),
]


def install(package):
    filename, expected, prefix, relative = package
    destination = SDK / relative
    marker = destination / ".verified-download"
    if marker.exists() and marker.read_text() == expected:
        print("Already installed:", relative, flush=True)
        return
    path = DOWNLOADS / filename
    if not path.exists() or hashlib.sha1(path.read_bytes()).hexdigest() != expected:
        temporary = path.with_suffix(".partial")
        print("Downloading:", filename, flush=True)
        with urllib.request.urlopen("https://dl.google.com/android/repository/" + filename,
                                    timeout=90) as response, temporary.open("wb") as output:
            total = int(response.headers.get("Content-Length", 0))
            copied = 0
            checkpoint = 0
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                output.write(block)
                copied += len(block)
                if total and copied * 100 // total >= checkpoint + 20:
                    checkpoint = copied * 100 // total
                    print(filename, str(checkpoint) + "%", flush=True)
        if hashlib.sha1(temporary.read_bytes()).hexdigest() != expected:
            raise ValueError("Download checksum mismatch: " + filename)
        temporary.replace(path)
    print("Extracting:", filename, flush=True)
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            parts = Path(entry.filename).parts
            if ".." in parts or Path(entry.filename).is_absolute():
                raise ValueError("Unsafe archive path")
            if parts[0] != prefix:
                raise ValueError("Unexpected archive root: " + entry.filename)
            target = destination.joinpath(*parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
    marker.write_text(expected)
    print("Installed:", relative, flush=True)


def setup():
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    SDK.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(install, PACKAGES):
            pass


if __name__ == "__main__":
    setup()
