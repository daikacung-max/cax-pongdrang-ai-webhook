from config import DYNAMIC_LEGAL_TOP_K
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
            if dynamic:
                # Dynamic chỉ có cửa sổ phản hồi rất ngắn. Giữ các nguồn xếp hạng cao nhất,
                # giảm input token và giảm nguy cơ rate-limit/timeout.
                legal_units = legal_units[:DYNAMIC_LEGAL_TOP_K]
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
        # Với API Core đầy đủ, cho model sửa 1 lần. Với Zalo Dynamic, không gọi model lần 2
        # vì vượt giới hạn thời gian; nếu claim chưa đạt, dùng fail-safe có nguồn.
        if (not dynamic) and (not verification["ok"]) and legal_context:
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
            # Chỉ dùng khi verifier bắt được claim chưa đủ căn cứ. Không phát claim sai.
            if legal_units:
                top = legal_units[0]
                article = str(top.get("article") or "").strip()
                title = str(top.get("title") or "").strip()
                if article and title:
                    raw_answer = (
                        f"Nội dung anh/chị hỏi có liên quan đến Điều {article} Bộ luật Hình sự, "
                        f"{title}. Tuy nhiên, từ các dữ kiện hiện có chưa nên kết luận theo một điều kiện riêng lẻ; "
                        "cần xem đầy đủ các trường hợp và ngoại lệ ngay trong điều luật, cùng diễn biến thực tế của vụ việc. "
                        "Anh/chị có thể cho biết thêm công cụ được sử dụng, cách sử dụng và kết quả xác định tỷ lệ tổn thương cơ thể để tôi phân tích sát hơn."
                    )
                else:
                    raw_answer = (
                        "Phần viện dẫn pháp luật cụ thể vừa tạo chưa vượt qua bước kiểm chứng nguồn. "
                        "Anh/chị có thể mô tả thêm dữ kiện của vụ việc để tôi tra và phân tích chính xác hơn."
                    )
            else:
                raw_answer = (
                    "Tôi có thể tiếp tục hỗ trợ anh/chị phân tích tình huống, nhưng hiện chưa có đủ nguồn "
                    "để khẳng định chi tiết pháp lý cụ thể. Anh/chị có thể mô tả thêm dữ kiện cần làm rõ."
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
            "dynamic": bool(dynamic),
        }

        db.add_message(user_id, "user", question, meta={"legal_plan": search_plan})
        db.add_message(user_id, "assistant", final_answer, meta=meta)

        return {"answer": final_answer, "meta": meta}


core = AICore()
