# Heavy MACH: Defense Windows 与 Android 适配

从 [最新 Release](https://github.com/18241950925/HeavyMachDefense/releases/latest) 下载游玩包：

| 平台 | 下载文件 | 当前版本 |
| --- | --- | --- |
| Windows x64 | `HeavyMachDefense-Windows.zip` | `1.0.3-zh4` 中文高清便携版，支持自动分辨率、全屏和 DPI 缩放 |
| Android ARM64 | `HeavyMachDefense-arm64.apk` | `1.0.3-zh4` 中文修复版，Android 5.0 及以上 |

Android 安装和画质设置见 [android/安装说明.md](android/安装说明.md)。本地安装包仍位于 `android/HeavyMachDefense-arm64.apk`；已安装旧版时直接覆盖安装，保留存档。目前尚未进行安卓真机测试。

Windows 与 Android 均包含汉化、简体字和高清文字、机甲及技能图标、购买按钮卡住修复，并优化首次基地升级加载。Windows 新版已同步共用兼容层；更新时保留原目录的 `runtime/touchHLE_sandbox` 存档文件夹。

工作区原文件为 `MachDefense v1.0.3 - (com.wemadeent.HeavyMachDefence).ipa`。Info.plist 确认最低系统版本为 iOS 4.3，程序为未加密的 ARMv7 Mach-O。

Windows 游玩包解压后运行 `HeavyMachDefense.exe`，操作说明见 [windows/游玩说明.md](windows/游玩说明.md)。实际验证结果见 [windows/verification.md](windows/verification.md)。

本地便携压缩包为 `HeavyMachDefense-Windows.zip`，解压后双击其中的 `HeavyMachDefense.exe`。无需安装开发工具。当前版本实测了第一关出兵、战斗与存档重读，后续关卡尚未逐关验证。

启动器已支持根据屏幕尺寸自动提高渲染分辨率和 Windows 高 DPI 缩放。`windows/Fullscreen.cmd` 使用自动高清全屏，手动调整可编辑 `windows/Display.ini`。

适配使用原版游戏程序和资源，通过本地修改的 [touchHLE](https://github.com/touchHLE/touchHLE) 执行。网络搜索还找到了 [Mesabloo/hm-defense](https://github.com/Mesabloo/hm-defense)，它是尚未完成的社区重写项目，仅保留作参考，没有用它替换原版战斗逻辑。

源码与目录（GitHub 仓库不包含本地原 IPA、存档、签名密钥及开发工具缓存）：

- `original/`：本地 IPA 解包内容，用于分析和校验。
- `windows/`：本地运行目录；仓库保留显示配置、操作说明、验证记录及当前兼容层补丁。
- `tools/prepare_windows.py`：从原 IPA 重新生成适配游戏包，按原程序 SHA-256 检查版本。
- `tools/launcher.cpp`：Windows 启动器源码。
- `tools/build_launcher.ps1`：使用 MinGW 编译启动器及图标。
- `tools/build_runtime.ps1`：使用工作区内 Rust 工具链、Visual Studio C++ 和 CMake 编译兼容层。
- `reference/touchHLE/`：修改后的完整兼容层源码；依赖通过固定版本 Git 子模块提供。
- `android/project/`：Android 启动器源码；`android/source-support/`：中文修复版补丁与构建资料。
- `reference/hm-defense/`：仅在本地保留的社区项目参考。

完整构建准备见 [BUILD.md](BUILD.md)，第三方来源和许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。在原工作区根目录重新生成 Windows 包的流程如下；GitHub 源码下载后需先准备依赖、原 IPA 和运行目录：

```powershell
python tools/prepare_windows.py
powershell -NoProfile -ExecutionPolicy Bypass -File tools/build_runtime.ps1
Copy-Item reference/touchHLE/target/release/touchHLE.exe windows/runtime/touchHLE.exe
powershell -NoProfile -ExecutionPolicy Bypass -File tools/build_launcher.ps1
python tools/verify_windows.py
python tools/package_windows.py
```

预编译的 Windows 目录不需要这些开发工具。原 IPA、游戏美术和声音归原作者所有；touchHLE 的许可与依赖声明保存在运行目录中。
