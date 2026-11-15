# Forecast log: the frozen model on newly published delays

This is a plan, not results yet. The shipped model (`data/model.json`, trained on delays up to September 30, 2026) is frozen. Each time the City of Toronto publishes newer TTC subway delays, `scripts/forecast_log.py` scores that exact model, never refit, on every delay dated after September 30, 2026, and adds one dated line below. It reports the same measures as the evaluation (AUC, log loss, Brier score and calibration error, with 95% intervals resampling whole days in `docs/frozen-test-<date>.json`) against the same two baselines (the cause only rule and the first model, both fit only on data up to September 30, 2026). Every line stays, whatever it shows.

| Checked | Newest delay in the file | Delays after September 30, 2026 | Result |
|---|---|---|---|
| Nov 15, 2026 | Sep 30, 2026 | 0 | No new delays yet, so no score |
