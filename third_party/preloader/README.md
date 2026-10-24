# Header của preloader-android (vendored)

Thư mục `include/` là bản sao nguyên văn từ `preloader-android.zip` do người dùng cung cấp
(bản khớp với LeviLaunchroid 1.5.27). Mod chỉ biên dịch với các header này; các hàm `pl::...` được
bộ nạp (preloader trong launcher) cung cấp lúc chạy, không liên kết tĩnh.

Nguồn gốc: https://github.com/LiteLDev/preloader-android (zip không kèm file LICENSE, bạn cần tự kiểm tra
giấy phép của dự án này trước khi phát hành lại). Không dùng tag 0.2.2: bản đó thiếu API Mod Menu v2.
