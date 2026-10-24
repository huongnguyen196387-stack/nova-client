#!/data/data/com.termux/files/usr/bin/sh
# Trích assembly ARM64 của các hàm culling trong libminecraftpe.so 1.26.50.4 ra file culler_asm.txt.
# Dùng:  sh dump_culler_asm.sh /đường/dẫn/libminecraftpe.so
# Cần:   pkg install radare2     (hoặc: pkg install python clang cmake make && pip install capstone)
LIB="$1"
OUT="${2:-culler_asm.txt}"
[ -f "$LIB" ] || { echo "Không thấy file: $LIB"; echo "Dùng: sh $0 ~/storage/downloads/libminecraftpe.so"; exit 1; }

# tên  địa chỉ(vaddr = offset file)  kích thước(byte)
FUNCS="
Manhattan_slot2        0xb309e00 936
DistanceField_slot2    0xb307fd8 936
DistanceField_slot3    0xb3083e8 12
DistanceField_slot4    0xb3083f4 252
DistanceField_slot10   0xb3084f0 16
DistanceField_slot12   0xb308bd0 12
Shadow_slot2           0xb30b668 936
Shadow_slot4           0xb30ba84 288
None_slot2             0xb30a7f0 1080
Cached_slot5           0xb306df4 516
Cached_slot6           0xb307588 712
Cached_slot7           0xb306ff8 864
Cached_slot8           0xb307358 232
Cached_slot9           0xb307440 328
Cached_slot11          0xb307e30 308
CachedBase_dtor        0xb306d24 204
Perspective_slot14     0xb3097e8 1000
"

disasm_r2() { r2 -q -n -a arm -b 64 -c "pd $3 @ $2" "$LIB" 2>/dev/null; }
disasm_py() {
python - "$LIB" "$2" "$3" <<'PY'
import sys, capstone
lib, addr, n = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3])
with open(lib, 'rb') as f:
    f.seek(addr); code = f.read(n * 4)
for i in capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM).disasm(code, addr):
    print(f"  {i.address:#x}  {i.mnemonic:8s} {i.op_str}")
PY
}

if command -v r2 >/dev/null 2>&1; then D=disasm_r2
elif python -c "import capstone" >/dev/null 2>&1; then D=disasm_py
else echo "Thiếu công cụ. Chạy:  pkg install radare2"; exit 1; fi
echo "Dùng: $D"

: > "$OUT"
echo "$FUNCS" | while read -r NAME ADDR SIZE; do
  [ -z "$NAME" ] && continue
  N=$((SIZE / 4))
  { echo; echo "===== $NAME @ $ADDR ($SIZE byte, $N lệnh) ====="; $D "$NAME" "$ADDR" "$N"; } >> "$OUT"
  echo "  xong $NAME"
done
echo "Đã ghi: $OUT ($(wc -c < "$OUT") byte). Hãy gửi file này cho Claude."
