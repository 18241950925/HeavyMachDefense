/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. https://mozilla.org/MPL/2.0/ */
//! Optional visible-text localization for the dedicated Heavy MACH build.
use crate::Environment;
use std::borrow::Cow;
use crate::font::{Font, TextAlignment};
use crate::image::Image;
use std::collections::HashMap;
use std::rc::Rc;

pub const TEXT_SCALE: u32 = 4;

pub struct Canvas {
    pub data: u32,
    pub dimensions: (u32, u32),
    pub fingerprint: u64,
    pub fingerprint_dirty: bool,
    pub alpha_fingerprint: u64,
    pub alpha_half_fingerprint: u64,
    pub grayscale: bool,
    pub image: Rc<Image>,
    pub uploaded: bool,
}

#[derive(Default)]
pub struct State {
    pub canvases: HashMap<u32, Canvas>,
    pub textures: HashMap<u32, Canvas>,
    pub hd_uploads: u32,
    pub alpha_uploads: u32,
}

pub fn fingerprint(bytes: &[u8]) -> u64 {
    use std::hash::{Hash, Hasher};
    let mut hash = std::collections::hash_map::DefaultHasher::new();
    bytes.hash(&mut hash);
    hash.finish()
}

pub fn alpha_fingerprints(bytes: &[u8]) -> (u64, u64) {
    let alpha: Vec<u8> = bytes.chunks_exact(4).map(|pixel| pixel[3]).collect();
    let half: Vec<u8> = alpha.iter().map(|value| value >> 1).collect();
    (fingerprint(&alpha), fingerprint(&half))
}

/// Snapshot once at upload/release, rather than scanning a whole bitmap after
/// every image, label, and fill used to build a menu atlas.
fn refresh_fingerprints(mem: &crate::mem::Mem, canvas: &mut Canvas) {
    if !canvas.fingerprint_dirty { return; }
    let size = canvas.dimensions.0 * canvas.dimensions.1 * if canvas.grayscale { 1 } else { 4 };
    let pixels = mem.bytes_at(crate::mem::ConstPtr::<u8>::from_bits(canvas.data), size);
    canvas.fingerprint = fingerprint(pixels);
    (canvas.alpha_fingerprint, canvas.alpha_half_fingerprint) = if canvas.grayscale {
        let half: Vec<u8> = pixels.iter().map(|value| value >> 1).collect();
        (canvas.fingerprint, fingerprint(&half))
    } else { alpha_fingerprints(pixels) };
    canvas.fingerprint_dirty = false;
}

/// Text is uploaded either directly from a grayscale bitmap, or from
/// ImageAttacher.makeAlphaTile's copied and halved RGBA alpha channel.
/// Match contents because the upload buffer may use a different allocation.
pub fn alpha_texture(env: &mut Environment, data: u32, width: i32, height: i32) -> Option<(Rc<Image>, bool, bool)> {
    if !enabled(env) || width <= 0 || height <= 0 { return None; }
    let size = (width as u32).checked_mul(height as u32)?;
    let hash = fingerprint(env.mem.bytes_at(crate::mem::ConstPtr::<u8>::from_bits(data), size));
    let state = &mut env.framework_state.uikit.localization;
    for canvas in state.canvases.values_mut().chain(state.textures.values_mut()) {
        if canvas.dimensions == (width as u32, height as u32) {
            refresh_fingerprints(&env.mem, canvas);
        }
    }
    let matches = |canvas: &&mut Canvas| canvas.dimensions == (width as u32, height as u32)
        && (canvas.alpha_fingerprint == hash || canvas.alpha_half_fingerprint == hash);
    let canvas = if let Some(canvas) = state.canvases.values_mut().find(matches) {
        canvas
    } else {
        state.textures.values_mut().find(matches)?
    };
    let half = canvas.alpha_fingerprint != hash;
    let grayscale = canvas.grayscale;
    let image = canvas.image.clone();
    let old_data = canvas.data;
    canvas.uploaded = true;
    state.textures.remove(&old_data);
    state.alpha_uploads += 1;
    if state.alpha_uploads == 1 { log!("Chinese text: high-resolution alpha font atlas uploaded"); }
    Some((image, half, grayscale))
}

