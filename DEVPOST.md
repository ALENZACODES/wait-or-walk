## Worked example
Alert pasted on a weekday at 5:30 p.m., heading to Jane: *"Line 2 Bloor-Danforth: Delays at Kipling due to a person at track level."*
- **Read from the alert (tagged for checking):** Line 2, Kipling, person at track level.
- **Estimated chance:** 23% that an incident like this delays subway service 10 minutes or more (moderate risk). Beside it: 40% for 5+ minutes, 10% for 20+ minutes.
- **Drift correction:** 29% before recalibration, 23% after.
- **Why 23% and not 48%:** 48% is every logged delay with this cause since January 2025 (270 of 563). The estimate adjusts that for the station, the line, the time of day and the drop in long delays in 2026 (in the latest 91 days, 41% of 80 delays with this cause ran 10 minutes or more). The cause raises the odds; Kipling and the evening rush lower them.
- **Plan B, earliest scheduled arrival first (may not be running right now):** 149 Etobicoke-Bloor from Kipling Station (10 m, about a 1 minute walk, accessible boarding listed): next you can catch 5:39, 6:07 and 6:35 p.m.; by the schedule at Jane about 5:57 p.m. Then 40 Junction-Dundas West (100 m): next you can catch 5:53 p.m.; at Islington about 5:58, then Line 2 to Jane about 6:04 p.m. if the subway runs normally there.
- **Safety first:** always follow TTC staff and announcements. This is a planning aid for riders on a platform, not for decisions about leaving a train or evacuating.

## Overview
Wait or Walk answers the question every Toronto subway rider asks when the train stops: will this be two minutes or twenty? Paste the TTC alert and it gives the estimated chance of a 5, 10 or 20 minute delay, the reasons behind it, and scheduled buses, streetcars and LRT within 300 metres that head where you are going, ordered by the arrival the schedule allows, counting only departures you can still catch.

## Problem and solution
TTC alerts say what happened, not how long it will take. Riders guess, and guessing wrong costs real time: people wait twenty minutes for a fire investigation to clear, or leave a platform for a passenger alarm that would have cleared in three. City of Toronto Open Data publishes a TTC subway delay log starting January 1, 2025, with each incident's cause, station and minutes of delay; the copy used here has 47,915 records up to September 30, 2026. Wait or Walk turns those records into a risk estimate you can use on the platform, for daily commuters, students, shift workers and visitors who do not know the surface routes.

## How it works
- **Reading the alert:** hand written rules, not a trained model. Regular expressions find line names ("Line 2", "Bloor-Danforth"), keyword patterns find 14 causes in a fixed order with the most specific first ("person at track level" before "track"), and a search finds the 71 station names plus a few older names, such as Dundas for TMU. Values read are tagged "from alert, please check".
- **No number until it is clear:** two stations named, a two line station without a line, or a station that is not on the chosen line (Union on Line 2) all give no number until you choose. Clearing the alert clears what it filled in. Automated tests cover each case.
- **Three calibrated models:** logistic regressions for 5+, 10+ and 20+ minutes on cause (the TTC's 124 delay codes grouped into the 15 causes alerts use), station, line, time of day and weekend, trained in Python with scikit-learn and run in the browser, so nothing you type is sent anywhere. The three are kept in order; before that step they crossed for under 1% of test delays. A parity test checks the browser against Python on 30 inputs for all three.
- **Drift:** long delays became rarer in 2026 (about 19% of delays in early 2025, about 12% by summer 2026). Newer delays count more (180 day half life), and each output is recalibrated with Platt scaling on the latest 91 days; the base model never sees those days, and that exact pair ships with no refit. The call card shows the forecast before and after.
- **Plan B, scheduled alternatives:** from the TTC schedule (files dated Oct 20, 2026, covering Nov 1 to Dec 21, 2026, the newest published on November 15), every regular stop pattern of every bus, streetcar and LRT route with the subway stations it passes in order. Only departures you can still catch are shown: leaving at or after now plus the walk (80 metres a minute in a straight line) plus 1 minute to board. Entries are ordered by that departure plus the scheduled ride, plus the scheduled subway time onward where you change, never claimed as the quickest way. Times refresh every minute and follow the service date past midnight; outside the schedule's dates the page says "Schedule data ends on Dec 21, 2026" and shows no times. A warning above the list says a scheduled alternative might not be running now. Five journeys were checked by hand against the raw schedule files.

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

## Responsible use
No accounts and no tracking. Not affiliated with or endorsed by the Toronto Transit Commission. Always follow TTC staff and announcements; it is not for decisions about leaving a train or evacuating. The forecast is labelled as an estimate, rare causes and stations are flagged, every value read from an alert can be checked and changed, and Plan B is labelled as scheduled alternatives that might not be running. It has not been tested with riders.

## Challenges I ran into
The drift was the big one: a model that looked fine on 2025 data was wrong on 2026, and my first fix used a calibration process that did not match the shipped model, which I caught and redid. Matching station names was the other: the delay log writes "BLOOR STATION", "YONGE BD STATION" and old names like "DUNDAS", while the schedule uses "Bloor Station", "Yonge Station" and "TMU Station". And the simulation first let crosstown buses "beat" the subway by jumping across the U of Line 1; limiting it to stations a few stops along fixed that.

## What I learned
Calibration matters as much as ranking for a tool people act on, it has to be validated the same way it is shipped, and intervals keep you honest about which differences are real. Here the cause alone gets most of the way, and the time saved is in the long tail.

## What's next
- An optional "already lasted N minutes" input. The delay log gives total minutes but not when an alert went out, so this cannot be validated honestly yet.
- Accessibility beyond the schedule's stop flag: elevator outages and step free routes between stops.
- Read live TTC alerts automatically, add live arrival times and streetcar delay data, and test it with riders.

## Built during the event
SLAY HACKS began November 7, 2026, and all of Wait or Walk was built after that. A private prototype script came first, to test the idea; the public repo's first commit (git log --reverse) is from 6:08 a.m. Toronto time on November 15, 2026, and every change since is in its history. No application code came from earlier projects: a line by line comparison with my other GitHub repos found only boilerplate in common (page colour variables and a few base style rules, the standard module wrapper, test imports). Data: City of Toronto Open Data, TTC Subway Delay Data since 2025 and TTC Routes and Schedules (GTFS), both under the Open Government Licence Toronto. Libraries: pandas, NumPy, SciPy and scikit-learn for training.
