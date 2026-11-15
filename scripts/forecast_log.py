"""Add one dated line to docs/forecast-log.md: the frozen shipped model scored on delays published after its training data.

Each run downloads the newest TTC Subway Delay Data since 2025 file and scores data/model.json, unchanged, on every delay
dated after model.json trainedThrough, against the cause only rule and the first model (scripts/frozen_test.py does the
scoring). The model is never refit for this log. Run it whenever the City updates the file (about monthly):
python3 scripts/forecast_log.py [cache_dir]
"""
import os, sys, datetime
sys.argv = sys.argv[:2]
import frozen_test as F

ROOT = os.path.join(os.path.dirname(__file__), '..')
LOG = os.path.join(ROOT, 'docs', 'forecast-log.md')
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
words = lambda iso: f"{MON[int(iso[5:7]) - 1]} {int(iso[8:10])}, {iso[:4]}"

def main():
    out = F.score()
    if out['delaysAfterFreeze']:
        m = out['byDay']['methods']; f = lambda k, q, d: f"{m[k][q]['value']:.{d}f}"
        res = (f"AUC {f('waitOrWalk', 'auc', 3)} (cause only {f('causeOnly', 'auc', 3)}, first model {f('firstModel', 'auc', 3)}); "
               f"log loss {f('waitOrWalk', 'logLoss', 4)}; Brier {f('waitOrWalk', 'brier', 4)}; calibration error {m['waitOrWalk']['calError']['value'] * 100:.1f} pts")
    else:
        res = 'No new delays yet, so no score'
    line = f"| {words(out['checked'])} | {words(out['latestDelayDate'])} | {out['delaysAfterFreeze']:,} | {res} |\n"
    open(LOG, 'a').write(line); print(line)

if __name__ == '__main__':
    main()
