(function () {
  const $ = (s) => document.querySelector(s);
  let model = null;
  const pct = (p) => Math.round(p * 100) + '%';

  function fillSelects() {
    const st = $('#station');
    const sorted = model.stations.slice().sort((a, b) => a.label.localeCompare(b.label));
    st.innerHTML = sorted.map((s) => `<option value="${s.name}">${s.label}</option>`).join('');
    const order = ['medical', 'security', 'alarm', 'track_person', 'injury_track', 'fire', 'doors', 'signals', 'track', 'train', 'power', 'weather', 'cleaning', 'operations', 'other'];
    $('#group').innerHTML = order.map((g) => `<option value="${g}">${model.groups[g].label}</option>`).join('');
    const now = WaitOrWalk.torontoNow();
    $('#time').value = WaitOrWalk.timeBucket(now.hour);
    $('#weekend').checked = now.weekend;
    $('#station').value = 'Union'; $('#group').value = 'medical';
  }

  function current() {
    return { line: $('#line').value, station: $('#station').value, group: $('#group').value, time: $('#time').value, weekend: $('#weekend').checked };
  }

  function render() {
    const x = current();
    const s = model.stations.find((t) => t.name === x.station);
    if (s && !s.lines.includes(x.line)) { x.line = s.lines[0]; $('#line').value = x.line; }
    const { p } = WaitOrWalk.predict(model, x);
    const a = WaitOrWalk.advice(p);
    $('#pct').textContent = pct(p);
    $('.result').className = 'card result ' + a.call;
    $('#advice').textContent = a.text;
    const g = model.groups[x.group];
    $('#typical').textContent = `Across ${g.delays.toLocaleString('en-CA')} logged delays with this cause, half were over in ${g.medianMinutes} minutes or less.`;
    $('#why').innerHTML = WaitOrWalk.explain(model, x).map((e) => `<li class="${e.up ? 'up' : 'down'}">${e.text}.</li>`).join('');
    $('#pbStation').textContent = s ? s.label : x.station;
    const near = s ? s.nearby.filter((r) => !r.night).slice(0, 8) : [];
    const nights = s ? s.nearby.filter((r) => r.night).map((r) => r.route) : [];
    $('#planb').innerHTML = near.length
      ? near.map((r) => `<li class="${r.kind}"><b>${r.route} ${r.name}</b> <span class="meta">${r.kind}</span><br><span class="meta">${r.stop}, about ${r.metres} m</span></li>`).join('') + (nights.length ? `<li><b>Overnight</b><br><span class="meta">Blue Night routes ${nights.join(', ')}</span></li>` : '')
      : '<li>No bus or streetcar stop within 300 metres in the schedule data.</li>';
  }

  function readAlert() {
    const text = $('#alert').value.trim();
    if (!text) { $('#readNote').textContent = ''; return; }
    const r = WaitOrWalk.readAlert(text, model);
    if (r.line) $('#line').value = r.line;
    if (r.station) $('#station').value = r.station;
    if (r.group) $('#group').value = r.group;
    const got = [r.line && 'line', r.station && 'station', r.group && 'cause'].filter(Boolean);
    const miss = ['line', 'station', 'cause'].filter((k) => !got.includes(k));
    $('#readNote').textContent = got.length ? `Read the ${got.join(', ')} from the alert.${miss.length ? ' Pick the ' + miss.join(' and ') + ' below.' : ''} Check the boxes below.` : 'Could not find a line, station or cause in that text. Pick them below.';
    render();
  }

  function metrics(m) {
    const rows = [];
    for (const f of m.folds) {
      const items = [['Overall rate', f.overallRate], ['Cause only rule', f.causeOnlyRate], ['First model (no recency, no recalibration)', f.firstModel], ['Wait or Walk', f.waitOrWalk]];
      items.forEach(([name, s], i) => rows.push(`<tr class="${name === 'Wait or Walk' ? 'ours' : ''}"><td>${i === 0 ? f.test.replace(' to ', ' to ') + ` (${f.testDelays.toLocaleString('en-CA')} delays)` : ''}</td><td>${name}</td><td>${s.auc.toFixed(3)}</td><td>${s.logLoss.toFixed(4)}</td><td>${pct(s.meanPredicted)} vs ${pct(f.actualShareLong)}</td></tr>`));
    }
    $('#metrics tbody').innerHTML = rows.join('');
    const months = Object.entries(m.monthlyShareLong);
    const max = Math.max(...months.map(([, v]) => v));
    $('#trend').innerHTML = months.map(([k, v], i) => `<div class="${i >= months.length - 3 ? 'recent' : ''}" style="height:${Math.round((v / max) * 100)}%" title="${k}: ${pct(v)}">${i % 3 === 0 ? `<span>${k}</span>` : ''}</div>`).join('');
  }

  Promise.all([fetch('data/model.json').then((r) => r.json()), fetch('data/metrics.json').then((r) => r.json())]).then(([mo, me]) => {
    model = mo; fillSelects(); render(); metrics(me);
    ['#line', '#station', '#group', '#time', '#weekend'].forEach((id) => $(id).addEventListener('change', render));
    $('#alert').addEventListener('input', readAlert);
    document.querySelectorAll('[data-alert]').forEach((b) => b.addEventListener('click', () => { $('#alert').value = b.dataset.alert; readAlert(); }));
  });
})();
