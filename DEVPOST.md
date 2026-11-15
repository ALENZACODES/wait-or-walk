## Worked example
Alert pasted on a weekday at 5:30 p.m., heading to Jane: *"Line 2 Bloor-Danforth: Delays at Kipling due to a person at track level."*
- **Read from the alert (tagged for checking):** Line 2, Kipling, person at track level.
- **The call:** 23%, moderate risk of a long delay. "Know your other route and check the alert again in a few minutes."
- **Drift correction:** 29% before recalibration, 23% after.
- **Behind it:** 563 logged delays with this cause, 270 of them 10 minutes or more; half were over in 9 minutes or less. The cause raises the odds; Kipling and the evening rush lower them.
- **Plan B, scheduled alternatives (may not be running right now):** 149 Etobicoke-Bloor, East towards Jane Station, from Kipling Station (10 m, about a 1 minute walk, accessible boarding listed); next scheduled 5:39, 6:07 and 6:35 p.m.; get off at Jane Station. Or 40 Junction-Dundas West east past the delay to Islington, then Line 2 (next 5:53, 6:17 and 6:42 p.m.).

## Overview
Wait or Walk answers the question every Toronto subway rider asks when the train stops: will this be two minutes or twenty? Paste the TTC alert and it shows how often comparable logged incidents delayed subway service 10 minutes or more, the reasons behind that number, and scheduled buses, streetcars and LRT within 300 metres that head where you are going, with their next scheduled departures.

## Problem and solution
TTC alerts say what happened, not how long it will take. Riders guess, and guessing wrong costs real time: people wait twenty minutes for a fire investigation to clear, or leave a platform for a passenger alarm that would have cleared in three. City of Toronto Open Data publishes a TTC subway delay log starting January 1, 2025, with each incident's cause, station and minutes of delay; the copy used here has 47,915 records up to September 30, 2026. Wait or Walk turns those records into a risk estimate you can use on the platform, for daily commuters, students, shift workers and visitors who do not know the surface routes.

## How it works
- **Reading the alert:** hand written rules, not a trained model. Regular expressions find line names ("Line 2", "Bloor-Danforth"), keyword patterns find 14 causes in a fixed order with the most specific first ("person at track level" before "track"), and a search finds the 71 station names plus a few older names, such as Dundas for TMU. Values read are tagged "from alert, please check"; anything not found is left empty.
- **No number until it is clear:** if two stations are named, or Bloor-Yonge or another two line station has no line, you choose before any number appears. A station that is not on the chosen line (Union on Line 2) also gives no number. Clearing the alert clears what it filled in, and the number with it. Automated tests cover each case.
- **What the number means:** the estimated chance that an incident like this one, logged with more than 0 minutes of delay, delayed subway service 10 minutes or more. It is not your own remaining wait. Under 15% reads as low risk, 15% to 35% as moderate, and 35% and up as high, "worth checking another route now".
- **Model:** logistic regression on cause (the TTC's 124 delay codes grouped into the 15 causes alerts use), station, line, time of day and weekend, trained in Python with scikit-learn and run in the browser, so nothing you type is sent anywhere. A parity test checks that the browser gives the same answer as Python on 30 example inputs.
- **Drift:** long delays became rarer in 2026 (about 19% of delays in early 2025, about 12% by summer 2026). Newer delays count more (180 day half life), and the output is recalibrated with Platt scaling: the base model is trained on everything before the last 91 days, the recalibration is fitted on those 91 days, and that exact pair ships with no refit. The call card shows the forecast before and after this correction, right under the risk band.
- **Plan B, scheduled alternatives:** not verified fastest routes, and the page says right above the list that a scheduled alternative might not be running now. From the TTC schedule, every regular stop pattern of every bus, streetcar and LRT route (Line 5 Eglinton is listed as LRT), with the subway stations it passes in order. Stops count within 300 metres in a straight line, shown with walking time at 80 metres a minute and the schedule's accessible boarding flag. Departure times use the service calendar for today and the current Toronto time. Pick where you are headed and you get routes that reach near your destination in the right direction, or that carry you past the delay to a station on the way. Five journeys on Lines 1 and 2, including one that changes lines, were checked by hand against the raw schedule files, with screenshots in the repo.

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

## Responsible use
No accounts and no tracking. Not affiliated with or endorsed by the Toronto Transit Commission. The forecast is labelled as an estimate, rare causes and stations are flagged, every value read from an alert can be checked and changed, and Plan B is labelled as scheduled alternatives that might not be running. It has not been tested with riders.

## Challenges I ran into
The drift was the big one: a model that looked fine on 2025 data was wrong on 2026, and my first fix used a calibration process that did not match the shipped model, which I caught and redid. Matching station names was the other: the delay log writes "BLOOR STATION", "YONGE BD STATION" and old names like "DUNDAS", while the schedule uses "Bloor Station", "Yonge Station" and "TMU Station", so I built a mapping and checked that 99% of delays land on a real station.

## What I learned
Calibration matters as much as ranking for a tool people act on, it has to be validated the same way it is shipped, and intervals keep you honest about which differences are real. Here the cause alone gets most of the way.

## What's next
- An optional "already lasted N minutes" input. The delay log gives total minutes but not when an alert went out, so this cannot be validated honestly yet.
- Accessibility beyond the schedule's stop flag: elevator outages and step free routes between stops.
- Read live TTC alerts automatically, add live arrival times and streetcar delay data, and test it with riders.

## Built during the event
SLAY HACKS began November 7, 2026. Work on Wait or Walk started on November 15, 2026; the first commit in the public repo is from 6:08 a.m. Toronto time that day, and every change since is in its history. Data: City of Toronto Open Data, TTC Subway Delay Data since 2025 and TTC Routes and Schedules (GTFS, schedule dated Oct 20, 2026), both under the Open Government Licence Toronto. Libraries: pandas, NumPy and scikit-learn for training.
