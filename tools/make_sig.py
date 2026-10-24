#!/usr/bin/env python3
"""Tạo signature ARM64 (định dạng preloader) từ địa chỉ hàm trong libminecraftpe.so.

  python3 make_sig.py libminecraftpe.so 0xA45DA80 [slotName] [--base 0x100000]

--base: image base của Ghidra (mặc định Ghidra nạp .so ở 0x100000 => truyền --base 0x100000
        để địa chỉ Ghidra được trừ đi trước khi dò). Địa chỉ ở đây là offset trong file/vaddr.
Script tăng dần độ dài signature tới khi chỉ còn ĐÚNG 1 vị trí khớp trong .text.
"""
import mmap, re, struct, sys

def sections(f):
    f.seek(0); h = f.read(64)
    shoff, = struct.unpack_from('<Q', h, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', h, 0x3A)
    f.seek(shoff); raw = f.read(shentsize * shnum)
    secs = [struct.unpack_from('<IIQQQQIIQQ', raw, i * shentsize) for i in range(shnum)]
    f.seek(secs[shstrndx][4]); names = f.read(secs[shstrndx][5])
    out = {}
    for s in secs:
        n = names[s[0]:names.index(b'\0', s[0])].decode()
        out[n] = (s[3], s[4], s[5])  # addr, offset, size
    return out

def positional(w):
    """True nếu lệnh phụ thuộc vị trí (sẽ đổi khi game cập nhật) => thay bằng wildcard."""
    if (w & 0x7C000000) == 0x14000000: return True        # B / BL
    if (w & 0x9F000000) in (0x90000000, 0x10000000): return True  # ADRP / ADR
    if (w & 0x3B000000) == 0x18000000: return True        # LDR literal
    if (w & 0xFF000010) == 0x54000000: return True        # B.cond
    if (w & 0x7E000000) == 0x34000000: return True        # CBZ / CBNZ
    if (w & 0x7E000000) == 0x36000000: return True        # TBZ / TBNZ
    if (w & 0x7F800000) == 0x11000000 and ((w >> 22) & 1) == 0: return True  # ADD imm (thường là lo12 sau ADRP)
    if (w & 0x3B000000) == 0x39000000: return True        # LDR/STR imm (offset sau ADRP)
    return False

def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    base = 0
    if '--base' in sys.argv:
        base = int(sys.argv[sys.argv.index('--base') + 1], 16)
        a = [x for x in a if x != sys.argv[sys.argv.index('--base') + 1]]
    path, addr = a[0], int(a[1], 16) - base
    slot = a[2] if len(a) > 2 else 'slot'

    f = open(path, 'rb')
    secs = sections(f)
    taddr, toff, tsize = secs['.text']
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    if not (taddr <= addr < taddr + tsize):
        sys.exit(f'Địa chỉ 0x{addr:X} nằm ngoài .text (0x{taddr:X}..0x{taddr+tsize:X}). Kiểm tra --base.')
    fo = toff + (addr - taddr)

    for n in range(8, 41, 4):
        toks, pat = [], b''
        for i in range(n):
            word = struct.unpack_from('<I', mm, fo + 4 * i)[0]
            raw = mm[fo + 4 * i: fo + 4 * i + 4]
            if positional(word):
                toks += ['?'] * 4; pat += b'....'
            else:
                toks += [f'{b:02X}' for b in raw]; pat += b''.join(re.escape(bytes([b])) for b in raw)
        hits = []
        for m in re.finditer(pat, mm[toff:toff + tsize] if False else mm, re.DOTALL):
            if toff <= m.start() < toff + tsize:
                hits.append(m.start())
                if len(hits) > 1: break
        status = 'DUY NHẤT' if len(hits) == 1 else ('>1 khớp' if hits else '0 khớp (lỗi)')
        print(f'{n:2d} lệnh: {status}')
        if len(hits) == 1:
            print('\nDán vào resources/signatures.ini:\n')
            print(f'{slot}={" ".join(toks)}')
            return
    sys.exit('Không tìm được signature duy nhất tới 40 lệnh – hàm có thể là thunk ngắn; chọn hàm lân cận.')

if __name__ == '__main__':
    main()
