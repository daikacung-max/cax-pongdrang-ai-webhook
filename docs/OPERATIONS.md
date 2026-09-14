# CAX PƠNG DRANG AI CORE — Production Operations

## Nguyên tắc kiến trúc

Tác phẩm do tác giả cung cấp là **Artifact Core**. Danh mục 19 nguồn, tiêu đề, tóm tắt, câu hỏi gợi ý và quy luật hội thoại được giữ tại `core/artifact_core.py`. Nguồn pháp luật/TTHC hiện hành chỉ đóng vai trò cập nhật và kiểm chứng phía sau biên nguồn đã chọn, không được thay thế hoặc đổi tên Artifact Core.

Luồng sản phẩm:

`Zalo OA → webhook đã xác thực → Artifact planner → nguồn Artifact Core → retrieval nguồn hỗ trợ hiện hành → model → verifier + source guard → OA reply`

Demo `/demo` sử dụng cùng `core.chat` và cùng Artifact Core với production, không phải chatbot mô phỏng riêng.

## Kiểm tra sức khỏe

- `/health`: trạng thái AI Core, model/provider và cơ sở dữ liệu.
- `/health/readiness`: trạng thái sẵn sàng vận hành, chỉ trả boolean/trạng thái, không lộ credential.

Các cờ Zalo quan trọng:

- `zalo_webhook_enabled`: webhook đang bật.
- `zalo_signature_required`: production buộc kiểm chữ ký.
- `zalo_signature_secret_ready`: có secret để xác thực webhook.
- `zalo_direct_reply_enabled`: hệ thống được phép gửi trực tiếp qua OA API.
- `zalo_access_token_present`: có access token được cấu hình.
- `zalo_refresh_token_present`: có refresh token được cấu hình.
- `zalo_oauth_refresh_ready`: đủ App ID + App secret + refresh token để tự làm mới access token.
- `zalo_end_to_end_reply_ready`: chỉ `true` khi luồng nhận webhook và gửi phản hồi trực tiếp đã đủ điều kiện cấu hình.

Không coi tích hợp Zalo hoàn tất chỉ vì `/api/chat` hoặc demo hoạt động. Chỉ `zalo_end_to_end_reply_ready=true` cộng với thử nghiệm tin nhắn OA thật mới là bằng chứng end-to-end.

## Biến môi trường Zalo

Không commit giá trị bí mật vào GitHub.

- `ZALO_WEBHOOK_ENABLED=true`
- `ZALO_APP_ID`
- `ZALO_OA_SECRET_KEY` — secret dùng xác thực webhook.
- `ZALO_APP_SECRET_KEY` — App secret dùng riêng cho OAuth v4; phải cấu hình rõ, không suy đoán từ webhook secret.
- `ZALO_OA_ACCESS_TOKEN` — tùy chọn nếu đã có access token.
- `ZALO_OA_REFRESH_TOKEN` — khuyến nghị để runtime có thể tự làm mới token.
- `ZALO_REPLY_MODE=auto|direct|dynamic`

Ở `auto`, production tự bật Direct Reply khi có access token hoặc khi đủ bộ App ID + App secret + refresh token để refresh.

## Vòng đời OA token

OA client sử dụng header `access_token` theo OA OpenAPI. Khi token không có hoặc hết hiệu lực, runtime có thể đổi refresh token qua OAuth v4. Runtime xử lý cả:

- HTTP `401/403`;
- OA JSON `error=-124` dù HTTP vẫn là `200`.

Chỉ retry một lần sau refresh để tránh vòng lặp. Lỗi quota/quyền nghiệp vụ khác fail-closed.

Refresh token mới trả về được giữ trong bộ nhớ tiến trình. Vì credential Zalo là dữ liệu tài khoản ngoài repository, sau khi OA thực tế được cấp quyền cần quản trị credential theo chính sách bí mật của môi trường triển khai.

## Webhook signature

Production fail-closed. Chữ ký được tính từ `app_id` trong payload đã ký + raw JSON body + timestamp + OA secret. Một `ZALO_APP_ID` local cũ không được làm hỏng một webhook có digest hợp lệ, nhưng runtime sẽ ghi cảnh báo an toàn `config_app_id_drift=true` để vận hành biết cần đồng bộ cấu hình.

Log chẩn đoán không chứa UID, nội dung tin nhắn hay secret. Các nguyên nhân có thể thấy:

- `missing_secret`
- `missing_signed_fields`
- `digest_mismatch`
- `config_app_id_drift=true`

## Chống im lặng khi AI lỗi

Khi Direct Reply đã sẵn sàng nhưng model/provider tạm lỗi, runtime vẫn cố gửi một thông báo an toàn qua OA, chỉ dùng tên đơn vị và số trực ban được phê duyệt `02623509777`. Nếu chính OA transport thất bại, lỗi được giữ fail-closed và ghi telemetry thay vì giả vờ đã gửi thành công.

## Acceptance suite

Mỗi thay đổi production phải vượt:

- 100.000 câu routing khác nhau;
- 10.000 câu retrieval kiểm biên Artifact Core;
- 10.000 tình huống người dân trình báo;
- 10.000 câu audit nguồn/ngữ nghĩa pháp lý;
- regression tests về verifier, source guard, memory, intake, VNeID và Zalo;
- production smoke gọi `/demo`, `/demo/api/ai-chat`, `/demo/api/ai-history`, `/api/chat`, `/health/readiness` và Zalo security boundary.

CI không được hạ tiêu chuẩn để lấy số PASS. Nếu test đỏ, sửa nguyên nhân ở code hoặc sửa mock cũ khi mock không còn phản ánh API chính thức.
