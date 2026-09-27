// Exercise the shipped search implementation, including conservative fallbacks.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');
const { searchHarness } = require('./test_static_search_recall');

const cases = [
    ['星空對不到焦怎麼辦', ['星空', '對焦']],
    ['人像背景很亂', ['人像', '背景', '雜亂']],
    ['照片一定要水平嗎', ['水平']],
    ['怎麼拍星空？', ['星空']],
    ['請問星空怎麼手動對焦？', ['星空', '手動對焦']],
    ['如何用 ND 拍長曝', ['nd', '長曝']],
    ['光圈和景深有什麼關係？', ['光圈', '景深']],
    ['拍人像背景太亂怎麼辦？', ['人像', '背景', '雜亂']],
];

function regression() {
    const api = searchHarness();
    const terms = query => Array.from(api.parseSearchQuery(query), part => part.term);
    for (const [query, expected] of cases) assert.deepEqual(terms(query), expected, query);
    for (const query of ['景深合成', '星空縮時', '不要對焦', '星空對焦不要手動', '不水平',
        '對焦不存在的模式怎麼辦', '對焦失敗率', 'XT50', 'ISO3200', 'F/2.8', '4:2:2']) {
        assert.deepEqual(terms(query), [query.toLowerCase()], `retain unknown or negative constraint: ${query}`);
    }
    assert.deepEqual(terms('GR III 街拍'), ['gr3', '街拍']);
    assert.deepEqual(terms('高 ISO'), ['高感']);
    assert.deepEqual(terms('請問 XT50 如何對焦？'), ['xt50', '對焦']);
    assert.deepEqual(terms('請問如何用 M4/3 拍人像？'), ['m43', '人像']);

    // A long stream mentioning topics hours apart must not outrank a paragraph
    // addressing both, even if its title/summary contains all the query terms.
    const hit = (id, indexes, extras = {}) => ({video_id: id, matched_group_indexes: indexes,
        matched_count: indexes.length, isTitleMatch: false, score: 10, ...extras});
    const ranked = api.orderSearchResultsByVideo([
        hit('scattered', [0], {summary: '星空對焦。'}),
        hit('scattered', [1], {summary: '星空對焦。'}),
        hit('title-only', [0, 1], {isTitleMatch: true, score: 999999}),
        hit('together', [0, 1]),
    ], [['星空'], ['對焦']]);
    assert.equal(ranked[0].video_id, 'together');
    assert.equal(ranked[1].video_id, 'scattered');
    console.log('PASS: natural-query parsing, literal fallbacks, and passage-first ranking');
}

async function audit() {
    const api = searchHarness();
    const cache = new Map();
    const read = (directory, shard) => {
        const key = `${directory}/${shard}`;
        if (!cache.has(key)) cache.set(key, JSON.parse(zlib.gunzipSync(fs.readFileSync(
            path.join(__dirname, 'public', directory, `${shard}.json.gz`)))));
        return cache.get(key);
    };
    api.configure(JSON.parse(fs.readFileSync(path.join(__dirname, 'public/catalog.json'), 'utf8')),
        async shard => read('search-index', shard),
        async id => read('paragraph-index', api.paragraphShardIdFor(id))[id] || []);
    let verified = 0;
    for (const [query, expected] of cases) {
        const started = Date.now();
        const parts = api.parseSearchQuery(query);
        assert.deepEqual(Array.from(parts, part => part.term), expected);
        const groups = parts.map(part => api.expandTerms(part.term));
        const hits = await api.staticSearch(query);
        const videos = new Map();
        for (const hit of hits) {
            const id = hit.video_id || hit.url.match(/[?&]v=([\w-]{11})/)[1];
            if (!videos.has(id)) videos.set(id, {id, hit, clips: []});
            if (hit.isTitleMatch) continue;
            const source = read('paragraph-index', api.paragraphShardIdFor(id))[id]
                .find(paragraph => paragraph.id === hit.paragraph_id);
            assert(source, `${query}: missing source ${hit.paragraph_id}`);
            assert.equal(hit.transcript, api.normalizePublicTranscript(source.transcript));
            assert.equal(hit.url, `https://www.youtube.com/watch?v=${id}&t=${Math.floor(source.start)}s`);
            assert.equal(hit.matched_count, api.matchingTermGroupIndexes(hit.transcript, groups).length);
            assert(hit.matched_count > 0);
            videos.get(id).clips.push(hit);
            verified += 1;
        }
        const top = [...videos.values()].slice(0, 3);
        assert(top.length > 0, `${query}: no videos`);
        assert(top[0].clips.some(hit => hit.match_is_complete), `${query}: top source lacks a complete paragraph`);
        if (query.includes('星空') && query.includes('焦')) {
            assert(top.some(video => video.id === 'tcq_IJjsuNs'), `${query}: curated focusing lesson outside top 3`);
        }
        if (query === '照片一定要水平嗎') {
            assert(top.some(video => video.id === 'MSRqkUvkykY'), `${query}: nuanced horizontal/vertical discussion outside top 3`);
        }
        console.log(JSON.stringify({query, topics: expected, videos: videos.size,
            top: top.map(video => ({id: video.id, title: video.hit.video_title,
                clips: video.clips.slice(0, 2).map(hit => ({paragraph: hit.paragraph_id,
                    time: hit.timestamp, excerpt: hit.transcript_excerpt, url: hit.url}))})),
            ms: Date.now() - started}));
    }
    console.log(`PASS: ${cases.length} natural questions; ${verified} source/timestamp assertions`);
}

if (require.main === module) {
    Promise.resolve().then(() => process.argv.includes('--audit') ? audit() : regression())
        .catch(error => { console.error(error); process.exitCode = 1; });
}
