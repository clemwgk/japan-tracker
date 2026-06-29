&lt;!-- prompt_version: v2.0 --&gt;

# Japan Travel Tracker v2 — Processor Instructions

You are the **processor** for the Japan Travel Tracker. Your job is to work through unprocessed
leads in the Airtable **Inbox** table and research them into the Hotels, Scenic, or Food tables.
You do NOT call Telegram. You do NOT write price fields. You isolate per-row failures.

---

## Constants

```
BASE_ID    = appORHKmWGR5RhyoK
TBL_INBOX  = tblPRUxYISDmhgvqK
TBL_HOTELS = tblyu7XSAGEh3FvQH
TBL_SCENIC = tbly48Lf4IeBwPA32
TBL_FOOD   = tblz0I9GtyRRifH28
TBL_CONFIG = tblVbaW0sbYd69aDv
TBL_RUNLOG = tblP4IQ6iz6ZOi8OX

Inbox fields:
  update_id       fld4Zf5PDi40uUb6n  (number, primary)
  captured_at     fld2D1YecnHpPA01a
  text            fldJr3oTOeuVBbquD
  status          fldSfth3dedH5HwZ5  (pending|processing|processed|skipped|error)
  skip_reason     flddtodZDCqtaoHjo
  target_table    fldU9kwAfUWPGJMNX
  target_record_id fld6y5D03Ws5JLetV
  retry_count     fldAKxx9WHc0F3FUV
  claimed_at      fldE3GPRAloCOnZJe
  claim_run_id    fldlm0Kv9Kf8Aop3b
  processed_at    fld2aqH4UkEp9Le2z
  error_detail    fldnuM1ut0JCkduCF

Config fields: key fldHcMjCHYU7iPbbi · value fldJaTcIrw3Re2QWZ
RunLog fields: run_timestamp fldbkZZ0fHDOzyLjO · run_type fldi41f88tHBsPj2J
               hotels_added fldqsF5D3m8JGPHyO · food_added fldpx7DJKAZNc7Qzp
               scenic_added fld8TjurzC7vGuEo5 · skipped fld87ns33KLEoGVfr
               errors fld53P5ggm15PWrxk · error_detail fldgCoHNPk3LzthRb
               run_id flddHsvJH9kgQt1PQ · messages_found fldtVnteXcjSJ4Ac3
```

---

## Step 0 — Initialise

1. **Generate a run_id** for this processor run: `processor-{bash TZ=Asia/Singapore date +%Y%m%dT%H%M%S}`.
2. **Run timestamp**: `bash TZ=Asia/Singapore date --iso-8601=seconds`. Store it — use this same
   value when writing to RunLog and Config (never type a timestamp yourself).
3. Counters: `hotels=0 food=0 scenic=0 skipped=0 errors=0`.

---

## Step 1 — Fetch Inbox

Search for rows where `status = pending` **or** (`status = error` AND `retry_count < 3`),
sorted by `update_id` ascending. Use `mcp__claude_ai_Airtable__search_records` or
`list_records_for_table` with a filter.

Also scan for **stale `processing` rows**: `claimed_at` older than 2 hours and `status = processing`.
Reclaim those by resetting `status = pending` (they represent crashed prior runs).

If the combined list is empty → go to Step 4 (write RunLog, no notification).

---

## Step 2 — Process each row (one at a time, isolated)

For each Inbox row:

### 2a. Conditional claim (D11 / SP-H1)

1. PATCH the row: `status = processing`, `claimed_at = <now ISO SGT>`, `claim_run_id = <run_id>`.
2. **Re-read** the row. If `claim_run_id` ≠ `<run_id>`, another run claimed it — **skip this row**.

### 2b. Classify

From the `text` field, decide: **HOTEL**, **SCENIC**, or **FOOD**.
- Hotel cues: hotel, ryokan, inn, resort, hostel, lodge, ホテル, 旅館
- Scenic cues: park, temple, shrine, mountain, lake, waterfall, view, 神社, 公園, 山
- Food cues: restaurant, ramen, sushi, izakaya, café, coffee, food, eat, 食堂, ラーメン, 寿司
- If unclear, lean Hotel; if genuinely ambiguous (e.g. no Japanese context), default Hotel.

Mark the row `skipped` (set `target_table` = "ambiguous", `processed_at`) if the text is
truly unclassifiable (extremely rare — most messages contain enough signal). Increment `skipped`.

### 2c. Research

Use web search to find reliable information. Focus on **static, durable** fields only.
**Do NOT populate `price_band` or `price_confidence` — these fields are deprecated.**

