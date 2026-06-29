"""
Japan Tracker v2 — Airtable REST adapter (portability seam).

All Airtable reads/writes for the logger go through this class.
Reads env var AIRTABLE_PAT via the caller; secrets are never imported here.
"""

import datetime

import requests

import config


class AirtableStore:
    BASE_URL = "https://api.airtable.com/v0"

    def __init__(self, pat):
        self._headers = {
            "Authorization": f"Bearer {pat}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, table_id, params=None):
        url = f"{self.BASE_URL}/{config.BASE_ID}/{table_id}"
        merged = {"returnFieldsByFieldId": "true"}
        if params:
            merged.update(params)
        r = requests.get(url, headers=self._headers, params=merged, timeout=30)
        r.raise_for_status()
        return r.json()

    def _post(self, table_id, body):
        url = f"{self.BASE_URL}/{config.BASE_ID}/{table_id}"
        r = requests.post(url, headers=self._headers, json=body, timeout=30)
        r.raise_for_status()
        return r.json()

    def _patch(self, table_id, rec_id, body):
        url = f"{self.BASE_URL}/{config.BASE_ID}/{table_id}/{rec_id}"
        r = requests.patch(url, headers=self._headers, json=body, timeout=30)
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def get_config(self, key):
        """Return the value string for a Config key, or None if not found."""
        data = self._get(
            config.TBL_CONFIG,
            params={"filterByFormula": f"{{key}}='{key}'", "maxRecords": 1},
        )
        records = data.get("records", [])
        if not records:
            return None
        return records[0].get("fields", {}).get(config.FLD_CONFIG_VALUE) or ""

    def set_config(self, key, value):
        """Set a Config row value. Uses cached record ID when known."""
        rec_id = config.CONFIG_RECORD_IDS.get(key)
        if not rec_id:
            data = self._get(
                config.TBL_CONFIG,
                params={"filterByFormula": f"{{key}}='{key}'", "maxRecords": 1},
            )
            records = data.get("records", [])
            if not records:
                raise ValueError(f"Config key not found: {key!r}")
            rec_id = records[0]["id"]

        self._patch(config.TBL_CONFIG, rec_id, {"fields": {config.FLD_CONFIG_VALUE: value}})

    # ------------------------------------------------------------------
    # Inbox
    # ------------------------------------------------------------------

    def find_inbox_by_update_id(self, update_id):
        """Return the Airtable record dict for the given update_id, or None."""
        data = self._get(
            config.TBL_INBOX,
            params={
                "filterByFormula": f"{{update_id}}={int(update_id)}",
                "maxRecords": 1,
            },
        )
        records = data.get("records", [])
        return records[0] if records else None

    def create_inbox_row(self, *, update_id, captured_at, message_date, text,
                         chat_id, raw_json, raw_truncated, status,
                         skip_reason=None, possible_gap=False):
        """Create an Inbox row. Returns the new record ID."""
        if len(raw_json) > config.RAW_JSON_MAX_CHARS:
            raw_json = raw_json[:config.RAW_JSON_MAX_CHARS]
            raw_truncated = True

        fields = {
            config.FLD_INBOX_UPDATE_ID:     int(update_id),
            config.FLD_INBOX_CAPTURED_AT:   captured_at,
            config.FLD_INBOX_MESSAGE_DATE:  message_date,
            config.FLD_INBOX_TEXT:          text or "",
            config.FLD_INBOX_CHAT_ID:       str(chat_id),
            config.FLD_INBOX_RAW_JSON:      raw_json,
            config.FLD_INBOX_RAW_TRUNCATED: bool(raw_truncated),
            config.FLD_INBOX_STATUS:        status,
            config.FLD_INBOX_POSSIBLE_GAP:  bool(possible_gap),
        }
        if skip_reason:
            fields[config.FLD_INBOX_SKIP_REASON] = skip_reason

        result = self._post(config.TBL_INBOX, {"fields": fields})
        return result["id"]

    def update_inbox_row(self, rec_id, **kwargs):
        """Update named Inbox fields on an existing row."""
        _MAP = {
            "status":           config.FLD_INBOX_STATUS,
            "skip_reason":      config.FLD_INBOX_SKIP_REASON,
            "possible_gap":     config.FLD_INBOX_POSSIBLE_GAP,
            "target_table":     config.FLD_INBOX_TARGET_TABLE,
            "target_record_id": config.FLD_INBOX_TARGET_RECORD_ID,
            "retry_count":      config.FLD_INBOX_RETRY_COUNT,
            "claimed_at":       config.FLD_INBOX_CLAIMED_AT,
            "claim_run_id":     config.FLD_INBOX_CLAIM_RUN_ID,
            "processed_at":     config.FLD_INBOX_PROCESSED_AT,
            "error_detail":     config.FLD_INBOX_ERROR_DETAIL,
        }
        fields = {_MAP[k]: v for k, v in kwargs.items() if k in _MAP}
        if not fields:
            return
        self._patch(config.TBL_INBOX, rec_id, {"fields": fields})

    def get_pending_inbox_rows(self, max_records=200):
        """Return Inbox records with status=pending (for watchdog age check)."""
        data = self._get(
            config.TBL_INBOX,
            params={
                "filterByFormula": "{status}='pending'",
                "maxRecords": max_records,
            },
        )
        return data.get("records", [])

    # ------------------------------------------------------------------
    # RunLog
    # ------------------------------------------------------------------

    def write_runlog(self, *, run_type, run_id, run_timestamp,
                     errors=0, error_detail="",
                     raw_update_count=0, offset_requested=0, offset_committed=0,
                     lowest_update_id_seen=None, highest_update_id_seen=None,
                     getupdates_http_status="", possible_gap_detected=False,
                     hotels_added=0, food_added=0, scenic_added=0,
                     skipped=0, messages_found=0):
        """Append one row to RunLog."""
        fields = {
            config.FLD_RUNLOG_RUN_TYPE:               run_type,
            config.FLD_RUNLOG_RUN_ID:                 str(run_id),
            config.FLD_RUNLOG_RUN_TIMESTAMP:          run_timestamp,
            config.FLD_RUNLOG_ERRORS:                 int(errors),
            config.FLD_RUNLOG_ERROR_DETAIL:           error_detail or "",
            config.FLD_RUNLOG_RAW_UPDATE_COUNT:       int(raw_update_count),
            config.FLD_RUNLOG_OFFSET_REQUESTED:       int(offset_requested),
            config.FLD_RUNLOG_OFFSET_COMMITTED:       int(offset_committed),
            config.FLD_RUNLOG_GETUPDATES_HTTP_STATUS: str(getupdates_http_status),
            config.FLD_RUNLOG_POSSIBLE_GAP_DETECTED:  bool(possible_gap_detected),
            config.FLD_RUNLOG_HOTELS_ADDED:           int(hotels_added),
            config.FLD_RUNLOG_FOOD_ADDED:             int(food_added),
            config.FLD_RUNLOG_SCENIC_ADDED:           int(scenic_added),
            config.FLD_RUNLOG_SKIPPED:                int(skipped),
            config.FLD_RUNLOG_MESSAGES_FOUND:         int(messages_found),
        }
        if lowest_update_id_seen is not None:
            fields[config.FLD_RUNLOG_LOWEST_UPDATE_ID_SEEN]  = int(lowest_update_id_seen)
        if highest_update_id_seen is not None:
            fields[config.FLD_RUNLOG_HIGHEST_UPDATE_ID_SEEN] = int(highest_update_id_seen)

        self._post(config.TBL_RUNLOG, {"fields": fields})
