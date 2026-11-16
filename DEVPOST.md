**Subway stopped? Paste the TTC alert to see the chance a comparable recorded delay lasts 10+ minutes, and timetabled buses nearby.**

It also gives a cautious wait or switch call, and it rarely says switch: on 107 of 13,174 simulated trips (a past delay and a direction of travel), about 1 in 120. In the simulation those calls saved about 8 minutes each with an on time bus and lost about 15 each when the first bus was missed. No rider testing has been done.

Live: https://alenzacodes.github.io/wait-or-walk/ · Code: https://github.com/ALENZACODES/wait-or-walk (full method, every table and every check are in the README).

## 2 minute judge path
1. Open the live page and tap "Person at track level, Kipling" (simulated Monday, November 16, 2026, 5:30 p.m.). Read the 23%: the chance the recorded delay lasts 10 minutes or more, among comparable TTC incidents with a recorded delay of 1 minute or more. Beside it, 15% is the all incidents view, which counts the incidents logged with 0 minutes too. The verdict says wait: about 8 minutes against 19 by the 149 bus, by the timetable.
2. Tap "Fire at St George, headed to Dupont". 66% (4% in the all incidents view), and the verdict says switch, by about 11 minutes by the timetable. Timetable risk for this trip: about 11 minutes saved by the timetable with the 5:35 p.m. bus on time, about 6 if it leaves 5 minutes late, about 12 lost if you miss it.
3. Tap "Delay already reached 5 min": the chance becomes 10 minutes or more in total among delays that reached 5.
4. Under "How good is it?": how rarely it says switch, the held out parser score (98%) and the zero minute check.
5. Optional: paste a current alert from ttc.ca/service-alerts for live time Plan B departures and the Live check line under the verdict.

The code judged is the tag `slay-hacks-submission`. Later commits titled "Copy TTC subway alerts" are automated data copies that never touch the model, the verdict rule or the parser (all three are frozen; a freeze check runs in the tests).

## The problem
TTC alerts say what happened, not how long it will take. Riders guess: some wait twenty minutes for a fire investigation, others leave the platform for an alarm that clears in three. City of Toronto Open Data publishes every logged TTC subway delay since January 1, 2025, with its cause, station and minutes. Wait or Walk turns those records into a number you can use on the platform.

