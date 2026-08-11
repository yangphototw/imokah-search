document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const clearBtn = document.getElementById('clearBtn');
    const btnText = document.getElementById('btnText');
    const categoryTabs = document.getElementById('categoryTabs');
    const videoGrid = document.getElementById('videoGrid');
    const sectionTitle = document.getElementById('sectionTitle');
    const resultCount = document.getElementById('resultCount');
    const hotTags = document.querySelectorAll('.tag-pill');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const randomBtn = document.getElementById('randomBtn');
    const htmlEl = document.documentElement;

    let currentCategory = 'all';
    let encyclopediaData = null;
    let isSearching = false;

    let lastSearchQuery = '';
    let currentRawSearchResults = null;
    const shardCache = new Map();
    const MAX_CACHED_SHARDS = 24;
    const MAX_SEARCH_RESULTS = 80;
    let videosById = null;
    const paragraphShardCache = new Map();
    const MAX_CACHED_PARAGRAPH_SHARDS = 32;

    // These are spelling and naming aliases, not broad topical associations.
    // A search for "GR3 街拍" must not be satisfied by a video that mentions
    // only street photography.  Related concepts (for example ISO and noise)
    // stay separate so multi-term queries retain their AND meaning.
    const SEARCH_ALIASES = {
        'iso': ['iso', '感光度'],
        '高感': ['高感', '高iso', '高感光度'],
        '噪點': ['噪點', '雜訊'],
        '光圈': ['光圈', 'aperture', 'f值'],
        '景深': ['景深', 'depth of field'],
        '虛化': ['虛化', '背景虛化'],
        '快門': ['快門', 'shutter', '快門速度'],
        '慢快門': ['慢快門', '慢速快門'],
        '長曝': ['長曝', '長時間曝光'],
        '底片': ['底片', '膠卷'],
        '底片模擬': ['底片模擬', 'film simulation'],
        '對焦': ['對焦', 'focus', '自動對焦', 'af'],
        '追焦': ['追焦', '連續對焦'],
        '眼對焦': ['眼對焦', '眼部對焦'],
        '白平衡': ['白平衡', 'white balance', 'wb'],
        '富士': ['富士', 'fuji', 'fujifilm'],
        '索尼': ['索尼', 'sony'],
        '尼康': ['尼康', 'nikon'],
        'ricoh': ['ricoh', '理光'],
        '佳能': ['佳能', 'canon'],
        '萊卡': ['萊卡', '徠卡', 'leica'],
        '蔡司': ['蔡司', 'zeiss', 'carl zeiss'],
        'cpl': ['cpl', '偏光鏡', '偏振鏡'],
        'nd': ['nd', '減光鏡'],
        '街拍': ['街拍', '快照', 'snap', 'street photography', '掃街', '抓拍'],
        '調色': ['調色', 'color grading'],
        '鏡頭': ['鏡頭', 'lens'],
        'gr3': ['gr3', 'griii', 'gr iii', 'gr 3'],
        'gr3x': ['gr3x', 'griiix', 'gr iiix', 'gr 3x']
    };

    const QUERY_NORMALIZATION = {
        '接拍': '街拍',
        'griii': 'gr3',
        'gr iii': 'gr3',
        'gr 3': 'gr3',
        'griiix': 'gr3x',
        'gr iiix': 'gr3x',
        'gr 3x': 'gr3x',
        '理光': 'ricoh'
    };

    const KNOWN_QUERY_TERMS = [...new Set([
        ...Object.keys(SEARCH_ALIASES),
        ...Object.keys(QUERY_NORMALIZATION)
    ])].sort((a, b) => b.length - a.length);

    function normalizeQueryTerm(term) {
        return QUERY_NORMALIZATION[term] || term;
    }

    // Preserve the visitor's wording alongside the canonical lookup term.
    // For example, "GRIII 接拍" becomes [{ term: "gr3", label: "GRIII" },
    // { term: "街拍", label: "接拍" }].  The label is what we show on each
    // result card, so a partial hit can never be presented as the whole query.
    function parseSearchQuery(query) {
        const rawTokens = String(query || '').trim().split(/\s+/).filter(Boolean);
        const parts = [];

        rawTokens.forEach(rawToken => {
            const normalized = rawToken.toLowerCase()
                .replace(/^gr\s*iii\s*x$/i, 'gr3x')
                .replace(/^gr\s*iii$/i, 'gr3')
                .replace(/^gr\s*3\s*x$/i, 'gr3x')
                .replace(/^gr\s*3$/i, 'gr3');
            const split = [];
            let remaining = normalized;

            while (remaining) {
                const known = KNOWN_QUERY_TERMS.find(candidate => remaining.startsWith(candidate));
                if (!known) {
                    split.push(normalizeQueryTerm(remaining));
                    break;
                }
                split.push(normalizeQueryTerm(known));
                remaining = remaining.slice(known.length);
            }

            split.forEach(term => {
                if (!parts.some(part => part.term === term)) {
                    parts.push({
                        term,
                        // An unspaced compound has no unambiguous raw label for
                        // each part, so use its canonical, readable term instead.
                        label: split.length === 1 ? rawToken : term
                    });
                }
            });
        });

        return parts.slice(0, 4);
    }

    function expandTerms(term) {
        const normalized = normalizeQueryTerm(term.trim().toLowerCase());
        return [...new Set([normalized, ...(SEARCH_ALIASES[normalized] || [])])];
    }

    function normalizeForSearchMatch(value) {
        return String(value || '').toLowerCase().replace(/[\s\-_]/g, '');
    }

    function matchingTermGroupIndexes(text, termGroups) {
        const content = normalizeForSearchMatch(text);
        return termGroups.flatMap((group, index) => (
            group.some(term => content.includes(normalizeForSearchMatch(term))) ? [index] : []
        ));
    }

    function labelsForIndexes(indexes, queryParts) {
        return indexes.map(index => queryParts[index]?.label).filter(Boolean);
    }

    // Highlight only aliases which literally occur in the displayed text.
    // Search matching also ignores spacing/hyphens, but inventing a highlight
    // at a non-literal location would be visually misleading.
    function literalMatchedTerms(text, termGroups, indexes) {
        const lowerText = String(text || '').toLowerCase();
        const matches = indexes.flatMap(index => termGroups[index]
            .filter(term => lowerText.includes(String(term).toLowerCase())));
        return [...new Set(matches)].sort((a, b) => b.length - a.length);
    }

    function escapeRegExp(value) {
        return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function highlightSearchTerms(text, terms) {
        const source = String(text || '');
        const uniqueTerms = [...new Set((terms || []).filter(Boolean))]
            .sort((a, b) => String(b).length - String(a).length);
        if (!source || uniqueTerms.length === 0) return escapeHtml(source);

        const expression = new RegExp(uniqueTerms.map(escapeRegExp).join('|'), 'giu');
        let html = '';
        let offset = 0;
        for (const match of source.matchAll(expression)) {
            const start = match.index ?? 0;
            html += escapeHtml(source.slice(offset, start));
            html += `<mark class="search-highlight">${escapeHtml(match[0])}</mark>`;
            offset = start + match[0].length;
        }
        return html + escapeHtml(source.slice(offset));
    }

    function escapeHtml(value) {
        return String(value ?? '').replace(/[&<>'"]/g, character => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        })[character]);
    }

    // These are the same deliberately narrow corrections used by the local
    // transcript audit.  They improve displayed text only: the downloadable
    // raw ASR corpus remains intact and no broad global substitution is made.
    function normalizePublicTranscript(value) {
        let text = String(value || '');
        const focalContext = /(?:\d{2,3}\s*mm|鏡頭|視角|廣角|望遠|景深)/iu.test(text);
        if (focalContext) {
            text = text.replaceAll('焦燈', '焦段').replaceAll('四角', '視角');
            if (/交代.{0,18}(?:鏡頭|廣角|望遠)|(?:鏡頭|廣角|望遠).{0,18}交代/iu.test(text)) {
                text = text.replaceAll('交代', '焦段');
            }
        }
        text = text.replace(/((?:(?:嗨|大家好|OK).{0,20}?我是)|我是)\s*(?:道子|到此|刀子|到齊)(?=[，。！？!?\s]|$)/u, '$1道慈');
        text = text.replace(/(?:道子|到此|刀子|到齊)老師/gu, '道慈老師');
        text = text.replace(/(?:在|去|做|喜歡|練習)接拍(?=的時候|時|[，。！？!?\s]|$)/gu, match => match.replace('接拍', '街拍'));
        return text;
    }

    // Search shards intentionally contain only the original transcript.  A
    // pre-written summary for all 1.27M cuts would make the free static site
    // much larger, so make a conservative listening guide only for cuts the
    // visitor actually opens.  It never adds claims beyond the transcript.
    function createClipListeningGuide(text, query) {
        const cleanText = String(text || '')
            .replace(/\s+/g, ' ')
            .replace(/^(?:嗯+|呃+|啊+|那個|就是|然後|其實|對|好)[，,、\s]*/u, '')
            .trim();
        if (!cleanText) return '這段沒有可用的逐字稿內容。';

        const queryTerms = String(query || '').toLowerCase().match(/[a-z0-9]+|[\u4e00-\u9fff]{1,4}/gi) || [];
        const phrases = cleanText.split(/[。！？!?；;]+/).map(part => part.trim()).filter(Boolean);
        const relevant = phrases.find(phrase => queryTerms.some(term => phrase.toLowerCase().includes(term))) || phrases[0] || cleanText;
        const preview = relevant.length > 54 ? `${relevant.slice(0, 54).replace(/[，,、\s]+$/u, '')}…` : relevant;
        return `這段會聽到：${preview}`;
    }

    // This must match build_static_search_index.py.  FNV-1a gives a stable,
    // evenly distributed shard without revealing the entire search corpus.
    function shardIdFor(term) {
        let hash = 0x811c9dc5;
        for (let i = 0; i < term.length; i += 1) {
            hash ^= term.charCodeAt(i);
            hash = Math.imul(hash, 0x01000193);
        }
        return String((hash >>> 0) & 511).padStart(3, '0');
    }

    async function loadSearchShard(shardId) {
        if (shardCache.has(shardId)) {
            const cached = shardCache.get(shardId);
            // Map insertion order gives us a small LRU cache without keeping
            // every decompressed shard alive for the whole browser session.
            shardCache.delete(shardId);
            shardCache.set(shardId, cached);
            return cached;
        }

        const pending = (async () => {
            const response = await fetch(`/search-index/${shardId}.json.gz`);
            if (!response.ok) throw new Error(`搜尋索引分片載入失敗 (${response.status})`);
            if (!('DecompressionStream' in window)) {
                throw new Error('你的瀏覽器不支援壓縮搜尋索引');
            }
            const stream = response.body.pipeThrough(new DecompressionStream('gzip'));
            return JSON.parse(await new Response(stream).text());
        })();
        shardCache.set(shardId, pending);
        while (shardCache.size > MAX_CACHED_SHARDS) {
            shardCache.delete(shardCache.keys().next().value);
        }
        try {
            return await pending;
        } catch (error) {
            shardCache.delete(shardId);
            throw error;
        }
    }

    // Search shards contain small ASR cuts solely to locate a timestamp.  The
    // public card must instead show this independently-built paragraph context.
    // Keep the video-id hash in sync with build_public_paragraph_index.py.
    function paragraphShardIdFor(videoId) {
        let hash = 0x811c9dc5;
        for (let i = 0; i < videoId.length; i += 1) {
            hash ^= videoId.charCodeAt(i);
            hash = Math.imul(hash, 0x01000193);
        }
        return String((hash >>> 0) & 511).padStart(3, '0');
    }

    async function loadParagraphsForVideo(videoId) {
        const shardId = paragraphShardIdFor(videoId);
        if (!paragraphShardCache.has(shardId)) {
            const pending = (async () => {
                const response = await fetch(`/paragraph-index/${shardId}.json.gz`);
                if (!response.ok) throw new Error(`Paragraph index unavailable (${response.status})`);
                if (!('DecompressionStream' in window)) throw new Error('This browser cannot read the paragraph index.');
                return JSON.parse(await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).text());
            })();
            paragraphShardCache.set(shardId, pending);
            while (paragraphShardCache.size > MAX_CACHED_PARAGRAPH_SHARDS) {
                paragraphShardCache.delete(paragraphShardCache.keys().next().value);
            }
        }
        const shard = await paragraphShardCache.get(shardId);
        return shard[videoId] || [];
    }

    function paragraphAt(paragraphs, start) {
        const point = Number(start) || 0;
        return paragraphs.find(item => point >= item.start && point <= item.end + 1)
            || paragraphs.reduce((nearest, item) => (!nearest || Math.abs(item.start - point) < Math.abs(nearest.start - point) ? item : nearest), null);
    }

    async function attachParagraphContexts(results) {
        const transcriptResults = results.filter(item => !item.isTitleMatch);
        await Promise.all(transcriptResults.map(async item => {
            try {
                const paragraph = paragraphAt(await loadParagraphsForVideo(item.video_id), item.start);
                if (!paragraph) return;
                item.paragraph_id = paragraph.id;
                item.timestamp = formatTimestamp(paragraph.start);
                item.url = `https://www.youtube.com/watch?v=${item.video_id}&t=${Math.floor(paragraph.start)}s`;
                item.transcript = normalizePublicTranscript(paragraph.transcript);
                item.summary = paragraph.summary || '';
                item.topic_tag = topicTag(item.transcript);
            } catch (error) {
                // A failed optional context request must not hide a search hit.
                // The UI labels this fallback as a locating excerpt, never a transcript.
                item.transcript = '';
            }
        }));
        return results;
    }

    function formatTimestamp(seconds) {
        const value = Math.max(0, Math.floor(Number(seconds) || 0));
        return `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`;
    }

    function allVideosById() {
        if (videosById) return videosById;
        const videos = new Map();
        encyclopediaData.categories.forEach(category => {
            category.videos.forEach(video => videos.set(video.id, { ...video, category: category.id }));
        });
        videosById = videos;
        return videosById;
    }

    function topicTag(text) {
        const content = (text || '').toLowerCase();
        if (['光圈', 'aperture', '景深', '虛化', '散景'].some(term => content.includes(term))) return '光圈與景深';
        if (['iso', '感光度', '高感', '噪點'].some(term => content.includes(term))) return 'ISO 與感光度';
        if (['快門', 'shutter'].some(term => content.includes(term))) return '快門與動態';
        if (['對焦', '追焦', '眼對焦'].some(term => content.includes(term))) return '對焦';
        if (['鏡頭', '焦段', '35mm', '50mm', '85mm'].some(term => content.includes(term))) return '鏡頭與焦段';
        return '對話段落';
    }

    function compareSearchResultTiers(a, b) {
        return Number(b.isTitleMatch) - Number(a.isTitleMatch)
            || (b.matched_count || 0) - (a.matched_count || 0)
            || b.score - a.score;
    }

    function selectSearchResultsByTier(items, totalTerms) {
        // Reserve space for every source and match-count tier.  Otherwise a
        // broad partial title term (such as 「街拍」) can consume all 80 slots
        // before the visitor ever sees a full transcript match.
        const perTierLimit = Math.max(1, Math.floor(
            MAX_SEARCH_RESULTS / Math.max(1, totalTerms * 2)
        ));
        const selected = [];
        const selectedItems = new Set();
        const add = item => {
            if (!selectedItems.has(item) && selected.length < MAX_SEARCH_RESULTS) {
                selectedItems.add(item);
                selected.push(item);
            }
        };

        [true, false].forEach(isTitleMatch => {
            for (let matchedCount = totalTerms; matchedCount >= 1; matchedCount -= 1) {
                items
                    .filter(item => item.isTitleMatch === isTitleMatch && item.matched_count === matchedCount)
                    .sort(compareSearchResultTiers)
                    .slice(0, perTierLimit)
                    .forEach(add);
            }
        });

        // Use any spare capacity without changing the displayed hierarchy.
        items.sort(compareSearchResultTiers).forEach(add);
        return selected.sort(compareSearchResultTiers);
    }

    async function staticSearch(query) {
        const queryParts = parseSearchQuery(query);
        if (queryParts.length === 0) return [];
        const termGroups = queryParts.map(part => expandTerms(part.term));
        const terms = [...new Set(termGroups.flat())];
        const shards = await Promise.all([...new Set(terms.map(shardIdFor))].map(loadSearchShard));
        const index = new Map();
        shards.forEach(shard => Object.entries(shard).forEach(([term, hits]) => index.set(term, hits)));

        const videos = allVideosById();
        const scored = new Map();
        const totalTerms = termGroups.length;

        // Preserve useful partial results, but record exactly which requested
        // concepts each title contains.  A generic street-photography title
        // must say "標題符合『接拍』", never "符合『GRIII 接拍』".
        videos.forEach(video => {
            const title = (video.title || '').toLowerCase();
            const matchedIndexes = matchingTermGroupIndexes(title, termGroups);
            if (matchedIndexes.length > 0) {
                const matchedTerms = labelsForIndexes(matchedIndexes, queryParts);
                const isCompleteMatch = matchedIndexes.length === totalTerms;
                const key = `${video.id}_title`;
                scored.set(key, {
                    score: (isCompleteMatch ? 2000000 : 100000) + (matchedIndexes.length * 10000),
                    video_title: video.title,
                    timestamp: '00:00',
                    text: video.title,
                    summary: '',
                    topic_tag: '📌 【標題專題討論】',
                    match_reason: `影片標題符合「${matchedTerms.join('、')}」`,
                    matched_terms: matchedTerms,
                    matched_count: matchedIndexes.length,
                    total_query_terms: totalTerms,
                    highlight_terms: literalMatchedTerms(video.title, termGroups, matchedIndexes),
                    match_is_complete: isCompleteMatch,
                    url: video.url,
                    type: '標題精確匹配',
                    isTitleMatch: true,
                    category: video.category,
                    publish_date: video.publish_date,
                    is_member_only: video.is_member_only
                });
            }
        });

        termGroups.forEach((group, groupIndex) => {
            group.forEach(term => {
                (index.get(term) || []).forEach(hit => {
                    const [videoId, timestamp, text, start] = hit;
                    const displayText = normalizePublicTranscript(text);
                    const key = `${videoId}_${timestamp}`;
                    const video = videos.get(videoId);
                    if (!video) return;
                    let item = scored.get(key);
                    if (!item) {
                        item = {
                            score: 0,
                            hitGroups: new Set(),
                            video_id: videoId,
                            video_title: video.title,
                            timestamp,
                            start: Number(start) || 0,
                            locating_excerpt: displayText,
                            summary: '',
                            topic_tag: topicTag(displayText),
                            match_reason: '',
                            url: `https://www.youtube.com/watch?v=${videoId}&t=${Math.floor(Number(start) || 0)}s`,
                            type: '對白同義詞檢索',
                            isTitleMatch: false,
                            category: video.category,
                            publish_date: video.publish_date,
                            is_member_only: video.is_member_only
                        };
                        scored.set(key, item);
                    }
                    if (item.hitGroups && !item.hitGroups.has(groupIndex)) {
                        item.hitGroups.add(groupIndex);
                        item.score += 5000 * (10 ** (totalTerms - groupIndex - 1));
                    }
                });
            });
        });

        const scoredCandidates = [...scored.values()]
            .map(item => {
                if (item.hitGroups) {
                    const allMatched = item.hitGroups.size === totalTerms;
                    if (allMatched) {
                        item.score += 1000000;
                    }
                    item.matched_count = item.hitGroups.size;
                    item.total_query_terms = totalTerms;
                    delete item.hitGroups;
                }
                return item;
            })
            .sort((a, b) => b.score - a.score);
        const candidates = selectSearchResultsByTier(scoredCandidates, totalTerms);
        const results = await attachParagraphContexts(candidates);
        return results
            .map(item => {
                if (item.isTitleMatch) return item;

                const matchedIndexes = matchingTermGroupIndexes(item.transcript, termGroups);
                if (matchedIndexes.length === 0) return null;
                const matchedTerms = labelsForIndexes(matchedIndexes, queryParts);
                item.matched_terms = matchedTerms;
                item.matched_count = matchedIndexes.length;
                item.total_query_terms = totalTerms;
                item.highlight_terms = literalMatchedTerms(item.transcript, termGroups, matchedIndexes);
                item.match_is_complete = matchedIndexes.length === totalTerms;
                item.match_reason = `逐字稿命中 ${matchedIndexes.length}/${totalTerms} 個搜尋詞：「${matchedTerms.join('、')}」`;
                return item;
            })
            .filter(Boolean)
            // Keep the result hierarchy stable: every title tier first, from
            // most to least query terms; then transcript evidence in the same
            // order.  Partial matches remain useful without masquerading as a
            // complete multi-term result.
            .sort(compareSearchResultTiers)
            .slice(0, MAX_SEARCH_RESULTS);
    }

    function initTheme() {
        const savedTheme = localStorage.getItem('ppvi-theme') || 'light';
        setTheme(savedTheme);
    }

    function setTheme(theme) {
        htmlEl.setAttribute('data-theme', theme);
        localStorage.setItem('ppvi-theme', theme);

        if (themeToggleBtn) {
            const icon = themeToggleBtn.querySelector('.theme-icon');
            const text = themeToggleBtn.querySelector('.theme-text');
            if (theme === 'light') {
                if (icon) icon.textContent = '☀';
                if (text) text.textContent = '亮色模式';
            } else {
                if (icon) icon.textContent = '☾';
                if (text) text.textContent = '深色模式';
            }
        }
    }

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = htmlEl.getAttribute('data-theme') || 'dark';
            const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
            setTheme(nextTheme);
        });
    }

    function toggleClearBtn() {
        if (clearBtn) {
            clearBtn.style.display = searchInput.value.trim() ? 'block' : 'none';
        }
    }

    if (searchInput) {
        searchInput.addEventListener('input', toggleClearBtn);
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            searchInput.value = '';
            lastSearchQuery = '';
            currentRawSearchResults = null;
            toggleClearBtn();
            renderCategory(currentCategory);
        });
    }

    if (randomBtn) {
        randomBtn.addEventListener('click', () => {
            if (!encyclopediaData || !encyclopediaData.categories) return;

            let candidateVids = [];
            if (currentCategory === 'all') {
                encyclopediaData.categories.forEach(c => {
                    if (c.videos) candidateVids.push(...c.videos);
                });
            } else {
                const catObj = encyclopediaData.categories.find(c => c.id === currentCategory);
                if (catObj && catObj.videos) {
                    candidateVids = catObj.videos;
                }
            }

            if (candidateVids.length === 0) return;

            const randomIndex = Math.floor(Math.random() * candidateVids.length);
            const selectedVid = candidateVids[randomIndex];
            const targetUrl = selectedVid.url || `https://www.youtube.com/watch?v=${selectedVid.id}&t=0s`;

            window.open(targetUrl, '_blank');
        });
    }

    function showLoadingState() {
        if (loadingOverlay) loadingOverlay.classList.add('active');
        if (searchBtn) {
            searchBtn.disabled = true;
            if (btnText) btnText.textContent = '檢索中';
        }
    }

    function hideLoadingState() {
        if (loadingOverlay) loadingOverlay.classList.remove('active');
        if (searchBtn) {
            searchBtn.disabled = false;
            if (btnText) btnText.textContent = '搜尋';
        }
    }

    async function loadEncyclopedia() {
        try {
            const res = await fetch('/catalog.json');
            if (!res.ok) throw new Error('API request failed');
            encyclopediaData = await res.json();
            videosById = null;
            const statusText = document.querySelector('.status-pill span:last-child');
            const totalVideos = encyclopediaData?.channel_info?.total_videos;
            if (statusText && Number.isInteger(totalVideos)) {
                statusText.textContent = `${totalVideos.toLocaleString('zh-TW')} 部影片資料庫在線`;
            }
            renderCategory('all');
        } catch (err) {
            console.error('Failed to load data:', err);
            resultCount.textContent = '資料載入失敗，請重新整理。';
        }
    }

    function checkIsMember(item) {
        if (typeof item.is_member_only !== 'undefined') {
            return item.is_member_only;
        }
        if (typeof item.category !== 'undefined') {
            return ['member_review', 'live', 'book'].includes(item.category);
        }
        const t = (item.title || item.video_title || "").toLowerCase();
        const kw = ["會員", "評圖", "獨家", "會後", "專屬", "限定", "直播", "週三八點半", "讀書會", "導讀"];
        return kw.some(k => t.includes(k));
    }

    function renderCategory(catId) {
        if (!encyclopediaData) return;
        currentCategory = catId;

        if (lastSearchQuery && currentRawSearchResults) {
            renderSearchResultsByCategory();
            return;
        }

        let videos = [];
        if (catId === 'all') {
            sectionTitle.textContent = '全頻道影片資料庫';
            encyclopediaData.categories.forEach(cat => {
                videos.push(...cat.videos);
            });
            
            const uniqueMap = new Map();
            videos.forEach(v => uniqueMap.set(v.id, v));
            videos = Array.from(uniqueMap.values());
        } else {
            const catObj = encyclopediaData.categories.find(c => c.id === catId);
            if (catObj) {
                sectionTitle.textContent = `${catObj.name}`;
                videos = catObj.videos;
            }
        }

        resultCount.textContent = `共 ${videos.length} 部影片`;
        renderVideoCards(videos);
    }

    function createVideoCardElement(v) {
        const card = document.createElement('div');
        card.className = 'video-card';
        
        const thumbUrl = `https://img.youtube.com/vi/${v.id}/hqdefault.jpg`;
        const firstQuote = (v.sample_quotes && v.sample_quotes.length > 0) ? v.sample_quotes[0] : null;
        
        const excerpt = normalizePublicTranscript(firstQuote?.text || '')
            .replace(/\s+/g, ' ').trim();
        const titleText = normalizePublicTranscript(v.title || '').replace(/\s+/g, ' ').trim();
        const hasTranscriptExcerpt = Boolean(excerpt && excerpt !== titleText);
        const tsText = hasTranscriptExcerpt ? firstQuote.timestamp : '00:00';
        const summaryText = hasTranscriptExcerpt
            ? `逐字稿摘錄：${excerpt.slice(0, 100)}${excerpt.length > 100 ? '…' : ''}`
            : `影片主題：${v.title}`;

        const targetUrl = hasTranscriptExcerpt ? firstQuote.url : v.url;

        const isMember = checkIsMember(v);
        const badgeHtml = isMember 
            ? '<span class="badge-tag member-only">會員獨家</span>' 
            : '<span class="badge-tag public-free">公開影片</span>';

        const dateHtml = v.publish_date ? `<span class="card-date">發布 ${escapeHtml(v.publish_date)}</span>` : '';

        card.innerHTML = `
            <div class="thumb-container">
                <img class="card-thumb" src="${thumbUrl}" alt="${escapeHtml(v.title)}" loading="lazy">
                ${badgeHtml}
                <span class="ts-badge">${hasTranscriptExcerpt ? `從 ${tsText}` : '影片開頭'}</span>
            </div>
            <div class="card-content">
                ${dateHtml ? `<div style="margin-bottom: 6px;">${dateHtml}</div>` : ''}
                <h3 class="type-lvl-3-title" title="${escapeHtml(v.title)}">${escapeHtml(v.title)}</h3>
                <div class="summary-block">
                    <div class="summary-text">${escapeHtml(summaryText)}</div>
                </div>
            </div>
        `;

        card.addEventListener('click', () => {
            window.open(targetUrl, '_blank');
        });
        
        return card;
    }

    function renderVideoCards(videos) {
        videoGrid.innerHTML = '';
        if (videos.length === 0) {
            videoGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">未找到相關影片。</div>';
            return;
        }

        const BATCH_SIZE = 24;
        let currentlyShown = 0;

        function appendNextBatch() {
            const batch = videos.slice(currentlyShown, currentlyShown + BATCH_SIZE);
            currentlyShown += batch.length;

            batch.forEach(v => {
                const card = createVideoCardElement(v);
                videoGrid.appendChild(card);
            });

            // Remove existing load more button if present
            const oldBtnContainer = document.getElementById('loadMoreContainer');
            if (oldBtnContainer) oldBtnContainer.remove();

            if (currentlyShown < videos.length) {
                const remaining = videos.length - currentlyShown;
                const loadMoreContainer = document.createElement('div');
                loadMoreContainer.id = 'loadMoreContainer';
                loadMoreContainer.style.gridColumn = '1 / -1';
                loadMoreContainer.style.textAlign = 'center';
                loadMoreContainer.style.padding = '24px 0';

                loadMoreContainer.innerHTML = `
                    <button class="search-btn" style="padding: 12px 36px; font-size: 1rem; border-radius: 16px;">
                        ▼ 載入更多影片 (還有 ${remaining} 部影片)
                    </button>
                `;

                loadMoreContainer.querySelector('button').addEventListener('click', () => {
                    appendNextBatch();
                });

                videoGrid.appendChild(loadMoreContainer);
            }
        }

        appendNextBatch();
    }

    // 🚀 使用者權威五大分類過濾器
    function filterVideoByCategory(videoTitle, clipText, catId, resultItem) {
        if (catId === 'all') return true;
        
        // 優先使用後端回傳的準確分類
        if (resultItem && resultItem.category) {
            return resultItem.category === catId;
        }
        
        // Fallback rule engine
        const text = (videoTitle + ' ' + clipText).toLowerCase();
        const isLive = ["週三八點半", "週三攝影週報", "週三攝影周報", "攝影週報", "攝影周報", "會後直播"].some(k => text.includes(k));
        const isBook = ["讀書會", "導讀", "攝影集", "畫冊", "作品集", "經典畫冊", "書報"].some(k => text.includes(k));
        const isMemberReview = text.includes("評圖") || (resultItem && resultItem.is_member_only && (text.includes("作業") || text.includes("照片")));
        const isGear = ["相機", "鏡頭", "實測", "評測", "開箱", "選購", "濾鏡", "包"].some(k => text.includes(k));

        if (catId === 'live') return isLive;
        if (catId === 'book') return isBook && !isLive;
        if (catId === 'member_review') return isMemberReview && !isLive && !isBook;
        if (catId === 'gear') return isGear && !isLive && !isBook && !isMemberReview;
        if (catId === 'daily') return !isBook && !isLive && !isMemberReview && !isGear;

        return true;
    }

    function renderSearchResultsByCategory() {
        if (!currentRawSearchResults) return;

        const groupedMap = new Map();

        currentRawSearchResults.forEach(r => {
            let vId = '';
            const match = r.url.match(/v=([a-zA-Z0-9_-]{11})/);
            if (match) vId = match[1];

            const key = vId || r.video_title;
            const clipText = r.transcript || r.locating_excerpt || '';

            if (filterVideoByCategory(r.video_title, clipText, currentCategory, r)) {
                if (!groupedMap.has(key)) {
                    groupedMap.set(key, {
                        vId: vId,
                        video_title: r.video_title,
                        publish_date: r.publish_date || '',
                        is_member_only: checkIsMember(r),
                        titleMatch: false,
                        titleMatchedTerms: [],
                        titleMatchedCount: 0,
                        totalQueryTerms: 0,
                        titleMatchIsComplete: false,
                        clips: []
                    });
                }
                if (r.isTitleMatch) {
                    const group = groupedMap.get(key);
                    group.titleMatch = true;
                    group.titleMatchedTerms = r.matched_terms || [];
                    group.titleMatchedCount = r.matched_count || group.titleMatchedTerms.length;
                    group.totalQueryTerms = r.total_query_terms || group.titleMatchedCount;
                    group.titleMatchIsComplete = Boolean(r.match_is_complete);
                    return;
                }
                groupedMap.get(key).clips.push({
                    timestamp: r.timestamp,
                    transcript: r.transcript || '',
                    locating_excerpt: r.locating_excerpt || '',
                    summary: r.summary || '',
                    topic_tag: r.topic_tag || '段落上下文',
                    match_reason: r.match_reason || `含關鍵字: ${lastSearchQuery}`,
                    highlight_terms: r.highlight_terms || [],
                    url: r.url
                });
            }
        });

        // Keep every title tier.  The source result order is already:
        // title all terms -> title partial tiers -> transcript all terms ->
        // transcript partial tiers.  Grouping only merges evidence belonging
        // to the same video; it must not discard a useful partial title match.
        const groupedVideos = Array.from(groupedMap.values());

        const catNames = {
            'all': '全頻道專題',
            'daily': '日常影片',
            'gear': '器材評測',
            'live': '直播存檔',
            'member_review': '會員評圖',
            'book': '讀書會'
        };

        const catLabel = catNames[currentCategory] || '';
        sectionTitle.textContent = `搜尋「${lastSearchQuery}」 ‧ ${catLabel}`;
        resultCount.textContent = `共 ${groupedVideos.length} 部符合條件的影片`;

        videoGrid.innerHTML = '';
        if (groupedVideos.length === 0) {
            videoGrid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 48px; color: var(--text-secondary);">
                    <div style="font-size: 1.1rem; color: var(--text-primary); font-weight: 700;">在「${escapeHtml(catLabel)}」分類中未找到「${escapeHtml(lastSearchQuery)}」相關影片</div>
                    <div style="font-size: 0.85rem; margin-top: 6px; color: var(--text-muted);">建議點選【全頻道專題】或其他分類查看完整搜尋結果</div>
                </div>`;
            return;
        }

        groupedVideos.forEach(item => {
            const card = document.createElement('div');
            card.className = 'video-card';

            const thumbUrl = item.vId ? `https://img.youtube.com/vi/${item.vId}/hqdefault.jpg` : '';
            const badgeHtml = item.is_member_only 
                ? '<span class="badge-tag member-only">會員獨家</span>' 
                : '<span class="badge-tag public-free">公開影片</span>';

            let featureBadgeHtml = '';
            if (item.clips.length >= 3) {
                featureBadgeHtml = `<span class="featured-label">「${lastSearchQuery}」主題精華</span>`;
            }

            const dateHtml = item.publish_date ? `<span class="card-date">發布 ${escapeHtml(item.publish_date)}</span>` : '';

            const INITIAL_SHOW = 2;
            const visibleClips = item.clips.slice(0, INITIAL_SHOW);
            const hiddenClips = item.clips.slice(INITIAL_SHOW);

            const titleMatchedTerms = item.titleMatchedTerms.length
                ? item.titleMatchedTerms.join('、')
                : lastSearchQuery;
            const titleMatchDescription = `標題命中 ${item.titleMatchedCount}/${item.totalQueryTerms} 個搜尋詞：「${titleMatchedTerms}」`;
            let clipsHtml = '<div class="clips-wrapper">';
            // Title and transcript are distinct evidence sources.  Keep the
            // title tier visible even when the video also has transcript hits.
            if (item.titleMatch) {
                clipsHtml += `
                    <div class="clip-node title-match-node">
                        <div class="match-reason-pill">${escapeHtml(titleMatchDescription)}</div>
                        ${item.clips.length === 0
                            ? `<div class="quote-text">${item.titleMatchIsComplete ? '標題包含所有搜尋詞' : '標題只符合部分搜尋詞'}；目前尚未找到可定位的逐字稿時間點。</div>`
                            : ''}
                    </div>
                `;
            }
            
            visibleClips.forEach(clip => {
                clipsHtml += `
                    <div class="clip-node" data-url="${escapeHtml(clip.url)}">
                        <div class="clip-meta">
                            <span class="topic-label">${escapeHtml(clip.topic_tag)}</span>
                            <span class="ts-link">${clip.timestamp}</span>
                        </div>
                        <div class="match-reason-pill">${escapeHtml(clip.match_reason)}</div>
                        ${clip.summary ? `<div class="match-reason-pill clip-summary">摘要：${escapeHtml(clip.summary)}</div>` : ''}
                        <div class="quote-text">${clip.transcript ? `逐字稿：${highlightSearchTerms(clip.transcript, clip.highlight_terms)}` : `命中片段（完整段落載入失敗）：${escapeHtml(clip.locating_excerpt)}`}</div>
                    </div>
                `;
            });

            if (hiddenClips.length > 0) {
                clipsHtml += `<div class="more-clips-container" style="display: none;">`;
                hiddenClips.forEach(clip => {
                    clipsHtml += `
                        <div class="clip-node" data-url="${escapeHtml(clip.url)}">
                            <div class="clip-meta">
                                <span class="topic-label">${escapeHtml(clip.topic_tag)}</span>
                            <span class="ts-link">${clip.timestamp}</span>
                            </div>
                            <div class="match-reason-pill">${escapeHtml(clip.match_reason)}</div>
                            ${clip.summary ? `<div class="match-reason-pill clip-summary">摘要：${escapeHtml(clip.summary)}</div>` : ''}
                            <div class="quote-text">${clip.transcript ? `逐字稿：${highlightSearchTerms(clip.transcript, clip.highlight_terms)}` : `命中片段（完整段落載入失敗）：${escapeHtml(clip.locating_excerpt)}`}</div>
                        </div>
                    `;
                });
                clipsHtml += `</div>`;
                clipsHtml += `
                    <button class="fold-btn">
                        <span>▼ 展開更多 ${hiddenClips.length} 個對話片段</span>
                    </button>
                `;
            }

            clipsHtml += '</div>';

            card.innerHTML = `
                <div class="thumb-container">
                    <img class="card-thumb" src="${thumbUrl}" alt="${escapeHtml(item.video_title)}" loading="lazy">
                    ${badgeHtml}
                    <span class="ts-badge">${item.clips.length ? `${item.clips.length} 個可定位片段` : '標題符合'}</span>
                </div>
                <div class="card-content">
                    ${dateHtml ? `<div style="margin-bottom: 6px;">${dateHtml}</div>` : ''}
                    ${featureBadgeHtml}
                    <h3 class="type-lvl-3-title">${escapeHtml(item.video_title)}</h3>
                    ${clipsHtml}
                </div>
            `;

            const expandBtn = card.querySelector('.fold-btn');
            if (expandBtn) {
                expandBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const moreContainer = card.querySelector('.more-clips-container');
                    if (moreContainer.style.display === 'none') {
                        moreContainer.style.display = 'flex';
                        moreContainer.style.flexDirection = 'column';
                        moreContainer.style.gap = '14px';
                        moreContainer.style.marginTop = '14px';
                        expandBtn.innerHTML = '<span>▲ 收起對話片段</span>';
                    } else {
                        moreContainer.style.display = 'none';
                        expandBtn.innerHTML = `<span>▼ 展開更多 ${hiddenClips.length} 個對話片段</span>`;
                    }
                });
            }

            card.querySelectorAll('.clip-node').forEach(clipEl => {
                clipEl.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const targetUrl = clipEl.dataset.url;
                    window.open(targetUrl, '_blank');
                });
            });

            card.addEventListener('click', (e) => {
                if (!e.target.closest('.fold-btn')) {
                    if (item.clips.length > 0) {
                        window.open(item.clips[0].url, '_blank');
                    }
                }
            });

            videoGrid.appendChild(card);
        });
    }

    async function performSearch(query) {
        const cleanQuery = query.trim();
        if (!cleanQuery) {
            lastSearchQuery = '';
            currentRawSearchResults = null;
            renderCategory(currentCategory);
            return;
        }

        if (isSearching) return;
        isSearching = true;

        showLoadingState();

        lastSearchQuery = cleanQuery;
        sectionTitle.textContent = `搜尋「${cleanQuery}」觀點與時間軸`;
        resultCount.textContent = '正在搜尋索引...';

        try {
            currentRawSearchResults = await staticSearch(cleanQuery);
            renderSearchResultsByCategory();
        } catch (err) {
            console.error('Search failed:', err);
            resultCount.textContent = '搜尋發生錯誤。';
        } finally {
            hideLoadingState();
            isSearching = false;
        }
    }

    categoryTabs.addEventListener('click', (e) => {
        if (e.target.classList.contains('tab-pill')) {
            document.querySelectorAll('.tab-pill').forEach(btn => btn.classList.remove('active'));
            e.target.classList.add('active');
            const catId = e.target.dataset.cat;
            currentCategory = catId;
            renderCategory(catId);
        }
    });

    searchBtn.addEventListener('click', () => {
        performSearch(searchInput.value);
    });

    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch(searchInput.value);
        }
    });

    hotTags.forEach(tag => {
        tag.addEventListener('click', () => {
            const keyword = tag.dataset.tag;
            searchInput.value = keyword;
            toggleClearBtn();
            performSearch(keyword);
        });
    });

    initTheme();
    loadEncyclopedia();
});
