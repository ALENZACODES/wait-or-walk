# Wait or Walk

**Subway stopped? Paste the TTC alert to see the chance of a long delay, timetabled buses nearby, and whether to wait.**

Or tap an alert from the copied TTC feed. In about 30 seconds you see four things: the alert read back, the chance comparable recorded delays lasted 10 minutes or more, the scheduled departures you may be able to catch (timetable estimates, not real time), and a verdict on whether waiting or switching looks better by the timetable, with its break even margin. No rider testing has been done yet.

Live: https://alenzacodes.github.io/wait-or-walk/

Built by John Khan in Toronto, Ontario for SLAY HACKS 2026. Not affiliated with or endorsed by the Toronto Transit Commission (TTC).

## Worked example
Simulated Monday, November 16, 2026, 5:30 p.m., heading to Jane: *"Line 2 Bloor-Danforth: Delays at Kipling due to a person at track level."* Example buttons on the page run on a fixed clock, labelled "Simulated Monday, November 16, 2026, 5:30 p.m.", inside the schedule data, so they still work after it ends on Dec 21, 2026.
- **Read from the alert (tagged for checking):** Line 2, Kipling, person at track level.
- **Estimated chance:** 23%, the chance the recorded delay lasts 10 minutes or more, among comparable recorded TTC delays (moderate risk). Beside it: 40% for 5+ minutes, 10% for 20+ minutes. Under it: "Not the chance your alert causes this delay, or your remaining wait." In full, under "What this number means": "Among comparable recorded TTC delays, the model estimates a 23% chance the recorded delay lasts 10 minutes or more. This is not the chance your current alert causes that delay, or your remaining wait."
- **Drift correction:** 29% before recalibration, 23% after.
- **Why 23% and not 48%:** 48% is every logged delay with this cause since January 2025 (270 of 563). The estimate adjusts that for the station, the line, the time of day and the drop in long delays in 2026 (in the latest 91 days, 41% of 80 delays with this cause ran 10 minutes or more). The cause raises the odds; Kipling and the evening rush lower them.
- **Plan B, earliest scheduled arrival first (may not be running right now):** 149 Etobicoke-Bloor from Kipling Station (10 m, about a 1 minute walk, accessible boarding listed): scheduled departures you may be able to catch: 5:39, 6:07 and 6:35 p.m.; timetable estimate, not real time: at Jane about 5:57 p.m. Then 40 Junction-Dundas West (100 m): scheduled departure you may be able to catch: 5:53 p.m.; timetable estimate: at Islington about 5:58, then Line 2 to Jane about 6:04 p.m. if the subway runs normally there.
- **Verdict, schedule comparison: waiting looks better.** Assuming the incident has just begun, delays like this average about 8 minutes, against 19 extra minutes by Plan B (route 149 Etobicoke-Bloor to Jane, a timetable estimate, not real time). An estimate from recorded delays, not your remaining wait. Break even line: "by the timetable switching loses by about 11 minutes; it would pay off only if this delay ran about 11 minutes longer than the estimate."
- **Already underway:** with "Delay already reached 5 min", the chance of 10 minutes or more in total among comparable delays that reached 5 becomes 58% (25% for 20+), with about 10 minutes left on average: still wait. With "Delay already reached 10 min", 43% for 20 or more in total, about 12 minutes left: still wait, against 19 by the 149.
- **Jane is 4 stops from Kipling** (Islington, Royal York, Old Mill, Jane). The simulation's 3 stop cap does not apply here: on the page the switch cost runs door to destination, while in the simulation the cap only picks which station counts as past the delay (for the 149 from Kipling, Islington, 1 stop along).
- **How 23% becomes about 8 minutes:** a 60% chance of under 5 minutes (about 3 on average), 17% of 5 to 10 (about 6), 13% of 10 to 20 (about 13) and 10% of 20 or more (about 34).
- **Safety first:** always follow TTC staff and announcements. This is a planning aid for riders on a platform, not for decisions about leaving a train or evacuating.

**The contrasting case, where switching looks better.** Same weekday, 5:30 p.m., heading to Dupont: *"Line 1: Trains are bypassing St. George while we investigate a fire."* Estimated chance 66% (96% for 5+, 46% for 20+, flagged as rough because only 94 logged delays have this cause). By this estimate delays like this average about 20 minutes. Plan B: 26 Dupont from St George Station (70 m, about a 1 minute walk), scheduled departure you may be able to catch: 5:35 p.m., at Dupont about 5:41 p.m. (timetable estimate, not real time), 9 extra minutes. The verdict says switching looks better, and that switching only helps if you make that bus and it runs on time, with a link to check TTC service alerts. Break even line: "by the timetable switching wins by about 11 minutes. If the 5:35 p.m. bus leaves 11 minutes or more late, or you miss it (the next is 5:58 p.m.), waiting would have been better." With the delay already at 5 minutes it is 69% and about 16 minutes left, still switching. Both cases are buttons on the simulated clock, and a browser test with the date faked as January 5, 2027 checks both still work while live time shows the schedule ended message.

## How it works