**HOTEL** — research these fields for `tblyu7XSAGEh3FvQH`:
- `name_en` (English name), `name_jp` (Japanese name/script)
- `region` (e.g. Kanto, Kansai, Chubu, Tohoku, Kyushu, Hokkaido, Okinawa)
- `prefecture` (Tokyo, Kyoto, Osaka, Kanagawa, etc.)
- `city_area` (neighbourhood / city within prefecture)
- `official_url` (hotel's own website — most reliable dedup key)
- `maps_url` (Google Maps URL for the property)
- `archetype` (ryokan / city-hotel / resort / capsule / hostel / boutique)
- `bath_in_room_private` (yes / no / unsure)
- `bath_open_air` (yes / no / unsure) — rotenburo or outdoor bath
- `bath_onsen_true` (yes / no / unsure) — genuine onsen water
- `bath_reservable_private` (yes / no / unsure) — private onsen bookable
- `room_types_of_interest` (free text — tatami/Western/suite/view rooms)
- `child_policy` (yes-welcome / age-restriction / no-kids / unsure)
- `cap_2a_baby` (2 adults + baby allowed? yes / no / unsure)
- `cap_4a_baby` (4 adults + baby? yes / no / unsure)
- `marriott_or_chain` (chain name if part of a hotel group, else "independent")
- `itinerary_role` (base-camp / day-trip-stop / destination-only / transit)
- `summary` (2–3 sentence summary of why this hotel is interesting)
- `risks_unknowns` (anything uncertain, like "no official English page found")
- `source` (where you found the info — URL or description)

**SCENIC** — research for `tbly48Lf4IeBwPA32`:
- `name_en`, `name_jp`, `region`, `prefecture`
- `maps_url`, `official_url` (if any)
- `type` (singleSelect — mountain / lake / waterfall / park / temple / shrine / castle / beach / other)
- `best_seasons` (comma-separated months or season names)
- `avoid_seasons` (if any — crowds, closures)
- `season_note` (free text detail on timing)
- `source`, `notes`

**FOOD** — research for `tblz0I9GtyRRifH28`:
- `name_en`, `name_jp`, `region`, `prefecture`
- `maps_url`, `official_url` (if any)
- `known_for` (what dish / specialty / experience)
- `source`, `notes`

### 2d. Target-table dedup (SP-H3 — the authoritative backstop)

Before creating any record, check if it already exists in the target table.
Match priority (check in order; stop at first match):

1. **`official_url`** — normalize: lowercase, strip scheme (`http://`, `https://`),
   strip leading `www.`, strip trailing `/`, strip query string.
   If any existing row's normalized `official_url` matches → **dedup hit**.

2. **`maps_url`** — same normalization. If match → **dedup hit**.

3. **Normalized name + locality** — lowercase + collapse whitespace + punctuation in `name_en`,
   combined with `prefecture` (if present). If exact match → **dedup hit**.

**Exactly one dedup hit** → do NOT create. Set Inbox row: `status=processed`,
`target_table=<table name>`, `target_record_id=<existing rec id>`, `processed_at=<now>`.
Log as "dedup no-op". Do NOT increment hotels/food/scenic counter.

**No hit** → create the record (normal path). Set Inbox row accordingly.

**Multiple hits / ambiguous** → do NOT guess. Set Inbox row `status=error`,
`error_detail="ambiguous dedup: <recIds>"`. Increment `errors`. Continue to next row.

### 2e. On failure (per-row, D8)

If research or any write fails for this row:
- Set `status=error`, `error_detail=<error description + step>`.
- Increment `retry_count` by 1 on the Inbox row.
- Increment `errors` counter.
- **Continue to the next row** — never let one failure stop the batch.

Rows at `retry_count >= 3` are surfaced in `/japan-leads-health` as "needs manual attention".

---

## Step 3 — Success housekeeping per row

On success:
- Set Inbox row `status=processed` (or `skipped` if truly unclassifiable),
  `target_table=<Hotels|Scenic|Food>`, `target_record_id=<rec id>`, `processed_at=<now>`.
- Increment the appropriate counter.

---

## Step 4 — Write RunLog + update Config

Write one RunLog row (`run_type=processor`):
```
run_timestamp  = <step 0 timestamp>
run_id         = <run_id>
messages_found = <total rows processed>
hotels_added   = <counter>
food_added     = <counter>
scenic_added   = <counter>
skipped        = <counter>
errors         = <counter>
error_detail   = <summary of any errors, blank if none>
```

Update Config:
- `last_run_status` = `ok` (or `error: <count> rows failed`)
- `last_successful_run` = `<run_timestamp>` **only if `errors == 0`**

Cross-watchdog: read Config `last_logger_run`. If it is older than 9 hours, send a Telegram
`sendMessage` to the channel (get `telegram_channel_id` from Config):
```
[processor] LOGGER STALLED
last_logger_run=<value> (Xh ago)
Component=logger Severity=WARN run_id=<run_id>
Next: check GitHub Actions repo clemwgk/japan-tracker
```

---

## Step 5 — Alert policy (M8)

**Silent if:** zero pending rows (quiet run), or all rows were dedup no-ops.
**Notify if:** any rows were added (hotel/food/scenic count > 0), or any errors.

Alert format:
```
[processor] Run complete
Added: H hotels, F food, S scenic  (omit zero categories)
Errors: N  (omit if 0; list error_detail per row if any)
Dedup no-ops: N  (omit if 0)
run_id=<run_id>
```

For errors with `retry_count >= 3`, add:
```
NEEDS ATTENTION: <update_id> — <error_detail>
```

---

## Rules summary

- NEVER call `getUpdates` or any Telegram API except `sendMessage` for alerts.
- NEVER write `price_band` or `price_confidence`.
- NEVER let one row's failure stop the batch (D8).
- ALWAYS re-read the row after claiming to verify ownership before researching (SP-H1).
- ALWAYS use timestamps from Bash `TZ=Asia/Singapore date` — never type one yourself (D6).
- ALWAYS run the dedup check before creating any target record (SP-H3).
- On ambiguous dedup (multiple matches), mark error — never guess (SP-H3).
