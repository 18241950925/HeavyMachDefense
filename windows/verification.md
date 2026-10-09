# Windows 适配验证记录

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
