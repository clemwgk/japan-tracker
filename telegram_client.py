"""
Japan Tracker v2 — Telegram capture layer.

Pure functions (no I/O): parse_updates, classify_skip, compute_gap, summarize.
One thin network function: fetch() — single HTTP request, no durable side effects.
"""

import datetime
import json
import re

import requests

import config

# Matches any Unicode word character (letter, digit, underscore)
_WORD_RE = re.compile(r"\w", re.UNICODE)
# Matches "test" as a whole word (case-insensitive)
_TEST_RE = re.compile(r"\btest\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Pure functions (unit-tested, no I/O)
# ---------------------------------------------------------------------------

def parse_updates(raw_response):
    """
    Parse a raw Telegram getUpdates response dict into a list of update dicts.

    Each update dict:
      update_id, date (ISO Asia/Singapore), text (or ""), chat_id (str),
      raw_json (str), raw_truncated (bool), service (bool), skip_reason (str|None)
    """
    updates = []
    tz_sgt = datetime.timezone(datetime.timedelta(hours=8))

    for item in raw_response.get("result", []):
        update_id = item["update_id"]
        post = item.get("channel_post", {})

        # Detect service messages (no text/caption, has service fields)
        service_fields = {
            "pinned_message", "new_chat_members", "left_chat_member",
            "new_chat_title", "new_chat_photo", "delete_chat_photo",
            "group_chat_created", "channel_chat_created",
        }
        is_service = any(f in post for f in service_fields)

        text = post.get("text") or post.get("caption") or ""

        raw_str = json.dumps(item, ensure_ascii=False)
        raw_truncated = len(raw_str) > config.RAW_JSON_MAX_CHARS
        if raw_truncated:
            raw_str = raw_str[:config.RAW_JSON_MAX_CHARS]

        ts = post.get("date")
        if ts:
            date_iso = datetime.datetime.fromtimestamp(ts, tz=tz_sgt).isoformat()
        else:
            date_iso = ""

        chat_id = str(post.get("chat", {}).get("id", ""))

        upd = {
            "update_id":     update_id,
            "date":          date_iso,
            "text":          text,
            "chat_id":       chat_id,
            "raw_json":      raw_str,
            "raw_truncated": raw_truncated,
            "service":       is_service,
        }
        upd["skip_reason"] = classify_skip(upd)
        updates.append(upd)

    updates.sort(key=lambda u: u["update_id"])
    return updates


def classify_skip(update):
    """
    Return the skip_reason string if this update should not be researched,
    or None if it should become a pending lead.

    Order matters: service > no_text > text_too_short > emoji_only > test_message.
    """
    if update.get("service"):
        return "service_message"

    text = update.get("text") or ""
    if not text.strip():
        return "no_text"

    if len(text.strip()) < config.MIN_TEXT_LENGTH:
        return "text_too_short"

    if not _WORD_RE.search(text):
        return "emoji_only"

    if _TEST_RE.search(text):
        return "test_message"

    return None


def compute_gap(updates, requested_offset):
    """
    Return True if there is a *possible* gap between requested_offset and the
    lowest update_id we actually received. This is a signal, not proof — other
    update types consume IDs we never see when using allowed_updates filtering.
    """
    if not updates:
        return False
    lowest = min(u["update_id"] for u in updates)
    return lowest > requested_offset


def summarize(updates):
    """Return {lowest, highest, count} for a list of parsed updates."""
    if not updates:
        return {"lowest": None, "highest": None, "count": 0}
    ids = [u["update_id"] for u in updates]
    return {"lowest": min(ids), "highest": max(ids), "count": len(ids)}


# ---------------------------------------------------------------------------
# Thin network function (one HTTP request, no durable side effects)
# ---------------------------------------------------------------------------

def fetch(token, channel_id, offset):
    """
    Fetch pending updates from Telegram for the given channel.

    Makes exactly ONE getUpdates request (30s timeout).
    Does NOT advance the offset or write any record.

    Returns a dict matching the output contract in v2-build-plan §5 Phase 2.
    On any failure returns {"error": True, "message": ..., "http_status": ...}.
    """
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={
                "offset": offset,
                "allowed_updates": json.dumps(["channel_post"]),
                "timeout": 0,
            },
            timeout=30,
        )
        http_status = r.status_code

        if http_status != 200:
            return {
                "error": True,
                "http_status": http_status,
                "message": f"Telegram returned HTTP {http_status}: {r.text[:300]}",
            }

        body = r.json()
        if not body.get("ok"):
            return {
                "error": True,
                "http_status": http_status,
                "message": f"Telegram ok=false: {body.get('description', body)[:300]}",
            }

        updates = parse_updates(body)
        s = summarize(updates)
        gap = compute_gap(updates, requested_offset=offset)

        return {
            "error": False,
            "http_status": http_status,
            "updates": updates,
            "lowest_update_id": s["lowest"],
            "highest_update_id": s["highest"],
            "raw_update_count": s["count"],
            "possible_gap": gap,
        }

    except requests.RequestException as exc:
        return {
            "error": True,
            "http_status": None,
            "message": f"RequestException: {exc}",
        }
