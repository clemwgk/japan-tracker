import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from telegram_client import parse_updates


MOCK_RESPONSE = {
    "ok": True,
    "result": [
        {
            "update_id": 693378403,
            "channel_post": {
                "message_id": 100,
                "chat": {"id": -1003985188435, "type": "channel"},
                "date": 1751100000,
                "text": "FUFU Kawaguchiko, friend says view rooms amazing"
            }
        },
        {
            "update_id": 693378404,
            "channel_post": {
                "message_id": 101,
                "chat": {"id": -1003985188435, "type": "channel"},
                "date": 1751100060,
                "photo": [{"file_id": "abc", "width": 100, "height": 100, "file_size": 1}],
                "caption": "Some scenic view in Kyoto beautiful"
            }
        },
        {
            "update_id": 693378405,
            "channel_post": {
                "message_id": 102,
                "chat": {"id": -1003985188435, "type": "channel"},
                "date": 1751100120,
                "text": "test"
            }
        },
        {
            "update_id": 693378406,
            "channel_post": {
                "message_id": 103,
                "chat": {"id": -1003985188435, "type": "channel"},
                "date": 1751100180,
                "pinned_message": {"message_id": 99, "text": "pinned"}
            }
        },
    ]
}


def test_parse_returns_four_updates():
    updates = parse_updates(MOCK_RESPONSE)
    assert len(updates) == 4


def test_updates_sorted_by_update_id():
    updates = parse_updates(MOCK_RESPONSE)
    ids = [u["update_id"] for u in updates]
    assert ids == sorted(ids)


def test_parse_text_update_no_skip():
    updates = parse_updates(MOCK_RESPONSE)
    u = next(u for u in updates if u["update_id"] == 693378403)
    assert "FUFU Kawaguchiko" in u["text"]
    assert u["chat_id"] == "-1003985188435"
    assert u["skip_reason"] is None


def test_parse_photo_with_caption_no_skip():
    updates = parse_updates(MOCK_RESPONSE)
    u = next(u for u in updates if u["update_id"] == 693378404)
    assert "Kyoto" in u["text"]
    assert u["skip_reason"] is None


def test_parse_short_text_skipped():
    updates = parse_updates(MOCK_RESPONSE)
    u = next(u for u in updates if u["update_id"] == 693378405)
    # "test" (4 chars) is text_too_short (< 10) — that check comes before test_message
    assert u["skip_reason"] == "text_too_short"


def test_parse_service_message_skipped():
    updates = parse_updates(MOCK_RESPONSE)
    u = next(u for u in updates if u["update_id"] == 693378406)
    assert u["skip_reason"] == "service_message"


def test_raw_json_is_valid_json():
    updates = parse_updates(MOCK_RESPONSE)
    for u in updates:
        parsed = json.loads(u["raw_json"])
        assert parsed["update_id"] == u["update_id"]


def test_date_is_iso_string():
    updates = parse_updates(MOCK_RESPONSE)
    u = updates[0]
    # Should be an ISO string ending with +08:00
    assert "+08:00" in u["date"]


def test_empty_result():
    updates = parse_updates({"ok": True, "result": []})
    assert updates == []
