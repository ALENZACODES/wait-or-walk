# Wait or Walk

The subway just stopped. Will it be two minutes or twenty? Paste a TTC subway alert and Wait or Walk shows how often comparable logged incidents delayed subway service 10 minutes or more, the reasons behind that number, and scheduled buses and streetcars a short walk away that head where you are going.

Live: https://alenzacodes.github.io/wait-or-walk/

Built by John Khan in Toronto, Ontario for SLAY HACKS 2026. Not affiliated with or endorsed by the Toronto Transit Commission (TTC).

## Worked example
Alert pasted on a weekday at 5:30 p.m., heading to Jane: *"Line 2 Bloor-Danforth: Delays at Kipling due to a person at track level."*
- **Read from the alert (tagged for checking):** Line 2, Kipling, person at track level.
- **Estimated chance:** 23% that an incident like this delays subway service 10 minutes or more (moderate risk). Beside it: 40% for 5+ minutes, 10% for 20+ minutes.
- **Drift correction:** 29% before recalibration, 23% after.
- **Why 23% and not 48%:** 48% is every logged delay with this cause since January 2025 (270 of 563). The estimate adjusts that for the station, the line, the time of day and the drop in long delays in 2026 (in the latest 91 days, 41% of 80 delays with this cause ran 10 minutes or more). The cause raises the odds; Kipling and the evening rush lower them.
- **Plan B, earliest scheduled arrival first (may not be running right now):** 149 Etobicoke-Bloor from Kipling Station (10 m, about a 1 minute walk, accessible boarding listed): next you can catch 5:39, 6:07 and 6:35 p.m.; by the schedule at Jane about 5:57 p.m. Then 40 Junction-Dundas West (100 m): next you can catch 5:53 p.m.; at Islington about 5:58, then Line 2 to Jane about 6:04 p.m. if the subway runs normally there.
- **Safety first:** always follow TTC staff and announcements. This is a planning aid for riders on a platform, not for decisions about leaving a train or evacuating.

## How it works

1. **Read the alert.** `logic.js` reads the alert with hand written rules, not a trained model: regular expressions for line names, keyword patterns for 14 causes checked in a fixed order with the most specific first ("person at track level" before "track"), and a search for the 71 station names plus a few older names such as Dundas for TMU. It pulls the line, the station and the cause out of the alert text (for example "Line 2: Delays at Kipling due to a person at track level"). Anything it reads is tagged "from alert, please check", and anything it cannot find is left empty, never carried over from before. If the alert is ambiguous, no number is shown until you choose: an alert that names more than one station asks which one, and Bloor-Yonge (or St George, Spadina or Sheppard-Yonge) without a line asks which line. A station that is not on the chosen line (Union on Line 2) also gives no number. Clearing the alert clears everything it filled in, and the number with it.
2. **Score it.** Three logistic regressions (5+, 10+ and 20+ minutes), trained in Python with scikit-learn and run in the browser, score five things an alert tells you: cause, station, line, time of day and weekend. The three are kept in order (5+ at least the 10+ chance, 20+ at most).
3. **Explain it.** Right under the risk band, the call card shows the drift correction (the forecast before and after recalibration). Below that: the number of logged delays behind the cause (with a warning under 100) and the factors that pushed the chance up or down most.
4. **Plan B: scheduled alternatives.** Never claimed as the quickest way; right above the list the page warns that a scheduled alternative might not be running now. From the TTC schedule (GTFS files dated Oct 20, 2026, covering Nov 1 to Dec 21, 2026; still the newest published on Nov 15, 2026), every regular stop pattern (5% or more of a route direction's trips) of every bus, streetcar and LRT route, with the subway stations it passes within 300 metres in order and the median scheduled ride time between them. Line 5 Eglinton and Line 6 Finch West are listed as LRT. Each stop shows its distance and walking time (80 metres a minute, straight line) and the schedule's accessible boarding flag (`wheelchair_boarding`). Only departures you can still catch are shown: at or after now plus the walk plus 1 minute to board, using today's service calendar and exceptions (and the previous day's trips that run past midnight). With a destination, entries are ordered by that departure plus the scheduled ride, plus the scheduled subway time onward where you change. Times refresh every minute and follow the service date past midnight; outside the schedule's dates the page says "Schedule data ends on Dec 21, 2026" and shows no times. Blue Night routes (300 to 399) are listed separately.

## What the number means

The TTC logs each incident with the minutes it delayed subway service. The headline number ("Estimated chance") is the estimated chance that an incident like this one, logged with more than 0 minutes of delay, delayed service 10 minutes or more. It is not your own remaining wait. Records with 0 minutes of delay (30,515 on Lines 1, 2 and 4) are left out.

The risk bands are a plain language summary: under 15% low, 15% to 35% moderate, 35% and up high ("worth checking another route now").

## The model

