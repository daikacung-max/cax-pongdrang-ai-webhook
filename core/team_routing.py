"""Phân luồng nghiệp vụ nội bộ cho Công an xã Pơng Drang.

Nhãn tổ công tác chỉ giúp chatbot hướng dẫn và xếp hàng đợi đúng hướng. Nó
không thay thế việc cán bộ có thẩm quyền kiểm tra, phân công hoặc thụ lý hồ sơ.
"""


TEAM_BY_QUEUE = {
    "ADMIN_IDENTITY": "Tổ Cảnh sát khu vực",
    "ADMIN_RESIDENCE": "Tổ Cảnh sát khu vực",
    "ADMIN_INTAKE": "Tổ Cảnh sát khu vực",
    "CRIME_INTAKE": "Tổ Cảnh sát phòng, chống tội phạm",
    "VEHICLE_REGISTRATION": "Tổ Cảnh sát trật tự",
    "PUBLIC_ORDER_INTAKE": "Tổ Cảnh sát khu vực",
    "COMMUNITY_DISPUTE_INTAKE": "Tổ Cảnh sát khu vực",
}


def team_for_queue(queue):
    """Trả tên tổ phù hợp, hoặc ``None`` khi chưa đủ để phân loại."""
    return TEAM_BY_QUEUE.get(str(queue or ""))


def routing_prompt_hint(intake):
    """Ngữ cảnh ngắn cho model, không công bố mã hàng đợi nội bộ."""
    team = (intake or {}).get("handling_team")
    if not team:
        return ""
    return (
        f"PHÂN LUỒNG NGHIỆP VỤ: Nội dung này thuộc {team}. "
        "Khi người dân hỏi tổ nào phụ trách, đang yêu cầu tiếp nhận, hoặc cần biết nơi xử lý, "
        "hãy nêu đúng tên tổ này một cách tự nhiên. Không nói hồ sơ đã được chuyển/thụ lý "
        "trừ khi hệ thống thực sự đã tạo yêu cầu tiếp nhận."
    )
