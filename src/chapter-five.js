(() => {
  'use strict';

  const cards = [...document.querySelectorAll('.system-card')];
  const responsibilityItems = [...document.querySelectorAll('[data-responsibility]')];
  const activeName = document.querySelector('#active-system-name');
  const activeNote = document.querySelector('#active-system-note');
  const chapterName = document.querySelector('.chapter-name');
  let current = '';
  let queued = false;

  function activate(card) {
    if (!card || card.dataset.system === current) return;
    current = card.dataset.system;
    const active = new Set((card.dataset.responsibilities || '').split(',').filter(Boolean));
    cards.forEach(item => item.classList.toggle('is-active', item === card));
    responsibilityItems.forEach(item => {
      const selected = active.has(item.dataset.responsibility);
      item.classList.toggle('is-active', selected);
      item.setAttribute('aria-current', selected ? 'true' : 'false');
    });
    if (activeName) activeName.textContent = card.dataset.label || 'Compare the work';
    if (activeNote) activeNote.textContent = card.dataset.note || '';
    if (chapterName) chapterName.textContent = 'REAL SYSTEMS';
  }

  function updateFromScroll() {
    queued = false;
    const target = innerHeight * .3;
    const candidates = cards
      .map(card => ({ card, rect: card.getBoundingClientRect() }))
      .filter(item => item.rect.bottom > innerHeight * .12 && item.rect.top < innerHeight * .72);
    if (!candidates.length) return;
    candidates.sort((a, b) => Math.abs(a.rect.top - target) - Math.abs(b.rect.top - target));
    activate(candidates[0].card);
  }

  function requestUpdate() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(updateFromScroll);
  }

  addEventListener('scroll', requestUpdate, { passive: true });
  addEventListener('resize', requestUpdate);
  addEventListener('hashchange', requestUpdate);
  requestUpdate();
})();
