from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
UNIT_NAME = os.getenv("UNIT_NAME", "Công an xã Pơng Drang, tỉnh Đắk Lắk")
HOTLINE = os.getenv("HOTLINE", "02623509777")
GROQ_API_KEY = "".join((os.getenv("GROQ_API_KEY") or "").split())
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1/chat/completions")

# AI Core đầy đủ dùng 120B. Zalo Dynamic bị giới hạn thời gian phản hồi rất ngắn,
# nên dùng GPT-OSS 20B cho nhánh real-time; câu trả lời pháp luật vẫn đi qua
# retrieval + verifier/fallback dựa trên nguồn.
ANSWER_MODEL = os.getenv("ANSWER_MODEL", "openai/gpt-oss-120b")
DYNAMIC_ANSWER_MODEL = os.getenv("DYNAMIC_ANSWER_MODEL", "openai/gpt-oss-20b")
PLANNER_MODEL = os.getenv("PLANNER_MODEL", "openai/gpt-oss-20b")

DB_PATH = Path(os.getenv("LEGAL_DB_PATH", str(BASE_DIR / "data" / "legal.db")))
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))
LEGAL_TOP_K = int(os.getenv("LEGAL_TOP_K", "8"))
DYNAMIC_LEGAL_TOP_K = int(os.getenv("DYNAMIC_LEGAL_TOP_K", "2"))
CORE_REASONING_EFFORT = os.getenv("CORE_REASONING_EFFORT", "medium")
DYNAMIC_REASONING_EFFORT = os.getenv("DYNAMIC_REASONING_EFFORT", "low")
CORE_TIMEOUT_SECONDS = float(os.getenv("CORE_TIMEOUT_SECONDS", "12"))
DYNAMIC_TIMEOUT_SECONDS = float(os.getenv("DYNAMIC_TIMEOUT_SECONDS", "1.45"))
MAX_ZALO_MESSAGES = int(os.getenv("MAX_ZALO_MESSAGES", "4"))
TARGET_ZALO_CHARS = int(os.getenv("TARGET_ZALO_CHARS", "650"))
MAX_ZALO_TOTAL_CHARS = int(os.getenv("MAX_ZALO_TOTAL_CHARS", "2400"))
PENDING_TTL_SECONDS = int(os.getenv("PENDING_TTL_SECONDS", "30"))
