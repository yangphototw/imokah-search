// Offline baseline audit. Uses the shipped search; never changes search/data.
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const { searchHarness } = require('../test_static_search_recall');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'docs/search-audit/20260917');
const spec = JSON.parse(fs.readFileSync(path.join(output, 'keywords.json'), 'utf8'));
const queries = Object.entries(spec.categories).flatMap(([category, words]) =>
    words.map(query => ({number: 0, category, query})));
queries.forEach((item, i) => { item.number = i + 1; });
assert.equal(queries.length, 200);
assert.equal(new Set(queries.map(q => q.query)).size, 200);
const sha = data => crypto.createHash('sha256').update(data).digest('hex');
const write = (name, data) => fs.writeFileSync(path.join(output, name), data, 'utf8');
const escape = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const compact = value => String(value || '').toLowerCase().replace(/[\s_-]/g, '');

// Independent intent matcher: these are candidate hints, NOT semantic judgments.
// ISO800/ND1000 are intentional; camera names retain both token boundaries.
function matcher(groups, production = false) {
    const prepared = groups.map(group => group.map(alias => {
        const term = alias.toLowerCase();
        if (/^[a-z0-9\s_\-/:.]+$/.test(term)) {
            let pattern = term.split(/[\s_-]+/).map(escape).join('[\\s_-]*');
            if (/^m\s*4\s*\/?\s*3$/.test(term)) pattern = 'm\\s*4\\s*\\/?\\s*3';
            const suffix = production ? (/\d$/.test(compact(term)) ? '[a-z0-9]' : '[a-z]')
                : (/^(iso|nd)$/.test(compact(term)) ? '[a-z]' : '[a-z0-9]');
            return {regex: new RegExp(`(^|[^a-z0-9])${pattern}(?!${suffix})`, 'i')};
        }
        return {term: compact(term)};
    }));
    return record => prepared.every(group => group.some(alias => alias.regex
        ? alias.regex.test(record.text) : record.compact.includes(alias.term)));
}

function textRecord(text) { return {text: text || '', compact: compact(text)}; }
function excerpt(text, groups, limit = 260) {
    const lower = text.toLowerCase();
    const positions = groups.flat().map(term => lower.indexOf(term.toLowerCase())).filter(i => i >= 0);
    const start = Math.max(0, (positions.length ? Math.min(...positions) : 0) - 75);
    return (start ? '…' : '') + text.slice(start, start + limit) + (start + limit < text.length ? '…' : '');
}

