# Freeze for judging

The model, the wait or switch rule (with the live safety gate) and the alert parser are frozen at the tag `slay-hacks-submission`, which is the code judged. The parser tag `parser-freeze-r11` points at the first frozen commit (`0fb2fe8`); the parser has not changed since.

- Frozen files and their hashes: `data/freeze.json` (`logic.js`, `data/model.json`, `data/policy.json`, `data/decision_checks.json`).
- `scripts/freeze_check.mjs` runs in the tests and fails if any of them changes.
- The automated "Copy TTC subway alerts" commits change only data files (`data/live_alerts.json`, `data/alert_history.json`, `data/access_alerts.json`, `data/alert_forecasts.jsonl`, `data/parser_fresh.json`), never the frozen files.
- Parser freeze time: `frozenAt` in `data/freeze.json` (November 15, 2026, 11:02 p.m. Toronto time). Alerts first seen after it are the fresh parser test set (`data/parser_fresh.json`, `scripts/parser_fresh.mjs`, labels in `data/alerts_fresh_labels.json`).

## Changes after the freeze
Any change to a frozen file after the tag must be a bug fix, listed here with the date, the reason and the new hashes.

### November 16, 2026: live check, early bus (bug fix)
- **File:** `logic.js`, function `liveCheck` only. The parser (`readAlert`), the model maths and the wait or switch rule are unchanged; the diff touches only `liveCheck` and its comment.
- **Bug (found in review):** if the timetabled bus was 6 minutes away, you needed 5 to reach it, and the feed predicted it at 4, the old code dropped that prediction as unreachable, took the next bus at 16 and reported a bus 10 minutes late. That bus is early, not late. If every prediction was unreachable, the old code returned nothing, so the page said nothing.
- **Fix:** the prediction nearest the timetabled time is taken as that bus (a tie goes to the earlier one). If it is earlier than you could reach the stop, the state is `early`; if the first bus you could reach is 5 or more minutes after the timetabled time, `late`; otherwise `agrees`. Unit tests cover early, unreachable only, early but reachable, a tie, cancelled or short turned, a sparse list and unreadable minutes; the browser check covers the early case.
- **Effect on the verdict:** none. The verdict is still worked out from the timetable; the live check only warns.
- **Hashes:** `logic.js` from `caa553000196416a569f38b2592a4a1882eb75543a71129fc090bc4747801601` to `6e624931957ba95b7309a39de36b0ed44c45d888896a27ad7b13673046cea1da` (recorded in `data/freeze.json` under `changes`). The other three frozen files are unchanged.
- **Tag:** `slay-hacks-submission` was moved to the commit with this fix after its checks passed. The first tagged commit, `0fb2fe8`, keeps the tag `slay-hacks-submission-r11`. `parser-freeze-r11` stays on `0fb2fe8`, since the parser did not change; the fresh parser test set still starts at `frozenAt`.

### November 16, 2026: round 13, tag move only (no frozen file changed)
- **Frozen files:** `logic.js`, `data/model.json`, `data/policy.json` and `data/decision_checks.json` are byte for byte the same as at `543f06f`; `scripts/freeze_check.mjs` passes with no new entry under `changes`.
- **What changed outside the freeze:** the page shows the all incidents view beside every shipped chance, read from a new unfrozen lookup table (`data/all_incidents.json`, written by `scripts/all_incidents_table.py`) that the verdict never reads; wording (the live check says matching by time does not confirm it is the same vehicle, and switch saving figures say they are simulated); a shorter DEVPOST; a self restarting relay for the alerts copy (`.github/workflows/alerts-chain.yml`).
- **Tag:** `slay-hacks-submission` was moved to the round 13 commit after its checks passed. `543f06f` keeps the tag `slay-hacks-submission-r12`.

### November 16, 2026: round 14, tag move only (no frozen file changed)
- **Frozen files:** `logic.js`, `data/model.json`, `data/policy.json` and `data/decision_checks.json` are byte for byte the same as at `e2e8de1`; `scripts/freeze_check.mjs` passes with no new entry under `changes`.
- **What changed outside the freeze:** the alerts copy writes a last checked time on every successful check; the page uses that time and also asks the relay's Actions runs; a short watchdog restarts the relay if the chain has stopped; when the verdict says switch, the card states that the call uses the first chance and timetable Plan B times, and for fire or smoke it states the 1,478 of 1,572 figure; the write ups reconcile the private prototype with the public repo dates, report measured Actions run counts, and shorten DEVPOST; step free routing was considered and not added.
- **Tag:** `slay-hacks-submission` is moved to the round 14 commit after its checks pass. `e2e8de1` keeps the tag `slay-hacks-submission-r13`.
