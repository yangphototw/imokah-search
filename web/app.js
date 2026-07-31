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
            const res = await fetch('/api/encyclopedia');
            if (!res.ok) throw new Error('API request failed');
            encyclopediaData = await res.json();
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
            sectionTitle.textContent = '全頻道熱門觀點與精選影片';
            encyclopediaData.categories.forEach(cat => {
                videos.push(...cat.videos);
            });
        } else {
            const catObj = encyclopediaData.categories.find(c => c.id === catId);
            if (catObj) {
                sectionTitle.textContent = `${catObj.name}`;
                videos = catObj.videos;
            }
        }

        resultCount.textContent = `共 ${videos.length} 部影片專題`;
        renderVideoCards(videos);
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

                const dateHtml = v.publish_date ? `<span style="font-size: 0.75rem; color: var(--text-muted); opacity: 0.85;">📅 ${v.publish_date}</span>` : '';

                card.innerHTML = `
                    <div class="thumb-container">
                        <img class="card-thumb" src="${thumbUrl}" alt="${v.title}" loading="lazy">
                        ${badgeHtml}
                        <span class="ts-badge">▶️ ${tsText} 點播</span>
                    </div>
                    <div class="card-content">
                        ${dateHtml ? `<div style="margin-bottom: 6px;">${dateHtml}</div>` : ''}
                        <h3 class="type-lvl-3-title" title="${v.title}">${v.title}</h3>
                        <div class="summary-block">
                            <div class="summary-text">${summaryText}</div>
                        </div>
                    </div>
                `;

                card.addEventListener('click', () => {
                    window.open(targetUrl, '_blank');
                });

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
                    summary: r.summary || r.text,
                    topic_tag: r.topic_tag || '💡 【核心觀點】',
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
                    <div style="font-size: 1.1rem; color: var(--text-primary); font-weight: 700;">在「${catLabel}」分類中未找到「${lastSearchQuery}」相關影片</div>
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

            const dateHtml = item.publish_date ? `<span style="font-size: 0.75rem; color: var(--text-muted); opacity: 0.85;">📅 ${item.publish_date}</span>` : '';

            const INITIAL_SHOW = 2;
            const visibleClips = item.clips.slice(0, INITIAL_SHOW);
            const hiddenClips = item.clips.slice(INITIAL_SHOW);

            let clipsHtml = '<div class="clips-wrapper">';
            
            visibleClips.forEach(clip => {
                clipsHtml += `
                    <div class="clip-node" data-url="${clip.url}">
                        <div class="clip-meta">
                            <span class="topic-label">${clip.topic_tag}</span>
                            <span class="ts-link">▶️ ${clip.timestamp} 點播</span>
                        </div>
                        <div class="match-reason-pill">🎯 ${clip.match_reason}</div>
                        <div class="summary-block">
                            <div class="summary-text">${clip.summary}</div>
                        </div>
                        <div class="quote-text">💬 原對白：「${clip.text}」</div>
                    </div>
                `;
            });

            if (hiddenClips.length > 0) {
                clipsHtml += `<div class="more-clips-container" style="display: none;">`;
                hiddenClips.forEach(clip => {
                    clipsHtml += `
                        <div class="clip-node" data-url="${clip.url}">
                            <div class="clip-meta">
                                <span class="topic-label">${clip.topic_tag}</span>
                                <span class="ts-link">▶️ ${clip.timestamp} 點播</span>
                            </div>
                            <div class="match-reason-pill">🎯 ${clip.match_reason}</div>
                            <div class="summary-block">
                                <div class="summary-text">${clip.summary}</div>
                            </div>
                            <div class="quote-text">💬 原對白：「${clip.text}」</div>
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
                    <img class="card-thumb" src="${thumbUrl}" alt="${item.video_title}" loading="lazy">
                    ${badgeHtml}
                    <span class="ts-badge">共 ${item.clips.length} 個重點對話</span>
                </div>
                <div class="card-content">
                    ${dateHtml ? `<div style="margin-bottom: 6px;">${dateHtml}</div>` : ''}
                    ${featureBadgeHtml}
                    <h3 class="type-lvl-3-title">${item.video_title}</h3>
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
        resultCount.textContent = '倒排索引比對 ‧ 載入 Gemini 3.6 觀點...';

        try {
            const res = await fetch(`/api/search?q=${encodeURIComponent(cleanQuery)}`);
            currentRawSearchResults = await res.json();
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
