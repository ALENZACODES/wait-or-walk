// Freeze check. The model, the verdict rule and the alert parser were frozen for judging at the tag in data/freeze.json:
// logic.js (parser, model maths, wait or switch rule, live safety gate), data/model.json, data/policy.json and
// data/decision_checks.json (which settings ship). This fails if any of them changes, so a change after the freeze has to
// be a deliberate bug fix that updates data/freeze.json and is listed in docs/freeze.md. The automated alerts commits do
// not touch these files.
// Run: node scripts/freeze_check.mjs [--write]   (--write records the current hashes; only when freezing)
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const file = (f) => new URL('../' + f, import.meta.url);
const FILES = ['logic.js', 'data/model.json', 'data/policy.json', 'data/decision_checks.json'];
const sha = (f) => createHash('sha256').update(readFileSync(file(f))).digest('hex');
const fz = JSON.parse(readFileSync(file('data/freeze.json')));
if (process.argv.includes('--write')) {
  fz.files = Object.fromEntries(FILES.map((f) => [f, sha(f)]));
  writeFileSync(file('data/freeze.json'), JSON.stringify(fz, null, 1) + '\n');
  console.log('Recorded', FILES.length, 'hashes');
} else {
  const changed = FILES.filter((f) => fz.files[f] !== sha(f));
  console.log(changed.length ? `Changed since the freeze (${fz.tag}): ${changed.join(', ')}` : `Frozen files unchanged since ${fz.tag} (${FILES.length} files).`);
  if (changed.length) process.exit(1);
}
