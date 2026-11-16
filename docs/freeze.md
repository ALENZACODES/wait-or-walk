# Freeze for judging

The model, the wait or switch rule (with the live safety gate) and the alert parser are frozen at the tag `slay-hacks-submission`, which is the code judged. The parser tag `parser-freeze-r11` points at the same commit.

- Frozen files and their hashes: `data/freeze.json` (`logic.js`, `data/model.json`, `data/policy.json`, `data/decision_checks.json`).
- `scripts/freeze_check.mjs` runs in the tests and fails if any of them changes.
- The automated "Copy TTC subway alerts" commits change only data files (`data/live_alerts.json`, `data/alert_history.json`, `data/access_alerts.json`, `data/alert_forecasts.jsonl`, `data/parser_fresh.json`), never the frozen files.
- Parser freeze time: `frozenAt` in `data/freeze.json` (November 15, 2026, 11:02 p.m. Toronto time). Alerts first seen after it are the fresh parser test set (`data/parser_fresh.json`, `scripts/parser_fresh.mjs`, labels in `data/alerts_fresh_labels.json`).

## Changes after the freeze
Any change to a frozen file after the tag must be a bug fix, listed here with the date, the reason and the new hashes. None so far.