pub fn release_context(env: &mut Environment, context: crate::objc::id) {
    let state = &mut env.framework_state.uikit.localization;
    if let Some(mut canvas) = state.canvases.remove(&context.to_bits()) {
        if !canvas.uploaded {
            // Context deallocation calls here before freeing its guest buffer.
            refresh_fingerprints(&env.mem, &mut canvas);
            // Some loaders release the bitmap context before uploading the
            // caller-owned buffer. Bound the cache and validate its contents.
            if state.textures.len() >= 64 { state.textures.clear(); }
            state.textures.insert(canvas.data, canvas);
        }
    }
}

pub fn texture(env: &mut Environment, data: u32, width: i32, height: i32) -> Option<Rc<Image>> {
    if !enabled(env) || width <= 0 || height <= 0 { return None; }
    let size = (width as u32).checked_mul(height as u32)?.checked_mul(4)?;
    let state = &mut env.framework_state.uikit.localization;
    let canvas = if let Some(canvas) = state.canvases.values_mut().find(|canvas| canvas.data == data) {
        canvas
    } else {
        state.textures.get_mut(&data)?
    };
    if canvas.grayscale || canvas.dimensions != (width as u32, height as u32) {
        return None;
    }
    refresh_fingerprints(&env.mem, canvas);
    if canvas.fingerprint != fingerprint(env.mem.bytes_at(crate::mem::ConstPtr::<u8>::from_bits(data), size)) {
        return None;
    }
    canvas.uploaded = true;
    let image = canvas.image.clone();
    state.textures.remove(&data);
    state.hd_uploads += 1;
    if state.hd_uploads == 1 { log!("Chinese text: uploading textures rendered at {}x resolution", image.dimensions().0 / width as u32); }
    Some(image)
}

pub fn enabled(env: &Environment) -> bool {
    env.options.preferred_languages.as_ref().is_some_and(|languages|
        languages.iter().any(|language| language.starts_with("zh")))
}