- **Data:** TTC Subway Delay Data since 2025 (City of Toronto Open Data, refreshed Oct 26, 2026). The copy used here has 47,915 records from Jan 1, 2025 to Sep 30, 2026; I have not checked it against the TTC's internal logs. Kept: Lines 1, 2 and 4, delays over 0 minutes (16,548 delays). Target: 10 minutes or more.
- **Causes a rider can see:** the TTC's 124 delay codes are grouped into the 15 causes alerts actually say, such as "medical emergency", "person at track level" or "signal problem".
- **Drift:** long delays became rarer in 2026 (about 19% of delays in early 2025, about 12% in summer 2026). Each delay is weighted by age with a 180 day half life, and the output is recalibrated (Platt scaling).
- **One process, tested as shipped:** the base model is trained on everything before the last 91 days, Platt scaling is fitted on those 91 days, and that pair is shipped with no refit. The shipped model: base trained through Jul 1, 2026, recalibrated on Jul 2 to Sep 30, 2026.
- **Rare causes:** cause features get lighter shrinkage than station features, so a rare but serious cause such as a personal injury at track level is not pulled towards average.

## Honest results
**In three lines:**
1. **Ranking:** clearly better than the cause alone (AUC 0.751 against 0.727) and level with the first model (0.751 against 0.753, not distinguishable).
2. **Calibration:** closer than the first model (1.8 against 2.4 points, distinguishable), but forecasts still run a few points high.
3. **Decisions:** in a simulation with schedule based switch costs it saves time only on long delays and loses a little on short ones; overall it is 0.35 minutes behind always waiting. It has not been tested with riders.

Everything below is on three out of time evaluation periods not used for fitting (Jan to Mar, Apr to Jun and Jul to Sep 2026; 7,455 delays), each run with the exact process that ships, with 95% bootstrap intervals (2,000 resamples).

| 10+ minutes, pooled | AUC | Log loss | Brier score | Calibration error |
|---|---|---|---|---|
| Wait or Walk | 0.751 (0.736 to 0.767) | 0.3628 (0.3507 to 0.3758) | 0.1103 (0.1058 to 0.1150) | 1.8 (1.1 to 2.5) pts |
| Cause only rule | 0.727 (0.712 to 0.743) | 0.3723 (0.3605 to 0.3852) | 0.1130 (0.1084 to 0.1178) | 1.9 (1.2 to 2.7) pts |
| First model | 0.753 (0.737 to 0.768) | 0.3630 (0.3513 to 0.3757) | 0.1103 (0.1059 to 0.1150) | 2.4 (1.7 to 3.2) pts |

- **Against the cause only rule:** AUC 0.024 better (0.016 to 0.032), log loss 0.0095 better (0.0060 to 0.0127), Brier 0.0027 better, all distinguishable; calibration error not distinguishable. Distinguishably better in the first two periods; not in the latest.
- **Against the first model:** AUC, log loss and Brier not distinguishable; calibration error 0.6 points lower (0.3 to 0.9), distinguishable. Distinguishably behind in the first period (AUC 0.724 against 0.731), distinguishably better on log loss, Brier and calibration in the latest.
- **Day blocks:** delays on one day can share causes, so as a sensitivity check whole service days were resampled. All 32 conclusions (pooled and per period, both baselines, four measures) stay the same.
- **5+ and 20+ minutes:** 5+ AUC 0.702 against 0.643 for the cause alone; level with the first model on AUC, better calibrated (2.4 against 4.5 points). 20+ AUC 0.773 against 0.752; level with the first model. Only 4% of test delays ran 20+ minutes.
- **Station by cause pooling:** an empirical Bayes adjustment for every station and cause pair (gamma prior, strength picked by marginal likelihood) chose the strongest pooling tried, in effect no adjustment; without pooling the pairs make it worse (log loss 0.3702). Not shipped.
- **How the settings were chosen:** the 180 day half life, 91 day window and 15% and 35% cut offs were set in the first commit and never changed, but not blind: an earlier private prototype was tested on July to September 2026, saw forecasts running high, and that led to age weighting and recalibration. A 61 day window would have scored slightly better (log loss 0.3619 against 0.3628); the shipped values were kept rather than tuned on the test periods.

**Decision value** at the risk band cut offs, pooled:

| Flag at | Method | Share of 10+ minute delays flagged | False flag rate | Flagged that ran 10+ minutes |
|---|---|---|---|---|
| 15% | Wait or Walk | 74% | 37% | 25% |
| 15% | Cause only rule | 71% | 37% | 25% |
| 15% | First model | 75% | 39% | 25% |
| 35% | Wait or Walk | 25% | 5% | 44% |
| 35% | Cause only rule | 14% | 2% | 51% |
| 35% | First model | 29% | 7% | 43% |

**A decision simulation with schedule based switch costs, not real savings.** For each test delay and each direction along its line, switching costs the walk plus 1 minute to board, the wait for the next scheduled departure, and the scheduled ride to a station past the delay (at most 3 stops along), minus the scheduled subway time for the same stations (floored at 0). Waiting costs the logged delay minutes, capped at 60. A rider switches at 35% or more. Intervals resample whole days.

