"""Bộ đáp ứng cục bộ cho demo, không gọi provider và không tạo hồ sơ thật."""

from core import db
from core.intake import assess
from core.planner import plan
from core.retrieval import retrieve
from core.verifier import finalize, grounded_dynamic_fallback


def _no_source_answer(intake):
    if intake.get("procedure_code") == "unclassified":
        return (
            "Anh/chị cần tôi hỗ trợ nội dung nào: căn cước, VNeID, cư trú, đăng ký xe, "
            "trình báo hoặc tố giác?"
        )
    if intake.get("procedure_code") == "lost_document":
        return (
            "Tôi đã ghi nhận anh/chị bị mất thẻ Căn cước, giấy tờ hoặc tài sản. "
            "Kho dữ liệu demo chưa có nguồn thủ tục cấp lại đã được kiểm chứng cho đúng trường hợp, "
            "nên tôi chưa thể khẳng định giấy tờ, thời hạn hoặc điểm tiếp nhận."
        )
    if intake.get("procedure_code") == "crime_report":
        return (
            "Tôi đã ghi nhận anh/chị muốn trình báo hoặc thông tin về một sự việc. "
            "Tôi chưa thể kết luận trách nhiệm hay tội danh chỉ từ nội dung ban đầu. "
            "Sự việc xảy ra khi nào và ở đâu?"
        )
    if intake.get("procedure_code") == "assault_evidence":
        return (
            "Tôi đã ghi nhận anh/chị có hình ảnh hoặc video liên quan đến một sự việc. "
            "Anh/chị nên giữ nguyên file gốc, không chỉnh sửa và sao lưu thêm một bản; "
            "camera ghi lại sự việc gì để tôi hướng dẫn bước tiếp theo phù hợp?"
        )
    if intake.get("procedure_code") == "vehicle_registration":
        return (
            "Tôi đã ghi nhận anh/chị cần sang tên hoặc cấp đổi giấy tờ xe. "
            "Kho dữ liệu demo chưa có nguồn thủ tục đã được kiểm chứng cho đúng trường hợp này, "
            "nên tôi chưa thể tự nêu hồ sơ, thời hạn hoặc điểm tiếp nhận."
        )
    if intake.get("conversation_mode") == "intake_requested":
        question = intake.get("next_question")
        if question:
            return (
                "Tôi đã ghi nhận anh/chị muốn được tiếp nhận xử lý. "
                f"Để ghi nhận đúng nhu cầu, {question}? "
                "Phần hướng dẫn chi tiết chỉ được trả lời khi kho dữ liệu có nguồn đã kiểm chứng phù hợp."
            )
        return (
            "Tôi đã ghi nhận nhu cầu tiếp nhận của anh/chị. Kho dữ liệu demo chưa có nguồn đã kiểm chứng đủ gần "
            "để hướng dẫn chi tiết nội dung này, nên tôi sẽ không tự đoán thủ tục hoặc giấy tờ."
        )
    return (
        "Kho dữ liệu demo chưa có nguồn đã kiểm chứng đủ gần để tôi hướng dẫn chi tiết nội dung này. "
        "Tôi không tự đoán giấy tờ, thời hạn hoặc thẩm quyền khi chưa có nguồn phù hợp."
    )


def respond(demo_session_id, message):
    """Trả lời và lưu lịch sử demo bằng khóa HMAC như đường chạy thật.

    `handoff_status` chỉ là trạng thái mô phỏng để trình diễn; hàm này tuyệt đối
    không gửi dữ liệu sang Zalo, cán bộ hay bất cứ hệ thống bên ngoài nào.
    """
    history = db.get_history(demo_session_id, limit=10)
    intake = assess(message, history)
    search_plan = plan(message, history, dynamic=True)
    units = retrieve(search_plan, message) if search_plan.get("is_legal") else []

    if units:
        answer = grounded_dynamic_fallback(message, units)
        source_state = "grounded"
    else:
        answer = _no_source_answer(intake)
        source_state = "no_source"
    if intake.get("conversation_mode") == "intake_requested" and intake.get("next_question"):
        question = intake["next_question"]
        if question.casefold() not in answer.casefold():
            answer += f" Để ghi nhận yêu cầu tiếp nhận demo, {question}?"
    answer = finalize(answer)

    meta = {
        "demo": True,
        "source_state": source_state,
        "intake": intake,
    }
    db.add_message(demo_session_id, "user", message, meta={"demo": True})
    db.add_message(demo_session_id, "assistant", answer, meta=meta)
    return {
        "answer": answer,
        "mode": intake["conversation_mode"],
        "handoff_status": intake["handoff_status"],
        "source_state": source_state,
    }
