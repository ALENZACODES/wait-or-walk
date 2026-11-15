## Worked example
Alert pasted on a weekday at 5:30 p.m., heading to Jane: *"Line 2 Bloor-Danforth: Delays at Kipling due to a person at track level."*
- **Read from the alert (tagged for checking):** Line 2, Kipling, person at track level.
- **Estimated chance:** 23% that an incident like this delays subway service 10 minutes or more (moderate risk). Beside it: 40% for 5+ minutes, 10% for 20+ minutes. Under it: "This predicts a logged service delay category, not how many minutes you personally have left to wait."
- **Drift correction:** 29% before recalibration, 23% after.
- **Why 23% and not 48%:** 48% is every logged delay with this cause since January 2025 (270 of 563). The estimate adjusts that for the station, the line, the time of day and the drop in long delays in 2026 (in the latest 91 days, 41% of 80 delays with this cause ran 10 minutes or more). The cause raises the odds; Kipling and the evening rush lower them.
- **Plan B, earliest scheduled arrival first (may not be running right now):** 149 Etobicoke-Bloor from Kipling Station (10 m, about a 1 minute walk, accessible boarding listed): next you can catch 5:39, 6:07 and 6:35 p.m.; by the schedule at Jane about 5:57 p.m. Then 40 Junction-Dundas West (100 m): next you can catch 5:53 p.m.; at Islington about 5:58, then Line 2 to Jane about 6:04 p.m. if the subway runs normally there.
- **Wait or switch: wait.** Incidents like this delay service about 8 minutes on average, by this estimate; by the schedule the best Plan B gets you to Jane about 19 minutes later than an on time subway, which is more. This uses the expected cost rule described under Honest results.
- **Safety first:** always follow TTC staff and announcements. This is a planning aid for riders on a platform, not for decisions about leaving a train or evacuating.

## Overview
Wait or Walk answers the question every Toronto subway rider asks when the train stops: will this be two minutes or twenty? Paste the TTC alert and it gives the estimated chance of a 5, 10 or 20 minute delay, the reasons behind it, and scheduled buses, streetcars and LRT within 300 metres that head where you are going, ordered by the arrival the schedule allows, counting only departures you can still catch, and says whether waiting or switching looks better by the schedule.

## Problem and solution
TTC alerts say what happened, not how long it will take. Riders guess, and guessing wrong costs real time: people wait twenty minutes for a fire investigation to clear, or leave a platform for a passenger alarm that would have cleared in three. City of Toronto Open Data publishes a TTC subway delay log starting January 1, 2025, with each incident's cause, station and minutes of delay; the copy used here has 47,915 records up to September 30, 2026. Wait or Walk turns those records into a risk estimate you can use on the platform, for daily commuters, students, shift workers and visitors who do not know the surface routes.

