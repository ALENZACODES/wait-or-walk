## Overview
Wait or Walk answers the question every Toronto subway rider asks when the train stops: will this be two minutes or twenty? Paste the TTC alert, or pick the line, station and cause, and it shows the chance the delay lasts 10 minutes or more, the reasons behind that number, and the bus and streetcar routes with a stop within 300 metres.

## Problem and solution
TTC alerts say what happened, not how long it will take. Riders guess, and guessing wrong costs real time: people wait twenty minutes for a fire investigation to clear, or leave a platform for a passenger alarm that would have cleared in three. The TTC has published every subway delay it logs since 2025, with its cause and length, so the answer to "how long do delays like this usually last" already exists. Wait or Walk turns those records into a forecast you can use on the platform, for daily commuters, students, shift workers and visitors who do not know the surface routes.

## How the model works
- **Data:** 16,548 subway delays on Lines 1, 2 and 4 from Jan 1, 2025 to Sep 30, 2026 (City of Toronto Open Data), and the TTC GTFS schedule for nearby stops.
- **Features a rider actually has:** the TTC's 120 or so internal delay codes are grouped into the 15 causes alerts use, such as medical emergency, person at track level or signal problem. The model sees only cause, station, line, time of day and weekend, all of which an alert gives you.
- **Model:** logistic regression trained in Python with scikit-learn, exported as weights and run in the browser, so it is instant, works offline once loaded and never sends your data anywhere. The browser matches the Python model to within 0.0001 on 30 held out delays, checked by the tests.
- **Fixing drift:** long delays became rarer in 2026 (about 19% of delays in early 2025, about 12% by summer 2026). My first model kept forecasting the old rate. Now newer delays count more (180 day half life) and the output is recalibrated with Platt scaling on the latest 91 days, fitted on a model that never saw those days.
- **Explainable:** each forecast lists the factors that pushed it up or down most, such as "Cause (fire or smoke) raises the odds".

## Honest results
Each test is trained only on earlier data. On Jul to Sep 2026 (2,248 delays): AUC 0.772 against 0.761 for a rule that only looks at the cause, log loss 0.3132 against 0.3225, and an average forecast of 13% against the actual 12%, where the first model said 16%. On Apr to Jun 2026 the gain is smaller (AUC 0.764 against 0.737) and the recalibration could not see the spring drop coming, which the page says plainly. The cause carries most of the signal, and the page shows the full table and a monthly chart so anyone can judge it.

## Responsible use
No accounts, no tracking and no data leaves the browser. The forecast is labelled as an estimate, rare causes are flagged as resting on few cases, and the tool always shows the alternative routes so the decision stays with the rider.

## Challenges I ran into
The drift was the big one: a model that looked fine on 2025 data was wrong on 2026. Matching station names was the other: the delay log writes "BLOOR STATION", "YONGE BD STATION" and old names like "DUNDAS", while the schedule uses "Bloor Station", "Yonge Station" and "TMU Station", so I built a mapping and checked that 99% of delays land on a real station.

## What I learned
Calibration matters as much as ranking for a tool people act on, and the honest baseline is the one to beat. Here the cause alone gets most of the way.

## What's next
Read live TTC alerts automatically, add streetcar delay data, and show live arrival times for the Plan B routes.

## Built during the event
Wait or Walk was built during SLAY HACKS, from November 14, 2026. Data: City of Toronto Open Data under the Open Government Licence Toronto. Libraries: pandas, NumPy and scikit-learn for training.
