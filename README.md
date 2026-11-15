# Wait or Walk

The subway just stopped. Will it be two minutes or twenty? Paste a TTC subway alert and Wait or Walk shows how often comparable logged incidents delayed subway service 10 minutes or more, the reasons behind that number, and scheduled buses and streetcars a short walk away that head where you are going.

Live: https://alenzacodes.github.io/wait-or-walk/

Built by John Khan in Toronto, Ontario for SLAY HACKS 2026.

## How it works

1. **Read the alert.** `logic.js` pulls the line, the station and the cause out of the alert text (for example "Line 2: Delays at Kipling due to a person at track level"). Anything it reads is tagged "from alert, please check", and anything it cannot find is left empty, never carried over from before. If the alert is ambiguous, no number is shown until you choose: an alert that names more than one station asks which one, and Bloor-Yonge (or St George, Spadina or Sheppard-Yonge) without a line asks which line. Clearing the alert clears everything it filled in, and the number with it.
2. **Score it.** A logistic regression model, trained in Python with scikit-learn and run in the browser, scores five things an alert tells you: cause, station, line, time of day and weekend.
3. **Explain it.** Right under the risk band, the call card shows the drift correction (the forecast before and after recalibration). Below that: the number of logged delays behind the cause (with a warning under 100) and the factors that pushed the chance up or down most.
4. **Plan B: scheduled alternatives.** These are scheduled alternatives, not verified fastest routes. From the TTC schedule (GTFS), every regular stop pattern of every bus and streetcar route, with the subway stations it passes within 300 metres in order. Without a destination you see each nearby route by direction and the next subway station it reaches. Pick where you are headed and you see the routes that go from the delayed station to near your destination in the right direction, and otherwise the routes that carry you past the delay to a station on the way, then the subway onward. Blue Night routes are listed separately.

## What the number means

The TTC logs each incident with the minutes it delayed subway service. The number is the estimated chance that an incident like this one, logged with more than 0 minutes of delay, delayed service 10 minutes or more. It is not your own remaining wait. Records with 0 minutes of delay (30,515 on Lines 1, 2 and 4) are left out.

The risk bands are a plain language summary: under 15% low, 15% to 35% moderate, 35% and up high ("worth checking another route now").

## The model

- **Data:** TTC Subway Delay Data since 2025 (City of Toronto Open Data, refreshed Oct 26, 2026): every logged subway delay from Jan 1, 2025 to Sep 30, 2026. Kept: Lines 1, 2 and 4, delays over 0 minutes (16,548 delays). Target: 10 minutes or more.
- **Causes a rider can see:** the TTC's 124 delay codes are grouped into the 15 causes alerts actually say, such as "medical emergency", "person at track level" or "signal problem".
- **Drift:** long delays became rarer in 2026 (about 19% of delays in early 2025, about 12% in summer 2026). Each delay is weighted by age with a 180 day half life, and the output is recalibrated (Platt scaling).
- **One process, tested as shipped:** the base model is trained on everything before the last 91 days, Platt scaling is fitted on those 91 days, and that pair is shipped with no refit. The shipped model: base trained through Jul 1, 2026, recalibrated on Jul 2 to Sep 30, 2026.
- **Rare causes:** cause features get lighter shrinkage than station features, so a rare but serious cause such as a personal injury at track level is not pulled towards average.

## Honest results

**Forecasts run high.** Pooled over the three evaluation periods, forecasts sat above what happened in every band: 3 to 4 points in the bands above 30% (35% forecast vs 31% actual, 59% vs 55%) and up to 3 points below that. By period, the average forecast was 18% vs 18% actual, 17% vs 14%, and 14% vs 12%.

**Ranking.** Wait or Walk beats the cause only rule on AUC and log loss in all three periods, and that is the only baseline it beats. It ranks a little below the first model on AUC in all three (0.724 vs 0.731, 0.758 vs 0.760, 0.769 vs 0.770): recalibrating on the latest three months costs a little ranking, because the base model cannot learn from those months. On log loss it is about level with the first model (better in the latest period, slightly worse in the two earlier ones).

**How it was tested.** Out of time evaluation periods not used for fitting. Each period runs the shipped process exactly: the base model stops 91 days before the period, Platt scaling uses those 91 days, and the period itself is never used for fitting. The cause only rule is recalibrated the same way.

| Evaluation period | Method | AUC | Log loss | Average forecast vs actual |
|---|---|---|---|---|
| Jan to Mar 2026 (2,576 delays) | Cause only rule | 0.685 | 0.4340 | 18% vs 18% |
| | First model (no recency, no recalibration) | 0.731 | 0.4151 | 18% vs 18% |
| | **Wait or Walk** | **0.724** | **0.4189** | 18% vs 18% |
| Apr to Jun 2026 (2,631 delays) | Cause only rule | 0.729 | 0.3593 | 17% vs 14% |
| | First model | 0.760 | 0.3472 | 17% vs 14% |
| | **Wait or Walk** | **0.758** | **0.3484** | 17% vs 14% |
| Jul to Sep 2026 (2,248 delays) | Cause only rule | 0.760 | 0.3167 | 13% vs 12% |
| | First model | 0.770 | 0.3217 | 16% vs 12% |
| | **Wait or Walk** | **0.769** | **0.3154** | 14% vs 12% |

An earlier version reported 0.772 AUC and 0.3132 log loss for the latest months. That came from a process that fitted the recalibration on one model and applied it to a refit model, so it did not match what was shipped. The numbers above replace it.

All numbers are in `data/metrics.json` and are rebuilt by the training script.

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

`train.py` writes `data/model.json`, `data/metrics.json` (evaluation periods, calibration bands) and `data/parity.json`. `build_planb.py` writes `data/planb.json`. `check_planb.py` rewrites the hand check report from the raw schedule.

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
- Every evaluation period keeps base, recalibration and test periods in order and beats the cause only rule.

A real browser check clicks every example button at 390 px and 1440 px, then runs the ambiguous alert flow, clearing, and the load error retry:

```
pip install playwright && python3 -m playwright install chromium
python3 tests/browser_check.py https://alenzacodes.github.io/wait-or-walk/
```

## Limits

An estimate, not a promise. Rare causes rest on few cases (fire or smoke: 94 delays; personal injury at track level: 34), and the page says so. Plan B uses straight line distance and the regular schedule, not live detours or shuttle buses. It has not been tested with riders. Data: City of Toronto Open Data under the Open Government Licence Toronto.

## Licence

Code: MIT, copyright John Khan. See `LICENSE`. Data: City of Toronto Open Data under the Open Government Licence Toronto.
