const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { matcher, textRecord } = require('./tools/audit_keyword_search');
const matches = (text, groups) => matcher(groups)(textRecord(text));
assert(matches('拍鳥需要等待時機。', [['拍鳥', '鳥類攝影']]));
assert(matches('離機的閃光燈。', [['離機'], ['閃燈', '閃光燈']]));
assert(!matches('閃燈装在機頂。', [['離機'], ['閃燈', '閃光燈']]));
assert(matches('Sony A7 IV操作', [['A7 IV', 'A74']]));
assert(!matches('Sony A7 IV操作', [['A7 III', 'A73']]));
assert(!matches('GR3x與Zfc、XT50', [['GR3']]));
assert(!matches('GR3x與Zfc、XT50', [['ZF']]));
assert(!matches('GR3x與Zfc、XT50', [['XT5']]));
assert(matches('高ISO800配合ND1000', [['ISO'], ['ND']]));
assert(!matches('方程式sqrt加NDVI', [['ND']]));
assert(matches('使用M4/3系統。', [['M43']]));
assert(matches('depth of field', [['DEPTH OF FIELD']]));
const directory = path.join(__dirname, 'docs/search-audit/20260917');
const rows = fs.readFileSync(path.join(directory, 'baseline-results.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
assert.equal(rows.length, 200);
assert.equal(new Set(rows.map(row => row.query)).size, 200);
assert.deepEqual(rows.map(row => row.number), Array.from({length: 200}, (_, i) => i + 1));
for (const row of rows) {
    assert.equal(row.returned_videos, row.returned.length);
    assert.equal(new Set(row.returned.map(v => v.id)).size, row.returned.length);
    assert.equal(row.returned_passages, row.returned.reduce((sum, v) => sum + v.hits.length, 0));
    assert.equal(row.missing_source_candidates, row.missing.filter(v => v.source).length);
    assert(row.missing.every(v => !row.returned.some(r => r.id === v.id)));
}
const snapshot = JSON.parse(fs.readFileSync(path.join(directory, 'snapshot.json')));
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname, file))).digest('hex');
assert.equal(snapshot.app_sha256,
    'd68f0c46f0962ea1931bc97284e5121b77526875a2a612ac6a9a4a1735aa7bf4',
    'frozen search baseline was edited');
assert.equal(snapshot.catalog_sha256, hash('public/catalog.json'), 'catalog changed after baseline');
assert.equal(snapshot.spec_sha256, hash('docs/search-audit/20260917/keywords.json'), 'keyword fixture changed');
console.log('PASS: intent boundary checks; all 200 frozen baseline rows reconcile; catalog and query list unchanged');
