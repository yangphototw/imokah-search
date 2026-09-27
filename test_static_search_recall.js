// Execute the real browser search logic with controlled or published sources.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const zlib = require('node:zlib');

function searchHarness() {
    const source = fs.readFileSync(path.join(__dirname, 'public/app.js'), 'utf8');
    const boundary = source.indexOf('    function initTheme()');
    assert(boundary > 0, 'search/UI boundary must exist');
    const prefix = source.slice(0, boundary).replace(
        "document.addEventListener('DOMContentLoaded', () => {", '(() => {'
    );
    return vm.runInNewContext(prefix + `
        return { staticSearch, parseSearchQuery, expandTerms, lookupTokensForTerm,
            matchingTermGroupIndexes, normalizePublicTranscript, paragraphShardIdFor,
            allVideosById, summaryRecallParagraphHits, orderSearchResultsByVideo,
            configure(catalog, searchLoader, paragraphLoader) {
                encyclopediaData = catalog;
                videosById = null;
                loadSearchShard = searchLoader;
                loadParagraphsForVideo = paragraphLoader;
            }
        };
    })()`, {document: {getElementById: () => ({}), querySelectorAll: () => [], documentElement: {}}, console});
}

const video = (id, summary = '', date = '2026-09-04') => ({
    id, title: `來源 ${id}`, ai_summary: summary, publish_date: date,
    url: `https://www.youtube.com/watch?v=${id}`
});
const paragraph = (id, transcript, start = 1679.38) => ({id: `${id}:0`, start, end: start + 40, transcript});
const catalog = videos => ({categories: [{id: 'daily', videos}]});

async function regression() {
    const api = searchHarness();
    const matches = (query, passage) => {
        const groups = api.parseSearchQuery(query).map(part => api.expandTerms(part.term));
        return api.matchingTermGroupIndexes(passage, groups);
    };
    assert.deepEqual([...matches('自動對焦', '拍星空用手動對焦找無限遠。')], []);
    assert.deepEqual([...matches('連續對焦', '拍賽車用慢快門追焦。')], []);
    assert.deepEqual([...matches('連續對焦', 'FC 是連續對焦，適合追蹤移動主體。')], [0]);
    assert.deepEqual([...matches('引閃器', '運動賽事用遠端相機觸發器。')], []);
    assert.deepEqual([...matches('引閃器', '閃燈的觸發器設定頻道。')], [0]);
    assert.deepEqual([...matches('離機閃燈', '主體脫離閃燈的凝結瞬間。')], []);
    assert.deepEqual([...matches('離機閃燈', '離閃可以控制光線方向。')], [0]);
    assert.deepEqual([...matches('焦外', '內對焦外對焦，還有外變焦外變焦。')], []);
    assert.deepEqual([...matches('焦外', '鏡頭焦外散景的模糊感。')], [0]);
    assert.deepEqual([...matches('夜拍對焦', '晚上看星空，使用手動對焦。')], [0, 1]);
    const target = 'tcq_IJjsuNs';
    const old = Array.from({length: 48}, (_, i) => video(`old${String(i).padStart(8, '0')}`));
    const data = new Map(old.map(v => [v.id, [paragraph(v.id, '用手動對焦。', 30)]]));
    data.set(target, [paragraph(target, '拍星空用手動對焦找無限遠。')]);
    const terms = api.lookupTokensForTerm('手動對焦');
    const postings = Object.fromEntries(terms.map(term => [term, old.map(v => [v.id, 30])]));
    api.configure(catalog([...old, video(target, '星空拍攝要手動對焦。')]), async () => postings,
        async id => data.get(id) || []);
    let hits = await api.staticSearch('手動對焦');
    let found = hits.find(hit => hit.video_id === target);
    assert(found, 'summary-backed transcript must survive a saturated 48-hit index');
    assert.equal(found.paragraph_id, `${target}:0`);
    assert.equal(found.timestamp, '27:59');
    assert.equal(found.url, `https://www.youtube.com/watch?v=${target}&t=1679s`);
    assert(found.match_is_complete);

    data.set(target, [paragraph(target, '只有談到別的事情。')]);
    hits = await api.staticSearch('手動對焦');
    assert(!hits.some(hit => hit.video_id === target), 'summary alone is not evidence');

    data.set(target, [paragraph(target, '拍星空應找沒有光害的地方。')]);
    hits = await api.staticSearch('星空 手動對焦');
    found = hits.find(hit => hit.video_id === target);
    assert(found);
    assert.equal(found.matched_count, 1);
    assert.equal(found.match_is_complete, false, 'summary must not promote a partial source to full');

    api.configure(catalog([video(target, 'XT5 操作。')]), async () => ({}),
        async () => [paragraph(target, '這是 XT50。')]);
    assert.equal((await api.staticSearch('XT5')).length, 0, 'model boundary must remain exact');

    const bounded = Array.from({length: 30}, (_, i) => video(`new${String(i).padStart(8, '0')}`,
        '手動對焦。', `2026-08-${String(i + 1).padStart(2, '0')}`));
    const loaded = [];
    api.configure(catalog(bounded), async () => ({}), async id => {
        loaded.push(id);
        return [1, 2, 3].map(start => paragraph(id, '手動對焦。', start));
    });
    const supplements = await api.summaryRecallParagraphHits(api.allVideosById(), [['手動對焦']]);
    assert.equal(loaded.length, 24);
    assert.equal(loaded[0], bounded[29].id, 'prefer recent sources on equal coverage');
    assert.equal(supplements.length, 48, 'at most two source paragraphs per recalled video');

    api.configure(catalog([old[0], video(target, '手動對焦。')]), async () => postings, async id => {
        if (id === target) throw new Error('optional paragraph unavailable');
        return data.get(id) || [];
    });
    hits = await api.staticSearch('手動對焦');
    assert(hits.some(hit => hit.video_id === old[0].id), 'normal source hits survive optional failure');

    data.set(target, [paragraph(target, '拍星空用手動對焦。')]);
    api.configure(catalog([...old, video(target, '星空手動對焦。')]), async () => postings,
        async id => data.get(id) || []);
    hits = await api.staticSearch('星空 手動對焦');
    assert.equal(hits[0].video_id, target, 'complete spoken evidence ranks ahead of partial evidence');
    assert(hits[0].match_is_complete);
    console.log('PASS: 7 behavioral search-recall cases');
}

