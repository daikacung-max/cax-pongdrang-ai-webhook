from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
UNIT_NAME = os.getenv("UNIT_NAME", "Công an xã Pơng Drang, tỉnh Đắk Lắk")
HOTLINE = os.getenv("HOTLINE", "02623509777")
PRODUCTION_MODE = os.getenv("PRODUCTION_MODE", "false").lower() in ("1", "true", "yes", "on")
GROQ_API_KEY = "".join((os.getenv("GROQ_API_KEY") or "").split())
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1/chat/completions")
OPENAI_API_KEY = "".join((os.getenv("OPENAI_API_KEY") or "").split())
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")

# Model routing mặc định ở chế độ AUTO. Các biến ANSWER_MODEL/DYNAMIC_ANSWER_MODEL
# cũ trên Render sẽ không vô tình ghim hệ thống vào một model mãi mãi. Khi OpenAI
# API key tồn tại, AI Core tự dùng GPT-5.6; nếu chưa có, hệ thống giữ GPT-OSS/Groq
# để không làm gián đoạn dịch vụ. Chuyển MODEL_ROUTING_MODE=manual nếu cần khóa
# model thủ công cho một đợt thử nghiệm có chủ đích.
MODEL_ROUTING_MODE = os.getenv("MODEL_ROUTING_MODE", "auto").strip().lower()
_AUTO_DYNAMIC_MODEL = "gpt-5.6-luna" if OPENAI_API_KEY else "openai/gpt-oss-20b"
_AUTO_ANSWER_MODEL = "gpt-5.6-terra" if OPENAI_API_KEY else "openai/gpt-oss-120b"
_AUTO_PLANNER_MODEL = "gpt-5.6-luna" if OPENAI_API_KEY else "openai/gpt-oss-20b"

if MODEL_ROUTING_MODE == "manual":
    ANSWER_MODEL = os.getenv("ANSWER_MODEL", _AUTO_ANSWER_MODEL).strip() or _AUTO_ANSWER_MODEL
    DYNAMIC_ANSWER_MODEL = os.getenv("DYNAMIC_ANSWER_MODEL", _AUTO_DYNAMIC_MODEL).strip() or _AUTO_DYNAMIC_MODEL
    PLANNER_MODEL = os.getenv("PLANNER_MODEL", _AUTO_PLANNER_MODEL).strip() or _AUTO_PLANNER_MODEL
else:
    ANSWER_MODEL = _AUTO_ANSWER_MODEL
    DYNAMIC_ANSWER_MODEL = _AUTO_DYNAMIC_MODEL
    PLANNER_MODEL = _AUTO_PLANNER_MODEL

ESCALATION_MODEL = os.getenv("ESCALATION_MODEL", "gpt-5.6-sol")
DYNAMIC_CANDIDATE_MODEL = os.getenv("DYNAMIC_CANDIDATE_MODEL", "gpt-5.6-luna")
FULL_CORE_CANDIDATE_MODEL = os.getenv("FULL_CORE_CANDIDATE_MODEL", "gpt-5.6-terra")
ENABLE_MODEL_ESCALATION = os.getenv("ENABLE_MODEL_ESCALATION", "false").lower() in ("1", "true", "yes", "on")

DB_PATH = Path(os.getenv("LEGAL_DB_PATH", str(BASE_DIR / "data" / "legal.db")))
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))
DYNAMIC_HISTORY_MESSAGES = int(os.getenv("DYNAMIC_HISTORY_MESSAGES", "8"))
DYNAMIC_HISTORY_MAX_CHARS = int(os.getenv("DYNAMIC_HISTORY_MAX_CHARS", "3000"))
RETRIEVAL_HISTORY_USER_TURNS = int(os.getenv("RETRIEVAL_HISTORY_USER_TURNS", "4"))
LEGAL_TOP_K = int(os.getenv("LEGAL_TOP_K", "8"))
DYNAMIC_LEGAL_TOP_K = int(os.getenv("DYNAMIC_LEGAL_TOP_K", "2"))
CORE_REASONING_EFFORT = os.getenv("CORE_REASONING_EFFORT", "medium")
# GPT-OSS trên Groq tính token suy luận vào cùng ngân sách hoàn thành. Với câu
# trả lời có nguồn dài, mức thấp dành phần ngân sách còn lại cho câu trả lời cuối.
GROQ_CORE_REASONING_EFFORT = os.getenv("GROQ_CORE_REASONING_EFFORT", "low")
DYNAMIC_REASONING_EFFORT = os.getenv(
    "DYNAMIC_REASONING_EFFORT",
    "none" if str(DYNAMIC_ANSWER_MODEL).startswith("gpt-5.6") else "low",
)
CORE_TIMEOUT_SECONDS = float(os.getenv("CORE_TIMEOUT_SECONDS", "12"))
# Dynamic phải fail-fast. Nếu model chậm, AI Core dùng grounded fallback từ
# nguồn đã kiểm chứng thay vì kéo dài vượt deadline của kênh Zalo.
DYNAMIC_TIMEOUT_SECONDS = float(os.getenv("DYNAMIC_TIMEOUT_SECONDS", "1.05"))
MAX_ZALO_MESSAGES = int(os.getenv("MAX_ZALO_MESSAGES", "4"))
TARGET_ZALO_CHARS = int(os.getenv("TARGET_ZALO_CHARS", "650"))
MAX_ZALO_TOTAL_CHARS = int(os.getenv("MAX_ZALO_TOTAL_CHARS", "2400"))
PENDING_TTL_SECONDS = int(os.getenv("PENDING_TTL_SECONDS", "30"))

