from pathlib import Path
import os

BASE_DIR = Path(os.getenv("BASE_DIR", Path(__file__).resolve().parent))
UNIT_NAME = os.getenv("UNIT_NAME", "Công an xã Pơng Drang, tỉnh Đắk Lắk")
HOTLINE = os.getenv("HOTLINE", "02623509777")
PRODUCTION_MODE = os.getenv("PRODUCTION_MODE", "false").lower() in ("1", "true", "yes", "on")
GROQ_API_KEY = "".join((os.getenv("GROQ_API_KEY") or "").split())
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1/chat/completions")
OPENAI_API_KEY = "".join((os.getenv("OPENAI_API_KEY") or "").split())
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")

MODEL_ROUTING_MODE = os.getenv("MODEL_ROUTING_MODE", "auto").strip().lower()
_AUTO_DYNAMIC_MODEL = "gpt-5.6-luna" if OPENAI_API_KEY else "openai/gpt-oss-20b"
_AUTO_ANSWER_MODEL = "gpt-5.6-terra" if OPENAI_API_KEY else "openai/gpt-oss-120b"
_AUTO_PLANNER_MODEL = "gpt-5.6-luna" if OPENAI_API_KEY else "openai/gpt-oss-20b"
DYNAMIC_PROVIDER_FALLBACK_MODEL = os.getenv(
    "DYNAMIC_PROVIDER_FALLBACK_MODEL",
    "openai/gpt-oss-20b" if GROQ_API_KEY else "",
).strip()

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
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "16"))
DYNAMIC_HISTORY_MESSAGES = int(os.getenv("DYNAMIC_HISTORY_MESSAGES", "12"))
DYNAMIC_HISTORY_MAX_CHARS = int(os.getenv("DYNAMIC_HISTORY_MAX_CHARS", "6000"))
RETRIEVAL_HISTORY_USER_TURNS = int(os.getenv("RETRIEVAL_HISTORY_USER_TURNS", "6"))
LEGAL_TOP_K = int(os.getenv("LEGAL_TOP_K", "8"))
DYNAMIC_LEGAL_TOP_K = int(os.getenv("DYNAMIC_LEGAL_TOP_K", "2"))
CORE_REASONING_EFFORT = os.getenv("CORE_REASONING_EFFORT", "medium")
GROQ_CORE_REASONING_EFFORT = os.getenv("GROQ_CORE_REASONING_EFFORT", "low")
DYNAMIC_REASONING_EFFORT = os.getenv(
    "DYNAMIC_REASONING_EFFORT",
    "none" if str(DYNAMIC_ANSWER_MODEL).startswith("gpt-5.6") else "low",
)
CORE_TIMEOUT_SECONDS = float(os.getenv("CORE_TIMEOUT_SECONDS", "12"))
# A dynamic conversation needs enough time for a real provider round trip.
# One second caused legitimate OpenAI/Groq responses to be aborted before the
# provider could answer, which turned ordinary questions into safe fallbacks.
DYNAMIC_TIMEOUT_SECONDS = float(os.getenv("DYNAMIC_TIMEOUT_SECONDS", "8"))
DYNAMIC_MAX_COMPLETION_TOKENS = int(os.getenv("DYNAMIC_MAX_COMPLETION_TOKENS", "140"))
MAX_ZALO_MESSAGES = int(os.getenv("MAX_ZALO_MESSAGES", "4"))
TARGET_ZALO_CHARS = int(os.getenv("TARGET_ZALO_CHARS", "650"))
MAX_ZALO_TOTAL_CHARS = int(os.getenv("MAX_ZALO_TOTAL_CHARS", "2400"))
PENDING_TTL_SECONDS = int(os.getenv("PENDING_TTL_SECONDS", "30"))

