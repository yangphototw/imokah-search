// The two reading modes remember their own location within this browser tab.
(() => {
    const key = location.pathname.startsWith('/wiki') ? 'knowledge' : 'videos';
    const remember = () => {
        try {
            sessionStorage.setItem(`aiok-location-${key}`, location.pathname + location.search + location.hash);
            sessionStorage.setItem(`aiok-scroll-${key}`, String(window.scrollY));
        } catch {}
    };
    const restoreLinks = () => {
        document.querySelectorAll('[data-mode-link]').forEach(link => {
            if (link.dataset.modeLink === key) return;
            try {
                const saved = sessionStorage.getItem(`aiok-location-${link.dataset.modeLink}`);
                if (!saved) return;
                const url = new URL(saved, location.origin);
                const valid = link.dataset.modeLink === 'knowledge'
                    ? url.pathname === '/wiki/' || url.pathname === '/wiki/index.html'
                        || url.pathname === '/wiki/roadmap.html' || /^\/wiki\/chapters\/[a-z0-9-]+\.html$/.test(url.pathname)
                    : url.pathname === '/' || url.pathname === '/index.html';
                if (url.origin === location.origin && valid) link.href = url.pathname + url.search + url.hash;
            } catch {}
        });
    };
    window.addEventListener('pagehide', remember);
    window.addEventListener('hashchange', remember);
    window.addEventListener('pageshow', event => {restoreLinks(); if (event.persisted) restorePosition();});
    document.querySelectorAll('[data-mode-link]').forEach(link => link.addEventListener('click', () => {
        if (link.dataset.modeLink === key) return;
        try { sessionStorage.setItem('aiok-restore-mode', link.dataset.modeLink); } catch {}
    }));
    function restorePosition() {
        try {
            if (sessionStorage.getItem('aiok-restore-mode') !== key) return;
            sessionStorage.removeItem('aiok-restore-mode');
            const offset = Number(sessionStorage.getItem(`aiok-scroll-${key}`));
            // Reaching a header link can scroll the page to the top. Preserve the
            // chosen reading section instead of replacing its anchor with zero.
            if (offset === 0 && location.hash && document.body.classList.contains('reader-page')) return;
            if (Number.isFinite(offset) && offset >= 0) requestAnimationFrame(() => window.scrollTo(0,offset));
        } catch {}
    }
    window.addEventListener('aiok-content-ready', restorePosition);
    // Preserve the previous mode's saved position until its content has loaded.
    restoreLinks();
})();
