#pragma once

#include <cstdint>

namespace nova {

// Đếm FPS thật của game bằng cách hook eglSwapBuffers (không cần signature của libminecraftpe).
// Swap của RenderThread (HWUI vẽ overlay launcher) bị loại ra bằng tên thread.
class FrameClock {
  public:
    static bool install();
    static void uninstall();
    static bool installed();

    // Gọi định kỳ từ luồng HUD (~30Hz). nowMs: đồng hồ steady, đơn vị ms.
    static void update(int64_t nowMs);
    static float fps();
    static float frameTimeMs();

    // Giới hạn FPS / giữ nhịp khung hình đều (0 = tắt). Áp dụng ngay trong hook swap của thread game.
    static void setFrameCap(int fps);

    // Tắt/bật VSync bằng eglSwapInterval (áp dụng trên thread game ở lần swap kế tiếp).
    // Cho phép game render nhanh hơn tần số quét màn hình; không "tạo thêm khung hình".
    static void setVsyncOff(bool off);
    static bool canSetSwapInterval();
};

} // namespace nova