1. **Read the alert.** You paste the whole alert (there is a paste button and a link to TTC service alerts), or tap one from a copy of the TTC's open GTFS Realtime subway alerts (City of Toronto Open Data, Open Government Licence Toronto). The page cannot read that feed itself (it sends no cross origin header), so a scheduled GitHub Action (`.github/workflows/alerts.yml`, `scripts/fetch_alerts.py`) copies it into `data/live_alerts.json` every 30 minutes and commits only when the alerts changed; the page shows when the copy was made and paste always works. The job also logs when each alert was first and last seen (`data/alert_history.json`), shown as an "alerts seen this month" strip: a record of what the TTC posted, not a check of the forecasts. The page asks GitHub's public API when the job last ran; if the copy was last checked more than 90 minutes ago it marks the alerts as possibly out of date, in red, with a link to TTC service alerts. The job's commits are automated: they are titled "Copy TTC subway alerts", are made under my name by the workflow, and change only the alerts data files (`data/live_alerts.json`, `data/alert_history.json` and `data/access_alerts.json`). The job runs on a 30 minute schedule and can also be started by hand; as of 3:45 p.m. Toronto time on November 15, 2026, both runs so far were started by hand, and the first scheduled run is pending. Alerts that read as planned work or a slow zone get no forecast at all: "This is planned service work. The incident delay model does not apply." `logic.js` reads it with hand written rules, not a trained model: regular expressions for line names, keyword patterns for 14 causes checked in a fixed order with the most specific first ("person at track level" before "track"), and a search for the 71 station names plus a few older names such as Dundas for TMU. It pulls the line, the station and the cause out of the alert text (for example "Line 2: Delays at Kipling due to a person at track level"). Anything it reads is tagged "from alert, please check", and anything it cannot find is left empty, never carried over from before. If the alert is ambiguous, no number is shown until you choose: an alert that names more than one station asks which one, and Bloor-Yonge (or St George, Spadina or Sheppard-Yonge) without a line asks which line. A station that is not on the chosen line (Union on Line 2) also gives no number. Clearing the alert clears everything it filled in, and the number with it.
2. **Score it.** Three logistic regressions (5+, 10+ and 20+ minutes), trained in Python with scikit-learn and run in the browser, score five things an alert tells you: cause, station, line, time of day and weekend. The three are kept in order (5+ at least the 10+ chance, 20+ at most).
3. **Explain it.** Right under the risk band, the call card shows the drift correction (the forecast before and after recalibration). Below that: the number of logged delays behind the cause (with a warning under 100) and the factors that pushed the chance up or down most.
4. **Already underway.** Three buttons on the card: "Just started", "Delay already reached 5 min" and "Delay already reached 10 min", with the note "The model is calibrated on recorded delay length, not time since the alert." They condition the same calibrated models, with no refit: P(10+ | 5+) = P(10+) / P(5+) and P(20+ | 10+) = P(20+) / P(10+), which stay between 0 and 1 because the bands are kept in order (zero bands give no number rather than a division by zero). Expected minutes left come from the averages of the ranges still possible, minus the minutes gone. The log gives total minutes, not alert times, so the buttons say what they mean: "the recorded delay already reached 5 minutes". Checked on the same test periods (`scripts/underway_checks.py`): among 3,573 test delays that reached 5 minutes, the 10+ chance averaged 34% against 31% actual (AUC 0.689, 0.671 to 0.707, against 0.678 for the cause alone; calibration error 3.2 points); among 1,092 that reached 10, the 20+ chance averaged 28% against 28% actual (28.5 against 28.3) (AUC 0.683, 0.644 to 0.720). Expected minutes left against logged: 6.9 against 6.6 from the start, 5.4 against 5.0 from 5 minutes, 9.1 against 8.9 from 10 minutes.
5. **Plan B: scheduled alternatives.** Never claimed as the quickest way; right above the list the page warns that a scheduled alternative might not be running now. From the TTC schedule (GTFS files dated Oct 20, 2026, covering Nov 1 to Dec 21, 2026; still the newest published on Nov 15, 2026), every regular stop pattern (5% or more of a route direction's trips) of every bus, streetcar and LRT route, with the subway stations it passes within 300 metres in order and the median scheduled ride time between them. Line 5 Eglinton and Line 6 Finch West are listed as LRT. Each stop shows its distance and walking time (80 metres a minute, straight line) and the schedule's accessible boarding flag (`wheelchair_boarding`). Only scheduled departures you may be able to catch are shown (timetable estimates, not real time): at or after now plus the walk plus 1 minute to board, using today's service calendar and exceptions (and the previous day's trips that run past midnight). With a destination, entries are ordered by that departure plus the scheduled ride, plus the scheduled subway time onward where you change. Times refresh every minute and follow the service date past midnight; outside the schedule's dates the page says "Schedule data ends on Dec 21, 2026" and shows no times. Blue Night routes (300 to 399) are listed separately.
6. **Plan B extras, behind a fold.** An elevator or escalator outage at the delay station or your destination shows as a warning under Plan B, from the TTC's accessibility alerts feed, copied by the same job (Open Government Licence Toronto); the page does not invent step free routes. Inside "More: route delay history, Bike Share and weather": how often each Plan B route logged a delay of 10 minutes or more (TTC bus and streetcar delay logs, Jan to Sep 2026, per scheduled trip), shown only because a check passed first: each route's 2025 rate ranked the routes' 2026 rates well (rank correlation 0.87 over 200 routes with at least 200 trips a week) and was a closer guess than the network average (average error 0.08 against 0.17 per 100 trips). These count reported incidents, not on time performance, and do not change the estimate. Then Bike Share Toronto stations within 400 metres of the delay station and the destination, with live bikes and open docks read in your browser from the Bike Share Toronto GBFS feed (no ride time is estimated; snow, luggage or a stroller can make cycling the wrong choice). Last, current Toronto weather from Environment and Climate Change Canada, as context only: weather is not part of the forecast, because it has not been tested as a predictor.

