(() => {
  'use strict';
  const bar = document.getElementById('story-timeline');
  const map = document.getElementById('story-map');
  const opener = document.getElementById('timeline-overview');
  const links = [...map.querySelectorAll('.timeline-step-link')];
  const allLinks = [...document.querySelectorAll('[data-timeline-step]')];
  const chapters = [...bar.querySelectorAll('.timeline-chapter')];
  const cards = [...document.querySelectorAll('.system-card')];
  const label = document.getElementById('timeline-current');
  const dialog = document.createElement('dialog');
  dialog.id = 'story-timeline-dialog';
  dialog.setAttribute('aria-labelledby', 'story-map-title');
  map.before(dialog);
  dialog.append(map);
  const close = map.querySelector('.timeline-close');
  close.hidden = false;
  opener.setAttribute('aria-haspopup', 'dialog');
  opener.setAttribute('aria-controls', dialog.id);
  opener.setAttribute('aria-expanded', 'false');
  let jumpTarget = null;
  let active = null;
  let queued = false;

  opener.addEventListener('click', event => {
    if (event.button || event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return;
    event.preventDefault();
    jumpTarget = null;
    dialog.showModal();
    opener.setAttribute('aria-expanded', 'true');
    close.focus({preventScroll:true});
  });
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    opener.setAttribute('aria-expanded', 'false');
    (jumpTarget || opener).focus({preventScroll:true});
    jumpTarget = null;
  });

  function navigate(event) {
    const link = event.target.closest('[data-timeline-step], [data-timeline-start]');
    if (!link || event.button || event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return;
    const target = document.getElementById(link.hash.slice(1));
    if (!target) return;
    event.preventDefault();
    const focusTarget = link.hasAttribute('data-timeline-start') ? document.getElementById('opening-title') : target;
    focusTarget.setAttribute('tabindex', '-1');
    if (dialog.open) { jumpTarget = focusTarget; dialog.close(); }
    if (location.hash !== link.hash) history.pushState(null, '', link.hash);
    target.scrollIntoView({block:'start',behavior:'instant'});
    focusTarget.focus({preventScroll:true});
    requestUpdate();
  }
  bar.addEventListener('click', navigate);
  map.addEventListener('click', navigate);

  function update() {
    queued = false;
    let index = Number.parseInt(document.body.dataset.beat, 10);
    if (!Number.isFinite(index)) index = document.getElementById('story').getBoundingClientRect().bottom < 0 ? 26 : -1;
    if (document.getElementById('chapter-five').getBoundingClientRect().top < innerHeight * .65) {
      const system = cards.findIndex(card => card.classList.contains('is-active'));
      index = 27 + Math.max(0, system);
    }
    if (index === active) return;
    active = index;
    bar.dataset.activeStep = String(index);
    label.querySelector('strong').textContent = index < 0 ? 'INTRO' : `${index+1} / ${links.length}`;
    const title = index < 0 ? 'Meet Morrow Works' : links[index].lastElementChild.textContent;
    label.querySelector('span').textContent = title;
    label.title = title;
    allLinks.forEach(link => {
      const selected = Number(link.dataset.timelineStep) === index;
      if (selected) link.setAttribute('aria-current', 'step');
      else link.removeAttribute('aria-current');
      link.classList.toggle('is-before', Number(link.dataset.timelineStep) < index);
    });
    chapters.forEach(chapter => {
      const first = Number(chapter.dataset.first), end = Number(chapter.dataset.end);
      const selected = index >= first && index < end;
      chapter.classList.toggle('is-current', selected);
      const chapterLink = chapter.querySelector('.timeline-chapter-link');
      if (selected) chapterLink.setAttribute('aria-current', 'location');
      else chapterLink.removeAttribute('aria-current');
      chapter.style.setProperty('--chapter-progress', `${Math.max(0,Math.min(1,(index-first+1)/(end-first)))*100}%`);
    });
  }
  function requestUpdate() {
    if (!queued) { queued = true; requestAnimationFrame(update); }
  }
  const observer = new MutationObserver(requestUpdate);
  observer.observe(document.body, {attributes:true,attributeFilter:['data-beat']});
  cards.forEach(card => observer.observe(card, {attributes:true,attributeFilter:['class']}));
  addEventListener('scroll',requestUpdate,{passive:true});
  addEventListener('resize',requestUpdate);
  addEventListener('hashchange',requestUpdate);
  addEventListener('popstate',requestUpdate);
  requestUpdate();
  if (location.hash === '#story-map') opener.click();
})();