pub fn visible<'a>(env: &Environment, text: &'a str) -> Cow<'a, str> {
    if !enabled(env) {
        return Cow::Borrowed(text);
    }
    let translated = match text {
        "Resume Game" => "继续游戏",
        "Save & Exit Game" => "保存并退出",
        "Help" => "帮助",
        "Leader Board" | "LeaderBoard" => "排行榜",
        "Select Slot" => "选择存档",
        "Select Stage" => "选择关卡",
        "SYSTEM MENU" | "System Menu" => "游戏菜单",
        "UPGRADE & EQUIP" => "升级与装备",
        "BGM Vol." => "音乐音量",
        "SFX Vol." => "音效音量",
        "Not enough Cr." => "金币不足。",
        "Tap to attack." => "点击指定攻击位置。",
        "Tap to build." => "点击放置炮台。",
        "Not enough Mach." => "机甲数量不足。",
        "Deleting the slot will permanently destroy all game data in it." => "删除存档会清空全部进度。",
        "Not enough empty slot." => "没有空闲存档位。",
        "Enter your name in 10 or less letters." => "名字最多十个字符。",
        "Kill count" => "击杀数量",
        "Dead count" => "损失数量",
        "MachineGun" => "机枪",
        "HMG" => "重机枪",
        "Missile" => "导弹",
        "HeavyMissile" => "重导弹",
        "ShotGun" => "霰弹枪",
        "PlasmaGun" => "等离子枪",
        "IonRifle" => "离子步枪",
        "RifleTurret" => "机枪炮台",
        "MissileTurret" => "导弹炮台",
        "Vulcan" => "火神炮",
        "IonCannon" => "离子炮",
        "LaserTurret" => "激光炮台",
        "PlasmaCannon" => "等离子炮",
        "Tanker" => "重装机甲",
        "ATK." => "攻击",
        "Range" => "射程",
        "DEF." => "防御",
        "SPD." => "速度",
        "Base Cannon" => "基地火炮",
        "Base Defense" => "基地防御",
        "Build Time" => "生产速度",
        "Cr Research" => "金币研究",
        "Cell Research" => "能量研究",
        "Cell Storage" => "能量上限",
        "NEW" => "新建",
        "BACK" => "返回",
        "DELETE" | "DEL" => "删除",
        "CLOSE" => "关闭",
        "OK" => "确定",
        "YES" => "是",
        "NO" => "否",
        "CANCEL" => "取消",
        "UPGRADE" => "升级",
        "MENU" => "菜单",
        "BASE UPGRADE" => "基地升级",
        "EXIT HELP MENU" => "关闭帮助",
        "TAP TO START GAME" => "点击开始游戏",
        "Create Date" => "创建日期",
        "Last Access" => "上次游玩",
        "Player" => "玩家",
        "FULL    " | "FULL" => "已满",
        "Stage Clear Bonus!" => "通关奖励！",
        "You've got a new Mach." => "获得了新的机甲。",
        "Missile Launcher" => "导弹发射器",
        "Body Parts" => "机身部件",
        "Foot Parts" => "足部部件",
        "Equip Parts" => "装备部件",
        "Repair Kit" => "维修工具",
        "Special Attack" => "特殊攻击",
        "Special Item" => "特殊道具",
        "Attacker BOT" => "攻击机器人",
        "Defender BOT" => "防御机器人",
        "Item Picker BOT" => "拾取机器人",
        "Repair BOT" => "维修机器人",
        "Incorrect Name" => "名字无效",
        "New User" => "新建存档",
        "Name: 1~10 Character" => "名字需为一至十个字符",
        "Not Exist Empty Slot" => "没有空闲存档位",
        "Delete Slot" => "删除存档",
        "Support" => "支持",
        "More Games" => "更多游戏",
        _ => {
            if text.contains('\n') {
                let lines: Vec<_> = text.split('\n').map(|line| visible(env, line)).collect();
                if lines.iter().any(|line| matches!(line, Cow::Owned(_)))
                    || lines.iter().zip(text.split('\n')).any(|(a, b)| a.as_ref() != b) {
                    return Cow::Owned(lines.iter().map(|line| line.as_ref()).collect::<Vec<_>>().join("\n"));
                }
            }
            for (original, chinese) in [
                ("ATK. : ", "攻击："), ("DEF. : ", "防御："), ("SPD. : ", "速度："),
                ("Atk ", "攻击 "), ("HP : ", "耐久："), ("Def : ", "防御："),
                ("Speed : ", "速度："), ("Price : ", "价格："), ("SellPrice : ", "售价："),
                ("Attack Point : ", "伤害："), ("Damage Range : ", "范围："),
                ("Count : ", "数量："), ("Size : ", "容量："), ("Play Time : ", "时间："),
                ("Kill count : ", "击杀："), ("Dead count : ", "损失："),
            ] {
                if let Some(value) = text.strip_prefix(original) {
                    return Cow::Owned(format!("{chinese}{value}"));
                }
            }
            if let Some((name, level)) = text.rsplit_once("  Lv. ") {
                return Cow::Owned(format!("{} 等级{level}", visible(env, name)));
            }
            if let Some(value) = text.strip_prefix("Lv. ") {
                return Cow::Owned(format!("等级 {value}"));
            }
            for prefix in ["Stage. ", "Stage ", "Stage"] {
                if let Some(number) = text.strip_prefix(prefix).and_then(|value| value.trim().parse::<u32>().ok()) {
                    if (1..=80).contains(&number) {
                        return Cow::Owned(format!("第{number}关"));
                    }
                }
            }
            return Cow::Borrowed(text);
        }
    };
    Cow::Borrowed(translated)
}