## What the number means

The TTC logs each incident with the minutes it delayed subway service. In full: among comparable recorded TTC delays, the model estimates the chance the recorded delay lasts 10 minutes or more (23% in the Kipling example). This is not the chance your current alert causes that delay, or your remaining wait. Comparable means delays with this cause, station, line, time of day and day type, as the model weighs them. Records with 0 minutes of delay (30,515 on Lines 1, 2 and 4) are left out.

The risk bands are a plain language summary: under 15% low, 15% to 35% moderate, 35% and up high. The wait or switch line under them compares the expected logged delay with the best scheduled switch to your destination (see Honest results).

## The model

- **Data:** TTC Subway Delay Data since 2025 (City of Toronto Open Data, refreshed Oct 26, 2026). The copy used here has 47,915 records from Jan 1, 2025 to Sep 30, 2026; I have not checked it against the TTC's internal logs. Kept: Lines 1, 2 and 4, delays over 0 minutes (16,548 delays). Target: 10 minutes or more.
- **Causes a rider can see:** the TTC's 124 delay codes are grouped into the 15 causes alerts actually say, such as "medical emergency", "person at track level" or "signal problem".
- **Drift:** long delays became rarer in 2026 (about 19% of delays in early 2025, about 12% in summer 2026). Each delay is weighted by age with a 180 day half life, and the output is recalibrated (Platt scaling).
- **One process, tested as shipped:** the base model is trained on everything before the last 91 days, Platt scaling is fitted on those 91 days, and that pair is shipped with no refit. The shipped model: base trained through Jul 1, 2026, recalibrated on Jul 2 to Sep 30, 2026.
- **Rare causes:** cause features get lighter shrinkage than station features, so a rare but serious cause such as a personal injury at track level is not pulled towards average.

## Honest results
**In three lines:**
1. **Ranking:** better than the cause alone (AUC 0.751 against 0.727) and level with the first model (0.751 against 0.753, not distinguishable).
2. **Calibration:** better calibrated than the first model (1.8 against 2.4 points, distinguishable), though forecasts still run a few points high.
3. **Decisions:** on delays of 20 minutes or more, the schedule comparison saves about 3 minutes per delay in simulation (3.08, 2.23 to 4.04). Averaged over all delays the gain is small (0.16 minutes, 0.11 to 0.20), exploratory, and gone if buses run 5 minutes late or a departure is missed. No rider testing has been done; a five question test script is ready in [docs/rider-test.md](docs/rider-test.md).

The shipped model itself is never scored; every number below comes from per period models built the same way.

**Which data each test period's model saw.** No test period is scored with a calibration fit on that period. Each has its own base model and its own Platt scaling, fit on the 91 days before the period starts:

| Test period | Base model trained on | Recalibrated on | Test delays |
|---|---|---|---|
| Jan 1 to Mar 31, 2026 | Jan 1, 2025 to Oct 1, 2025 | Oct 2 to Dec 31, 2025 | 2,576 |
| Apr 1 to Jun 30, 2026 | Jan 1, 2025 to Dec 30, 2025 | Dec 31, 2025 to Mar 31, 2026 | 2,631 |
| Jul 1 to Sep 30, 2026 | Jan 1, 2025 to Mar 31, 2026 | Apr 1 to Jun 30, 2026 | 2,248 |
| None: the shipped model | Jan 1, 2025 to Jul 1, 2026 | Jul 2 to Sep 30, 2026 | not scored |

The shipped model is not used for any score here, and the calibration chart on the page uses the test period forecasts. An automated test checks that every recalibration window, and every decision rule setting, comes from data before its test period.

- **Jul to Sep 2026 is not a fully independent check.** An earlier private prototype was tested on that period, and what it showed (forecasts running high) led to the age weighting and recalibration. So the results from that period informed the approach. The pooled results are shown without it below.
- **No fresh frozen test yet.** On November 15, 2026 the newest TTC delay file on City of Toronto Open Data (updated October 26, 2026) still ends on September 30, 2026, the last day the shipped model saw, so there are no newer delays to score. `scripts/frozen_test.py` checked and recorded that in `docs/frozen-test-2026-11-15.json`; when newer delays are published it scores the frozen shipped model once on them against the cause only rule and the first model. That period will be the untouched one.

