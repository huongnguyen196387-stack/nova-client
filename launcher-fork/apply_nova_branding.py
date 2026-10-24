#!/usr/bin/env python3
"""
Biến bản clone LeviLaunchroid thành launcher riêng (fork) có sẵn Nova Client.

  python apply_nova_branding.py <thư-mục-repo-LeviLaunchroid> \
      --name "Nova Launcher" --app-id com.yourname.novalauncher \
      --levipack path/to/nova_client-0.1.0-arm64-v8a.levipack

Script chỉ sửa 3 thứ, chạy lại nhiều lần vẫn an toàn (idempotent):
  1. applicationId trong app/build.gradle   (namespace/package code giữ nguyên để JNI không vỡ)
  2. app_name trong mọi res/values*/strings.xml
  3. (tuỳ chọn) nhúng .levipack vào assets + NovaBootstrap tự cài mod ở lần mở đầu tiên
Icon: tự thay các file res/mipmap-*/ic_launcher*.png (script không đụng tới).
"""
import argparse, pathlib, re, shutil, sys

JAVA = '''package org.levimc.launcher.nova;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.util.Log;

import org.levimc.launcher.core.mods.FileHandler;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.List;

/** Tự cài mod đóng gói sẵn trong assets (một lần cho mỗi phiên bản gói). */
public final class NovaBootstrap {
    private static final String TAG = "NovaBootstrap";
    private static final String PREFS = "nova_bootstrap";
    private static final String KEY_INSTALLED = "installed_fingerprint";
    private static final String ASSET = "nova/nova_client.levipack";

    private NovaBootstrap() {}

    public static void installOnce(Context context, FileHandler fileHandler) {
        try {
            File out = new File(context.getCacheDir(), "nova_client.levipack");
            long size = copyAsset(context, out);
            String fingerprint = String.valueOf(size);

            SharedPreferences sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            if (fingerprint.equals(sp.getString(KEY_INSTALLED, null))) return;

            Intent intent = new Intent();
            intent.setData(Uri.fromFile(out));
            List<String> versions = new ArrayList<>();
            versions.add("1.26.*");
            fileHandler.processCatalogModDirectly(intent, "Nova Client", "Nova", "bundled", versions,
                    new FileHandler.FileOperationCallback() {
                        @Override public void onSuccess(int processedFiles) {
                            sp.edit().putString(KEY_INSTALLED, fingerprint).apply();
                            Log.i(TAG, "Đã cài Nova Client");
                        }
                        @Override public void onError(String errorMessage) {
                            Log.w(TAG, "Không cài được Nova Client: " + errorMessage);
                        }
                        @Override public void onProgressUpdate(int progress) {}
                    });
        } catch (Throwable t) {
            Log.w(TAG, "Bỏ qua cài mod đóng gói sẵn", t);
        }
    }

    private static long copyAsset(Context context, File out) throws Exception {
        long total = 0;
        try (InputStream in = context.getAssets().open(ASSET); OutputStream os = new FileOutputStream(out)) {
            byte[] buf = new byte[64 * 1024];
            int n;
            while ((n = in.read(buf)) > 0) { os.write(buf, 0, n); total += n; }
        }
        return total;
    }
}
'''

HOOK_ANCHOR = "fileHandler = new FileHandler(this, viewModel, versionManager);"
HOOK_LINE = "        org.levimc.launcher.nova.NovaBootstrap.installOnce(this, fileHandler);"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo"); ap.add_argument("--name", default="Nova Launcher")
    ap.add_argument("--app-id", default="com.nova.launcher"); ap.add_argument("--levipack")
    a = ap.parse_args()
    root = pathlib.Path(a.repo)
    app = root / "app"
    gradle = app / "build.gradle"
    if not gradle.is_file():
        sys.exit(f"Không thấy {gradle} – truyền đúng thư mục gốc repo LeviLaunchroid")
    if not re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", a.app_id):
        sys.exit("app-id không hợp lệ (ví dụ: com.yourname.novalauncher)")

    # 1. applicationId
    g = gradle.read_text(encoding="utf-8")
    g2, n = re.subn(r'applicationId\s+"[^"]+"', f'applicationId "{a.app_id}"', g, count=1)
    if n == 0: sys.exit("Không tìm thấy applicationId trong app/build.gradle")
    gradle.write_text(g2, encoding="utf-8")
    print(f"[1] applicationId -> {a.app_id}")

    # 2. app_name ở mọi ngôn ngữ
    name = a.name.replace("&", "&amp;").replace("<", "&lt;").replace("'", "\\'")
    cnt = 0
    for f in (app / "src/main/res").glob("values*/strings.xml"):
        t = f.read_text(encoding="utf-8")
        t2, k = re.subn(r'(<string name="app_name"[^>]*>)[^<]*(</string>)', rf"\g<1>{name}\g<2>", t)
        if k: f.write_text(t2, encoding="utf-8"); cnt += 1
    print(f"[2] app_name -> '{a.name}' ({cnt} file ngôn ngữ)")

    # 3. nhúng mod
    if a.levipack:
        src = pathlib.Path(a.levipack)
        if not src.is_file(): sys.exit(f"Không thấy {src}")
        dst = app / "src/main/assets/nova/nova_client.levipack"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        jf = app / "src/main/java/org/levimc/launcher/nova/NovaBootstrap.java"
        jf.parent.mkdir(parents=True, exist_ok=True)
        jf.write_text(JAVA, encoding="utf-8")

        ma = app / "src/main/java/org/levimc/launcher/ui/activities/MainActivity.java"
        t = ma.read_text(encoding="utf-8")
        if "NovaBootstrap.installOnce" in t:
            print("[3] hook MainActivity đã có – bỏ qua")
        elif HOOK_ANCHOR not in t:
            sys.exit("Không tìm thấy vị trí chèn trong MainActivity (bản launcher khác 1.5.27?)")
        else:
            t = t.replace(HOOK_ANCHOR, HOOK_ANCHOR + "\n" + HOOK_LINE, 1)
            ma.write_text(t, encoding="utf-8")
            print("[3] đã nhúng .levipack + chèn hook vào MainActivity")
    else:
        print("[3] bỏ qua nhúng mod (không có --levipack)")

    print("\nXong. Việc còn lại: thay icon (res/mipmap-*), giữ nguyên LICENSE/NOTICE (Apache 2.0), build bằng Android Studio.")

if __name__ == "__main__":
    main()
