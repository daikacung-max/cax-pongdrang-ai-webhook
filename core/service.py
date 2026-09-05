from config import (
    ANSWER_MODEL,
    DYNAMIC_ANSWER_MODEL,
    DYNAMIC_LEGAL_TOP_K,
    ENABLE_MODEL_ESCALATION,
    ESCALATION_MODEL,
    MAX_HISTORY_MESSAGES,
)
from core import db
from core import cases
from core.answerer import answer as generate_answer, answer_dynamic_text
from core.history import conversation_key
from core.intake import assess as assess_intake, prompt_hint as intake_prompt_hint
from core.llm import LLMTimeout
from core.planner import plan
from core.providers import provider_name_for_model
from core.retrieval import format_context, retrieve
from core.telemetry import StageTimer
from core.verifier import (
    finalize,
    grounded_dynamic_fallback,
    norm,
    repair_note,
    verify,
    verify_dynamic_text,
)


def _safe_question_for_fallback(question):
    q = str(question or "")
    q = q.replace("thường chú", "thường trú").replace("thuong chu", "thuong tru")
    q = q.replace("tạm chú", "tạm trú").replace("tam chu", "tam tru")
    q = q.replace("vne id", "vneid").replace("VNe ID", "VNeID").replace("vnied", "vneid")
    return q


def _has_doc_prefix(units, prefix):
    return any(str(x.get("document_id") or "").startswith(prefix) for x in units)


def _dynamic_answer_is_weak(question, answer, legal_units):
    """Chỉ buộc fallback khi model bỏ qua nguồn hoặc đưa hướng dẫn TTHC rủi ro."""
    q = norm(question)
    a = norm(answer)

    if any(str(x.get("article") or "") == "134" for x in legal_units):
        # Dữ kiện mới ở chuỗi hành hung phải được nhắc đúng; nếu không, dùng câu
        # fallback đã bám nguồn thay vì hỏi lại một thông tin vừa được người dân nêu.
        if "%" in q and "%" not in a:
            return True
        if "dao" in q and "dao" not in a:
            return True
        if any(x in q for x in ["camera", "video", "clip", "ghi hinh"]) and not any(
            x in a for x in ["camera", "video", "clip", "ghi hinh"]
        ):
            return True

    if _has_doc_prefix(legal_units, "VNEID_"):
        weak = [
            "chua the ket luan",
            "tham khao huong dan cu the tu bo cong an",
            "trang chinh thuc cua vneid",
            "khong co du thong tin de huong dan",
        ]
        if any(x in a for x in weak):
            return True

    if any(str(x.get("document_id") or "").startswith(("RESIDENCE_", "TTHC_TEMP_RESIDENCE_")) for x in legal_units):
        risky = [
            "ho khau gia dinh", "so ho khau", "giay khai sinh", "giay ket hon",
            "so do", "so hong", "dich vu buu chinh", "buu chinh cong ich",
            "van phong cong an xa", "giay to tuy than cua nguoi dang ky",
        ]
        if any(x in a for x in risky):
            return True

    return False


def _model_meta(model):
    return {"model": model, "provider": provider_name_for_model(model)}


