#!/usr/bin/env python3
"""
Tìm hàm trong libminecraftpe.so (ARM64) theo chuỗi văn bản mà hàm đó tham chiếu.

Dùng:  python find_xrefs.py libminecraftpe.so "gfx_gamma" "ENABLE_FOG" [--disasm 30] [--sig 12]
Cần: python3 + numpy.  Tuỳ chọn: capstone (pip install capstone) để in mã assembly.

Với mỗi chuỗi: in địa chỉ chuỗi, các chỗ tham chiếu (ADRP+ADD), hàm chứa chỗ đó (theo .eh_frame_hdr),
và (--sig N) signature N lệnh đầu của hàm kèm số lần khớp (phải = 1 mới dùng được).
"""
import argparse, bisect, mmap, re, struct, sys
import numpy as np

CHUNK = 1 << 24  # 16 MB mỗi lượt quét

def load_phdrs(mm):
    phoff = struct.unpack_from('<Q', mm, 0x20)[0]
    phentsize, phnum = struct.unpack_from('<HH', mm, 0x36)
    out = []
    for i in range(phnum):
        t, fl, off, va, _pa, fsz, msz, _al = struct.unpack_from('<IIQQQQQQ', mm, phoff + i * phentsize)
        out.append((t, fl, off, va, fsz, msz))
    return out

def load_functions(mm, phdrs):
    hdr = next((p for p in phdrs if p[0] == 0x6474E550), None)  # PT_GNU_EH_FRAME
    if not hdr:
        sys.exit("Không có .eh_frame_hdr – không xác định được ranh giới hàm")
    off, va = hdr[2], hdr[3]
    ver, _enc_ptr, enc_cnt, enc_tab = mm[off], mm[off + 1], mm[off + 2], mm[off + 3]
    if ver != 1 or enc_cnt != 0x03 or enc_tab != 0x3B:
        sys.exit(f"Định dạng eh_frame_hdr lạ: {ver},{enc_cnt:#x},{enc_tab:#x}")
    count = struct.unpack_from('<I', mm, off + 8)[0]
    tab = np.frombuffer(mm, dtype='<i4', count=count * 2, offset=off + 12).reshape(-1, 2)
    return sorted(set(int(va + x) for x in tab[:, 0]))

def text_ranges(phdrs):
    return [(p[2], p[2] + p[4]) for p in phdrs if p[0] == 1 and (p[1] & 1)]  # LOAD + exec

def find_strings(mm, s):
    needle = b'\0' + s.encode() + b'\0'
    hits, pos = [], 0
    while True:
        i = mm.find(needle, pos)
        if i < 0: return hits
        hits.append(i + 1)  # vaddr == file offset trong segment đầu của lib này
        pos = i + 1

def scan_xrefs(mm, ranges, targets):
    """Trả {địa chỉ chuỗi: [pc, ...]} cho cặp ADRP rd + ADD rd,rd,#imm."""
    tset = np.array(sorted(targets), dtype=np.int64)
    found = {t: [] for t in targets}
    for lo, hi in ranges:
        for base in range(lo, hi, CHUNK):
            end = min(base + CHUNK + 4, hi)
            n = (end - base) // 4
            w = np.frombuffer(mm, dtype='<u4', count=n, offset=base)
            idx = np.nonzero((w[:-4] & 0x9F000000) == 0x90000000)[0]
            if idx.size == 0: continue
            a = w[idx].astype(np.int64)
            pc0 = base + idx * 4
            imm = (((a >> 5) & 0x7FFFF) << 2) | ((a >> 29) & 3)
            imm = np.where(imm & 0x100000, imm - 0x200000, imm)
            page = (pc0 & ~0xFFF) + (imm << 12)
            pcs, addrs = [], []
            # ADD xd, xn, #imm (xn = thanh ghi ADRP) trong 4 lệnh kế tiếp (trình biên dịch hay chèn lệnh khác vào giữa)
            for k in range(1, 5):
                b = w[idx + k].astype(np.int64)
                ok = ((b & 0xFFC00000) == 0x91000000) & (((b >> 5) & 31) == (a & 31))
                pcs.append(pc0[ok]); addrs.append(page[ok] + ((b[ok] >> 10) & 0xFFF))
            pc = np.concatenate(pcs); addr = np.concatenate(addrs)
            m = np.isin(addr, tset)
            for p, ad in zip(pc[m], addr[m]):
                found[int(ad)].append(int(p))
    return found

