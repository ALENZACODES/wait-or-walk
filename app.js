(function () {
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const VERSION = 'r8';
  let model = null, planb = null, ptimes = null, policy = null, best = null, checks = null, underwayChecks = null;
  // sim: the fixed example clock (WaitOrWalk.SIM) or null for live time; elapsed: the "already underway" setting.
  let sim = null, elapsed = 0, planned = false, live = null;
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
    liveTimeFields();
  }
  function liveTimeFields() {
    const now = WaitOrWalk.torontoNow();
    $('#time').value = WaitOrWalk.timeBucket(now.hour);
    $('#weekend').checked = now.weekend;
  }
  // The worked examples run on a fixed clock inside the schedule window; typing or pasting an alert goes back to live time.
  function setSim(on) {
    sim = on ? WaitOrWalk.SIM : null;
    $('#simBanner').hidden = !sim;
    if (sim) { $('#simLabel').textContent = sim.label; $('#time').value = WaitOrWalk.timeBucket(Math.floor(sim.minutes / 60)); $('#weekend').checked = sim.dow >= 5; }
    else liveTimeFields();
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
    $('#empty').hidden = !!ready; $('#callBody').hidden = !ready; if (!ready) verdict(null);
    if (planned) { $('#empty').hidden = false; $('#callBody').hidden = true; $('#empty').textContent = 'This is planned service work. The incident delay model does not apply.'; $('.result').className = 'card result planned'; verdict(null); return; }
    if (WaitOrWalk.mismatch(state, model)) { $('#empty').textContent = `No number: ${s.label} is not on ${LINE[x.line]}. Choose a matching line or station under “Check the details”.`; $('.result').className = 'card result'; return; }
    if (state.pending) { $('#empty').textContent = 'No number yet: the alert could mean more than one place. Pick one under the alert to see the call.'; $('.result').className = 'card result'; return; }
    if (!ready) {
      const miss = [!x.station && 'station', !x.line && 'line', !x.group && 'cause'].filter(Boolean);
      $('#empty').textContent = (x.station || x.group || x.line) ? `Choose the ${miss.length > 1 ? miss.slice(0, -1).join(', ') + ' and ' + miss[miss.length - 1] : miss[0]} under “Check the details” to see the call.` : 'Paste an alert above, or choose the station and cause under “Check the details”.';
      $('.result').className = 'card result';
      return;
    }
    const { p, raw } = WaitOrWalk.predict(model, x);
    const bands = WaitOrWalk.predictBands(model, x);
    const bm = policy && policy.binMeans;
    const u = WaitOrWalk.underway(bands, bm, elapsed) || WaitOrWalk.underway(bands, bm, 0);
    if (u) u.bands = bands;
    const h = u ? u.headline : p;
    $('#pct').textContent = pct(h);
    $('#pctlab').textContent = !u || !u.elapsed ? 'chance the recorded delay lasts 10 minutes or more, among comparable recorded TTC delays'
      : `chance it reaches ${u.target} minutes or more in total, among comparable recorded delays that reached ${u.elapsed}`;
    $('#scope').textContent = !u || !u.elapsed ? 'Not the chance your alert causes this delay, or your remaining wait.' : 'From the same models, given the minutes already gone. Not a promise of your remaining wait.';
    $('#bands').innerHTML = !u ? '' : u.chips.map(([k, q]) => `<span class="${k === u.target ? 'on' : ''}"><b>${pct(q)}</b> ${k}+ min${u.elapsed ? ' total' : ''}</span>`).join('');
    document.querySelectorAll('[data-elapsed]').forEach((b) => b.setAttribute('aria-pressed', String(+b.dataset.elapsed === (u ? u.elapsed : 0))));
    $('#meaning').textContent = !u || !u.elapsed
      ? `Among comparable recorded TTC delays, the model estimates a ${pct(p)} chance the recorded delay lasts 10 minutes or more. This is not the chance your current alert causes that delay, or your remaining wait. Comparable means delays in the TTC log since January 2025 with this cause, station, line, time of day and day type, as the model weighs them; records with 0 minutes are left out.`
      : `Among comparable recorded TTC delays that reached ${u.elapsed} minutes, the model estimates a ${pct(u.headline)} chance the recorded delay reached ${u.target} minutes or more in total (the ${u.target}+ chance divided by the ${u.elapsed}+ chance, from the same calibrated models, no refit). The log gives total minutes, not alert times, so “about ${u.elapsed} minutes in” is read as “the recorded delay has reached ${u.elapsed} minutes”. On the test periods these conditional chances averaged ${underwayChecks ? underwayNote(u.elapsed) : 'close to actual'}. This is not the chance your current alert causes that delay, or your remaining wait.`;
    const a = !u || !u.elapsed ? WaitOrWalk.advice(p) : u.elapsed === 5 ? WaitOrWalk.advice(u.headline)
      : { level: u.headline >= 0.35 ? 'high' : 'moderate', title: 'Already a long delay', text: `Comparable delays that reached 10 minutes went on to 20 or more ${pct(u.headline)} of the time.` };
    $('.result').className = 'card result ' + a.level;
    $('#advice').textContent = a.title + '.';
    $('#adviceText').textContent = a.text;
    verdict(u);
    const g = model.groups[x.group];
    $('#typical').textContent = `This cause: ${g.delays.toLocaleString('en-CA')} logged delays, ${g.longDelays.toLocaleString('en-CA')} of them 10 minutes or more; half were over in ${g.medianMinutes} minutes or less.`;
    const share = g.longDelays / g.delays;
    $('#reconcile').textContent = `${u && u.elapsed ? `The chance of 10+ minutes from the start is ${pct(p)}. ` : ''}Why ${pct(p)} and not ${pct(share)}: ${pct(share)} is every logged delay with this cause since January 2025 (${g.longDelays.toLocaleString('en-CA')} of ${g.delays.toLocaleString('en-CA')}). The estimate adjusts that for the station, the line, the time of day and the drop in long delays in 2026${g.recentShareLong !== null && g.recentDelays ? ` (in the latest 91 days, ${pct(g.recentShareLong)} of ${g.recentDelays} delays with this cause ran 10 minutes or more)` : ''}.`;
    const sd = (model.stationDelays || {})[x.station] || 0;
    const rare = [];
    if (g.delays < RARE) rare.push(`only ${g.delays} logged delays have this cause`);
    if (sd < RARE) rare.push(`only ${sd} logged delays happened at ${s ? s.label : x.station}`);
    $('#rare').hidden = !rare.length;
    $('#rare').textContent = rare.length ? `Rough estimate: ${rare.join(' and ')}, so treat this number as a guide.` : '';
    $('#why').innerHTML = WaitOrWalk.explain(model, x).map((e) => `<li class="${e.up ? 'up' : 'down'}">${esc(e.text)}.</li>`).join('');
    $('#drift').innerHTML = `<b>Drift correction:</b> <span class="drift-n">${pct(raw)}</span> before recalibration, <span class="drift-n">${pct(p)}</span> after. Long delays became rarer in 2026, so the shipped model is recalibrated on ${span(model.calibratedOn)}.`;
  }

  function underwayNote(el) {
    const c = underwayChecks[el === 5 ? 'tenGivenFive' : 'twentyGivenTen'];
    return `${pct(c.meanForecast)} against ${pct(c.actualShare)} actual (${c.delays.toLocaleString('en-CA')} test delays)`;
  }
  // The wait or switch verdict: expected (remaining) logged delay against the best scheduled switch, shipped rule and margin.
  function verdict(u) {
    const em = !u || u.remaining === null ? null : Math.round(u.remaining);
    const call = em !== null && best && WaitOrWalk.switchCall(u.remaining, best.cost, policy.margin);
    const just = !u || !u.elapsed, left = just ? '' : ' left';
    const lead = just ? 'assuming the incident has just begun, delays like this average' : `about ${u.elapsed} minutes in, comparable delays had on average`;
    const cap = (t) => t.charAt(0).toUpperCase() + t.slice(1);
    const tail = ' An estimate from recorded delays, not your remaining wait; always follow TTC announcements.';
    const ttc = '<a href="https://www.ttc.ca/service-alerts" target="_blank" rel="noopener">Check TTC service alerts</a>';
    let full = '', short = '';
    if (em !== null && call) {
      const w = call.switch ? 'switching' : 'waiting';
      full = `<b>Schedule comparison: ${w} looks better.</b> ${cap(lead)} about ${em} minutes${left}, against ${Math.round(call.cost)} extra minutes by Plan B (route ${esc(best.route)} to ${esc(best.dest)}, from the schedule).${call.switch ? ` Switching only helps if you can catch that bus and it runs on time: in the simulation, a missed or late bus erased the gain. ${ttc}.` : ''}${tail}`;
      short = `<b>Verdict: ${w} looks better</b> by the schedule, about ${em} minutes${left} against ${Math.round(call.cost)} by route ${esc(best.route.split(' ')[0])}${call.switch ? ', only if you can catch that bus and it runs on time' : ''}. <a href="#v-h">Why</a>`;
    } else if (em !== null) {
      const why = !$('#dest').value ? 'Choose where you are headed under Plan B to compare it with the best scheduled switch.' : ctx && !ctx.covered ? 'The schedule data has ended, so there is no switch to compare.' : 'No scheduled switch you can catch could be compared for that trip (the comparison needs a destination on the same line).';
      full = `<b>Schedule comparison:</b> ${cap(lead)} about ${em} minutes${left}. ${why}${tail}`;
      short = `<b>Verdict:</b> ${!$('#dest').value ? 'choose where you are headed under Plan B to compare waiting with switching.' : 'no scheduled switch to compare.'} <a href="#v-h">Details</a>`;
    }
    $('#suggest').innerHTML = full || 'Paste an alert to see the comparison.';
    $('#verdictShort').innerHTML = short; $('#verdictShort').hidden = !short;
    const bmn = policy && policy.binMeans, sh = (q) => Math.round(q * 100) + '%';
    if (!u || !bmn || em === null) { $('#mix').textContent = ''; return; }
    const b = u.bands;
    $('#mix').textContent = just
      ? `How ${pct(u.headline)} becomes about ${em} minutes: a ${sh(1 - b.p5)} chance of under 5 minutes (about ${Math.round(bmn[0])} on average), ${sh(b.p5 - b.p10)} of 5 to 10 (about ${Math.round(bmn[1])}), ${sh(b.p10 - b.p20)} of 10 to 20 (about ${Math.round(bmn[2])}) and ${sh(b.p20)} of 20 or more (about ${Math.round(bmn[3])}).`
      : `How about ${em} minutes${left}: the average recorded minutes of the ranges still possible (${u.elapsed === 5 ? `5 to 10: about ${Math.round(bmn[1])}, ` : ''}10 to 20: about ${Math.round(bmn[2])}, 20 or more: about ${Math.round(bmn[3])}), weighted by their chances given ${u.elapsed} minutes so far, minus the ${u.elapsed} minutes gone.`;
  }
  const KIND = { bus: 'bus', streetcar: 'streetcar', LRT: 'LRT (light rail)' };
  const clock = (m) => { const h = Math.floor(m / 60) % 24, mm = String(m % 60).padStart(2, '0'); return `${h % 12 || 12}:${mm} ${h < 12 ? 'a.m.' : 'p.m.'}`; };
  let ctx = null;
  const ymdWords = (y) => `${MON[+y.slice(4, 6) - 1]} ${+y.slice(6)}, ${y.slice(0, 4)}`;
  function timeContext() {
    const c = sim || WaitOrWalk.torontoClock(new Date());
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
    ctx = timeContext(); best = null;
    const dest = $('#dest').value;
    const d = dest && model.stations.find((t) => t.name === dest);
    const r = WaitOrWalk.planB(planb, s.name, dest);
    let html = `<p class="warn" id="planbWarn"><b>A scheduled alternative might not be running right now.</b> Routes can be detoured, short turned or replaced by shuttle buses. Check <a href="https://www.ttc.ca/service-alerts">TTC service alerts</a> before you walk.</p>`;
    const rg = ctx.range;
    if (ctx.covered) html += `<p class="small" id="planbClock">${sim ? `<b>${esc(sim.label)}.</b> Departures you could catch then` : `Departures you can still catch from now (${clock(ctx.now)} Toronto time)`}, allowing the walk at 80 metres a minute in a straight line plus 1 minute to board.${sim ? ' Paste your own alert for live times.' : ' Updated every minute.'} Schedule data ends on ${ymdWords(rg.to)}.</p>`;
    else html += `<p class="warn" id="planbClock"><b>Schedule data ends on ${ymdWords(rg.to)}.</b> ${ctx.ymd > rg.to ? 'Today is after that' : `It starts on ${ymdWords(rg.from)}, and today is before that`}, so departure times are not shown. Routes and stops below are from that schedule and may have changed.</p>`;
    if (d && d.name !== s.name) {
      const ranked = ctx.covered ? WaitOrWalk.rankByArrival(planb, ptimes.times, r.direct.concat(r.via), ctx.today, ctx.yesterday, ctx.now, d.name) : r.direct.concat(r.via).map((x) => Object.assign({}, x, { first: null, estimate: null }));
      const top = ranked.find((x) => x.estimate !== null);
      const line = $('#line').value, sub = WaitOrWalk.subwayMinutes(planb, line, s.name, d.name);
      if (ctx.covered && top && sub !== null) best = { cost: top.estimate - ctx.now - sub, route: `${top.route} ${top.name}`, dest: d.label };
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
    if (nights.length && WaitOrWalk.isOvernight(ctx.now)) html += `<p class="small"><b>Overnight:</b> ${nights.length > 1 ? `Blue Night routes ${nights.join(', ')} also stop` : `Blue Night route ${nights[0]} also stops`} here.</p>`;
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
    $('#flags').innerHTML = ''; $('#example').hidden = true; elapsed = 0;
    if (!text) { planned = false; state = WaitOrWalk.applyAlert(state, null); sync(); $('#readNote').textContent = ''; render(); return; }
    const r = WaitOrWalk.readAlert(text, model);
    planned = !!r.planned;
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
  const mg = (x) => (x === 0 ? '0 minutes' : `${Math.abs(x)} ${Math.abs(x) === 1 ? 'minute' : 'minutes'} ${x < 0 ? 'below' : 'above'}`);
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
    $('#foldTable').innerHTML = `<table><thead><tr><th scope="col">Test period</th><th scope="col">Base model trained on</th><th scope="col">Recalibrated on</th><th scope="col">Test delays</th></tr></thead><tbody>${m.folds.map((f) => `<tr><td>${span(f.test)}</td><td>Jan 1, 2025 to ${day(f.baseTrainedThrough)}</td><td>${span(f.calibratedOn)}</td><td>${f.testDelays.toLocaleString('en-CA')}</td></tr>`).join('')}<tr class="ours"><td>None: the shipped model</td><td>Jan 1, 2025 to ${day(model.baseTrainedThrough)}</td><td>${span(model.calibratedOn)}</td><td>not scored</td></tr></tbody></table>`;
    $('#firstTwoTable').innerHTML = tbl(MHEAD, methodRows(ev.pooledFirstTwo.byDelay)) + tbl(DHEAD, diffRows(ev.pooledFirstTwo.byDelay));
    const dp = ev.decisionPolicy;
    $('#policyTable').innerHTML = `<table><thead><tr><th scope="col">Delays</th><th scope="col">Always wait</th><th scope="col">Cause only at 35%</th><th scope="col">Old rule: 35%</th><th scope="col">20+ chance rule</th><th scope="col">Expected cost rule (shipped)</th><th scope="col">Expected cost against always wait (95% interval)</th><th scope="col">Expected cost against the old rule</th><th scope="col">Expected cost against cause only</th></tr></thead><tbody>${['all', 'under10', 'atLeast20', 'atLeast30'].map((k) => { const r = dp.subsets[k]; return `<tr><td>${SN[k]} (${r.delays.toLocaleString('en-CA')})</td><td>${mins2(r.alwaysWait)}</td><td>${mins2(r.causeOnly35)}</td><td>${mins2(r.current35)}</td><td>${mins2(r.p20Rule)}</td><td><b>${mins2(r.expectedCost)}</b></td><td>${saved(r.expectedCost_savedVsWait)}</td><td>${saved(r.expectedCost_savedVsCurrent)}</td><td>${saved(r.expectedCost_savedVsCause)}</td></tr>`; }).join('')}</tbody></table>`;
    $('#policyChosen').textContent = 'Picked on earlier data only: ' + dp.chosen.map((c) => `for ${span(c.test)}, on ${span(c.chosenOn)}: 20+ chance at least ${pct(c.p20Threshold)}, expected cost margin ${mg(c.expectedCostMargin)}`).join('; ') + `. Shipped: margin ${mg(policy.margin)}, picked the same way on ${span(policy.chosenOn)}.`;
    const SC = { asScheduled: 'As scheduled (1.3 m/s walk, 1 minute to board)', busLate5: 'Bus 5 minutes late', busLate10: 'Bus 10 minutes late', missedDeparture: 'First catchable departure missed', walk60: 'Walking at 1.0 m/s', board2: '2 minutes to board', board3: '3 minutes to board', allBad: 'All of these at once (5 late, missed, 1.0 m/s, 3 minutes)' };
    const st = checks.stress.subsets;
    $('#stressTable').innerHTML = `<table><thead><tr><th scope="col">What really happens (the rider still decides from the schedule)</th><th scope="col">All delays: against always wait (95% interval)</th><th scope="col">20+ minute delays: against always wait</th></tr></thead><tbody>${Object.keys(SC).map((k) => `<tr class="${k === 'asScheduled' ? 'ours' : ''}"><td>${SC[k]}</td><td>${saved(st.all[k].savedVsWait)}</td><td>${saved(st.atLeast20[k].savedVsWait)}</td></tr>`).join('')}</tbody></table>`;
    const rb = checks.robust.subsets;
    $('#robustTable').innerHTML = `<table><thead><tr><th scope="col">What really happens</th><th scope="col">Shipped rule against always wait</th><th scope="col">Late bus rule against always wait</th><th scope="col">Late bus rule against shipped (95% interval)</th></tr></thead><tbody>${Object.keys(SC).map((k) => `<tr class="${k === 'asScheduled' || k === 'busLate5' ? 'ours' : ''}"><td>${SC[k]}</td><td>${saved(st.all[k].savedVsWait)}</td><td>${saved(rb.all[k].savedVsWait)}</td><td>${saved(rb.all[k].robustMinusShipped)}</td></tr>`).join('')}</tbody></table>`;
    const r0 = rb.all.asScheduled.robustMinusShipped, r5 = rb.all.busLate5.robustMinusShipped;
    $('#robustNote').textContent = `All delays. Read honestly: it loses ${Math.abs(r0.value).toFixed(2)} minutes per delay as scheduled against the shipped rule (${Math.abs(r0.high).toFixed(2)} to ${Math.abs(r0.low).toFixed(2)}) and saves ${r5.value.toFixed(2)} when buses run 5 minutes late (${r5.low.toFixed(2)} to ${r5.high.toFixed(2)}); on delays of 20 minutes or more it gives up ${Math.abs(rb.atLeast20.asScheduled.robustMinusShipped.value).toFixed(2)} minutes as scheduled. It is ${checks.robust.ship ? 'shipped' : 'not shipped, because it is worse as scheduled'}. The card instead says to switch only if you can catch that bus and it runs on time.`;
    const U = underwayChecks, UH = '<thead><tr><th scope="col">Given the delay reached</th><th scope="col">Test delays</th><th scope="col">Forecast on average</th><th scope="col">Actual share</th><th scope="col">AUC, Wait or Walk (95% interval)</th><th scope="col">AUC, cause only</th><th scope="col">Calibration error</th></tr></thead>';
    const urow = (lab, c) => `<tr><td>${lab}</td><td>${c.delays.toLocaleString('en-CA')}</td><td>${pct(c.meanForecast)}</td><td>${pct(c.actualShare)}</td><td>${ci(c.methods.waitOrWalk.auc, 3)}</td><td>${c.methods.causeOnly.auc.value.toFixed(3)}</td><td>${(c.methods.waitOrWalk.calError.value * 100).toFixed(1)} pts</td></tr>`;
    $('#underwayTable').innerHTML = `<table>${UH}<tbody>${urow('5 minutes: chance of 10+ in total', U.tenGivenFive)}${urow('10 minutes: chance of 20+ in total', U.twentyGivenTen)}</tbody></table>`;
    const rm = U.remaining;
    $('#underwayNote').textContent = `The same test periods as above, no refit: the conditional chances are the band ratios of the per period models. They rank less well than the headline (once a delay has lasted 5 minutes, the easy short ones are gone) but stay level with or ahead of the cause only rule, and calibration is within ${Math.ceil(Math.max(U.tenGivenFive.methods.waitOrWalk.calError.value, U.twentyGivenTen.methods.waitOrWalk.calError.value) * 100)} points. Expected remaining minutes against logged remaining minutes (capped at 60): ${rm.map((r) => `from ${r.elapsed} minutes, ${r.expectedRemaining.toFixed(1)} expected against ${r.loggedRemaining.toFixed(1)} logged`).join('; ')}. The log gives total minutes, not alert times, so “about 5 minutes in” is read as “the recorded delay reached 5 minutes”.`;
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

  // A destination the rider chose before is filled in again for their own alerts (kept only in this browser).
  function savedDest() {
    try { const d = localStorage.getItem('wowDest'); if (d && !$('#dest').value && model.stations.some((t) => t.name === d)) { $('#dest').value = d; render(); } } catch (e) { /* storage off */ }
  }
  // A link that reopens this alert, destination and setting (nothing is stored on any server).
  function share() {
    const q = new URLSearchParams();
    if ($('#alert').value.trim()) q.set('alert', $('#alert').value.trim());
    if ($('#dest').value) q.set('dest', $('#dest').value);
    if (elapsed) q.set('in', String(elapsed));
    const url = location.origin + location.pathname + (q.toString() ? '?' + q : '');
    const done = (t) => { $('#shareNote').textContent = t; };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(() => done('Link copied.'), () => done(url));
    else done(url);
  }
  // The TTC's open subway alerts, copied into this site every 30 minutes by a scheduled job (data/live_alerts.json).
  const when = (sec) => { const d = new Date(sec * 1000), c = WaitOrWalk.torontoClock(d); return `${clock(c.minutes)} on ${ymdWords(c.ymd)}`; };
  function loadLive(get) {
    get('data/live_alerts.json?t=' + Math.floor(Date.now() / 60000)).then((L) => {
      live = L; const now = Date.now() / 1000;
      const act = L.alerts.filter((a) => !a.end || a.end > now);
      const age = Math.round((now - L.fetchedAt) / 60);
      $('#liveSum').textContent = `TTC subway alerts (${act.length}), copied ${when(L.fetchedAt)}`;
      $('#liveList').innerHTML = act.length ? act.map((a, i) => `<li><span>${esc(a.header)}</span> <button type="button" data-live="${i}">Use this alert</button></li>`).join('') : '<li>No subway alerts in the latest copy.</li>';
      $('#liveList').querySelectorAll('[data-live]').forEach((b) => b.addEventListener('click', () => { setSim(false); $('#alert').value = act[+b.dataset.live].header; readAlert(); savedDest(); }));
      $('#liveNote').textContent = `Copied from the TTC's open GTFS Realtime feed (Open Government Licence Toronto). The copy updates within about 30 minutes when the alerts change, and scheduled runs can be late${age > 120 ? `; this copy is ${Math.round(age / 60)} hours old` : ''}. For the newest alert, paste it from the TTC.`;
      $('#live').hidden = false;
    }).catch(() => { $('#live').hidden = true; });
  }

  let wired = false;
  function load() {
    $('#loading').hidden = false; $('#loadError').hidden = true;
    const get = (f) => fetch(f).then((r) => { if (!r.ok) throw new Error(f + ' ' + r.status); return r.json(); });
    const v = (f) => get(f + '?v=' + VERSION);
    Promise.all([v('data/model.json'), v('data/metrics.json'), v('data/planb.json'), v('data/planb_times.json'), v('data/policy.json'), v('data/decision_checks.json'), v('data/underway_checks.json')]).then(([mo, me, pb, pt, po, dc, uc]) => {
      model = mo; planb = pb; ptimes = pt; policy = po; checks = dc; underwayChecks = uc;
      $('#baseThrough').textContent = day(mo.baseTrainedThrough); $('#calOn').textContent = span(mo.calibratedOn);
      fillSelects(); metrics(me);
      $('#loading').hidden = true; $('#app').hidden = false;
      if (!wired) {
        wired = true;
        ['#line', '#station', '#group'].forEach((id) => $(id).addEventListener('change', () => { const k = id.slice(1); state[k] = $(id).value; state.derived.delete(k); if (k !== 'group') state.pending = null; tag(k, false); render(); }));
        ['#time', '#weekend', '#dest'].forEach((id) => $(id).addEventListener('change', render));
        $('#alert').addEventListener('input', () => { setSim(false); readAlert(); savedDest(); });
        $('#dest').addEventListener('change', () => { try { if ($('#dest').value && !sim) localStorage.setItem('wowDest', $('#dest').value); } catch (e) { /* storage off */ } });
        $('#liveTime').addEventListener('click', () => { setSim(false); render(); });
        document.querySelectorAll('[data-elapsed]').forEach((b) => b.addEventListener('click', () => { elapsed = +b.dataset.elapsed; render(); }));
        $('#shareBtn').addEventListener('click', share);
        $('#pasteBtn').addEventListener('click', () => {
          if (!navigator.clipboard || !navigator.clipboard.readText) { $('#alert').focus(); $('#readNote').textContent = 'Paste the alert into the box (long press or Ctrl+V).'; return; }
          navigator.clipboard.readText().then((t) => { setSim(false); $('#alert').value = t; readAlert(); savedDest(); }).catch(() => { $('#alert').focus(); $('#readNote').textContent = 'Could not read the clipboard. Paste the alert into the box (long press or Ctrl+V).'; });
        });
        document.querySelectorAll('[data-alert]').forEach((b) => b.addEventListener('click', () => {
          setSim(true); $('#alert').value = b.dataset.alert; readAlert(); $('#dest').value = b.dataset.dest || ''; render();
          const res = $('.result'); res.classList.remove('flash'); void res.offsetWidth; res.classList.add('flash');
          if (res.getBoundingClientRect().top > window.innerHeight - 120) res.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }));
        $('#tableDetails').open = !window.matchMedia('(max-width: 700px)').matches;
      }
      // On phones, show one worked example straight away so the result is visible without scrolling.
      const q = new URLSearchParams(location.search);
      if (q.get('alert') && !$('#alert').value) {
        $('#alert').value = q.get('alert').slice(0, 600); readAlert();
        if (q.get('dest') && model.stations.some((t) => t.name === q.get('dest'))) $('#dest').value = q.get('dest');
        if (['5', '10'].includes(q.get('in'))) elapsed = +q.get('in');
      } else if (!$('#alert').value && window.matchMedia('(max-width: 700px)').matches) {
        setSim(true); $('#alert').value = document.querySelector('[data-worked]').dataset.alert; readAlert(); $('#dest').value = 'Jane';
      }
      loadLive(get);
      render();
    }).catch(() => { $('#loading').hidden = true; $('#loadError').hidden = false; });
  }
  // Keep Plan B times current: re-render when the Toronto minute or the service date changes.
  setInterval(() => {
    if (!model || !ptimes || !ctx || sim || $('#app').hidden) return;
    const c = WaitOrWalk.torontoClock(new Date());
    if (c.minutes !== ctx.now || c.ymd !== ctx.ymd) render();
  }, 5000);
  $('#retry').addEventListener('click', load);
  load();
})();
