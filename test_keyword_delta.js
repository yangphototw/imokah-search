const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const root = __dirname;
const dir = path.join(root, 'docs/search-audit/20260927');
const read = name => JSON.parse(fs.readFileSync(path.join(dir, name), 'utf8'));
const rows = fs.readFileSync(path.join(dir, 'results.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
const queue = read('review-queue.json');
const verdicts = read('semantic-delta.json').verdicts;
const summary = read('summary.json');
const snapshot = read('snapshot.json');
const appHash = crypto.createHash('sha256').update(fs.readFileSync(path.join(root, 'public/app.js'))).digest('hex');
assert.equal(snapshot.app_sha256, appHash, 'search changed; rerun comparison and review its delta');
assert.equal(rows.length, 200);
assert.equal(summary.queries, rows.length);
assert.equal(summary.changed_top_three_to_review, queue.length);
assert.equal(queue.length, verdicts.length, 'every changed top-three result needs a judgment');
const key = item => `${item.query}\0${item.id}`;
const byKey = new Map(verdicts.map(item => [key(item), item]));
assert.equal(byKey.size, verdicts.length);
for (const item of queue) {
    const judgment = byKey.get(key(item));
    assert(judgment, `${item.query}: missing judgment of ${item.id}`);
    assert(item.paragraph_ids.includes(judgment.paragraph_id),
        `${item.query}: judgment cites an unshown passage`);
    assert(['useful', 'mention', 'irrelevant', 'alternate_intent', 'unclear'].includes(judgment.verdict));
}
assert.equal(rows.reduce((sum, row) => sum + row.returned_videos, 0), summary.returned_video_query_pairs);
assert(rows.every(row => row.returned.length === row.returned_videos));
console.log(`PASS: ${rows.length} current keywords; all ${queue.length} changed top-three results reviewed`);
