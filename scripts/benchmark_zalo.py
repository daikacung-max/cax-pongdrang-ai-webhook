"""Gửi bộ hội thoại tổng hợp qua đúng contract Zalo và ghi độ trễ phía khách."""

import argparse
import json
import time
import uuid

import requests


REQUIRED_CONVERSATION = [
    "Tôi bị người khác đánh.",
    "Kết quả thương tích là 5%.",
    "Người đó có dùng dao.",
    "Chỗ xảy ra việc có camera ghi lại.",
]

OTHER_CASES = [
    "Tôi muốn đăng ký tạm trú thì làm thế nào?",
    "Tôi muốn đăng ký thường trú vào nhà thuê thì cần làm gì?",
    "Tôi bị lừa chuyển khoản, giờ nên làm gì?",
    "Điều 134 quy định thế nào?",
    "Tôi muốn đăng ký VNeID mức độ 2.",
    "Đăng ký lần đầu xe máy cần những gì?",
]


def send_turn(session, base_url, uid, question, label, sequence):
    message_id = "bench-" + uuid.uuid4().hex
    webhook = {
        "event_name": "user_send_text",
        "sender": {"id": uid},
        "message": {"text": question, "msg_id": message_id},
    }
    post = session.post(base_url + "/zalo/webhook", json=webhook, timeout=15)
    post.raise_for_status()
    started = time.perf_counter()
    response = session.get(base_url + "/zalo/ai", params={"uid": uid}, timeout=30)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    response.raise_for_status()
    body = response.json()
    messages = body.get("content", {}).get("messages", [])
    return {
        "label": label,
        "sequence": sequence,
        "client_ms": elapsed_ms,
        "status": response.status_code,
        "text_only": bool(messages) and all(x.get("type") == "text" for x in messages),
        "message_count": len(messages),
        "answer": " ".join(str(x.get("text") or "") for x in messages),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--label", choices=("warm", "cold"), default="warm")
    parser.add_argument("--conversation-only", action="store_true")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    session = requests.Session()
    if args.label == "warm":
        session.get(base_url + "/health", timeout=30).raise_for_status()

    cases = REQUIRED_CONVERSATION if args.conversation_only else REQUIRED_CONVERSATION + OTHER_CASES
    shared_uid = "benchmark-conversation-" + uuid.uuid4().hex
    for index in range(max(1, args.count)):
        question = cases[index % len(cases)]
        uid = shared_uid if index < len(REQUIRED_CONVERSATION) else "benchmark-" + uuid.uuid4().hex
        result = send_turn(session, base_url, uid, question, args.label, index + 1)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
