import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock

import config
import logger


def _store_returning(value, raises=False):
    store = MagicMock()
    if raises:
        store.get_config.side_effect = RuntimeError("airtable down")
    else:
        store.get_config.return_value = value
    return store


def test_resolves_config_value_and_caches():
    logger._alert_channel = None
    store = _store_returning("-1009999999999")
    assert logger._resolve_alert_channel(store) == "-1009999999999"
    # Second call must NOT hit Config again (cached).
    assert logger._resolve_alert_channel(store) == "-1009999999999"
    assert store.get_config.call_count == 1
    store.get_config.assert_called_with("telegram_channel_id")


def test_falls_back_to_constant_when_config_empty():
    logger._alert_channel = None
    store = _store_returning("")
    assert logger._resolve_alert_channel(store) == config.TELEGRAM_CHANNEL_ID


def test_falls_back_to_constant_on_lookup_error():
    logger._alert_channel = None
    store = _store_returning(None, raises=True)
    assert logger._resolve_alert_channel(store) == config.TELEGRAM_CHANNEL_ID
