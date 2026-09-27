// Re-run the frozen 200-query audit without repeating full-corpus semantic review.
// Source checks are deterministic; old judgments are reused only for the same
// query, video and displayed source paragraph.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');
const {searchHarness} = require('../test_static_search_recall');

const root = path.resolve(__dirname, '..');
const baselineDir = path.join(root, 'docs/search-audit/20260917');
const outputDir = path.join(root, 'docs/search-audit/20260927');
const read = file => fs.readFileSync(file, 'utf8');
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const baseline = read(path.join(baselineDir, 'baseline-results.jsonl')).trim().split('\n').map(JSON.parse);
const specBytes = fs.readFileSync(path.join(baselineDir, 'keywords.json'));
const spec = JSON.parse(specBytes);
const originalSnapshot = JSON.parse(read(path.join(baselineDir, 'snapshot.json')));
const judgments = new Map();
const missingJudgments = new Map();
for (const reviewer of ['a', 'b', 'c']) {
    const packet = JSON.parse(read(path.join(baselineDir, `semantic-${reviewer}.json`)));
    for (const query of packet.queries) {
        for (const item of query.returned) judgments.set(`${query.query}\0${item.id}`, item);
        for (const item of query.missing) missingJudgments.set(`${query.query}\0${item.id}`, item);
    }
}
const pairKey = (query, id) => `${query}\0${id}`;
const written = (name, data) => fs.writeFileSync(path.join(outputDir, name), data, 'utf8');

