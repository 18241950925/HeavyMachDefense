# 第三方来源与许可

- 原游戏为 Heavy MACH: Defense 1.0.3，包名 `com.wemadeent.HeavyMachDefence`。原游戏程序、图片、声音和关卡归原作者所有，本项目未取得原版游戏源码。游玩包保留原版程序与资源。
- 兼容层来自 [touchHLE](https://github.com/touchHLE/touchHLE)，上游基线 `d34530b52174e8a4f1fe43178cc4fb0c99506f9f`。本地修改后的源码保存在 `reference/touchHLE/`，遵循其中的 MPL-2.0 许可和逐文件声明。它不是 touchHLE 官方发布。
- SDL、Dynarmic、OpenAL Soft、stb 及其依赖保留各自许可，来源和固定版本见 `.gitmodules`、`source-manifest.json` 与各依赖目录。
- 简体中文字体由 Google Fonts 的 Noto Sans SC 派生，使用 SIL Open Font License 1.1。原字体来源和 SHA-256 见 `android/chinese-fonts/source.json`，许可见 `android/chinese-fonts/LICENSE.noto-sc`。兼容层提供的其他字体许可保留在 `reference/touchHLE/touchHLE_fonts/`。
- Windows 游玩包包含 Microsoft Visual C++ 运行库；这些文件不属于 touchHLE 的 MPL 许可。
- [Mesabloo/hm-defense](https://github.com/Mesabloo/hm-defense) 曾用于分析参考，未作为当前游玩版本的游戏引擎。

安装包内的第三方声明继续保留。本仓库没有为原游戏资源重新授予开源许可。
