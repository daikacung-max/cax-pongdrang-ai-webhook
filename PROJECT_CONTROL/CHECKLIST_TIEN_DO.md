# Checklist đánh giá tiến độ

Quy ước: `[x]` chỉ dùng khi có bằng chứng ghi ở cột ghi chú. `[ ]` là chưa hoàn thành.

## A. Nền tảng hiện có

- [x] Zalo webhook nhận tin nhắn văn bản.
- [x] `/zalo/ai` trả JSON tin nhắn văn bản.
- [x] Retrieval FTS5 và verifier fail-closed.
- [x] Lịch sử HMAC + giới hạn số tin/ngày lưu.
- [x] Log timing không chứa nội dung người dân.
- [x] 51 kiểm tra tự động đạt tại thời điểm cập nhật, gồm ranh giới nguồn, bảo mật lịch sử và adapter Zalo.
- [ ] OA thật đã kiểm thử hai chiều.

## B. Demo nghiệp vụ

- [x] Có danh mục khởi tạo 9 nhóm tiếp nhận cho demo; còn chờ cán bộ duyệt nội dung và mở rộng 10–15 thủ tục.
- [ ] Mỗi thủ tục có nguồn chính thức, ngày hiệu lực và người duyệt.
- [ ] Mỗi thủ tục có bộ câu hỏi tối thiểu và điều kiện đủ dữ kiện.
- [ ] Mỗi thủ tục có bộ câu trả lời mẫu tự nhiên, ngắn, bằng văn bản.
- [x] Phân biệt tư vấn thông thường với yêu cầu tiếp nhận; không tạo hồ sơ chỉ vì người dân hỏi thông tin.
- [x] Có 30 kịch bản hội thoại độc lập và một chuỗi bắt buộc 4 lượt với kết quả mong đợi; kiểm tra tự động trong `tests/test_demo_acceptance.py`.
- [x] Có demo cục bộ tách production: chat văn bản, chỉ tư vấn/tiếp nhận theo yêu cầu, lịch sử tách theo phiên và không gửi dữ liệu ra ngoài.
- [x] Nhớ dữ kiện qua chuỗi 4 lượt hành hung/thương tích/dao/camera trong demo cục bộ.
- [x] Khi thiếu dữ kiện, luồng demo chỉ hỏi một dữ kiện tiếp theo của nhóm nghiệp vụ; chưa thay cho bước rà soát nghiệp vụ của cán bộ.
- [ ] Khi không có nguồn thì nói rõ giới hạn và chuyển người thật.

## C. Tiếp nhận và chuyển xử lý

- [ ] Mô hình dữ liệu hồ sơ vụ việc và nhật ký sự kiện.
- [ ] Phân loại thủ tục/vụ việc bằng mã cố định.
- [ ] Bảng định tuyến theo bộ phận chuyên môn.
- [ ] Tạo mã hồ sơ và xác nhận cho người dân.
- [ ] Cán bộ nhận, yêu cầu bổ sung, chuyển tuyến và đóng hồ sơ.
- [ ] Có SLA, cảnh báo quá hạn và người thay thế.
- [ ] Có nút tắt AI và chuyển ngay cho cán bộ.

## D. Bảo mật và production

- [ ] Threat model và phân loại dữ liệu được duyệt.
- [ ] Bí mật nằm trong secret manager/environment, không nằm trong mã/git/log.
- [ ] Postgres production cùng region, backup và kiểm tra restore.
- [ ] RBAC cho cán bộ, MFA, thu hồi phiên và phân quyền tối thiểu.
- [ ] Mã hóa khi truyền và khi lưu; HMAC/ẩn danh định danh người dân.
- [ ] Audit log chống sửa/xóa và không ghi nội dung nhạy cảm không cần thiết.
- [ ] Kiểm thử xâm nhập, dependency scan, secret scan và rà soát cấu hình.
- [ ] Quy trình xử lý sự cố và thông báo vi phạm dữ liệu.

## Nhật ký phiên làm việc

| Ngày | Nội dung đã làm | Bằng chứng | Vấn đề còn lại | Người duyệt |
|---|---|---|---|---|
| 2026-09-05 | Tạo hồ sơ mục tiêu, checklist và kế hoạch bảo mật | Commit/tài liệu trong `PROJECT_CONTROL/` | Chưa có bộ thủ tục và luồng chuyển cán bộ | Chưa duyệt |
| 2026-09-05 | Thêm phân loại tiếp nhận an toàn cho 8 nhóm demo | `core/intake.py`, test intake | Chưa chuyển hồ sơ thật; chờ nguồn và quy trình nghiệp vụ duyệt | Chưa duyệt |
| 2026-09-05 | Nhập thêm nguồn Bộ Công an cho căn cước dưới 14 tuổi và tố giác/tin báo | `core/verified_sources.py` | Các chủ đề còn thiếu nguồn chi tiết vẫn fail-closed | Chưa duyệt |
| 2026-09-05 | Sửa lỗi mất căn cước bị kéo nhầm sang Điều 134; nhập nguồn cấp lại thẻ căn cước tại cấp tỉnh và mở rộng 30 kịch bản demo | Thủ tục 2.001194 của Cổng DVC Bộ Công an; 49/49 test đạt | Cấp mới/đổi căn cước, sang tên xe và các thủ tục còn lại vẫn chờ nguồn duyệt | Chưa duyệt |
| 2026-09-05 | Tách nguồn cấp thẻ căn cước lần đầu từ đủ 14 tuổi tại cấp tỉnh | Thủ tục 2.000200 của Cổng DVC Bộ Công an; 50/50 test đạt | Đổi thẻ căn cước vẫn chờ nguồn riêng | Chưa duyệt |
