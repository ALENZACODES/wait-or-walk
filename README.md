# Wait or Walk

**Subway stopped? Paste the TTC alert to see the chance a comparable recorded delay lasts 10+ minutes, and timetabled buses nearby.**

It also gives a cautious wait or switch call. Simulated on 7,455 past delays, it said switch on 107 of 13,174 trips (a delay and a direction of travel, 0.8%): about 8 minutes saved on each (5.5 to 10.4) with buses on schedule, about 3 with the bus 5 minutes late, and about 15 lost when the first bus was missed. Overall that is 0.06 minutes per delay, and 0.95 on delays of 20 minutes or more. No rider testing has been done.

Or tap an alert from the copied TTC feed. In about 30 seconds you see four things: the alert read back, the chance comparable incidents with a recorded delay of 1 minute or more lasted 10 minutes or more, the scheduled departures you may be able to catch (timetable estimates, not real time, with a live prediction where the TTC's older feed has one), and a verdict on whether waiting or switching looks better by the timetable, with its break even margin and what a late or missed bus would do. No rider testing has been done yet.

Live: https://alenzacodes.github.io/wait-or-walk/

Built by John Khan in Toronto, Ontario for SLAY HACKS 2026. Not affiliated with or endorsed by the Toronto Transit Commission (TTC).

## 2 minute judge path
1. Open https://alenzacodes.github.io/wait-or-walk/ and tap "Person at track level, Kipling" (simulated Monday, November 16, 2026, 5:30 p.m.). Read the 23%: the chance the recorded delay lasts 10 minutes or more, among comparable TTC incidents with a recorded delay of 1 minute or more. The verdict says wait: about 8 minutes against 19 by the 149 bus, by the timetable.
2. Tap "Fire at St George, headed to Dupont". 66%, and the verdict says switch, by about 11 minutes by the timetable. Read the timetable risk lines under it: about 11 minutes saved with the 5:35 p.m. bus on time, about 6 if it leaves 5 minutes late, and about 12 lost if you miss it.
3. Tap "Delay already reached 5 min" and see the chance change to 10 minutes or more in total among delays that reached 5.
4. Under "How good is it?": how rarely the verdict says switch (107 of 13,174 simulated trips) and what those calls gain, the held out parser score (98%), and what changes if the 0 minute records are counted.
5. Optional: paste a current alert from ttc.ca/service-alerts to see live time Plan B departures, marked live where the TTC's NextBus feed has a prediction.

The code judged is the tag `slay-hacks-submission` (https://github.com/ALENZACODES/wait-or-walk/tree/slay-hacks-submission). Commits after it titled "Copy TTC subway alerts" are automated data copies and do not touch the model, the verdict rule or the parser.

## Worked example
Simulated Monday, November 16, 2026, 5:30 p.m., heading to Jane: *"Line 2 Bloor-Danforth: Delays at Kipling due to a person at track level."* Example buttons on the page run on a fixed clock, labelled "Simulated Monday, November 16, 2026, 5:30 p.m.", inside the schedule data, so they still work after it ends on Dec 21, 2026.
- **Read from the alert (tagged for checking):** Line 2, Kipling, person at track level.
- **Estimated chance:** 23%, the chance the recorded delay lasts 10 minutes or more, among comparable TTC incidents with a recorded delay of 1 minute or more (moderate risk). Beside it: 40% for 5+ minutes, 10% for 20+ minutes. Under it: "Not the chance your alert causes this delay, or your remaining wait." In full, under "What this number means": "Among comparable TTC incidents with a recorded delay of 1 minute or more, the model estimates a 23% chance the recorded delay lasts 10 minutes or more. This is not the chance your current alert causes that delay, or your remaining wait."
- **Drift correction:** 29% before recalibration, 23% after.
- **Why 23% and not 48%:** 48% is every logged delay with this cause since January 2025 (270 of 563). The estimate adjusts that for the station, the line, the time of day and the drop in long delays in 2026 (in the latest 91 days, 41% of 80 delays with this cause ran 10 minutes or more). The cause raises the odds; Kipling and the evening rush lower them.
- **Plan B, earliest scheduled arrival first (may not be running right now):** 149 Etobicoke-Bloor from Kipling Station (10 m, about a 1 minute walk, accessible boarding listed): scheduled departures you may be able to catch: 5:39, 6:07 and 6:35 p.m.; timetable estimate, not real time: at Jane about 5:57 p.m. Then 40 Junction-Dundas West (100 m): scheduled departure you may be able to catch: 5:53 p.m.; timetable estimate: at Islington about 5:58, then Line 2 to Jane about 6:04 p.m. if the subway runs normally there.
- **Verdict, schedule comparison: waiting looks better.** Assuming the incident has just begun, delays like this average about 8 minutes, against 19 extra minutes by Plan B (route 149 Etobicoke-Bloor to Jane, a timetable estimate, not real time). An estimate from recorded delays, not your remaining wait. Break even line: "by the timetable switching loses by about 11 minutes; it would pay off only if this delay ran about 11 minutes longer than the estimate." Timetable risk for this trip: waiting is better by about 11 minutes with the 5:39 p.m. bus on time, about 16 if it leaves 5 minutes late, and about 39 if you miss it and take the next one (6:07 p.m.).
- **Already underway:** with "Delay already reached 5 min", the chance of 10 minutes or more in total among comparable delays that reached 5 becomes 58% (25% for 20+), with about 10 minutes left on average: still wait. With "Delay already reached 10 min", 43% for 20 or more in total, about 12 minutes left: still wait, against 19 by the 149.
- **Jane is 4 stops from Kipling** (Islington, Royal York, Old Mill, Jane). The simulation's 3 stop cap does not apply here: on the page the switch cost runs door to destination, while in the simulation the cap only picks which station counts as past the delay (for the 149 from Kipling, Islington, 1 stop along).
- **How 23% becomes about 8 minutes:** a 60% chance of under 5 minutes (about 3 on average), 17% of 5 to 10 (about 6), 13% of 10 to 20 (about 13) and 10% of 20 or more (about 34).
- **Safety first:** always follow TTC staff and announcements. This is a planning aid for riders on a platform, not for decisions about leaving a train or evacuating.

**The contrasting case, where switching looks better.** Same weekday, 5:30 p.m., heading to Dupont: *"Line 1: Trains are bypassing St. George while we investigate a fire."* Estimated chance 66% (96% for 5+, 46% for 20+, flagged as rough because only 94 logged delays have this cause). By this estimate delays like this average about 20 minutes. Plan B: 26 Dupont from St George Station (70 m, about a 1 minute walk), scheduled departure you may be able to catch: 5:35 p.m., at Dupont about 5:41 p.m. (timetable estimate, not real time), 9 extra minutes. The verdict says switching looks better: it wins by about 11 minutes by the timetable, more than the 5 minute late bus check, and switching only helps if you make that bus, with a link to check TTC service alerts. Break even line: "by the timetable switching wins by about 11 minutes, so it still wins if the bus leaves 5 minutes late. If the 5:35 p.m. bus leaves 11 minutes or more late, or you miss it (the next is 5:58 p.m.), waiting would have been better." Timetable risk for this trip: by the timetable (the 5:35 p.m. bus on time), switching saves about 11 minutes; if that bus leaves 5 minutes late, about 6; if you miss it and take the next one (5:58 p.m.), waiting is better by about 12 minutes. With the delay already at 5 minutes it is 69% and about 16 minutes left, still switching. Both cases are buttons on the simulated clock, and a browser test with the date faked as January 5, 2027 checks both still work while live time shows the schedule ended message.

## How it works

1. **Read the alert.** You paste the whole alert (there is a paste button and a link to TTC service alerts), or tap one from a copy of the TTC's open GTFS Realtime subway alerts (City of Toronto Open Data, Open Government Licence Toronto). The page cannot read that feed itself (it sends no cross origin header), so a scheduled GitHub Action (`.github/workflows/alerts.yml`, `scripts/fetch_alerts.py`) copies it into `data/live_alerts.json` every 30 minutes and commits only when the alerts changed; the page shows when the copy was made and paste always works. The job also logs when each alert was first and last seen (`data/alert_history.json`), shown as an "alerts seen this month" strip: a record of what the TTC posted, not a check of the forecasts. The page asks GitHub's public API when the job last ran; if the copy was last checked more than 90 minutes ago it marks the alerts as possibly out of date, in red, with a link to TTC service alerts. The job's commits are automated: they are titled "Copy TTC subway alerts", are made under my name by the workflow, and change only the alerts data files (`data/live_alerts.json`, `data/alert_history.json` and `data/access_alerts.json`), the alert time forecast log (`data/alert_forecasts.jsonl`) and the fresh parser test count (`data/parser_fresh.json`). The job runs on a 30 minute schedule, a second schedule offset by 15 minutes, and by hand. Scheduled runs so far: from the first schedule (added at 2:57 p.m. Toronto time on November 15, 2026) to 11:18 p.m. on November 15, the schedule asked for 17 runs and GitHub started 1 (6%): 6:53 p.m. (run 43777263323). The other runs were started by hand. The cron line is valid and the workflow is active on the default branch; GitHub documents that scheduled runs can be delayed or dropped when its runners are busy. So from version r11 a second, independent schedule in its own workflow (`.github/workflows/alerts-backup.yml`, at 22 and 52 minutes past the hour) calls the same job, sharing one concurrency group so the two never run at once; it is free and needs no outside service. Its reliability is not known yet. The page does not depend on it: it reads when the job last ran and marks the copy as possibly out of date after 90 minutes, and paste always works. Each run also saves the forecast for every new alert at that time (`data/alert_forecasts.jsonl`, see Honest results). Alerts that read as planned work or a slow zone get no forecast at all: "This is planned service work. The incident delay model does not apply." `logic.js` reads it with hand written rules, not a trained model: regular expressions for line names, keyword patterns for 14 causes checked in a fixed order with the most specific first ("person at track level" before "track"), and a search for the 71 station names plus a few older names such as Dundas for TMU, ignoring a name inside a longer one (St Clair inside St Clair West). Tested on 102 real TTC alerts posted from August to November 2026, each labelled by hand from the text alone (`data/alerts_labelled.json`, scored by `scripts/parser_eval.mjs`, which runs in CI): the first version named the right station in 87% (13 wrong) and the right cause in 92% (99% of the causes it named were right), and caught 6 of 7 planned work alerts. Fixes found on the 51 older alerts (a station name inside a longer one, such as St Clair in St Clair West; "Vaughan"; "operational problem", "communication issue" and "TPS investigation") lifted the 51 newer ones from 82% to 98% for stations and from 91% to 98% for causes. Three more fixes for the errors left in the newer half make all 102 right, but that score is on the alerts used to fix it, so it is not an independent test. It pulls the line, the station and the cause out of the alert text (for example "Line 2: Delays at Kipling due to a person at track level"). Anything it reads is tagged "from alert, please check", and anything it cannot find is left empty, never carried over from before. If the alert is ambiguous, no number is shown until you choose: an alert that names more than one station asks which one, and Bloor-Yonge (or St George, Spadina or Sheppard-Yonge) without a line asks which line. A station that is not on the chosen line (Union on Line 2) also gives no number. Clearing the alert clears everything it filled in, and the number with it.
2. **Score it.** Three logistic regressions (5+, 10+ and 20+ minutes), trained in Python with scikit-learn and run in the browser, score five things an alert tells you: cause, station, line, time of day and weekend. The three are kept in order (5+ at least the 10+ chance, 20+ at most).
3. **Explain it.** Right under the risk band, the call card shows the drift correction (the forecast before and after recalibration). Below that: the number of logged delays behind the cause (with a warning under 100) and the factors that pushed the chance up or down most.
4. **Already underway.** Three buttons on the card: "Just started", "Delay already reached 5 min" and "Delay already reached 10 min", with the note "The model is calibrated on recorded delay length, not time since the alert." They condition the same calibrated models, with no refit: P(10+ | 5+) = P(10+) / P(5+) and P(20+ | 10+) = P(20+) / P(10+), which stay between 0 and 1 because the bands are kept in order (zero bands give no number rather than a division by zero). Expected minutes left come from the averages of the ranges still possible, minus the minutes gone. The log gives total minutes, not alert times, so the buttons say what they mean: "the recorded delay already reached 5 minutes". Checked on the same test periods (`scripts/underway_checks.py`): among 3,573 test delays that reached 5 minutes, the 10+ chance averaged 34% against 31% actual (AUC 0.689, 0.671 to 0.707, against 0.678 for the cause alone; calibration error 3.2 points); among 1,092 that reached 10, the 20+ chance averaged 28% against 28% actual (28.5 against 28.3) (AUC 0.683, 0.644 to 0.720). Expected minutes left against logged: 6.9 against 6.6 from the start, 5.4 against 5.0 from 5 minutes, 9.1 against 8.9 from 10 minutes.
5. **Plan B: scheduled alternatives.** Never claimed as the quickest way; right above the list the page warns that a scheduled alternative might not be running now. From the TTC schedule (GTFS files dated Oct 20, 2026, covering Nov 1 to Dec 21, 2026; still the newest published on Nov 15, 2026), every regular stop pattern (5% or more of a route direction's trips) of every bus, streetcar and LRT route, with the subway stations it passes within 300 metres in order and the median scheduled ride time between them. Line 5 Eglinton and Line 6 Finch West are listed as LRT. Each stop shows its distance and walking time (80 metres a minute, straight line) and the schedule's accessible boarding flag (`wheelchair_boarding`). Only scheduled departures you may be able to catch are shown (timetable estimates, not real time): at or after now plus the walk plus 1 minute to board, using today's service calendar and exceptions (and the previous day's trips that run past midnight). With a destination, entries are ordered by that departure plus the scheduled ride, plus the scheduled subway time onward where you change. Times refresh every minute and follow the service date past midnight; outside the schedule's dates the page says "Schedule data ends on Dec 21, 2026" and shows no times. Blue Night routes (300 to 399) are listed separately. Where the TTC's older NextBus feed (on UmoIQ, open to browsers with no key) has a live prediction for a Plan B stop, route and direction, the page shows it under the scheduled times, marked live, with the time it was checked; where it has none, or cannot be read, the page says the times are timetable estimates. The City lists that feed as decommissioned, so it may stop; the newer TTC GTFS Realtime feed cannot be read from a browser. Not shown on the simulated examples. Only the stop code is sent to the NextBus host (webservices.umoiq.com), never the alert or your destination; like any web request it also sees your IP address. The verdict still uses the timetable, with one safety gate: if a live prediction shows the bus the verdict relies on leaving 5 or more minutes after its timetabled time, a warning appears under the verdict saying what that bus would do to the comparison and not to rely on a switch verdict (`liveCheck` in `logic.js`, with unit and browser tests). The verdict itself is not changed by it.
6. **Plan B extras, behind a fold.** An elevator or escalator outage at the delay station or your destination shows as a warning under Plan B, from the TTC's accessibility alerts feed, copied by the same job (Open Government Licence Toronto); the page does not invent step free routes. Inside "More: route delay history and Bike Share": how often each Plan B route logged a delay of 10 minutes or more (TTC bus and streetcar delay logs, Jan to Sep 2026, per scheduled trip), shown only because a check passed first: each route's 2025 rate ranked the routes' 2026 rates well (rank correlation 0.87 over 200 routes with at least 200 trips a week) and was a closer guess than the network average (average error 0.08 against 0.17 per 100 trips). These count reported incidents, not on time performance, and do not change the estimate. Then Bike Share Toronto stations within 400 metres of the delay station and the destination, with live bikes and open docks read in your browser from the Bike Share Toronto GBFS feed (no ride time is estimated; snow, luggage or a stroller can make cycling the wrong choice). The weather panel of the last version was cut: it was not part of the forecast and had not been tested as a predictor.

## What the number means

The TTC logs each incident with the minutes it delayed subway service. In full: among comparable TTC incidents with a recorded delay of 1 minute or more, the model estimates the chance the recorded delay lasts 10 minutes or more (23% in the Kipling example). This is not the chance your current alert causes that delay, or your remaining wait. Comparable means delays with this cause, station, line, time of day and day type, as the model weighs them. Records with 0 minutes of delay (30,515 on Lines 1, 2 and 4, 65% of the records) are left out, so the chance is conditional on the incident having a recorded delay at all. Counting them gives lower chances (the Kipling example: 15% instead of 23%); see "Zero minute records" under Honest results for both views.

The risk bands are a plain language summary: under 15% low, 15% to 35% moderate, 35% and up high. The wait or switch line under them compares the expected logged delay with the best scheduled switch to your destination (see Honest results).

## The model

- **Data:** TTC Subway Delay Data since 2025 (City of Toronto Open Data, refreshed Oct 26, 2026). The copy used here has 47,915 records from Jan 1, 2025 to Sep 30, 2026; I have not checked it against the TTC's internal logs. Kept: Lines 1, 2 and 4, delays over 0 minutes (16,548 delays). Target: 10 minutes or more.
- **Causes a rider can see:** the TTC's 124 delay codes are grouped into the 15 causes alerts actually say, such as "medical emergency", "person at track level" or "signal problem".
- **Drift:** long delays became rarer in 2026 (about 19% of delays in early 2025, about 12% in summer 2026). Each delay is weighted by age with a 180 day half life, and the output is recalibrated (Platt scaling).
- **One process, tested as shipped:** the base model is trained on everything before the last 91 days, Platt scaling is fitted on those 91 days, and that pair is shipped with no refit. The shipped model: base trained through Jul 1, 2026, recalibrated on Jul 2 to Sep 30, 2026.
- **Rare causes:** cause features get lighter shrinkage than station features, so a rare but serious cause such as a personal injury at track level is not pulled towards average.

## Honest results
**In brief:**
1. **Ranking:** better than the cause alone (AUC 0.751 against 0.727) and level with the first model (0.751 against 0.753, not distinguishable).
2. **Calibration:** expected calibration error 1.8 points pooled, against 2.4 for the first model (distinguishable). Calibration in the large (average forecast against actual share of 10+ delays) by period: 18% against 18%, 17% against 14% and 14% against 12%, so forecasts ran high in 2026 as long delays kept getting rarer. A fresher recalibration, fitted on earlier data and checked on later, did not pass and is not shipped.
3. **Decisions, what a rider would see:** the card says switch only when switching still wins with the bus 5 minutes late, so it rarely does. In a simulation on 7,455 test delays it said switch on 107 of 13,174 trips (a delay and a direction of travel, 0.8%; 20 of 551, 3.6%, on delays of 20 minutes or more). On those calls it saved about 7.9 minutes each (5.5 to 10.4) with buses on schedule and 2.9 with the bus 5 minutes late, and lost 14.5 when the first bus was missed; 17% of the calls lost time even on schedule. Spread over all delays that is 0.06 minutes per delay (0.04 to 0.08), and 0.95 on delays of 20 minutes or more (0.54 to 1.43). These are simulated minutes, not measured rider savings. Against switching on the timetable alone, the late bus check gives up 0.10 minutes per delay when buses run on time and loses less when they do not; averaged over eight equally weighted what if scenarios, whose real frequencies are unknown, it came out 0.63 minutes per delay ahead in the simulation. That average compares two rules; it is not a rider benefit. Exploratory.
4. **Reading alerts:** on the 51 newest of 102 real TTC alerts (Oct 15 to Nov 15, 2026, Toronto time), held out while the parser was fixed, it named the right station in 98% (50 of 51) and the right cause in 98% (45 of 46). Planned work: 7 of the 102 alerts, 4 in the held out half, of which it caught 3 (75%, too few to say much). Before any fixes it named the right station in 87% of all 102. After three more fixes all 102 are right, but that is on the alerts used to fix it, so it is not the headline. The parser is frozen at the submission tag; alerts first seen after the freeze are a fresh test set (none yet).
5. **Live times:** where the TTC's older NextBus feed has a live prediction for a Plan B stop, it is shown beside the timetable; everything else is a timetable estimate, and the verdict uses the timetable. A live safety gate warns under the verdict when a live prediction shows the bus the verdict relies on leaving 5 or more minutes after its timetabled time. Only the stop code is sent to the NextBus host. No rider testing has been done; a 10 minute script for five riders is ready in docs/rider-check.md, with no results yet.
6. **What the chance is conditional on:** incidents with a recorded delay of 1 minute or more. The 30,515 records with 0 minutes of delay on Lines 1, 2 and 4 are left out. A sensitivity check that keeps them is below ("Zero minute records"): the Kipling example would be 15% instead of 23%.

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

| Evaluation period (scored on, later) | Settings picked on (earlier window) | Delays | AUC, Wait or Walk (cause only) | 10+ forecast vs actual | Late bus check (shipped) against always wait: all delays / 20+ minutes | Status |
|---|---|---|---|---|---|---|
| Jan 1 to Mar 31, 2026 | Oct 2 to Dec 31, 2025 (margin 0.5 minutes below) | 2,576 | 0.724 (0.685) | 18% vs 18% | 0.06 saved (0.03 to 0.10) / 0.56 saved (0.08 to 1.25) | Exploratory: looked at while the rules were chosen |
| Apr 1 to Jun 30, 2026 | Dec 31, 2025 to Mar 31, 2026 (margin 1 minute above) | 2,631 | 0.758 (0.729) | 17% vs 14% | 0.08 saved (0.04 to 0.12) / 1.61 saved (0.78 to 2.63) | Exploratory: looked at while the rules were chosen |
| Jul 1 to Sep 30, 2026 | Apr 1 to Jun 30, 2026 (margin 0.5 minutes above) | 2,248 | 0.769 (0.760) | 14% vs 12% | 0.03 saved (level to 0.06) / 0.71 saved (level to 1.69) | Exploratory: looked at while the rules were chosen, and it informed the approach |

**The wait or switch rule, picked on earlier data.** The old rule said to check another route whenever the 10+ chance was 35% or more. Two rules were tried in its place, each with its setting picked on earlier data only (each test period's own recalibration window) and then tested on that period in the station simulation described below. *20+ chance rule:* switch when the 20+ minute chance reaches a threshold. *Expected cost rule:* switch when the expected logged delay (the three bands times the average logged minutes in each range, capped at 60) minus the station's scheduled switch cost reaches a margin. Average minutes lost per delay, intervals resampling whole days:

| Delays | Always wait | Cause only at 35% | Old rule: 35% | 20+ chance rule | Expected cost rule, timetable only (r6 to r9) | Expected cost rule with the late bus check (shipped) | Shipped against always wait |
|---|---|---|---|---|---|---|---|
| All (7,455) | 6.56 | 6.71 | 6.91 | 6.53 | 6.40 | **6.50** | 0.06 saved (0.04 to 0.08) |
| Under 10 minutes (6,363) | 4.45 | 4.67 | 4.86 | 4.47 | 4.49 | **4.44** | 0.01 saved (level to 0.01) |
| 20+ minutes (309) | 34.02 | 32.42 | 32.34 | 32.89 | 30.94 | **33.07** | 0.95 saved (0.54 to 1.43) |
| 30+ minutes (139) | 46.64 | 43.63 | 43.48 | 44.47 | 41.83 | **45.30** | 1.34 saved (0.53 to 2.29) |

On these periods the expected cost rule was clearly better than the old rule, the cause only rule (0.31 minutes saved, 0.24 to 0.38) and always waiting, so it was adopted (versions r6 to r9 switched on the timetable alone), with its margin (0 minutes) picked the same way on the shipped model's own recalibration window; the 20+ chance rule was not. Since r10 it ships with the late bus check (last two columns). It wins by switching less on short delays and more on long ones. These are simulated minutes: the intervals hold only under the simulation's assumptions (Tue Nov 17, Sat Nov 21 and Sun Nov 22, 2026 schedule days applied to earlier delays, logged delay minutes as the cost of waiting, alternatives that run as scheduled). On the page the switch cost uses your destination when it is on the same line; in the simulation it is the first station past the delay, averaged over both directions.

**Exploratory, not confirmed.** The expected cost rule was chosen over the 20+ chance rule after both were compared on these same evaluation periods, so its advantage is exploratory: the intervals above do not account for that choice, and it has not been confirmed on an untouched period (none exists yet; see the forecast log below). Within the rule, the margin picked on each earlier window varied: 0.5 minutes below, 1 minute above and 0.5 minutes above; the shipped margin is 0.

**Too close to call, tested.** The verdict can say "too close to call" when the expected delay and the timetable switch are within a break even band; inside the band the advice is to wait. For each evaluation period the band was picked on its earlier window (the widest of 0.5 to 5 minutes costing at most 0.01 minutes per delay there): 2, 0.5 and 0.5 minutes. On the later periods it was level with the shipped rule as scheduled (0.00 minutes per delay, 0.02 lost to 0.02 saved) and lost less when buses ran 5 minutes late (0.10 saved, 0.07 to 0.12) or a departure was missed (0.57 saved, 0.48 to 0.65), so it passed the rule set in advance. On delays of 20 minutes or more it was worse as scheduled (0.51 minutes, 0.15 to 0.97). Picked the same way on the shipped model's own window, the band is 0 minutes, so the page never says "too close to call": every comparison ends in wait or switch. Narrow margins are handled by the late bus check below instead: when switching wins by the timetable but by less than 5 minutes, the card says "Narrow margin", gives the minutes, and says wait, because a bus 5 minutes late would wipe out the gain. Every verdict also shows a break even line and the timetable risk for that trip: the same switch with the bus on time, 5 minutes late, and missed (with the next scheduled departure).

**What a rider would see: how often it says switch, and what those calls gain.** The minutes per delay above are spread over every delay, most of which get a wait call. This counts the switch calls of the shipped rule itself (`switchCalls` in `data/decision_checks.json`): each trip is one test delay and one direction of travel along the line (13,174 trips; 7,483 had a scheduled alternative within 3 hours). The rider decides from the schedule; the rows say what really happens after that. A recomputation of the same simulation, with no new rule. Minutes gained per switch call (95% intervals, whole days resampled):

| What really happens | Per switch call, all delays | Switch calls that lost time | Per switch call, 20+ minute delays |
|---|---|---|---|
| How often it says switch | 107 of 13,174 trips (0.8%) | | 20 of 551 trips (3.6%) |
| As scheduled | 7.9 saved (5.5 to 10.4) | 17% | 29.3 saved (23.7 to 35.1) |
| Bus 5 minutes late | 2.9 saved (0.5 to 5.4) | 52% | 24.3 saved (18.7 to 30.1) |
| Bus 10 minutes late | 2.1 lost (4.5 lost to 0.4 saved) | 75% | 19.3 saved (13.7 to 25.1) |
| First scheduled departure missed | 14.5 lost (11.2 to 18.0) | 86% | 1.2 lost (8.1 lost to 5.3 saved) |
| Walking at 1.0 m/s | 4.1 saved (1.1 to 7.2) | 27% | 21.8 saved (11.6 to 31.1) |
| 2 minutes to board | 0.3 saved (3.3 lost to 3.7 saved) | 50% | 20.4 saved (9.6 to 29.8) |
| 3 minutes to board | 5.6 lost (1.9 to 9.3) | 70% | 17.1 saved (7.1 to 26.1) |
| All of these at once | 33.1 lost (28.4 to 38.2) | 96% | 21.8 lost (10.8 to 35.4) |

Read honestly: the switch calls are rare and worth about 7.9 minutes each when the bus runs as scheduled, about 2.9 with the bus 5 minutes late, and a loss of about 14.5 when the first bus is missed. 17% of them lose time even on schedule, because the delay turned out short. On delays of 20 minutes or more they hold up unless the bus is missed. Simulated minutes, not measured rider savings.

**The late bus check: shipped.** Switch only if switching still wins with the bus 5 minutes late. The 5 minutes was fixed, not tuned. It was scored on each period's earlier window and on the later test period. The rule for shipping, set before that run: not worse than the timetable only rule averaged over all eight stress scenarios on the test periods. It was added after a stress test of the timetable only rule was known, so it is exploratory. Minutes per delay, 7,455 test delays (95% intervals, whole days resampled):

| What really happens | Late bus check against always wait | Late bus check against timetable only rule, test periods | Same, earlier windows | Same, 20+ minute delays |
|---|---|---|---|---|
| As scheduled | 0.06 saved (0.04 to 0.08) | 0.10 lost (0.06 to 0.14) | 0.11 worse | 2.13 lost (1.38 to 3.01) |
| Bus 5 minutes late | 0.02 saved (level to 0.04 saved) | 0.16 saved (0.12 to 0.20) | 0.13 better | 1.74 lost (1.10 to 2.51) |
| Bus 10 minutes late | 0.02 lost (0.03 lost to level) | 0.42 saved (0.37 to 0.47) | 0.38 better | 1.35 lost (0.80 to 2.03) |
| First scheduled departure missed | 0.11 lost (0.08 to 0.14) | 1.25 saved (1.14 to 1.37) | 1.20 better | 0.18 saved (0.39 lost to 0.71 saved) |
| Walking at 1.0 m/s | 0.03 saved (0.01 to 0.05) | 0.05 saved (0.01 lost to 0.11 saved) | 0.03 better | 2.07 lost (1.35 to 2.89) |
| 2 minutes to board | level (0.02 lost to 0.03 saved) | 0.32 saved (0.24 to 0.40) | 0.28 better | 2.06 lost (1.34 to 2.86) |
| 3 minutes to board | 0.04 lost (0.01 to 0.07) | 0.61 saved (0.52 to 0.71) | 0.55 better | 1.61 lost (1.04 to 2.27) |
| All of these at once | 0.24 lost (0.18 to 0.30) | 2.30 saved (2.09 to 2.52) | 2.19 better | 1.44 saved (0.62 to 2.42) |
| Average of the eight | | 0.63 saved (0.55 to 0.70) | 0.58 better | 1.17 lost (0.67 to 1.79) |

Read honestly: when buses run on time it gives up 0.10 minutes per delay against the timetable only rule (2.13 on delays of 20 minutes or more), because it switches less. In return it loses far less when the bus is late, boarding is slow or a departure is missed, and the earlier windows show the same trade (0.58 minutes per delay better on average). Averaged over the eight scenarios it is 0.63 better (0.55 to 0.70) on all delays but 1.17 worse (0.67 to 1.79) on delays of 20 minutes or more. It passed and ships. Both worked examples keep their call: Kipling waits, and St George switches, winning by about 11 minutes. Per period, as scheduled, it saves 0.06, 0.08 and 0.03 minutes per delay against always waiting. The eight scenarios are equally weighted what ifs, not measured frequencies, so the 0.63 compares two rules in a simulation; it is not a rider benefit.

**The late bus check, reconsidered after review: kept, unchanged.** It passed the rule set before its run; a margin picked separately for late buses (below) lands in the same place, level with it as scheduled and with buses 5 minutes late; and going back to the timetable only rule would be one more change made after seeing results. The cost is stated plainly: on delays of 20 minutes or more it gives up 2.13 minutes per delay as scheduled, and 1.17 averaged over the eight scenarios, which is where switching matters most. No extra rule for long delays was added: it would be tuned to the one place the check hurts and could not be tested independently. The model, the rule and the parser are now frozen (see "Freeze and tag").

**A margin picked for late buses: tested, not shipped.** For each test period the margin was picked on that period's earlier window as the one with the fewest minutes if every bus ran 5 minutes late (margins 3.5, 12.5 and 4 minutes), then the full stress test was run with it. It had to be at least as good as the timetable only rule as scheduled and lose less under slippage. Minutes saved per delay against always waiting, all 7,455 delays (95% intervals, whole days resampled):

| What really happens | Late bus margin against always wait | Late bus margin against the late bus check (shipped) |
|---|---|---|
| As scheduled | 0.06 saved (0.04 to 0.08) | level (0.01 lost to 0.02 saved) |
| Bus 5 minutes late | 0.02 saved (level to 0.04) | level (0.02 lost to 0.01 saved) |
| Bus 10 minutes late | 0.03 lost (0.01 to 0.04) | 0.01 lost (level to 0.02) |
| First scheduled departure missed | 0.14 lost (0.11 to 0.18) | 0.03 lost (0.01 to 0.06) |
| Walking at 1.0 m/s | 0.03 saved (0.01 to 0.06) | level (0.01 lost to 0.02 saved) |
| 2 minutes to board | 0.02 lost (0.05 lost to 0.01 saved) | 0.02 lost (level to 0.05) |
| 3 minutes to board | 0.07 lost (0.04 to 0.10) | 0.03 lost (level to 0.06) |
| All of these at once | 0.30 lost (0.24 to 0.36) | 0.05 lost (0.01 to 0.10) |

It lands in almost the same place as the late bus check (level as scheduled and with buses 5 minutes late), so two different guards against late buses agree. Like the late bus check it is worse than the timetable only rule as scheduled (0.10 minutes per delay, and 2.17 minutes per delay of 20 minutes or more, 1.43 to 2.98), so by its rule set in advance it was not shipped. The late bus check would have failed that same rule; it was judged on the average of all eight scenarios instead, a rule set after this result was known.

**Drift in the expected delay.** The averages in each range come from the base training data, and long delays became rarer in 2026. They barely moved: for 20+ minutes, 33.9 minutes in the base data against 32.0, 35.2 and 34.0 in the windows just before each period. Using those recent averages instead (with the margin picked again on the same earlier window) changed the simulated minutes by 0.01 per delay, not distinguishable, so the shipped averages are kept. The expected delay does run high in the later periods (6.4 against 5.95 logged minutes on average in Jul to Sep, 7.1 against 6.4 in Apr to Jun) because the forecasts themselves run high, not because of the averages.

**Forecast log, a plan.** `docs/forecast-log.md` gets one dated line each time the City publishes newer delays: the frozen shipped model scored, never refit, on delays after September 30, 2026, against both baselines (`scripts/forecast_log.py`). Today it has one line: no new delays yet, so no score.

**Alert time forecast log.** Each run of the alerts job now also saves the forecast for every new subway alert as the page would have shown it then (time of day, the alert as read, the 5+, 10+ and 20+ chances, the model it came from), one line per alert in `data/alert_forecasts.jsonl`, never edited (`scripts/log_forecasts.mjs`). Lines logged more than 40 minutes after the alert was first seen are marked backfilled; the first two are. A sanity check (`scripts/check_forecast_log.mjs`, in the tests and in the job) checks every line: unique ids that match the alert history, chances in order, no forecast for planned work, the backfilled flag, and the time of day and day type against the first seen time. So far: 4 alerts, 1 with a forecast (Museum, medical emergency: 74% for 5+, 23% for 10+, 4% for 20+), 3 planned work, 2 backfilled; all checks pass. Too few to compare with anything, so no comparison is made. A sanity check (`scripts/check_forecast_log.mjs`, in the tests and in the job) checks every line: unique ids that match the alert history, chances in order, no forecast for planned work, the backfilled flag, and the time of day and day type against the first seen time. So far: 4 alerts, 1 with a forecast (Museum, medical emergency: 74% for 5+, 23% for 10+, 4% for 20+), 3 planned work, 2 backfilled; all checks pass. Too few to compare with anything, so no comparison is made. Once the City publishes delays for those dates they can be matched and scored. It has not been scored, so it makes no accuracy claim.

**Why forecasts run high, and a fix that did not pass.** Two measures, named: calibration in the large is the average forecast against the actual share; calibration error is the expected calibration error, the gap in seven forecast bands weighted by delays. The pooled 1.8 points hides the direction: by period the 10+ forecasts averaged 18% against 18% actual (Jan to Mar), 17% against 14% (Apr to Jun) and 14% against 12% (Jul to Sep); in the 5 minute underway check, 34% against 31%. The share of 10+ delays kept falling through 2026 (19% in January, 15% in April, 11% in July), and the recalibration averages the 91 days before each period, so it lags a falling trend. Tested (`scripts/calibration_check.py`): shift each period's forecasts so they match the actual share in only the last 30, 46 or 61 days of its earlier window, then score on the later period. Rule: ship only if the 10+ gap shrinks in all three periods and pooled log loss is no worse for any band; this rule was written after a first look at the numbers. None passed. Each window helps Apr to Jun (17.3% down to 15.1% to 16.6%, against 13.7% actual) but pushes Jan to Mar off (18.0% to 17.0% to 19.1%, against 18.0%) and leaves Jul to Sep about where it was (13.4% to 13.7%, against 12.0%). So the forecasts ship as they are, with this note.

**Reading the alert, tested.** 102 real TTC alerts posted by @TTCnotices from August 8 to November 15, 2026, Toronto time (the last at 9:12 p.m. on November 15, which is November 16 in UTC), each labelled by hand from the text alone by one labeller with no second check (`data/alerts_labelled.json`, scored by `scripts/parser_eval.mjs`, which runs in CI). The older 51 (to October 15) were used to find and fix errors; the newer 51 were held out. **Headline: on the held out 51, after fixes from the older half only, 98% for stations (50 of 51) and 98% for causes (45 of 46).** 7 of the 102 are planned work (3 older, 4 newer); the held out planned work recall of 75% is 3 of 4, too few to say much. The first version named the right station in 87% of all 102 (13 wrong) and the right cause in 92% (99% of the causes it named were right), and caught 6 of 7 planned work alerts. Fixes from the older half: a station name inside a longer one, such as St Clair in St Clair West; "Vaughan"; "operational problem", "communication issue" and "TPS investigation". Three more fixes for the errors left in the newer half make all 102 right, but that score is on the alerts used to fix it, so it is not independent and not the headline. Station counts as right when the one station named is read, or, for an alert naming two or more, when the choice lists exactly those stations.

| Alerts and parser version | Alerts | Line right | Station right | Cause precision / recall | Planned work precision / recall |
|---|---|---|---|---|---|
| All 102, first version | 102 | 100% | 87.3% (13 wrong) | 98.9% / 91.5% | 100% / 85.7% |
| Older 51, first version | 51 | 100% | 92.2% (4 wrong) | 100% / 91.7% | 100% / 100% |
| Newer 51 (held out), first version | 51 | 100% | 82.4% (9 wrong) | 97.7% / 91.3% | 100% / 75% |
| **Newer 51 (held out), after fixes from the older half: the headline** | 51 | 100% | **98% (1 wrong)** | 97.8% / 97.8% | 100% / 75% |
| All 102, after the last three fixes (not independent, not the headline) | 102 | 100% | 100% (0 wrong) | 100% / 100% | 100% / 100% |

**Zero minute records: a sensitivity check.** The shipped models are fitted on incidents with a recorded delay of 1 minute or more, so every chance on the page is conditional on the incident having a recorded delay. The City log also has 30,515 records with 0 minutes on Lines 1, 2 and 4 (30,515 of 47,063, 65%; for a person at track level, 436 of 999). `scripts/zero_minute_check.py` runs the same pipeline (features, age weighting, recalibration, test periods) with those records kept as "not 10+ minutes", and changes nothing in the app. Forecast against actual share on the test periods:

| Chance of | Shipped, among incidents with a recorded delay (what the page shows; 7,455 test incidents) | Shipped, read as a chance per logged incident, 0 minute records included (21,771) | Refit with 0 minute records kept | Kipling example: shipped / refit |
|---|---|---|---|---|
| 5+ minutes | 50.3% vs 47.9% (AUC 0.702) | 53.4% vs 16.4% (AUC 0.566) | 18.5% vs 16.4% (AUC 0.665) | 40% / 26% |
| 10+ minutes | 16.4% vs 14.6% (AUC 0.751) | 19.4% vs 5.0% (AUC 0.667) | 5.8% vs 5.0% (AUC 0.729) | 23% / 15% |
| 20+ minutes | 4.6% vs 4.1% (AUC 0.773) | 6.2% vs 1.4% (AUC 0.715) | 1.6% vs 1.4% (AUC 0.763) | 10% / 6% |

Read honestly: the page's chances are right only as chances among incidents with a recorded delay. Read as a chance for any logged incident they run far too high (19.4% forecast against 5.0% actual for 10+). The refit answers that other question well (5.8% against 5.0%). The page keeps the positive delay model and says so on the card, on the assumption that a rider reading a delay alert is usually in an incident that delays service; that assumption has not been tested.

**Freeze and tag.** The model, the wait or switch rule (with the live safety gate) and the alert parser are frozen at the tag `slay-hacks-submission`, which is the code judged. `scripts/freeze_check.mjs` runs in the tests and fails if `logic.js`, `data/model.json`, `data/policy.json` or `data/decision_checks.json` changes from the hashes in `data/freeze.json`; any later change has to be a bug fix listed in `docs/freeze.md`. The automated "Copy TTC subway alerts" commits change only data files and never these. The parser freeze time is in `data/freeze.json` (November 15, 2026, 11:02 p.m. Toronto time). Alerts the alerts job first sees after it are a fresh test set that was never used to fix the parser: counted in `data/parser_fresh.json` by `scripts/parser_fresh.mjs` on every run, and scored once labelled by hand in `data/alerts_fresh_labels.json` (ideally by someone else, from the text alone). None yet, so no fresh score.

**Accessibility.** Automated checks run on every change: axe-core finds no WCAG 2.1 A or AA violations at phone and desktop widths with every fold open; a keyboard only run tabs to an example, opens it with Enter, presses the underway buttons with Space and picks a station choice with Enter, with focus visible and moved to the result; every control has a name; the call is announced by one short status line; headings do not skip levels. No manual screen reader test has been done.

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
python3 scripts/calibration_check.py /tmp/ttc
python3 scripts/zero_minute_check.py /tmp/ttc
node scripts/parser_eval.mjs --write
python3 scripts/frozen_test.py /tmp/ttc
python3 scripts/forecast_log.py /tmp/ttc
python3 scripts/build_bikeshare.py
python3 scripts/surface_delays.py bus.csv streetcar.csv /tmp/ttc/gtfs.zip
```

Run `build_planb.py` first: the station simulation in `train.py` reads its output. `train.py` writes `data/model.json` (the 10+ model plus the 5+ and 20+ models), `data/metrics.json` (evaluation periods, calibration bands, bootstrap intervals by delay and by day, the 5+ and 20+ results, station by cause pooling, settings sensitivity, decision value and both simulations) and `data/parity.json`. It takes about 15 minutes. `build_planb.py` writes `data/planb.json` and `data/planb_times.json` (departure times and the service calendar). `check_planb.py` rewrites the hand check report from the raw schedule. `choose_policy.py` picks the wait or switch margin on the shipped model's recalibration window and writes `data/policy.json`. `frozen_test.py` downloads the newest delay file and scores the frozen shipped model once on delays after its training data, writing `docs/frozen-test-<date>.json`; on November 15, 2026 there were none. `decision_checks.py` runs the drift check and the stress test (`data/decision_checks.json`). `forecast_log.py` adds a dated line to `docs/forecast-log.md`. `build_bikeshare.py` saves the Bike Share stations near each subway station (`data/bikeshare_near.json`; live counts are never stored). `surface_delays.py` reads the TTC bus and streetcar delay logs (download both CSVs from City of Toronto Open Data first), runs the earlier against later check and writes `data/surface_delays.json`. `decision_checks.py` also tests the too close to call band and writes the per period results. It also scores the late bus check on the earlier windows and the test periods (`lateSafe`). `calibration_check.py` tests the fresher recalibration (`data/calibration_check.json`). `parser_eval.mjs` scores the alert reader on `data/alerts_labelled.json` and writes `data/parser_eval.json`. `build_planb.py` now also keeps each stop's GTFS stop code, which the live predictions use. The alerts job runs `scripts/log_forecasts.mjs`, `scripts/check_forecast_log.mjs` and `scripts/parser_fresh.mjs` after each copy. `zero_minute_check.py` repeats the pipeline with the 0 minute records kept (`data/zero_minute_check.json`), and `decision_checks.py` also counts the switch calls (`switchCalls`).

## Tests

```
for t in tests/*.mjs; do node "$t"; done
node scripts/parser_eval.mjs --check
node scripts/freeze_check.mjs
node scripts/check_forecast_log.mjs
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/consistency_check.py
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
- The late bus check (switch only if it still wins with the bus 5 minutes late; narrow margins say wait) and the timetable risk figures for one trip.
- Alert reading on 102 real labelled TTC alerts (`scripts/parser_eval.mjs --check` fails CI if any is misread) and the parser fixes it led to: names inside longer names, Vaughan, operational problem, communication issue, TPS, power shut off at track level, Line 4 Sheppard, limited nightly service.
- The alert time forecast log: a new alert gets 5+, 10+ and 20+ chances in order, planned work gets none, two stations get one forecast each, a late log is marked backfilled.
- The live safety gate (`liveCheck`): no warning when the feed cannot be read, has no prediction, or agrees; a warning when the first live bus you could reach leaves 5 or more minutes after the timetabled one. The browser check runs it with a fixture where the live 26 is 12 minutes later than the 5:35 p.m. bus: the card warns that waiting would be better by about 1 minute and not to rely on the switch verdict.
- The freeze (`scripts/freeze_check.mjs`: the frozen files match `data/freeze.json`), the forecast log sanity check (`scripts/check_forecast_log.mjs`) and the fresh parser test count (`scripts/parser_fresh.mjs`).
- Sensitivity, not a test: `scripts/zero_minute_check.py` (the 0 minute records) and the switch call counts in `scripts/decision_checks.py` are rerun by hand after training.
- The too close to call band (0 on the page) and break even slack, the shipped band in `data/policy.json`, the per period results, and the shapes of the alert history, accessibility, Bike Share and route delay files (the route line is shown only if its check passed).
- No leakage: every evaluation period keeps base, recalibration and test periods in order, every decision rule setting is picked before its test period, and the shipped model's recalibration comes after every test period's; bootstrap intervals (by delay and by day) bracket their values; the published claims about which differences are distinguishable match the numbers.

A real browser check clicks every example button at 390 px and 1440 px, runs the ambiguous alert and mismatch flows, clearing, the card labels and safety line, Plan B with the clock fixed at 5:38 p.m. (the 5:39 bus is not offered, the wait or switch line compares the best switch, no Blue Night line), Dec 7, Dec 20, 3 a.m. (Blue Night route 300 shown) and Dec 22, a minute by minute refresh across midnight, the examples on the simulated clock on Nov 16 and with the date faked as Jan 5, 2027 (both still work; live time shows the schedule ended message), the already underway buttons, planned work with no forecast, the alerts copy (shown with its time, one tap fills the alert, missing copy leaves paste working), a shared link, the load error retry, the stale alerts banner (job status unknown, a run 10 minutes ago with an unchanged feed, a run 3.5 hours ago), the alerts seen this month strip, the elevator and escalator warning, the route delay history and Bike Share extras (and what happens when they fail; the weather panel is gone), live bus predictions with a fixture (shown, a feed error labelled timetable only, none on the simulated example), the timetable risk lines for the St George example, a keyboard only flow (Tab to an example, Enter, Space on the underway buttons, Enter on a station choice, visible focus, focus moved to the result, one short status line announced, every control named, no skipped heading levels), and axe-core (Mozilla Public License 2.0, installed in CI, not stored here) checking WCAG 2.1 A and AA rules at both widths with every fold open; it found scrollable tables that could not be reached by keyboard, now fixed. axe-core cannot prove a page is accessible:

```
pip install playwright && python3 -m playwright install chromium
python3 tests/browser_check.py https://alenzacodes.github.io/wait-or-walk/
```

## Limits

An estimate, not a promise. Rare causes rest on few cases (fire or smoke: 94 delays; personal injury at track level: 34), and the page says so. The alert is pasted, or taken from a copy of the TTC feed made every 30 minutes, which can be late (the page marks it as possibly out of date after 90 minutes); planned work and slow zones get no forecast. Plan B uses straight line distance and the regular schedule, not live detours or shuttle buses; every time shown is a timetable estimate, not real time, except live predictions from the TTC's older NextBus feed, which are marked live and may stop (the City lists that feed as decommissioned). The route delay history counts logged incidents, not on time performance. No rider testing has been done; a 10 minute script for five riders is in docs/rider-check.md, with no results yet. Data: City of Toronto Open Data under the Open Government Licence Toronto.

## What's next

- Score the "already underway" setting against real alert times once the copied feed has a few months of alerts to match to the delay log.
- Step free routes between stops, beyond the elevator and escalator warning.
- Live arrival times from the TTC's new GTFS Realtime feed (it cannot be read from a browser, so it needs a small relay), and running the 10 minute rider check in docs/rider-check.md with five riders.
- Score the alert time forecast log once the City publishes delays for the dates it covers.

## Safety

Always follow TTC staff and announcements. Wait or Walk is a planning aid for riders on a platform, not for decisions about leaving a train or evacuating.

Privacy: no accounts and no tracking. Alerts are read in your browser. For live bus predictions only the Plan B stop code is sent to the NextBus host (webservices.umoiq.com). For live bus predictions only the Plan B stop code is sent to the NextBus host (webservices.umoiq.com). The last destination you chose is kept only in your own browser, and "Copy a link to this result" puts the alert in the link itself, not on any server.

## Licence

Code: MIT, copyright John Khan. See `LICENSE`. Data: City of Toronto Open Data, TTC Subway Delay Data since 2025 and TTC Routes and Schedules (GTFS, files dated Oct 20, 2026), both under the Open Government Licence Toronto (https://open.toronto.ca/open-data-licence/). Also under that licence: TTC GTFS Realtime subway and accessibility alerts, and TTC Bus Delay Data and TTC Streetcar Delay Data. Bike Share Toronto station data from its live GBFS feed (Open Government Licence Toronto in the City catalogue; the live feed is listed as CC BY 4.0 by the Mobility Database). Live bus predictions: the TTC's NextBus feed on UmoIQ ("All data copyright Toronto Transit Commission"), listed by City of Toronto Open Data under the Open Government Licence Toronto as TTC Real Time Next Vehicle Arrival (NVAS), read in your browser. Testing uses axe-core (Mozilla Public License 2.0) and Playwright. Not affiliated with or endorsed by the TTC.

SLAY HACKS began November 7, 2026, and all of Wait or Walk was built after that. A private prototype script came first, to test the idea; the public repo's first commit (git log --reverse) is from 6:08 a.m. Toronto time on November 15, 2026, and every change since is in its history. No application code came from earlier projects: a line by line comparison with my other GitHub repos found only boilerplate in common (page colour variables and a few base style rules, the standard module wrapper, test imports). Data: City of Toronto Open Data, TTC Subway Delay Data since 2025 and TTC Routes and Schedules (GTFS), both under the Open Government Licence Toronto. Libraries: pandas, NumPy, SciPy and scikit-learn for training.
