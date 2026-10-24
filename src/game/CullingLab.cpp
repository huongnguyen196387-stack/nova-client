#include "game/CullingLab.h"

#include <atomic>
#include <chrono>
#include <mutex>
#include <thread>

#include <pl/Logger.hpp>

#include "game/GameHooks.h"

namespace nova {
namespace {

using Fn = bool (*)(void *, void *);

struct Slot {
    const char *name;
    Fn orig = nullptr;
    std::atomic<int> mode{CullingLab::Passthrough};
    std::atomic<uint64_t> calls{0};
    std::atomic<uint64_t> trues{0};
    bool hooked = false;
};

Slot gSlots[2] = {{"cullerQueryA"}, {"cullerQueryB"}};

inline bool run(Slot &s, void *self, void *arg) {
    s.calls.fetch_add(1, std::memory_order_relaxed);
    switch (s.mode.load(std::memory_order_relaxed)) {
    case CullingLab::ForceFalse: return false;
    case CullingLab::ForceTrue: return true;
    default: break;
    }
    bool r = s.orig ? s.orig(self, arg) : false;
    if (r) s.trues.fetch_add(1, std::memory_order_relaxed);
    return r;
}

bool detourA(void *self, void *arg) { return run(gSlots[0], self, arg); }
bool detourB(void *self, void *arg) { return run(gSlots[1], self, arg); }

std::atomic<int> gStatus{CullingLab::NotConfigured};
std::atomic<bool> gStop{false};
std::thread gThread;
std::mutex gMutex;

// Trả true nếu cả hai hook đã sẵn sàng.
bool tryInstall() {
    auto &hooks = GameHooks::get();
    bool ok = true;
    const pl::memory::FuncPtr detours[2] = {reinterpret_cast<pl::memory::FuncPtr>(&detourA),
                                            reinterpret_cast<pl::memory::FuncPtr>(&detourB)};
    for (int i = 0; i < 2; ++i) {
        Slot &s = gSlots[i];
        if (s.hooked) continue;
        if (hooks.hookSlot(s.name, detours[i], reinterpret_cast<pl::memory::FuncPtr *>(&s.orig))) s.hooked = true;
        else ok = false;
    }
    return ok;
}

} // namespace

bool CullingLab::configured() {
    auto &h = GameHooks::get();
    return h.hasSlot("cullerQueryA") && h.hasSlot("cullerQueryB");
}

CullingLab::Status CullingLab::status() { return static_cast<Status>(gStatus.load()); }

void CullingLab::install() {
    std::lock_guard lock(gMutex);
    if (!configured()) { gStatus = NotConfigured; return; }
    gStop = false;
    if (tryInstall()) { gStatus = Ready; return; }
    gStatus = Waiting;
    if (gThread.joinable()) return;
    gThread = std::thread([] {
        for (int i = 0; i < 120 && !gStop.load(); ++i) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
            std::lock_guard l(gMutex);
            if (gStop.load()) return;
            if (tryInstall()) { gStatus = Ready; return; }
        }
        gStatus = Failed;
    });
}

void CullingLab::uninstall() {
    gStop = true;
    if (gThread.joinable()) gThread.join();
    std::lock_guard lock(gMutex);
    for (auto &s : gSlots) { s.mode = Passthrough; s.hooked = false; } // hook thật được gỡ bởi GameHooks::removeAll()
    gStatus = configured() ? Waiting : NotConfigured;
}

void CullingLab::setMode(int slot, Mode m) {
    if (slot >= 0 && slot < 2) gSlots[slot].mode.store(m);
}

CullStats CullingLab::stats(int slot) {
    if (slot < 0 || slot >= 2) return {};
    return {gSlots[slot].calls.load(), gSlots[slot].trues.load()};
}

bool CullingLab::callDetourForTest(int slot, void *self, void *arg, bool (*orig)(void *, void *)) {
    gSlots[slot].orig = orig;
    return run(gSlots[slot], self, arg);
}

} // namespace nova