| Average minutes lost per delay | Always wait | Cause only | First model | Wait or Walk | Hindsight | Wait or Walk against always wait |
|---|---|---|---|---|---|---|
| All delays (7,455) | 6.56 | 6.71 | 6.96 | 6.91 | 6.12 | 0.35 lost (0.26 to 0.44) |
| Under 10 minutes (6,363) | 4.45 | 4.67 | 4.91 | 4.86 | 4.41 | 0.41 lost (0.33 to 0.50) |
| 20+ minutes (309) | 34.02 | 32.42 | 32.56 | 32.34 | 26.62 | 1.68 saved (0.98 to 2.48) |
| 30+ minutes (139) | 46.64 | 43.63 | 44.14 | 43.48 | 34.37 | 3.16 saved (1.80 to 4.79) |

Read honestly: it saves minutes in the long tail and loses a little on the many short delays. In the tail it is level with the cause only rule (0.08 minutes ahead, 0.21 behind to 0.39 ahead); across all delays the cause only rule, which switches less, loses less. 7,483 of 13,174 delay and direction pairs had a scheduled alternative within 3 hours.

All numbers are in `data/metrics.json` (`folds` for each period; `evidence` for intervals, `dayBlock`, `survival`, `bands`, `cellShrinkage`, `sensitivity`, `decisionValue`, `stationSimulation` and the fixed cost `simulation`) and are rebuilt by the training script.

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
pip install pandas numpy scipy scikit-learn
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
python3 scripts/build_planb.py /tmp/ttc
python3 scripts/train.py /tmp/ttc
python3 scripts/check_planb.py /tmp/ttc > docs/plan-b-checks.md
```

Run `build_planb.py` first: the station simulation in `train.py` reads its output. `train.py` writes `data/model.json` (the 10+ model plus the 5+ and 20+ models), `data/metrics.json` (evaluation periods, calibration bands, bootstrap intervals by delay and by day, the 5+ and 20+ results, station by cause pooling, settings sensitivity, decision value and both simulations) and `data/parity.json`. It takes about 15 minutes. `build_planb.py` writes `data/planb.json` and `data/planb_times.json` (departure times and the service calendar). `check_planb.py` rewrites the hand check report from the raw schedule.

## Tests

```
node tests/test_logic.mjs
```

GitHub Actions runs this on every push. It covers:

- **Parity test:** the browser code gives the same 5+, 10+ and 20+ probabilities as the Python models on 30 example inputs, within 0.0001, and keeps them in order. This is an implementation check, not an accuracy test.
- Cause ordering, risk bands, and alert reading.
- Ambiguous alerts: Bloor-Yonge with no line, two stations named, and a two line station with no line all give no number until a choice is made. Clearing the alert clears the derived fields and the number.
- Every example button gives a number, except the one meant to show the choice.
- The Toronto clock and the station data.
- Plan B direction and destination cases, including the five hand checked journeys.
- Station and line mismatch (Union on Line 2) gives no number.
- Line 5 Eglinton is LRT; trips that end at the station are not offered; the service calendar, walking time, and reachable departures: the hand checked 7:35 weekday 149 is offered at 7:33 and not at 7:34; ranking by scheduled arrival; Dec 7 and Dec 20 covered, Dec 22 not; 3 a.m. counts the previous day's late trips.
- Every evaluation period keeps base, recalibration and test periods in order; bootstrap intervals (by delay and by day) bracket their values; the published claims about which differences are distinguishable match the numbers.

A real browser check clicks every example button at 390 px and 1440 px, runs the ambiguous alert and mismatch flows, clearing, the card labels and safety line, Plan B with the clock fixed at 5:38 p.m. (the 5:39 bus is not offered), Dec 7, Dec 20, 3 a.m. and Dec 22, a minute by minute refresh across midnight, and the load error retry:

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

## Safety

Always follow TTC staff and announcements. Wait or Walk is a planning aid for riders on a platform, not for decisions about leaving a train or evacuating.

## Licence

Code: MIT, copyright John Khan. See `LICENSE`. Data: City of Toronto Open Data, TTC Subway Delay Data since 2025 and TTC Routes and Schedules (GTFS, files dated Oct 20, 2026), both under the Open Government Licence Toronto (https://open.toronto.ca/open-data-licence/). Not affiliated with or endorsed by the TTC.

SLAY HACKS began November 7, 2026, and all of Wait or Walk was built after that. A private prototype script came first, to test the idea; the public repo's first commit (git log --reverse) is from 6:08 a.m. Toronto time on November 15, 2026, and every change since is in its history. No application code came from earlier projects: a line by line comparison with my other GitHub repos found only boilerplate in common (page colour variables and a few base style rules, the standard module wrapper, test imports). Data: City of Toronto Open Data, TTC Subway Delay Data since 2025 and TTC Routes and Schedules (GTFS), both under the Open Government Licence Toronto. Libraries: pandas, NumPy, SciPy and scikit-learn for training.
