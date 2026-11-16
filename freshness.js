/* Alert copy freshness. Last checked uses only the committed copy. Workflow status is separate. No network. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) {
    if (root.WaitOrWalk) Object.assign(root.WaitOrWalk, api);
    else root.WaitOrWalkFreshness = api;
  }
})(typeof self !== 'undefined' ? self : this, function () {
  const BAD = { failure: 1, cancelled: 1, timed_out: 1, startup_failure: 1, action_required: 1 };
  const QUEUED = { queued: 1, pending: 1, requested: 1, waiting: 1 };

  // Unix seconds from the committed copy. Non-finite values (NaN, Infinity) and unreadable strings are unknown.
  function unixSeconds(v) {
    if (v == null || v === '') return null;
    const n = typeof v === 'number' ? v : Number(v);
    return Number.isFinite(n) ? n : null;
  }

  // Last checked time in unix seconds, from the committed copy only.
  // Prefer checkedAt; if a copy has no checkedAt (older files), use fetchedAt from the same file.
  // A present but unreadable checkedAt is unknown; it does not fall back to fetchedAt.
  // Workflow run start or update times are never used, including runs with a null conclusion.
  function committedCheckedAt(copy) {
    if (!copy) return null;
    if (copy.checkedAt != null && copy.checkedAt !== '') return unixSeconds(copy.checkedAt);
    if (copy.fetchedAt != null && copy.fetchedAt !== '') return unixSeconds(copy.fetchedAt);
    return null;
  }

  function workflowStatus(runs) {
    if (runs == null) return { kind: 'pending', text: '' };
    if (!runs.length) return { kind: 'unknown', text: 'The job status could not be read.' };
    let best = null, bestT = -1;
    for (const r of runs) {
      const t = Date.parse(r.updated_at || r.created_at || '') || 0;
      if (t >= bestT) { bestT = t; best = r; }
    }
    if (!best) return { kind: 'unknown', text: 'The job status could not be read.' };
    const st = best.status, c = best.conclusion;
    if (QUEUED[st]) return { kind: 'queued', text: 'A copy job is queued.' };
    if (st === 'in_progress') return { kind: 'in_progress', text: 'A copy job is running.' };
    if (BAD[c]) return { kind: 'failed', text: 'The last copy job failed.' };
    if (c === 'success') return { kind: 'success', text: 'The last copy job finished.' };
    return { kind: 'unknown', text: 'The job status could not be read.' };
  }

  function alertFreshness(copy, runs, now, staleMin) {
    const limit = staleMin == null ? 90 : staleMin;
    const wf = workflowStatus(runs);
    const unknown = { checkedAt: null, ageMinutes: null, stale: true, staleMin: limit, workflow: wf };
    if (!Number.isFinite(now)) return unknown;
    const checked = committedCheckedAt(copy);
    // Future or unreadable times are unknown and stale, never a negative age that would look fresh.
    if (checked == null || checked > now) return unknown;
    const age = Math.round((now - checked) / 60);
    if (!Number.isFinite(age) || age < 0) return unknown;
    const stale = age > limit;
    return { checkedAt: checked, ageMinutes: age, stale, staleMin: limit, workflow: wf };
  }

  return { unixSeconds, committedCheckedAt, workflowStatus, alertFreshness };
});
