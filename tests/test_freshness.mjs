import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const F = require('../freshness.js');

const NOW = Date.parse('2026-11-16T08:17:00Z') / 1000; // 3:17 a.m. Toronto
const HOUR = 3600;
const oldCopy = { checkedAt: NOW - 3 * HOUR, fetchedAt: NOW - 3 * HOUR };
const iso = (sec) => new Date(sec * 1000).toISOString();
const run = (status, conclusion, at) => ({ status, conclusion, created_at: iso(at), updated_at: iso(at) });

// Queued run: must not make an old copy look fresh
{
  const r = F.alertFreshness(oldCopy, [run('queued', null, NOW - 60)], NOW, 90);
  assert.equal(r.checkedAt, oldCopy.checkedAt);
  assert.equal(r.ageMinutes, 180);
  assert.equal(r.stale, true);
  assert.equal(r.workflow.kind, 'queued');
  assert.equal(r.workflow.text, 'A copy job is queued.');
}

// In-progress run: same
{
  const r = F.alertFreshness(oldCopy, [run('in_progress', null, NOW - 30)], NOW, 90);
  assert.equal(r.checkedAt, oldCopy.checkedAt);
  assert.equal(r.stale, true);
  assert.equal(r.ageMinutes, 180);
  assert.equal(r.workflow.kind, 'in_progress');
  assert.equal(r.workflow.text, 'A copy job is running.');
}

// Failed run: same
{
  const r = F.alertFreshness(oldCopy, [run('completed', 'failure', NOW - 120)], NOW, 90);
  assert.equal(r.checkedAt, oldCopy.checkedAt);
  assert.equal(r.stale, true);
  assert.equal(r.workflow.kind, 'failed');
  assert.equal(r.workflow.text, 'The last copy job failed.');
}

// Success without new data: a finished run, but the committed checkedAt was not updated
{
  const r = F.alertFreshness(oldCopy, [run('completed', 'success', NOW - 120)], NOW, 90);
  assert.equal(r.checkedAt, oldCopy.checkedAt);
  assert.equal(r.stale, true);
  assert.equal(r.ageMinutes, 180);
  assert.equal(r.workflow.kind, 'success');
  assert.equal(r.workflow.text, 'The last copy job finished.');
}

// A recent committed checkedAt is fresh, even if fetchedAt (the list) is old
{
  const copy = { checkedAt: NOW - 10 * 60, fetchedAt: NOW - 3 * HOUR };
  const r = F.alertFreshness(copy, [run('completed', 'success', NOW - 10 * 60)], NOW, 90);
  assert.equal(r.checkedAt, copy.checkedAt);
  assert.equal(r.ageMinutes, 10);
  assert.equal(r.stale, false);
  assert.equal(r.workflow.kind, 'success');
}

// A newer fetchedAt must not override an older checkedAt
{
  const copy = { checkedAt: NOW - 3 * HOUR, fetchedAt: NOW - 60 };
  const r = F.alertFreshness(copy, [], NOW, 90);
  assert.equal(r.checkedAt, copy.checkedAt);
  assert.equal(r.stale, true);
  assert.equal(r.workflow.kind, 'unknown');
}

// Older copy with no checkedAt: fall back to the committed fetchedAt, still not to run times
{
  const copy = { fetchedAt: NOW - 3 * HOUR };
  const r = F.alertFreshness(copy, [run('in_progress', null, NOW)], NOW, 90);
  assert.equal(r.checkedAt, copy.fetchedAt);
  assert.equal(r.stale, true);
  assert.equal(r.workflow.kind, 'in_progress');
}

// No copy times at all: treat as stale, and still report workflow status
{
  const r = F.alertFreshness({}, [run('queued', null, NOW)], NOW, 90);
  assert.equal(r.checkedAt, null);
  assert.equal(r.ageMinutes, null);
  assert.equal(r.stale, true);
  assert.equal(r.workflow.kind, 'queued');
}

// Latest run wins for status only
{
  const r = F.workflowStatus([
    run('completed', 'success', NOW - 20 * 60),
    run('in_progress', null, NOW - 30),
  ]);
  assert.equal(r.kind, 'in_progress');
}

console.log('test_freshness.mjs ok');

// Status not yet read (the page paints the copy before the job API returns)
{
  const r = F.alertFreshness(oldCopy, null, NOW, 90);
  assert.equal(r.stale, true);
  assert.equal(r.workflow.kind, 'pending');
  assert.equal(r.workflow.text, '');
}
console.log('test_freshness.mjs pending ok');

// Malformed checkedAt (NaN): unknown and stale, never fresh
{
  const r = F.alertFreshness({ checkedAt: NaN, fetchedAt: NOW - 10 * 60 }, [], NOW, 90);
  assert.equal(r.checkedAt, null);
  assert.equal(r.ageMinutes, null);
  assert.equal(r.stale, true);
}

// Unreadable checkedAt string: same, and it does not fall back to a valid fetchedAt
{
  const r = F.alertFreshness({ checkedAt: 'not-a-date', fetchedAt: NOW - 10 * 60 }, [], NOW, 90);
  assert.equal(r.checkedAt, null);
  assert.equal(r.ageMinutes, null);
  assert.equal(r.stale, true);
}

// Infinity is unreadable
{
  const r = F.alertFreshness({ checkedAt: Infinity }, [], NOW, 90);
  assert.equal(r.checkedAt, null);
  assert.equal(r.stale, true);
  assert.equal(r.ageMinutes, null);
}

// A checkedAt in the future must read unknown/stale, never a negative age
{
  const r = F.alertFreshness({ checkedAt: NOW + HOUR, fetchedAt: NOW - 10 * 60 }, [], NOW, 90);
  assert.equal(r.checkedAt, null);
  assert.equal(r.ageMinutes, null);
  assert.equal(r.stale, true);
}

// A slightly future time is still stale, not fresh
{
  const r = F.alertFreshness({ checkedAt: NOW + 1 }, [], NOW, 90);
  assert.equal(r.stale, true);
  assert.equal(r.ageMinutes, null);
}

console.log('test_freshness.mjs invalid and future times ok');
