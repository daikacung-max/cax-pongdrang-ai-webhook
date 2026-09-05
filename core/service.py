from config import DYNAMIC_LEGAL_TOP_K
from core import db
from core.planner import plan
from core.retrieval import retrieve, format_context
from core.answerer import answer as generate_answer, answer_dynamic_text
from core.verifier import (
    verify,
    verify_dynamic_text,
    grounded_dynamic_fallback,
    repair_note,
    finalize,
)
from core.llm import LLMError


class AICore:
    """Conversation -> Plan -> Retrieve -> Answer -> Verify -> Repair -> Finalize"""

    def chat(self, user_id, question, dynamic=False):
        user_id = str(user_id or "").strip()
        question = str(question or "").strip()
        if not user_id:
            raise ValueError("user_id là bắt buộc.")
        if not question:
            raise ValueError("question/message không được để trống.")

        history = db.get_history(user_id, limit=10)
        search_plan = plan(question, history, dynamic=dynamic)

        legal_units = []
        legal_context = ""
        if search_plan.get("is_legal"):
            legal_units = retrieve(search_plan, question)
            if dynamic:
                legal_units = legal_units[:max(1, min(DYNAMIC_LEGAL_TOP_K, 2))]
            legal_context = format_context(legal_units)

        # Nguyên tắc an toàn cốt lõi: câu hỏi pháp luật/TTHC mà chưa có nguồn phù hợp
        # thì không cho model tự sáng tác chi tiết cụ thể.
        if search_plan.get("is_legal") and not legal_units:
            raw_answer = grounded_dynamic_fallback(question, [])
            final_answer = finalize(raw_answer, contact_recommended=False)
            meta = {
                "legal": True,
                "retrieved_unit_ids": [],
                "verified": False,
                "repaired": False,
                "verification_errors": ["no_verified_source"],
                "dynamic": bool(dynamic),
                "path": "legal_no_source_fail_closed",
            }
            db.add_message(user_id, "user", question, meta={"legal_plan": search_plan})
            db.add_message(user_id, "assistant", final_answer, meta=meta)
            return {"answer": final_answer, "meta": meta}

        if dynamic:
            # Zalo Dynamic: một lần gọi model real-time. Nếu timeout hoặc verifier từ chối,
            # trả fail-safe dựng từ chính nguồn đã truy xuất.
            try:
                raw_answer = answer_dynamic_text(
                    question,
                    history,
                    legal_context=legal_context,
                )
                dynamic_check = verify_dynamic_text(raw_answer, legal_units) if legal_units else {
                    "ok": True,
                    "errors": [],
                }
                if not dynamic_check["ok"]:
                    raw_answer = grounded_dynamic_fallback(question, legal_units)
                    verified = False
                    verification_errors = dynamic_check["errors"]
                else:
                    verified = True
                    verification_errors = []
            except LLMError as exc:
                if legal_units:
                    raw_answer = grounded_dynamic_fallback(question, legal_units)
                    verified = False
                    verification_errors = [str(exc)]
                else:
                    raise

            final_answer = finalize(raw_answer, contact_recommended=False)
            meta = {
                "legal": bool(search_plan.get("is_legal")),
                "retrieved_unit_ids": [x["id"] for x in legal_units],
                "verified": bool(verified),
                "repaired": False,
                "verification_errors": verification_errors,
                "dynamic": True,
                "path": "fast_text_with_source_fallback",
            }

            db.add_message(user_id, "user", question, meta={"legal_plan": search_plan})
            db.add_message(user_id, "assistant", final_answer, meta=meta)
            return {"answer": final_answer, "meta": meta}

        # AI Core đầy đủ: 120B + structured claims + verifier + một lượt sửa.
        draft = generate_answer(
            question,
            history,
            legal_context=legal_context,
            dynamic=False,
        )

        verification = verify(draft, legal_units) if legal_units else {
            "ok": True,
            "errors": [],
            "verified_claims": [],
            "allowed_articles": [],
        }

        repaired = False
        if (not verification["ok"]) and legal_context:
            repaired = True
            draft = generate_answer(
                question,
                history,
                legal_context=legal_context,
                dynamic=False,
                repair_note=repair_note(verification),
            )
            verification = verify(draft, legal_units)

        if not verification["ok"]:
            raw_answer = grounded_dynamic_fallback(question, legal_units)
            contact_recommended = draft.get("contact_recommended", False)
        else:
            raw_answer = draft["answer"]
            contact_recommended = draft.get("contact_recommended", False)

        final_answer = finalize(
            raw_answer,
            contact_recommended=contact_recommended,
        )

        meta = {
            "legal": bool(search_plan.get("is_legal")),
            "retrieved_unit_ids": [x["id"] for x in legal_units],
            "verified": bool(verification["ok"]),
            "repaired": repaired,
            "verification_errors": verification.get("errors", []),
            "dynamic": False,
            "path": "structured_120b_verified",
        }

        db.add_message(user_id, "user", question, meta={"legal_plan": search_plan})
        db.add_message(user_id, "assistant", final_answer, meta=meta)

        return {"answer": final_answer, "meta": meta}


core = AICore()
