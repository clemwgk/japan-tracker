# Japan Travel Tracker v2

Robust, zero-cost pipeline that captures Japan hotel/food/scenic leads from a Telegram channel
and researches them into Airtable.

## Architecture

```
[Telegram channel "Japan Leads"]
        │  getUpdates (pull)
        ▼
[LOGGER — GitHub Actions cron, every 4h, pure Python]
   logger.py  →  telegram_client.py  →  airtable_store.py
   writes every raw update → Inbox table (status: pending|skipped)
   advances offset only after durable write; never loses a message once captured
        │
        ▼
[Inbox table (Airtable)] ← source of truth + forensics
        │  status=pending
        ▼
[PROCESSOR — Claude Code routine, daily 08:00 SGT]
   reads research_prompt.md instructions
   classifies → researches → dedup → writes Hotels/Scenic/Food
   marks Inbox rows processed|error; isolates per-row failures
        │
        ▼
[Hotels / Scenic / Food tables] + [RunLog audit] + [/japan-leads-health]
```

**There is no direct integration between GitHub Actions and Claude Code.**
The Airtable Inbox is the only interface — an async mailbox.

## Schema snapshot (built 2026-06-29)

| Table | ID |
|---|---|
| Inbox (new v2) | `tblPRUxYISDmhgvqK` |
| Hotels | `tblyu7XSAGEh3FvQH` |
| Scenic | `tbly48Lf4IeBwPA32` |
| Food | `tblz0I9GtyRRifH28` |
| Config | `tblVbaW0sbYd69aDv` |
| RunLog | `tblP4IQ6iz6ZOi8OX` |

All field and record IDs are in `config.py`.

## Running

### GitHub Actions (production)
Logger runs automatically on `schedule: "17 */4 * * *"` once `LOGGER_ENABLED=true` is set.
Manual trigger: Actions → "Japan Tracker — Logger" → Run workflow.

### Locally (debugging)
```bash
export TELEGRAM_BOT_TOKEN=...
export AIRTABLE_PAT=...
python logger.py
```

### Tests
```bash
pip install requests pytest
pytest tests/ -v
```

## Secrets (never in code)

| Secret | Where |
|---|---|
| `TELEGRAM_BOT_TOKEN` | GitHub repo encrypted secrets |
| `AIRTABLE_PAT` | GitHub repo encrypted secrets |

## Cutover checklist

See `v2-manual-setup.md` (M5) and `v2-build-plan.md` §5 Phase 6.

1. Processor switched to Inbox-only (no `getUpdates`)
2. `telegram_last_logged_update_id` seeded to last consumed v1 offset
3. No other Telegram consumer active
4. Controlled dispatch test passes
5. Human sets `LOGGER_ENABLED=true` in repo Variables
6. One real scheduled run confirmed
