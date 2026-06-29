"""Japan Tracker v2 — stable field/table/record IDs and thresholds. No secrets."""

BASE_ID = "appORHKmWGR5RhyoK"

# --- Table IDs ---
TBL_HOTELS  = "tblyu7XSAGEh3FvQH"
TBL_SCENIC  = "tbly48Lf4IeBwPA32"
TBL_FOOD    = "tblz0I9GtyRRifH28"
TBL_CONFIG  = "tblVbaW0sbYd69aDv"
TBL_RUNLOG  = "tblP4IQ6iz6ZOi8OX"
TBL_INBOX   = "tblPRUxYISDmhgvqK"  # created v2-build-plan Phase 1

# --- Config field IDs ---
FLD_CONFIG_KEY   = "fldHcMjCHYU7iPbbi"
FLD_CONFIG_VALUE = "fldJaTcIrw3Re2QWZ"

# Config record IDs for direct PATCH (avoids a search round-trip per write)
CONFIG_RECORD_IDS = {
    "telegram_last_logged_update_id": "recl5fv8GXRWUpKGL",
    "last_logger_run":                "recJ6Req4S6OJQnal",
    "last_logger_status":             "recXFy8zeCeEDW1Z6",
    "last_successful_run":            "recOChHVKU5wAwUya",
    "last_run_status":                "recaXPYYl7nCnD5Wk",
}

# --- Inbox field IDs (all created 2026-06-29) ---
FLD_INBOX_UPDATE_ID       = "fld4Zf5PDi40uUb6n"  # primary, number
FLD_INBOX_CAPTURED_AT     = "fld2D1YecnHpPA01a"
FLD_INBOX_MESSAGE_DATE    = "fldj5YavSNKw9Xaik"
FLD_INBOX_TEXT            = "fldJr3oTOeuVBbquD"
FLD_INBOX_CHAT_ID         = "fldgS9Uyv9au2VdeC"
FLD_INBOX_RAW_JSON        = "fldRXLW2BIpZxqgd6"
FLD_INBOX_RAW_TRUNCATED   = "fld0iW5pKzjDS18h1"
FLD_INBOX_STATUS          = "fldSfth3dedH5HwZ5"   # pending|processing|processed|skipped|error
FLD_INBOX_SKIP_REASON     = "flddtodZDCqtaoHjo"
FLD_INBOX_TARGET_TABLE    = "fldU9kwAfUWPGJMNX"
FLD_INBOX_TARGET_RECORD_ID= "fld6y5D03Ws5JLetV"
FLD_INBOX_RETRY_COUNT     = "fldAKxx9WHc0F3FUV"
FLD_INBOX_CLAIMED_AT      = "fldE3GPRAloCOnZJe"
FLD_INBOX_CLAIM_RUN_ID    = "fldlm0Kv9Kf8Aop3b"
FLD_INBOX_PROCESSED_AT    = "fld2aqH4UkEp9Le2z"
FLD_INBOX_POSSIBLE_GAP    = "fldXEjlZTGI6Wpt5Z"
FLD_INBOX_ERROR_DETAIL    = "fldnuM1ut0JCkduCF"

# --- RunLog field IDs (existing 8) ---
FLD_RUNLOG_RUN_TIMESTAMP  = "fldbkZZ0fHDOzyLjO"
FLD_RUNLOG_MESSAGES_FOUND = "fldtVnteXcjSJ4Ac3"
FLD_RUNLOG_HOTELS_ADDED   = "fldqsF5D3m8JGPHyO"
FLD_RUNLOG_FOOD_ADDED     = "fldpx7DJKAZNc7Qzp"
FLD_RUNLOG_SCENIC_ADDED   = "fld8TjurzC7vGuEo5"
FLD_RUNLOG_SKIPPED        = "fld87ns33KLEoGVfr"
FLD_RUNLOG_ERRORS         = "fld53P5ggm15PWrxk"
FLD_RUNLOG_ERROR_DETAIL   = "fldgCoHNPk3LzthRb"

# --- RunLog field IDs (new 9, created 2026-06-29) ---
FLD_RUNLOG_RUN_TYPE              = "fldi41f88tHBsPj2J"  # logger|processor
FLD_RUNLOG_OFFSET_REQUESTED      = "fldimGd4TAqx80vzo"
FLD_RUNLOG_OFFSET_COMMITTED      = "fldEagn70J0JoUWaf"
FLD_RUNLOG_RAW_UPDATE_COUNT      = "fldDO0o9wwyrY3vi0"
FLD_RUNLOG_LOWEST_UPDATE_ID_SEEN = "fldGEfn5kjS7qvqw6"
FLD_RUNLOG_HIGHEST_UPDATE_ID_SEEN= "fldnz0t10mon270lQ"
FLD_RUNLOG_GETUPDATES_HTTP_STATUS= "fldMJgKXwGFEJhMT7"
FLD_RUNLOG_POSSIBLE_GAP_DETECTED = "fldGxeb3G2VlRZfMu"
FLD_RUNLOG_RUN_ID                = "flddHsvJH9kgQt1PQ"

# --- Runtime constants ---
TELEGRAM_CHANNEL_ID = "-1003985188435"

# Texts shorter than this are skipped as text_too_short
MIN_TEXT_LENGTH = 10

# raw_json truncation ceiling (chars); Airtable's cell limit is 100k
RAW_JSON_MAX_CHARS = 90_000

# Watchdog thresholds
LOGGER_STALE_SECONDS    = 9 * 3600   # alert if logger hasn't run in 9h
PROCESSOR_STALE_SECONDS = 48 * 3600  # alert if processor hasn't succeeded in 48h
INBOX_PENDING_STALE_SECONDS = 36 * 3600  # alert if oldest pending > 36h

# Claim recovery: reclaim processing rows older than this
STALE_CLAIM_SECONDS = 2 * 3600
