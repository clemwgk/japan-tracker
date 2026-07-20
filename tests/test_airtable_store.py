import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock

import config
from airtable_store import AirtableStore


def _mock_response():
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"records": []}
    return resp


def test_set_config_many_single_patch_all_records():
    store = AirtableStore("fake-pat")
    updates = {
        "telegram_last_logged_update_id": "693378410",
        "last_logger_run":                "2026-07-20T01:00:00+08:00",
        "last_logger_status":             "ok",
    }

    with patch("airtable_store.requests.patch", return_value=_mock_response()) as mock_patch, \
         patch("airtable_store.requests.get") as mock_get:
        store.set_config_many(updates)

    # Exactly one PATCH, and no fallback GET (all keys are cached).
    assert mock_patch.call_count == 1
    assert mock_get.call_count == 0

    args, kwargs = mock_patch.call_args
    # Targets the Config table URL with no trailing record id.
    url = args[0] if args else kwargs["url"]
    assert url.endswith(f"/{config.BASE_ID}/{config.TBL_CONFIG}")
    assert kwargs["timeout"] == 30

    body = kwargs["json"]
    records = body["records"]
    assert len(records) == len(updates)

    # Each record carries the cached record id and the value under FLD_CONFIG_VALUE.
    by_id = {r["id"]: r["fields"][config.FLD_CONFIG_VALUE] for r in records}
    for key, value in updates.items():
        rec_id = config.CONFIG_RECORD_IDS[key]
        assert by_id[rec_id] == value


def test_set_config_many_empty_noop():
    store = AirtableStore("fake-pat")
    with patch("airtable_store.requests.patch") as mock_patch:
        store.set_config_many({})
    assert mock_patch.call_count == 0
