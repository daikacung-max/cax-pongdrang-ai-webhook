# Vận hành Zalo OA

Hệ thống chỉ trả lời bằng tin nhắn văn bản. Mỗi lượt Zalo đi theo luồng Planner → SQLite FTS5 → Answer → Verifier → fallback; nhánh Dynamic chỉ gọi model một lần.

## Đo độ trễ

Sau khi deploy bản instrumentation, chạy tối thiểu 30 lượt warm:

```powershell
python scripts/benchmark_zalo.py --base-url https://cax-pongdrang-ai.onrender.com --count 30 --label warm
```

Một mẫu cold chỉ hợp lệ khi tiến trình vừa khởi động mới hoặc dịch vụ vừa thức dậy sau khi ngủ. Thực hiện 10 lần ở 10 lần khởi động lạnh riêng biệt; không gắn nhãn cold cho yêu cầu gửi vào tiến trình đã warm:

```powershell
python scripts/benchmark_zalo.py --base-url https://cax-pongdrang-ai.onrender.com --count 1 --label cold
```

Xuất các dòng log có `event=zalo_ai_latency` từ Render, rồi tổng hợp:

```powershell
python scripts/summarize_latency.py latency-render.log
```

Log chỉ chứa trace ngẫu nhiên, timing, mã fallback, model và số đơn vị nguồn; không chứa câu hỏi, Zalo ID, tên, số điện thoại, hội thoại hay khóa API.

## Canary model

Giữ `DYNAMIC_ANSWER_MODEL=openai/gpt-oss-20b` trong đợt instrumentation. Chỉ đặt `DYNAMIC_ANSWER_MODEL=gpt-5.6-luna` khi có `OPENAI_API_KEY` và benchmark đạt đồng thời: chất lượng grounding không giảm, p95 thấp hơn deadline Zalo ít nhất 300 ms, fallback dưới 5%.

Quay lại Groq không cần rollback mã: đặt `DYNAMIC_ANSWER_MODEL=openai/gpt-oss-20b`. Full Core dùng Terra bằng `ANSWER_MODEL=gpt-5.6-terra`; chỉ bật `ENABLE_MODEL_ESCALATION=true` sau canary để cho phép chuyển sang Sol khi bài toán phức tạp hoặc lần sửa đầu không vượt verifier.

## Dữ liệu hội thoại

Kho pháp luật vẫn là `data/legal.db` SQLite FTS5. Lịch sử hội thoại dùng Render Postgres qua internal `DATABASE_URL`; user ID được HMAC trước khi lưu, tối đa 20 tin hoặc 30 ngày mỗi người dùng. Web service và Postgres phải cùng vùng `singapore`.
