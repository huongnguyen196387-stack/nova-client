#pragma once

#include <cstdint>

namespace nova {

struct CullStats {
    uint64_t calls = 0;
    uint64_t trues = 0; // số lần hàm gốc trả true (chỉ đếm khi chạy hàm gốc)
};

// Bộ thử nghiệm hook 2 hàm trong LevelCullerCachedBase của Minecraft 1.26.50.4:
//   slot "cullerQueryA" (vtable slot 8,  0xb307358): bool f(this, const X*)  – tra ô lưới theo vị trí
//   slot "cullerQueryB" (vtable slot 11, 0xb307e30): bool f(this, const Y*)  – tra ô lưới theo đối tượng (có vẻ là Actor)
// Ý nghĩa/độ phân cực (true = nhìn thấy hay bị che?) CHƯA xác minh – module dùng để đo và thử trong game.
class CullingLab {
  public:
    enum Mode : int { Passthrough = 0, ForceFalse = 1, ForceTrue = 2 };
    enum Status : int { NotConfigured = 0, Waiting = 1, Ready = 2, Failed = 3 };

    // Cài hook ngay nếu resolve được; nếu game chưa nạp xong thì thử lại nền (tối đa ~2 phút).
    static void install();
    static void uninstall();

    static bool configured(); // signatures.ini có đủ 2 slot
    static Status status();
    static void setMode(int slot, Mode m); // slot 0 = A, 1 = B
    static CullStats stats(int slot);

    // Dùng cho test: gọi detour với hàm gốc giả.
    static bool callDetourForTest(int slot, void *self, void *arg, bool (*orig)(void *, void *));
};

} // namespace nova
