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

# AI Core đầy đủ dùng 120B. Zalo Dynamic bị giới hạn thời gian phản hồi rất ngắn,
# nên dùng GPT-OSS 20B cho nhánh real-time; câu trả lời pháp luật vẫn đi qua
# retrieval + verifier/fallback dựa trên nguồn.
ANSWER_MODEL = os.getenv("ANSWER_MODEL", "openai/gpt-oss-120b")
DYNAMIC_ANSWER_MODEL = os.getenv("DYNAMIC_ANSWER_MODEL", "openai/gpt-oss-20b")
PLANNER_MODEL = os.getenv("PLANNER_MODEL", "openai/gpt-oss-20b")
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
DYNAMIC_REASONING_EFFORT = os.getenv("DYNAMIC_REASONING_EFFORT", "low")
CORE_TIMEOUT_SECONDS = float(os.getenv("CORE_TIMEOUT_SECONDS", "12"))
# Dynamic GET có thể phải đợi webhook tới khoảng 0.4-0.6s; dành khoảng 1.05s cho model.
# Nếu model chậm, AI Core tự dùng grounded fallback từ nguồn đã kiểm chứng.
DYNAMIC_TIMEOUT_SECONDS = float(os.getenv("DYNAMIC_TIMEOUT_SECONDS", "1.05"))
MAX_ZALO_MESSAGES = int(os.getenv("MAX_ZALO_MESSAGES", "4"))
TARGET_ZALO_CHARS = int(os.getenv("TARGET_ZALO_CHARS", "650"))
MAX_ZALO_TOTAL_CHARS = int(os.getenv("MAX_ZALO_TOTAL_CHARS", "2400"))
PENDING_TTL_SECONDS = int(os.getenv("PENDING_TTL_SECONDS", "30"))

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

# Bản demo chỉ chạy cục bộ, tách khỏi Zalo OA và production. Mặc định tắt để
# không vô tình công khai lịch sử hội thoại demo trên web service.
ENABLE_DEMO_CONSOLE = os.getenv("ENABLE_DEMO_CONSOLE", "false").lower() in ("1", "true", "yes", "on")
LOCAL_BIND_HOST = os.getenv(
    "LOCAL_BIND_HOST",
    "127.0.0.1" if ENABLE_DEMO_CONSOLE else "0.0.0.0",
)