ZALO_WEBHOOK_ENABLED = os.getenv("ZALO_WEBHOOK_ENABLED", "true").lower() in ("1", "true", "yes", "on")
_requested_signature_check = os.getenv("ZALO_WEBHOOK_SIGNATURE_REQUIRED", "false").lower() in ("1", "true", "yes", "on")
ZALO_WEBHOOK_SIGNATURE_REQUIRED = bool(
    _requested_signature_check or (PRODUCTION_MODE and ZALO_WEBHOOK_ENABLED)
)
ZALO_APP_ID = os.getenv("ZALO_APP_ID", "").strip()
ZALO_OA_SECRET_KEY = os.getenv("ZALO_OA_SECRET_KEY", "").strip()
# OAuth App secret and OA webhook secret have different roles. Requiring the
# explicit OAuth secret prevents a false-ready state caused by guessing they are
# interchangeable.
ZALO_APP_SECRET_KEY = os.getenv("ZALO_APP_SECRET_KEY", "").strip()
ZALO_OA_ACCESS_TOKEN = os.getenv("ZALO_OA_ACCESS_TOKEN", "").strip()
ZALO_OA_REFRESH_TOKEN = os.getenv("ZALO_OA_REFRESH_TOKEN", "").strip()
ZALO_OAUTH_CALLBACK_URL = os.getenv("ZALO_OAUTH_CALLBACK_URL", "").strip()
ZALO_OAUTH_REFRESH_READY = bool(
    ZALO_APP_ID and ZALO_APP_SECRET_KEY and ZALO_OA_REFRESH_TOKEN
)
ZALO_REPLY_MODE = os.getenv("ZALO_REPLY_MODE", "auto").strip().lower()
_requested_direct_reply = os.getenv("ZALO_DIRECT_REPLY_ENABLED", "false").lower() in ("1", "true", "yes", "on")
ZALO_DIRECT_REPLY_ENABLED = bool(
    _requested_direct_reply
    or (ZALO_REPLY_MODE == "direct")
    or (
        ZALO_REPLY_MODE == "auto"
        and PRODUCTION_MODE
        and ZALO_WEBHOOK_ENABLED
        and (ZALO_OA_ACCESS_TOKEN or ZALO_OAUTH_REFRESH_READY)
    )
)
if ZALO_REPLY_MODE == "dynamic":
    ZALO_DIRECT_REPLY_ENABLED = False

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
HISTORY_HMAC_SECRET = os.getenv("HISTORY_HMAC_SECRET", "").strip()
HISTORY_RETENTION_DAYS = int(os.getenv("HISTORY_RETENTION_DAYS", "30"))
HISTORY_MAX_MESSAGES = int(os.getenv("HISTORY_MAX_MESSAGES", "40"))
HISTORY_POOL_MAX_SIZE = int(os.getenv("HISTORY_POOL_MAX_SIZE", "5"))
PERSISTENCE_REQUIRED = os.getenv(
    "PERSISTENCE_REQUIRED", "true" if PRODUCTION_MODE else "false"
).lower() in ("1", "true", "yes", "on")
ZALO_JOB_LEASE_SECONDS = int(os.getenv("ZALO_JOB_LEASE_SECONDS", "90"))
ZALO_JOB_MAX_ATTEMPTS = int(os.getenv("ZALO_JOB_MAX_ATTEMPTS", "3"))
ZALO_JOB_RETENTION_DAYS = int(os.getenv("ZALO_JOB_RETENTION_DAYS", "7"))

OFFICER_API_TOKEN = os.getenv("OFFICER_API_TOKEN", "").strip()
ENABLE_INTAKE_CASES = os.getenv("ENABLE_INTAKE_CASES", "true").lower() in ("1", "true", "yes", "on")

ENABLE_DEMO_CONSOLE = os.getenv("ENABLE_DEMO_CONSOLE", "false").lower() in ("1", "true", "yes", "on")
LOCAL_BIND_HOST = os.getenv(
    "LOCAL_BIND_HOST",
    "127.0.0.1" if ENABLE_DEMO_CONSOLE else "0.0.0.0",
)
