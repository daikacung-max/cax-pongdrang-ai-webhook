from config import DYNAMIC_LEGAL_TOP_K
from core import db
from core.planner import plan
from core.retrieval import retrieve, format_context
from core.answerer import answer as generate_answer, answer_dynamic_text
from core.verifier import verify, verify_dynamic_text, grounded_dynamic_fallback, repair_note, finalize
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

        if search_plan.get("is_legal") and not legal_units:
            raw_answer = grounded_dynamic_fallback(question, [])
            final_answer = finalize(raw_answer)
            meta = {
                "legal": True, "retrieved_unit_ids": [], "verified": False, "repaired": False,
                "verification_errors": ["no_verified_source"], "dynamic": bool(dynamic), "path": "legal_no_source_fail_closed",
            }
            db.add_message(user_id, "user", question, meta={"legal_plan": search_plan})
            db.add_message(user_id, "assistant", final_answer, meta=meta)
            return {"answer": final_answer, "meta": meta}

        if dynamic:
            # Dynamic chỉ gọi model một lần. Bất kỳ lỗi model/verifier nào cũng rơi về nguồn cục bộ,
            # không đẩy lỗi kỹ thuật ra cho người dân nếu đã có nguồn phù hợp.
            try:
                raw_answer = answer_dynamic_text(question, history, legal_context=legal_context)
                check = verify_dynamic_text(raw_answer, legal_units) if legal_units else {"ok": True, "errors": []}
                if check["ok"]:
                    verified = True
                    verification_errors = []
                else:
                    raw_answer = grounded_dynamic_fallback(question, legal_units)
                    verified = False
                    verification_errors = check["errors"]
            except Exception as exc:
                if legal_units:
                    raw_answer = grounded_dynamic_fallback(question, legal_units)
                    verified = False
                    verification_errors = [f"dynamic_fallback:{type(exc).__name__}"]
                else:
                    raise

            final_answer = finalize(raw_answer)
            meta = {
                "legal": bool(search_plan.get("is_legal")),
                "retrieved_unit_ids": [x["id"] for x in legal_units],
                "verified": bool(verified), "repaired": False,
                "verification_errors": verification_errors,
                "dynamic": True, "path": "single_call_or_grounded_fallback",
            }
            db.add_message(user_id, "user", question, meta={"legal_plan": search_plan})
            db.add_message(user_id, "assistant", final_answer, meta=meta)
            return {"answer": final_answer, "meta": meta}

        draft = generate_answer(question, history, legal_context=legal_context, dynamic=False)
        verification = verify(draft, legal_units) if legal_units else {"ok": True, "errors": [], "verified_claims": [], "allowed_articles": []}
        repaired = False
        if not verification["ok"] and legal_context:
            repaired = True
            draft = generate_answer(question, history, legal_context=legal_context, dynamic=False, repair_note=repair_note(verification))
            verification = verify(draft, legal_units)

        if verification["ok"]:
            raw_answer = draft["answer"]
            contact_recommended = draft.get("contact_recommended", False)
        else:
            raw_answer = grounded_dynamic_fallback(question, legal_units)
            contact_recommended = False

        final_answer = finalize(raw_answer, contact_recommended=contact_recommended)
        meta = {
            "legal": bool(search_plan.get("is_legal")),
            "retrieved_unit_ids": [x["id"] for x in legal_units],
            "verified": bool(verification["ok"]), "repaired": repaired,
            "verification_errors": verification.get("errors", []),
            "dynamic": False, "path": "structured_120b_verified",
        }
        db.add_message(user_id, "user", question, meta={"legal_plan": search_plan})
        db.add_message(user_id, "assistant", final_answer, meta=meta)
        return {"answer": final_answer, "meta": meta}


core = AICore()
