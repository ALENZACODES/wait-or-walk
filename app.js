(function () {
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  let model = null, planb = null;
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
    renderPlanB(state.pending ? null : s);
    const ready = WaitOrWalk.canForecast(state);
    $('#empty').hidden = !!ready; $('#callBody').hidden = !ready;
    if (state.pending) { $('#empty').textContent = 'No number yet: the alert could mean more than one place. Pick one under the alert to see the call.'; $('.result').className = 'card result'; return; }
    if (!ready) {
      const miss = [!x.station && 'station', !x.line && 'line', !x.group && 'cause'].filter(Boolean);
      $('#empty').textContent = (x.station || x.group || x.line) ? `Choose the ${miss.length > 1 ? miss.slice(0, -1).join(', ') + ' and ' + miss[miss.length - 1] : miss[0]} under “Check the details” to see the call.` : 'Paste an alert above, or choose the station and cause under “Check the details”.';
      $('.result').className = 'card result';
      return;
    }
    const { p, raw } = WaitOrWalk.predict(model, x);
    const a = WaitOrWalk.advice(p);
    $('#pct').textContent = pct(p);
    $('.result').className = 'card result ' + a.level;
    $('#advice').textContent = a.title + '.';
    $('#adviceText').textContent = a.text;
    const g = model.groups[x.group];
    $('#typical').textContent = `This cause: ${g.delays.toLocaleString('en-CA')} logged delays, ${g.longDelays.toLocaleString('en-CA')} of them 10 minutes or more; half were over in ${g.medianMinutes} minutes or less.`;
    const sd = (model.stationDelays || {})[x.station] || 0;
    const rare = [];
    if (g.delays < RARE) rare.push(`only ${g.delays} logged delays have this cause`);
    if (sd < RARE) rare.push(`only ${sd} logged delays happened at ${s ? s.label : x.station}`);
    $('#rare').hidden = !rare.length;
    $('#rare').textContent = rare.length ? `Rough estimate: ${rare.join(' and ')}, so treat this number as a guide.` : '';
    if (s && !s.lines.includes(x.line)) { $('#rare').hidden = false; $('#rare').textContent = `${s.label} is not on ${LINE[x.line]}. Check the line and station.`; }
    $('#why').innerHTML = WaitOrWalk.explain(model, x).map((e) => `<li class="${e.up ? 'up' : 'down'}">${esc(e.text)}.</li>`).join('');
    $('#drift').innerHTML = `<b>Drift correction:</b> <span class="drift-n">${pct(raw)}</span> before recalibration, <span class="drift-n">${pct(p)}</span> after. Long delays became rarer in 2026, so the shipped model is recalibrated on ${span(model.calibratedOn)}.`;
  }

  function routeLine(r, extra) {
    return `<li class="${r.kind}"><b>${esc(r.route)} ${esc(r.name)}</b> <span class="meta">${r.kind}</span>${r.heading ? `<br><span class="dir">${esc(r.heading)}</span>` : ''}<br><span class="meta">Board at ${esc(r.stop)}, about ${r.metres} m</span>${extra || ''}</li>`;
  }

  function renderPlanB(s) {
    const out = $('#planbOut');
    if (!s) { out.innerHTML = '<p class="small">Choose the station of the delay to see nearby routes.</p>'; return; }
    const dest = $('#dest').value;
    const d = dest && model.stations.find((t) => t.name === dest);
    const r = WaitOrWalk.planB(planb, s.name, dest);
    let html = '';
    if (d && d.name !== s.name) {
      if (r.direct.length) html += `<h3>Goes from ${esc(s.label)} to near ${esc(d.label)}</h3><ul class="planb">${r.direct.map((x) => routeLine(x, `<br><span class="meta">Get off at ${esc(x.alight)}</span>`)).join('')}</ul>`;
      if (r.via.length) html += `<h3>${r.direct.length ? 'Also: ride' : 'No single scheduled route goes there. Ride'} past the delay, then take the subway</h3><ul class="planb">${r.via.map((x) => routeLine(x, `<br><span class="meta">Change to ${LINE[x.line]} at ${esc(WaitOrWalk.labelFor(model, x.transfer))}</span>`)).join('')}</ul>`;
      if (!r.direct.length && !r.via.length) {
        const all = WaitOrWalk.planB(planb, s.name, '');
        html += `<p>No bus or streetcar from ${esc(s.label)} reaches ${esc(d.label)}, or a station on the way, in the schedule. Routes near ${esc(s.label)} in every direction:</p>` + listAll(all);
      }
    } else {
      html += `<h3>Scheduled routes within 300 metres of ${esc(s.label)}, by direction</h3>` + listAll(r);
    }
    const nights = [...new Set(r.night.map((x) => x.route))];
    if (nights.length) html += `<p class="small"><b>Overnight:</b> ${nights.length > 1 ? `Blue Night routes ${nights.join(', ')} also stop` : `Blue Night route ${nights[0]} also stops`} here.</p>`;
    out.innerHTML = html;
  }

  function listAll(r) {
    if (!r.all.length) return '<p>No daytime bus or streetcar stop within 300 metres in the schedule data.</p>';
    return `<ul class="planb">${r.all.slice(0, 10).map((x) => routeLine(x, x.directions.map((q) => `<br><span class="dir">${esc(q.heading)}</span>${q.next ? ` <span class="meta">next subway: ${esc(WaitOrWalk.labelFor(model, q.next))}</span>` : ''}`).join(''))).join('')}</ul>`;
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

  function metrics(m) {
    const rows = [];
    for (const f of m.folds) {
      const items = [['Overall rate', f.overallRate], ['Cause only rule, recalibrated the same way', f.causeOnlyRate], ['First model (no recency, no recalibration)', f.firstModel], ['Wait or Walk', f.waitOrWalk]];
      items.forEach(([name, s], i) => rows.push(`<tr class="${name === 'Wait or Walk' ? 'ours' : ''}"><td>${i === 0 ? `${span(f.test)} (${f.testDelays.toLocaleString('en-CA')} delays)` : ''}</td><td>${name}</td><td>${s.auc.toFixed(3)}</td><td>${s.logLoss.toFixed(4)}</td><td>${pct(s.meanPredicted)} vs ${pct(f.actualShareLong)}</td></tr>`));
    }
    $('#metrics tbody').innerHTML = rows.join('');
    const fa = m.folds.map((f) => `${f.waitOrWalk.auc.toFixed(3)} vs ${f.firstModel.auc.toFixed(3)}`).join(', ');
    $('#metricsNote').textContent = `Wait or Walk beats the cause only rule on ranking and log loss in all three periods; that is the only baseline it beats. It ranks a little below the first model on AUC in all three (${fa}): recalibrating on the latest three months costs a little ranking, because the base model cannot learn from them. On log loss it is about level with the first model.`;
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
    $('#calibNote').textContent = `Each dot is a forecast band over ${m.pooled.delays.toLocaleString('en-CA')} delays from the three evaluation periods; dots on the dashed line would be perfect. The dots sit below it, so forecasts run high: ` + b.map((q) => `${pct(q.predicted)} forecast, ${pct(q.actual)} actual`).join('; ') + '.';
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
    Promise.all([get('data/model.json'), get('data/metrics.json'), get('data/planb.json')]).then(([mo, me, pb]) => {
      model = mo; planb = pb;
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
        $('#alert').value = document.querySelector('[data-alert]').dataset.alert; readAlert(); $('#example').hidden = false;
      }
      render();
    }).catch(() => { $('#loading').hidden = true; $('#loadError').hidden = false; });
  }
  $('#retry').addEventListener('click', load);
  load();
})();
