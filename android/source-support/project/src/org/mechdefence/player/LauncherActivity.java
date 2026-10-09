/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. https://mozilla.org/MPL/2.0/ */
package org.mechdefence.player;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.os.Bundle;
import android.util.Log;
import android.view.Gravity;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.security.MessageDigest;

public class LauncherActivity extends Activity {
    private TextView status;
    private boolean preparing;
    private static final int EXPORT_LOG = 1;

    @Override
    public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setGravity(Gravity.CENTER);
        int pad = (int)(24 * getResources().getDisplayMetrics().density);
        layout.setPadding(pad, pad, pad, pad);
        status = new TextView(this);
        status.setTextSize(18);
        status.setGravity(Gravity.CENTER);
        status.setText("Heavy MACH: Defense\n正在准备游戏…");
        layout.addView(status);
        ProgressBar progress = new ProgressBar(this);
        layout.addView(progress);
        Button standard = new Button(this);
        standard.setText("开始游戏（标准画质）");
        standard.setOnClickListener(view -> startGame(2));
        layout.addView(standard);
        Button hd = new Button(this);
        hd.setText("开始游戏（高清画质，推荐）");
        hd.setOnClickListener(view -> startGame(3));
        layout.addView(hd);
        Button ultra = new Button(this);
        ultra.setText("开始游戏（超清画质）");
        ultra.setOnClickListener(view -> startGame(4));
        layout.addView(ultra);
        Button logs = new Button(this);
        logs.setText("导出运行日志");
        logs.setOnClickListener(view -> exportLog());
        layout.addView(logs);
        setContentView(layout);
        preparing = true;
        new Thread(() -> {
            try {
                prepareGame();
                runOnUiThread(() -> {
                    preparing = false;
                    progress.setVisibility(android.view.View.GONE);
                    status.setText("Heavy MACH: Defense\n中文增强版 · 4\n卡顿时可选择标准画质");
                    // Attempt automatic launch only once, so a device-specific
                    // native crash cannot prevent access to settings and logs.
                    if (state == null && !getPreferences(MODE_PRIVATE).getBoolean("started", false)) {
                        getPreferences(MODE_PRIVATE).edit().putBoolean("started", true).apply();
                        startGame(3);
                    }
                });
            } catch (Exception error) {
                Log.e("MechDefense", "Game preparation failed", error);
                runOnUiThread(() -> {
                    preparing = false;
                    progress.setVisibility(android.view.View.GONE);
                    status.setText("游戏准备失败，请重新打开应用。\n" + error.getMessage());
                });
            }
        }, "GamePreparation").start();
    }

    private void prepareGame() throws Exception {
        File root = getExternalFilesDir(null);
        if (root == null) throw new java.io.IOException("应用存储暂不可用");
        File directory = new File(root, "touchHLE_apps");
        if (!directory.isDirectory() && !directory.mkdirs()) throw new java.io.IOException("无法创建游戏目录");
        File game = new File(directory, "MachDefense.ipa");
        String expected = getString(R.string.game_sha256);
        String prepared = getPreferences(MODE_PRIVATE).getString("prepared", "");
        if (expected.equals(prepared) && game.isFile() && game.length() == Long.parseLong(getString(R.string.game_size))) return;
        File temporary = new File(directory, "MachDefense.ipa.part");
        MessageDigest hash = MessageDigest.getInstance("SHA-256");
        try (InputStream input = getAssets().open("game/MachDefense.ipa");
             OutputStream output = new FileOutputStream(temporary)) {
            byte[] buffer = new byte[65536];
            int count;
            while ((count = input.read(buffer)) != -1) {
                output.write(buffer, 0, count);
                hash.update(buffer, 0, count);
            }
        }
        StringBuilder actual = new StringBuilder();
        for (byte value : hash.digest()) actual.append(String.format(java.util.Locale.ROOT, "%02x", value & 255));
        if (!expected.equals(actual.toString())) throw new java.io.IOException("游戏资源校验失败");
        if (!temporary.renameTo(game)) throw new java.io.IOException("无法完成游戏资源准备");
        getPreferences(MODE_PRIVATE).edit().putString("prepared", expected).apply();
    }

    private void startGame(int scale) {
        if (preparing) return;
        File root = getExternalFilesDir(null);
        if (root == null || !new File(root, "touchHLE_apps/MachDefense.ipa").isFile()) return;
        startActivity(new Intent(this, MainActivity.class).putExtra("scale", scale));
    }

    private void exportLog() {
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("text/plain");
        intent.putExtra(Intent.EXTRA_TITLE, "HeavyMachDefense-log.txt");
        startActivityForResult(intent, EXPORT_LOG);
    }

    @Override
    protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request != EXPORT_LOG || result != RESULT_OK || data == null || data.getData() == null) return;
        try (OutputStream output = getContentResolver().openOutputStream(data.getData())) {
            String device = "Model: " + android.os.Build.MANUFACTURER + " " + android.os.Build.MODEL +
                "\nAndroid: " + android.os.Build.VERSION.RELEASE + " (API " + android.os.Build.VERSION.SDK_INT + ")\n" +
                "ABIs: " + java.util.Arrays.toString(android.os.Build.SUPPORTED_ABIS) + "\n\n";
            output.write(device.getBytes("UTF-8"));
            File log = new File(getExternalFilesDir(null), "touchHLE_log.txt");
            if (log.isFile()) {
                try (InputStream input = new java.io.FileInputStream(log)) {
                    byte[] buffer = new byte[65536];
                    int count;
                    while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
                }
            } else output.write("No runtime log was created.\n".getBytes("UTF-8"));
        } catch (Exception error) {
            new AlertDialog.Builder(this).setMessage("日志导出失败：" + error.getMessage())
                .setPositiveButton("确定", null).show();
        }
    }
}
