# Nova Client – client cho Minecraft Bedrock (Android) chạy trên LeviLauncher

Mod native (`preload-native`) dựa trên **preloader-android** + **mod-template** bạn gửi.
Giao diện cấu hình nằm trong **Mod Menu** của LeviLauncher, vị trí HUD kéo thả trong **HUD editor**.

## Trạng thái tính năng

### ✅ Chạy ngay – không cần signature của Minecraft

| Tính năng | Ghi chú |
|---|---|
| **FPS Counter** | Hook `eglSwapBuffers` để đếm FPS thật của game (loại swap của `RenderThread` – overlay launcher). Có tuỳ chọn tắt hook trong `config/config.json` (`fpsHook`). |
| **CPS Counter** | Tách trái/phải. Chuột ngoài: đếm theo nút. Cảm ứng: chạm vùng giữa màn hình (ngoài joystick/nút) tính là click trái – đây là **ước lượng**, không phân biệt được "đánh" với "đặt block". |
| **Keystrokes** | W/A/S/D, Space, LMB/RMB + CPS. Hỗ trợ bàn phím ngoài; trên cảm ứng suy ra W/A/S/D từ hướng kéo joystick (ước lượng). |
| **Crosshair** | Chữ thập / chấm / vòng tròn / vuông / chữ X; chỉnh size, độ dày, khoảng hở, màu, viền. Tâm ngắm của game vẫn còn – hãy ẩn nó trong cài đặt Bedrock nếu muốn. |
| **Toggle Sprint / Auto Sneak** | 2 nút công tắc trên màn hình (bấm 1 lần = giữ phím, bấm lần nữa = nhả), gửi Ctrl / Shift. Đổi keycode hoặc kích thước nút cần khởi động lại game. |
| **Debug Menu** | Bản overlay kiểu F3: FPS, frame time, CPS, RAM, số luồng, kích thước overlay. (Chưa có XYZ/biome/chunk – cần hook game, xem dưới.) |
| **Frame Pacing / FPS Limit** | Giữ khoảng cách giữa các khung hình đều (hoặc giới hạn FPS) ngay trong hook `eglSwapBuffers`. Ẩn khỏi menu nếu hook FPS không cài được. Chỉ làm đều nhịp present, **không** làm game render nhanh hơn. |
| **Culling Lab** (thử nghiệm, mặc định tắt) | Hook 2 hàm truy vấn culling của game **chỉ cho Minecraft 1.26.50.4**: hiện số lần gọi/giây, tỉ lệ true và cho ép kết quả để xác minh ý nghĩa. Chưa phải tính năng tăng FPS. |
| **Clock** | Giờ hệ thống (bonus). |
| Lưu cấu hình | `config/settings.ini`, nhớ bật/tắt + mọi tuỳ chọn. |

### 🔧 Khung đã có, cần hook theo phiên bản Minecraft

**Coordinates, Speed Display, Reach Display, Ping Counter, Armor Status, Item Counter** đã viết xong phần hiển thị,
nhưng dữ liệu nằm trong `libminecraftpe.so` (đổi theo từng bản MC). Các module này **tự ẩn khỏi menu** cho tới khi có
`GameBridge::Provider`. Xem mục "Thêm hook game".

### 🚧 Chưa triển khai

| Tính năng | Lý do |
|---|---|
| Fullbright, Low Fire, Fog/Time Changer, Freelook, Hit Particles, Block Outline, Chunk Borders, Motion Blur / Post Processing, Auto Hotbar, Scoreboard / Boss bar di chuyển được | Phải hook vào code render/gameplay của Minecraft → cần signature/offset đúng bản MC. |
| Zoom | LeviLauncher đã có sẵn **Zoom, Auto Sprint, FPS, CPS** dạng inbuilt – có thể dùng luôn. |
| Pack Switcher | Thuộc phía launcher (`ResourcePackManager`), không làm được thuần bằng mod native. |
| UI Caching, Chunk Culling, Fast Entity Render, tắt Particles/Animations/Fog, Optimized Network Packets | Phải hook sâu vào engine render và tầng mạng của Minecraft (cần signature bản 1.26.50.4 + nghiên cứu từng hàm). Chưa làm. |
| Cosmetics / Capes, Replay Mod, Proximity Chat | Cần backend/server hoặc hệ thống render riêng – là dự án lớn, nên làm riêng từng cái. |

### Công cụ dò vtable (`tools/vtable_dump.py`) và kết quả Performance

`python tools/vtable_dump.py libminecraftpe.so 15LevelCullerBase 24LevelCullerDistanceField` in vtable của lớp C++ (dựng từ RTTI + bảng relocation).
Kết quả dò nhóm Performance cho bản 1.26.50.4 nằm ở `docs/findings-1.26.50.4.md`.

## Build

Yêu cầu: Android SDK, NDK `28.2.13676358`, CMake 3.22+, Ninja, PowerShell 7+ (giống template).

```powershell
$env:ANDROID_HOME = "C:/Users/<you>/AppData/Local/Android/Sdk"
./scripts/package.ps1 -Abi arm64-v8a      # hoặc -Abi all
```

Ra file `build-arm64-v8a/nova_client-0.1.0-arm64-v8a.levipack` → import vào LeviLauncher.
GitHub Actions (`.github/workflows/build.yml`) build sẵn cả hai ABI.

`manifest.json` mặc định `minecraft_versions: ["1.26.*"]`; đổi bằng `-DMOD_MINECRAFT_VERSIONS='["1.26.*"]'`.

## Header preloader (quan trọng)

