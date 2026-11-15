## Overview
Wait or Walk answers the question every Toronto subway rider asks when the train stops: will this be two minutes or twenty? Paste the TTC alert and it shows how often comparable logged incidents delayed subway service 10 minutes or more, the reasons behind that number, and the buses and streetcars a short walk away that head where you are going.

## Problem and solution
TTC alerts say what happened, not how long it will take. Riders guess, and guessing wrong costs real time: people wait twenty minutes for a fire investigation to clear, or leave a platform for a passenger alarm that would have cleared in three. The TTC has published every subway delay it logs since 2025, with its cause and length, so the answer to "how long do incidents like this usually hold up service" already exists. Wait or Walk turns those records into a risk estimate you can use on the platform, for daily commuters, students, shift workers and visitors who do not know the surface routes.

## How it works
- **Reading the alert:** the line, station and cause are pulled from the alert text and tagged "from alert, please check". Anything not found is left empty instead of keeping an old choice, and uncertain matches are flagged, such as an alert naming two stations or Bloor-Yonge without a line.
- **What the number means:** the TTC logs each incident with the minutes it delayed subway service. The number is the estimated chance that an incident like this one, logged with more than 0 minutes of delay, delayed service 10 minutes or more. It is not your personal remaining wait, and records with 0 minutes of delay are left out. Under 15% reads as low risk, 15% to 35% as moderate, and 35% and up as high, "worth checking another route now".
- **Data:** 16,548 subway delays on Lines 1, 2 and 4 from Jan 1, 2025 to Sep 30, 2026 (City of Toronto Open Data), and the TTC GTFS schedule.
- **Features a rider actually has:** the TTC's 124 delay codes are grouped into the 15 causes alerts use. The model sees only cause, station, line, time of day and weekend.
- **Model:** logistic regression trained in Python with scikit-learn, exported as weights and run in the browser, so nothing you type is sent anywhere. A test checks the browser code gives the same answer as the Python model on 30 example inputs.
- **Drift:** long delays became rarer in 2026 (about 19% of delays in early 2025, about 12% by summer 2026). Newer delays count more (180 day half life), and the output is recalibrated with Platt scaling. The base model is trained on everything before the last 91 days, the recalibration is fitted on those 91 days, and that exact pair is shipped with no refit. The page shows the forecast before and after this correction.
- **Plan B that knows direction:** from the schedule, every regular stop pattern of every bus and streetcar route, with the subway stations it passes in order. Pick where you are headed and you get the routes from the delayed station that reach near your destination in the right direction, or that carry you past the delay to a station on the way, then the subway onward. Blue Night routes are listed separately.
- **Explainable:** each forecast lists the factors that pushed it up or down most, how many logged delays share the cause, and a warning when a cause or station has fewer than 100.

## Honest results
Every test runs the shipped process exactly: the base model stops 91 days before the test months, the recalibration uses those 91 days, and the test months are touched once, for scoring. On Jul to Sep 2026 (2,248 delays): AUC 0.769 against 0.760 for a rule that only looks at the cause (recalibrated the same way), log loss 0.3154 against 0.3167, average forecast 14% against the actual 12%. On Apr to Jun 2026: AUC 0.758 against 0.729, log loss 0.3484 against 0.3593. On Jan to Mar 2026: AUC 0.724 against 0.685, log loss 0.4189 against 0.4340. Against my first model, which skips recalibration and so can learn from the three most recent months, it is about level. Pooled over all 7,455 test delays, forecasts ran up to 4 points high, and the page draws that as a calibration chart. An earlier version of this page reported 0.772 AUC from a calibration process that did not match what was shipped; the numbers above replace it.

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
