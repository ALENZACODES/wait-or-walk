**Subway stopped? Paste the TTC alert to see the chance a comparable recorded delay lasts 10+ minutes, and timetabled buses nearby.**

It also gives a cautious wait or switch call, and it rarely says switch: on 107 of 13,174 simulated trips (a past delay and a direction of travel), about 1 in 120. In the simulation those calls saved about 8 minutes each with an on time bus and lost about 15 each when the first bus was missed. No rider testing has been done.

Live: https://alenzacodes.github.io/wait-or-walk/  Code: https://github.com/ALENZACODES/wait-or-walk (full method, every table and every check are in the README).

## 2 minute judge path
1. Open the live page and tap "Person at track level, Kipling" (simulated Monday, November 16, 2026, 5:30 p.m.). Read the 23%: the chance the recorded delay lasts 10 minutes or more, among comparable TTC incidents with a recorded delay of 1 minute or more. Beside it, 15% is the all incidents view, which counts incidents logged with 0 minutes too. The verdict says wait: about 8 minutes against 19 by the 149 bus, by the timetable.
2. Tap "Fire at St George, headed to Dupont". 66% (4% in the all incidents view), and the verdict says switch, by about 11 minutes by the timetable. A line under the two chances states that this switch call uses the first chance, which assumes the fire or smoke delays service, and Plan B times from the timetable; 1,478 of 1,572 logged fire and smoke incidents record 0 minutes. Timetable risk for this trip: about 11 minutes saved by the timetable with the 5:35 p.m. bus on time, about 6 if it leaves 5 minutes late, about 12 lost if you miss it.
3. Tap "Delay already reached 5 min": the chance becomes 10 minutes or more in total among delays that reached 5.
4. Under "How good is it?": how rarely it says switch, the held out parser score (98%) and the Zero minute check.
5. Optional: paste a current alert from ttc.ca/service-alerts for live Plan B times and the Live check line under the verdict.

The code judged is the tag `slay-hacks-submission`. Later commits titled "Copy TTC subway alerts" are automated data copies that never touch the model, the verdict rule or the parser (all three are frozen; a freeze check runs in the tests).

## What it does
Paste the alert (or tap one from a copy of the TTC feed). You see the alert read back, two chances side by side, Plan B buses within 300 metres (timetable estimates, not real time; marked live where the TTC's NextBus feed has a prediction), and a cautious verdict that switches only if it still wins with the bus 5 minutes late.

**Next to existing transit apps.** Transit and the TTC's own tools show live arrivals, trip plans and alerts. Their public pages (checked November 15, 2026) do not estimate how long a subway delay is likely to last. Wait or Walk adds that one thing and is meant to sit beside them.

## How the machine learning works
Three calibrated logistic regressions for 5+, 10+ and 20+ minutes, on cause, station, line, time of day and day type, with a 180 day half life and Platt scaling on the 91 days before each period. The shipped models leave out 0 minute records; a separate fit that keeps them is the all incidents view, which the verdict never reads. Alerts are read with hand written rules. The Live check, where NextBus has a prediction, can only warn: it matches by time only, taking the nearest predicted departure as the timetabled bus, which does not confirm it is the same vehicle. Stack: GitHub Pages, Python for training, GitHub Actions for the alerts copy, Playwright and axe-core for checks.

## Results, in brief
Tested on three later periods the model never saw (7,455 delays, January to September 2026), each run with the exact process that ships. Ranking: AUC 0.751, better than the cause alone (0.727) and level with the first model (0.753). Calibration error 1.8 points pooled; a fresher recalibration was tested and did not pass. Decisions, in a simulation, not measured on riders: switch on 107 of 13,174 simulated trips; in the simulation those calls saved about 7.9 minutes each on schedule, 2.9 with the bus 5 minutes late, and lost 14.5 when the first bus was missed. Spread over every simulated trip that is 0.06 minutes per trip. Averaged over eight what if scenarios the late bus check came out 0.63 minutes per delay ahead of the timetable only rule in the simulation; that compares two rules and is not a rider benefit. On the 51 newest of 102 real TTC alerts, held out while the rules were fixed, it named the right station in 98% (50 of 51) and the right cause in 98% (45 of 46). All 102 are right after later fixes, but that is on alerts used for fixing, so it is not the headline. Zero minute records: counting them, 5.0% of incidents reach 10 minutes instead of 14.6%.

## Limits, stated plainly
No rider testing has been done; a 10 minute script for five riders is ready in docs/rider-check.md. No manual screen reader test has been done; the accessibility checks are automated. No fresh frozen test yet: the newest City delay file still ends on September 30, 2026. Plan B uses the regular schedule, not live detours. The alert copy can be late. Scheduled runs so far: see the README. The page shows when the copy was made and last checked, marks it out of date after 90 minutes, and paste always works. Step free routing was considered and not added: elevator warnings are shown, but the open data used here has no station path graph for honest step free routes.

## Responsible use
No accounts and no tracking. Only the stop code is sent to the NextBus host (webservices.umoiq.com), never your alert or destination; like any web host, it also sees your IP address and the time of the request. Always follow TTC staff and announcements. Not affiliated with or endorsed by the Toronto Transit Commission.

Data: City of Toronto Open Data (TTC Subway Delay Data, TTC Routes and Schedules, TTC GTFS Realtime alerts, TTC Real Time Next Vehicle Arrival), all under the Open Government Licence Toronto. Contains information licensed under the Open Government Licence – Toronto. Bike Share Toronto station data from its GBFS feed (Open Government Licence Toronto in the City catalogue; the live feed is listed as CC BY 4.0).

## When it was built
SLAY HACKS began November 7, 2026. The public repo's first commit is from 6:08 a.m. Toronto time on November 15, 2026, and every change since is in its history. A private prototype script was written first, to test the idea on the July to September 2026 delay records; that test showed forecasts running high, and that is why the public project uses age weighting and recalibration. The exact date of that prototype is not recorded, so this write up does not claim a day for it. What carried over is that finding, not the prototype code.

## What's next
Score the alert time forecast log once the City publishes newer delays, run the rider check with five riders, and read the TTC's newer GTFS Realtime feed through a small relay.
