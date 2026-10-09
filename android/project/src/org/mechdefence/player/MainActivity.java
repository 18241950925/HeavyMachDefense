/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. https://mozilla.org/MPL/2.0/ */
package org.mechdefence.player;

import org.libsdl.app.SDLActivity;
import java.io.File;

public class MainActivity extends SDLActivity {
    @Override
    protected String[] getLibraries() {
        return new String[]{"SDL2", "touchHLE"};
    }

    @Override
    protected String[] getArguments() {
        File root = getExternalFilesDir(null);
        File game = new File(root, "touchHLE_apps/MachDefense.ipa");
        int scale = Math.max(2, Math.min(4, getIntent().getIntExtra("scale", 3)));
        return new String[]{game.getAbsolutePath(), "--device-family=iphone",
            "--preferred-languages=zh,en", "--scale-hack=" + scale, "--fullscreen"};
    }
}