## What it does
Paste the alert (or tap one from a copy of the TTC feed). In about 30 seconds you see:
- **The alert read back**, with line, station and cause you can correct.
- **Two chances side by side.** The chance a comparable recorded delay lasts 5, 10 or 20 minutes or more, among incidents with a recorded delay (what the verdict uses), and the all incidents view, which counts the 65% of logged incidents that record 0 minutes. Kipling: 23% and 15%. St George fire: 66% and 4%, because 1,478 of 1,572 logged fire and smoke incidents record 0 minutes.
- **Plan B:** scheduled buses, streetcars and LRT within 300 metres heading your way, with departures you may be able to catch (timetable estimates, not real time; marked live where the TTC's NextBus feed has a prediction).
- **A cautious verdict:** wait or switch by the timetable, switching only if it still wins with the bus 5 minutes late, plus what a late or missed bus would do.

**Next to existing transit apps.** Transit and the TTC's own tools show live arrivals, trip plans and alerts, and for those they are the place to look. Their public pages (checked November 15, 2026) do not estimate how long a subway delay is likely to last. Wait or Walk adds that one thing and is meant to sit beside them.

## How the machine learning works
- **Models:** three calibrated logistic regressions (scikit-learn) for 5+, 10+ and 20+ minutes, on cause (the TTC's 124 delay codes grouped into the 15 causes alerts use), station, line, time of day and day type. Newer delays weigh more (180 day half life), and each model is recalibrated with Platt scaling on the 91 days before it, because long delays became rarer in 2026.
- **Zero minute records:** the shipped models leave out incidents logged with 0 minutes, so their chance assumes the incident delays service. A separate fit that keeps them gives the all incidents view, served as a lookup table the verdict never reads. Once a delay has already reached 5 minutes, that view does not apply and the card says so.
- **Reading the alert:** hand written rules, not a trained model, for line, 71 stations and 14 causes. Ambiguous alerts (two stations, a two line station without a line) ask you to choose. Planned work and slow zones get no forecast.
- **Live check:** where the TTC's NextBus feed has a prediction for the Plan B stop, a gate warns when the bus the verdict relies on is predicted 5 or more minutes late or earlier than you could reach the stop. The live check matches by time only: the nearest predicted departure is taken as the timetabled bus, which does not confirm it is the same vehicle, so it is an approximate conflict check that can only warn. It runs in the browser; the Live check line always names its state (off, loading, unavailable, no prediction, out of date, no conflict found, disagrees).
- **Stack:** plain HTML, CSS and JavaScript on GitHub Pages; Python (pandas, NumPy, SciPy, scikit-learn) for training; GitHub Actions to copy the TTC alerts feed every 30 minutes; Playwright and axe-core for browser and accessibility checks.

## Results, in brief
Tested on three later periods the model never saw (7,455 delays, January to September 2026), each run with the exact process that ships:
1. **Ranking:** AUC 0.751, better than the cause alone (0.727) and level with the first model (0.753).
2. **Calibration:** error 1.8 points pooled. Forecasts still ran a little high in 2026 (17% forecast against 14% actual in one period); a fresher recalibration was tested and did not pass.
3. **Decisions, in a simulation, not measured on riders:** it said switch on 107 of 13,174 simulated trips (a past delay and a direction of travel). In the simulation those calls saved about 7.9 minutes each with buses on schedule, 2.9 with the bus 5 minutes late, and lost 14.5 when the first bus was missed; 17% lost time even on schedule. Spread over every simulated trip that is 0.06 minutes per trip. Averaged over eight what if scenarios the late bus check came out 0.63 minutes per delay ahead of the timetable only rule in the simulation; that compares two rules and is not a rider benefit.
4. **Reading alerts:** on the 51 newest of 102 real TTC alerts, held out while the rules were fixed, it named the right station in 98% (50 of 51) and the right cause in 98% (45 of 46). All 102 are right after later fixes, but that is on alerts used for fixing, so it is not the headline.
5. **Zero minute records:** counting them, 5.0% of incidents reach 10 minutes instead of 14.6%. That is why the card now shows both numbers.

## Limits, stated plainly
- No rider testing has been done; a 10 minute script for five riders is ready in docs/rider-check.md. No manual screen reader test has been done; the accessibility checks are automated.
- No fresh frozen test yet: the newest City delay file still ends on September 30, 2026. A forecast log scores the frozen model when newer data appears.
- Rare causes rest on few cases (fire or smoke: 94 recorded delays) and the page flags them.
- Plan B uses the regular schedule and straight line distance, not live detours or shuttle buses. Live times exist only where the older NextBus feed answers.
- The alert copy can be late. GitHub can delay or drop scheduled runs. Scheduled runs so far: see the README. The page does not depend on it: it shows when the copy was made and last checked, marks it out of date after 90 minutes, and paste always works.

## Responsible use
No accounts and no tracking. Only the stop code is sent to the NextBus host (webservices.umoiq.com), never your alert or destination; like any web host, it also sees your IP address and the time of the request. Always follow TTC staff and announcements; this is not for decisions about leaving a train or evacuating. Not affiliated with or endorsed by the Toronto Transit Commission.

Data: City of Toronto Open Data (TTC Subway Delay Data, TTC Routes and Schedules, TTC GTFS Realtime alerts, TTC Real Time Next Vehicle Arrival), all under the Open Government Licence Toronto. Contains information licensed under the Open Government Licence – Toronto. Bike Share Toronto station data from its GBFS feed (Open Government Licence Toronto in the City catalogue; the live feed is listed as CC BY 4.0).

## Built during the event
SLAY HACKS began November 7, 2026, and all of Wait or Walk was built after that. The public repo's first commit is from 6:08 a.m. Toronto time on November 15, 2026, and every change since is in its history.

## Challenges and what I learned
Drift was the big one: a model that looked fine on 2025 data ran high on 2026, and the fix had to be validated the same way it ships. Station names were the other: the delay log writes "YONGE BD STATION" and old names like "DUNDAS", the schedule writes "Yonge Station" and "TMU Station". A decision rule needs the same care as the model: picking its setting on earlier data and testing it on later periods is what made it cautious.

## What's next
Score the alert time forecast log once the City publishes newer delays, run the rider check with five riders, add step free routing, and read the TTC's newer GTFS Realtime feed through a small relay.
