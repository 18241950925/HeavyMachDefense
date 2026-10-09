# Local compatibility runtime

Upstream: https://github.com/touchHLE/touchHLE

Base commit: `d34530b52174e8a4f1fe43178cc4fb0c99506f9f`.

This is a locally modified Windows x64 build, not an official touchHLE release. The complete source checkout is retained at `../../reference/touchHLE` relative to this file. `compatibility.patch` contains all local runtime changes against the upstream commit above, including the new NSOutputStream source file. Its MPL-2.0 license and bundled library/font notices are retained alongside this executable.

Changes needed by Heavy MACH: Defense 1.0.3:

- Implement NSMutableArray.removeObjectsInArray: using a retained snapshot.
- Make selector-based sorted copies available for mutable array receivers.
- Forward UIScreen.displayLinkWithTarget:selector: to the existing CADisplayLink implementation.
- Handle zero as the legacy default display-link frame interval.
- Implement UIKit bitmap image contexts and image snapshots.
- Allow absent images in atlas size queries and drawing.
- Implement legacy CGContext font selection and ASCII text drawing for game labels.
- Include object identity and expected type in missing-host-object diagnostics.
- Implement synchronous NSOutputStream file writes for the original save writer.
- Report the original guest assertion message through __assert_rtn.
- Support signed integer formatting such as %+d used by base upgrade bonuses.
- Share Android 1.0.3-zh4's Chinese captions, bundled Simplified Chinese fonts,
  four-times text rendering, and RGBA / alpha texture atlas handling.
- Mirror ordinary image, fill and clear operations into high-resolution canvases
  so all four mech icons and the three skill icons remain visible.
- Defer cancellation of this game's unavailable iOS purchase alert until its
  initiating call returns, delivering the original Cancel callback to resume battle.
- Hash menu canvases once at upload / release, directly copy compatible opaque
  pixels, and cache exact 8-bit gamma conversions to reduce first-open menu work.

The original ARM game has a small patch to NEW: it calls the original save creation routine with the name Player, because touchHLE's UIAlertView text input UI is unimplemented. Preparation also removes the obsolete iAd view dependency, fixes startup orientation, and decrypts the 94 QTable files with the verified Darwin random() sequence. The original IPA remains unchanged.

`source-support/` includes the launcher and game preparation sources. The Windows package also includes the Microsoft Visual C++ 2022 x64 runtime DLLs from the installed redistributable (14.44.35112). These are Microsoft components, not part of touchHLE's MPL license. See Microsoft's redistribution terms: https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files

The launcher selects --preferred-languages=zh,en and the existing --scale-hack
option based on monitor size (or Display.ini), enables SDL's per-monitor-v2 DPI
awareness, and accepts --fullscreen, --windowed and --scale=0..6. This Windows
Chinese edition ships the current shared compatibility runtime and Mech Sans SC
fonts with their OFL notice. The original game resources and save format are retained.
