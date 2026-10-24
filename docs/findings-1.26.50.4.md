# Kết quả dò libminecraftpe.so 1.26.50.4 (ARM64) – nhóm Performance

Build ID: `afa62bd3385161f1facfe36aad58ac63998f46d2`, chuỗi phiên bản `1.26.50.04_RC3`.
Mọi địa chỉ là vaddr (Ghidra thường cộng 0x100000). **Chưa có phân tích assembly** – bảng dưới chỉ là cấu trúc, ý nghĩa từng slot là suy đoán.

## Game đã có sẵn culling

Các lớp RTTI: `LevelCullerBase`, `LevelCullerCachedBase`, `LevelCullerNone`, `LevelCullerNoneAsync`, `LevelCullerManhattan`,
`LevelCullerDistanceField`, `LevelCullerDistanceFieldPerspective`, `LevelCullerShadow`, `BlockCullingGroup`.
=> "Chunk Culling" không phải thuật toán còn thiếu. Hướng khả thi: ép game dùng bộ culler mạnh hơn, hoặc chỉnh tham số của nó.

## Vtable (từ `tools/vtable_dump.py`)

| Lớp | vtable | Slot | Ghi chú |
|---|---|---|---|
| LevelCullerBase | 0x12d60908 | 0–1 | destructor; các slot sau là pure virtual |
| LevelCullerNone | 0x12d61a28 | 14 | slot 2 = 1080 B; slot 3,5,6,7,9 chỉ 4 B (rất có thể `ret` – không làm gì) |
| LevelCullerManhattan | 0x12d601c8 | 14 | slot 2 = 0xb309e00 (936 B) |
| LevelCullerDistanceField | 0x12d5ffd0 | 14 | slot 2 = 0xb307fd8 (936 B), slot 4 = 0xb3083f4 (252 B) |
| LevelCullerDistanceFieldPerspective | 0x12d60120 | 19 | thêm slot 14–18 (slot 14 = 0xb3097e8, 1000 B) |
| LevelCullerShadow | 0x12d60248 | 14 | slot 2 = 0xb30b668 (936 B) |

Slot 5–9 và 11 của Manhattan / DistanceField / Shadow trỏ **cùng** hàm (0xb306df4, 0xb307588, 0xb306ff8, 0xb307358, 0xb307440, 0xb307e30)
=> logic chung nằm ở `LevelCullerCachedBase`; chỉ slot 2, 3, 4, 10, 12 khác nhau giữa các biến thể.

## Việc cần làm tiếp (cần đọc assembly – Ghidra trên PC, hoặc Termux: `sh tools/dump_culler_asm.sh libminecraftpe.so`)

1. Mở 0xb307fd8 (DistanceField slot 2) và 0xb309e00 (Manhattan slot 2): xác nhận đây là hàm quyết định visibility.
2. Tìm nơi game **chọn** culler (chỗ tạo `LevelCullerX`): từ vtable address (vd 0x12d5ffd0) tìm ADRP/ADD trỏ tới nó trong code
   (script `find_xrefs.py` hiện chỉ dò chuỗi; cần mở rộng sang địa chỉ vtable).
3. Chỉ sau đó mới quyết định hook: ép chọn culler khác, hoặc bọc slot 2 để nới/siết điều kiện.

## Khoá tuỳ chọn Performance có trong game (options.txt)

`gfx_particleviewdistance`, `gfx_bubble_particles`, `gfx_fancyskies`, `gfx_smoothlighting`, `gfx_renderdistance`, `gfx_msaa`,
`gfx_multithreaded_renderer`, `gfx_max_framerate`, `gfx_hidehand`, `gfx_damagebobbing`, `gfx_resizableui`.
Launcher đã có trình sửa `options.txt` (OptionsEditorActivity). Ý nghĩa giá trị từng khoá **chưa được xác minh**.

## Hệ thống particle (từ tên RTTI)

`EmitParticleSystemAnon::handleEmitParticleRequest`, `ParticleEventRequestSystem`, `ParticleEventDispatcherComponent`,
`SpawnParticleEffectPacket`. Là ứng viên để chặn particle, chưa dò địa chỉ.

## Kết quả đọc assembly (từ culler_asm.txt) – giả thuyết, CHƯA kiểm chứng trong game

Các hàm dưới đây là của `LevelCullerCachedBase` (dùng chung cho Manhattan / DistanceField / Shadow):

- **Slot 8 @ 0xb307358** `bool f(this, const X*)`: khoá mutex (this+0xf0), đổi vị trí → toạ độ ô lưới 3 chiều, đọc ô 16 byte
  (byte +0xF = "thế hệ" so với this+0x40, byte +0xE bit 1 = cờ), trả `thếHệ(hiện tại hoặc hiện tại-1) && cờ`.
- **Slot 11 @ 0xb307e30** `bool f(this, const Y*)`: tương tự nhưng đầu vào là một đối tượng (gọi 2 getter 0xa56ffb4 / 0xa56ffbc,
  có vẻ là Actor), so bit 2/3/4 của cờ ô với bit vị trí con trong ô; **không có dữ liệu → trả 0, ô không khớp → trả 1**.
- DistanceField slot 3 = `this->+0x190 = 1` (đặt cờ), slot 10 = đọc cờ atomic `+0x1b0 & 1`, slot 12 = đọc atomic u32 `+0x18c`.

**Chưa biết:** true nghĩa là "nhìn thấy" hay "bị che"; hai hàm được gọi cho đối tượng nào/bao nhiêu lần mỗi khung. Phải đo trong game.

### Culling Lab (module thử nghiệm trong Nova)

Hook hai hàm trên (signature trong `resources/signatures.ini`, mỗi cái khớp đúng 1 vị trí). Bật module "Culling Lab" để xem **số lần gọi/giây** và **tỉ lệ true**.
Quy trình thử gợi ý: (1) đứng trên mặt đất nhìn mob, ghi số liệu; (2) xuống hầm, ghi lại; (3) chuyển từng hàm sang "Luôn trả false/true",
xem mob/chunk biến mất hay vẽ thừa; luôn trả về "Tắt" sau khi thử. Dựa vào đó mới quyết định hook cắt chunk/entity thật.
