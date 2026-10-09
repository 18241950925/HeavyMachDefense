"""Export the local runtime changes and Android build sources alongside the APK."""
from pathlib import Path
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = "d34530b52174e8a4f1fe43178cc4fb0c99506f9f"


def git(*args, where=None):
    return subprocess.check_output(["git", "-C", str(where or ROOT / "reference/touchHLE"), *args])


def export():
    output = ROOT / "android/source-support"
    output.mkdir(parents=True, exist_ok=True)
    if not (ROOT / "reference/touchHLE/.git").exists():
        if not (output / "touchHLE.patch").exists():
            raise RuntimeError("The source snapshot is missing its original runtime patch")
        print("This published snapshot already includes complete sources and exported patches")
        return
    (output / "touchHLE.patch").write_bytes(git("diff", "--binary", BASE, "--", ".", ":!vendor/SDL"))
    (output / "SDL-ndk28.patch").write_bytes(git("diff", "--binary", where=ROOT / "reference/touchHLE/vendor/SDL"))
    for name in ["build_android_runtime.ps1", "build_android_apk.py", "android_cmake.cmd",
                 "setup_android.py", "setup_android_rust.ps1", "prepare_chinese_fonts.py",
                 "prepare_windows.py", "macho.py"]:
        shutil.copy2(ROOT / "tools" / name, output / name)
    shutil.copytree(ROOT / "android/project/src", output / "project/src", dirs_exist_ok=True)
    shutil.copy2(ROOT / "android/project/AndroidManifest.xml", output / "project")
    shutil.copy2(ROOT / "reference/touchHLE/LICENSE", output / "LICENSE.touchHLE")
    shutil.copy2(ROOT / "android/chinese-fonts/LICENSE.noto-sc", output)
    (output / "source.json").write_text(json.dumps({
        "upstream": "https://github.com/touchHLE/touchHLE", "upstream_base": BASE,
        "local_commit": git("rev-parse", "HEAD").decode().strip(),
        "full_local_source": "reference/touchHLE", "runtime_patch": "touchHLE.patch",
        "android_launcher": "android/project", "signing_key_included": False,
        "font_source": json.loads((ROOT / "android/chinese-fonts/source.json").read_text()),
    }, indent=2), encoding="utf-8")
    print("Runtime patch and Android build sources exported")


if __name__ == "__main__":
    export()
