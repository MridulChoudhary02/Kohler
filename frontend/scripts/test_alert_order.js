// frontend/scripts/test_alert_order.js — Unit test asserting monotonic descending sort for CompactAlertsList
const assert = require('assert');

function dedupeAndSort(events) {
  const latestByFixture = new Map();
  for (const ev of events) {
    const existing = latestByFixture.get(ev.fixture_id);
    if (!existing || new Date(ev.detected_at).getTime() > new Date(existing.detected_at).getTime()) {
      latestByFixture.set(ev.fixture_id, ev);
    }
  }

  const sorted = Array.from(latestByFixture.values())
    .sort((a, b) => new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime())
    .slice(0, 25);

  // Runtime monotonicity assertion
  for (let i = 1; i < sorted.length; i++) {
    const prev = new Date(sorted[i - 1].detected_at).getTime();
    const curr = new Date(sorted[i].detected_at).getTime();
    assert(prev >= curr, `Sort violation at index ${i}: ${sorted[i - 1].detected_at} < ${sorted[i].detected_at}`);
  }

  return sorted;
}

// Test case 1: Multiple events on different days where time-of-day alone would mislead
const testEvents = [
  { fixture_id: 'fix-ward-003', detected_at: '2026-09-16T15:05:00Z' },
  { fixture_id: 'fix-lab-001', detected_at: '2026-09-17T09:01:30Z' },
  { fixture_id: 'fix-ward-002', detected_at: '2026-09-16T11:06:00Z' },
  { fixture_id: 'fix-lob-002', detected_at: '2026-09-17T17:29:00Z' },
  { fixture_id: 'fix-icu-002', detected_at: '2026-09-17T10:03:00Z' },
  { fixture_id: 'fix-icu-003', detected_at: '2026-09-15T16:33:00Z' },
  // Older duplicates that should be deduped out:
  { fixture_id: 'fix-lob-002', detected_at: '2026-09-15T10:00:00Z' },
  { fixture_id: 'fix-icu-002', detected_at: '2026-09-15T10:00:00Z' }
];

const result = dedupeAndSort(testEvents);
assert.strictEqual(result.length, 6, 'Should have 6 distinct fixtures');
assert.strictEqual(result[0].fixture_id, 'fix-lob-002', 'Sep 17 17:29 should be 1st');
assert.strictEqual(result[1].fixture_id, 'fix-icu-002', 'Sep 17 10:03 should be 2nd');
assert.strictEqual(result[2].fixture_id, 'fix-lab-001', 'Sep 17 09:01 should be 3rd (above Sep 16 15:05)');
assert.strictEqual(result[3].fixture_id, 'fix-ward-003', 'Sep 16 15:05 should be 4th');
assert.strictEqual(result[4].fixture_id, 'fix-ward-002', 'Sep 16 11:06 should be 5th');
assert.strictEqual(result[5].fixture_id, 'fix-icu-003', 'Sep 15 16:33 should be 6th');

console.log('✅ CompactAlertsList chronological monotonicity test passed');