/// Render translated captions into the original UI skins at load time.
/// The IPA bytes and all sprite-sheet dimensions remain intact.
pub fn localize_image(env: &Environment, path: &str, image: Image) -> Image {
    if !enabled(env) { return image; }
    let normalized = path.rsplit('/').next().unwrap_or(path).replace("@2x", "");
    let name = normalized.as_str();
    let (width, height) = image.dimensions();
    if name.contains("HelpScr") { return help_image(name, image); }
    let (caption, boxes): (&str, Vec<(u32, u32, u32, u32)>) = if name.starts_with("Common_Btn_") {
        let word = name.strip_prefix("Common_Btn_").unwrap().trim_end_matches(".png");
        let caption = match word {
            "BACK" => "返回", "NEW" => "新建", "DEL" => "删除", "CLOSE" => "关闭",
            "CANCEL" => "取消", "OK" => "确定", "YES" => "是", "NO" => "否",
            "EXIT" => "退出", "NEXT" => "下一项", "PREV" => "上一项", "RANKING" => "排行",
            _ => return image,
        };
        (caption, (0..height / 64).map(|row| (12, row * 64 + 14, width - 12, row * 64 + 50)).collect())
    } else if name.starts_with("Btn_BaseUpgrade_") {
        let caption = match name {
            "Btn_BaseUpgrade_BaseDefense.png" => "基地防御",
            "Btn_BaseUpgrade_BaseCannon.png" => "基地火炮",
            "Btn_BaseUpgrade_BuildTime.png" => "生产速度",
            "Btn_BaseUpgrade_CrResearch.png" => "金币研究",
            "Btn_BaseUpgrade_CellResearch.png" => "能量研究",
            "Btn_BaseUpgrade_CellStorage.png" => "能量上限",
            _ => return image,
        };
        (caption, (0..height / 64).map(|row| (64, row * 64 + 12, 216, row * 64 + 50)).collect())
    } else if name == "Btn_UpgradeBase_Close.png" || name == "Btn_UpgradeBase_Upgrade.png" {
        (if name.contains("Close") { "关闭" } else { "升级" },
         (0..height / 64).map(|row| (20, row * 64 + 12, width - 20, row * 64 + 50)).collect())
    } else if name == "SysMenu_Top.png" {
        ("游戏菜单", vec![(112, 20, 400, 63)])
    } else if name == "CommonUI_Upgrade.png" || name == "CommonUI_Summary.png" || name == "CommonUI_Defeat.png" {
        (match name { "CommonUI_Upgrade.png" => "升级与装备", "CommonUI_Summary.png" => "战斗结果", _ => "战斗失败" },
         vec![(80, 12, width - 80, height - 2)])
    } else if name == "CommonUI_StageClear.png" {
        ("关卡完成", vec![(32, 8, width - 32, height - 4)])
    } else if name.starts_with("SummaryBtn_") {
        let caption = match name {
            "SummaryBtn_NextStage.png" => "下一关", "SummaryBtn_SelectStage.png" => "选关",
            "SummaryBtn_Retry.png" => "重试", "SummaryBtn_ExitGame.png" => "退出",
            "SummaryBtn_LeaderBoard.png" => "排行", _ => return image,
        };
        (caption, (0..height / 32).map(|row| (14, row * 32 + 2, width - 14, row * 32 + 27)).collect())
    } else if name.starts_with("UpgradeBtn_") {
        let caption = match name { "UpgradeBtn_Buy.png" => "购买", "UpgradeBtn_Upgrade.png" => "升级",
            "UpgradeBtn_Install.png" => "装配", "UpgradeBtn_Uninstall.png" => "卸下", _ => return image };
        let (top, bottom) = if matches!(name, "UpgradeBtn_Buy.png" | "UpgradeBtn_Upgrade.png") { (30, 52) } else { (14, 48) };
        (caption, (0..height / 64).map(|row| (30, row * 64 + top, width - 18, row * 64 + bottom)).collect())
    } else if name == "UiTitle.png" {
        ("", vec![(12, 0, 244, 31), (12, 32, 244, 63), (12, 64, 244, 95)])
    } else if name.starts_with("iPon_SelSlot_Sel") || name.starts_with("iPad_SelSlot_Sel") {
        let factor = width as f32 / 256.0;
        ("", (0..2).flat_map(|row| [(24, row*128+51, 84, row*128+63),
                                   (24, row*128+69, 91, row*128+81),
                                   (165, row*128+58, 203, row*128+72)])
            .map(|(a,b,c,d)| ((a as f32*factor) as u32, (b as f32*factor) as u32,
                             (c as f32*factor) as u32, (d as f32*factor) as u32)).collect())
    } else if name == "GameUI_HpGauge.png" {
        ("", vec![(20, 4, 75, 23), (444, 4, 494, 23)])
    } else if name.starts_with("iPon_QuickBtn") || name.starts_with("iPad_QuickBtn") {
        let factor = width as f32 / 256.0;
        ("", vec![(36, 5, 92, 22), (164, 5, 220, 22), (36, 37, 92, 54), (164, 37, 220, 54)]
            .into_iter().map(|(a,b,c,d)| ((a as f32*factor) as u32, (b as f32*factor) as u32,
                                      (c as f32*factor) as u32, (d as f32*factor) as u32)).collect())
    } else if name.starts_with("iPon_SelSlot_BG") || name.starts_with("iPad_SelSlot_BG") {
        let factor = width as f32 / 320.0;
        ("选择存档", vec![( (100.0*factor) as u32, (24.0*factor) as u32,
                           (232.0*factor) as u32, (60.0*factor) as u32 )])
    } else if name.starts_with("iPon_SelStage_Fore") || name.starts_with("iPad_SelStage_Fore") {
        let factor = width as f32 / 320.0;
        ("选择关卡", vec![((96.0*factor) as u32, (23.0*factor) as u32, (248.0*factor) as u32, (60.0*factor) as u32)])
    } else { return image; };
    let original_size = (width, height);
    let scale = TEXT_SCALE;
    let image = image.enlarged(scale);
    let (width, height) = image.dimensions();
    let font = Font::sans_chinese(true);
    let mut pixels = image.pixels().to_vec();
    for (x0, y0, x1, y1) in boxes {
        let caption = if name == "UiTitle.png" { match y0 { 0 => "生产机甲", 32 => "特殊攻击", _ => "编队控制" } }
            else if name.contains("SelSlot_Sel") {
                let factor = original_size.0 as f32 / 256.0;
                if x0 as f32 / factor > 100.0 { "关卡" }
                else if ((y0 as f32 / factor) as u32) % 128 < 60 { "创建" } else { "游玩" }
            }
            else if name == "GameUI_HpGauge.png" { if x0 < 100 { "我方" } else { "敌方" } }
            else if name.contains("QuickBtn") { if y0 < original_size.1 / 2 { "菜单" } else { "基地升级" } }
            else { caption };
        let (x0,y0,x1,y1) = (x0*scale,y0*scale,x1*scale,y1*scale);
        if x1 >= width || y1 >= height || x1 <= x0 || y1 <= y0 { continue; }
        let mut brightness = 0u8;
        let mut visible = false;
        for y in y0..y1 {
            for x in x0..x1 {
                let offset = ((y * width + x) * 4) as usize;
                visible |= pixels[offset + 3] > 0;
                brightness = brightness.max(pixels[offset].min(pixels[offset+1]).min(pixels[offset+2]));
            }
        }
        if !visible { continue; }
        // Sample each side of the caption on the same row, retaining the
        // original skin's gradient, border and active/disabled state.
        for y in y0..y1 {
            let left = ((y * width + x0 - 3) * 4) as usize;
            let right = ((y * width + x1 + 2) * 4) as usize;
            let a: [u8;4] = pixels[left..left+4].try_into().unwrap();
            let b: [u8;4] = pixels[right..right+4].try_into().unwrap();
            for x in x0..x1 {
                let offset = ((y * width + x) * 4) as usize;
                let factor = (x - x0) as f32 / (x1 - x0) as f32;
                for channel in 0..4 {
                    pixels[offset+channel] = if name == "UiTitle.png" { 0 }
                        else { ((a[channel] as f32)*(1.0-factor) + (b[channel] as f32)*factor) as u8 };
                }
            }
        }
        let size = ((y1-y0) as f32 * 0.66).min((x1-x0) as f32 / caption.chars().count() as f32 * 0.85);
        let (_, text_height) = font.calculate_text_size(size, caption, None);
        let origin = ((x0+x1) as f32/2.0, y0 as f32 + ((y1-y0) as f32-text_height)/2.0);
        let level = if name == "GameUI_HpGauge.png" { 35.0 } else { brightness.max(165) as f32 };
        for (offset, color) in [(scale as f32 * 0.5, 0.0), (0.0, level)] {
            font.draw(size, caption, (origin.0+offset, origin.1+offset), None, TextAlignment::Center, |glyph| {
                let (gx,gy) = glyph.origin();
                let (gw,gh) = glyph.dimensions();
                for y in 0..gh { for x in 0..gw {
                    let px = gx.round() as i32+x; let py = gy.round() as i32+y;
                    if px<0 || py<0 || px>=width as i32 || py>=height as i32 { continue; }
                    let alpha = glyph.pixel_at((x,y));
                    let index = ((py as u32*width+px as u32)*4) as usize;
                    for channel in 0..3 {
                        pixels[index+channel] = (color*alpha + pixels[index+channel] as f32*(1.0-alpha)) as u8;
                    }
                    pixels[index+3] = (255.0*alpha + pixels[index+3] as f32*(1.0-alpha)) as u8;
                }}
            });
        }
    }
    finish_image(Image::from_pixel_vec(pixels, (width,height)), original_size)
}

