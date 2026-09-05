from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import db
from core.ingest import import_article_index


def main():
    db.init_schema()
    count = import_article_index(
        index_path=ROOT / "Bộ luật Hình sự năm 2025 - chỉ mục điều luật.json",
        document_id="BLHS_2025",
        title="Bộ luật Hình sự năm 2025",
        source_path=ROOT / "Bộ luật Hình sự năm 2025.pdf",
        number="100/2015/QH13 (đã được sửa đổi, bổ sung)",
        issuer="Quốc hội",
        effective_from=None,
    )
    print(f"Đã nạp BLHS: {count} Điều.")
    print(db.stats())


if __name__ == "__main__":
    main()
