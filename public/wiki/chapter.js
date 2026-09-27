(() => {
  'use strict';
  const theme = document.getElementById('reader-theme');
  function setTheme(value) {
    const dark = value === 'dark';
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    theme.querySelector('.theme-text').textContent = dark ? '暗色模式' : '亮色模式';
    theme.querySelector('.theme-icon').textContent = dark ? '☾' : '☀';
    theme.setAttribute('aria-label', dark ? '切換為亮色模式' : '切換為暗色模式');
  }
  try { setTheme(localStorage.getItem('ppvi-theme')); } catch { setTheme('light'); }
  theme.addEventListener('click', () => {
    const value = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    setTheme(value);
    try { localStorage.setItem('ppvi-theme', value); } catch { /* Optional preference. */ }
  });

  const contents = document.getElementById('reader-contents');
  const narrowScreen = matchMedia('(max-width:900px)');
  contents.open = !narrowScreen.matches;
  narrowScreen.addEventListener('change', event => { contents.open = !event.matches; });
  const sections = [...document.querySelectorAll('.reader-section')];
  const chapterLinks = [...document.querySelectorAll('[data-section-link]')];
  const position = document.querySelector('.reader-position');
  const next = document.getElementById('reader-next');
  const current = document.getElementById('reader-current');
  position.hidden = false;

  function updatePosition() {
    const threshold = Math.max(position.getBoundingClientRect().height + 56, Math.min(innerHeight * .35, 280));
    let index = -1;
    sections.forEach((section, i) => { if (section.getBoundingClientRect().top <= threshold) index = i; });
    const atSources = document.getElementById('chapter-sources').getBoundingClientRect().top <= threshold;
    chapterLinks.forEach(link => {
      if (!atSources && index >= 0 && link.dataset.sectionLink === sections[index].id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    current.textContent = atSources ? '本章影片來源' : index < 0 ? '準備開始 · 共 ' + sections.length + ' 節'
      : (index + 1) + ' / ' + sections.length + ' · ' + sections[index].dataset.shortTitle;
    next.href = atSources ? '#chapter-top' : index < sections.length - 1 ? '#' + sections[index + 1].id : '#chapter-sources';
    next.textContent = atSources ? '回到開頭 ↑' : index < 0 ? '開始閱讀 ↓' : index < sections.length - 1 ? '下一節 →' : '影片來源 ↓';
  }
  let frame;
  function schedulePosition() {
    if (frame) return;
    frame = requestAnimationFrame(() => { frame = null; updatePosition(); });
  }
  window.addEventListener('scroll', schedulePosition, {passive:true});
  window.addEventListener('resize', schedulePosition);
  document.addEventListener('toggle', schedulePosition, true);

  function reveal() {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const target = document.getElementById(id);
    if (!target) return;
    if (id === 'contents') contents.open = true;
    let parent = target;
    while (parent) {
      if (parent.tagName === 'DETAILS') parent.open = true;
      parent = parent.parentElement;
    }
    requestAnimationFrame(() => { target.scrollIntoView({block:'start'}); updatePosition(); });
  }
  window.addEventListener('hashchange', reveal);

  const tocDialog = document.getElementById('reader-toc-dialog');
  const sourceDialog = document.getElementById('reader-source-dialog');
  const sourceContent = document.getElementById('reader-source-content');
  const allPassages = document.getElementById('reader-all-passages');
  let selectedVideo;
  if (typeof tocDialog.showModal === 'function') {
    document.body.classList.add('reader-enhanced');
    document.querySelectorAll('[data-open-contents], [data-source-ids]').forEach(link => {
      link.setAttribute('aria-haspopup', 'dialog');
      link.setAttribute('aria-controls', link.hasAttribute('data-open-contents') ? tocDialog.id : sourceDialog.id);
    });
  }

  function openDialog(dialog, trigger) {
    dialog.returnFocus = trigger;
    dialog.returnScroll = {left:window.scrollX, top:window.scrollY};
    dialog.showModal();
    document.documentElement.classList.add('reader-modal-open');
    dialog.scrollTop = 0;
  }
  [tocDialog, sourceDialog].forEach(dialog => {
    dialog.querySelector('[data-close-dialog]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => {
      document.documentElement.classList.remove('reader-modal-open');
      dialog.returnFocus?.focus({preventScroll:true});
      if (dialog.returnScroll) window.scrollTo({...dialog.returnScroll, behavior:'instant'});
      schedulePosition();
    });
    dialog.addEventListener('click', event => {
      if (event.target !== dialog) return;
      const bounds = dialog.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
    });
  });

  function showPassages(passages, fullVideo = false) {
    sourceContent.replaceChildren(...passages.map((passage, index) => {
      const copy = passage.cloneNode(true);
      copy.removeAttribute('id');
      copy.querySelectorAll('[id]').forEach(node => node.removeAttribute('id'));
      copy.open = !fullVideo || index === 0;
      return copy;
    }));
    document.getElementById('source-dialog-context').textContent =
      (fullVideo ? '本章全部引用' : '這段文字的來源') + ' · ' + selectedVideo.querySelector('.video-label').textContent;
    document.getElementById('source-dialog-title').textContent = selectedVideo.querySelector('.video-title').textContent;
    const total = selectedVideo.querySelectorAll('.reader-passage').length;
    allPassages.hidden = passages.length === total;
    allPassages.textContent = '查看這支影片在本章的全部 ' + total + ' 個時間點';
  }
  allPassages.addEventListener('click', () => {
    showPassages([...selectedVideo.querySelectorAll('.reader-passage')], true);
    sourceDialog.scrollTop = 0;
    sourceDialog.querySelector('[data-close-dialog]').focus({preventScroll:true});
  });

  document.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#"]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    if (link.dataset.sourceIds && typeof sourceDialog.showModal === 'function') {
      const video = document.getElementById(link.hash.slice(1));
      const passages = link.dataset.sourceIds.split(' ').map(id => document.getElementById(id));
      if (!video || passages.some(passage => !passage || !video.contains(passage))) return;
      event.preventDefault();
      selectedVideo = video;
      // Preserve chronological order while showing only this claim's evidence.
      showPassages([...video.querySelectorAll('.reader-passage')].filter(passage => passages.includes(passage)));
      openDialog(sourceDialog, link);
    } else if (link.hasAttribute('data-open-contents') && typeof tocDialog.showModal === 'function') {
      event.preventDefault();
      openDialog(tocDialog, link);
    } else {
      if (tocDialog.contains(link)) {
        tocDialog.returnScroll = null;
        tocDialog.returnFocus = document.getElementById(link.hash.slice(1));
        tocDialog.close();
      }
      if (link.hash === location.hash) reveal();
    }
  });
  reveal();
  updatePosition();
  window.dispatchEvent(new Event('aiok-content-ready'));
})();
