# 源码与构建

普通游玩请从 [Release](https://github.com/18241950925/HeavyMachDefense/releases/latest) 下载 Windows ZIP 或 Android APK，无需准备开发环境。

仓库中的 `reference/touchHLE/` 是最新中文修复版的完整兼容层源码快照，保留上游许可。第三方 C/C++ 依赖通过 Git 子模块固定版本；SDL 的 Android NDK 28 修改保存在 `android/source-support/SDL-ndk28.patch`。下载源码后先运行：

```powershell
git clone --recurse-submodules https://github.com/18241950925/HeavyMachDefense.git
cd HeavyMachDefense
python tools/prepare_dependencies.py
```

原游戏程序和资源随游玩安装包提供，不重复放入 Git 历史。重新构建时需把原版 1.0.3 IPA 放到仓库根目录，再执行 `python tools/prepare_windows.py`。脚本会检查游戏程序 SHA-256；适配不包含原版游戏源码。

构建脚本面向 Windows 主机，需要 Python 3、JDK、Rust、Visual Studio 2022 C++、CMake、Ninja；Windows 启动器另需 MinGW 的 `g++` 和 `windres`。Python 依赖见 `requirements.txt`。

```powershell
python -m pip install -r requirements.txt
python tools/setup_android.py
```

Rust 脚本使用工作区内 `tools/rust/cargo`、`tools/rust/rustup`。可以使用 rustup-init 将 Rust 安装到这两个目录，也可以调整脚本中的 `CARGO_HOME`、`RUSTUP_HOME` 以使用自己的工具链。`tools/build_android_runtime.ps1` 的 Ninja 路径来自原构建机，需要改成你的 Visual Studio / Ninja 安装路径；临时盘符 `X:` 必须空闲。

## Android

在准备 IPA 并初始化依赖后，将源码快照中的字体、辅助动态库和默认配置放到打包脚本使用的目录：

```powershell
New-Item -ItemType Directory -Force windows/runtime | Out-Null
Copy-Item reference/touchHLE/touchHLE_fonts windows/runtime -Recurse -Force
Copy-Item reference/touchHLE/touchHLE_dylibs windows/runtime -Recurse -Force
Copy-Item reference/touchHLE/touchHLE_default_options.txt windows/runtime
Copy-Item reference/touchHLE/LICENSE windows/runtime/COPYING.txt
powershell -NoProfile -ExecutionPolicy Bypass -File tools/setup_android_rust.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools/build_android_runtime.ps1
python tools/build_android_apk.py
```

输出为 `android/HeavyMachDefense-arm64.apk`。字体已经提供，无需重新下载；需要重新生成字体时运行 `python tools/prepare_chinese_fonts.py`。APK 构建脚本检查签名、16 KB 库对齐、ZIP 完整性和游戏资源一致性。

发布用的 Android 签名私钥留在原构建机，未上传。其他电脑首次构建会生成自己的签名，不能直接覆盖安装本项目已发布 APK；要保持更新兼容性，维护者需使用原签名密钥。

## Windows

`tools/build_runtime.ps1` 编译兼容层，`tools/build_launcher.ps1` 编译启动器；`tools/verify_windows.py` 和 `tools/package_windows.py` 用于检查并生成便携 ZIP。运行目录还需要 touchHLE 字体、动态库、配置文件和 Microsoft Visual C++ 运行库，布局见游玩包。

当前 Release 的 Windows 包保留已有英文运行版本，其对应上游版本和改动见 `windows/runtime/SOURCE.md`、`windows/runtime/compatibility.patch`。最新源码快照包含 Android 后续修复；它与现有 Windows Release 的运行程序版本不同。Windows ZIP 已验证第一关战斗和存档重读，Android 真机运行仍待验证。
