#include "core/FrameClock.h"

#include <dlfcn.h>
#include <pthread.h>

#include <time.h>

#include <atomic>
#include <cerrno>
#include <cstring>

#include <pl/memory/Hook.hpp>

namespace nova {
namespace {

using SwapFn = unsigned int (*)(void *display, void *surface);
using SwapIntervalFn = unsigned int (*)(void *display, int interval);

SwapFn gOrig = nullptr;
void *gTarget = nullptr;
bool gInstalled = false;

std::atomic<uint64_t> gGameFrames{0}; // thread không phải RenderThread
std::atomic<uint64_t> gUiFrames{0};   // RenderThread (HWUI)

uint64_t gLastGame = 0, gLastUi = 0;
int64_t gLastMs = 0;
std::atomic<float> gFps{0.f};
std::atomic<int> gCapFps{0};
SwapIntervalFn gSwapInterval = nullptr;
std::atomic<bool> gVsyncOff{false};
std::atomic<int> gVsyncGen{0}; // tăng mỗi lần đổi => thread game áp dụng lại

int64_t nowNs() {
    timespec ts{};
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return int64_t(ts.tv_sec) * 1000000000LL + ts.tv_nsec;
}

void sleepUntilNs(int64_t t) {
    timespec ts{time_t(t / 1000000000LL), long(t % 1000000000LL)};
    while (clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &ts, nullptr) == EINTR) {}
}

unsigned int hookedSwap(void *display, void *surface) {
    thread_local int cls = -1; // 0 = game, 1 = ui
    if (cls < 0) {
        char name[32] = {0};
        pthread_getname_np(pthread_self(), name, sizeof name);
        cls = std::strcmp(name, "RenderThread") == 0 ? 1 : 0;
    }
    (cls == 0 ? gGameFrames : gUiFrames).fetch_add(1, std::memory_order_relaxed);

    // VSync: áp dụng trên thread game (cần EGL context hiện tại) khi cấu hình đổi.
    if (cls == 0 && gSwapInterval) {
        thread_local int applied = 0;
        const int gen = gVsyncGen.load(std::memory_order_relaxed);
        if (applied != gen) {
            applied = gen;
            gSwapInterval(display, gVsyncOff.load(std::memory_order_relaxed) ? 0 : 1);
        }
    }

    // Frame pacing: khung hình chỉ được present cách nhau ít nhất 1/cap giây, tính từ lần present thực tế
    // trước đó (không "bù" dồn khi bị trễ, nên không tạo cụm khung hình sau một cú giật).
    const int cap = gCapFps.load(std::memory_order_relaxed);
    if (cls == 0 && cap > 0) {
        thread_local int64_t next = 0;
        int64_t t = nowNs();
        if (next != 0 && t < next) {
            sleepUntilNs(next);
            t = next;
        }
        next = t + 1000000000LL / cap;
    }
    return gOrig ? gOrig(display, surface) : 1u;
}

} // namespace

bool FrameClock::install() {
    if (gInstalled) return true;
    gTarget = dlsym(RTLD_DEFAULT, "eglSwapBuffers");
    if (!gTarget) return false;
    gSwapInterval = reinterpret_cast<SwapIntervalFn>(dlsym(RTLD_DEFAULT, "eglSwapInterval"));
    int rc = pl::memory::hook(gTarget, reinterpret_cast<pl::memory::FuncPtr>(&hookedSwap),
                              reinterpret_cast<pl::memory::FuncPtr *>(&gOrig));
    gInstalled = (rc == 0);
    return gInstalled;
}

void FrameClock::uninstall() {
    if (!gInstalled) return;
    setVsyncOff(false); // lần swap tới (nếu còn) sẽ trả VSync về 1
    setFrameCap(0);
    pl::memory::unhook(gTarget, reinterpret_cast<pl::memory::FuncPtr>(&hookedSwap));
    gInstalled = false;
}

bool FrameClock::installed() { return gInstalled; }

void FrameClock::update(int64_t nowMs) {
    if (!gInstalled) return;
    if (gLastMs == 0) {
        gLastMs = nowMs;
        gLastGame = gGameFrames.load();
        gLastUi = gUiFrames.load();
        return;
    }
    int64_t dt = nowMs - gLastMs;
    if (dt < 500) return;

    uint64_t g = gGameFrames.load(), u = gUiFrames.load();
    uint64_t frames = (g - gLastGame) > 0 ? (g - gLastGame) : (u - gLastUi); // ưu tiên thread game
    float inst = static_cast<float>(frames) * 1000.f / static_cast<float>(dt);
    float prev = gFps.load();
    gFps.store(prev <= 0.f ? inst : prev * 0.4f + inst * 0.6f);

    gLastMs = nowMs;
    gLastGame = g;
    gLastUi = u;
}

void FrameClock::setVsyncOff(bool off) {
    gVsyncOff.store(off);
    gVsyncGen.fetch_add(1);
}

bool FrameClock::canSetSwapInterval() { return gInstalled && gSwapInterval != nullptr; }

void FrameClock::setFrameCap(int fps) { gCapFps.store(fps < 0 ? 0 : fps); }

float FrameClock::fps() { return gFps.load(); }

float FrameClock::frameTimeMs() {
    float f = gFps.load();
    return f > 0.5f ? 1000.f / f : 0.f;
}

} // namespace nova
