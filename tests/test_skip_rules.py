import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from telegram_client import classify_skip


def _upd(text, service=False):
    return {"update_id": 1, "text": text, "service": service}


def test_service_message():
    assert classify_skip(_upd(None, service=True)) == "service_message"


def test_no_text_none():
    assert classify_skip(_upd(None)) == "no_text"


def test_no_text_empty():
    assert classify_skip(_upd("")) == "no_text"


def test_no_text_whitespace():
    assert classify_skip(_upd("   ")) == "no_text"


def test_text_too_short():
    assert classify_skip(_upd("hi")) == "text_too_short"


def test_exactly_at_min_length_is_not_short():
    # MIN_TEXT_LENGTH is 10; exactly 10 chars should not be text_too_short
    import config
    text = "A" * config.MIN_TEXT_LENGTH
    result = classify_skip(_upd(text))
    assert result != "text_too_short"


def test_emoji_only():
    # Must be >= MIN_TEXT_LENGTH chars so text_too_short doesn't fire first
    assert classify_skip(_upd("😀😂🎉🌸✨😎🍕🎸🌊🔥")) == "emoji_only"


def test_emoji_only_with_spaces():
    # Spaces count toward length but \w still finds no word chars
    assert classify_skip(_upd("😀 😂 🎉 🌸 ✨ 😎 🍕")) == "emoji_only"


def test_test_message_whole_word():
    assert classify_skip(_upd("test hotel in tokyo please ignore")) == "test_message"


def test_test_message_case_insensitive():
    assert classify_skip(_upd("TEST this is a probe lead")) == "test_message"


def test_test_not_matched_in_word():
    # "testing" contains "test" but as substring — should NOT skip as test_message
    result = classify_skip(_upd("Testing the waters at this ryokan amazing"))
    assert result != "test_message"


def test_normal_hotel_lead():
    assert classify_skip(_upd("Shinagawa Prince Hotel — great views, friend recommends")) is None


def test_japanese_with_english():
    assert classify_skip(_upd("東京 ホテル amazing baths and great location")) is None


def test_url_only_lead():
    # URL has word chars (alphanumeric) so not emoji_only; long enough
    result = classify_skip(_upd("https://example.com/hotel-review-page-long"))
    assert result is None


def test_service_takes_priority_over_no_text():
    assert classify_skip(_upd(None, service=True)) == "service_message"
