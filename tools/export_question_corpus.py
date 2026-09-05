"""Xuất bộ 1.000 câu hỏi kiểm thử ra CSV UTF-8 để cán bộ rà soát."""

import csv
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from core.question_corpus import build_question_corpus


def export(destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("id", "nhom", "cau_hoi", "chinh_sach_kiem_thu", "nguon_ky_vong"))
        writer.writeheader()
        for case in build_question_corpus():
            writer.writerow({
                "id": case.case_id,
                "nhom": case.category,
                "cau_hoi": case.question,
                "chinh_sach_kiem_thu": case.policy,
                "nguon_ky_vong": case.source_prefix,
            })


if __name__ == "__main__":
    import sys
    export(sys.argv[1] if len(sys.argv) > 1 else "outputs/bo-1000-cau-hoi-kiem-thu.csv")
