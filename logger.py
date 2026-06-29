"""
Japan Tracker v2 — Logger entrypoint (GitHub Actions, every 4h).
Pure Python, no LLM. Single responsibility: drain Telegram into the Inbox.
"""

import datetime
import os
import sys
import time
import traceback

import requests

import airtable_store
import config
import telegram_client

# GitHub Actions injects these; fall back to a local-run sentinel
_GH_SERVER  = os.environ.get("GITHUB_SERVER_URL", "")
_GH_REPO    = os.environ.get("GITHUB_REPOSITORY", "")
_GH_RUN_ID  = os.environ.get("GITHUB_RUN_ID", "")
RUN_ID = (
    f"{_GH_SERVER}/{_GH_REPO}/actions/runs/{_GH_RUN_ID}"
    if _GH_RUN_ID
    else f"local-{int(time.time())}"
)


def _now_sgt():
    tz = datetime.timezone(datetime.timedelta(hours=8))
    return datetime.datetime.now(tz).isoformat()


def _send_alert(token, channel_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": channel_id, "text": text},
            timeout=15,
        )
    except Exception:
        pass


def _log(step, **kv):
    parts = " ".join(f"{k}={v}" for k, v in kv.items())
    print(f"[{RUN_ID}] step={step} {parts}", flush=True)


