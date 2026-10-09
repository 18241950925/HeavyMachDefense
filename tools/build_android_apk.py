"""Build a signed standalone APK using Android's official command-line tools."""
import argparse
import hashlib
import io
import json
import os
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "android/project"
BUILD = ROOT / "android/build"
SDK = ROOT / "tools/android-sdk"
TOOLS = SDK / "build-tools/35.0.0"
PLATFORM = SDK / "platforms/android-35/android.jar"
LLVM = SDK / "ndk/28.2.13676358/toolchains/llvm/prebuilt/windows-x86_64/bin"


def run(arguments):
    result = subprocess.run([str(item) for item in arguments], capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout.strip()


def java_home():
    result = subprocess.run(["java", "-XshowSettings:properties", "-version"],
                            capture_output=True, text=True)
    for line in result.stderr.splitlines():
        if "java.home =" in line:
            return Path(line.split("=", 1)[1].strip())
    raise RuntimeError("A JDK is required to build the APK")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(java):
    print("Preparing bundled game and resources", flush=True)
    assets = BUILD / "assets"
    game_dir = assets / "game"
    game_dir.mkdir(parents=True, exist_ok=True)
    game = game_dir / "MachDefense.ipa"
    with zipfile.ZipFile(game, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted((ROOT / "windows/game/MachDefense.app").rglob("*")):
            if path.is_file():
                archive.write(path, "Payload/" + path.relative_to(ROOT / "windows/game").as_posix())
    for name in ("touchHLE_fonts", "touchHLE_dylibs"):
        shutil.copytree(ROOT / "windows/runtime" / name, assets / name, dirs_exist_ok=True)
    shutil.copytree(ROOT / "android/chinese-fonts", assets / "touchHLE_fonts", dirs_exist_ok=True)
    shutil.copy2(ROOT / "windows/runtime/touchHLE_default_options.txt", assets)
    shutil.copy2(ROOT / "windows/runtime/COPYING.txt", assets / "NOTICE.txt")
    res = BUILD / "res"
    (res / "drawable-nodpi").mkdir(parents=True, exist_ok=True)
    (res / "values").mkdir(exist_ok=True)
    ipa = next(ROOT.glob("*.ipa"))
    with zipfile.ZipFile(ipa) as archive:
        artwork = Image.open(io.BytesIO(archive.read("iTunesArtwork")))
        artwork.save(res / "drawable-nodpi/game_icon.png")
    (res / "values/game.xml").write_text(
        '<resources><string name="game_sha256">' + digest(game) + '</string>' +
        '<string name="game_size">' + str(game.stat().st_size) + '</string></resources>', encoding="utf-8")
    compiled = BUILD / "compiled-resources.zip"
    run([TOOLS / "aapt2.exe", "compile", "--dir", res, "-o", compiled])
    generated = BUILD / "generated"
    generated.mkdir(exist_ok=True)
    run([TOOLS / "aapt2.exe", "link", "-o", BUILD / "resources.apk", "-I", PLATFORM,
         "--manifest", PROJECT / "AndroidManifest.xml", "--java", generated,
         "--min-sdk-version", "21", "--target-sdk-version", "32", compiled])
    classes = BUILD / "classes"
    classes.mkdir(exist_ok=True)
    sources = list((PROJECT / "src").rglob("*.java")) + list(generated.rglob("*.java"))
    sources += list((ROOT / "reference/touchHLE/vendor/SDL/android-project/app/src/main/java").rglob("*.java"))
    print("Compiling Android launcher and SDL Java bridge", flush=True)
    run([java / "bin/javac.exe", "-encoding", "UTF-8", "-source", "8", "-target", "8",
         "-classpath", PLATFORM, "-d", classes] + sources)
    jar = BUILD / "classes.jar"
    with zipfile.ZipFile(jar, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in classes.rglob("*.class"):
            archive.write(path, path.relative_to(classes).as_posix())
    dex = BUILD / "dex"
    dex.mkdir(exist_ok=True)
    run([java / "bin/java.exe", "-Xmx1536m", "-cp", TOOLS / "lib/d8.jar",
         "com.android.tools.r8.D8", "--release", "--min-api", "21", "--lib", PLATFORM,
         "--output", dex, jar])
    print("Launcher DEX compiled successfully", flush=True)


def elf_info(path):
    data = path.read_bytes()
    if data[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", data, 18)[0] != 183:
        raise ValueError("Expected an AArch64 ELF library: " + path.name)
    offset = struct.unpack_from("<Q", data, 32)[0]
    stride, count = struct.unpack_from("<HH", data, 54)
    alignments = []
    for i in range(count):
        header = offset + i * stride
        kind = struct.unpack_from("<I", data, header)[0]
        if kind == 1:
            alignment = struct.unpack_from("<Q", data, header + 48)[0]
            if alignment < 16384:
                raise ValueError("Native library is not 16 KB aligned: " + path.name)
            alignments.append(alignment)
    return {"sha256": digest(path), "machine": "AArch64", "load_alignments": alignments}


def package(java):
    native = PROJECT / "jniLibs/arm64-v8a"
    native.mkdir(parents=True, exist_ok=True)
    output = ROOT / "tools/android-native-build/aarch64-linux-android/release"
    # cargo-ndk copies the root cdylib; SDL's bundled shared library is built
    # inside sdl2-sys's installation directory.
    libraries = {
        "libtouchHLE.so": output / "libtouchHLE.so",
        "libc++_shared.so": SDK / "ndk/28.2.13676358/toolchains/llvm/prebuilt/windows-x86_64/sysroot/usr/lib/aarch64-linux-android/libc++_shared.so",
    }
    candidates = list((output / "build").glob("sdl2-sys-*/out/lib/libSDL2.so"))
    if not candidates:
        raise ValueError("Compiled SDL2 shared library was not found")
    libraries["libSDL2.so"] = max(candidates, key=lambda path: path.stat().st_mtime)
    report = {}
    for name, source in libraries.items():
        shutil.copy2(source, native / name)
        run([LLVM / "llvm-strip.exe", "--strip-unneeded", native / name])
        report[name] = elf_info(native / name)
    exports = run([LLVM / "llvm-nm.exe", "-D", native / "libtouchHLE.so"])
    if " SDL_main" not in exports:
        raise ValueError("Native Android entry point is missing")
    unsigned = BUILD / "unsigned.apk"
    with zipfile.ZipFile(BUILD / "resources.apk") as resources, zipfile.ZipFile(unsigned, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as apk:
        for entry in resources.infolist():
            apk.writestr(entry, resources.read(entry))
        for path in (BUILD / "dex").glob("*.dex"):
            apk.write(path, path.name)
        for path in (BUILD / "assets").rglob("*"):
            if path.is_file():
                method = zipfile.ZIP_STORED if path.suffix == ".ipa" else zipfile.ZIP_DEFLATED
                apk.write(path, "assets/" + path.relative_to(BUILD / "assets").as_posix(), compress_type=method)
        for path in native.glob("*.so"):
            apk.write(path, "lib/arm64-v8a/" + path.name, compress_type=zipfile.ZIP_STORED)
    aligned = BUILD / "aligned.apk"
    run([TOOLS / "zipalign.exe", "-f", "-P", "16", "4", unsigned, aligned])
    keys = ROOT / "tools/android-signing"
    keys.mkdir(exist_ok=True)
    key = keys / "mechdefence.keystore"
    password = "mechdefence-local-build"
    if not key.exists():
        run([java / "bin/keytool.exe", "-genkeypair", "-keystore", key, "-alias", "mechdefence",
             "-storepass", password, "-keypass", password, "-keyalg", "RSA", "-keysize", "2048",
             "-validity", "36500", "-dname", "CN=Local Heavy MACH Defense Build", "-noprompt"])
    apk = ROOT / "android/HeavyMachDefense-arm64.apk"
    signer = [java / "bin/java.exe", "-jar", TOOLS / "lib/apksigner.jar"]
    run(signer + ["sign", "--ks", key, "--ks-key-alias", "mechdefence", "--ks-pass", "pass:" + password,
                  "--v1-signing-enabled", "true", "--v2-signing-enabled", "true", "--v3-signing-enabled", "true",
                  "--out", apk, aligned])
    signature = run(signer + ["verify", "--verbose", "--print-certs", apk])
    alignment = run([TOOLS / "zipalign.exe", "-c", "-P", "16", "4", apk])
    badging = run([TOOLS / "aapt2.exe", "dump", "badging", apk])
    with zipfile.ZipFile(apk) as archive:
        if archive.testzip() is not None:
            raise ValueError("APK CRC verification failed")
        bundled = archive.read("assets/game/MachDefense.ipa")
        with zipfile.ZipFile(io.BytesIO(bundled)) as game:
            for path in (ROOT / "windows/game/MachDefense.app").rglob("*"):
                if path.is_file():
                    name = "Payload/" + path.relative_to(ROOT / "windows/game").as_posix()
                    if game.read(name) != path.read_bytes():
                        raise ValueError("Bundled game resource differs: " + name)
    report = {"apk_sha256": digest(apk), "apk_size": apk.stat().st_size,
              "min_android_api": 21, "target_android_api": 32, "abi": "arm64-v8a",
              "game_sha256": digest(BUILD / "assets/game/MachDefense.ipa"),
              "bundled_game_matches_prepared_windows_game": True, "native_libraries": report,
              "signature_verification": signature, "apk_16kb_alignment_verified": True,
              "device_tested": False}
    (ROOT / "android/verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (ROOT / "android/apk-info.txt").write_text(badging + "\n", encoding="utf-8")
    apk.with_suffix(".apk.sha256").write_text(digest(apk) + "  " + apk.name + "\n", encoding="ascii")
    print("Signed APK:", apk, flush=True)
    print("Size:", apk.stat().st_size, "bytes; SHA-256:", digest(apk), flush=True)
    print("Signature v1/v2/v3, ARM64 ELF alignment, APK alignment and bundled resources verified", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--package-only", action="store_true")
    args = parser.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    java = java_home()
    if not args.package_only:
        prepare(java)
    if not args.prepare_only:
        package(java)


if __name__ == "__main__":
    main()
