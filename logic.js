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

  // Risk bands for the chance that a comparable logged incident delayed service 10 minutes or more.
  function advice(p) {
    if (p >= 0.35) return { level: 'high', title: 'High risk of a long delay', text: 'Worth checking another route now.' };
    if (p >= 0.15) return { level: 'moderate', title: 'Moderate risk of a long delay', text: 'Know your other route and check the alert again in a few minutes.' };
    return { level: 'low', title: 'Low risk of a long delay', text: 'Comparable incidents rarely held up service 10 minutes or more. Waiting is usually reasonable.' };
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
    const out = { group: null, station: null, line: null, found: [], flags: [], choice: null };
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
      if (i >= 0) cands.push({ i, len: alias.length + 1, name: name || (out.line === 'BD' ? 'Yonge' : 'Bloor'), byAlias: !name });
    }
    cands.sort((a, b) => a.i - b.i || b.len - a.len);
    const byAlias = new Set(cands.filter((c) => c.byAlias).map((c) => c.name));
    const distinct = [...new Set(cands.map((c) => c.name))];
    const st = (n) => model.stations.find((x) => x.name === n);
    const opt = (n, l, showLine) => { const s = st(n); const lab = s ? s.label : n; return { station: n, line: l || null, label: showLine && l && !/Line \d/.test(lab) ? `${lab} on ${LABELS[l]}` : lab }; };
    const LORDER = ['YU', 'BD', 'SHP'];
    // Expand one named station into the options a rider could mean.
    const expand = (n) => {
      if (byAlias.has(n) && !out.line) return [opt('Bloor', 'YU'), opt('Yonge', 'BD')];
      const s = st(n);
      if (out.line) return [opt(n, out.line)];
      if (s && s.lines.length > 1) return s.lines.slice().sort((a, b) => LORDER.indexOf(a) - LORDER.indexOf(b)).map((l) => opt(n, l, true));
      return [opt(n, s ? s.lines[0] : null)];
    };
    const options = distinct.flatMap(expand);
    if (options.length === 1) {
      out.station = options[0].station;
      if (!out.line) out.line = options[0].line;
    } else if (options.length > 1) {
      let text;
      if (distinct.length > 1) text = 'The alert names more than one station. Which one is the delay at?';
      else if (byAlias.size) text = 'Bloor-Yonge serves two lines and the alert does not say which. Which line?';
      else text = `${st(distinct[0]).label} serves more than one line. Which line?`;
      out.choice = { text, options };
    }
    if (out.line && out.station) { const s = st(out.station); if (s && !s.lines.includes(out.line)) out.flags.push({ field: 'station', text: `${s.label} is not on ${LABELS[out.line]}. Check the station.` }); }
    for (const k of ['line', 'station', 'group']) if (out[k]) out.found.push(k);
    return out;
  }

  // Plan B from the schedule. pb: data/planb.json. from, to: station names (to may be empty).
  function planB(pb, from, to) {
    const out = { direct: [], via: [], all: [], night: [] };
    const seen = new Set();
    const lineOf = (n) => Object.keys(pb.lines).filter((l) => pb.lines[l].includes(n));
    if (!to || to === from) {
      const byRoute = new Map();
      for (const q of pb.patterns) {
        const i = q.visits.findIndex((v) => v.station === from);
        if (i < 0) continue;
        const next = q.visits.slice(i + 1).map((v) => v.station);
        const key = q.route + '|' + q.heading;
        if (seen.has(key)) continue; seen.add(key);
        const r = byRoute.get(q.route) || { route: q.route, name: q.name, kind: q.kind, night: q.night, stop: q.visits[i].stop, metres: q.visits[i].metres, directions: [] };
        if (q.visits[i].metres < r.metres) { r.metres = q.visits[i].metres; r.stop = q.visits[i].stop; }
        r.directions.push({ heading: q.heading, next: next[0] || null });
        byRoute.set(q.route, r);
      }
      for (const r of byRoute.values()) (r.night ? out.night : out.all).push(r);
      out.all.sort((a, b) => a.metres - b.metres || a.route.localeCompare(b.route, 'en', { numeric: true }));
      return out;
    }
    const fromLines = lineOf(from), toLines = lineOf(to);
    const shared = fromLines.find((l) => toLines.includes(l));
    for (const q of pb.patterns) {
      const i = q.visits.findIndex((v) => v.station === from);
      if (i < 0) continue;
      const j = q.visits.findIndex((v, k) => k > i && v.station === to);
      const key = q.route + '|' + q.heading;
      if (j > 0) {
        if (seen.has(key)) continue; seen.add(key);
        (q.night ? out.night : out.direct).push({ route: q.route, name: q.name, kind: q.kind, night: q.night, heading: q.heading, stop: q.visits[i].stop, metres: q.visits[i].metres, alight: q.visits[j].stop });
      }
    }
    const directRoutes = new Set(out.direct.map((r) => r.route));
    // Otherwise: routes that carry you past the delay to a station closer to where you are going, then the subway onward.
    let useful = null;
    if (shared) {
      const o = pb.lines[shared], a = o.indexOf(from), b = o.indexOf(to);
      const between = a < b ? o.slice(a + 1, b) : o.slice(b + 1, a).reverse();
      useful = new Map(between.map((n, k) => [n, { rank: k, line: shared }]));
    } else {
      useful = new Map();
      for (const l of toLines) { const o = pb.lines[l], b = o.indexOf(to); o.forEach((n, k) => { if (n !== to && n !== from) useful.set(n, { rank: -Math.abs(k - b), line: l }); }); }
    }
    const best = new Map();
    for (const q of pb.patterns) {
      if (q.night || directRoutes.has(q.route)) continue;
      const i = q.visits.findIndex((v) => v.station === from);
      if (i < 0) continue;
      let pick = null;
      q.visits.slice(i + 1).forEach((v) => { const u = useful.get(v.station); if (u && (!pick || u.rank > pick.u.rank)) pick = { v, u }; });
      if (!pick) continue;
      const key = q.route + '|' + q.heading;
      const cur = best.get(key);
      if (!cur || pick.u.rank > cur.rank) best.set(key, { route: q.route, name: q.name, kind: q.kind, heading: q.heading, stop: q.visits[i].stop, metres: q.visits[i].metres, transfer: pick.v.station, line: pick.u.line, rank: pick.u.rank });
    }
    out.via = [...best.values()].sort((a, b) => b.rank - a.rank || a.metres - b.metres).slice(0, 6);
    return out;
  }

  // Page state helpers, kept here so the rules are tested without a browser.
  // state: { line, station, group, derived: Set of fields read from the alert, pending: choice or null }
  function applyAlert(state, r) {
    const next = { ...state, derived: new Set(state.derived), pending: r ? r.choice : null };
    for (const k of ['line', 'station', 'group']) {
      if (!r) { if (next.derived.has(k)) next[k] = ''; next.derived.delete(k); continue; }
      next[k] = r[k] || '';
      if (r[k]) next.derived.add(k); else next.derived.delete(k);
    }
    return next;
  }
  function chooseOption(state, o) {
    const next = { ...state, derived: new Set(state.derived), pending: null, station: o.station };
    if (o.line) next.line = o.line;
    next.derived.add('station'); if (o.line) next.derived.add('line');
    return next;
  }
  function canForecast(state) { return !state.pending && !!(state.line && state.station && state.group); }

  function torontoNow(date) {
    const f = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Toronto', hour: 'numeric', hourCycle: 'h23', weekday: 'short' }).formatToParts(date || new Date());
    const hour = Number(f.find((p) => p.type === 'hour').value);
    const wd = f.find((p) => p.type === 'weekday').value;
    return { hour, weekend: wd === 'Sat' || wd === 'Sun' };
  }

  return { predict, explain, advice, readAlert, planB, applyAlert, chooseOption, canForecast, timeBucket, torontoNow, labelFor, LABELS };
});
