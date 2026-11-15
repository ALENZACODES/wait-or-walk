# Wait or Walk

The subway just stopped. Will it be two minutes or twenty? Paste a TTC subway alert and Wait or Walk shows how often comparable logged incidents delayed subway service 10 minutes or more, the reasons behind that number, and scheduled buses and streetcars a short walk away that head where you are going.

Live: https://alenzacodes.github.io/wait-or-walk/

Built by John Khan in Toronto, Ontario for SLAY HACKS 2026. Not affiliated with or endorsed by the Toronto Transit Commission (TTC).

## Worked example
Alert pasted on a weekday at 5:30 p.m., heading to Jane: *"Line 2 Bloor-Danforth: Delays at Kipling due to a person at track level."*
- **Read from the alert (tagged for checking):** Line 2, Kipling, person at track level.
- **The call:** 23%, moderate risk of a long delay. "Know your other route and check the alert again in a few minutes."
- **Drift correction:** 29% before recalibration, 23% after.
- **Behind it:** 563 logged delays with this cause, 270 of them 10 minutes or more; half were over in 9 minutes or less. The cause raises the odds; Kipling and the evening rush lower them.
- **Plan B, scheduled alternatives (may not be running right now):** 149 Etobicoke-Bloor, East towards Jane Station, from Kipling Station (10 m, about a 1 minute walk, accessible boarding listed); next scheduled 5:39, 6:07 and 6:35 p.m.; get off at Jane Station. Or 40 Junction-Dundas West east past the delay to Islington, then Line 2 (next 5:53, 6:17 and 6:42 p.m.).

## How it works

