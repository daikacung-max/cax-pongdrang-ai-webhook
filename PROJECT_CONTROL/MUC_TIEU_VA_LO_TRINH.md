# Mục tiêu và lộ trình CAX Pơng Drang AI Core

Ngày cập nhật: 2026-09-05

## Mục tiêu cuối cùng

Xây dựng trợ lý AI Công an xã Pơng Drang phục vụ qua Zalo OA bằng tin nhắn văn bản tự nhiên. Trợ lý có thể hướng dẫn thủ tục hành chính thuộc phạm vi Công an cấp xã, tiếp nhận trình báo/tố giác, hỏi bổ sung dữ kiện còn thiếu, ghi nhớ lịch sử trao đổi, phân loại vụ việc và chuyển hồ sơ có cấu trúc đến đúng bộ phận chuyên môn để cán bộ xử lý.

AI chỉ tư vấn và hỗ trợ tiếp nhận; không thay cán bộ quyết định, không kết luận tội phạm, không tự xác nhận hồ sơ đã được giải quyết.

## Đánh giá hiện tại

Mức tổng thể ước tính: **25% mục tiêu toàn hệ thống**.

Đã có nền tảng khoảng 45% của phần “trả lời tư vấn ban đầu”, nhưng chưa thể coi là trợ lý toàn diện hoặc hệ thống tiếp nhận nghiệp vụ hoàn chỉnh.

### Đã có

- Web service và contract cơ bản cho `/zalo/webhook`, `/zalo/ai`, `/health`, `/debug/article/134`.
- Luồng Planner → SQLite FTS5 → Answer → Verifier → fallback.
- Trả lời văn bản tiếng Việt theo hội thoại, hỏi một dữ kiện quan trọng khi thiếu thông tin.
- Lịch sử tạm thời bằng SQLite, khóa người dùng dạng HMAC, giới hạn lịch sử.
- Instrumentation không ghi câu hỏi, Zalo ID, tên, số điện thoại hay nội dung hội thoại.
- Đã có kiểm thử cho retrieval, verifier, history, provider, pending race và Zalo text response.
- Các chủ đề ban đầu: hành hung/Điều 134, một phần lừa đảo chuyển khoản, cư trú, VNeID, đăng ký xe.

### Chưa có và không được bỏ qua

- Bộ tri thức nghiệp vụ đầy đủ, được Công an xã duyệt và có ngày hiệu lực.
- Danh mục thủ tục 10–15 nhóm đầu tiên cùng bộ câu hỏi tiếp nhận cho từng nhóm.
- CSDL vụ việc/ticket, phân tuyến bộ phận, cán bộ phụ trách, trạng thái, SLA và nhật ký xử lý.
- Màn hình an toàn cho cán bộ xem, nhận, chuyển và đóng hồ sơ.
- Luồng chuyển nội dung thật đến bộ phận chuyên môn và cơ chế xác nhận đã nhận.
- Lưu trữ bền vững cho production: hiện lịch sử vẫn là SQLite; chưa có Postgres vì chưa bật thanh toán.
- Kiểm thử end-to-end với OA thật, tải bình thường và cold start sau khi chốt hạ tầng.

## Lộ trình thực hiện

### Giai đoạn 0 — Chốt phạm vi và bảo mật

Đầu ra: danh sách thủ tục, bộ phận nhận việc, nguồn chính thức, quy tắc dữ liệu, người duyệt nghiệp vụ và tiêu chí demo. Chưa trả phí hạ tầng.

### Giai đoạn 1 — Demo tư vấn Zalo bằng tin nhắn

Đầu ra: 10–15 thủ tục ưu tiên, hỏi bổ sung tự nhiên, trả lời có nguồn, nhớ chuỗi hội thoại, fail-closed khi thiếu căn cứ. Dùng hạ tầng hiện có để demo.

Tiêu chí qua: 30 kịch bản hội thoại không bịa điều luật, số liệu, giấy tờ hoặc thẩm quyền; chỉ trả lời văn bản; không lộ dữ liệu giữa hai người dùng.

### Giai đoạn 2 — Tiếp nhận và chuyển bộ phận

Đầu ra: tạo hồ sơ vụ việc sau khi đủ dữ kiện; phân loại; định tuyến; mã hồ sơ; trạng thái tiếp nhận/đang xử lý/cần bổ sung/đã chuyển/đã đóng; thông báo lại cho người dân bằng tin nhắn.

### Giai đoạn 3 — Cổng cán bộ và lưu trữ bền vững

Đầu ra: tài khoản cán bộ, phân quyền theo bộ phận, Postgres cùng region, mã hóa, audit log, sao lưu, chính sách lưu/xóa dữ liệu.

### Giai đoạn 4 — Pilot có kiểm soát

Đầu ra: chạy với nhóm người dùng giới hạn, giám sát fallback và verifier, cán bộ duyệt mẫu trả lời, quy trình xử lý sự cố và nút tắt AI.

### Giai đoạn 5 — Vận hành chính thức

Chỉ thực hiện sau khi qua đánh giá bảo mật, nghiệm thu nghiệp vụ, kiểm thử OA thật, phê duyệt bảo vệ dữ liệu và có phương án khôi phục.

## Thứ tự ưu tiên nghiệp vụ demo

1. Cấp/đổi/cấp lại căn cước.
2. Kích hoạt và xử lý VNeID mức 2.
3. Thường trú, tạm trú và thay đổi thông tin cư trú.
4. Đăng ký, sang tên, cấp đổi giấy tờ xe.
5. Trình báo mất giấy tờ/tài sản.
6. Tiếp nhận tố giác, tin báo về tội phạm.
7. Lừa đảo chuyển khoản và hướng dẫn bảo toàn chứng cứ.
8. Hành hung, thương tích và hướng dẫn bảo toàn video/chứng cứ.

## Quyết định về chi phí

Demo hiện dùng hạ tầng đang có. Chỉ đề xuất nâng Render/Postgres sau khi bản demo đạt tiêu chí nghiệm thu và người dùng đồng ý; không coi SQLite hiện tại là lưu trữ production bền vững.
