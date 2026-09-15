# CAX PƠNG DRANG AI CORE — Production Operations

## Nguyên tắc kiến trúc

Tác phẩm do tác giả cung cấp là **Artifact Core**. Danh mục 19 nguồn, tiêu đề, tóm tắt, câu hỏi gợi ý và quy luật hội thoại được giữ tại `core/artifact_core.py`. Nguồn pháp luật/TTHC hiện hành chỉ đóng vai trò cập nhật và kiểm chứng phía sau biên nguồn đã chọn, không được thay thế hoặc đổi tên Artifact Core.

Luồng production chính thức:

`Zalo OA → webhook đã xác thực → ghi job mã hóa vào Postgres → ACK webhook → worker → Artifact planner → Artifact Core → nguồn hiện hành → model → verifier + source guard → OA reply`

Webhook không phải chờ model trả lời. Tuy nhiên hệ thống chỉ ACK sau khi job đã được ghi bền. Nhờ đó deploy/restart không làm mất bản tin đã được xác nhận nhận thành công.

## Ba mức health

- `/health`: process/AI Core đang chạy.
- `/health/readiness`: các thành phần và credential đã được cấu hình đến đâu, không lộ giá trị bí mật.
- `/health/go-live`: **cổng khai trương fail-closed**. Chỉ trả HTTP `200` và `ready_for_official_operation=true` khi toàn bộ điều kiện chính thức đều xanh; nếu còn thiếu trả HTTP `503` cùng tên blocker.

Điều kiện go-live bắt buộc:

- production mode;
- có LLM provider;
- lịch sử hội thoại lưu bền bằng Postgres + HMAC key;
- Zalo webhook bật và bắt buộc kiểm chữ ký;
- Direct Reply có credential;
- OAuth refresh sẵn sàng;
- refresh token xoay được mã hóa và lưu bền;
- hàng đợi Direct Reply mã hóa/lưu bền;
- demo công khai đã tắt.

Không lấy `/health=200` làm căn cứ khai trương.

## Bề mặt HTTP production

- `/debug/*` mặc định đóng trong production.
- `/api/chat` không mở công khai. Nếu cần tích hợp nội bộ phải có `API_CHAT_TOKEN` và Bearer token đúng.
- request body có giới hạn kích thước.
- demo có rate-limit trong giai đoạn thử nghiệm và phải tắt trước go-live.
- response có `nosniff`, chống iframe, referrer policy, permissions policy, HSTS và `no-store` cho các API nhạy cảm.

## Zalo webhook và OAuth

Biến cấu hình quan trọng:

- `ZALO_WEBHOOK_ENABLED=true`
- `ZALO_APP_ID`
- `ZALO_OA_SECRET_KEY`: secret xác thực webhook.
- `ZALO_APP_SECRET_KEY`: App secret riêng cho OAuth v4.
- `ZALO_OA_ACCESS_TOKEN`: access token seed nếu có.
- `ZALO_OA_REFRESH_TOKEN`: refresh token seed.
- `ZALO_TOKEN_ENCRYPTION_KEY`: Fernet key riêng để mã hóa refresh token và payload hàng đợi trong Postgres.
- `ZALO_REPLY_MODE=auto|direct|dynamic`

OA client dùng header `access_token`; refresh qua OAuth v4. Runtime xử lý cả HTTP `401/403` và OA JSON `error=-124`, retry tối đa một lần sau refresh. Refresh token mới chỉ được đưa vào runtime sau khi ghi bền thành công; nếu persistence lỗi thì fail-closed.

## Durable Direct Reply

Trong chế độ Direct Reply chính thức:

1. webhook hợp lệ được kiểm chữ ký;
2. `user_send_text` được mã hóa và ghi vào bảng `zalo_reply_jobs`;
3. chỉ sau khi ghi thành công mới ACK `200`;
4. worker lấy job bằng row lock, giải mã trong RAM, chạy AI và gửi OA;
5. gửi thành công thì xóa job ngay;
6. lỗi tạm thời retry có giới hạn; không retry vô tận;
7. nhiều worker/instance vẫn tránh lấy cùng một job nhờ `FOR UPDATE SKIP LOCKED`.

Không ghi UID, nội dung tin nhắn hay token vào log.

## Quyền dữ liệu

Webhook `user_withdraw` có chữ ký hợp lệ được xử lý riêng. Hệ thống:

- xóa tin pending;
- xóa job Direct Reply chưa xử lý của người đó;
- xóa lịch sử hội thoại;
- xóa liên kết hồ sơ tiếp nhận tối thiểu;
- không ghi nội dung/UID vào log xóa.

Việc xóa sử dụng cùng khóa HMAC conversation key đang dùng trong history/cases, không tạo thêm bản sao định danh thô.

## Chống im lặng khi AI lỗi

Nếu model/provider tạm lỗi nhưng OA còn hoạt động, runtime gửi thông báo an toàn với tên **Công an xã Pơng Drang, tỉnh Đắk Lắk** và duy nhất số trực ban **02623509777**. Nếu OA transport thất bại thì job được retry theo chính sách hàng đợi, không giả vờ đã gửi thành công.

## Acceptance suite

Mỗi thay đổi production phải vượt:

- 100.000 câu routing;
- 10.000 câu retrieval kiểm biên Artifact Core;
- 10.000 tình huống người dân trình báo;
- 10.000 câu audit nguồn/ngữ nghĩa pháp lý;
- regression tests về verifier, source guard, memory, intake, privacy, HTTP security, OAuth refresh, durable dispatch và Zalo signature;
- production smoke kiểm demo thật trong giai đoạn pre-production;
- workflow `Official Go-Live Gate` kiểm `/health/go-live` trên production sau mỗi push `main`.

CI không được hạ tiêu chuẩn để lấy PASS.

## Hạ tầng chính thức

Không khai trương trên cấu hình chỉ phù hợp thử nghiệm. Trước ngày hoạt động chính thức phải bảo đảm:

- Postgres không còn là database thử nghiệm có ngày hết hạn;
- web service có tài nguyên/SLA phù hợp, không dựa vào free single-instance nếu yêu cầu phục vụ liên tục;
- Render health check được cấu hình tới endpoint health phù hợp;
- `ENABLE_DEMO_CONSOLE=false`;
- `/health/go-live` trả `200`;
- gửi một tin nhắn Zalo OA thật và nhìn thấy phản hồi trên thiết bị thật.
