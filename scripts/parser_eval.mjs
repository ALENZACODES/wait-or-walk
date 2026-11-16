// Parser accuracy on real TTC alerts with hand set labels (data/alerts_labelled.json).
// Scores line, station and cause read from the alert text, and the planned work flag, for each split.
// Run: node scripts/parser_eval.mjs [--write]   (--write saves data/parser_eval.json)
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
const require = createRequire(import.meta.url);
const W = require('../logic.js');
const load = (f) => JSON.parse(readFileSync(new URL('../data/' + f, import.meta.url)));
const model = load('model.json');
const L = load('alerts_labelled.json');

export function score(alerts) {
  const n = alerts.length, c = { line: 0, stationOk: 0, stationWrong: 0, stationMissed: 0, causePred: 0, causeOk: 0, causeWrong: 0, causeKnown: 0, incidents: 0,
    plannedTP: 0, plannedFP: 0, plannedFN: 0, ready: 0 };
  const errors = [];
  for (const a of alerts) {
    const r = W.readAlert(a.text, model), lab = a.label, err = [];
    if (r.line === lab.line) c.line++; else err.push(`line ${r.line} (label ${lab.line})`);
    const want = [...new Set(lab.stations)].sort();
    const got = r.choice ? [...new Set(r.choice.options.map((o) => o.station))].sort() : r.station ? [r.station] : [];
    if (!got.length) { c.stationMissed++; err.push(`no station (label ${want.join(', ')})`); }
    else if (got.join('|') === want.join('|')) c.stationOk++;
    else { c.stationWrong++; err.push(`station ${got.join(', ')} (label ${want.join(', ')})`); }
    if (lab.planned) { if (r.planned) c.plannedTP++; else { c.plannedFN++; err.push('planned work not flagged'); } }
    else {
      if (r.planned) { c.plannedFP++; err.push('flagged as planned work'); }
      c.incidents++;
      if (lab.cause !== 'other') c.causeKnown++;
      if (r.group) { c.causePred++; if (r.group === lab.cause) c.causeOk++; else { c.causeWrong++; err.push(`cause ${r.group} (label ${lab.cause})`); } }
      else if (lab.cause !== 'other') err.push(`no cause (label ${lab.cause})`);
      if (r.line === lab.line && want.length === 1 && got.join('|') === want.join('|') && !r.choice && r.group === lab.cause && !r.planned) c.ready++;
    }
    if (err.length) errors.push({ id: a.id, text: a.text, errors: err });
  }
  const pct = (a, b) => (b ? Math.round((1000 * a) / b) / 10 : null);
  const singles = alerts.filter((a) => !a.label.planned && new Set(a.label.stations).size === 1).length;
  return {
    alerts: n, incidents: c.incidents, planned: n - c.incidents,
    line: { correct: c.line, accuracy: pct(c.line, n) },
    station: { correct: c.stationOk, wrong: c.stationWrong, missed: c.stationMissed, precision: pct(c.stationOk, c.stationOk + c.stationWrong), recall: pct(c.stationOk, n), note: 'correct means the one station named, or for alerts naming two or more stations, a choice listing exactly those stations' },
    cause: { predicted: c.causePred, correct: c.causeOk, wrong: c.causeWrong, labelledKnown: c.causeKnown, precision: pct(c.causeOk, c.causePred), recall: pct(c.causeOk, c.causeKnown) },
    plannedWork: { truePositive: c.plannedTP, falsePositive: c.plannedFP, falseNegative: c.plannedFN, precision: pct(c.plannedTP, c.plannedTP + c.plannedFP), recall: pct(c.plannedTP, c.plannedTP + c.plannedFN) },
    readyWithoutHelp: { count: c.ready, of: singles, share: pct(c.ready, singles), note: 'single station incident alerts where line, station and cause were all read correctly with no question asked' },
    errors
  };
}
if (import.meta.url === `file://${process.argv[1]}`) {
  const out = { source: L.source, labelRules: L.labelRules, split: L.split };
  for (const s of ['development', 'held out']) out[s === 'held out' ? 'heldOut' : s] = score(L.alerts.filter((a) => a.split === s));
  out.all = score(L.alerts);
  if (process.argv.includes('--write')) writeFileSync(new URL('../data/parser_eval.json', import.meta.url), JSON.stringify(out, null, 1));
  const brief = (k) => { const x = out[k]; return `${k}: ${x.alerts} alerts; line ${x.line.accuracy}%; station precision ${x.station.precision}% recall ${x.station.recall}% (${x.station.wrong} wrong, ${x.station.missed} missed); cause precision ${x.cause.precision}% recall ${x.cause.recall}% (${x.cause.wrong} wrong); planned precision ${x.plannedWork.precision}% recall ${x.plannedWork.recall}%; ready ${x.readyWithoutHelp.count}/${x.readyWithoutHelp.of}`; };
  console.log(['development', 'heldOut', 'all'].map(brief).join('\n'));
  if (process.argv.includes('--errors')) for (const e of out.all.errors) console.log(' -', e.errors.join('; '), '|', e.text.slice(0, 110));
  if (process.argv.includes('--check') && out.all.errors.filter((e) => !(e.errors.length === 1 && /^no cause \(label other\)/.test(e.errors[0]))).length) { console.error('Parser errors on labelled alerts'); process.exit(1); }
}