# Zalo chỉ được phép đẩy sự kiện vào hàng đợi khi tích hợp đã được bật rõ ràng.
# Production fail-closed: khi webhook công khai đã bật, kiểm tra chữ ký luôn là
# bắt buộc bất kể biến môi trường vô tình đặt false. Local/test vẫn có thể tắt.
ZALO_WEBHOOK_ENABLED = os.getenv("ZALO_WEBHOOK_ENABLED", "true").lower() in ("1", "true", "yes", "on")
_requested_signature_check = os.getenv("ZALO_WEBHOOK_SIGNATURE_REQUIRED", "false").lower() in ("1", "true", "yes", "on")
ZALO_WEBHOOK_SIGNATURE_REQUIRED = bool(
    _requested_signature_check or (PRODUCTION_MODE and ZALO_WEBHOOK_ENABLED)
)
ZALO_APP_ID = os.getenv("ZALO_APP_ID", "").strip()
ZALO_OA_SECRET_KEY = os.getenv("ZALO_OA_SECRET_KEY", "").strip()

# Direct Reply ở chế độ AUTO: khi OA Access Token hợp lệ xuất hiện, production
# tự chuyển từ đường Dynamic/pending sang gửi phản hồi trực tiếp qua OA API.
# Có thể ép "dynamic" để tắt hoặc "direct" để yêu cầu direct reply rõ ràng.
ZALO_OA_ACCESS_TOKEN = os.getenv("ZALO_OA_ACCESS_TOKEN", "").strip()
ZALO_REPLY_MODE = os.getenv("ZALO_REPLY_MODE", "auto").strip().lower()
_requested_direct_reply = os.getenv("ZALO_DIRECT_REPLY_ENABLED", "false").lower() in ("1", "true", "yes", "on")
ZALO_DIRECT_REPLY_ENABLED = bool(
    _requested_direct_reply
    or (ZALO_REPLY_MODE == "direct")
    or (ZALO_REPLY_MODE == "auto" and PRODUCTION_MODE and ZALO_WEBHOOK_ENABLED and ZALO_OA_ACCESS_TOKEN)
)
if ZALO_REPLY_MODE == "dynamic":
    ZALO_DIRECT_REPLY_ENABLED = False

# Lịch sử hội thoại dùng Postgres khi DATABASE_URL được cấu hình; local/test vẫn
# dùng SQLite. user_id luôn được HMAC trước khi ghi xuống storage.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
HISTORY_HMAC_SECRET = os.getenv("HISTORY_HMAC_SECRET", "").strip()
HISTORY_RETENTION_DAYS = int(os.getenv("HISTORY_RETENTION_DAYS", "30"))
HISTORY_MAX_MESSAGES = int(os.getenv("HISTORY_MAX_MESSAGES", "20"))
HISTORY_POOL_MAX_SIZE = int(os.getenv("HISTORY_POOL_MAX_SIZE", "5"))

# Cổng cán bộ là API nội bộ. Token chỉ dùng tạm thời sau reverse proxy/SSO;
# không trả về cho người dân và không được đưa vào mã nguồn hay log.
OFFICER_API_TOKEN = os.getenv("OFFICER_API_TOKEN", "").strip()
ENABLE_INTAKE_CASES = os.getenv("ENABLE_INTAKE_CASES", "true").lower() in ("1", "true", "yes", "on")

# Bản demo chỉ chạy cục bộ, tách khỏi Zalo OA và production. Mặc định tắt để
# không vô tình công khai lịch sử hội thoại demo trên web service.
ENABLE_DEMO_CONSOLE = os.getenv("ENABLE_DEMO_CONSOLE", "false").lower() in ("1", "true", "yes", "on")
LOCAL_BIND_HOST = os.getenv(
    "LOCAL_BIND_HOST",
    "127.0.0.1" if ENABLE_DEMO_CONSOLE else "0.0.0.0",
)
