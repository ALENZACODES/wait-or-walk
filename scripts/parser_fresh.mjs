// Fresh test set for the frozen parser. The parser in logic.js was frozen at the tag in data/freeze.json. Every subway
// alert the alerts Action first sees after that time is a fresh test case: it was never used to write or fix the parser.
// Labels go in data/alerts_fresh_labels.json, set by hand from the alert text alone (ideally by someone other than the
// author, without looking at what the page or the log read). This script counts the fresh alerts, scores the labelled
// ones with the same scoring as scripts/parser_eval.mjs, and writes data/parser_fresh.json. It refuses to score if
// logic.js no longer matches the frozen hash, so a score here is always for the frozen parser.
// Run: node scripts/parser_fresh.mjs
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { score } from './parser_eval.mjs';
const require = createRequire(import.meta.url);
const file = (f) => new URL('../' + f, import.meta.url);
const freeze = JSON.parse(readFileSync(file('data/freeze.json')));
const sha = createHash('sha256').update(readFileSync(file('logic.js'))).digest('hex');
const frozenAt = Date.parse(freeze.frozenAt) / 1000;
const hist = JSON.parse(readFileSync(file('data/alert_history.json'))).alerts;
const fresh = Object.entries(hist).filter(([, a]) => a.firstSeen > frozenAt).sort((a, b) => a[1].firstSeen - b[1].firstSeen);
const labels = existsSync(file('data/alerts_fresh_labels.json')) ? JSON.parse(readFileSync(file('data/alerts_fresh_labels.json'))).alerts : [];
const byId = new Map(labels.map((x) => [String(x.id), x]));
const labelled = fresh.filter(([id]) => byId.has(id)).map(([id, a]) => ({ id, text: a.header || '', label: byId.get(id).label }));
const out = {
  tag: freeze.tag, frozenAt: freeze.frozenAt, parserMatchesFreeze: sha === freeze.files['logic.js'],
  alertsSinceFreeze: fresh.length, labelled: labelled.length,
  firstSeen: fresh.map(([id, a]) => ({ id, firstSeen: new Date(a.firstSeen * 1000).toISOString() })),
  score: labelled.length && sha === freeze.files['logic.js'] ? score(labelled) : null,
  note: 'Alerts first seen by the alerts job after the parser was frozen. Not used to write or fix the parser. Unscored until labelled by hand.'
};
writeFileSync(file('data/parser_fresh.json'), JSON.stringify(out, null, 1) + '\n');
console.log(`Fresh test set: ${out.alertsSinceFreeze} alert${out.alertsSinceFreeze === 1 ? '' : 's'} since the freeze, ${out.labelled} labelled${out.score ? `; station ${out.score.station.recall}%, cause ${out.score.cause.recall}%` : ''}${out.parserMatchesFreeze ? '' : '; logic.js differs from the freeze, not scored'}.`);