def _check_processor_stalled(store, token, channel_id):
    """Alert if the processor looks stalled (Config or oldest Inbox pending)."""
    tz = datetime.timezone(datetime.timedelta(hours=8))
    now = datetime.datetime.now(tz)

    last_proc_str = store.get_config("last_successful_run")
    if last_proc_str:
        try:
            last_proc = datetime.datetime.fromisoformat(last_proc_str)
            age = (now - last_proc).total_seconds()
            if age > config.PROCESSOR_STALE_SECONDS:
                _send_alert(token, channel_id,
                    f"[logger] PROCESSOR STALLED\n"
                    f"last_successful_run={last_proc_str} ({age/3600:.1f}h ago)\n"
                    f"Component=processor Severity=WARN run_id={RUN_ID}\n"
                    f"Next: check the daily processor routine.")
        except ValueError:
            pass

    # Check oldest pending Inbox row
    try:
        rows = store.get_pending_inbox_rows(max_records=1)
        if rows:
            captured = rows[0].get("fields", {}).get(config.FLD_INBOX_CAPTURED_AT, "")
            if captured:
                cap_dt = datetime.datetime.fromisoformat(captured)
                age = (now - cap_dt).total_seconds()
                if age > config.INBOX_PENDING_STALE_SECONDS:
                    _send_alert(token, channel_id,
                        f"[logger] PROCESSOR STALLED (pending backlog)\n"
                        f"Oldest pending Inbox row: {captured} ({age/3600:.1f}h ago)\n"
                        f"Component=processor Severity=WARN run_id={RUN_ID}\n"
                        f"Next: check if the daily processor routine is running.")
    except Exception:
        pass  # watchdog failure must not crash the main path


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    pat   = os.environ["AIRTABLE_PAT"]
    store = airtable_store.AirtableStore(pat)

    step   = "init"
    result = None

    try:
        # ----------------------------------------------------------------
        # Step 1 — read last committed offset
        # ----------------------------------------------------------------
        step = "get_offset"
        _log(step)
        raw_offset = store.get_config("telegram_last_logged_update_id")

        if not raw_offset:
            # Not yet seeded — wait for cutover (Phase 6 step 4).
            _log(step, status="not_seeded")
            print(f"[{RUN_ID}] telegram_last_logged_update_id not seeded — "
                  "run cutover first. Exiting without consuming Telegram queue.")
            sys.exit(0)

        last_offset      = int(raw_offset)
        requested_offset = last_offset + 1
        channel_id       = store.get_config("telegram_channel_id") or config.TELEGRAM_CHANNEL_ID
        _log(step, last_offset=last_offset, requested_offset=requested_offset)

        # ----------------------------------------------------------------
        # Step 2 — fetch from Telegram (no durable side effects)
        # ----------------------------------------------------------------
        step = "fetch"
        _log(step)
        result = telegram_client.fetch(token, channel_id, requested_offset)

        if result["error"]:
            err_msg = result.get("message", "unknown")
            http_st = result.get("http_status", "")
            _log(step, error=True, http_status=http_st, message=err_msg[:200])

            store.write_runlog(
                run_type="logger", run_id=RUN_ID, run_timestamp=_now_sgt(),
                raw_update_count=0, offset_requested=requested_offset,
                offset_committed=last_offset,
                getupdates_http_status=str(http_st),
                possible_gap_detected=False, errors=1,
                error_detail=f"fetch: {err_msg}",
            )
            store.set_config("last_logger_run",    _now_sgt())
            store.set_config("last_logger_status", f"error: fetch {http_st}")
            _send_alert(token, channel_id,
                f"[logger] ERROR\nfetch failed: {err_msg[:200]}\n"
                f"Component=logger Severity=ERROR run_id={RUN_ID}\n"
                f"Next: check Actions run log at {RUN_ID}")
            sys.exit(1)

        updates         = result["updates"]
        raw_update_count= result["raw_update_count"]
        possible_gap    = result["possible_gap"]
        lowest          = result.get("lowest_update_id")
        highest         = result.get("highest_update_id")
        _log(step, raw_update_count=raw_update_count, possible_gap=possible_gap,
             lowest=lowest, highest=highest)

        # ----------------------------------------------------------------
        # Step 3 — dedup + write Inbox rows
        # ----------------------------------------------------------------
        step = "write_inbox"
        gap_row_id = None

        for upd in updates:
            uid = upd["update_id"]
            is_boundary = possible_gap and uid == lowest

            existing = store.find_inbox_by_update_id(uid)
            if existing:
                row_id = existing["id"]
                _log(step, update_id=uid, action="dedup_existing")
                if is_boundary:
                    store.update_inbox_row(row_id, possible_gap=True)
            else:
                status = "skipped" if upd.get("skip_reason") else "pending"
                row_id = store.create_inbox_row(
                    update_id=uid,
                    captured_at=_now_sgt(),
                    message_date=upd.get("date", ""),
                    text=upd.get("text", ""),
                    chat_id=upd.get("chat_id", ""),
                    raw_json=upd.get("raw_json", ""),
                    raw_truncated=upd.get("raw_truncated", False),
                    status=status,
                    skip_reason=upd.get("skip_reason"),
                    possible_gap=is_boundary,
                )
                _log(step, update_id=uid, status=status, rec_id=row_id)

            if is_boundary:
                gap_row_id = row_id

        # ----------------------------------------------------------------
        # Step 5 — advance offset (SP-H2: do NOT write on zero-update run)
        # ----------------------------------------------------------------
        step = "commit_offset"
        if raw_update_count > 0 and highest is not None:
            store.set_config("telegram_last_logged_update_id", str(highest))
            committed = highest
            _log(step, committed=committed)
        else:
            committed = last_offset
            _log(step, action="no_updates_offset_unchanged", committed=committed)

        # ----------------------------------------------------------------
        # Step 6 — RunLog + heartbeat
        # ----------------------------------------------------------------
        step = "runlog"
        store.write_runlog(
            run_type="logger", run_id=RUN_ID, run_timestamp=_now_sgt(),
            raw_update_count=raw_update_count,
            offset_requested=requested_offset, offset_committed=committed,
            lowest_update_id_seen=lowest, highest_update_id_seen=highest,
            getupdates_http_status=str(result.get("http_status", 200)),
            possible_gap_detected=possible_gap, errors=0,
        )
        store.set_config("last_logger_run",    _now_sgt())
        store.set_config("last_logger_status", "ok")
        _log(step, done=True)

        # ----------------------------------------------------------------
        # Step 7 — cross-watchdog (processor stalled?)
        # ----------------------------------------------------------------
        step = "watchdog"
        _check_processor_stalled(store, token, channel_id)

        # ----------------------------------------------------------------
        # Step 8 — alert policy: only on error / gap (silent on quiet run)
        # ----------------------------------------------------------------
        if possible_gap:
            _send_alert(token, channel_id,
                f"[logger] POSSIBLE UPDATE GAP\n"
                f"Requested offset={requested_offset}, lowest seen={lowest}. "
                f"Likely benign (filtered update types) — review if recurring.\n"
                f"Component=logger Severity=INFO run_id={RUN_ID}")

        _log("done", raw_update_count=raw_update_count, committed=committed)
        sys.exit(0)

    except Exception as exc:
        tb  = traceback.format_exc()[-2000:]
        detail = f"step={step} exc={type(exc).__name__}: {exc}\n{tb}"
        print(f"[{RUN_ID}] FATAL\n{detail}", file=sys.stderr)

        http_st = str(result.get("http_status", "")) if result else ""
        try:
            store.write_runlog(
                run_type="logger", run_id=RUN_ID, run_timestamp=_now_sgt(),
                errors=1, error_detail=detail,
                getupdates_http_status=http_st,
                offset_requested=0, offset_committed=0,
                raw_update_count=0, possible_gap_detected=False,
            )
            store.set_config("last_logger_run",    _now_sgt())
            store.set_config("last_logger_status", f"error: {step} {type(exc).__name__}")
        except Exception as write_exc:
            print(f"[{RUN_ID}] failed to write durable error record: {write_exc}",
                  file=sys.stderr)

        try:
            _send_alert(
                os.environ.get("TELEGRAM_BOT_TOKEN", ""),
                config.TELEGRAM_CHANNEL_ID,
                f"[logger] FATAL ERROR\nstep={step} exc={type(exc).__name__}: {str(exc)[:200]}\n"
                f"Component=logger Severity=ERROR run_id={RUN_ID}\n"
                f"Next: check Actions run log at {RUN_ID}",
            )
        except Exception:
            pass

        sys.exit(3)


if __name__ == "__main__":
    main()
