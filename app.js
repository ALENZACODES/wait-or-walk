(function () {
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const VERSION = 'r5';
  let model = null, planb = null, ptimes = null;
  let state = { line: '', station: '', group: '', derived: new Set(), pending: null };
  const sync = () => { $('#line').value = state.line; $('#station').value = state.station; $('#group').value = state.group; ['line', 'station', 'group'].forEach((k) => tag(k, state.derived.has(k))); };
  const pct = (p) => Math.round(p * 100) + '%';
  const RARE = 100;
  const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const day = (iso) => { const [y, m, d] = iso.split('-').map(Number); return `${MON[m - 1]} ${d}, ${y}`; };
  const span = (s) => s.replace(/\d{4}-\d{2}-\d{2}/g, day);
  const LINE = { YU: 'Line 1', BD: 'Line 2', SHP: 'Line 4' };

  function fillSelects() {
    const sorted = model.stations.slice().sort((a, b) => a.label.localeCompare(b.label));
    const opts = sorted.map((s) => `<option value="${esc(s.name)}">${esc(s.label)}</option>`).join('');
    $('#station').innerHTML = '<option value="">Choose a station</option>' + opts;
    $('#dest').innerHTML = '<option value="">Not set, show every direction</option>' + opts;
    const order = ['medical', 'security', 'alarm', 'track_person', 'injury_track', 'fire', 'doors', 'signals', 'track', 'train', 'power', 'weather', 'cleaning', 'operations', 'other'];
    $('#group').innerHTML = '<option value="">Choose a cause</option>' + order.map((g) => `<option value="${g}">${esc(model.groups[g].label)}</option>`).join('');
    const now = WaitOrWalk.torontoNow();
    $('#time').value = WaitOrWalk.timeBucket(now.hour);
    $('#weekend').checked = now.weekend;
  }

  const current = () => ({ line: state.line, station: state.station, group: state.group, time: $('#time').value, weekend: $('#weekend').checked });
  const tag = (k, on) => { document.querySelector(`.tag[data-for="${k}"]`).hidden = !on; };

  function render() {
    const x = current();
    const s = model.stations.find((t) => t.name === x.station);
    if (s && !x.line && s.lines.length === 1 && !state.pending) { state.line = x.line = s.lines[0]; $('#line').value = x.line; }
    renderChoice();
    renderPlanB(state.pending || WaitOrWalk.mismatch(state, model) ? null : s);
    const ready = WaitOrWalk.canForecast(state, model);
    $('#empty').hidden = !!ready; $('#callBody').hidden = !ready;
    if (WaitOrWalk.mismatch(state, model)) { $('#empty').textContent = `No number: ${s.label} is not on ${LINE[x.line]}. Choose a matching line or station under “Check the details”.`; $('.result').className = 'card result'; return; }
    if (state.pending) { $('#empty').textContent = 'No number yet: the alert could mean more than one place. Pick one under the alert to see the call.'; $('.result').className = 'card result'; return; }
    if (!ready) {
      const miss = [!x.station && 'station', !x.line && 'line', !x.group && 'cause'].filter(Boolean);
      $('#empty').textContent = (x.station || x.group || x.line) ? `Choose the ${miss.length > 1 ? miss.slice(0, -1).join(', ') + ' and ' + miss[miss.length - 1] : miss[0]} under “Check the details” to see the call.` : 'Paste an alert above, or choose the station and cause under “Check the details”.';
      $('.result').className = 'card result';
      return;
    }
    const { p, raw } = WaitOrWalk.predict(model, x);
    const a = WaitOrWalk.advice(p);
    const bands = WaitOrWalk.predictBands(model, x);
    $('#pct').textContent = pct(p);
    $('#bands').innerHTML = bands.p5 === null ? '' : `<span><b>${pct(bands.p5)}</b> 5+ min</span><span class="on"><b>${pct(p)}</b> 10+ min</span><span><b>${pct(bands.p20)}</b> 20+ min</span>`;
    $('.result').className = 'card result ' + a.level;
    $('#advice').textContent = a.title + '.';
    $('#adviceText').textContent = a.text;
    const g = model.groups[x.group];
    $('#typical').textContent = `This cause: ${g.delays.toLocaleString('en-CA')} logged delays, ${g.longDelays.toLocaleString('en-CA')} of them 10 minutes or more; half were over in ${g.medianMinutes} minutes or less.`;
    const share = g.longDelays / g.delays;
    $('#reconcile').textContent = `Why ${pct(p)} and not ${pct(share)}: ${pct(share)} is every logged delay with this cause since January 2025 (${g.longDelays.toLocaleString('en-CA')} of ${g.delays.toLocaleString('en-CA')}). The estimate adjusts that for the station, the line, the time of day and the drop in long delays in 2026${g.recentShareLong !== null && g.recentDelays ? ` (in the latest 91 days, ${pct(g.recentShareLong)} of ${g.recentDelays} delays with this cause ran 10 minutes or more)` : ''}.`;
    const sd = (model.stationDelays || {})[x.station] || 0;
    const rare = [];
    if (g.delays < RARE) rare.push(`only ${g.delays} logged delays have this cause`);
    if (sd < RARE) rare.push(`only ${sd} logged delays happened at ${s ? s.label : x.station}`);
    $('#rare').hidden = !rare.length;
    $('#rare').textContent = rare.length ? `Rough estimate: ${rare.join(' and ')}, so treat this number as a guide.` : '';
    $('#why').innerHTML = WaitOrWalk.explain(model, x).map((e) => `<li class="${e.up ? 'up' : 'down'}">${esc(e.text)}.</li>`).join('');
    $('#drift').innerHTML = `<b>Drift correction:</b> <span class="drift-n">${pct(raw)}</span> before recalibration, <span class="drift-n">${pct(p)}</span> after. Long delays became rarer in 2026, so the shipped model is recalibrated on ${span(model.calibratedOn)}.`;
  }

  const KIND = { bus: 'bus', streetcar: 'streetcar', LRT: 'LRT (light rail)' };
  const clock = (m) => { const h = Math.floor(m / 60) % 24, mm = String(m % 60).padStart(2, '0'); return `${h % 12 || 12}:${mm} ${h < 12 ? 'a.m.' : 'p.m.'}`; };
  let ctx = null;
  const ymdWords = (y) => `${MON[+y.slice(4, 6) - 1]} ${+y.slice(6)}, ${y.slice(0, 4)}`;
  function timeContext() {
    const c = WaitOrWalk.torontoClock(new Date());
    const a = WaitOrWalk.activeServices(ptimes.calendar, c.ymd, c.dow), b = WaitOrWalk.activeServices(ptimes.calendar, c.prevYmd, c.prevDow);
    return { now: c.minutes, today: a.services, yesterday: b.services, covered: a.covered, ymd: c.ymd, range: WaitOrWalk.scheduleRange(ptimes.calendar) };
  }
  const inMin = (m) => (m - ctx.now <= 0 ? 'now' : 'in ' + (m - ctx.now) + ' min');
  function departures(refs) {
    if (!ctx.covered) return '';
    const next = WaitOrWalk.reachable(planb, ptimes.times, refs, ctx.today, ctx.yesterday, ctx.now, 3);
    if (!next.length) return '<br><span class="meta notnow">No departure you can still catch in the next 3 hours, after walking and 1 minute to board</span>';
    return `<br><span class="meta deps">Next you can catch: ${next.map((x) => `${clock(x.dep)} (${inMin(x.dep)})`).join(', ')}</span>`;
  }
  function arrival(r, destLabel) {
    if (!ctx.covered || !r.first || r.estimate === null) return '';
    if (r.transfer) return `<br><span class="meta eta">By the schedule: at ${esc(WaitOrWalk.labelFor(model, r.transfer))} about ${clock(r.first.arrive)}, then ${LINE[r.line]} to ${esc(destLabel)} about ${clock(r.estimate)} if the subway runs normally there</span>`;
    return `<br><span class="meta eta">By the schedule: at ${esc(destLabel)} about ${clock(r.estimate)}</span>`;
  }
  function access(r) {
    if (r.access === 1) return '<br><span class="meta">Schedule lists accessible boarding at this stop</span>';
    if (r.access === 2) return '<br><span class="meta">Schedule lists no accessible boarding at this stop</span>';
    return '';
  }
  function routeLine(r, extra, deps) {
    return `<li class="${r.kind}"><b>${esc(r.route)} ${esc(r.name)}</b> <span class="meta">${KIND[r.kind] || r.kind}</span>${r.heading ? `<br><span class="dir">${esc(r.heading)}</span>` : ''}<br><span class="meta">Board at ${esc(r.stop)}: ${r.metres} m, about ${WaitOrWalk.walkMinutes(r.metres)} min walk</span>${access(r)}${deps || ''}${extra || ''}</li>`;
  }

  function renderPlanB(s) {
    const out = $('#planbOut');
    if (!s) { out.innerHTML = WaitOrWalk.mismatch(state, model) ? '<p class="small">Fix the line or station first: they do not match.</p>' : '<p class="small">Choose the station of the delay to see nearby routes.</p>'; return; }
    ctx = timeContext();
    const dest = $('#dest').value;
    const d = dest && model.stations.find((t) => t.name === dest);
    const r = WaitOrWalk.planB(planb, s.name, dest);
    let html = `<p class="warn" id="planbWarn"><b>A scheduled alternative might not be running right now.</b> Routes can be detoured, short turned or replaced by shuttle buses. Check <a href="https://www.ttc.ca/service-alerts">TTC service alerts</a> before you walk.</p>`;
    const rg = ctx.range;
    if (ctx.covered) html += `<p class="small" id="planbClock">Departures you can still catch from now (${clock(ctx.now)} Toronto time), allowing the walk at 80 metres a minute in a straight line plus 1 minute to board. Updated every minute. Schedule data ends on ${ymdWords(rg.to)}.</p>`;
    else html += `<p class="warn" id="planbClock"><b>Schedule data ends on ${ymdWords(rg.to)}.</b> ${ctx.ymd > rg.to ? 'Today is after that' : `It starts on ${ymdWords(rg.from)}, and today is before that`}, so departure times are not shown. Routes and stops below are from that schedule and may have changed.</p>`;
    if (d && d.name !== s.name) {
      const ranked = ctx.covered ? WaitOrWalk.rankByArrival(planb, ptimes.times, r.direct.concat(r.via), ctx.today, ctx.yesterday, ctx.now, d.name) : r.direct.concat(r.via).map((x) => Object.assign({}, x, { first: null, estimate: null }));
      if (ranked.length) {
        html += `<h3>From ${esc(s.label)} towards ${esc(d.label)}${ctx.covered ? ', earliest scheduled arrival first' : ''}</h3>`;
        if (ctx.covered) html += '<p class="small">Ordered by the first departure you can catch plus the scheduled ride (and the scheduled subway time onward where you change). These are schedule estimates, not live times and not a promise of the quickest way.</p>';
        html += `<ul class="planb">${ranked.map((x) => routeLine(x, (x.transfer ? `<br><span class="meta">Ride past the delay, then change to ${LINE[x.line]} at ${esc(WaitOrWalk.labelFor(model, x.transfer))}</span>` : `<br><span class="meta">Goes to near ${esc(d.label)}: get off at ${esc(x.alight)}</span>`) + arrival(x, d.label), departures(x.refs))).join('')}</ul>`;
      }
      if (!ranked.length) {
        const all = WaitOrWalk.planB(planb, s.name, '');
        html += `<p>No scheduled bus, streetcar or LRT from ${esc(s.label)} reaches ${esc(d.label)}, or a station on the way. Routes near ${esc(s.label)} in every direction:</p>` + listAll(all);
      }
    } else {
      html += `<h3>Scheduled routes within 300 metres of ${esc(s.label)}, by direction</h3>` + listAll(r);
    }
    const nights = [...new Set(r.night.map((x) => x.route))];
    if (nights.length) html += `<p class="small"><b>Overnight:</b> ${nights.length > 1 ? `Blue Night routes ${nights.join(', ')} also stop` : `Blue Night route ${nights[0]} also stops`} here.</p>`;
    out.innerHTML = html;
  }

  function listAll(r) {
    if (!r.all.length) return '<p>No daytime bus, streetcar or LRT stop within 300 metres in the schedule data.</p>';
    return `<ul class="planb">${r.all.slice(0, 10).map((x) => routeLine(x, x.directions.map((q) => `<br><span class="dir">${esc(q.heading)}</span>${q.stop !== x.stop ? ` <span class="meta">from ${esc(q.stop)}, ${q.metres} m</span>` : ''}${q.next ? ` <span class="meta">next subway: ${esc(WaitOrWalk.labelFor(model, q.next))}</span>` : ''}${departures(q.refs)}`).join(''))).join('')}</ul>`;
  }

  function renderChoice() {
    const c = state.pending, box = $('#choice');
    box.hidden = !c;
    if (!c) { box.innerHTML = ''; return; }
    box.innerHTML = `<p><b>${esc(c.text)}</b></p><div class="opts">${c.options.map((o, i) => `<button type="button" data-opt="${i}">${esc(o.label)}</button>`).join('')}</div>`;
    box.querySelectorAll('[data-opt]').forEach((b) => b.addEventListener('click', () => { state = WaitOrWalk.chooseOption(state, c.options[+b.dataset.opt]); sync(); render(); }));
  }

  function readAlert() {
    const text = $('#alert').value.trim();
    $('#flags').innerHTML = ''; $('#example').hidden = true;
    if (!text) { state = WaitOrWalk.applyAlert(state, null); sync(); $('#readNote').textContent = ''; render(); return; }
    const r = WaitOrWalk.readAlert(text, model);
    // A field the alert does not mention goes back to empty, so nothing stale is kept from before.
    state = WaitOrWalk.applyAlert(state, r); sync();
    const got = [r.line && 'line', r.station && 'station', r.group && 'cause'].filter(Boolean);
    const miss = ['line', 'station', 'cause'].filter((k) => !got.includes(k));
    const and = (a) => a.length > 1 ? a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1] : a[0];
    $('#readNote').textContent = got.length ? `Read the ${and(got)} from the alert.${miss.length ? ` Not found: ${and(miss)}. Choose ${miss.length > 1 ? 'them' : 'it'} under “Check the details”.` : ' Check them under “Check the details”.'}` : 'Could not find a line, station or cause in that text. Choose them under “Check the details”.';
    $('#flags').innerHTML = r.flags.map((f) => `<li>${esc(f.text)}</li>`).join('');
    render();
  }

  const NAMES = { waitOrWalk: 'Wait or Walk', causeOnly: 'Cause only rule', firstModel: 'First model' };
  const ci = (x, d) => `${x.value.toFixed(d)} <span class="ci">(${x.low.toFixed(d)} to ${x.high.toFixed(d)})</span>`;
  // Differences in words, so no minus signs: higher says whether a bigger number is better for this measure.
  const word = (b, d, good, bad) => Math.abs(b) < Math.pow(10, -d) / 2 ? 'level' : `${Math.abs(b).toFixed(d)} ${b > 0 ? good : bad}`;
  const dci = (x, d, higher, good = 'better', bad = 'worse') => {
    const f = higher ? 1 : -1; const lo = Math.min(x.low * f, x.high * f), hi = Math.max(x.low * f, x.high * f);
    let range;
    if (lo > 0) range = `${lo.toFixed(d)} to ${hi.toFixed(d)} ${good}`;
    else if (hi < 0) range = `${(-hi).toFixed(d)} to ${(-lo).toFixed(d)} ${bad}`;
    else range = `${word(lo, d, good, bad)} to ${word(hi, d, good, bad)}`;
    return `${word(x.value * f, d, good, bad)} <span class="ci">(${range})</span>`;
  };
  const pts = (x) => ({ value: x.value * 100, low: x.low * 100, high: x.high * 100 });
  const yes = (x) => x.distinguishable ? 'yes' : '<b>no</b>';
  function methodRows(b, names) {
    names = names || NAMES;
    return Object.keys(names).map((k) => { const v = b.methods[k]; return `<tr class="${k === 'waitOrWalk' ? 'ours' : ''}"><td>${names[k]}</td><td>${ci(v.auc, 3)}</td><td>${ci(v.logLoss, 4)}</td><td>${ci(v.brier, 4)}</td><td>${ci(pts(v.calError), 1)} pts</td></tr>`; }).join('');
  }
  function diffRows(b, names, base) {
    names = names || NAMES;
    return Object.keys(b.differences).map((k) => { const v = b.differences[k]; return `<tr><td>${base || 'Wait or Walk'} vs ${names[k].toLowerCase()}</td><td>${dci(v.auc, 3, true)}<br><span class="meta">distinguishable: ${yes(v.auc)}</span></td><td>${dci(v.logLoss, 4, false)}<br><span class="meta">distinguishable: ${yes(v.logLoss)}</span></td><td>${dci(v.brier, 4, false)}<br><span class="meta">distinguishable: ${yes(v.brier)}</span></td><td>${dci(pts(v.calError), 1, false)} pts<br><span class="meta">distinguishable: ${yes(v.calError)}</span></td></tr>`; }).join('');
  }
  const MHEAD = '<thead><tr><th scope="col">Method</th><th scope="col">AUC, higher is better (95% interval)</th><th scope="col">Log loss, lower is better</th><th scope="col">Brier score, lower is better</th><th scope="col">Calibration error, lower is better</th></tr></thead>';
  const DHEAD = '<thead><tr><th scope="col">Compared</th><th scope="col">AUC</th><th scope="col">Log loss</th><th scope="col">Brier score</th><th scope="col">Calibration error</th></tr></thead>';
  const tbl = (head, body) => `<table>${head}<tbody>${body}</tbody></table>`;
  const mins2 = (x) => x.toFixed(2);
  const saved = (x) => dci(x, 2, true, 'min saved', 'min lost');
  function metrics(m) {
    const ev = m.evidence;
    $('#pooledTable').innerHTML = tbl(MHEAD, methodRows(ev.pooled));
    $('#pooledDiff').innerHTML = tbl(DHEAD, diffRows(ev.pooled));
    $('#dayTable').innerHTML = tbl(DHEAD, diffRows(ev.dayBlock.pooled));
    const surv = ev.survival, same = surv.filter((x) => x.byDelay === x.byDay).length;
    $('#survNote').textContent = `${same} of ${surv.length} conclusions are the same both ways (pooled and in each period, against both baselines, on all four measures).` + (same < surv.length ? ' Changed: ' + surv.filter((x) => x.byDelay !== x.byDay).map((x) => `${span(x.scope)}, ${NAMES[x.against].toLowerCase()}, ${x.metric}`).join('; ') + '.' : '');
    $('#bandsTable').innerHTML = ['5', '20'].map((k) => { const B = ev.bands[k]; return `<h4>${k}+ minutes (${pct(B.actualShare)} of test delays)</h4><div class="tablewrap">${tbl(MHEAD, methodRows(B.pooled))}</div><div class="tablewrap">${tbl(DHEAD, diffRows(B.pooled))}</div>`; }).join('');
    const CN = { cellShrunk: 'With station by cause pooling', waitOrWalk: 'Wait or Walk as shipped', cellRaw: 'Station by cause, no pooling' };
    $('#cellTable').innerHTML = `<div class="tablewrap">${tbl(MHEAD, methodRows(ev.cellShrinkage.pooled, CN))}</div><div class="tablewrap">${tbl(DHEAD, diffRows(ev.cellShrinkage.pooled, CN, 'Pooling'))}</div>`;
    const dv = ev.decisionValue;
    $('#decisionTable').innerHTML = `<table><thead><tr><th scope="col">Flag when the forecast is at least</th><th scope="col">Method</th><th scope="col">Share of 10+ minute delays flagged</th><th scope="col">False flag rate (short delays flagged)</th><th scope="col">Flagged delays that ran 10+ minutes</th></tr></thead><tbody>${dv.map((r) => `<tr class="${r.method === 'waitOrWalk' ? 'ours' : ''}"><td>${pct(r.threshold)}</td><td>${NAMES[r.method]}</td><td>${pct(r.longFlagged)}</td><td>${pct(r.falseFlagRate)}</td><td>${pct(r.flaggedThatWereLong)}</td></tr>`).join('')}</tbody></table>`;
    const ss = ev.stationSimulation, SN = { all: 'All delays', under10: 'Under 10 minutes', atLeast20: '20 minutes or more', atLeast30: '30 minutes or more' };
    $('#stationSimTable').innerHTML = `<table><thead><tr><th scope="col">Delays</th><th scope="col">Always wait</th><th scope="col">Always switch</th><th scope="col">Cause only rule</th><th scope="col">First model</th><th scope="col">Wait or Walk</th><th scope="col">Hindsight best</th><th scope="col">Wait or Walk against always wait (95% interval)</th><th scope="col">Wait or Walk against cause only</th></tr></thead><tbody>${['all', 'under10', 'atLeast20', 'atLeast30'].map((k) => { const r = ss.subsets[k]; return `<tr><td>${SN[k]} (${r.delays.toLocaleString('en-CA')})</td><td>${mins2(r.alwaysWait)}</td><td>${mins2(r.alwaysSwitch)}</td><td>${mins2(r.causeOnly)}</td><td>${mins2(r.firstModel)}</td><td><b>${mins2(r.waitOrWalk)}</b></td><td>${mins2(r.hindsightBest)}</td><td>${saved(r.savedVsWait_waitOrWalk)}</td><td>${saved(r.savedVs_causeOnly)}</td></tr>`; }).join('')}</tbody></table>`;
    $('#stationSimNote').textContent = `${ss.directionsWithAlternative.toLocaleString('en-CA')} of ${ss.directions.toLocaleString('en-CA')} delay and direction pairs had a scheduled alternative leaving within 3 hours; the median switch cost was ${ss.medianSwitchCost} extra minutes.`;
    const sim = ev.simulation;
    $('#simTable').innerHTML = `<table><thead><tr><th scope="col">Assumed extra minutes to switch</th><th scope="col">Always wait</th><th scope="col">Cause only rule</th><th scope="col">Wait or Walk</th><th scope="col">Hindsight best</th><th scope="col">Wait or Walk against cause only (95% interval)</th></tr></thead><tbody>${sim.rows.map((r) => `<tr><td>${r.switchCost} min</td><td>${r.alwaysWait.toFixed(2)}</td><td>${r.causeOnly.toFixed(2)}</td><td>${r.waitOrWalk.toFixed(2)}</td><td>${r.hindsightBest.toFixed(2)}</td><td>${dci(r.waitOrWalkMinusCauseOnly, 2, false, 'min fewer', 'min more')}</td></tr>`).join('')}</tbody></table>`;
    $('#sensTable').innerHTML = `<table><thead><tr><th scope="col">Half life</th><th scope="col">Recalibration window</th><th scope="col">AUC</th><th scope="col">Log loss</th><th scope="col">Calibration error</th></tr></thead><tbody>${ev.sensitivity.map((r) => `<tr class="${r.shipped ? 'ours' : ''}"><td>${r.halfLifeDays ? r.halfLifeDays + ' days' : 'none (equal weights)'}</td><td>${r.calibrationDays} days</td><td>${r.auc.toFixed(4)}</td><td>${r.logLoss.toFixed(4)}</td><td>${r.calError.toFixed(1)} pts${r.shipped ? ' (shipped)' : ''}</td></tr>`).join('')}</tbody></table>`;
    $('#periodTables').innerHTML = ev.periods.map((p, i) => `<h4>${span(p.test)} (${p.delays.toLocaleString('en-CA')} delays; average forecast ${pct(m.folds[i].waitOrWalk.meanPredicted)} vs ${pct(m.folds[i].actualShareLong)} actual)</h4><div class="tablewrap">${tbl(MHEAD, methodRows(p))}</div><div class="tablewrap">${tbl(DHEAD, diffRows(p))}</div>`).join('');
    // Calibration chart: predicted vs actual for each forecast band, pooled over the three tests.
    const b = m.pooled.reliability, W = 330, H = 220, P = 44, mx = 0.65;
    const X = (v) => P + (v / mx) * (W - P - 10), Y = (v) => H - 34 - (v / mx) * (H - 44);
    const ticks = [0, 0.2, 0.4, 0.6];
    let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Calibration chart: forecast against what happened"><line x1="${X(0)}" y1="${Y(0)}" x2="${X(mx)}" y2="${Y(mx)}" class="diag"/>`;
    svg += ticks.map((t) => `<line x1="${X(t)}" y1="${Y(0)}" x2="${X(t)}" y2="${Y(0) + 4}" class="ax"/><text x="${X(t)}" y="${Y(0) + 16}" text-anchor="middle">${pct(t)}</text><text x="${P - 6}" y="${Y(t) + 4}" text-anchor="end">${pct(t)}</text>`).join('');
    svg += `<line x1="${X(0)}" y1="${Y(0)}" x2="${X(mx)}" y2="${Y(0)}" class="ax"/><line x1="${X(0)}" y1="${Y(0)}" x2="${X(0)}" y2="${Y(mx)}" class="ax"/>`;
    svg += b.map((q) => `<circle cx="${X(q.predicted)}" cy="${Y(q.actual)}" r="${3 + Math.sqrt(q.delays) / 8}"><title>Forecast ${pct(q.predicted)}, actual ${pct(q.actual)}, ${q.delays} delays</title></circle>`).join('');
    svg += `<text x="${(W + P) / 2}" y="${H - 2}" text-anchor="middle">Forecast</text><text x="10" y="${(H - 34) / 2}" text-anchor="middle" transform="rotate(-90 10 ${(H - 34) / 2})">Actual</text></svg>`;
    $('#calib').innerHTML = svg;
    $('#calibNote').textContent = `Each dot is a forecast band over ${m.pooled.delays.toLocaleString('en-CA')} delays from the three evaluation periods; dots on the dashed line would be perfect. Every dot sits below the line, so forecasts run high: 3 to 4 points in the bands above 30%, up to 3 points below that. ` + b.map((q) => `${pct(q.predicted)} forecast, ${pct(q.actual)} actual`).join('; ') + '.';
    const months = Object.entries(m.monthlyShareLong);
    const max = Math.max(...months.map(([, v]) => v));
    $('#trendNote').textContent = `Tallest bar ${pct(max)}. Red: the three months used to recalibrate the shipped model (${months.slice(-3).map(([, v]) => pct(v)).join(', ')}).`;
    $('#trend').innerHTML = months.map(([k, v], i) => `<div class="${i >= months.length - 3 ? 'recent' : ''}" style="height:${Math.round((v / max) * 100)}%" title="${MON[+k.slice(5) - 1]} ${k.slice(0, 4)}: ${pct(v)}">${i % 3 === 0 ? `<span>${MON[+k.slice(5) - 1]} ${k.slice(2, 4)}</span>` : ''}</div>`).join('');
    $('#zeroCount').textContent = m.zeroMinuteRecordsExcluded.toLocaleString('en-CA');
  }

  let wired = false;
  function load() {
    $('#loading').hidden = false; $('#loadError').hidden = true;
    const get = (f) => fetch(f).then((r) => { if (!r.ok) throw new Error(f + ' ' + r.status); return r.json(); });
    const v = (f) => get(f + '?v=' + VERSION);
    Promise.all([v('data/model.json'), v('data/metrics.json'), v('data/planb.json'), v('data/planb_times.json')]).then(([mo, me, pb, pt]) => {
      model = mo; planb = pb; ptimes = pt;
      $('#baseThrough').textContent = day(mo.baseTrainedThrough); $('#calOn').textContent = span(mo.calibratedOn);
      fillSelects(); metrics(me);
      $('#loading').hidden = true; $('#app').hidden = false;
      if (!wired) {
        wired = true;
        ['#line', '#station', '#group'].forEach((id) => $(id).addEventListener('change', () => { const k = id.slice(1); state[k] = $(id).value; state.derived.delete(k); if (k !== 'group') state.pending = null; tag(k, false); render(); }));
        ['#time', '#weekend', '#dest'].forEach((id) => $(id).addEventListener('change', render));
        $('#alert').addEventListener('input', readAlert);
        document.querySelectorAll('[data-alert]').forEach((b) => b.addEventListener('click', () => {
          $('#alert').value = b.dataset.alert; readAlert();
          const res = $('.result'); res.classList.remove('flash'); void res.offsetWidth; res.classList.add('flash');
          if (res.getBoundingClientRect().top > window.innerHeight - 120) res.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }));
        $('#tableDetails').open = !window.matchMedia('(max-width: 700px)').matches;
      }
      // On phones, show one worked example straight away so the result is visible without scrolling.
      if (!$('#alert').value && window.matchMedia('(max-width: 700px)').matches) {
        $('#alert').value = document.querySelector('[data-worked]').dataset.alert; readAlert(); $('#dest').value = 'Jane'; $('#example').hidden = false;
      }
      render();
    }).catch(() => { $('#loading').hidden = true; $('#loadError').hidden = false; });
  }
  // Keep Plan B times current: re-render when the Toronto minute or the service date changes.
  setInterval(() => {
    if (!model || !ptimes || !ctx || $('#app').hidden) return;
    const c = WaitOrWalk.torontoClock(new Date());
    if (c.minutes !== ctx.now || c.ymd !== ctx.ymd) render();
  }, 5000);
  $('#retry').addEventListener('click', load);
  load();
})();