class AICore:
    """Conversation -> Plan -> Retrieve -> Answer -> Verify -> Repair -> Finalize"""

    def chat(self, user_id, question, dynamic=False, trace_id=None):
        user_id = str(user_id or "").strip()
        question = str(question or "").strip()
        if not user_id:
            raise ValueError("user_id là bắt buộc.")
        if not question:
            raise ValueError("question/message không được để trống.")

        timer = StageTimer(trace_id=trace_id)
        safety_identifier = conversation_key(user_id)
        fallback_reason = None
        model_used = DYNAMIC_ANSWER_MODEL if dynamic else ANSWER_MODEL
        models_used = []

        with timer.stage("history_ms"):
            history = db.get_history(user_id, limit=MAX_HISTORY_MESSAGES)
        intake = assess_intake(question, history)
        intake_hint = intake_prompt_hint(intake)
        with timer.stage("planner_ms"):
            search_plan = plan(
                question,
                history,
                dynamic=dynamic,
                safety_identifier=safety_identifier,
            )

        legal_units = []
        legal_context = ""
        with timer.stage("retrieval_ms"):
            if search_plan.get("is_legal"):
                legal_units = retrieve(search_plan, question)
                if dynamic:
                    legal_units = legal_units[:max(1, min(DYNAMIC_LEGAL_TOP_K, 2))]
                legal_context = format_context(legal_units)

        fallback_question = _safe_question_for_fallback(question)

        if search_plan.get("is_legal") and not legal_units:
            fallback_reason = "no_source"
            with timer.stage("finalize_ms"):
                final_answer = finalize(grounded_dynamic_fallback(fallback_question, []))
            final_answer, handoff = self._record_ready_intake(user_id, intake, final_answer)
            meta = {
                "legal": True, "retrieved_unit_ids": [], "verified": False,
                "repaired": False, "verification_errors": ["no_verified_source"],
                "dynamic": bool(dynamic), "path": "legal_no_source_fail_closed",
                "intake": intake,
                "handoff": handoff,
                **_model_meta(model_used),
            }
            self._save(user_id, question, final_answer, search_plan, meta)
            telemetry = timer.finish(
                fallback_reason=fallback_reason,
                model_used=model_used,
                retrieved_unit_count=0,
            )
            return {"answer": final_answer, "meta": meta, "handoff": handoff, "_telemetry": telemetry}

        if dynamic:
            verified = False
            verification_errors = []
            try:
                with timer.stage("llm_ms"):
                    raw_answer = answer_dynamic_text(
                        question,
                        history,
                        legal_context=legal_context,
                        model=model_used,
                        safety_identifier=safety_identifier,
                        intake_hint=intake_hint,
                    )
                models_used.append(model_used)
                with timer.stage("verify_ms"):
                    check = verify_dynamic_text(raw_answer, legal_units, question=question) if legal_units else {"ok": True, "errors": []}
                    weak = _dynamic_answer_is_weak(question, raw_answer, legal_units)
                if check["ok"] and not weak:
                    verified = True
                else:
                    fallback_reason = "weak_answer" if weak else "verification_failed"
                    raw_answer = grounded_dynamic_fallback(fallback_question, legal_units)
                    verification_errors = check["errors"] + (["weak_answer"] if weak else [])
            except LLMTimeout:
                fallback_reason = "llm_timeout"
                if not legal_units:
                    raise
                raw_answer = grounded_dynamic_fallback(fallback_question, legal_units)
                verification_errors = ["dynamic_fallback:LLMTimeout"]
            except Exception as exc:
                fallback_reason = "llm_error"
                if not legal_units:
                    raise
                raw_answer = grounded_dynamic_fallback(fallback_question, legal_units)
                verification_errors = [f"dynamic_fallback:{type(exc).__name__}"]

            with timer.stage("finalize_ms"):
                final_answer = finalize(raw_answer)
            final_answer, handoff = self._record_ready_intake(user_id, intake, final_answer)
            meta = {
                "legal": bool(search_plan.get("is_legal")),
                "retrieved_unit_ids": [x["id"] for x in legal_units],
                "verified": bool(verified), "repaired": False,
                "verification_errors": verification_errors,
                "dynamic": True, "path": "single_call_or_grounded_fallback",
                "intake": intake,
                "handoff": handoff,
                **_model_meta(model_used),
            }
            self._save(user_id, question, final_answer, search_plan, meta)
            telemetry = timer.finish(
                fallback_reason=fallback_reason,
                model_used=model_used,
                retrieved_unit_count=len(legal_units),
            )
            return {"answer": final_answer, "meta": meta, "handoff": handoff, "_telemetry": telemetry}

        if ENABLE_MODEL_ESCALATION and search_plan.get("complexity") == "complex":
            model_used = ESCALATION_MODEL

        with timer.stage("llm_ms"):
            draft = generate_answer(
                question, history, legal_context=legal_context, dynamic=False,
                model=model_used, safety_identifier=safety_identifier, intake_hint=intake_hint,
            )
        models_used.append(model_used)
        with timer.stage("verify_ms"):
            verification = verify(draft, legal_units) if legal_units else {
                "ok": True, "errors": [], "verified_claims": [], "allowed_articles": [],
            }

        repaired = False
        if not verification["ok"] and legal_context:
            repaired = True
            with timer.stage("llm_ms"):
                draft = generate_answer(
                    question, history, legal_context=legal_context, dynamic=False,
                    repair_note=repair_note(verification), model=model_used,
                    safety_identifier=safety_identifier, intake_hint=intake_hint,
                )
            models_used.append(model_used)
            with timer.stage("verify_ms"):
                verification = verify(draft, legal_units)

        if (
            not verification["ok"] and legal_context and ENABLE_MODEL_ESCALATION
            and model_used != ESCALATION_MODEL
        ):
            model_used = ESCALATION_MODEL
            with timer.stage("llm_ms"):
                draft = generate_answer(
                    question, history, legal_context=legal_context, dynamic=False,
                    repair_note=repair_note(verification), model=model_used,
                    safety_identifier=safety_identifier, intake_hint=intake_hint,
                )
            models_used.append(model_used)
            with timer.stage("verify_ms"):
                verification = verify(draft, legal_units)

        if verification["ok"]:
            raw_answer = draft["answer"]
            contact_recommended = draft.get("contact_recommended", False)
        else:
            fallback_reason = "verification_failed"
            raw_answer = grounded_dynamic_fallback(fallback_question, legal_units)
            contact_recommended = False

        with timer.stage("finalize_ms"):
            final_answer = finalize(raw_answer, contact_recommended=contact_recommended)
        final_answer, handoff = self._record_ready_intake(user_id, intake, final_answer)
        meta = {
            "legal": bool(search_plan.get("is_legal")),
            "retrieved_unit_ids": [x["id"] for x in legal_units],
            "verified": bool(verification["ok"]), "repaired": repaired,
            "verification_errors": verification.get("errors", []),
            "dynamic": False, "path": "structured_verified",
            "intake": intake,
            "handoff": handoff,
            **_model_meta(model_used), "models_used": models_used,
        }
        self._save(user_id, question, final_answer, search_plan, meta)
        telemetry = timer.finish(
            fallback_reason=fallback_reason,
            model_used=model_used,
            retrieved_unit_count=len(legal_units),
        )
        return {"answer": final_answer, "meta": meta, "handoff": handoff, "_telemetry": telemetry}

    @staticmethod
    def _record_ready_intake(user_id, intake, answer_text):
        """Ghi hồ sơ sau khi người dân yêu cầu tiếp nhận và đã đủ dữ kiện."""
        handoff = cases.create_or_get_open(user_id, intake)
        if handoff and handoff.get("created"):
            answer_text = (
                f"{answer_text} Yêu cầu của anh/chị đã được ghi nhận với mã "
                f"{handoff['case_id']} để bộ phận chuyên môn tiếp nhận."
            )
        return answer_text, handoff

    @staticmethod
    def _save(user_id, question, final_answer, search_plan, meta):
        db.add_message(user_id, "user", question, meta={"legal_plan": search_plan})
        db.add_message(user_id, "assistant", final_answer, meta=meta)


core = AICore()