async function main() {
    assert.equal(baseline.length, 200);
    assert.equal(sha(specBytes), originalSnapshot.spec_sha256, 'frozen query list changed');
    const catalogBytes = fs.readFileSync(path.join(root, 'public/catalog.json'));
    assert.equal(sha(catalogBytes), originalSnapshot.catalog_sha256, 'catalog changed; audit corpus separately');
    const paragraphs = new Map();
    const fingerprints = [];
    for (const name of fs.readdirSync(path.join(root, 'public/paragraph-index')).filter(f => f.endsWith('.json.gz')).sort()) {
        const bytes = fs.readFileSync(path.join(root, 'public/paragraph-index', name));
        fingerprints.push([name, sha(bytes)]);
        for (const [id, rows] of Object.entries(JSON.parse(zlib.gunzipSync(bytes)))) paragraphs.set(id, rows);
    }
    assert.equal(sha(JSON.stringify(fingerprints)), originalSnapshot.paragraph_shards_sha256,
        'paragraph corpus changed; previous semantic judgments cannot be reused');
    const searchFingerprints = fs.readdirSync(path.join(root, 'public/search-index'))
        .filter(f => f.endsWith('.json.gz')).sort()
        .map(name => [name, sha(fs.readFileSync(path.join(root, 'public/search-index', name)))]);
    assert.equal(sha(JSON.stringify(searchFingerprints)), originalSnapshot.search_shards_sha256,
        'search index changed; audit index separately');

    const api = searchHarness();
    const shards = new Map();
    api.configure(JSON.parse(catalogBytes), async id => {
        if (!shards.has(id)) shards.set(id, JSON.parse(zlib.gunzipSync(
            fs.readFileSync(path.join(root, 'public/search-index', `${id}.json.gz`)))));
        return shards.get(id);
    }, async id => paragraphs.get(id) || []);
    const videos = api.allVideosById();
    const sourceById = new Map([...paragraphs.values()].flatMap(rows => rows.map(p => [p.id, p])));
    const results = [];
    const review = [];
    let checkedPassages = 0;
    let reused = 0;
    let unchangedUnreviewed = 0;
    const regainedUseful = [];
    const droppedUseful = [];
    const removedWeakTopThree = [];
    for (const old of baseline) {
        const groups = api.parseSearchQuery(old.query).map(part => api.expandTerms(part.term));
        const hits = await api.staticSearch(old.query);
        const grouped = new Map();
        for (const hit of hits) {
            const id = hit.video_id || hit.url.match(/[?&]v=([\w-]{11})/)[1];
            assert(videos.has(id), `${old.query}: unknown video ${id}`);
            if (!grouped.has(id)) grouped.set(id, {id, rank: grouped.size + 1,
                title: videos.get(id).title, title_only: true, paragraph_ids: [],
                first_excerpt: '', full_match: hit.video_match_is_complete});
            const item = grouped.get(id);
            if (hit.isTitleMatch) {
                assert.equal(hit.video_title, videos.get(id).title);
                assert.equal(hit.url, videos.get(id).url);
                assert(api.matchingTermGroupIndexes(hit.video_title, groups).length > 0);
                continue;
            }
            const source = sourceById.get(hit.paragraph_id);
            assert(source, `${old.query}: missing source ${hit.paragraph_id}`);
            assert.equal(hit.transcript, api.normalizePublicTranscript(source.transcript));
            assert.equal(hit.url, `https://www.youtube.com/watch?v=${id}&t=${Math.floor(source.start)}s`);
            assert.equal(hit.matched_count, api.matchingTermGroupIndexes(hit.transcript, groups).length);
            assert(hit.matched_count > 0);
            item.title_only = false;
            item.paragraph_ids.push(source.id);
            if (!item.first_excerpt) item.first_excerpt = hit.transcript.slice(0, 550);
            checkedPassages += 1;
        }
        const current = [...grouped.values()];
        const oldMap = new Map(old.returned.map(item => [item.id, item]));
        const newlyReturned = current.filter(item => !oldMap.has(item.id));
        const dropped = old.returned.filter(item => !grouped.has(item.id));
        for (const item of newlyReturned) {
            const verdict = missingJudgments.get(pairKey(old.query, item.id));
            if (verdict?.verdict === 'should_include') regainedUseful.push({query: old.query, id: item.id});
        }
        for (const item of dropped) {
            const verdict = judgments.get(pairKey(old.query, item.id));
            if (verdict?.verdict === 'useful') droppedUseful.push({query: old.query, id: item.id});
            if (item.rank <= 3 && ['mention_only', 'irrelevant'].includes(verdict?.verdict)) {
                removedWeakTopThree.push({query: old.query, id: item.id, verdict: verdict.verdict});
            }
        }
        const firstThree = current.slice(0, 3);
        for (const item of firstThree) {
            const prior = oldMap.get(item.id);
            const verdict = judgments.get(pairKey(old.query, item.id));
            const sameSource = prior && item.paragraph_ids[0] === prior.hits[0]?.paragraph_id;
            if (sameSource && verdict && verdict.paragraph_ids?.includes(item.paragraph_ids[0])) {
                reused += 1;
            } else if (sameSource) {
                // This was already outside the first review's coverage.  It
                // has not changed, so charging for it again saves no tokens.
                unchangedUnreviewed += 1;
            } else {
                review.push({query: old.query, rank: item.rank, id: item.id,
                    title: item.title, paragraph_ids: item.paragraph_ids.slice(0, 2),
                    excerpt: item.first_excerpt, previous_rank: prior?.rank || null,
                    previous_first_paragraph: prior?.hits[0]?.paragraph_id || null,
                    previous_verdict: verdict?.verdict || null,
                    reason: !prior ? 'new_top_three' : !sameSource ? 'source_changed' : 'not_previously_judged'});
            }
        }
        results.push({number: old.number, category: old.category, query: old.query,
            parsed: api.parseSearchQuery(old.query).map(part => part.term),
            returned_videos: current.length, returned_passages: hits.filter(hit => !hit.isTitleMatch).length,
            returned: current.map(({id, rank, paragraph_ids, title_only, full_match}) =>
                ({id, rank, first_paragraph_id: paragraph_ids[0] || null, title_only, full_match})),
            top_three: firstThree.map(({id, rank, paragraph_ids, title_only, full_match}) =>
                ({id, rank, paragraph_ids: paragraph_ids.slice(0, 2), title_only, full_match})),
            newly_returned: newlyReturned.map(item => item.id),
            dropped: dropped.map(item => item.id),
            old_returned_videos: old.returned_videos});
    }
    const aggregate = {
        queries: results.length, verified_passage_query_pairs: checkedPassages,
        returned_video_query_pairs: results.reduce((sum, row) => sum + row.returned_videos, 0),
        old_zero_results: baseline.filter(row => !row.returned_videos).map(row => row.query),
        current_zero_results: results.filter(row => !row.returned_videos).map(row => row.query),
        previously_zero_now_found: results.filter(row => row.returned_videos
            && !row.old_returned_videos).map(row => row.query),
        changed_top_three_to_review: review.length,
        reused_top_three_judgments: reused,
        unchanged_top_three_without_old_judgment: unchangedUnreviewed,
        newly_returned_previously_judged_useful: regainedUseful.length,
        dropped_previously_judged_useful: droppedUseful.length,
        removed_weak_old_top_three: removedWeakTopThree.length,
        newly_returned_pairs: results.reduce((sum, row) => sum + row.newly_returned.length, 0),
        dropped_pairs: results.reduce((sum, row) => sum + row.dropped.length, 0)
    };
    fs.mkdirSync(outputDir, {recursive: true});
    written('snapshot.json', JSON.stringify({created_at: new Date().toISOString(),
        app_sha256: sha(fs.readFileSync(path.join(root, 'public/app.js'))),
        catalog_sha256: sha(catalogBytes), spec_sha256: sha(specBytes),
        paragraph_shards_sha256: sha(JSON.stringify(fingerprints)),
        search_shards_sha256: sha(JSON.stringify(searchFingerprints))}, null, 2));
    written('results.jsonl', results.map(row => JSON.stringify(row)).join('\n') + '\n');
    written('review-queue.json', JSON.stringify(review, null, 2));
    written('judged-changes.json', JSON.stringify({regainedUseful, droppedUseful, removedWeakTopThree}, null, 2));
    written('summary.json', JSON.stringify(aggregate, null, 2));
    console.log(JSON.stringify(aggregate, null, 2));
}

if (require.main === module) main().catch(error => {console.error(error); process.exitCode = 1;});
