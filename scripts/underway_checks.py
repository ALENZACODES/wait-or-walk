"""Is it sound to condition the shipped bands on how long a delay has already lasted?

The page's "already underway" control uses the three calibrated models without refitting:
P(10+ | 5+) = P(10+) / P(5+) and P(20+ | 10+) = P(20+) / P(10+) (the bands are kept in order, so these are at most 1),
and the expected remaining delay from the bin averages of the ranges still possible.
This checks those conditional forecasts on the same test periods as train.py: among test delays that reached 5 minutes,
how well P(10+)/P(5+) predicts reaching 10; among those that reached 10, how well P(20+)/P(10+) predicts reaching 20;
and the expected remaining minutes against the logged remaining minutes (capped at 60). Same baselines, same intervals.
Note: the log gives total delay minutes, so "already 5 minutes in" is read as "the logged delay reached 5 minutes".
Run after train.py: python3 scripts/underway_checks.py [cache_dir]. Writes data/underway_checks.json.
"""
import json, os, sys, pickle
import numpy as np
sys.argv = sys.argv[:2]
import train as T0

ROOT = os.path.join(os.path.dirname(__file__), '..')
CACHE = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ttc'

def ratio(a, b):
    return np.where(b > 1e-9, np.minimum(a / np.maximum(b, 1e-9), 1.0), 0.0)

def div(a, b):
    return np.where(b > 1e-9, a / np.maximum(b, 1e-9), 0.0)

def remaining(p5, p10, p20, bm, elapsed):
    """Expected remaining logged minutes (capped at 60 in total) given the delay reached `elapsed` (0, 5 or 10)."""
    if elapsed == 0: return (1 - p5) * bm[0] + (p5 - p10) * bm[1] + (p10 - p20) * bm[2] + p20 * bm[3]
    if elapsed == 5: return div((p5 - p10) * bm[1] + (p10 - p20) * bm[2] + p20 * bm[3], p5) - 5
    return div((p10 - p20) * bm[2] + p20 * bm[3], p10) - 10

def main():
    P = pickle.load(open(os.path.join(CACHE, 'preds.pkl'), 'rb')); preds, calsets = P['preds'], P['calsets']
    rng = np.random.default_rng(20261119)
    out = {}
    for name, lo, num, den, hi in [('tenGivenFive', 5, 10, 5, 10), ('twentyGivenTen', 10, 20, 10, 20)]:
        parts = []
        for k in range(len(calsets)):
            D = preds[10][k]['minutes']; keep = D >= lo
            part = {'y': (D[keep] >= hi).astype(int), 'date': preds[10][k]['date'][keep]}
            for m in T0.METHODS: part[m] = ratio(preds[num][k][m][keep], preds[den][k][m][keep])
            parts.append(part)
        b = T0.block(parts, T0.METHODS, 'waitOrWalk', ['causeOnly', 'firstModel'], 'day', rng)
        y = np.concatenate([q['y'] for q in parts]); pw = np.concatenate([q['waitOrWalk'] for q in parts])
        b['actualShare'] = round(float(y.mean()), 3); b['meanForecast'] = round(float(pw.mean()), 3)
        out[name] = b
    rem = []
    for el in (0, 5, 10):
        pr, ac = [], []
        for k, cs in enumerate(calsets):
            D = preds[10][k]['minutes']; keep = D >= el
            r = remaining(preds[5][k]['waitOrWalk'], preds[10][k]['waitOrWalk'], preds[20][k]['waitOrWalk'], cs['binMeans'], el)[keep]
            pr.append(r); ac.append(np.minimum(D[keep], T0.WAIT_CAP) - el)
        pr, ac = np.concatenate(pr), np.concatenate(ac)
        rem.append({'elapsed': el, 'delays': int(len(ac)), 'expectedRemaining': round(float(pr.mean()), 2), 'loggedRemaining': round(float(ac.mean()), 2),
                    'correlation': round(float(np.corrcoef(pr, ac)[0, 1]), 3)})
    out['remaining'] = rem
    json.dump(out, open(os.path.join(ROOT, 'data', 'underway_checks.json'), 'w'), indent=1)
    for n in ['tenGivenFive', 'twentyGivenTen']:
        b = out[n]; print(n, b['delays'], b['actualShare'], b['meanForecast'], {m: {q: (v['value'], v['low'], v['high']) for q, v in b['methods'][m].items()} for m in b['methods']})
        print('  diffs', {m: {q: (v['value'], v['distinguishable']) for q, v in b['differences'][m].items()} for m in b['differences']})
    print(rem)

if __name__ == '__main__':
    main()