**Each evaluation period on its own.** The settings for each period (the decision rule margin and the recalibration) were picked on its earlier window, then scored once on the later period. All three periods were looked at while the rules were chosen, so every row is exploratory; Jul to Sep also informed the approach.

| Evaluation period (scored on, later) | Settings picked on (earlier window) | Delays | AUC, Wait or Walk (cause only) | 10+ forecast vs actual | Rule against always wait: all delays / 20+ minutes | Status |
|---|---|---|---|---|---|---|
| Jan 1 to Mar 31, 2026 | Oct 2 to Dec 31, 2025 (margin 0.5 minutes below) | 2,576 | 0.724 (0.685) | 18% vs 18% | 0.13 saved (0.06 to 0.21) / 2.24 saved (1.21 to 3.43) | Exploratory: looked at while the rules were chosen |
| Apr 1 to Jun 30, 2026 | Dec 31, 2025 to Mar 31, 2026 (margin 1 minute above) | 2,631 | 0.758 (0.729) | 17% vs 14% | 0.20 saved (0.12 to 0.29) / 3.86 saved (2.28 to 5.72) | Exploratory: looked at while the rules were chosen |
| Jul 1 to Sep 30, 2026 | Apr 1 to Jun 30, 2026 (margin 0.5 minutes above) | 2,248 | 0.769 (0.760) | 14% vs 12% | 0.14 saved (0.08 to 0.23) / 3.54 saved (1.62 to 5.78) | Exploratory: looked at while the rules were chosen, and it informed the approach |