## How it works
- **Reading the alert:** you paste or type the alert yourself; the page does not fetch live alerts. It is read by hand written rules, not a trained model. Regular expressions find line names ("Line 2", "Bloor-Danforth"), keyword patterns find 14 causes in a fixed order with the most specific first ("person at track level" before "track"), and a search finds the 71 station names plus a few older names, such as Dundas for TMU. Values read are tagged "from alert, please check".
- **No number until it is clear:** two stations named, a two line station without a line, or a station that is not on the chosen line (Union on Line 2) all give no number until you choose. Clearing the alert clears what it filled in. Automated tests cover each case.
- **Three calibrated models:** logistic regressions for 5+, 10+ and 20+ minutes on cause (the TTC's 124 delay codes grouped into the 15 causes alerts use), station, line, time of day and weekend, trained in Python with scikit-learn and run in the browser, so nothing you type is sent anywhere. The three are kept in order; before that step they crossed for under 1% of test delays. A parity test checks the browser against Python on 30 inputs for all three.
- **Drift:** long delays became rarer in 2026 (about 19% of delays in early 2025, about 12% by summer 2026). Newer delays count more (180 day half life), and each output is recalibrated with Platt scaling on the latest 91 days; the base model never sees those days, and that exact pair ships with no refit. The call card shows the forecast before and after.
- **Wait or switch:** the card turns the three bands into an expected logged delay and compares it with the best scheduled switch to your destination (its arrival minus an on time subway arrival). It suggests switching only when the expected delay is at least that switch cost, a rule picked on earlier data only and tested on later periods (see Honest results).
- **Plan B, scheduled alternatives:** from the TTC schedule (files dated Oct 20, 2026, covering Nov 1 to Dec 21, 2026, the newest published on November 15), every regular stop pattern of every bus, streetcar and LRT route with the subway stations it passes in order. Only departures you can still catch are shown: leaving at or after now plus the walk (80 metres a minute in a straight line) plus 1 minute to board. Entries are ordered by that departure plus the scheduled ride, plus the scheduled subway time onward where you change, never claimed as the quickest way. Times refresh every minute and follow the service date past midnight; outside the schedule's dates the page says "Schedule data ends on Dec 21, 2026" and shows no times. A warning above the list says a scheduled alternative might not be running now. Five journeys were checked by hand against the raw schedule files.

## Honest results
**In three lines:**
1. **Ranking:** clearly better than the cause alone (AUC 0.751 against 0.727) and level with the first model (0.751 against 0.753, not distinguishable).
2. **Calibration:** closer than the first model (1.8 against 2.4 points, distinguishable), but forecasts still run a few points high.
3. **Decisions:** in a simulation with schedule based switch costs, the wait or switch rule now shipped (switch when the expected delay is at least the scheduled switch cost) is 0.16 minutes per delay ahead of always waiting (0.11 to 0.20) and 0.50 ahead of the old 35% rule (0.41 to 0.60). These intervals hold only under the simulation's assumptions. It has not been tested with riders.

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

**The wait or switch rule, picked on earlier data.** The old rule said to check another route whenever the 10+ chance was 35% or more. Two rules were tried in its place, each with its setting picked on earlier data only (each test period's own recalibration window) and then tested on that period in the station simulation described below. *20+ chance rule:* switch when the 20+ minute chance reaches a threshold. *Expected cost rule:* switch when the expected logged delay (the three bands times the average logged minutes in each range, capped at 60) minus the station's scheduled switch cost reaches a margin. Average minutes lost per delay, intervals resampling whole days:

| Delays | Always wait | Cause only at 35% | Old rule: 35% | 20+ chance rule | Expected cost rule | Expected cost against always wait | Against the old rule |
|---|---|---|---|---|---|---|---|
| All (7,455) | 6.56 | 6.71 | 6.91 | 6.53 | **6.40** | 0.16 saved (0.11 to 0.20) | 0.50 saved (0.41 to 0.60) |
| Under 10 minutes (6,363) | 4.45 | 4.67 | 4.86 | 4.47 | 4.49 | 0.04 lost (0.03 to 0.05) | 0.37 saved (0.29 to 0.46) |
| 20+ minutes (309) | 34.02 | 32.42 | 32.34 | 32.89 | 30.94 | 3.08 saved (2.23 to 4.04) | 1.40 saved (0.61 to 2.26) |
| 30+ minutes (139) | 46.64 | 43.63 | 43.48 | 44.47 | 41.83 | 4.81 saved (3.17 to 6.74) | 1.65 saved (0.03 lost to 3.45 saved) |

The expected cost rule was clearly better than the old rule, the cause only rule (0.31 minutes saved, 0.24 to 0.38) and always waiting, so it ships, with its margin (0 minutes) picked the same way on the shipped model's own recalibration window; the 20+ chance rule was not, so it does not. It wins by switching less on short delays and more on long ones. These are simulated minutes: the intervals hold only under the simulation's assumptions (Tue Nov 17, Sat Nov 21 and Sun Nov 22, 2026 schedule days applied to earlier delays, logged delay minutes as the cost of waiting, alternatives that run as scheduled). On the page the switch cost uses your destination when it is on the same line; in the simulation it is the first station past the delay, averaged over both directions.

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

## Responsible use
No accounts and no tracking. Not affiliated with or endorsed by the Toronto Transit Commission. Always follow TTC staff and announcements; it is not for decisions about leaving a train or evacuating. The forecast is labelled as an estimate, rare causes and stations are flagged, every value read from an alert can be checked and changed, and Plan B is labelled as scheduled alternatives that might not be running. The alert is entered by hand. Blue Night routes are listed only overnight. It has not been tested with riders.

## Challenges I ran into
The drift was the big one: a model that looked fine on 2025 data was wrong on 2026, and my first fix used a calibration process that did not match the shipped model, which I caught and redid. Matching station names was the other: the delay log writes "BLOOR STATION", "YONGE BD STATION" and old names like "DUNDAS", while the schedule uses "Bloor Station", "Yonge Station" and "TMU Station". And the simulation first let crosstown buses "beat" the subway by jumping across the U of Line 1; limiting it to stations a few stops along fixed that.

## What I learned
Calibration matters as much as ranking for a tool people act on, it has to be validated the same way it is shipped, and intervals keep you honest about which differences are real. Here the cause alone gets most of the way, and the time saved is in the long tail. A decision rule needs the same care as the model: picking its setting on earlier data and testing it on later periods turned a rule that lost time overall into one that saves a little.

## What's next
- An optional "already lasted N minutes" input. The delay log gives total minutes but not when an alert went out, so this cannot be validated honestly yet.
- Accessibility beyond the schedule's stop flag: elevator outages and step free routes between stops.
- Read live TTC alerts automatically, add live arrival times and streetcar delay data, and test it with riders.

## Built during the event
SLAY HACKS began November 7, 2026, and all of Wait or Walk was built after that. A private prototype script came first, to test the idea; the public repo's first commit (git log --reverse) is from 6:08 a.m. Toronto time on November 15, 2026, and every change since is in its history. No application code came from earlier projects: a line by line comparison with my other GitHub repos found only boilerplate in common (page colour variables and a few base style rules, the standard module wrapper, test imports). Data: City of Toronto Open Data, TTC Subway Delay Data since 2025 and TTC Routes and Schedules (GTFS), both under the Open Government Licence Toronto. Libraries: pandas, NumPy, SciPy and scikit-learn for training.