Mod biên dịch với bộ header trong `third_party/preloader/include` (lấy từ `preloader-android.zip` bạn gửi, khớp LeviLaunchroid 1.5.27).
**Không** kéo preloader tag `0.2.2` từ GitHub như template gốc: bản đó thiếu API Mod Menu v2 nên build lỗi
(`ConfigChoiceStyleV2`, `setConfigSchemaJson`, `getHudSurfaceSize`... not found). Các hàm `pl::...` được launcher cung cấp lúc chạy.

## Cấu trúc

```
src/core/      Module, ModuleManager (menu + luồng HUD), HUD builder, InputState, FrameClock, Settings
src/modules/   FPS/CPS/Keystrokes/Crosshair/Clock/Debug, Movement (nút sprint/sneak), GameInfo (cần provider)
src/game/      GameBridge (trạng thái game), GameHooks (bảng signature), GameProvider (điểm mở rộng)
resources/     signatures.ini (đóng gói vào .levipack)
```

Thêm một module mới: kế thừa `Module` (hoặc `TextHudModule` cho hộp chữ), khai báo tuỳ chọn bằng `addToggle/addInt/addColor/addChoice`,
rồi `mgr.add(std::make_unique<MyModule>())` trong `registerAllModules`.

## Thêm hook game

1. Lấy `libminecraftpe.so` đúng phiên bản bạn chơi (trong APK Minecraft đã cài) và tìm signature ARM64 của hàm cần hook.
   Có thể tham khảo `preloader_signature_rules_source.json` trong APK LeviLauncher để xem định dạng pattern (`?` = wildcard).
2. Ghi vào `resources/signatures.ini`: `tênSlot=<pattern>` (một slot có thể có nhiều dòng cho nhiều phiên bản).
3. Trong `src/game/GameProvider.cpp`: `hooks.hookSlot("tênSlot", detour, &orig)`, đọc dữ liệu từ `this` (offset theo phiên bản)
   vào một `GameState` dùng chung, rồi `GameBridge::get().setProvider(...)`.
4. Build lại – các module Coordinates / Speed / Reach / Ping / Armor / Item Counter tự xuất hiện trong menu.

Signature và offset **không được suy đoán** trong repo này; sai một byte là hook hỏng hoặc crash game.

### Công cụ dò hàm (`tools/find_xrefs.py`)

Chạy trên PC (Python 3 + `pip install numpy capstone`). Tìm hàm trong `libminecraftpe.so` theo chuỗi văn bản hàm đó dùng,
in địa chỉ hàm, assembly và signature (kèm số lần khớp, phải = 1 mới dùng được):

```
python tools/find_xrefs.py libminecraftpe.so "gfx_gamma" "gfx_field_of_view" --disasm 40 --sig 12
```

Đã thử trên bản 1.26.50.4: tìm được tham chiếu và signature duy nhất cho chuỗi `ENABLE_FOG`. Phần in assembly (capstone) chưa được thử.

## Launcher riêng (`launcher-fork/`)

Script `apply_nova_branding.py` biến bản clone **LeviLaunchroid 1.5.27** thành launcher riêng, có sẵn Nova Client:

```
git clone --recursive https://github.com/LiteLDev/LeviLaunchroid   # --recursive để lấy preloader + libHttpClient
python launcher-fork/apply_nova_branding.py <repo> --name "Nova Launcher" --app-id com.ten.cua.ban --levipack nova_client-0.1.0-arm64-v8a.levipack
```

Rồi thay icon (`res/mipmap-*`) và build trong Android Studio.

**Không cần Android Studio:** đẩy repo này lên GitHub, vào tab **Actions → Build Nova Launcher → Run workflow**
(`.github/workflows/build-launcher.yml`). Workflow build mod, clone launcher + submodule, chạy script, rồi build
APK debug (tự ký, cài được ngay) – tải ở mục Artifacts `nova-launcher-apk`. Launcher gốc dùng Firebase nên workflow
dùng `google-services.json` placeholder (giống CI của repo gốc): Crashlytics và push news của launcher gốc sẽ không hoạt động. LeviLaunchroid dùng Apache 2.0: giữ nguyên LICENSE/NOTICE.
Đã thử script trên bản copy source (sửa đúng chỗ, chạy lại không bị nhân đôi). **Chưa build APK và chưa chạy**, đặc biệt đoạn Java tự cài mod lần đầu (`NovaBootstrap`) chưa được biên dịch.

## Đã kiểm chứng gì, chưa kiểm chứng gì

- ✔ Biên dịch kiểm tra cú pháp (`g++ -std=c++20 -Wall -Wextra`, 0 cảnh báo) với header SDK thật + stub cho fmt/jni/android.
- ✔ Test logic trên máy host với launcher giả lập: đăng ký module, schema JSON hợp lệ, CPS/Keystrokes/Crosshair, đổi config qua callback, tắt/bật, lưu `settings.ini`.
- ✘ **Chưa build bằng NDK và chưa chạy trên thiết bị/game thật.** Các điểm cần thử đầu tiên khi chạy thật:
  hook `eglSwapBuffers` (FPS), Ctrl/Shift có được Bedrock nhận qua nút on-screen, schema Mod Menu v2 hiển thị đúng, và heuristic chạm-màn-hình của CPS/Keystrokes.

## Công cụ tìm signature (`tools/make_sig.py`)

Sau khi tìm được địa chỉ hàm trong Ghidra/IDA:

```
python3 tools/make_sig.py libminecraftpe.so 0x<địa_chỉ> tênSlot --base 0x100000
```
`--base 0x100000` trừ image base mặc định của Ghidra. Script tăng độ dài tới khi signature **duy nhất** trong `.text`,
rồi in dòng `tênSlot=...` để dán vào `resources/signatures.ini`. Đã test trên bản 1.26.50.4.
