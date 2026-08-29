document.addEventListener('DOMContentLoaded', () => {
    const html = document.documentElement;
    const filter = document.getElementById('reviewFilter');
    const count = document.getElementById('reviewCount');
    const grid = document.getElementById('reviewGrid');
    const exceptionCount = document.getElementById('exceptionCount');
    const exceptionGrid = document.getElementById('exceptionGrid');
    const themeButton = document.getElementById('themeToggleBtn');
    let videos = [];
    let exceptions = [];

    const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (character) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    })[character]);

    const formatTimestamp = (seconds) => {
        const value = Math.max(0, Math.floor(Number(seconds) || 0));
        return `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`;
    };

    const videoUrlAt = (videoId, seconds) => `https://www.youtube.com/watch?v=${encodeURIComponent(videoId)}&t=${Math.floor(Number(seconds) || 0)}s`;

    function setTheme(theme) {
        html.setAttribute('data-theme', theme);
        localStorage.setItem('ppvi-theme', theme);
        const icon = themeButton?.querySelector('.theme-icon');
        const text = themeButton?.querySelector('.theme-text');
        if (icon) icon.textContent = theme === 'dark' ? '☾' : '☀';
        if (text) text.textContent = theme === 'dark' ? '深色模式' : '亮色模式';
    }

    function render() {
        const query = filter.value.trim().toLocaleLowerCase('zh-TW');
        const matched = videos.filter((video) => (
            !query || `${video.title} ${video.summary}`.toLocaleLowerCase('zh-TW').includes(query)
        ));
        count.textContent = query
            ? `符合 ${matched.length} / ${videos.length} 支人工校閱影片`
            : `共 ${videos.length} 支人工校閱影片`;

        if (!matched.length) {
            grid.innerHTML = '<p class="review-empty">沒有符合的已校閱影片，請換一個關鍵字。</p>';
        } else {
            grid.innerHTML = matched.map((video) => {
                const evidence = (Array.isArray(video.evidence) ? video.evidence : []).map((item) => (
                    `<a class="evidence-time" href="${videoUrlAt(video.id, item.start)}" target="_blank" rel="noopener noreferrer">${formatTimestamp(item.start)}</a>`
                )).join('');
                const hasEvidence = evidence.length > 0;
                const provenance = hasEvidence
                    ? `逐字稿核對 · ${video.evidence.length} 段證據`
                    : '頻道方人工核可摘要';
                const evidenceBlock = hasEvidence
                    ? `<div class="review-evidence"><span>核對段落</span><div class="evidence-times">${evidence}</div></div>`
                    : '<p class="review-evidence">此摘要由頻道方人工核可；未主張逐字稿時間點證據。</p>';
                const thumbnail = `https://img.youtube.com/vi/${encodeURIComponent(video.id)}/hqdefault.jpg`;
                return `
                <article class="review-card">
                    <a class="review-thumb" href="${escapeHtml(video.url)}" target="_blank" rel="noopener noreferrer" aria-label="在 YouTube 開啟：${escapeHtml(video.title)}">
                        <img src="${thumbnail}" alt="${escapeHtml(video.title)}" loading="lazy">
                    </a>
                    <div class="review-card-content">
                        <p class="review-proof">${provenance}</p>
                        <h2 class="type-lvl-3-title"><a href="${escapeHtml(video.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(video.title)}</a></h2>
                        <p class="review-summary">${escapeHtml(video.summary)}</p>
                        ${evidenceBlock}
                    </div>
                </article>`;
            }).join('');
        }

        if (!exceptionGrid) return;
        if (exceptionCount) {
            exceptionCount.textContent = `共 ${exceptions.length} 支待逐字稿修復影片`;
        }
        if (!exceptions.length) {
            exceptionGrid.innerHTML = '<p class="review-empty">目前沒有待修復的逐字稿例外。</p>';
            return;
        }
        exceptionGrid.innerHTML = exceptions.map((video) => `
            <article class="review-card">
                <div class="review-card-content">
                    <p class="review-proof">待音訊／逐字稿修復</p>
                    <h3 class="type-lvl-3-title"><a href="${escapeHtml(video.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(video.title)}</a></h3>
                    <p class="review-summary">${escapeHtml(video.reason)}</p>
                </div>
            </article>`).join('');
    }

    themeButton?.addEventListener('click', () => {
        setTheme(html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
    });
    setTheme(localStorage.getItem('ppvi-theme') || 'light');
    filter.addEventListener('input', render);

    const embeddedData = window.APPROVED_VIDEO_SUMMARIES;
    if (Array.isArray(embeddedData?.videos)) {
        videos = embeddedData.videos;
        exceptions = Array.isArray(embeddedData.exceptions) ? embeddedData.exceptions : [];
        render();
        return;
    }

    fetch('approved-video-summaries.json')
        .then((response) => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then((payload) => {
            videos = Array.isArray(payload.videos) ? payload.videos : [];
            exceptions = Array.isArray(payload.exceptions) ? payload.exceptions : [];
            render();
        })
        .catch(() => {
            count.textContent = '審查資料載入失敗。';
            grid.innerHTML = '<p class="review-empty">目前無法載入審查資料，請重新整理頁面。</p>';
        });
});