async function main() {
    let number = 0;
    const list = ['# 攝影關鍵字搜尋驗收：200 詞', '',
        '建立日期：2026-09-17。20 類各 10 詞；先固定清單，再測現有搜尋。', '',
        '每詞以「想學這個主題」為情境。器材詞包括該機型的操作、實拍或有內容的評測；只提到名稱不等於值得推薦。', '',
        '審查分為：來源／秒數正確、結果是否直接相關、只是順帶提及、可能漏掉的教學來源。零結果也可能是本機沒有內容，須對照原文才判定。', '',
        '相近詞刻意保留，用於測試同義詞與較窄的搜尋意圖（例如自動／手動對焦、街拍／快照、GR3／GR3x）。', '',
        '獨立候選詞組見 keywords.json；這些只用於找待審候選，並非產品改動或正確答案。', ''];
    for (const [category, words] of Object.entries(spec.categories)) {
        list.push(`## ${category}`, '', ...words.map(word => `${++number}. ${word}`), '');
    }
    write('KEYWORDS_200.md', list.join('\n'));
    const api = searchHarness();
    const catalogBytes = fs.readFileSync(path.join(root, 'public/catalog.json'));
    const catalog = JSON.parse(catalogBytes);
    const paragraphs = new Map();
    const fingerprints = [];
    for (const filename of fs.readdirSync(path.join(root, 'public/paragraph-index')).filter(f => f.endsWith('.json.gz')).sort()) {
        const bytes = fs.readFileSync(path.join(root, 'public/paragraph-index', filename));
        fingerprints.push([filename, sha(bytes)]);
        for (const [id, rows] of Object.entries(JSON.parse(zlib.gunzipSync(bytes)))) paragraphs.set(id, rows);
    }
    const searchCache = new Map();
    api.configure(catalog, async shard => {
        if (!searchCache.has(shard)) searchCache.set(shard, JSON.parse(zlib.gunzipSync(
            fs.readFileSync(path.join(root, 'public/search-index', `${shard}.json.gz`)))));
        return searchCache.get(shard);
    }, async id => paragraphs.get(id) || []);
    const videos = api.allVideosById();
    const corpus = [...videos.values()].map(video => ({video,
        title: textRecord(video.title), summary: textRecord(video.ai_summary),
        paragraphs: (paragraphs.get(video.id) || []).map(p => ({...p,
            ...textRecord(api.normalizePublicTranscript(p.transcript))}))}));
    const sourceById = new Map(corpus.flatMap(v => v.paragraphs.map(p => [p.id, p])));
    const snapshot = {created_at: new Date().toISOString(),
        app_sha256: sha(fs.readFileSync(path.join(root, 'public/app.js'))),
        catalog_sha256: sha(catalogBytes), spec_sha256: sha(fs.readFileSync(path.join(output, 'keywords.json'))),
        paragraph_shards_sha256: sha(JSON.stringify(fingerprints)),
        search_shards_sha256: sha(JSON.stringify(fs.readdirSync(path.join(root, 'public/search-index'))
            .filter(f => f.endsWith('.json.gz')).sort().map(f => [f, sha(fs.readFileSync(path.join(root, 'public/search-index', f)))]))),
        videos: videos.size, paragraphs: sourceById.size};
    const snapshotPath = path.join(output, 'snapshot.json');
    if (fs.existsSync(snapshotPath)) {
        const previous = JSON.parse(fs.readFileSync(snapshotPath, 'utf8'));
        for (const key of Object.keys(snapshot).filter(key => key !== 'created_at')) {
            assert.equal(snapshot[key], previous[key],
                `Refusing to overwrite reviewed baseline: ${key} changed; use a separate audit directory for a new version`);
        }
        snapshot.created_at = previous.created_at;
    }
    write('snapshot.json', JSON.stringify(snapshot, null, 2));
    const reports = [];
    const reviewPackets = [];
    let checked = 0;
    for (const query of queries) {
        const parts = api.parseSearchQuery(query.query);
        const groups = parts.map(part => api.expandTerms(part.term));
        const intended = spec.intent_groups[query.query] || [[query.query]];
        const intendedMatch = matcher(intended);
        const productionMatch = matcher(groups, true);
        const returned = await api.staticSearch(query.query);
        const grouped = new Map();
        for (const hit of returned) {
            const id = hit.video_id || hit.url.match(/[?&]v=([\w-]{11})/)[1];
            assert(videos.has(id));
            if (!grouped.has(id)) grouped.set(id, {id, rank: grouped.size + 1,
                title: videos.get(id).title, summary: videos.get(id).ai_summary || '', hits: [],
                title_only: true, full_match: hit.video_match_is_complete});
            const row = grouped.get(id);
            if (hit.isTitleMatch) {
                assert.equal(hit.video_title, videos.get(id).title);
                assert.equal(hit.url, videos.get(id).url);
                assert(api.matchingTermGroupIndexes(hit.video_title, groups).length > 0);
            }
            if (!hit.isTitleMatch) {
                const source = sourceById.get(hit.paragraph_id);
                assert(source, `${query.query}: missing source ${hit.paragraph_id}`);
                assert.equal(hit.transcript, source.text);
                assert.equal(hit.url, `https://www.youtube.com/watch?v=${id}&t=${Math.floor(source.start)}s`);
                assert.equal(hit.matched_count, api.matchingTermGroupIndexes(source.text, groups).length);
                assert(hit.matched_count > 0);
                checked += 1;
                row.title_only = false;
                row.hits.push({paragraph_id: source.id, start: source.start, end: source.end,
                    url: hit.url, intended_match: intendedMatch(source),
                    excerpt: excerpt(source.text, intended), matched_count: hit.matched_count});
            }
        }
        const corpusMatches = [];
        let productPool = 0;
        for (const item of corpus) {
            const lexical = productionMatch(item.title) || item.paragraphs.some(productionMatch);
            if (lexical) productPool += 1;
            const matches = item.paragraphs.filter(intendedMatch);
            const titleMatch = intendedMatch(item.title);
            const summaryMatch = intendedMatch(item.summary);
            if (!matches.length && !titleMatch && !summaryMatch) continue;
            const candidate = {id: item.video.id, title: item.video.title, summary: item.video.ai_summary || '',
                title_match: titleMatch, summary_match: summaryMatch, source_count: matches.length,
                source: matches[0] ? {paragraph_id: matches[0].id, start: matches[0].start, end: matches[0].end,
                    url: `https://www.youtube.com/watch?v=${item.video.id}&t=${Math.floor(matches[0].start)}s`,
                    excerpt: excerpt(matches[0].text, intended)} : null};
            corpusMatches.push(candidate);
            if (grouped.has(candidate.id)) {
                const result = grouped.get(candidate.id);
                result.intended_title = titleMatch;
                result.intended_summary = summaryMatch;
                result.intended_source_count = matches.length;
                result.intended_source = candidate.source;
            }
        }
        const missing = corpusMatches.filter(v => !grouped.has(v.id)).sort((a, b) =>
            Number(Boolean(b.source)) - Number(Boolean(a.source))
            || (Number(b.title_match) * 2 + Number(b.summary_match)) - (Number(a.title_match) * 2 + Number(a.summary_match))
            || b.source_count - a.source_count || a.id.localeCompare(b.id));
        const rows = [...grouped.values()];
        const suspect = rows.filter(v => !v.intended_title && !v.intended_summary && !v.intended_source_count);
        const row = {...query, parsed: parts.map(p => p.term), intended,
            returned_videos: rows.length, returned_passages: returned.filter(h => !h.isTitleMatch).length,
            title_only: rows.filter(v => v.title_only).length,
            production_lexical_pool: productPool,
            independent_source_candidates: corpusMatches.filter(v => v.source).length,
            missing_source_candidates: missing.filter(v => v.source).length,
            missing_title_or_summary_source_candidates: missing.filter(v => v.source && (v.title_match || v.summary_match)).length,
            no_intent_lexical_evidence: suspect.length,
            returned: rows, missing};
        reports.push(row);
        const reviewRows = [...new Map([...rows.slice(0, 3), ...suspect.slice(0, 2)].map(v => [v.id, v])).values()];
        reviewPackets.push({...query, parsed: row.parsed, intended,
            counts: {returned: rows.length, source_candidates: row.independent_source_candidates,
                missing: row.missing_source_candidates, potential_drift: suspect.length},
            returned_to_review: reviewRows.map(v => ({...v, hits: v.hits.slice(0, 1)})),
            missing_to_review: missing.filter(v => v.source).slice(0, 2)});
        if (query.number % 10 === 0) console.log(`${query.number}/200: ${query.query}; ${rows.length} videos`);
    }
    write('baseline-results.jsonl', reports.map(r => JSON.stringify(r)).join('\n') + '\n');
    for (let start = 0; start < 200; start += 10) {
        write(`review-${String(start + 1).padStart(3, '0')}-${String(start + 10).padStart(3, '0')}.json`,
            JSON.stringify(reviewPackets.slice(start, start + 10)));
    }
    const aggregate = {queries: reports.length, returned_video_query_pairs: reports.reduce((s, r) => s + r.returned_videos, 0),
        checked_passage_query_pairs: checked, zero_results: reports.filter(r => !r.returned_videos).map(r => r.query),
        zero_with_source_candidates: reports.filter(r => !r.returned_videos && r.independent_source_candidates).map(r => r.query),
        queries_with_intent_drift_candidates: reports.filter(r => r.no_intent_lexical_evidence).length,
        queries_with_missing_title_or_summary_source_candidates: reports.filter(r => r.missing_title_or_summary_source_candidates).length};
    write('baseline-summary.json', JSON.stringify(aggregate, null, 2));
    const table = ['# 200 詞搜尋基線（機械核對，尚非語意通過）', '',
        '逐字稿／連結／時間點均由實際搜尋輸出回查。候選由全庫另外掃描；候選數不是「正確答案數」，未顯示也不一律算缺陷。', '',
        '「偏離待審」表示整片標題、摘要、逐字稿都沒有獨立意圖詞組；需要閱讀後判斷。每詞前三部、最多兩部偏離候選、兩部遺漏候選交給 Subagent 審閱，其餘結果只完成機械核對。', '',
        '| 編號 | 分類 | 關鍵字 | 搜尋影片 | 有原文的獨立候選 | 未顯示候選 | 標題／摘要也命中但未顯示 | 偏離待審 |',
        '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |',
        ...reports.map(r => `| ${r.number} | ${r.category} | ${r.query} | ${r.returned_videos} | ${r.independent_source_candidates} | ${r.missing_source_candidates} | ${r.missing_title_or_summary_source_candidates} | ${r.no_intent_lexical_evidence} |`)];
    write('BASELINE_200.md', table.join('\n') + '\n');
    console.log(JSON.stringify(aggregate, null, 2));
}

module.exports = { matcher, textRecord };
if (require.main === module) main().catch(error => { console.error(error); process.exitCode = 1; });
