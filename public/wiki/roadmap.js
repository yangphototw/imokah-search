// This preview is static. Filtering and links require no AI or external service.
(() => {
  'use strict';
  const themeButton = document.getElementById('themeToggleBtn');
  function setTheme(value) {
    const theme = value === 'dark' ? 'dark' : 'light';
    document.documentElement.dataset.theme = theme;
    themeButton.querySelector('.theme-text').textContent = theme === 'dark' ? '暗色模式' : '亮色模式';
    themeButton.querySelector('.theme-icon').textContent = theme === 'dark' ? '☾' : '☀';
    themeButton.setAttribute('aria-label', theme === 'dark' ? '切換為亮色模式' : '切換為暗色模式');
  }
  try { setTheme(localStorage.getItem('ppvi-theme')); } catch { setTheme('light'); }
  themeButton.addEventListener('click', () => {
    const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    setTheme(theme);
    try { localStorage.setItem('ppvi-theme', theme); } catch { /* Optional preference. */ }
  });
  const points = [...document.querySelectorAll('.knowledge-point')];
  const chapters = [...document.querySelectorAll('[data-chapter]')];
  const buttons = [...document.querySelectorAll('[data-subject]')];
  const navLinks = [...document.querySelectorAll('[data-chapter-link]')];
  const status = document.getElementById('filter-status');
  function applyFilter(subject) {
    let count = 0;
    points.forEach(point => {
      point.hidden = subject !== 'everything' && !point.dataset.subjects.split(' ').includes(subject);
      if (!point.hidden) count += 1;
    });
    chapters.forEach(chapter => {
      const visibleCount = [...chapter.querySelectorAll('.knowledge-point')].filter(point => !point.hidden).length;
      chapter.hidden = visibleCount === 0;
      const label = chapter.querySelector('[data-total-points]');
      label.textContent = subject === 'everything'
        ? `${label.dataset.totalPoints} 個學習問題`
        : `顯示 ${visibleCount} 個題材相關問題`;
      navLinks.find(link => link.dataset.chapterLink === chapter.dataset.chapter).hidden = chapter.hidden;
    });
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.subject === subject)));
    const name = buttons.find(button => button.dataset.subject === subject)?.textContent || '';
    status.textContent = subject === 'everything'
      ? `目前整理 ${count} 個知識項目；後續盤點會持續增加與合併。`
      : `${name}相關：${count} 個已標記的知識項目。共通觀念可回到「全部知識」閱讀。`;
  }
  buttons.forEach(button => button.addEventListener('click', () => applyFilter(button.dataset.subject)));
  document.querySelector('.subject-filter').hidden = false;

  function revealHash() {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const target = document.getElementById(id);
    if (!target) return;
    if (target.closest('[hidden]')) applyFilter('everything');
    let ancestor = target;
    while (ancestor) {
      if (ancestor.tagName === 'DETAILS') ancestor.open = true;
      ancestor = ancestor.parentElement;
    }
    const chapter = target.closest('[data-chapter]');
    navLinks.forEach(link => {
      if (chapter?.dataset.chapter === link.dataset.chapterLink) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    requestAnimationFrame(() => target.scrollIntoView({block: 'start'}));
  }
  window.addEventListener('hashchange', revealHash);
  // Reopening the same anchor must work after its details were collapsed.
  document.addEventListener('click', event => {
    const anchor = event.target.closest('a[href^="#"]');
    if (anchor && anchor.hash === location.hash) revealHash();
  });
  revealHash();
  window.dispatchEvent(new Event('aiok-content-ready'));
})();