fn finish_image(high_resolution: Image, dimensions: (u32, u32)) -> Image {
    let (width, height) = dimensions;
    let (hd_width, _) = high_resolution.dimensions();
    let scale = hd_width / width;
    if scale == 1 { return high_resolution; }
    let mut pixels = vec![0; (width * height * 4) as usize];
    for y in 0..height { for x in 0..width {
        let mut sum = [0u32; 4];
        for dy in 0..scale { for dx in 0..scale {
            let at = (((y*scale+dy)*hd_width+x*scale+dx)*4) as usize;
            for c in 0..4 { sum[c] += high_resolution.pixels()[at+c] as u32; }
        }}
        let at = ((y*width+x)*4) as usize;
        for c in 0..4 { pixels[at+c] = (sum[c] / (scale*scale)) as u8; }
    }}
    let mut image = Image::from_pixel_vec(pixels, dimensions);
    image.set_high_resolution(Rc::new(high_resolution));
    image
}

fn paint_text(image: &mut Image, font: &Font, text: &str, size: f32, x: f32, y: f32, wrap: Option<f32>, center: bool) {
    let (width, height) = image.dimensions();
    let pixels = image.pixels_mut();
    font.draw(size, text, (x,y), wrap.map(|w| (w, crate::font::WrapMode::Char)),
        if center { TextAlignment::Center } else { TextAlignment::Left }, |glyph| {
            let (gx,gy) = glyph.origin();
            let (gw,gh) = glyph.dimensions();
            for y in 0..gh { for x in 0..gw {
                let px = gx.round() as i32 + x;
                let py = gy.round() as i32 + y;
                if px < 0 || py < 0 || px >= width as i32 || py >= height as i32 { continue; }
                let alpha = glyph.pixel_at((x,y));
                let at = ((py as u32*width+px as u32)*4) as usize;
                for c in 0..3 { pixels[at+c] = (235.0*alpha + pixels[at+c] as f32*(1.0-alpha)) as u8; }
                pixels[at+3] = 255;
            }}
        });
}

