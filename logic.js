/* Wait or Walk: model scoring, explanation and alert reading. No network. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.WaitOrWalk = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  const sig = (z) => 1 / (1 + Math.exp(-z));
  const logit = (p) => { const q = Math.min(Math.max(p, 1e-6), 1 - 1e-6); return Math.log(q / (1 - q)); };

  function timeBucket(hour) {
    if (hour <= 5) return 'night';
    if (hour <= 9) return 'am_peak';
    if (hour <= 15) return 'midday';
    if (hour <= 19) return 'pm_peak';
    return 'evening';
  }

  function featureKeys(x, model) {
    const known = new Set(model.stations.map((s) => s.name));
    return ['group=' + x.group, 'station=' + (known.has(x.station) ? x.station : 'Other'), 'line=' + x.line, 'time=' + x.time].concat(x.weekend ? ['weekend'] : []);
  }

  // x: {group, station, line, time, weekend}
  function predict(model, x) {
    const keys = featureKeys(x, model);
    let z = model.intercept;
    const parts = keys.map((k) => { const w = model.weights[k] || 0; z += w; return { key: k, weight: w }; });
    const raw = sig(z);
    const p = sig(model.platt.a * logit(raw) + model.platt.b);
    return { p, raw, parts };
  }

  const LABELS = { night: 'overnight (before 6 a.m.)', am_peak: 'morning rush (6 to 10 a.m.)', midday: 'midday (10 a.m. to 4 p.m.)', pm_peak: 'evening rush (4 to 8 p.m.)', evening: 'evening (8 p.m. on)', YU: 'Line 1', BD: 'Line 2', SHP: 'Line 4' };

  const SHORT = { night: 'overnight', am_peak: 'morning rush', midday: 'midday', pm_peak: 'evening rush', evening: 'evening' };

  // Plain words for the biggest pushes up and down.
  function explain(model, x) {
    const { parts } = predict(model, x);
    return parts
      .filter((q) => Math.abs(q.weight) >= 0.05)
      .sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight))
      .slice(0, 4)
      .map((q) => {
        const [kind, val] = q.key.includes('=') ? q.key.split('=') : ['weekend', 'weekend'];
        let what;
        if (kind === 'group') what = `Cause (${model.groups[val].label.toLowerCase()})`;
        else if (kind === 'station') what = val === 'Other' ? 'Location (between stations or in a yard)' : `Station (${labelFor(model, val)})`;
        else if (kind === 'line') what = LABELS[val];
        else if (kind === 'time') what = `Time of day (${SHORT[val]})`;
        else what = 'Weekend';
        return { text: `${what} ${q.weight > 0 ? 'raises' : 'lowers'} the odds`, up: q.weight > 0, weight: q.weight };
      });
  }

  function labelFor(model, name) { const s = model.stations.find((t) => t.name === name); return s ? s.label : name; }

  function advice(p) {
    if (p >= 0.35) return { call: 'walk', text: 'Lean towards walking to a bus or streetcar.' };
    if (p >= 0.15) return { call: 'either', text: 'Could go either way. Give it a few minutes, but know your other route.' };
    return { call: 'wait', text: 'Most delays like this clear in a few minutes. Waiting is usually fine.' };
  }

  // Order matters: more specific phrases first.
  const CAUSES = [
    ['injury_track', /personal injury|person struck|struck by|collision with a person|priority one/],
    ['track_person', /(person|someone|individual|trespasser|unauthori[sz]ed)[^.]{0,30}(at|on) (the )?track|track level|on the tracks/],
    ['fire', /\bfire\b|smoke/],
    ['medical', /medical|ill (customer|passenger|rider)|injured (customer|passenger|rider)|sick (customer|passenger)/],
    ['security', /security|police|disorderly|assault|altercation|unruly|fight/],
    ['alarm', /alarm|\bpaa\b/],
    ['doors', /\bdoors?\b/],
    ['weather', /weather|\bice\b|icy|snow|freezing/],
    ['power', /power|electrical/],
    ['cleaning', /clean|unsanitary|graffiti|spill/],
    ['signals', /signal/],
    ['track', /track|switch|\brail\b|work zone|track work/],
    ['train', /mechanical|train problem|disabled train|brake|equipment|stalled train/],
    ['operations', /operator|crew|schedule|regulat|service adjustment/]
  ];
  const STATION_ALIASES = { 'bloor-yonge': null, 'bloor yonge': null, 'dundas': 'TMU', 'eglinton west': 'Cedarvale', 'vmc': 'Vaughan Metropolitan Centre', 'sheppard': 'Sheppard-Yonge', 'yonge-sheppard': 'Sheppard-Yonge' };

  function readAlert(text, model) {
    const t = ' ' + String(text || '').toLowerCase().replace(/st\.\s/g, 'st ').replace(/\s+/g, ' ') + ' ';
    const out = { group: null, station: null, line: null, found: [] };
    if (/line 1\b|yonge.university|\byus?\b/.test(t)) out.line = 'YU';
    else if (/line 2\b|bloor.danforth|\bbd\b/.test(t)) out.line = 'BD';
    else if (/line 4\b|sheppard line/.test(t)) out.line = 'SHP';
    for (const [g, re] of CAUSES) if (re.test(t)) { out.group = g; break; }
    // Station: earliest mention in the text wins (alerts say "between A and B").
    const cands = [];
    const ts = t.replace(/yonge.university|bloor.danforth|sheppard line|line [124]/g, (m) => ' '.repeat(m.length));
    for (const s of model.stations) {
      if (s.name === 'Bloor' || s.name === 'Yonge') continue; // only through "Bloor-Yonge"
      const names = [s.name.toLowerCase(), s.label.toLowerCase()];
      for (const n of names) { const i = ts.search(new RegExp('[^a-z]' + n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '[^a-z]')); if (i >= 0) cands.push({ i, len: n.length, name: s.name }); }
    }
    for (const [alias, name] of Object.entries(STATION_ALIASES)) {
      const i = ts.search(new RegExp('[^a-z]' + alias + '[^a-z]'));
      if (i >= 0) cands.push({ i, len: alias.length + 1, name: name || (out.line === 'BD' ? 'Yonge' : 'Bloor') });
    }
    cands.sort((a, b) => a.i - b.i || b.len - a.len);
    if (cands.length) out.station = cands[0].name;
    if (!out.line && out.station) { const s = model.stations.find((x) => x.name === out.station); if (s && s.lines.length === 1) out.line = s.lines[0]; }
    for (const k of ['line', 'station', 'group']) if (out[k]) out.found.push(k);
    return out;
  }

  function torontoNow(date) {
    const f = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Toronto', hour: 'numeric', hourCycle: 'h23', weekday: 'short' }).formatToParts(date || new Date());
    const hour = Number(f.find((p) => p.type === 'hour').value);
    const wd = f.find((p) => p.type === 'weekday').value;
    return { hour, weekend: wd === 'Sat' || wd === 'Sun' };
  }

  return { predict, explain, advice, readAlert, timeBucket, torontoNow, labelFor };
});
