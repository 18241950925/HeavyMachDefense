# Windows 适配验证记录

## 中文高清版 1.0.3-zh4（2026-10-09）

同步 Android 中文增强版的完整共用兼容层，Windows 启动器默认使用 `zh,en`，随包提供相同的两款简体中文字体和 OFL 许可。测试使用 `verification-data/graphics-test/` 内独立存档，未覆盖玩家运行目录中的存档。

本次检查：

- Windows x64 运行程序和启动器编译成功，实际通过启动器进入游戏。4 倍全屏日志为内部 `1280×1920`，启用 Windows DPI 支持；鼠标点击位置正常。
- 默认窗口自动选择 2 倍渲染，客户区为 `640×960`，可通过[中文菜单](screenshots/zh4-window-menu.png)操作游戏。
- 点击“保存并退出”、关闭测试程序，再次通过启动器重开后，[存档选择](screenshots/zh4-reloaded-slots.png)仍显示 `33 Cr` 和更新后的游玩时间，能进入[关卡选择](screenshots/zh4-reloaded-stages.png)。本次生成的 42,496 字节存档解码校验通过，校验值 `18574`。
- [关卡选择](screenshots/zh4-stages.png)、[游戏菜单](screenshots/zh4-menu.png)、[基地升级](screenshots/zh4-base.png)及[帮助正文](screenshots/zh4-help-page1.png)的汉化、简体字和小字排版正常，没有观察到方框或缺字。日志确认 RGBA 高清贴图与灰度高清文字贴图两条路径均启用。
- [战场](screenshots/zh4-battle.png)右侧机枪、导弹、重装机甲和机枪炮台四个图标正常；[特殊攻击](screenshots/zh4-skills.png)的三个技能图标正常。
- 选择机枪进入[生产队列](screenshots/zh4-production.png)，随后观察到已生产机甲与敌人[交火](screenshots/zh4-combat.png)。
- 连续点击底部旧内购入口两次，均收到原游戏取消回调；[点击后](screenshots/zh4-purchase-2.png)能量继续恢复，战斗与生产可继续，不需要另点菜单解除等待。
- 本次 4 倍渲染的单次计时，首次基地升级菜单完整显示约 `5.30 s`，[再次打开](screenshots/zh4-base-warm.png)约 `2.64 s`，数据见 [首次](base-performance.json)、[再次](base-performance-warm.json)。计时包含动画，受本机桌面负载影响；本次没有在相同负载下重新测试旧版本。源码已包含 Android 版的画布指纹延后计算、兼容不透明像素直接绘制和精确颜色转换缓存；仍有首次资源准备开销。

当前版本主要菜单、升级、属性、结算与帮助已汉化，少量英文标签仍保留；原版美术细节受素材分辨率限制。Windows 后续关卡、其他硬件兼容性和 Android 真机运行仍未逐项验证。原英文版的验证记录保留如下。

## 历史英文版验证（2026-10-06）

验证日期：2026-10-06。测试环境为当前 Windows x64 工作站，NVIDIA GeForce RTX 3060 Laptop GPU，OpenGL 4.6；尚未在其他电脑验证。

原安装包为 Heavy MACH: Defense 1.0.3，最低系统 iOS 4.3，未加密 ARMv7 程序。IPA SHA-256：`882fe8efa9a0c3d51c23da190ee3d30376a1b6766e16cc6b87daf09b98dc92b1`。

已完成以下实际检查：

- 编译并运行 Windows x64 兼容层和原生启动器，窗口模式可显示原版标题、存档选择和关卡选择界面。
- 使用 `NEW` 建立原版存档，保存名为 `Player`；测试了两个独立存档槽。
- 进入第一关，显示战场、双方基地、能量槽、生产菜单和帮助界面。
- 生产 MachineGun 机甲并连续排队；观察到单位移动、敌我交火、弹药与爆炸、基地生命减少、击毁敌人后的资源奖励。
- 打开原版系统菜单及 `UPGRADE & EQUIP` 界面。
- 打开 `BASE UPGRADE`，核对带正号的升级属性能正常显示；修复了该菜单触发的旧 printf 格式兼容问题。见 [基地升级截图](screenshots/base-upgrade.png)。
- 从 `Save & Exit Game` 退出，关闭程序，再通过 Windows 启动器重新打开；存档界面仍显示第一关获得的 `23 Cr`。见 [存档重读截图](screenshots/reloaded-slot.png)。
- 读取实际生成的 42,496 字节存档，按原保存路径的加密方式解码后校验通过；该测试文件已留在工作区 `verification-data/`，交付包不预置测试进度。
- 全屏启动成功，游戏保持原版竖屏比例，左右留黑边。
- 高清全屏：在 1920×1080 屏幕上，启动器自动选择 3 倍渲染，内部画面为 960×1440；高 DPI 支持生效。已进入第一关，生产机甲并打开基地升级菜单，鼠标点击位置正常。见 [高清战场](screenshots/battle-hd.png) 与 [高清标题](screenshots/fullscreen-hd.png)。本次交互测试使用独立的 `verification-data/graphics-test/` 存档目录。
- 高清窗口：自动选择 2 倍渲染，实际客户区为 640×960，完整显示于当前屏幕内。见 [窗口截图](screenshots/window-hd.png)。也验证了 `--scale=1` 可恢复原始分辨率。
- 核对全部 1,109 张游戏图片、80 个音频文件与 IPA 中内容逐字节一致。94 个表格资源已解密，已知明文表的全部 4,059 字节完全匹配。

战斗画面见 [battle.png](screenshots/battle.png)。二进制与资源校验结果保存在 [integrity.json](integrity.json)，准备过程记录在 [preparation.json](preparation.json)。兼容层的全部本地源码改动见 [compatibility.patch](runtime/compatibility.patch)。

本次验证覆盖第一关的游玩流程，尚未完成全部 80 关的逐关通关测试，也尚未在其他硬件上检查音频和显示兼容性。英文界面的部分字体使用替代字体，新存档名固定为 `Player`。旧广告已关闭，在线排行和应用内购买尚未适配。原安装包引用的个别空图片由兼容层按空图处理。