fn help_image(name: &str, original: Image) -> Image {
    let dimensions = original.dimensions();
    // Recreate the original eight help pages with Chinese text. The main
    // page's navigation rows remain at the original touch coordinates.
    let (title, body) = if name.contains("Main") { ("游戏帮助", "") }
        else if name.contains("01_") { ("能量与金币", "能量（cell）用于生产机甲和使用特殊攻击，会随时间恢复。\n\n金币（Cr）用于升级机甲、购买道具和强化基地。击败敌人可以获得金币。\n\n右上方显示当前能量与上限，左下方显示金币余额。") }
        else if name.contains("02_") { ("三个控制按钮", "屏幕底部的三个按钮分别用于：\n\n生产机甲：点选右侧槽位中的机甲。\n\n特殊攻击：选择已装配的技能。\n\n金币购买：原版 iOS 内购入口，本移植版已停用。\n\n点击升级与装备按钮，可以更换右侧槽位的内容。") }
        else if name.contains("03_") { ("左侧战场信息", "顶部的两条耐久条分别表示我方与敌方基地的耐久。\n\n左侧小地图显示双方单位的位置。点击地图，可以快速移动战场视角。\n\n生产中的机甲会显示在队列里。\n\n左下方显示关卡编号和当前金币。") }
        else if name.contains("04_") { ("右侧装备槽", "右上方显示当前能量与最大容量。\n\n右侧槽位显示当前装配的机甲或特殊攻击，点击对应图标即可使用。\n\n升级与装备：强化机甲、购买道具并装配到槽位。\n\n菜单：继续游戏、查看帮助或保存退出。\n\n基地升级：强化我方基地。") }
        else if name.contains("05_") { ("升级与装配机甲", "通关后会随机获得新的机甲。\n\n在升级与装备界面选中机甲，左侧显示当前属性及升级后的变化。\n\n升级：消耗金币提高机甲等级。\n\n装配：将选中的机甲放入右侧槽位。\n\n卸下：从槽位中移除，机甲仍保留在列表里。") }
        else if name.contains("06_") { ("特殊攻击", "特殊攻击能够更快地击败敌人。推进关卡可以获得更多种类。\n\n购买：消耗金币补充使用次数。\n\n升级：消耗金币强化效果。\n\n装配后，切换到底部的特殊攻击按钮，再点击右侧技能图标。部分技能需要点击战场指定目标。") }
        else { ("强化我方基地", "基地火炮：提高基地的攻击力。\n\n基地防御：提高基地的防御能力。\n\n生产速度：缩短机甲生产时间。\n\n金币研究：提高击败敌人获得的金币。\n\n能量研究：加快能量恢复。\n\n能量上限：提高最大储量。") };
    let sampling = if dimensions.0 > 512 { 1 } else { TEXT_SCALE };
    let scale = dimensions.0 as f32 / 320.0 * sampling as f32;
    let width = dimensions.0 * sampling;
    let height = dimensions.1 * sampling;
    let mut pixels = vec![0; (width*height*4) as usize];
    for y in 0..height { for x in 0..width {
        let at = ((y*width+x)*4) as usize;
        let border = x < 4 || y < 4 || x >= width-4 || y >= height-4;
        pixels[at..at+4].copy_from_slice(if border { &[38,154,166,255] } else { &[18,27,33,255] });
    }}
    let mut image = Image::from_pixel_vec(pixels, (width,height));
    let font = Font::sans_chinese(true);
    paint_text(&mut image, &font, title, 21.0*scale, 160.0*scale, 58.0*scale, None, true);
    if name.contains("Main") {
        for (index, text) in ["能量与金币", "三个控制按钮", "左侧战场信息", "右侧装备槽", "升级与装配机甲", "特殊攻击", "强化我方基地"].iter().enumerate() {
            paint_text(&mut image, &font, text, 13.0*scale, 160.0*scale, (151.0+index as f32*27.0)*scale, None, true);
        }
    } else {
        paint_text(&mut image, &Font::sans_chinese(false), body, 13.0*scale, 34.0*scale, 109.0*scale, Some(252.0*scale), false);
    }
    paint_text(&mut image, &font, "<", 24.0*scale, 12.0*scale, 236.0*scale, None, true);
    paint_text(&mut image, &font, ">", 24.0*scale, 308.0*scale, 236.0*scale, None, true);
    paint_text(&mut image, &font, "返回目录", 12.0*scale, 160.0*scale, 18.0*scale, None, true);
    paint_text(&mut image, &font, "关闭帮助", 13.0*scale, 160.0*scale, 431.0*scale, None, true);
    paint_text(&mut image, &font, "翻页可查看各项说明", 10.0*scale, 160.0*scale, 399.0*scale, None, true);
    finish_image(image, dimensions)
}
