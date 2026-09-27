(() => {
    const data = window.CHANNEL_KNOWLEDGE_WIKI;
    const app = document.getElementById('app');
    const search = document.getElementById('knowledge-query');
    const hubs = new Map(data.hubs.map(h => [h.id, h]));
    const articles = new Map(data.articles.map(a => [a.id, a]));
    const subjects = new Map((data.subjects || []).map(s => [s.id, s]));
    let page = 1;
    let requestCounts = null;
    let countsFailed = false;
    const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const link = state => '#' + new URLSearchParams(state).toString();
    const topics = id => data.articles.filter(a => a.hub === id);
    const videoSearch = words => '../?q=' + encodeURIComponent(words);
    function markdown(text) {
        return String(text || '').split(/\n\n+/).map(block => {
            const lines = block.split('\n').filter(Boolean);
            const list = lines.every(line => /^\s*(?:\d+\.|[-*])\s/.test(line));
            const inline = value => esc(value).replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
            return list ? '<ul>' + lines.map(line => '<li>' + inline(line.replace(/^\s*(?:\d+\.|[-*])\s/,'')) + '</li>').join('') + '</ul>'
                : '<p>' + inline(block) + '</p>';
        }).join('');
    }
    function readingMeta(article) {
        const length = (article.sections || []).flatMap(s=>s.paragraphs).reduce((n,p)=>n+p.text.length,0);
        return `${new Set(article.sources.map(s=>s.video_id)).size} 支來源影片${length ? ` · 約 ${Math.max(1,Math.ceil(length/450))} 分鐘閱讀` : ''}`;
    }
    function topicRow(article, subject) {
        return `<a class="topic-row" href="${link({point:article.id,...(subject ? {subject} : {})})}"><span><strong>${esc(article.display_title)}</strong><small>${esc(readingMeta(article))}</small></span><span aria-hidden="true">↗</span></a>`;
    }
    function subjectLinks(active) {
        return `<nav class="subject-pills" aria-label="拍攝題材">${[...subjects.values()].map(s=>`<a href="${link({subject:s.id})}" ${active===s.id?'aria-current="page"':''}>${esc(s.title)}</a>`).join('')}</nav>`;
    }
    function subjectPage(subject) {
        const ordered = subject.reading_order.map(id=>articles.get(id));
        const first = ordered[0];
        return `<nav class="breadcrumb"><a href="#">知識地圖</a><span>／</span><span>依題材閱讀</span></nav>${subjectLinks(subject.id)}<header class="subject-header"><p class="map-eyebrow">${esc(subject.eyebrow)}</p><h1>${esc(subject.title)}攝影</h1><p class="reading-lead">${esc(subject.intro)}</p></header><section class="featured-article"><span class="map-eyebrow">從這篇開始</span><h2><a href="${link({point:first.id,subject:subject.id})}">${esc(first.display_title)}</a></h2><p>${esc(first.lead)}</p><span class="map-meta">${esc(readingMeta(first))}</span><a class="quiet-action" href="${link({point:first.id,subject:subject.id})}">開始閱讀 →</a></section><div class="map-section-head"><h2>接著，依需要往下讀</h2><p>共 ${ordered.length} 篇文章</p></div><div class="subject-reading-list">${ordered.slice(1).map((a,i)=>`<article><span class="route-number">${String(i+2).padStart(2,'0')}</span><div>${topicRow(a,subject.id)}<p>${esc(a.lead)}</p></div></article>`).join('')}</div>`;
    }
    function sourcesMarkup(sources) {
        return `<div class="source-grid">${sources.map((s,i) => {
            const id = s.video_id || new URL(s.url).searchParams.get('v');
            return `<div class="source-card" id="source-${i+1}"><div class="source-card-head"><img src="https://img.youtube.com/vi/${encodeURIComponent(id)}/hqdefault.jpg" alt="${esc(s.title || s.label)}" loading="lazy"><div><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${i+1}. ${esc(s.title || s.label)} ↗</a><br><span class="source-time">${esc(s.timestamp || '開啟原片時間點')} · ${s.member_only ? '會員影片' : '公開影片'}</span></div></div><blockquote><span>${s.paragraph_id ? '逐字稿摘錄' : '來源內容提示'}</span>${esc(s.quote)}</blockquote></div>`;
        }).join('')}</div>`;
    }
    function home() {
        return `<div class="map-section-head"><div><p class="map-eyebrow">今天，想拍什麼？</p><h2>先從拍攝題材開始</h2></div><p>同樣的技術，不同的現場選擇</p></div><div class="subject-grid">${[...subjects.values()].map((s,i)=>`<a class="subject-card subject-${s.id}" href="${link({subject:s.id})}"><span class="subject-index">0${i+1} / ${s.reading_order.length} 篇</span><h2>${esc(s.title)}</h2><p>${esc(s.eyebrow)}</p><span class="subject-arrow" aria-hidden="true">↗</span></a>`).join('')}</div><div class="map-section-head"><div><p class="map-eyebrow">也可以，沿著觀念慢慢讀</p><h2>八個章節，串起拍攝的過程</h2></div><p>${data.hubs.length} 章 · ${data.articles.length} 篇文章</p></div><div class="chapter-grid">${data.hubs.map(h => `<section class="chapter-card"><span class="chapter-number">CHAPTER ${esc(h.number)}</span><h2><a href="${link({chapter:h.id})}">${esc(h.title)}</a></h2><p>${esc(h.intro)}</p>${topics(h.id).map(a=>topicRow(a)).join('')}</section>`).join('')}</div><div class="pager"><a class="quiet-action" href="${link({view:'videos'})}">查看全頻道影片筆記</a><a class="quiet-action" href="#view=requests">敲碗下一堂課 →</a></div>`;
    }
    function notes(videos) {
        return `<div class="notes-grid">${videos.slice(0,page*18).map(v => `<article class="video-note"><div class="map-meta">${esc(v.date || '日期未確認')} · ${v.kind === 'approved' ? '摘要有來源' : '人工摘要／例外'}</div><h3><a href="${esc(v.url)}" target="_blank" rel="noopener noreferrer">${esc(v.title)} ↗</a></h3><p>${esc(v.summary)}</p><div class="note-evidence">${(v.evidence || []).map(e=>`<a href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">${esc(e.label)}</a>`).join('')}</div></article>`).join('')}</div>${videos.length>page*18?'<div class="pager"><button class="quiet-action" data-more>載入更多影片</button></div>':''}`;
    }
    function articleMarkup(article, subject) {
        const hub = hubs.get(article.hub);
        const words = article.search_terms?.join(' ') || article.keywords?.slice(0,2).join(' ') || hub.title;
        const claims = article.claims?.map(c => `<p>${esc(c.text)} ${c.sources.map(n=>`<a class="evidence-ref" href="#source-${n}" data-source="${n}" aria-label="查看來源 ${n}">[${n}]</a>`).join('')}</p>`).join('') || markdown(article.interpretation);
        const route = subject?.reading_order || topics(hub.id).map(a=>a.id);
        const next = articles.get(route[route.indexOf(article.id)+1]);
        const sections = article.sections || [];
        const body = sections.length ? sections.map(s=>`<section class="reading-section" id="${esc(s.id)}" tabindex="-1"><h2>${esc(s.title)}</h2>${s.paragraphs.map(p=>`<p>${esc(p.text)} ${p.sources.map(n=>`<a class="evidence-ref" href="#source-${n}" data-source="${n}" aria-label="查看來源 ${n}">[${n}]</a>`).join('')}</p>`).join('')}</section>`).join('') : `<section class="reading-section"><h2>老師怎麼說</h2>${claims}</section>`;
        const toc = sections.length ? `<nav class="article-toc" aria-label="本篇目錄"><p>這篇會讀到</p><ol>${sections.map(s=>`<li><a href="#${esc(s.id)}" data-section="${esc(s.id)}">${esc(s.title)}</a></li>`).join('')}</ol></nav>` : '';
        return `<article class="reading"><nav class="breadcrumb" aria-label="閱讀位置"><a href="#">知識地圖</a><span>／</span>${subject?`<a href="${link({subject:subject.id})}">${esc(subject.title)}攝影</a>`:`<a href="${link({chapter:hub.id})}">${esc(hub.title)}</a>`}</nav><div class="article-tags">${(article.subjects||[]).map(id=>`<a href="${link({subject:id})}">${esc(subjects.get(id).title)}</a>`).join('')}<span>${esc(hub.title)}</span></div><h1>${esc(article.display_title)}</h1><p class="reading-lead">${esc(article.lead || '')}</p><p class="article-byline">整理自道慈老師的頻道內容 · ${esc(readingMeta(article))}</p><div class="reading-toolbar"><a class="quiet-action" href="${videoSearch(words)}">延伸找影片 ↗</a><button class="quiet-action" data-copy-link>複製文章連結</button></div>${toc}${body}<section class="reading-section boundary-panel"><h2>這篇文章的適用範圍</h2>${markdown(article.boundaries)}</section><details class="article-sources"><summary>查看 ${article.sources.length} 段原片來源與逐字稿摘錄</summary><p class="map-meta">段落依逐字稿整理，點時間可回到原片。影片中的器材、軟體與場景資訊保留當時情境。</p>${sourcesMarkup(article.sources)}</details><nav class="article-next" aria-label="延伸閱讀">${next?`<span class="map-eyebrow">${subject?esc(subject.title)+'攝影':'同章節'} · 接著讀</span><a href="${link({point:next.id,...(subject?{subject:subject.id}:{})})}">${esc(next.display_title)} →</a>`:''}<a class="gap-link" href="${subject?link({subject:subject.id}):link({chapter:hub.id})}">${subject?'回到'+esc(subject.title)+'題材':'回到'+esc(hub.title)}的文章目錄</a></nav>${article.gap ? `<section class="gap-panel"><span class="gap-label">編輯提出的補拍問題</span><h3>${esc(article.gap.question)}</h3><p>${esc(article.gap.reason)}</p><p>${esc(article.gap.coverage_note)}</p><button class="quiet-action" data-request="${esc(article.id)}">敲碗老師拍這題</button><p class="gap-status" role="status">${window.AIOKLessonRequests.enabled ? '集中收集需求；以此瀏覽器的匿名識別碼避免重複紀錄。' : '介面預覽：集中收集尚未開放，點擊不會送出。'}</p><a class="gap-link" href="#view=requests">看看大家想學什麼 →</a></section>` : ''}</article>`;
    }
    function requestsMarkup() {
        const live = requestCounts !== null;
        const entries = [...data.articles].sort((a,b) => (requestCounts?.[b.id] || 0) - (requestCounts?.[a.id] || 0));
        return `<nav class="breadcrumb"><a href="#">全部章節</a></nav><div class="map-section-head"><div><p class="map-eyebrow">下一堂，你想學什麼？</p><h2>敲碗清單</h2></div><span class="map-meta">${live ? '依敲碗次數排序' : '尚無統計'}</span></div><p class="reading-lead">${live ? '把想深入學習的題目告訴老師。這份清單顯示收到的需求，不代表已排定拍攝。' : window.AIOKLessonRequests.enabled ? (countsFailed ? '目前無法取得統計，請稍後重試。' : '正在取得敲碗統計…') : '先看看每個知識點還可以延伸哪些示範。集中收集尚未開放，目前依章節排列。'}</p><div class="request-list">${entries.map(a=>`<article class="request-item"><span class="request-count">${live ? (requestCounts[a.id] || 0)+' 次敲碗' : '尚未統計'}</span><div><span class="map-meta">${esc(hubs.get(a.hub).title)}</span><h3><a href="${link({point:a.id})}">${esc(a.gap.question)}</a></h3><p>${esc(a.gap.reason)}</p></div></article>`).join('')}</div>`;
    }
    function render() {
        const legacy = location.hash.slice(1);
        const legacyChapter = legacy === 'exposure' ? 'light' : legacy;
        const state = new URLSearchParams(hubs.has(legacyChapter) ? `chapter=${legacyChapter}` : legacy === 'all' ? 'view=videos' : legacy);
        const point = articles.get(state.get('point'));
        const subject = subjects.get(state.get('subject'));
        const chapter = hubs.get(state.get('chapter'));
        const query = state.get('q') || '';
        search.value = query;
        document.querySelectorAll('#chapter-nav a').forEach(a => a.removeAttribute('aria-current'));
        const active = point?.hub || chapter?.id;
        document.querySelector(`#chapter-nav a[data-chapter="${active || 'all'}"]`)?.setAttribute('aria-current','page');
        document.body.classList.toggle('is-reading',Boolean(point));
        if (point) app.innerHTML = articleMarkup(point,subject?.reading_order.includes(point.id)?subject:null);
        else if (subject) app.innerHTML = subjectPage(subject);
        else if (chapter) app.innerHTML = `<nav class="breadcrumb"><a href="#">全部章節</a></nav><div class="map-section-head"><div><p class="map-eyebrow">CHAPTER ${esc(chapter.number)}</p><h2>${esc(chapter.title)}</h2></div></div><p class="reading-lead">${esc(chapter.intro)}</p><div class="topic-results">${topics(chapter.id).map(a=>topicRow(a)).join('')}</div><div class="map-section-head"><h2>延伸影片筆記</h2><p>逐字稿支持的摘要與例外分開標示</p></div>${notes(data.videos.filter(v=>v.primary_hub===chapter.id))}`;
        else if (query) {
            const results = window.AIOKKnowledgeSearch.find(query,data.articles);
            app.innerHTML = `<div class="map-section-head"><h2>找「${esc(query)}」的知識</h2><p>${results.length} 個知識點</p></div><div class="topic-results">${results.map(a=>topicRow(a)).join('') || `<div class="empty-state"><p>目前的知識點還沒有符合這個說法。</p><a class="quiet-action" href="${videoSearch(query)}">到全頻道逐字稿繼續找 ↗</a></div>`}</div>`;
        } else if (state.get('view') === 'requests') app.innerHTML = requestsMarkup() + (countsFailed ? '<div class="pager"><button class="quiet-action" data-retry-counts>重新取得統計</button></div>' : '');
        else if (state.get('view') === 'videos') app.innerHTML = `<div class="map-section-head"><h2>全頻道影片筆記</h2><p>${data.videos.length} 支完成知識處理</p></div>${notes(data.videos)}`;
        else app.innerHTML = home();
        document.title = `${point?.display_title || (subject?subject.title+'攝影':chapter?.title) || '攝影知識地圖'}｜複習都OK`;
    }
    document.getElementById('chapter-nav').innerHTML = `<a href="#" data-chapter="all">全部章節</a>` + data.hubs.map(h=>`<a href="${link({chapter:h.id})}" data-chapter="${esc(h.id)}">${esc(h.number)} ${esc(h.title)}</a>`).join('');
    document.getElementById('corpus-status').textContent = `${data.stats.total_videos.toLocaleString('zh-TW')} 部來源影片${data.stats.pending_pipeline_videos ? ' · 資料同步中' : ''}`;
    document.getElementById('footer-count').textContent = `${data.stats.total_videos.toLocaleString('zh-TW')} 支影片已同步；${data.stats.processed_videos.toLocaleString('zh-TW')} 支完成知識處理 · ${data.stats.passage_count.toLocaleString('zh-TW')} 段可回查來源`;
    document.getElementById('knowledge-search').addEventListener('submit', e => {e.preventDefault(); location.hash = search.value.trim() ? link({q:search.value.trim()}) : '';});
    app.addEventListener('click', async e => {
        if (e.target.closest('[data-retry-counts]')) {countsFailed=false;render();loadCounts();}
        const request = e.target.closest('[data-request]');
        if (request) {
            const status = request.parentElement.querySelector('.gap-status');
            request.disabled = true;
            const result = await window.AIOKLessonRequests.vote(request.dataset.request);
            request.disabled = false;
            if (result.status === 'preview') status.textContent = '這是介面預覽，尚未送出。開放後，老師就能集中看到這一題的需求。';
            else if (result.status === 'received') {
                request.textContent = '已敲碗'; request.disabled = true;
                status.textContent = `${result.duplicate ? '這個瀏覽器已經敲過這題，沒有重複增加。' : '已收到你的敲碗。'} 目前共 ${result.count} 次。`;
                requestCounts = null;
            } else if (result.status === 'failed') status.textContent = '目前無法確認是否送達，請再試一次；重試不會重複增加同一題的敲碗。';
        }
        const source = e.target.closest('[data-source]');
        if (source) {e.preventDefault();const target=document.getElementById(`source-${source.dataset.source}`);if(target){target.closest('details').open=true;target.scrollIntoView({block:'start'});}}
        const section = e.target.closest('[data-section]');
        if (section) {e.preventDefault();const target=document.getElementById(section.dataset.section);target?.focus({preventScroll:true});target?.scrollIntoView({block:'start'});}
        if (e.target.closest('[data-more]')) {page += 1; render();}
        const copy = e.target.closest('[data-copy-link]');
        if (copy) {try {await navigator.clipboard.writeText(location.href); copy.textContent='已複製連結';} catch {copy.textContent='請複製網址列的連結';}}
    });
    window.addEventListener('hashchange', () => {page=1;render();app.focus({preventScroll:true});app.scrollIntoView({block:'start'});loadCounts();});
    async function loadCounts() {
        if (!location.hash.includes('view=requests') || !window.AIOKLessonRequests.enabled || requestCounts !== null) return;
        try {requestCounts = await window.AIOKLessonRequests.counts(); countsFailed=false;} catch {countsFailed=true;}
        if (location.hash.includes('view=requests')) render();
    }
    const theme = document.getElementById('themeToggleBtn');
    const setTheme = value => {document.documentElement.dataset.theme=value;theme.querySelector('.theme-icon').textContent=value==='dark'?'☾':'☀';theme.querySelector('.theme-text').textContent=value==='dark'?'深色模式':'亮色模式';};
    try {setTheme(localStorage.getItem('ppvi-theme') || 'light');} catch {setTheme('light');}
    theme.addEventListener('click',()=>{const value=document.documentElement.dataset.theme==='dark'?'light':'dark';setTheme(value);try{localStorage.setItem('ppvi-theme',value);}catch{}});
    render();
    window.dispatchEvent(new Event('aiok-content-ready'));
    loadCounts();
})();
