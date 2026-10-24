# Ghi chú dịch ngược – Minecraft Bedrock 1.26.50.4 (ARM64)  [build-id afa62bd3385161f1...]

Địa chỉ = offset trong file = vaddr của libminecraftpe.so (không có image base). Đã kiểm chứng: 4 signature của
LeviLauncher cho 1.26.50 đều khớp đúng 1 vị trí trong file này.

## Đã xác định (đọc từ mã, độ tin cậy: khá, chưa test trên game)
- 0xac12e8c (~0x18d90 byte): hàm khai báo toàn bộ tuỳ chọn. Chứa các chuỗi gfx_field_of_view, gfx_field_of_view_toggle, gfx_gamma.
- Tuỳ chọn FOV: tạo qua hàm 0xc9d1b9c(this, id=0x2f, 0, 0x10, "options.fov", "gfx_field_of_view", float, float, float);
  hằng float trong mã: 60.0 và 110.0 (+0.001). vptr của đối tượng: 0x12e4dc58.
- Đăng ký tuỳ chọn vào Options: gọi hàm ảo slot index 18 (offset 0x90) của đối tượng Options.

## Chưa biết (cần làm tiếp)
- Hàm/đường đọc giá trị FOV lúc render (để hook cho Zoom). Quét hằng số 0x2f cho 1774 kết quả – quá nhiễu.
- ID và đối tượng của gfx_gamma (chưa trích).
- Vtable 0x12e4dc58 là đa kế thừa; chưa xác định slot nào là getter float.

## Công cụ (python3 + numpy)
a64.py   bộ giải mã ARM64 rút gọn:   python3 a64.py 0xBEGIN 0xEND
xref.py  tìm xref của chuỗi → hàm:   python3 xref.py gfx_gamma
vt.py    đọc vtable qua relocation:  python3 vt.py 0x12e4dc58 24 7
idscan.py quét hằng số ID
LƯU Ý: a64.py chỉ giải mã một phần lệnh (lệnh dấu phẩy động hiện là .word). Không dùng kết quả làm nguồn duy nhất.