async function audit() {
    const api = searchHarness();
    const cache = new Map();
    const read = (directory, shard) => {
        const key = `${directory}/${shard}`;
        if (!cache.has(key)) cache.set(key, JSON.parse(zlib.gunzipSync(
            fs.readFileSync(path.join(__dirname, 'public', directory, `${shard}.json.gz`))
        )));
        return cache.get(key);
    };
    api.configure(JSON.parse(fs.readFileSync(path.join(__dirname, 'public/catalog.json'), 'utf8')),
        async shard => read('search-index', shard),
        async id => read('paragraph-index', api.paragraphShardIdFor(id))[id] || []);
    const queries = ['星空', '500 法則', '手動對焦', '星空 手動對焦', '光害', '星空 ISO',
        '倒數拍攝', '聽海天台', '低角度', '欄杆 長焦', '高低差', '景深', 'GR3 街拍',
        'XT5', 'XT50', 'F/2.8', 'M4/3', '4:2:2', '曝光補償', '背鍵對焦', 'CPL 反光',
        'ND 長曝', '高 ISO', 'ISO 3200', 'HSL 調色', '虛化', '移軸', '底片 修圖',
        '星空 無限遠', '低角度 人像', '街道 寬度', '主體 尷尬', '水平 垂直', '有意識 變形'];
    let verified = 0;
    for (const query of queries) {
        const started = Date.now();
        const hits = await api.staticSearch(query);
        const groups = api.parseSearchQuery(query).map(part => api.expandTerms(part.term));
        const videos = new Map();
        for (const hit of hits) {
            const id = hit.video_id || hit.url.match(/[?&]v=([\w-]{11})/)[1];
            if (!videos.has(id)) videos.set(id, hit);
            if (hit.isTitleMatch) continue;
            const source = read('paragraph-index', api.paragraphShardIdFor(id))[id]
                .find(p => p.id === hit.paragraph_id);
            assert(source, `${query}: missing source ${hit.paragraph_id}`);
            assert.equal(hit.transcript, api.normalizePublicTranscript(source.transcript));
            assert.equal(hit.url, `https://www.youtube.com/watch?v=${id}&t=${Math.floor(source.start)}s`);
            assert.equal(hit.matched_count, api.matchingTermGroupIndexes(hit.transcript, groups).length);
            assert(hit.matched_count > 0);
            verified += 1;
        }
        if (['星空', '500 法則', '手動對焦', '星空 手動對焦', '星空 無限遠'].includes(query)) {
            assert(videos.has('tcq_IJjsuNs'), `${query}: new livestream missing`);
        }
        if (['聽海天台', '欄杆 長焦', '高低差'].includes(query)) {
            assert(videos.has('b6pQ7u-2TXI'), `${query}: new Short missing`);
        }
        const expected = {'街道 寬度': 'ARfpY7tSFv0', '主體 尷尬': 'd5iswchnhiQ',
            '水平 垂直': 'MSRqkUvkykY', '有意識 變形': 'MSRqkUvkykY'}[query];
        if (expected) assert(videos.get(expected)?.video_match_is_complete,
            `${query}: newly curated source must have complete source coverage`);
        console.log(JSON.stringify({query, videos: videos.size,
            full: [...videos.values()].filter(hit => hit.video_match_is_complete).length,
            top: [...videos.entries()].slice(0, 3).map(([id, hit]) => ({id, time: hit.timestamp})),
            ms: Date.now() - started}));
    }
    console.log(`PASS: ${queries.length} real queries; ${verified} source/timestamp assertions`);
}

module.exports = { searchHarness };

if (require.main === module) {
    (process.argv.includes('--audit') ? audit() : regression()).catch(error => {
        console.error(error);
        process.exitCode = 1;
    });
}
