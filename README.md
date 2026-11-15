# Wait or Walk

The subway just stopped. Will it be two minutes or twenty? Paste a TTC subway alert, or pick the line, station and cause, and Wait or Walk gives the chance the delay lasts 10 minutes or more, the reasons behind that number, and the buses and streetcars within a short walk.

Live: https://alenzacodes.github.io/wait-or-walk/

Built by John Khan in Toronto, Ontario for SLAY HACKS 2026.

## How it works

1. **Read the alert.** `logic.js` pulls the line, the station and the cause out of the alert text (for example "Line 2: Delays at Kipling due to a person at track level"). Every value stays editable.
2. **Score it.** A logistic regression model, trained in Python with scikit-learn and run in the browser, scores five things an alert tells you: cause, station, line, time of day and weekend.
3. **Explain it.** The page lists the factors that pushed the chance up or down most.
4. **Plan B.** For the station, the bus and streetcar routes with a stop within 300 metres, from the TTC schedule (GTFS).

## The model

- **Data:** TTC Subway Delay Data since 2025 (City of Toronto Open Data, refreshed Oct 26, 2026): every logged subway delay from Jan 1, 2025 to Sep 30, 2026. Kept: Lines 1, 2 and 4, delays over 0 minutes (16,548 delays). Target: 10 minutes or more.
- **Causes a rider can see:** the TTC's 120 or so internal delay codes are grouped into the 15 causes alerts actually say, such as "medical emergency", "person at track level" or "signal problem". The model only uses information you have when the alert appears.
- **Fixing the drift:** long delays became rarer in 2026 (about 19% of delays in early 2025, about 12% in summer 2026). The first model kept forecasting the old rate. Wait or Walk now (a) weights each delay by age with a 180 day half life and (b) recalibrates its output (Platt scaling) on the latest 91 days, fitted on a model that never saw those days.
- **Rare causes:** cause features get lighter shrinkage than station features, so a rare but serious cause such as a personal injury at track level is not pulled towards average.

## Honest results

Each fold is trained only on data before its test months.

| Test months | Method | AUC | Log loss | Average forecast vs actual |
|---|---|---|---|---|
| Apr to Jun 2026 (2,631 delays) | Cause only rule | 0.737 | 0.3568 | 17% vs 14% |
| | First model | 0.760 | 0.3472 | 17% vs 14% |
| | **Wait or Walk** | **0.764** | **0.3466** | 17% vs 14% |
| Jul to Sep 2026 (2,248 delays) | Cause only rule | 0.761 | 0.3225 | 16% vs 12% |
| | First model | 0.770 | 0.3217 | 16% vs 12% |
| | **Wait or Walk** | **0.772** | **0.3132** | **13% vs 12%** |

The cause carries most of the signal; station, line and time add a little ranking power. The recalibration fixes the overestimate in the latest months (13% forecast vs 12% actual), but it could not see the spring 2026 drop coming, because the months it calibrated on (Jan to Mar 2026) still had many long delays. All numbers are in `data/metrics.json` and are rebuilt by the training script.

## Tests

```
node tests/test_logic.mjs
```

GitHub Actions runs them on every push. They check that the browser gives the same probability as the trained Python model on 30 held out delays (within 0.0001), the cause ordering, the advice thresholds, alert reading, the Toronto clock, the station data, and that the published metrics still beat the cause only rule.

## Rebuild the model

```
pip install pandas numpy scikit-learn
python3 scripts/train.py /tmp/ttc
```

The script downloads both open datasets into the cache folder, then writes `data/model.json`, `data/metrics.json` and `data/parity.json`.

## Run locally

```
python3 -m http.server 8080
```

## Limits

An estimate, not a promise. Rare causes rest on few cases (fire or smoke: 94 delays; personal injury at track level: 34). Plan B uses straight line distance and the regular schedule, not live shuttle buses. Data: City of Toronto Open Data under the Open Government Licence Toronto.

## License

MIT. See `LICENSE`.