def wildcard_word(w):
    """Byte-pattern của 1 lệnh; lệnh có toán hạng tương đối (b/bl/adrp/adr/ldr literal/cbz/tbz/b.cond) -> toàn '?'."""
    rel = ((w & 0x7C000000) == 0x14000000 or (w & 0x1F000000) == 0x10000000 or
           (w & 0x3B000000) == 0x18000000 or (w & 0x7E000000) == 0x34000000 or
           (w & 0x7E000000) == 0x36000000 or (w & 0xFF000010) == 0x54000000)
    b = struct.pack('<I', w)
    return ['?'] * 4 if rel else [f'{x:02X}' for x in b]

def make_sig(mm, start, n):
    words = struct.unpack_from(f'<{n}I', mm, start)
    return ' '.join(t for w in words for t in wildcard_word(w))

def count_sig(mm, ranges, sig):
    pat = b''.join(b'.' if t == '?' else re.escape(bytes([int(t, 16)])) for t in sig.split())
    rx = re.compile(pat, re.DOTALL)
    return sum(len(rx.findall(mm, lo, hi)) for lo, hi in ranges)

def disasm(mm, start, n):
    try:
        import capstone
    except ImportError:
        words = struct.unpack_from(f'<{n}I', mm, start)
        return [f'  {start + i*4:#x}: {w:08x}   (cài capstone để xem assembly)' for i, w in enumerate(words)]
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    return [f'  {i.address:#x}: {i.mnemonic:8s} {i.op_str}' for i in md.disasm(bytes(mm[start:start + n * 4]), start)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('lib'); ap.add_argument('strings', nargs='+')
    ap.add_argument('--disasm', type=int, default=0, help='in N lệnh đầu của mỗi hàm')
    ap.add_argument('--sig', type=int, default=0, help='tạo signature từ N lệnh đầu và kiểm tra tính duy nhất')
    a = ap.parse_args()

    f = open(a.lib, 'rb'); mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    phdrs = load_phdrs(mm); funcs = load_functions(mm, phdrs); ranges = text_ranges(phdrs)
    print(f'[i] {len(funcs)} hàm (eh_frame), {len(ranges)} segment thực thi')

    allstr = {s: find_strings(mm, s) for s in a.strings}
    targets = {v for vs in allstr.values() for v in vs}
    xrefs = scan_xrefs(mm, ranges, targets) if targets else {}

    for s, addrs in allstr.items():
        print(f'\n=== "{s}"')
        if not addrs: print('  không tìm thấy chuỗi'); continue
        for ad in addrs:
            refs = xrefs.get(ad, [])
            print(f'  chuỗi @ {ad:#x}: {len(refs)} tham chiếu')
            seen = set()
            for pc in refs:
                k = bisect.bisect_right(funcs, pc) - 1
                if k < 0 or funcs[k] in seen: continue
                seen.add(funcs[k]); fs = funcs[k]
                size = (funcs[k + 1] - fs) if k + 1 < len(funcs) else 0
                print(f'    xref {pc:#x} -> hàm {fs:#x} (≈{size} byte, +{pc - fs:#x})')
                if a.sig:
                    sig = make_sig(mm, fs, a.sig)
                    print(f'      sig({a.sig}) = {sig}\n      số lần khớp = {count_sig(mm, ranges, sig)}')
                if a.disasm:
                    print('\n'.join(disasm(mm, fs, a.disasm)))

if __name__ == '__main__':
    main()
