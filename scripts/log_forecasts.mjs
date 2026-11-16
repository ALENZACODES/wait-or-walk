// Alert time forecast log: run by the alerts Action after each copy of the TTC feed. For every subway alert not logged
// before, it saves the forecast the page would have shown when the alert was first seen (first seen time, Toronto time
// of day and day type, the alert read by logic.js, the 5+, 10+ and 20+ chances, the model it came from) to
// data/alert_forecasts.jsonl, one line per alert, never edited afterwards. Each line also says when it was logged; a line
// logged more than 40 minutes after the alert was first seen is marked backfilled. Planned work is logged with no forecast.
// The log exists to be scored later against the City's delay log; it has not been scored, so it makes no accuracy claim.
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync, existsSync, appendFileSync } from 'node:fs';
const require = createRequire(import.meta.url);
const W = require('../logic.js');
const path = (f) => new URL('../data/' + f, import.meta.url);
const model = JSON.parse(readFileSync(path('model.json')));
const LOG = path('alert_forecasts.jsonl');

export function entry(id, a, model, loggedAt) {
  const when = new Date(a.firstSeen * 1000), now = W.torontoNow(when);
  const r = W.readAlert(a.header || '', model);
  const time = W.timeBucket(now.hour), base = { line: r.line || '', group: r.group || '', time, weekend: now.weekend };
  const places = r.choice ? r.choice.options.map((o) => ({ station: o.station, line: o.line || r.line || '' })) : r.station ? [{ station: r.station, line: r.line || '' }] : [];
  let forecasts = null, reason = null;
  if (r.planned) reason = 'planned work: no forecast';
  else if (!r.group) reason = 'cause not read from the alert';
  else if (!places.length) reason = 'station not read from the alert';
  else {
    forecasts = [];
    for (const pl of places) {
      const x = Object.assign({}, base, pl);
      if (!x.line || W.mismatch(x, model)) continue;
      const b = W.predictBands(model, x);
      forecasts.push({ station: pl.station, line: x.line, p5: +b.p5.toFixed(4), p10: +b.p10.toFixed(4), p20: +b.p20.toFixed(4) });
    }
    if (!forecasts.length) { forecasts = null; reason = 'line and station did not match'; }
  }
  const lg = loggedAt || new Date();
  // backfilled: logged more than 40 minutes after the alert was first seen (the log started after the alert), so not a forecast made at alert time
  return { id, firstSeen: when.toISOString(), loggedAt: lg.toISOString(), backfilled: lg - when > 40 * 60000, header: a.header, read: { line: r.line, station: r.station, group: r.group, planned: !!r.planned, choice: !!r.choice },
    time, weekend: now.weekend, forecasts, reason, model: { trainedThrough: model.trainedThrough, calibratedOn: model.calibratedOn } };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const hist = JSON.parse(readFileSync(path('alert_history.json'))).alerts;
  const seen = new Set(existsSync(LOG) ? readFileSync(LOG, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l).id) : []);
  if (!existsSync(LOG)) writeFileSync(LOG, '');
  const add = Object.entries(hist).filter(([id]) => !seen.has(id)).sort((a, b) => a[1].firstSeen - b[1].firstSeen);
  for (const [id, a] of add) appendFileSync(LOG, JSON.stringify(entry(id, a, model)) + '\n');
  console.log(`Logged ${add.length} new alert${add.length === 1 ? '' : 's'}; ${seen.size + add.length} in the log.`);
}
