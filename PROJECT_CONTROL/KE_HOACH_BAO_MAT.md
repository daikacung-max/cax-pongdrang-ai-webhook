# Kế hoạch nâng cấp bảo mật

Bảo mật là điều kiện bắt buộc trước khi dùng với dữ liệu thật. Thứ tự dưới đây ưu tiên giảm rủi ro lộ danh tính, lộ nội dung tố giác và truy cập trái phép.

## 1. Quản trị dữ liệu và quyền riêng tư

- Lập bản đồ dữ liệu: Zalo user key, nội dung chat, ảnh/video/tệp, hồ sơ vụ việc, nhật ký cán bộ.
- Chỉ thu thập dữ liệu cần cho thủ tục; thông báo cho người dân AI đang hỗ trợ và mục đích lưu trữ.
- Đặt thời hạn lưu riêng cho chat, hồ sơ vụ việc và tệp chứng cứ; tự động xóa hoặc ẩn danh khi hết hạn.
- Có chức năng cán bộ tra cứu, chỉnh sửa, xuất và xóa theo thẩm quyền; ghi nhận mọi yêu cầu.
- Không đưa nội dung nhận dạng cá nhân vào log, prompt debug, dữ liệu benchmark hoặc công cụ phân tích bên ngoài.

## 2. Danh tính, bí mật và API

- Dùng secret manager/environment variables; xoay vòng Zalo token, webhook secret, HMAC secret và API key định kỳ.
- Không đưa khóa vào git, file ZIP, ảnh chụp màn hình, lỗi trả về hoặc log.
- Dùng HMAC định danh người dùng; tách bảng định danh thật khỏi bảng hội thoại và giới hạn người được truy cập.
- Dùng TLS, kiểm tra chữ ký webhook, chống replay bằng timestamp/idempotency và giới hạn tốc độ theo nguồn/người dùng.

## 3. Phân quyền cán bộ

- RBAC tối thiểu: tiếp nhận, cán bộ chuyên môn, lãnh đạo duyệt, quản trị hệ thống, kiểm toán.
- MFA, phiên ngắn hạn, tự khóa khi bất thường, thu hồi ngay khi cán bộ đổi vị trí.
- Một cán bộ chỉ xem hồ sơ thuộc phạm vi được giao; thao tác nhạy cảm cần lý do và có thể yêu cầu duyệt hai người.
- Không cho mô hình hoặc tài khoản kỹ thuật tự ý đóng hồ sơ hay quyết định kết quả pháp lý.

## 4. Bảo vệ ứng dụng và AI

- Kiểm tra đầu vào, giới hạn kích thước tệp/tin nhắn, chống prompt injection và nội dung giả mạo nguồn.
- Retrieval chỉ lấy nguồn đã duyệt; lưu phiên bản nguồn và ngày hiệu lực.
- Verifier bắt buộc kiểm tra điều luật, số liệu, thời hạn, mức phạt, giấy tờ, cơ quan và kết luận trách nhiệm.
- Fail-closed khi nguồn thiếu, model lỗi, verifier từ chối hoặc có dấu hiệu khẩn cấp; chuyển cán bộ.
- Không gửi dữ liệu nhạy cảm sang provider nếu chưa có đánh giá, hợp đồng và cấu hình lưu dữ liệu phù hợp.
- Có bộ test hồi quy chống bịa, rò rỉ lịch sử giữa người dùng, kết luận tội phạm và bỏ sót ngoại lệ pháp luật.

## 5. Hạ tầng và vận hành

- Chuyển lịch sử production sang Postgres quản lý cùng region; bật mã hóa, backup tự động và diễn tập restore.
- Tách môi trường demo/staging/production; dữ liệu demo phải giả lập, không dùng dữ liệu người dân thật.
- Vá dependency, quét secret, quét lỗ hổng image/package và rà soát cấu hình trước mỗi deploy.
- Giám sát uptime, lỗi provider, fallback, truy cập bất thường và xuất dữ liệu; cảnh báo không kèm nội dung chat.
- Có rollback, nút tắt AI, tài khoản khẩn cấp và runbook khi mất OA, lộ khóa, database bị xâm nhập hoặc model trả lời sai.

## 6. Đánh giá độc lập trước production

- Rà soát mã nguồn và threat model bởi người không trực tiếp viết tính năng.
- Kiểm thử phân quyền, webhook giả mạo, replay, rate limit, SQL injection, XSS, SSRF, upload độc hại và rò rỉ prompt.
- Kiểm thử xâm nhập có phạm vi, biên bản khắc phục và kiểm thử lại.
- Phê duyệt nghiệp vụ và bảo vệ dữ liệu bằng văn bản trước khi mở rộng người dùng.

## Cổng an toàn bắt buộc

Không chuyển sang production nếu còn một trong các lỗi: lộ khóa; log chứa dữ liệu cá nhân; không xác thực webhook; cán bộ xem sai phạm vi; không khôi phục được backup; AI tự kết luận tội phạm; hoặc không có nút chuyển người thật.
