# Chạy demo cục bộ

Demo này chỉ dùng dữ liệu giả lập, không gọi Zalo OA, không gửi hồ sơ cho cán bộ và không gọi model/provider. Câu trả lời được tạo từ kho nguồn đã kiểm chứng và các fallback an toàn, vì vậy có thể chạy khi chưa trả phí hoặc chưa có API key. Khi bật demo, server mặc định chỉ lắng nghe tại `127.0.0.1`, không mở ra mạng nội bộ hay Internet.

Trong PowerShell tại thư mục dự án:

```powershell
$env:ENABLE_DEMO_CONSOLE = "true"
$env:LEGAL_DB_PATH = "data/demo-local.db"
python app.py
```

Mở `http://127.0.0.1:10000/demo`.

Thử lần lượt:

1. `Làm VNeID mức 2 cần gì?` — chỉ tư vấn, không tạo tiếp nhận.
2. `Tôi muốn nộp hồ sơ đăng ký tạm trú.` — hỏi thông tin chỗ ở để tiếp nhận demo.
3. `Tôi muốn nộp hồ sơ đăng ký tạm trú, hiện đang ở nhà thuê.` — hiện trạng thái đủ thông tin để tiếp nhận demo.
4. `Con tôi 10 tuổi cần làm căn cước.` — trả lời từ nguồn căn cước dưới 14 tuổi.
5. `Tôi muốn tố giác một vụ việc.` — hướng dẫn theo nguồn tố giác và hiển thị trạng thái cần bổ sung.

Khi tắt cửa sổ PowerShell, demo dừng. Dữ liệu thử nằm trong `data/demo-local.db`; file này đã được git ignore. Không dùng dữ liệu cá nhân thật trong bản demo.
