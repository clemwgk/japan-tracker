import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from telegram_client import compute_gap, summarize


def _upd(uid):
    return {
        "update_id": uid, "text": "lead text here ok", "service": False,
        "chat_id": "-1", "date": "2026-06-29T08:00:00+08:00",
        "raw_json": "{}", "raw_truncated": False, "skip_reason": None,
    }


UPDATES = [_upd(100), _upd(101), _upd(102)]


def test_no_gap_when_contiguous():
    # requested=100, lowest seen=100 → no gap
    assert compute_gap(UPDATES, requested_offset=100) is False


def test_possible_gap_when_jump():
    # requested=98, lowest seen=100 → gap of 2
    assert compute_gap(UPDATES, requested_offset=98) is True


def test_single_update_no_gap():
    assert compute_gap([_upd(693378410)], requested_offset=693378410) is False


def test_single_update_gap():
    assert compute_gap([_upd(693378410)], requested_offset=693378405) is True


def test_empty_updates_no_gap():
    # SP-H2: zero-update run must not falsely report a gap
    assert compute_gap([], requested_offset=693378409) is False


def test_summarize_normal():
    s = summarize(UPDATES)
    assert s["lowest"] == 100
    assert s["highest"] == 102
    assert s["count"] == 3


def test_summarize_single():
    s = summarize([_upd(500)])
    assert s["lowest"] == 500
    assert s["highest"] == 500
    assert s["count"] == 1


def test_summarize_empty():
    s = summarize([])
    assert s["lowest"] is None
    assert s["highest"] is None
    assert s["count"] == 0


def test_zero_update_run_offset_safety():
    """
    SP-H2: when getUpdates returns 0 results, compute_gap is False.
    The logger must NOT advance the offset in this case.
    This test verifies the pure-function contract; logger logic tested separately.
    """
    assert compute_gap([], requested_offset=693378409) is False
    s = summarize([])
    assert s["highest"] is None  # logger checks: if highest is None, don't commit
