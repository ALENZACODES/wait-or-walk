# Wait or Walk

The subway just stopped. Will it be two minutes or twenty? Paste a TTC subway alert and Wait or Walk shows how often comparable logged incidents delayed subway service 10 minutes or more, the reasons behind that number, and the buses and streetcars a short walk away that head where you are going.

Live: https://alenzacodes.github.io/wait-or-walk/

Built by John Khan in Toronto, Ontario for SLAY HACKS 2026.

## How it works

1. **Read the alert.** `logic.js` pulls the line, the station and the cause out of the alert text (for example "Line 2: Delays at Kipling due to a person at track level"). Anything it reads is tagged "from alert, please check". Anything it cannot find is left empty, never carried over from before, and uncertain matches are flagged: an alert that names more than one station, Bloor-Yonge without a line, or a station that is not on the named line.
2. **Score it.** A logistic regression model, trained in Python with scikit-learn and run in the browser, scores five things an alert tells you: cause, station, line, time of day and weekend.
3. **Explain it.** The page lists the factors that pushed the chance up or down most, the number of logged delays behind the cause (with a warning under 100), and the forecast before and after the drift correction.
4. **Plan B.** From the TTC schedule (GTFS), every regular stop pattern of every bus and streetcar route, with the subway stations it passes within 300 metres in order. Without a destination you see each nearby route by direction and the next subway station it reaches. Pick where you are headed and you see the routes that go from the delayed station to near your destination in the right direction, and otherwise the routes that carry you past the delay to a station on the way, then the subway onward. Blue Night routes are listed separately.

## What the number means

The TTC logs each incident with the minutes it delayed subway service. The number is the estimated chance that an incident like this one, logged with more than 0 minutes of delay, delayed service 10 minutes or more. It is not your own remaining wait. Records with 0 minutes of delay (30,515 on Lines 1, 2 and 4) are left out.

The risk bands are a plain language summary: under 15% low, 15% to 35% moderate, 35% and up high ("worth checking another route now").

## The model

- **Data:** TTC Subway Delay Data since 2025 (City of Toronto Open Data, refreshed Oct 26, 2026): every logged subway delay from Jan 1, 2025 to Sep 30, 2026. Kept: Lines 1, 2 and 4, delays over 0 minutes (16,548 delays). Target: 10 minutes or more.
- **Causes a rider can see:** the TTC's 124 delay codes are grouped into the 15 causes alerts actually say, such as "medical emergency", "person at track level" or "signal problem".
- **Drift:** long delays became rarer in 2026 (about 19% of delays in early 2025, about 12% in summer 2026). Each delay is weighted by age with a 180 day half life, and the output is recalibrated (Platt scaling).
- **One process, tested as shipped:** the base model is trained on everything before the last 91 days, Platt scaling is fitted on those 91 days, and that pair is shipped with no refit. The shipped model: base trained through Jul 1, 2026, recalibrated on Jul 2 to Sep 30, 2026.
- **Rare causes:** cause features get lighter shrinkage than station features, so a rare but serious cause such as a personal injury at track level is not pulled towards average.

## Honest results

Each test runs the shipped process exactly: the base model stops 91 days before the test months, Platt scaling uses those 91 days, and the test months are used once, for scoring. The cause only rule is recalibrated the same way.

| Test months | Method | AUC | Log loss | Average forecast vs actual |
|---|---|---|---|---|
| Jan to Mar 2026 (2,576 delays) | Cause only rule | 0.685 | 0.4340 | 18% vs 18% |
| | First model (no recency, no recalibration) | 0.731 | 0.4151 | 18% vs 18% |
| | **Wait or Walk** | **0.724** | **0.4189** | 18% vs 18% |
| Apr to Jun 2026 (2,631 delays) | Cause only rule | 0.729 | 0.3593 | 17% vs 14% |
| | First model | 0.760 | 0.3472 | 17% vs 14% |
| | **Wait or Walk** | **0.758** | **0.3484** | 17% vs 14% |
| Jul to Sep 2026 (2,248 delays) | Cause only rule | 0.760 | 0.3167 | 13% vs 12% |
| | First model | 0.770 | 0.3217 | 16% vs 12% |
| | **Wait or Walk** | **0.769** | **0.3154** | 14% vs 12% |

What this shows:

- Wait or Walk ranks incidents better than the cause only rule in all three tests and has lower log loss in all three.
- Against the first model it is about level: better log loss in the latest test, slightly worse in the two earlier ones. The first model learns from the three most recent months, which Wait or Walk sets aside for recalibration.
- Calibration, pooled over the 7,455 test delays: forecasts ran up to 4 points high in every band (for example 24% forecast vs 22% actual, 35% vs 31%), likely because long delays kept getting rarer after each recalibration window. The page draws this as a chart.

An earlier version reported 0.772 AUC and 0.3132 log loss for the latest months. That figure came from a process that fitted the recalibration on one model and applied it to a refit model, so it did not match what was shipped. The numbers above replace it.

All numbers are in `data/metrics.json` and are rebuilt by the training script.

## Tests

```
node tests/test_logic.mjs
```

GitHub Actions runs them on every push. They check that the browser code gives the same probability as the Python model on 30 example inputs (within 0.0001; an implementation check, not an accuracy test), the cause ordering, the risk bands, alert reading and its uncertainty flags, the Toronto clock, the station data, Plan B direction and destination cases, and that every test fold keeps the base, recalibration and test periods in order and still beats the cause only rule.

## Rebuild the data

```
pip install pandas numpy scikit-learn
python3 scripts/train.py /tmp/ttc
python3 scripts/build_planb.py /tmp/ttc
```

`train.py` downloads both open datasets into the cache folder, then writes `data/model.json`, `data/metrics.json` and `data/parity.json`. `build_planb.py` reads the cached schedule and writes `data/planb.json`.

## Run locally

```
python3 -m http.server 8080
```

The page needs a connection to load its data files. If they fail to load it says so and offers a retry.

## Limits

An estimate, not a promise. Rare causes rest on few cases (fire or smoke: 94 delays; personal injury at track level: 34), and the page says so. Plan B uses straight line distance and the regular schedule, not live detours or shuttle buses. It has not been tested with riders. Data: City of Toronto Open Data under the Open Government Licence Toronto.

## License

MIT. See `LICENSE`.
