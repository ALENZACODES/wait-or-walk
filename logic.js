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

  // Expected logged delay in minutes (capped at 60) from the three bands: P(under 5) m1 + P(5 to 10) m2 + P(10 to 20) m3 + P(20+) m4,
  // with m1 to m4 the average logged minutes in each range in the base training data (data/policy.json binMeans).
  function expectedDelay(b, bm) {
    if (!b || b.p5 === null || b.p20 === null || !bm) return null;
    return (1 - b.p5) * bm[0] + (b.p5 - b.p10) * bm[1] + (b.p10 - b.p20) * bm[2] + b.p20 * bm[3];
  }
  // The shipped decision rule: switch when the expected logged delay minus the scheduled switch cost reaches the margin
  // chosen on earlier data (data/policy.json). Switch cost: scheduled arrival by Plan B minus an on time subway arrival, at least 0.
  function switchCall(expected, cost, margin) {
    if (expected === null || cost === null || cost === undefined) return null;
    return { switch: expected - Math.max(cost, 0) >= margin, expected, cost: Math.max(cost, 0) };
  }

  // "Already underway": condition the same calibrated bands on the delay having reached 5 or 10 minutes, with no refit.
  // P(10+ | 5+) = P(10+) / P(5+) and P(20+ | 10+) = P(20+) / P(10+); the bands are kept in order (p5 >= p10 >= p20),
  // so each ratio is between 0 and 1 (clamped anyway). Expected remaining minutes use the bin averages of the ranges still
  // possible, minus the minutes already gone, floored at 0. Returns null when the conditioning band is (near) zero.
  // elapsed 0: headline is the 10+ chance; 5: chance of 10+ in total; 10: chance of 20+ in total.
  function underway(b, bm, elapsed) {
    if (!b || b.p5 === null || b.p20 === null || !bm) return null;
    const c = (x) => Math.min(Math.max(x, 0), 1);
    if (!elapsed) return { elapsed: 0, headline: b.p10, target: 10, chips: [[5, b.p5], [10, b.p10], [20, b.p20]], remaining: expectedDelay(b, bm) };
    if (elapsed === 5) {
      if (!(b.p5 > 1e-6)) return null;
      const q10 = c(b.p10 / b.p5), q20 = Math.min(c(b.p20 / b.p5), q10);
      const rem = ((b.p5 - b.p10) * bm[1] + (b.p10 - b.p20) * bm[2] + b.p20 * bm[3]) / b.p5 - 5;
      return { elapsed: 5, headline: q10, target: 10, chips: [[10, q10], [20, q20]], remaining: Math.max(rem, 0) };
    }
    if (elapsed === 10) {
      if (!(b.p10 > 1e-6)) return null;
      const q20 = c(b.p20 / b.p10);
      const rem = ((b.p10 - b.p20) * bm[2] + b.p20 * bm[3]) / b.p10 - 10;
      return { elapsed: 10, headline: q20, target: 20, chips: [[20, q20]], remaining: Math.max(rem, 0) };
    }
    return null;
  }

  // Overnight hours, the same band the model uses for its night time (midnight to 6 a.m.): when Blue Night routes matter.
  function isOvernight(minutes) { return minutes >= 0 && minutes < 360; }

  // x: {group, station, line, time, weekend}
  function predict(model, x) {
    const keys = featureKeys(x, model);
    let z = model.intercept;
    const parts = keys.map((k) => { const w = model.weights[k] || 0; z += w; return { key: k, weight: w }; });
    const raw = sig(z);
    const p = sig(model.platt.a * logit(raw) + model.platt.b);
    return { p, raw, parts };
  }

  // Chances of 5+, 10+ and 20+ minutes. Each band has its own model, trained and recalibrated the same way;
  // the bands are kept in order (5+ at least the 10+ chance, 20+ at most the 10+ chance), as in the evaluation.
  function predictBands(model, x) {
    const p10 = predict(model, x).p;
    const one = (b) => {
      if (!model.bands || !model.bands[b]) return null;
      const m = model.bands[b]; let z = m.intercept;
      for (const k of featureKeys(x, model)) z += m.weights[k] || 0;
      return sig(m.platt.a * logit(sig(z)) + m.platt.b);
    };
    const p5 = one('5'), p20 = one('20');
    return { p5: p5 === null ? null : Math.max(p5, p10), p10, p20: p20 === null ? null : Math.min(p20, p10) };
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
    if (p >= 0.35) return { level: 'high', title: 'High risk of a long delay', text: 'Incidents like this often run long. See the wait or switch line below.' };
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
    if (/planned|slower than usual|slow zone|reduced speed|while we (work|perform)|track work|maintenance|early closure|weekend closure/.test(t)) { out.planned = true; out.flags.push({ field: 'group', text: 'This looks like planned work or a slow zone, not an unplanned incident, so no delay forecast is shown. Check the TTC notice.' }); }
    for (const k of ['line', 'station', 'group']) if (out[k]) out.found.push(k);
    return out;
  }

  // Plan B from the schedule. pb: data/planb.json. from, to: station names (to may be empty).
  // Every entry carries refs: [pattern index, visit index] pairs, used to look up scheduled departures.
  function planB(pb, from, to) {
    const out = { direct: [], via: [], all: [], night: [] };
    const lineOf = (n) => Object.keys(pb.lines).filter((l) => pb.lines[l].includes(n));
    const base = (q, i) => ({ route: q.route, name: q.name, kind: q.kind, night: q.night, stop: q.visits[i].stop, metres: q.visits[i].metres, access: q.visits[i].access || 0 });
    if (!to || to === from) {
      const byRoute = new Map(), dirs = new Map();
      pb.patterns.forEach((q, pi) => {
        const i = q.visits.findIndex((v) => v.station === from);
        if (i < 0 || q.visits[i].end) return; // the trip ends here, so it cannot take you anywhere
        const key = q.route + '|' + q.heading;
        if (dirs.has(key)) { dirs.get(key).refs.push([pi, i]); return; }
        const r = byRoute.get(q.route) || Object.assign(base(q, i), { directions: [] });
        if (q.visits[i].metres < r.metres) Object.assign(r, { metres: q.visits[i].metres, stop: q.visits[i].stop, access: q.visits[i].access || 0 });
        const d = { heading: q.heading, next: (q.visits[i + 1] || {}).station || null, stop: q.visits[i].stop, metres: q.visits[i].metres, refs: [[pi, i]] };
        r.directions.push(d); dirs.set(key, d);
        byRoute.set(q.route, r);
      });
      for (const r of byRoute.values()) (r.night ? out.night : out.all).push(r);
      out.all.sort((a, b) => a.metres - b.metres || a.route.localeCompare(b.route, 'en', { numeric: true }));
      return out;
    }
    const fromLines = lineOf(from), toLines = lineOf(to);
    const shared = fromLines.find((l) => toLines.includes(l));
    const direct = new Map();
    pb.patterns.forEach((q, pi) => {
      const i = q.visits.findIndex((v) => v.station === from);
      if (i < 0) return;
      const j = q.visits.findIndex((v, k) => k > i && v.station === to);
      if (j < 0) return;
      const key = q.route + '|' + q.heading;
      if (direct.has(key)) { direct.get(key).refs.push([pi, i, j]); return; }
      direct.set(key, Object.assign(base(q, i), { heading: q.heading, alight: q.visits[j].stop, refs: [[pi, i, j]] }));
    });
    for (const r of direct.values()) (r.night ? out.night : out.direct).push(r);
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
    pb.patterns.forEach((q, pi) => {
      if (q.night || directRoutes.has(q.route)) return;
      const i = q.visits.findIndex((v) => v.station === from);
      if (i < 0) return;
      let pick = null;
      q.visits.forEach((v, j) => { if (j <= i) return; const u = useful.get(v.station); if (u && (!pick || u.rank > pick.u.rank)) pick = { v, u, j }; });
      if (!pick) return;
      const key = q.route + '|' + q.heading;
      const cur = best.get(key);
      if (cur && pick.u.rank === cur.rank) { cur.refs.push([pi, i, pick.j]); return; }
      if (!cur || pick.u.rank > cur.rank) best.set(key, Object.assign(base(q, i), { heading: q.heading, transfer: pick.v.station, line: pick.u.line, rank: pick.u.rank, refs: [[pi, i, pick.j]] }));
    });
    out.via = [...best.values()].sort((a, b) => b.rank - a.rank || a.metres - b.metres).slice(0, 6);
    return out;
  }

  // Schedule time helpers. cal: calendar block of data/planb_times.json. ymd: 'YYYYMMDD'. dow: 0 Monday to 6 Sunday.
  function activeServices(cal, ymd, dow) {
    const on = new Set(); let covered = false;
    for (const w of cal.weekly) if (w.from <= ymd && ymd <= w.to) { covered = true; if (w.days[dow]) on.add(w.s); }
    for (const [s, d, type] of cal.dates) if (d === ymd) { covered = true; if (type === 1) on.add(s); else on.delete(s); }
    return { services: on, covered };
  }
  function decodeTimes(str) {
    if (!str) return [];
    let t = 0; return str.split('.').map((x) => (t += parseInt(x, 36)));
  }
  // Next scheduled departures (minutes after midnight of today, may be under the current time for none) for a list of refs.
  function nextDepartures(times, refs, today, yesterday, nowMin, count) {
    const all = [];
    for (const [pi, vi] of refs) {
      const e = (times[pi] || [])[vi] || {};
      for (const s of today) for (const m of decodeTimes(e[s])) if (m >= nowMin) all.push(m);
      for (const s of yesterday) for (const m of decodeTimes(e[s])) if (m - 1440 >= nowMin) all.push(m - 1440);
    }
    return [...new Set(all)].sort((a, b) => a - b).slice(0, count || 3);
  }
  const BOARD_MINUTES = 1; // time allowed to board after walking to the stop
  const walkMinutes = (metres) => Math.max(1, Math.ceil(metres / 80)); // 80 metres a minute, about 4.8 km/h, straight line
  // Departures a rider can still catch: leaving at or after now + walking time + 1 minute to board, within the horizon.
  // refs: [pattern, boarding visit, optional visit where you get off]. Returns [{dep, arrive, walk}], earliest first.
  function reachable(pb, times, refs, today, yesterday, nowMin, count, horizon) {
    const all = new Map();
    for (const [pi, vi, vj] of refs) {
      const q = pb.patterns[pi]; if (!q) continue;
      const walk = walkMinutes(q.visits[vi].metres), earliest = nowMin + walk + BOARD_MINUTES;
      const ride = vj !== undefined && q.visits[vj] && q.visits[vi].ride !== undefined ? q.visits[vj].ride - q.visits[vi].ride : null;
      const e = (times[pi] || [])[vi] || {};
      const add = (m) => { if (m >= earliest && m - nowMin <= (horizon || 180)) { const cur = all.get(m); const arrive = ride === null ? null : m + ride; if (!cur || (arrive !== null && (cur.arrive === null || arrive < cur.arrive))) all.set(m, { dep: m, arrive, walk }); } };
      for (const s of today) for (const m of decodeTimes(e[s])) add(m);
      for (const s of yesterday) for (const m of decodeTimes(e[s])) add(m - 1440);
    }
    return [...all.values()].sort((a, b) => a.dep - b.dep).slice(0, count || 3);
  }
  // Scheduled subway running time between two stations on one line (minutes), or null.
  function subwayMinutes(pb, line, a, b) {
    const o = pb.lines[line], c = (pb.subwayMinutes || {})[line];
    if (!o || !c) return null;
    const i = o.indexOf(a), j = o.indexOf(b);
    return i < 0 || j < 0 ? null : Math.abs(c[j] - c[i]);
  }
  // Order Plan B entries by the scheduled arrival they allow: the first reachable departure plus the scheduled ride,
  // plus the scheduled subway time onward for ride past the delay entries. Entries without an estimate go last.
  function rankByArrival(pb, times, entries, today, yesterday, nowMin, dest) {
    return entries.map((r, k) => {
      const first = reachable(pb, times, r.refs, today, yesterday, nowMin, 1)[0] || null;
      let arrive = first && first.arrive !== null ? first.arrive : null, onward = null;
      if (arrive !== null && r.transfer) { onward = subwayMinutes(pb, r.line, r.transfer, dest); arrive = onward === null ? null : arrive + onward; }
      return Object.assign({}, r, { first, estimate: arrive, onward, order: k });
    }).sort((a, b) => (a.estimate === null) - (b.estimate === null) || (a.estimate || 0) - (b.estimate || 0) || a.order - b.order);
  }
  function scheduleRange(cal) {
    let from = null, to = null;
    for (const w of cal.weekly) { if (!from || w.from < from) from = w.from; if (!to || w.to > to) to = w.to; }
    return { from, to };
  }
  function torontoClock(date) {
    const f = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Toronto', year: 'numeric', month: '2-digit', day: '2-digit', hour: 'numeric', minute: '2-digit', hourCycle: 'h23', weekday: 'short' }).formatToParts(date || new Date());
    const g = (k) => f.find((p) => p.type === k).value;
    const dow = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].indexOf(g('weekday'));
    const ymd = g('year') + g('month') + g('day');
    const y = new Date(Date.UTC(+g('year'), +g('month') - 1, +g('day')) - 86400000);
    const prev = y.getUTCFullYear() + String(y.getUTCMonth() + 1).padStart(2, '0') + String(y.getUTCDate()).padStart(2, '0');
    return { ymd, prevYmd: prev, dow, prevDow: (dow + 6) % 7, minutes: Number(g('hour')) * 60 + Number(g('minute')) };
  }
  // The fixed clock the worked examples use, inside the schedule window, so they still work after the schedule data ends.
  const SIM = { ymd: '20261116', prevYmd: '20261115', dow: 0, prevDow: 6, minutes: 17 * 60 + 30, label: 'Simulated Monday, November 16, 2026, 5:30 p.m.' };
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
  // Station and line must match: a station that is not on the chosen line gives no number.
  function mismatch(state, model) {
    if (!model || !state.station || !state.line) return false;
    const s = model.stations.find((x) => x.name === state.station);
    return !!(s && !s.lines.includes(state.line));
  }
  function canForecast(state, model) { return !state.pending && !!(state.line && state.station && state.group) && !mismatch(state, model); }

  function torontoNow(date) {
    const f = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Toronto', hour: 'numeric', hourCycle: 'h23', weekday: 'short' }).formatToParts(date || new Date());
    const hour = Number(f.find((p) => p.type === 'hour').value);
    const wd = f.find((p) => p.type === 'weekday').value;
    return { hour, weekend: wd === 'Sat' || wd === 'Sun' };
  }

  return { predict, underway, SIM, isOvernight, expectedDelay, switchCall, predictBands, reachable, rankByArrival, subwayMinutes, scheduleRange, BOARD_MINUTES, explain, advice, readAlert, planB, applyAlert, chooseOption, canForecast, mismatch, activeServices, decodeTimes, nextDepartures, torontoClock, walkMinutes, timeBucket, torontoNow, labelFor, LABELS };
});
