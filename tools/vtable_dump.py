#!/usr/bin/env python3
"""
In vtable của các lớp C++ trong libminecraftpe.so (ARM64) dựa vào RTTI + bảng relocation.

  python vtable_dump.py libminecraftpe.so 15LevelCullerBase 20LevelCullerManhattan ...

Tên lớp ở dạng Itanium (độ dài + tên, ví dụ "15LevelCullerBase" cho LevelCullerBase).
Lớp đầu tiên được dùng làm mốc: slot nào khác mốc/ mới được đánh dấu.
Cần: python3 + numpy. Địa chỉ in ra là vaddr (trùng offset file ở segment thực thi đầu tiên;
Ghidra thường cộng thêm 0x100000 vào image base).
"""
import bisect, mmap, struct, sys
import numpy as np

def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    f = open(sys.argv[1], 'rb'); mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    phoff = struct.unpack_from('<Q', mm, 0x20)[0]; pes, pn = struct.unpack_from('<HH', mm, 0x36)
    ph = [struct.unpack_from('<IIQQQQQQ', mm, phoff + i * pes) for i in range(pn)]  # type,flags,off,va,pa,fsz,msz,al
    loads = [p for p in ph if p[0] == 1]

    def v2o(va):
        for p in loads:
            if p[3] <= va < p[3] + p[5]: return va - p[3] + p[2]
        return None
    ex = [(p[3], p[3] + p[5]) for p in loads if p[1] & 1]
    in_text = lambda x: any(lo <= x < hi for lo, hi in ex)

    # .dynamic -> DT_RELA / DT_RELASZ
    dyn = next(p for p in ph if p[0] == 2); rela_va = rela_sz = 0
    for i in range(0, dyn[5], 16):
        tag, val = struct.unpack_from('<qQ', mm, dyn[2] + i)
        if tag == 7: rela_va = val
        elif tag == 8: rela_sz = val
    if not rela_va: sys.exit("Không có RELA")
    RA = np.frombuffer(mm, dtype=np.dtype([('o', '<u8'), ('i', '<u8'), ('a', '<i8')]),
                       count=rela_sz // 24, offset=v2o(rela_va))
    RA = RA[RA['i'] == 0x403]                       # R_AARCH64_RELATIVE
    o = np.argsort(RA['o']); RO, RAD = RA['o'][o], RA['a'][o]
    b = np.argsort(RAD); SAD, SOF = RAD[b], RO[b]

    # ranh giới hàm
    eh = next(p for p in ph if p[0] == 0x6474E550)
    cnt = struct.unpack_from('<I', mm, eh[2] + 8)[0]
    tab = np.frombuffer(mm, dtype='<i4', count=cnt * 2, offset=eh[2] + 12).reshape(-1, 2)
    funcs = sorted(set(int(eh[3] + x) for x in tab[:, 0]))
    def fsize(a):
        k = bisect.bisect_left(funcs, a)
        return funcs[k + 1] - funcs[k] if k + 1 < len(funcs) and funcs[k] == a else -1

    def slot_val(off):
        k = np.searchsorted(RO, off); return int(RAD[k]) if k < len(RO) and RO[k] == off else None
    def with_addend(a):
        l, r = np.searchsorted(SAD, a, 'left'), np.searchsorted(SAD, a, 'right'); return [int(x) for x in SOF[l:r]]

    def vtable(cls):
        n = mm.find(b'\0' + cls.encode() + b'\0')
        if n < 0: return None, []
        for so in with_addend(n + 1):                # slot "name" của typeinfo
            ti = so - 8
            for ro in with_addend(ti):               # slot typeinfo trong vtable
                v, sl = ro + 8, []
                while True:
                    x = slot_val(v + 8 * len(sl))
                    if x is None or not in_text(x): break
                    sl.append(x)
                if len(sl) >= 2 and slot_val(ro - 8) in (0, None): return v, sl
        return None, []

    names = sys.argv[2:]; vts = {n: vtable(n) for n in names}; base = vts[names[0]][1]
    for n in names:
        v, sl = vts[n]
        print(f"\n{n}: vtable @ {hex(v) if v else None}, {len(sl)} slot")
        for i, a in enumerate(sl):
            tag = "= mốc" if i < len(base) and a == base[i] else ("KHÁC mốc" if i < len(base) else "mới")
            print(f"   [{i:2}] {a:#x} size={fsize(a):6} {tag}")

if __name__ == '__main__': main()
