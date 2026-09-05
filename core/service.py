from core import db
from core.planner import plan
from core.retrieval import retrieve, format_context
from core.answerer import answer as generate_answer
from core.verifier import verify, repair_note, finalize


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
            legal_context = format_context(legal_units)

        draft = generate_answer(
            question, history, legal_context=legal_context, dynamic=dynamic
        )

        verification = verify(draft, legal_units) if legal_units else {
            "ok": True,
            "errors": [],
            "verified_claims": [],
            "allowed_articles": [],
        }

        repaired = False
        if not verification["ok"] and legal_context:
            repaired = True
            draft = generate_answer(
                question,
                history,
                legal_context=legal_context,
                dynamic=dynamic,
                repair_note=repair_note(verification),
            )
            verification = verify(draft, legal_units)

        if not verification["ok"]:
            raw_answer = (
                "Tôi có thể tiếp tục hỗ trợ anh/chị phân tích tình huống, "
                "nhưng phần viện dẫn pháp luật cụ thể trong câu trả lời vừa tạo "
                "chưa vượt qua bước kiểm chứng nguồn. Anh/chị có thể mô tả thêm "
                "diễn biến, hậu quả và tài liệu đang có để tôi tra đúng quy định liên quan."
            )
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
        }

        db.add_message(user_id, "user", question, meta={"legal_plan": search_plan})
        db.add_message(user_id, "assistant", final_answer, meta=meta)

        return {"answer": final_answer, "meta": meta}


core = AICore()