**The wait or switch rule, picked on earlier data.** The old rule said to check another route whenever the 10+ chance was 35% or more. Two rules were tried in its place, each with its setting picked on earlier data only (each test period's own recalibration window) and then tested on that period in the station simulation described below. *20+ chance rule:* switch when the 20+ minute chance reaches a threshold. *Expected cost rule:* switch when the expected logged delay (the three bands times the average logged minutes in each range, capped at 60) minus the station's scheduled switch cost reaches a margin. Average minutes lost per delay, intervals resampling whole days:

| Delays | Always wait | Cause only at 35% | Old rule: 35% | 20+ chance rule | Expected cost rule | Expected cost against always wait | Against the old rule |
|---|---|---|---|---|---|---|---|
| All (7,455) | 6.56 | 6.71 | 6.91 | 6.53 | **6.40** | 0.16 saved (0.11 to 0.20) | 0.50 saved (0.41 to 0.60) |
| Under 10 minutes (6,363) | 4.45 | 4.67 | 4.86 | 4.47 | 4.49 | 0.04 lost (0.03 to 0.05) | 0.37 saved (0.29 to 0.46) |
| 20+ minutes (309) | 34.02 | 32.42 | 32.34 | 32.89 | 30.94 | 3.08 saved (2.23 to 4.04) | 1.40 saved (0.61 to 2.26) |
| 30+ minutes (139) | 46.64 | 43.63 | 43.48 | 44.47 | 41.83 | 4.81 saved (3.17 to 6.74) | 1.65 saved (0.03 lost to 3.45 saved) |

On these periods the expected cost rule was clearly better than the old rule, the cause only rule (0.31 minutes saved, 0.24 to 0.38) and always waiting, so it ships, with its margin (0 minutes) picked the same way on the shipped model's own recalibration window; the 20+ chance rule was not, so it does not. It wins by switching less on short delays and more on long ones. These are simulated minutes: the intervals hold only under the simulation's assumptions (Tue Nov 17, Sat Nov 21 and Sun Nov 22, 2026 schedule days applied to earlier delays, logged delay minutes as the cost of waiting, alternatives that run as scheduled). On the page the switch cost uses your destination when it is on the same line; in the simulation it is the first station past the delay, averaged over both directions.

**Exploratory, not confirmed.** The expected cost rule was chosen over the 20+ chance rule after both were compared on these same evaluation periods, so its advantage is exploratory: the intervals above do not account for that choice, and it has not been confirmed on an untouched period (none exists yet; see the forecast log below). Within the rule, the margin picked on each earlier window varied: 0.5 minutes below, 1 minute above and 0.5 minutes above; the shipped margin is 0.

**Too close to call, tested.** The verdict can say "too close to call" when the expected delay and the timetable switch are within a break even band; inside the band the advice is to wait. For each evaluation period the band was picked on its earlier window (the widest of 0.5 to 5 minutes costing at most 0.01 minutes per delay there): 2, 0.5 and 0.5 minutes. On the later periods it was level with the shipped rule as scheduled (0.00 minutes per delay, 0.02 lost to 0.02 saved) and lost less when buses ran 5 minutes late (0.10 saved, 0.07 to 0.12) or a departure was missed (0.57 saved, 0.48 to 0.65), so it passed the rule set in advance. On delays of 20 minutes or more it was worse as scheduled (0.51 minutes, 0.15 to 0.97). Picked the same way on the shipped model's own window, the band is 0 minutes, so today the page shows no "too close to call" label in practice. It always shows a break even line instead: by how many minutes switching wins or loses, and for a switch, how late the bus can leave (or that missing it, with the next scheduled departure) before waiting would have been better.

**Stress test: when the switch costs more than the schedule says.** The rider still decides from the schedule, but the switch really costs more. Minutes saved per delay against always waiting (95% intervals, whole days resampled):

| What really happens | All delays | 20+ minute delays |
|---|---|---|
| As scheduled (1.3 m/s walk, 1 minute to board) | 0.16 saved (0.11 to 0.20) | 3.08 saved (2.23 to 4.04) |
| Bus 5 minutes late | 0.14 lost (0.09 to 0.19) | 2.53 saved (1.79 to 3.36) |
| Bus 10 minutes late | 0.44 lost (0.38 to 0.49) | 1.98 saved (1.34 to 2.69) |
| First scheduled departure missed | 1.36 lost (1.24 to 1.48) | 0.22 lost (0.82 lost to 0.36 saved) |
| Walking at 1.0 m/s | 0.02 lost (0.08 lost to 0.04 saved) | 2.78 saved (1.92 to 3.68) |
| 2 minutes to board | 0.31 lost (0.23 to 0.40) | 2.72 saved (1.87 to 3.61) |
| 3 minutes to board | 0.65 lost (0.56 to 0.76) | 2.17 saved (1.43 to 2.93) |
| All of these at once | 2.54 lost (2.33 to 2.77) | 2.15 lost (1.24 to 3.31) |

Read honestly: across all delays the small gain does not survive late buses, a missed departure or longer boarding. On delays of 20 minutes or more it holds up, except with a missed departure or everything at once. That is why the verdict says switching only helps if you make that bus and it runs on time.

**A rule picked for late buses: tested, not shipped.** For each test period the margin was picked on that period's earlier window as the one with the fewest minutes if every bus ran 5 minutes late (margins 3.5, 12.5 and 4 minutes), then the full stress test was run with it. It had to be at least as good as the shipped rule as scheduled and lose less under slippage. Minutes saved per delay against always waiting, all 7,455 delays (95% intervals, whole days resampled):

| What really happens | Shipped rule | Late bus rule | Late bus rule against shipped |
|---|---|---|---|
| As scheduled | 0.16 saved (0.11 to 0.20) | 0.06 saved (0.04 to 0.08) | 0.10 lost (0.06 to 0.14) |
| Bus 5 minutes late | 0.14 lost (0.09 to 0.19) | 0.02 saved (level to 0.04 saved) | 0.16 saved (0.11 to 0.20) |
| Bus 10 minutes late | 0.44 lost (0.38 to 0.49) | 0.03 lost (0.01 to 0.04) | 0.41 saved (0.36 to 0.46) |
| First scheduled departure missed | 1.36 lost (1.24 to 1.48) | 0.14 lost (0.11 to 0.18) | 1.22 saved (1.10 to 1.34) |
| Walking at 1.0 m/s | 0.02 lost (0.08 lost to 0.04 saved) | 0.03 saved (0.01 to 0.06) | 0.05 saved (level to 0.11 saved) |
| 2 minutes to board | 0.31 lost (0.23 to 0.40) | 0.02 lost (0.05 lost to 0.01 saved) | 0.30 saved (0.22 to 0.38) |
| 3 minutes to board | 0.65 lost (0.56 to 0.76) | 0.07 lost (0.04 to 0.10) | 0.59 saved (0.49 to 0.68) |
| All of these at once | 2.54 lost (2.33 to 2.77) | 0.30 lost (0.24 to 0.36) | 2.25 saved (2.05 to 2.46) |

It loses far less when the switch goes wrong, but it is worse as scheduled (0.10 minutes per delay, and 2.17 minutes per delay of 20 minutes or more, 1.43 to 2.98), so by the rule set in advance it is not shipped and the shipped margin stays 0. The verdict instead says switching only helps if you make that bus and it runs on time.

**Drift in the expected delay.** The averages in each range come from the base training data, and long delays became rarer in 2026. They barely moved: for 20+ minutes, 33.9 minutes in the base data against 32.0, 35.2 and 34.0 in the windows just before each period. Using those recent averages instead (with the margin picked again on the same earlier window) changed the simulated minutes by 0.01 per delay, not distinguishable, so the shipped averages are kept. The expected delay does run high in the later periods (6.4 against 5.95 logged minutes on average in Jul to Sep, 7.1 against 6.4 in Apr to Jun) because the forecasts themselves run high, not because of the averages.

**Forecast log, a plan.** `docs/forecast-log.md` gets one dated line each time the City publishes newer delays: the frozen shipped model scored, never refit, on delays after September 30, 2026, against both baselines (`scripts/forecast_log.py`). Today it has one line: no new delays yet, so no score.

**The forecast in detail.** Everything below is on the three out of time evaluation periods (7,455 delays), each run with the exact process that ships, with 95% bootstrap intervals (2,000 resamples).

| 10+ minutes, pooled | AUC | Log loss | Brier score | Calibration error |
|---|---|---|---|---|
| Wait or Walk | 0.751 (0.736 to 0.767) | 0.3628 (0.3507 to 0.3758) | 0.1103 (0.1058 to 0.1150) | 1.8 (1.1 to 2.5) pts |
| Cause only rule | 0.727 (0.712 to 0.743) | 0.3723 (0.3605 to 0.3852) | 0.1130 (0.1084 to 0.1178) | 1.9 (1.2 to 2.7) pts |
| First model | 0.753 (0.737 to 0.768) | 0.3630 (0.3513 to 0.3757) | 0.1103 (0.1059 to 0.1150) | 2.4 (1.7 to 3.2) pts |

| 10+ minutes, Jan to Jun 2026 only (5,207 delays) | AUC | Log loss | Brier score | Calibration error |
|---|---|---|---|---|
| Wait or Walk | 0.742 (0.723 to 0.759) | 0.3833 (0.3681 to 0.3985) | 0.1176 (0.1118 to 0.1234) | 1.9 (1.2 to 2.8) pts |
| Cause only rule | 0.707 (0.688 to 0.726) | 0.3963 (0.3813 to 0.4111) | 0.1216 (0.1157 to 0.1274) | 2.0 (1.3 to 3.1) pts |
| First model | 0.746 (0.727 to 0.764) | 0.3808 (0.3651 to 0.3961) | 0.1168 (0.1109 to 0.1226) | 1.6 (1.1 to 2.6) pts |

- **Against the cause only rule:** AUC 0.024 better (0.016 to 0.032), log loss 0.0095 better (0.0060 to 0.0127), Brier 0.0027 better, all distinguishable; calibration error not distinguishable. Without Jul to Sep the gap is larger (AUC 0.035 better, 0.025 to 0.044).
- **Against the first model:** pooled, AUC, log loss and Brier not distinguishable; calibration error 0.6 points lower (0.3 to 0.9), distinguishable. Without Jul to Sep the first model is slightly ahead on AUC (by 0.004), log loss (by 0.0025) and Brier (by 0.0008), all small but distinguishable whether single delays or whole days are resampled; calibration error not distinguishable. The advantage over the first model comes from the latest period, where the 2026 drop in long delays matters most.
- **Day blocks:** delays on one day can share causes, so as a sensitivity check whole service days were resampled. All 32 conclusions (pooled and per period, both baselines, four measures) stay the same.
- **5+ and 20+ minutes:** 5+ AUC 0.702 against 0.643 for the cause alone; level with the first model on AUC, better calibrated (2.4 against 4.5 points). 20+ AUC 0.773 against 0.752; level with the first model. Only 4% of test delays ran 20+ minutes.
- **Tested and rejected, station by cause pooling:** an empirical Bayes adjustment for every station and cause pair (gamma prior, strength picked by marginal likelihood) chose the strongest pooling tried, in effect no adjustment; without pooling the pairs make it worse (log loss 0.3702). It is not part of the shipped model.
- **How the settings were chosen:** the 180 day half life, 91 day window and 15% and 35% cut offs were set in the first commit and never changed, but not blind to Jul to Sep 2026 (see above). A 61 day window would have scored slightly better (log loss 0.3619 against 0.3628); the shipped values were kept rather than tuned on the test periods. The cut offs still set the risk labels; the switch suggestion now comes from the expected cost rule.

**The old 35% rule in the station simulation.** For each test delay and each direction along its line, switching costs the walk plus 1 minute to board, the wait for the next scheduled departure, and the scheduled ride to a station past the delay (at most 3 stops along), minus the scheduled subway time for the same stations (floored at 0). Waiting costs the logged delay minutes, capped at 60. Here a rider switches at 35% or more.

| Average minutes lost per delay | Always wait | Cause only | First model | Old rule | Hindsight | Old rule against always wait |
|---|---|---|---|---|---|---|
| All delays (7,455) | 6.56 | 6.71 | 6.96 | 6.91 | 6.12 | 0.35 lost (0.26 to 0.44) |
| Under 10 minutes (6,363) | 4.45 | 4.67 | 4.91 | 4.86 | 4.41 | 0.41 lost (0.33 to 0.50) |
| 20+ minutes (309) | 34.02 | 32.42 | 32.56 | 32.34 | 26.62 | 1.68 saved (0.98 to 2.48) |
| 30+ minutes (139) | 46.64 | 43.63 | 44.14 | 43.48 | 34.37 | 3.16 saved (1.80 to 4.79) |

7,483 of 13,174 delay and direction pairs had a scheduled alternative within 3 hours.

**Decision value** of the risk labels, pooled:

| Flag at | Method | Share of 10+ minute delays flagged | False flag rate | Flagged that ran 10+ minutes |
|---|---|---|---|---|
| 15% | Wait or Walk | 74% | 37% | 25% |
| 15% | Cause only rule | 71% | 37% | 25% |
| 15% | First model | 75% | 39% | 25% |
| 35% | Wait or Walk | 25% | 5% | 44% |
| 35% | Cause only rule | 14% | 2% | 51% |
| 35% | First model | 29% | 7% | 43% |

All numbers are in `data/metrics.json` (`folds` for each period and the data each saw; `evidence` for intervals, `pooledFirstTwo`, `dayBlock`, `survival`, `bands`, `cellShrinkage`, `sensitivity`, `decisionValue`, `decisionPolicy`, `stationSimulation` and the fixed cost `simulation`) and are rebuilt by the training script. The shipped wait or switch setting is in `data/policy.json`.

## Plan B journeys checked by hand

Five journeys were checked against the raw TTC schedule files, not the app's own data: one scheduled weekday morning trip each, with the boarding and alighting stops, times and distances. Full details: [docs/plan-b-checks.md](docs/plan-b-checks.md), made by `scripts/check_planb.py`. Each is also an automated test.

| Journey | Lines | What the app shows | Schedule check |
|---|---|---|---|
| Union to College | Line 1 | 97 Yonge, North towards Eglinton Station | Weekday trip, 7:32 to 7:45, 10 stops |
| Finch to Eglinton | Line 1 | 97 Yonge, South towards St Clair Station | Weekday trip, 7:52 to 8:30, 30 stops |
| Kipling to Jane | Line 2 | 149 Etobicoke-Bloor, East towards Jane Station | Weekday trip, 7:35 to 7:55, 12 stops |
| Main Street to Broadview | Line 2 | 62 Mortimer, West towards Broadview Station | Weekday trip, 7:31 to 7:53, 26 stops |
| Dundas West to Union | Line 2 to Line 1 | 504 King east past the delay, change to Line 1 at St Andrew | Weekday trip, 7:30 to 8:19 at St Andrew, 30 stops |

Screenshots of each: `docs/checks/`. These are schedule checks only. No rider testing has been done.

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
python3 scripts/choose_policy.py /tmp/ttc
python3 scripts/check_planb.py /tmp/ttc > docs/plan-b-checks.md
python3 scripts/decision_checks.py /tmp/ttc
python3 scripts/frozen_test.py /tmp/ttc
python3 scripts/forecast_log.py /tmp/ttc
python3 scripts/build_bikeshare.py
python3 scripts/surface_delays.py bus.csv streetcar.csv /tmp/ttc/gtfs.zip
```

Run `build_planb.py` first: the station simulation in `train.py` reads its output. `train.py` writes `data/model.json` (the 10+ model plus the 5+ and 20+ models), `data/metrics.json` (evaluation periods, calibration bands, bootstrap intervals by delay and by day, the 5+ and 20+ results, station by cause pooling, settings sensitivity, decision value and both simulations) and `data/parity.json`. It takes about 15 minutes. `build_planb.py` writes `data/planb.json` and `data/planb_times.json` (departure times and the service calendar). `check_planb.py` rewrites the hand check report from the raw schedule. `choose_policy.py` picks the wait or switch margin on the shipped model's recalibration window and writes `data/policy.json`. `frozen_test.py` downloads the newest delay file and scores the frozen shipped model once on delays after its training data, writing `docs/frozen-test-<date>.json`; on November 15, 2026 there were none. `decision_checks.py` runs the drift check and the stress test (`data/decision_checks.json`). `forecast_log.py` adds a dated line to `docs/forecast-log.md`. `build_bikeshare.py` saves the Bike Share stations near each subway station (`data/bikeshare_near.json`; live counts are never stored). `surface_delays.py` reads the TTC bus and streetcar delay logs (download both CSVs from City of Toronto Open Data first), runs the earlier against later check and writes `data/surface_delays.json`. `decision_checks.py` also tests the too close to call band and writes the per period results.

## Tests

```
node tests/test_logic.mjs
python3 -m unittest discover -s tests -p 'test_*.py'
```

GitHub Actions runs these, and the browser check below, on every push. The Python tests check the alerts job without the network: an unchanged feed writes nothing (so no commit), a change logs first seen, last seen and gone by times, a late run records its own time, a returning alert starts a new sighting, an unchanged accessibility feed writes nothing, and the Bike Share station search keeps the nearest three within 400 metres. It covers:

- **Parity test:** the browser code gives the same 5+, 10+ and 20+ probabilities as the Python models on 30 example inputs, within 0.0001, and keeps them in order. This is an implementation check, not an accuracy test.
- Cause ordering, risk bands, and alert reading, including real TTC alerts from Nov 15, 2026 (line, cause and the station choice filled in; planned work and slow zones flagged so no forecast is shown).
- Already underway: the band ratios, expected minutes left, zero and crossed bands, every parity input, and the test period check file.
- The simulated example clock is a Monday at 5:30 p.m. inside the schedule; the alerts copy has its licensed source and fetch time; the late bus rule is reported and not shipped unless it passes.
- Ambiguous alerts: Bloor-Yonge with no line, two stations named, and a two line station with no line all give no number until a choice is made. Clearing the alert clears the derived fields and the number.
- Every example button gives a number, except the one meant to show the choice.
- The Toronto clock and the station data.
- Plan B direction and destination cases, including the five hand checked journeys.
- Station and line mismatch (Union on Line 2) gives no number.
- Line 5 Eglinton is LRT; trips that end at the station are not offered; the service calendar, walking time, and reachable departures: the hand checked 7:35 weekday 149 is offered at 7:33 and not at 7:34; ranking by scheduled arrival; Dec 7 and Dec 20 covered, Dec 22 not; 3 a.m. counts the previous day's late trips; Blue Night routes only overnight (midnight to 6 a.m.).
- The wait or switch rule: the expected delay from the three bands, the switch call and the shipped setting in `data/policy.json`, which must beat both the old rule and always waiting in the simulation.
- The too close to call band and break even slack, the shipped band in `data/policy.json`, the per period results, and the shapes of the alert history, accessibility, Bike Share and route delay files (the route line is shown only if its check passed).
- No leakage: every evaluation period keeps base, recalibration and test periods in order, every decision rule setting is picked before its test period, and the shipped model's recalibration comes after every test period's; bootstrap intervals (by delay and by day) bracket their values; the published claims about which differences are distinguishable match the numbers.

A real browser check clicks every example button at 390 px and 1440 px, runs the ambiguous alert and mismatch flows, clearing, the card labels and safety line, Plan B with the clock fixed at 5:38 p.m. (the 5:39 bus is not offered, the wait or switch line compares the best switch, no Blue Night line), Dec 7, Dec 20, 3 a.m. (Blue Night route 300 shown) and Dec 22, a minute by minute refresh across midnight, the examples on the simulated clock on Nov 16 and with the date faked as Jan 5, 2027 (both still work; live time shows the schedule ended message), the already underway buttons, planned work with no forecast, the alerts copy (shown with its time, one tap fills the alert, missing copy leaves paste working), a shared link, the load error retry, the stale alerts banner (job status unknown, a run 10 minutes ago with an unchanged feed, a run 3.5 hours ago), the alerts seen this month strip, the elevator and escalator warning, the route delay history, Bike Share and weather extras (and what happens when they fail), and axe-core (Mozilla Public License 2.0, installed in CI, not stored here) checking WCAG 2.1 A and AA rules at both widths with every fold open; it found scrollable tables that could not be reached by keyboard, now fixed. axe-core cannot prove a page is accessible:

```
pip install playwright && python3 -m playwright install chromium
python3 tests/browser_check.py https://alenzacodes.github.io/wait-or-walk/
```

## Limits

An estimate, not a promise. Rare causes rest on few cases (fire or smoke: 94 delays; personal injury at track level: 34), and the page says so. The alert is pasted, or taken from a copy of the TTC feed made every 30 minutes, which can be late (the page marks it as possibly out of date after 90 minutes); planned work and slow zones get no forecast. Plan B uses straight line distance and the regular schedule, not live detours or shuttle buses; every time shown is a timetable estimate, not real time. The route delay history counts logged incidents, not on time performance. No rider testing has been done; the test script is in docs/rider-test.md. Data: City of Toronto Open Data under the Open Government Licence Toronto.

## What's next

- Score the "already underway" setting against real alert times once the copied feed has a few months of alerts to match to the delay log.
- Step free routes between stops, beyond the elevator and escalator warning.
- Live arrival times, and running the five question rider test in docs/rider-test.md.
- Test weather as a predictor on earlier against later data before it is used for anything but context.

## Safety

Always follow TTC staff and announcements. Wait or Walk is a planning aid for riders on a platform, not for decisions about leaving a train or evacuating.

Privacy: no accounts and no tracking. Alerts are read in your browser. The last destination you chose is kept only in your own browser, and "Copy a link to this result" puts the alert in the link itself, not on any server.

## Licence

Code: MIT, copyright John Khan. See `LICENSE`. Data: City of Toronto Open Data, TTC Subway Delay Data since 2025 and TTC Routes and Schedules (GTFS, files dated Oct 20, 2026), both under the Open Government Licence Toronto (https://open.toronto.ca/open-data-licence/). Also under that licence: TTC GTFS Realtime subway and accessibility alerts, and TTC Bus Delay Data and TTC Streetcar Delay Data. Bike Share Toronto station data from its live GBFS feed (Open Government Licence Toronto in the City catalogue; the live feed is listed as CC BY 4.0 by the Mobility Database). Weather: Data Source: Environment and Climate Change Canada (ECCC Data Services End-use Licence), context only. Testing uses axe-core (Mozilla Public License 2.0) and Playwright. Not affiliated with or endorsed by the TTC.

SLAY HACKS began November 7, 2026, and all of Wait or Walk was built after that. A private prototype script came first, to test the idea; the public repo's first commit (git log --reverse) is from 6:08 a.m. Toronto time on November 15, 2026, and every change since is in its history. No application code came from earlier projects: a line by line comparison with my other GitHub repos found only boilerplate in common (page colour variables and a few base style rules, the standard module wrapper, test imports). Data: City of Toronto Open Data, TTC Subway Delay Data since 2025 and TTC Routes and Schedules (GTFS), both under the Open Government Licence Toronto. Libraries: pandas, NumPy, SciPy and scikit-learn for training.
