"""10,000 distinct citizen-report scenarios for intake/conversation testing.

Each scenario changes four factual dimensions: incident, time, place and evidence.
The oracle checks intake behaviour, not guilt or legal conclusions.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class IncidentCase:
    case_id: str
    procedure_code: str
    queue: str
    question: str


INCIDENTS = (
    ("crime_report", "CRIME_INTAKE", "Tôi muốn trình báo tôi bị trộm xe máy"),
    ("crime_report", "CRIME_INTAKE", "Tôi muốn trình báo tôi bị trộm điện thoại"),
    ("assault_evidence", "CRIME_INTAKE", "Tôi muốn trình báo việc tôi bị người khác đánh và tôi đã đi khám thương tích"),
    ("assault_evidence", "CRIME_INTAKE", "Tôi muốn trình báo việc người khác dùng dao đánh tôi và tôi đã đi khám thương tích"),
    ("crime_report", "CRIME_INTAKE", "Tôi muốn trình báo việc tôi bị đe dọa"),
    ("fraud_transfer", "CRIME_INTAKE", "Tôi muốn trình báo tôi bị lừa chuyển khoản"),
    ("lost_document", "ADMIN_INTAKE", "Tôi muốn trình báo tôi làm mất điện thoại, không xác định bị trộm"),
    ("lost_document", "ADMIN_INTAKE", "Tôi muốn trình báo tôi làm mất xe, chưa xác định có bị trộm hay không"),
    ("crime_report", "CRIME_INTAKE", "Tôi muốn trình báo tội phạm về việc tài sản của tôi bị phá hoại và bị mất một phần tài sản"),
    ("crime_report", "CRIME_INTAKE", "Tôi muốn tố giác một sự việc có dấu hiệu tội phạm liên quan đến việc đe dọa mà tôi trực tiếp chứng kiến"),
)

TIMES = (
    "hôm nay lúc 06 giờ",
    "hôm nay lúc 09 giờ",
    "hôm nay lúc 12 giờ",
    "hôm nay lúc 15 giờ",
    "hôm nay lúc 18 giờ",
    "hôm qua lúc 20 giờ",
    "hôm qua lúc 22 giờ",
    "ngày hôm qua vào buổi sáng",
    "ngày hôm qua vào buổi chiều",
    "ngày hôm qua vào buổi tối",
)

PLACES = (
    "tại nhà tôi ở xã Pơng Drang",
    "tại khu vực đường liên thôn ở xã Pơng Drang",
    "tại một cửa hàng trên địa bàn xã Pơng Drang",
    "tại khu vực chợ trên địa bàn xã Pơng Drang",
    "tại vườn sầu riêng trên địa bàn xã Pơng Drang",
    "tại kho sầu riêng trên địa bàn xã Pơng Drang",
    "tại khu dân cư trên địa bàn xã Pơng Drang",
    "tại nơi làm việc của tôi trên địa bàn xã Pơng Drang",
    "tại khu vực tôi đang tạm trú ở xã Pơng Drang",
    "tại một địa điểm công cộng trên địa bàn xã Pơng Drang",
)

# Every evidence bundle deliberately contains at least one durable visual/text
# item so assault and fraud intake paths both see enough evidence information.
EVIDENCE = (
    "tôi còn video camera và ảnh chụp liên quan",
    "tôi còn tin nhắn và ảnh chụp màn hình",
    "tôi có người chứng kiến và ảnh chụp liên quan",
    "tôi còn clip cùng ảnh chụp ghi lại một phần sự việc",
    "tôi có thông tin biển số xe và ảnh chụp liên quan",
    "tôi đã lưu đặc điểm người liên quan và ảnh chụp màn hình",
    "tôi có chứng từ giao dịch và tin nhắn liên quan",
    "tôi có ảnh hiện trường và người chứng kiến",
    "tôi còn dữ liệu camera và ảnh chụp ở khu vực xảy ra sự việc",
    "tôi đã lưu tài liệu, tin nhắn và ảnh chụp liên quan để cung cấp",
)


def build_incident_corpus_10000():
    cases = []
    serial = 0
    for incident_index, (procedure_code, queue, incident) in enumerate(INCIDENTS, start=1):
        for time_index, time_text in enumerate(TIMES, start=1):
            for place_index, place in enumerate(PLACES, start=1):
                for evidence_index, evidence in enumerate(EVIDENCE, start=1):
                    serial += 1
                    question = f"{incident}, xảy ra {time_text} {place}; {evidence}. Tôi cần Công an tiếp nhận trình báo."
                    cases.append(IncidentCase(
                        case_id=f"IR{incident_index:02d}{time_index:02d}{place_index:02d}{evidence_index:02d}",
                        procedure_code=procedure_code,
                        queue=queue,
                        question=question,
                    ))
    assert serial == 10000
    assert len({case.case_id for case in cases}) == 10000
    assert len({case.question for case in cases}) == 10000
    return tuple(cases)
