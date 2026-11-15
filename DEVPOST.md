## Overview
Wait or Walk answers the question every Toronto subway rider asks when the train stops: will this be two minutes or twenty? Paste the TTC alert and it shows how often comparable logged incidents delayed subway service 10 minutes or more, the reasons behind that number, and scheduled buses and streetcars a short walk away that head where you are going.

## Problem and solution
TTC alerts say what happened, not how long it will take. Riders guess, and guessing wrong costs real time: people wait twenty minutes for a fire investigation to clear, or leave a platform for a passenger alarm that would have cleared in three. The TTC has published every subway delay it logs since 2025, with its cause and length, so the answer to "how long do incidents like this usually hold up service" already exists. Wait or Walk turns those records into a risk estimate you can use on the platform, for daily commuters, students, shift workers and visitors who do not know the surface routes.

## How it works
- **Reading the alert:** the line, station and cause are pulled from the alert text and tagged "from alert, please check". Anything not found is left empty instead of keeping an old choice. If the alert is ambiguous, no number appears until you choose: two stations named asks which one, and Bloor-Yonge without a line asks which line. Clearing the alert clears what it filled in, and the number with it. Automated tests cover each of these cases.
- **What the number means:** the TTC logs each incident with the minutes it delayed subway service. The number is the estimated chance that an incident like this one, logged with more than 0 minutes of delay, delayed service 10 minutes or more. It is not your personal remaining wait, and records with 0 minutes of delay are left out. Under 15% reads as low risk, 15% to 35% as moderate, and 35% and up as high, "worth checking another route now".
- **Data:** 16,548 subway delays on Lines 1, 2 and 4 from Jan 1, 2025 to Sep 30, 2026 (City of Toronto Open Data), and the TTC GTFS schedule.
- **Features a rider actually has:** the TTC's 124 delay codes are grouped into the 15 causes alerts use. The model sees only cause, station, line, time of day and weekend.
- **Model:** logistic regression trained in Python with scikit-learn, exported as weights and run in the browser, so nothing you type is sent anywhere. A test checks the browser code gives the same answer as the Python model on 30 example inputs.
- **Drift:** long delays became rarer in 2026 (about 19% of delays in early 2025, about 12% by summer 2026). Newer delays count more (180 day half life), and the output is recalibrated with Platt scaling. The base model is trained on everything before the last 91 days, the recalibration is fitted on those 91 days, and that exact pair is shipped with no refit. The call card shows the forecast before and after this correction, right under the risk band.
- **Plan B, scheduled alternatives that know direction:** these are scheduled alternatives, not verified fastest routes. From the schedule, every regular stop pattern of every bus and streetcar route, with the subway stations it passes in order. Pick where you are headed and you get the routes from the delayed station that reach near your destination in the right direction, or that carry you past the delay to a station on the way, then the subway onward. Blue Night routes are listed separately. Five journeys on Lines 1 and 2, including one that changes lines, were checked by hand against the raw schedule files and are shown with screenshots in the repo.
- **Explainable:** each forecast lists the factors that pushed it up or down most, how many logged delays share the cause, and a warning when a cause or station has fewer than 100.

## Honest results
Forecasts run high. Pooled over three evaluation periods, they sat above what happened in every band: 3 to 4 points in the bands above 30% (35% forecast vs 31% actual, 59% vs 55%) and up to 3 points below that. By period, the average forecast was 18% vs 18% actual, 17% vs 14%, and 14% vs 12%. The page draws this as a calibration chart.

Wait or Walk beats a rule that only looks at the cause (recalibrated the same way) on AUC and log loss in all three periods, and that is the only baseline it beats. It ranks a little below my first model on AUC in all three (0.724 vs 0.731, 0.758 vs 0.760, 0.769 vs 0.770): recalibrating on the latest three months costs a little ranking, because the base model cannot learn from them. On log loss it is about level with the first model.

All three are out of time evaluation periods not used for fitting (Jan to Mar, Apr to Jun and Jul to Sep 2026), each run with the exact process that ships. An earlier version of this page reported 0.772 AUC from a calibration process that did not match what was shipped; these numbers replace it.

## Responsible use
No accounts and no tracking. The forecast is labelled as an estimate, rare causes and stations are flagged, every value read from an alert can be checked and changed, and the tool always shows alternative routes so the decision stays with the rider. It has not yet been tested with riders.

## Challenges I ran into
The drift was the big one: a model that looked fine on 2025 data was wrong on 2026, and my first fix used a calibration process that did not match the shipped model, which I caught and redid. Matching station names was the other: the delay log writes "BLOOR STATION", "YONGE BD STATION" and old names like "DUNDAS", while the schedule uses "Bloor Station", "Yonge Station" and "TMU Station", so I built a mapping and checked that 99% of delays land on a real station.

## What I learned
Calibration matters as much as ranking for a tool people act on, it has to be validated the same way it is shipped, and the honest baseline is the one to beat. Here the cause alone gets most of the way.

## What's next
Read live TTC alerts automatically, add streetcar delay data, show live arrival times for the Plan B routes, and test it with riders.

## Built during the event
Wait or Walk was built during SLAY HACKS, from November 14, 2026. Data: City of Toronto Open Data under the Open Government Licence Toronto. Libraries: pandas, NumPy and scikit-learn for training.
