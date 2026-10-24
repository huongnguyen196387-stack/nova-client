// Culling Lab: công cụ THỬ NGHIỆM để xác minh hai hàm truy vấn culling của game (xem game/CullingLab.h).
// Mặc định tắt; ở chế độ "Tắt (mặc định game)" hàm gốc được gọi nguyên vẹn, chỉ đếm số lần gọi.

#include <cstdio>

#include "game/CullingLab.h"
#include "modules/Modules.h"
#include "modules/TextHudModule.h"

namespace nova {
namespace {

CullingLab::Mode toMode(const std::string &s) {
    if (s == "false") return CullingLab::ForceFalse;
    if (s == "true") return CullingLab::ForceTrue;
    return CullingLab::Passthrough;
}

class CullingLabModule final : public TextHudModule {
  public:
    CullingLabModule()
        : TextHudModule("culling_lab", "Culling Lab (thử nghiệm)",
                        "Hook 2 hàm truy vấn culling của game để đo và thử. Ép kết quả có thể làm thế giới/mob "
                        "biến mất hoặc vẽ thừa – đặt lại \"Tắt\" để về bình thường. Chỉ dùng cho Minecraft 1.26.50.4.",
                        16, 780) {
        const std::vector<Choice> modes = {{"off", "Tắt (mặc định game)"}, {"false", "Luôn trả false"},
                                           {"true", "Luôn trả true"}};
        addChoice("modeA", "Hàm A (tra theo vị trí)", "off", modes);
        addChoice("modeB", "Hàm B (tra theo đối tượng)", "off", modes);
        addToggle("showStats", "Hiện thống kê gọi hàm", true);
    }

    [[nodiscard]] bool available() const override { return CullingLab::configured(); }

    void onEnable() override { apply(); mLastMs = 0; }
    void onDisable() override {
        CullingLab::setMode(0, CullingLab::Passthrough);
        CullingLab::setMode(1, CullingLab::Passthrough);
    }
    void onConfigChanged(const std::string &k) override {
        if ((k == "modeA" || k == "modeB") && enabled()) apply();
    }
    void onTick(float dt) override {
        mAccum += dt;
        if (mAccum < 1.f) return;
        for (int i = 0; i < 2; ++i) {
            CullStats s = CullingLab::stats(i);
            mRate[i] = float(s.calls - mPrev[i].calls) / mAccum;
            uint64_t dc = s.calls - mPrev[i].calls;
            mTruePct[i] = dc > 0 ? 100.f * float(s.trues - mPrev[i].trues) / float(dc) : -1.f;
            mPrev[i] = s;
        }
        mAccum = 0.f;
    }

  protected:
    std::vector<std::string> lines(const HudContext &) override {
        static const char *st[] = {"chưa cấu hình", "đang chờ game nạp", "sẵn sàng", "LỖI (không tìm thấy hàm)"};
        std::vector<std::string> out;
        out.push_back(std::string("Culling Lab: ") + st[CullingLab::status()]);
        if (flag("showStats") && CullingLab::status() == CullingLab::Ready) {
            char buf[80];
            for (int i = 0; i < 2; ++i) {
                if (mTruePct[i] >= 0.f)
                    std::snprintf(buf, sizeof buf, "%c: %.0f gọi/s, true %.0f%%", 'A' + i, mRate[i], mTruePct[i]);
                else
                    std::snprintf(buf, sizeof buf, "%c: %.0f gọi/s", 'A' + i, mRate[i]);
                out.push_back(buf);
            }
        }
        return out;
    }

  private:
    void apply() {
        CullingLab::setMode(0, toMode(str("modeA")));
        CullingLab::setMode(1, toMode(str("modeB")));
    }
    float mAccum = 0.f;
    float mRate[2] = {0, 0}, mTruePct[2] = {-1, -1};
    CullStats mPrev[2];
    long mLastMs = 0;
};

} // namespace

void registerCullingLabModules(ModuleManager &mgr) { mgr.add(std::make_unique<CullingLabModule>()); }

} // namespace nova