1. **Read the alert.** `logic.js` reads the alert with hand written rules, not a trained model: regular expressions for line names, keyword patterns for 14 causes checked in a fixed order with the most specific first ("person at track level" before "track"), and a search for the 71 station names plus a few older names such as Dundas for TMU. It pulls the line, the station and the cause out of the alert text (for example "Line 2: Delays at Kipling due to a person at track level"). Anything it reads is tagged "from alert, please check", and anything it cannot find is left empty, never carried over from before. If the alert is ambiguous, no number is shown until you choose: an alert that names more than one station asks which one, and Bloor-Yonge (or St George, Spadina or Sheppard-Yonge) without a line asks which line. A station that is not on the chosen line (Union on Line 2) also gives no number. Clearing the alert clears everything it filled in, and the number with it.
2. **Score it.** A logistic regression model, trained in Python with scikit-learn and run in the browser, scores five things an alert tells you: cause, station, line, time of day and weekend.
3. **Explain it.** Right under the risk band, the call card shows the drift correction (the forecast before and after recalibration). Below that: the number of logged delays behind the cause (with a warning under 100) and the factors that pushed the chance up or down most.
4. **Plan B: scheduled alternatives.** Not verified fastest routes; right above the list the page warns that a scheduled alternative might not be running now. From the TTC schedule (GTFS), every regular stop pattern (5% or more of a route direction's trips) of every bus, streetcar and LRT route, with the subway stations it passes within 300 metres in order. Line 5 Eglinton and Line 6 Finch West are listed as LRT. Each stop shows its distance and walking time (80 metres a minute, straight line, so 300 metres is about 4 minutes), the schedule's accessible boarding flag (`wheelchair_boarding`), and the next three scheduled departures for today, using the service calendar and calendar exceptions and the current Toronto time. Without a destination you see each nearby route by direction and the next subway station it reaches. With a destination you see routes that go from the delayed station to near it in the right direction, and otherwise routes that carry you past the delay to a station on the way, then the subway onward. Blue Night routes (300 to 399) are listed separately.

## What the number means

The TTC logs each incident with the minutes it delayed subway service. The number is the estimated chance that an incident like this one, logged with more than 0 minutes of delay, delayed service 10 minutes or more. It is not your own remaining wait. Records with 0 minutes of delay (30,515 on Lines 1, 2 and 4) are left out.

The risk bands are a plain language summary: under 15% low, 15% to 35% moderate, 35% and up high ("worth checking another route now").

## The model

- **Data:** TTC Subway Delay Data since 2025 (City of Toronto Open Data, refreshed Oct 26, 2026). The copy used here has 47,915 records from Jan 1, 2025 to Sep 30, 2026; I have not checked it against the TTC's internal logs. Kept: Lines 1, 2 and 4, delays over 0 minutes (16,548 delays). Target: 10 minutes or more.
- **Causes a rider can see:** the TTC's 124 delay codes are grouped into the 15 causes alerts actually say, such as "medical emergency", "person at track level" or "signal problem".
- **Drift:** long delays became rarer in 2026 (about 19% of delays in early 2025, about 12% in summer 2026). Each delay is weighted by age with a 180 day half life, and the output is recalibrated (Platt scaling).
- **One process, tested as shipped:** the base model is trained on everything before the last 91 days, Platt scaling is fitted on those 91 days, and that pair is shipped with no refit. The shipped model: base trained through Jul 1, 2026, recalibrated on Jul 2 to Sep 30, 2026.
- **Rare causes:** cause features get lighter shrinkage than station features, so a rare but serious cause such as a personal injury at track level is not pulled towards average.

## Honest results
Everything below is on three out of time evaluation periods not used for fitting (Jan to Mar, Apr to Jun and Jul to Sep 2026; 7,455 delays), each run with the exact process that ships, with 95% bootstrap intervals from 2,000 resamples.

**Forecasts run high:** 3 to 4 points in the bands above 30% (35% forecast against 31% actual, 59% against 55%), up to 3 points below that. Average forecast by period: 18% against 18%, 17% against 14%, 14% against 12%.

| Pooled | AUC (95% interval) | Log loss | Brier score | Calibration error |
|---|---|---|---|---|
| Wait or Walk | 0.751 (0.736 to 0.767) | 0.3628 (0.3507 to 0.3758) | 0.1103 | 1.8 points |
| Cause only rule | 0.727 (0.712 to 0.743) | 0.3723 (0.3605 to 0.3852) | 0.1130 | 1.9 points |
| First model | 0.753 (0.737 to 0.768) | 0.3630 (0.3513 to 0.3757) | 0.1103 | 2.4 points |

- **Against the cause only rule** (recent share of long delays for the cause, recalibrated the same way): AUC 0.024 better (0.016 to 0.032) and log loss 0.0095 better (0.0060 to 0.0127), both distinguishable. By period it is distinguishably better in the first two; in the latest period (0.769 against 0.760 AUC, 0.3154 against 0.3167 log loss) the difference is not distinguishable.
- **Against the first model** (same features, trained on all earlier data with equal weights and no recalibration): pooled AUC and log loss are not distinguishable (0.751 against 0.753; 0.3628 against 0.3630). Its AUC point estimate is a little lower in all three periods, distinguishably so only in the first (0.724 against 0.731). Recalibration costs a little ranking, because the base model cannot learn from the latest three months. Log loss: 0.4189 against 0.4151, then 0.3484 against 0.3472, then 0.3154 against 0.3217 (better, distinguishable, in the latest period).
- **Why this model ships:** ranking matches the first model within noise, calibration error is lower (1.8 against 2.4 points, distinguishable), and in the latest period it is distinguishably better on log loss and Brier score because it follows the 2026 drop in long delays. The cause alone gets most of the way; station, line, time and day add 0.024 AUC.

**Decision value** at the risk band cut offs, pooled:

| Flag at | Method | Share of 10+ minute delays flagged | False flag rate | Flagged that ran 10+ minutes |
|---|---|---|---|---|
| 15% | Wait or Walk | 74% | 37% | 25% |
| 15% | Cause only rule | 71% | 37% | 25% |
| 35% | Wait or Walk | 25% | 5% | 44% |
| 35% | Cause only rule | 14% | 2% | 51% |

**A decision simulation, not real savings.** Assumptions: waiting costs the logged delay minutes, capped at 60; switching costs a fixed 8, 12 or 15 extra minutes; a rider switches at 35% or more. Average minutes lost per incident: always wait 6.56; with an 8 minute switch, cause only 6.26 and Wait or Walk 6.18; at 12 minutes, 6.42 and 6.51; at 15 minutes, 6.55 and 6.76. Read honestly, there is no clear time saving: Wait or Walk is ahead only when switching is cheap, and the gaps are under a quarter of a minute either way.

An earlier version of this page reported 0.772 AUC from a calibration process that did not match what was shipped; these numbers replace it.

All numbers are in `data/metrics.json` (`folds` for each period, `evidence` for intervals, decision value and the simulation) and are rebuilt by the training script.

## Plan B journeys checked by hand

Five journeys were checked against the raw TTC schedule files, not the app's own data: one scheduled weekday morning trip each, with the boarding and alighting stops, times and distances. Full details: [docs/plan-b-checks.md](docs/plan-b-checks.md), made by `scripts/check_planb.py`. Each is also an automated test.

| Journey | Lines | What the app shows | Schedule check |
|---|---|---|---|
| Union to College | Line 1 | 97 Yonge, North towards Eglinton Station | Weekday trip, 7:32 to 7:45, 10 stops |
| Finch to Eglinton | Line 1 | 97 Yonge, South towards St Clair Station | Weekday trip, 7:52 to 8:30, 30 stops |
| Kipling to Jane | Line 2 | 149 Etobicoke-Bloor, East towards Jane Station | Weekday trip, 7:35 to 7:55, 12 stops |
| Main Street to Broadview | Line 2 | 62 Mortimer, West towards Broadview Station | Weekday trip, 7:31 to 7:53, 26 stops |
| Dundas West to Union | Line 2 to Line 1 | 504 King east past the delay, change to Line 1 at St Andrew | Weekday trip, 7:30 to 8:19 at St Andrew, 30 stops |

Screenshots of each: `docs/checks/`. These are schedule checks only. Wait or Walk has not been tested with riders.

## Setup

Needs Python 3.10 or newer and Node 18 or newer. The page itself is static: HTML, CSS and plain JavaScript, no build step.

```
git clone https://github.com/ALENZACODES/wait-or-walk
cd wait-or-walk
pip install pandas numpy scikit-learn
```

## Run locally

```
python3 -m http.server 8080
```

Then open http://localhost:8080/. The page needs a connection to load its data files. If they fail to load it says so and offers a retry.

## Data download

`scripts/train.py` downloads both open datasets from City of Toronto Open Data into a cache folder (default `/tmp/ttc`) on first run, then reuses them:

- TTC Subway Delay Data since 2025 (CSV)
- TTC Routes and Schedules (GTFS zip)

Both are under the Open Government Licence Toronto.

## Training

```
python3 scripts/train.py /tmp/ttc
python3 scripts/build_planb.py /tmp/ttc
python3 scripts/check_planb.py /tmp/ttc > docs/plan-b-checks.md
```

`train.py` writes `data/model.json`, `data/metrics.json` (evaluation periods, calibration bands, bootstrap intervals, decision value and the simulation) and `data/parity.json`. `build_planb.py` writes `data/planb.json` and `data/planb_times.json` (departure times and the service calendar). `check_planb.py` rewrites the hand check report from the raw schedule.

## Tests

```
node tests/test_logic.mjs
```

GitHub Actions runs this on every push. It covers:

- **Parity test:** the browser code gives the same probability as the Python model on 30 example inputs, within 0.0001. This is an implementation check, not an accuracy test.
- Cause ordering, risk bands, and alert reading.
- Ambiguous alerts: Bloor-Yonge with no line, two stations named, and a two line station with no line all give no number until a choice is made. Clearing the alert clears the derived fields and the number.
- Every example button gives a number, except the one meant to show the choice.
- The Toronto clock and the station data.
- Plan B direction and destination cases, including the five hand checked journeys.
- Station and line mismatch (Union on Line 2) gives no number.
- Line 5 Eglinton is LRT; trips that end at the station are not offered; the service calendar, next departures (including the hand checked 7:35 weekday 149) and walking time.
- Every evaluation period keeps base, recalibration and test periods in order; bootstrap intervals bracket their values; the published claims about which differences are distinguishable match the numbers.

A real browser check clicks every example button at 390 px and 1440 px, then runs the ambiguous alert flow, clearing, and the load error retry:

```
pip install playwright && python3 -m playwright install chromium
python3 tests/browser_check.py https://alenzacodes.github.io/wait-or-walk/
```

## Limits

An estimate, not a promise. Rare causes rest on few cases (fire or smoke: 94 delays; personal injury at track level: 34), and the page says so. Plan B uses straight line distance and the regular schedule, not live detours or shuttle buses. It has not been tested with riders. Data: City of Toronto Open Data under the Open Government Licence Toronto.

## What's next

- An optional "already lasted N minutes" input. The delay log gives total minutes but not when an alert went out, so this cannot be validated honestly yet.
- Accessibility beyond the schedule's stop flag: elevator outages and step free routes between stops.
- Live TTC alerts, live arrival times, streetcar delay data, and a test with riders.

## Licence

Code: MIT, copyright John Khan. See `LICENSE`. Data: City of Toronto Open Data, TTC Subway Delay Data since 2025 and TTC Routes and Schedules (GTFS, schedule dated Oct 20, 2026), both under the Open Government Licence Toronto (https://open.toronto.ca/open-data-licence/). Not affiliated with or endorsed by the TTC.

Built during SLAY HACKS (which began November 7, 2026); work started November 15, 2026, and the first commit is from 6:08 a.m. Toronto time that day.
