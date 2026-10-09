"""Initialize the published source snapshot's pinned vendor dependencies."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    if not (ROOT / '.gitmodules').exists():
        print('The original workspace already contains its dependency checkouts.')
        return
    subprocess.run(['git', 'submodule', 'update', '--init', '--recursive'],
                   cwd=ROOT, check=True)
    sdl = ROOT / 'reference/touchHLE/vendor/SDL'
    patch = ROOT / 'android/source-support/SDL-ndk28.patch'
    check = subprocess.run(['git', 'apply', '--check', str(patch)],
                           cwd=sdl, capture_output=True)
    if check.returncode == 0:
        subprocess.run(['git', 'apply', str(patch)], cwd=sdl, check=True)
        print('Applied the SDL Android NDK 28 compatibility patch.')
    else:
        applied = subprocess.run(['git', 'apply', '--reverse', '--check', str(patch)],
                                 cwd=sdl, capture_output=True)
        if applied.returncode:
            raise RuntimeError('SDL differs from the pinned version; cannot safely apply the patch.')
        print('The SDL Android patch is already applied.')


if __name__ == '__main__':
    main()
