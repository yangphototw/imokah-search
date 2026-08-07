document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const clearBtn = document.getElementById('clearBtn');
    const btnText = document.getElementById('btnText');
    const categoryTabs = document.getElementById('categoryTabs');
    const videoGrid = document.getElementById('videoGrid');
    const latestVideosSection = document.getElementById('latestVideosSection');
    const latestVideoGrid = document.getElementById('latestVideoGrid');
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

    // Keep this list deliberately small and client-side.  The index itself is
    // pre-built, so expanding a query only means downloading a few tiny shards.
    const CAMERA_SYNONYMS = {
        'iso': ['iso', '感光度', '感光', '高感', '噪點'],
        '感光度': ['感光度', 'iso', '感光', '高感', '噪點'],
        '高感': ['高感', 'iso', '感光度', '噪點', '夜拍', '夜景'],
        '噪點': ['噪點', 'iso', '高感', '感光度', '降噪'],
        '光圈': ['光圈', 'aperture', 'f值', 'f1.4', 'f1.8', 'f2.8', '大光圈', '小光圈', '景深', '散景', '虛化'],
        '景深': ['景深', '光圈', '虛化', '散景', '背景虛化'],
        '虛化': ['虛化', '景深', '散景', '光圈'],
        '快門': ['快門', 'shutter', '快門速度', '電子快門', '機械快門'],
        '慢快門': ['慢快門', '慢速快門', '長曝', '長時間曝光', '車軌', '流水', '腳架'],
        '長曝': ['長曝', '長時間曝光', '慢快門', '慢速快門', '腳架', '車軌', '流水'],
        '底片': ['底片', '底片相機', '膠卷', '底片膠卷', '135底片', '120底片'],
        '底片模擬': ['底片模擬', '富士底片模擬', 'film simulation', 'classic neg', '底片配方'],
        '對焦': ['對焦', 'focus', '眼對焦', '追焦', '手動對焦', 'af', 'mf'],
        '白平衡': ['白平衡', 'wb', '色溫', 'k值', '偏色'],
        '定焦': ['定焦', '35mm', '50mm', '85mm', '大光圈定焦'],
        '變焦': ['變焦', '24-70', '70-200', '24-105'],
        '富士': ['富士', 'fuji', 'fujifilm', 'x100v', 'x100vi', 'x-t5', 'x-e4', 'gfx'],
        '索尼': ['索尼', 'sony', 'a74', 'a7iv', 'a7m4', 'a7r5', 'a7c', 'fx3'],
        '尼康': ['尼康', 'nikon', 'zf', 'z8', 'z9', 'z6', 'zfc'],
        '理光': ['理光', 'ricoh', 'gr3', 'griii', 'gr3x', 'gr'],
        '佳能': ['佳能', 'canon', 'r5', 'r6', 'r6ii', 'r8', 'eos r'],
        '萊卡': ['萊卡', '徠卡', 'leica', 'm10', 'm11', 'q2', 'q3'],
        '蔡司': ['蔡司', 'zeiss', '蔡絲', 'carl zeiss'],
        'cpl': ['cpl', '偏光鏡', '偏振鏡'],
        'nd': ['nd', '減光鏡'],
        '街拍': ['街拍', '快照', 'snap', 'street photography', '掃街', '抓拍'],
        '調色': ['調色', '修圖', 'lightroom', 'lut', '色調', '後製', 'hsl'],
        '鏡頭': ['鏡頭', '焦段', '副廠', '騰龍', '適馬', '卡口']
    };

    function expandTerms(term) {
        const normalized = term.trim().toLowerCase();
        return [...new Set([normalized, ...(CAMERA_SYNONYMS[normalized] || [])])];
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
        if (['光圈', 'aperture', '景深', '虛化', '散景'].some(term => content.includes(term))) return '📷 【光圈與景深控制】';
        if (['iso', '感光度', '高感', '噪點'].some(term => content.includes(term))) return '🎨 【ISO 與感光度表現】';
        if (['快門', 'shutter'].some(term => content.includes(term))) return '⏱️ 【快門速度與動態】';
        if (['對焦', '追焦', '眼對焦'].some(term => content.includes(term))) return '🎯 【對焦性能與反應】';
        if (['鏡頭', '焦段', '35mm', '50mm', '85mm'].some(term => content.includes(term))) return '📷 【鏡頭搭配與焦段選擇】';
        return '💡 【核心觀點與建議】';
    }

    async function staticSearch(query) {
        const subQueries = query.trim().toLowerCase().split(/\s+/).filter(Boolean).slice(0, 4);
        const termGroups = subQueries.map(expandTerms);
        const terms = [...new Set(termGroups.flat())];
        const shards = await Promise.all([...new Set(terms.map(shardIdFor))].map(loadSearchShard));
        const index = new Map();
        shards.forEach(shard => Object.entries(shard).forEach(([term, hits]) => index.set(term, hits)));

        const videos = allVideosById();
        const scored = new Map();
        const totalTerms = termGroups.length;

        // Title matches are small enough to rank in the browser and give users
        // useful results even when a transcript has no matching time segment.
        videos.forEach(video => {
            const title = (video.title || '').toLowerCase();
            let hits = 0;
            let score = 0;
            termGroups.forEach((group, position) => {
                if (group.some(term => title.includes(term))) {
                    hits += 1;
                    score += 10000 * (10 ** (totalTerms - position - 1));
                }
            });
            if (hits) {
                const allMatched = hits === totalTerms;
                const key = `${video.id}_title`;
                scored.set(key, {
                    score: (allMatched ? 2000000 : 0) + score,
                    video_title: video.title,
                    timestamp: '00:00',
                    text: video.title,
                    summary: video.ai_summary || `影片標題包含「${query}」主題討論`,
                    topic_tag: '📌 【標題專題討論】',
                    match_reason: allMatched ? `🏆 「${query}」主題精華影片` : `含關鍵字: ${query}`,
                    url: video.url,
                    type: '標題精確匹配',
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
                    const key = `${videoId}_${timestamp}`;
                    const video = videos.get(videoId);
                    if (!video) return;
                    let item = scored.get(key);
                    if (!item) {
                        item = {
                            score: 0,
                            hitGroups: new Set(),
                            video_title: video.title,
                            timestamp,
                            text,
                            summary: video.ai_summary || `💡 攝影點評：探討「${query}」相關實務拍攝經驗與參數設定`,
                            topic_tag: topicTag(text),
                            match_reason: `含關鍵字: ${query}`,
                            url: `https://www.youtube.com/watch?v=${videoId}&t=${Math.floor(Number(start) || 0)}s`,
                            type: '對白同義詞檢索',
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

        return [...scored.values()]
            .map(item => {
                if (item.hitGroups) {
                    const allMatched = item.hitGroups.size === totalTerms;
                    if (allMatched) {
                        item.score += 1000000;
                        item.match_reason = `🏆 「${query}」主題精華影片`;
                    }
                    delete item.hitGroups;
                }
                return item;
            })
            .sort((a, b) => b.score - a.score)
            .slice(0, MAX_SEARCH_RESULTS);
    }

    function initTheme() {
        const savedTheme = localStorage.getItem('ppvi-theme') || 'dark';
        setTheme(savedTheme);
    }

    function setTheme(theme) {
        htmlEl.setAttribute('data-theme', theme);
        localStorage.setItem('ppvi-theme', theme);

        if (themeToggleBtn) {
            const icon = themeToggleBtn.querySelector('.theme-icon');
            const text = themeToggleBtn.querySelector('.theme-text');
            if (theme === 'light') {
                if (icon) icon.textContent = '☀️';
                if (text) text.textContent = '亮色模式';
            } else {
                if (icon) icon.textContent = '🌙';
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
            latestVideosSection.style.display = 'none';
            renderSearchResultsByCategory();
            return;
        }

        let videos = [];
        if (catId === 'all') {
            sectionTitle.textContent = '全頻道熱門觀點與精選影片';
            encyclopediaData.categories.forEach(cat => {
                videos.push(...cat.videos);
            });
            
            latestVideosSection.style.display = 'block';
            latestVideoGrid.innerHTML = '';
            
            const uniqueMap = new Map();
            videos.forEach(v => uniqueMap.set(v.id, v));
            const uniqueVideos = Array.from(uniqueMap.values());
            
            const sortedVideos = [...uniqueVideos].sort((a, b) => {
                const da = a.publish_date || '1970-01-01';
                const db = b.publish_date || '1970-01-01';
                return db.localeCompare(da);
            });
            
            const latestVideos = sortedVideos.slice(0, 4);
            latestVideos.forEach(v => {
                latestVideoGrid.appendChild(createVideoCardElement(v));
            });
            
        } else {
            latestVideosSection.style.display = 'none';
            const catObj = encyclopediaData.categories.find(c => c.id === catId);
            if (catObj) {
                sectionTitle.textContent = `${catObj.name}`;
                videos = catObj.videos;
            }
        }

        resultCount.textContent = `共 ${videos.length} 部影片專題`;
        renderVideoCards(videos);
    }

    function createVideoCardElement(v) {
        const card = document.createElement('div');
        card.className = 'video-card';
        
        const thumbUrl = `https://img.youtube.com/vi/${v.id}/hqdefault.jpg`;
        const firstQuote = (v.sample_quotes && v.sample_quotes.length > 0) ? v.sample_quotes[0] : null;
        const tsText = firstQuote ? firstQuote.timestamp : '00:00';
        
        let summaryText = v.ai_summary;
        if (!summaryText && firstQuote && firstQuote.summary) {
            summaryText = firstQuote.summary;
        }
        if (!summaryText) {
            summaryText = `💡 實戰觀點：道慈老師針對「${v.title.slice(0, 18)}」分享攝影心法與器材操練要點`;
        }

        const targetUrl = firstQuote ? firstQuote.url : v.url;

        const isMember = checkIsMember(v);
        const badgeHtml = isMember 
            ? '<span class="badge-tag member-only">會員獨家</span>' 
            : '<span class="badge-tag public-free">公開影片</span>';

        const dateHtml = v.publish_date ? `<span style="font-size: 0.75rem; color: var(--text-muted); opacity: 0.85;">📅 ${escapeHtml(v.publish_date)}</span>` : '';

        card.innerHTML = `
            <div class="thumb-container">
                <img class="card-thumb" src="${thumbUrl}" alt="${escapeHtml(v.title)}" loading="lazy">
                ${badgeHtml}
                <span class="ts-badge">▶️ ${tsText} 點播</span>
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
            const clipText = r.text || '';

            if (filterVideoByCategory(r.video_title, clipText, currentCategory, r)) {
                if (!groupedMap.has(key)) {
                    groupedMap.set(key, {
                        vId: vId,
                        video_title: r.video_title,
                        publish_date: r.publish_date || '',
                        is_member_only: checkIsMember(r),
                        clips: []
                    });
                }
                groupedMap.get(key).clips.push({
                    timestamp: r.timestamp,
                    text: r.text,
                    summary: createClipListeningGuide(r.text, lastSearchQuery),
                    topic_tag: r.topic_tag || '🎧 本段導讀',
                    match_reason: r.match_reason || `含關鍵字: ${lastSearchQuery}`,
                    url: r.url
                });
            }
        });

        const groupedVideos = Array.from(groupedMap.values());

        const catNames = {
            'all': '全頻道專題',
            'daily': '📸 日常影片 (外出拍照)',
            'gear': '📷 器材評測 (介紹器材)',
            'live': '🎙️ 直播存檔 (八點半與週報)',
            'member_review': '👑 會員評圖 (每月評圖)',
            'book': '📚 讀書會 (攝影集介紹)'
        };

        const catLabel = catNames[currentCategory] || '';
        sectionTitle.textContent = `搜尋「${lastSearchQuery}」 ‧ ${catLabel}`;
        resultCount.textContent = `共 ${groupedVideos.length} 部符合分類影片專題`;

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
                featureBadgeHtml = `<span class="featured-label">🏆 「${lastSearchQuery}」主題精華</span>`;
            }

            const dateHtml = item.publish_date ? `<span style="font-size: 0.75rem; color: var(--text-muted); opacity: 0.85;">📅 ${escapeHtml(item.publish_date)}</span>` : '';

            const INITIAL_SHOW = 2;
            const visibleClips = item.clips.slice(0, INITIAL_SHOW);
            const hiddenClips = item.clips.slice(INITIAL_SHOW);

            let clipsHtml = '<div class="clips-wrapper">';
            
            visibleClips.forEach(clip => {
                clipsHtml += `
                    <div class="clip-node" data-url="${escapeHtml(clip.url)}">
                        <div class="clip-meta">
                            <span class="topic-label">${escapeHtml(clip.topic_tag)}</span>
                            <span class="ts-link">▶️ ${clip.timestamp} 點播</span>
                        </div>
                        <div class="match-reason-pill">🎯 ${escapeHtml(clip.match_reason)}</div>
                        <div class="summary-block">
                            <div class="summary-text">${escapeHtml(clip.summary)}</div>
                        </div>
                        <div class="quote-text">📝 逐字稿原文：「${escapeHtml(clip.text)}」</div>
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
                                <span class="ts-link">▶️ ${clip.timestamp} 點播</span>
                            </div>
                            <div class="match-reason-pill">🎯 ${escapeHtml(clip.match_reason)}</div>
                            <div class="summary-block">
                                <div class="summary-text">${escapeHtml(clip.summary)}</div>
                            </div>
                            <div class="quote-text">📝 逐字稿原文：「${escapeHtml(clip.text)}」</div>
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
                    <span class="ts-badge">共 ${item.clips.length} 個重點對話</span>
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
