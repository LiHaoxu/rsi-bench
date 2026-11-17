(() => {
  'use strict';
  const entries = [...document.querySelectorAll('[data-entry]')];
  const form = document.querySelector('[data-filters]');
  const fields = form ? [...form.querySelectorAll('input[name],select[name]')] : [];
  const count = document.querySelector('[data-count]');
  const empty = document.querySelector('[data-empty]');
  const toast = document.querySelector('[data-toast]');
  const searchText = new Map(entries.map(entry => [entry, entry.textContent.toLocaleLowerCase()]));
  let toastTimer;
  let typingTimer;
  let typingEntry = false;

  function announce(message) {
    if (!toast) return;
    clearTimeout(toastTimer);
    toast.textContent = message;
    toast.hidden = false;
    toastTimer = setTimeout(() => { toast.hidden = true; }, 4500);
  }

  function targetFromHash(hash = location.hash) {
    try { return document.getElementById(decodeURIComponent(hash.replace(/^#/, ''))); }
    catch (_) { return null; }
  }

  function updateURL(mode = 'push', clearEntryHash = false) {
    if (!form) return;
    const url = new URL(location.href);
    fields.forEach(field => field.value ? url.searchParams.set(field.name, field.value) : url.searchParams.delete(field.name));
    if (clearEntryHash && targetFromHash()?.hasAttribute('data-entry')) url.hash = '';
    if (url.href === location.href) return;
    try { history[mode === 'replace' ? 'replaceState' : 'pushState'](null, '', url); }
    catch (_) { /* Filtering still works when file:// history is restricted. */ }
  }

  function filterEntries() {
    const filters = Object.fromEntries(fields.map(field => [field.name, field.value]));
    const terms = (filters.q || '').trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    let visible = 0;
    entries.forEach(entry => {
      const match = terms.every(term => searchText.get(entry).includes(term)) &&
        fields.every(field => field.name === 'q' || !field.value || entry.dataset[field.name] === field.value);
      entry.hidden = !match;
      if (match) visible++;
    });
    if (count) count.textContent = `显示 ${visible} / ${entries.length} 条`;
    if (empty) empty.hidden = visible > 0;
  }

  function revealHash(scroll = true) {
    const target = targetFromHash();
    if (!target) return;
    if (target.hasAttribute('data-entry') && target.hidden) {
      fields.forEach(field => { field.value = ''; });
      filterEntries();
      updateURL('replace');
      announce('已清除筛选，显示链接指定的资源。');
    }
    if (scroll) requestAnimationFrame(() => target.scrollIntoView({block: 'start'}));
  }

  function restoreFromURL() {
    clearTimeout(typingTimer);
    typingTimer = undefined;
    typingEntry = false;
    const params = new URLSearchParams(location.search);
    fields.forEach(field => { field.value = params.get(field.name) || ''; });
    filterEntries();
    revealHash();
  }

  function commitTyping() {
    clearTimeout(typingTimer);
    typingTimer = undefined;
    updateURL(typingEntry ? 'replace' : 'push', true);
    typingEntry = true;
  }

  fields.forEach(field => {
    if (field.tagName === 'INPUT') {
      field.addEventListener('input', () => {
        filterEntries();
        clearTimeout(typingTimer);
        typingTimer = setTimeout(commitTyping, 250);
      });
      field.addEventListener('blur', () => {
        if (typingTimer) commitTyping();
        typingEntry = false;
      });
    } else {
      field.addEventListener('change', () => {
        clearTimeout(typingTimer);
        typingTimer = undefined;
        typingEntry = false;
        filterEntries();
        updateURL('push', true);
      });
    }
  });
  form?.addEventListener('submit', event => { event.preventDefault(); commitTyping(); });
  document.querySelector('[data-reset]')?.addEventListener('click', () => {
    clearTimeout(typingTimer);
    typingTimer = undefined;
    typingEntry = false;
    fields.forEach(field => { field.value = ''; });
    filterEntries();
    updateURL('push', true);
  });
  document.querySelector('[data-expand]')?.addEventListener('click', () => entries.filter(entry => !entry.hidden).forEach(entry => entry.querySelectorAll('details').forEach(details => { details.open = true; })));
  document.querySelector('[data-collapse]')?.addEventListener('click', () => entries.forEach(entry => entry.querySelectorAll('details').forEach(details => { details.open = false; })));

  document.querySelectorAll('a[href^="#"]').forEach(anchor => anchor.addEventListener('click', () => {
    const target = targetFromHash(anchor.getAttribute('href'));
    if (target?.hasAttribute('data-entry') && target.hidden) {
      fields.forEach(field => { field.value = ''; });
      filterEntries();
      updateURL('replace');
    }
    if (anchor.hash === location.hash) revealHash();
  }));
  window.addEventListener('popstate', restoreFromURL);
  window.addEventListener('hashchange', () => revealHash());

  document.querySelectorAll('[data-share]').forEach(button => button.addEventListener('click', async () => {
    const url = new URL(location.href);
    url.search = '';
    url.hash = button.dataset.share;
    const fallback = button.closest('[data-entry]')?.querySelector('[data-share-fallback]');
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(url.href);
      if (fallback) fallback.hidden = true;
      announce(location.protocol === 'file:' ? '已复制本地资源链接；在线分享请使用发布后的页面。' : '已复制资源链接。');
    } catch (_) {
      if (!fallback) return;
      fallback.hidden = false;
      const input = fallback.querySelector('input');
      input.value = url.href;
      input.focus();
      input.select();
      announce('请复制已选中的资源链接。');
    }
  }));

  restoreFromURL();
})();
