(() => {
  'use strict';
  const oldStoryHashes = new Set(['meet','company','chapter-two','chapter-three','chapter-four','chapter-five','systems','hindsight','mem0','openviking','supermemory','graphrag','failure-cases','cost','selection','final-close']);
  const table = document.querySelector('#memory-comparison-table');
  const head = table.tHead;
  const normal = document.querySelector('#comparison-rows');
  const pinned = document.querySelector('#pinned-rows');
  // Immutable catalogue order; the actual rows (and controls) are never cloned.
  const rows = [...normal.rows];
  const checkboxes = rows.map(row => row.querySelector('.pin-checkbox'));
  const input = document.querySelector('#search');
  const status = document.querySelector('#filter-status');
  const pinStatus = document.querySelector('#pin-status');
  const clear = document.querySelector('#clear-selection');
  let kind = 'all';
  const panel = document.querySelector('#shared-radar-panel');
  const disclosure = document.querySelector('#shared-radar-disclosure');
  const workspace = document.querySelector('.comparison-workspace');
  const series = [...panel.querySelectorAll('[data-series]')];
  const mobile = matchMedia('(max-width:1200px)');
  const selectedSeries = () => series.filter(s => !s.hasAttribute('hidden'));
  function highlight(id) {
    series.forEach(s => {
      s.classList.toggle('is-muted', !!id && s.dataset.series !== id);
      s.classList.toggle('is-highlighted', s.dataset.series === id);
    });
    panel.querySelectorAll('[data-highlight]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.highlight === id)));
    document.querySelector('#series-highlight').textContent = id ? 'Highlight: ' + series.find(s => s.dataset.series === id).dataset.name : 'All selected profiles';
  }
  panel.addEventListener('focusin', event => { if (event.target.dataset.highlight) highlight(event.target.dataset.highlight); });
  panel.addEventListener('pointerover', event => { const b = event.target.closest('[data-highlight]'); if (b) highlight(b.dataset.highlight); });
  panel.addEventListener('click', event => {
    const b = event.target.closest('[data-highlight]');
    if (b) highlight(b.dataset.highlight);
    if (event.target.closest('#reset-series')) highlight(null);
    const remove = event.target.closest('[data-remove]');
    if (remove) {
      const checkbox = document.getElementById('pin-' + remove.dataset.remove);
      checkbox.checked = false;
      checkbox.dispatchEvent(new Event('change'));
      disclosure.querySelector('summary').focus({preventScroll: true});
    }
  });
  panel.addEventListener('focusout', event => { if (event.target.dataset.highlight) highlight(null); });
  panel.addEventListener('pointerleave', () => { if (!panel.querySelector('[data-highlight]:focus')) highlight(null); });

  const tooltip = document.createElement('div');
  tooltip.id = 'radar-tooltip';
  tooltip.setAttribute('role', 'tooltip');
  tooltip.setAttribute('popover', 'manual');
  tooltip.hidden = true;
  document.body.append(tooltip);
  let trigger = null;
  let closeTimer;
  function dismiss() {
    clearTimeout(closeTimer);
    if (trigger) trigger.removeAttribute('aria-describedby');
    trigger = null;
    if (tooltip.matches(':popover-open')) tooltip.hidePopover();
    tooltip.hidden = true;
  }
  function positionTooltip() {
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    const bodyRect = panel.querySelector('.shared-radar-body').getBoundingClientRect();
    const bottom = Math.min(innerHeight, bodyRect.bottom);
    const top = Math.max(0, bodyRect.top);
    if (!trigger.isConnected || !trigger.getClientRects().length || rect.bottom <= top || rect.top >= bottom || rect.right <= 0 || rect.left >= innerWidth) {
      dismiss(); return;
    }
    const above = rect.top - 20, below = innerHeight - rect.bottom - 20;
    const useBelow = below >= above;
    const panelRect = panel.getBoundingClientRect();
    if (!mobile.matches && panelRect.left >= 330) {
      // Keep the overlaid profiles visible while their values are inspected.
      tooltip.style.maxHeight = Math.min(innerHeight * .6, innerHeight - 20) + 'px';
      const box = tooltip.getBoundingClientRect();
      tooltip.style.left = (panelRect.left - box.width - 12) + 'px';
      tooltip.style.top = Math.max(10, Math.min(innerHeight - box.height - 10, rect.top + rect.height / 2 - box.height / 2)) + 'px';
      return;
    }
    tooltip.style.maxHeight = Math.max(70, Math.min(innerHeight * .6, useBelow ? below : above)) + 'px';
    const box = tooltip.getBoundingClientRect();
    tooltip.style.left = Math.max(10, Math.min(innerWidth - box.width - 10, rect.left + rect.width / 2 - box.width / 2)) + 'px';
    const y = useBelow ? rect.bottom + 10 : rect.top - box.height - 10;
    tooltip.style.top = Math.max(10, Math.min(innerHeight - box.height - 10, y)) + 'px';
  }
  function show(target) {
    dismiss();
    trigger = target;
    const title = document.createElement('strong');
    title.textContent = target.getAttribute('aria-label');
    const description = document.createElement('span');
    description.textContent = target.dataset.description;
    const list = document.createElement('ul');
    for (const item of selectedSeries()) {
      const value = JSON.parse(item.dataset.values)[target.dataset.axis];
      const entry = document.createElement('li');
      entry.dataset.score = value === null ? 'unknown' : value;
      entry.dataset.series = item.dataset.series;
      const name = document.createElement('span'); name.textContent = item.dataset.name;
      const score = document.createElement('b'); score.textContent = value === null ? 'Unknown' : value + '/3';
      entry.append(name, score); list.append(entry);
    }
    if (!list.children.length) list.textContent = 'Select approaches to inspect their scores.';
    tooltip.replaceChildren(title, description, list);
    target.setAttribute('aria-describedby', tooltip.id);
    tooltip.hidden = false;
    if (tooltip.showPopover) tooltip.showPopover();
    positionTooltip();
  }
  const axisSelector = '.axis-button, .radar-axis-target';
  panel.addEventListener('pointerover', event => {
    const target = event.target.closest(axisSelector);
    if (target && event.pointerType !== 'touch' &&
        (!document.activeElement.matches(axisSelector) || document.activeElement === target)) show(target);
  });
  panel.addEventListener('focusin', event => {
    if (event.target.matches(axisSelector)) show(event.target);
  });
  panel.addEventListener('focusout', event => {
    if (event.target === trigger) dismiss();
  });
  panel.addEventListener('pointerout', event => {
    if (trigger && event.target.closest(axisSelector) === trigger && document.activeElement !== trigger) {
      closeTimer = setTimeout(() => {
        if (trigger && !trigger.matches(':hover') && !tooltip.matches(':hover') && document.activeElement !== trigger) dismiss();
      }, 160);
    }
  });
  tooltip.addEventListener('pointerenter', () => clearTimeout(closeTimer));
  tooltip.addEventListener('pointerleave', () => { if (document.activeElement !== trigger) dismiss(); });
  panel.addEventListener('click', event => {
    const target = event.target.closest(axisSelector);
    if (target) show(target);
  });
  panel.addEventListener('keydown', event => {
    if (event.target === trigger && ['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
      event.preventDefault();
      if (event.key === 'Home') tooltip.scrollTop = 0;
      else if (event.key === 'End') tooltip.scrollTop = tooltip.scrollHeight;
      else tooltip.scrollTop += event.key === 'ArrowDown' ? 48 : -48;
    }
    if (event.target.matches('.radar-axis-target') && ['Enter', ' '].includes(event.key)) {
      event.preventDefault(); show(event.target);
    }
  });
  document.addEventListener('keydown', event => { if (event.key === 'Escape') dismiss(); });
  document.addEventListener('pointerdown', event => {
    if (!event.target.closest(axisSelector) && !tooltip.contains(event.target)) dismiss();
  });
  // Capture nested scrolling too; tooltip lives in the top layer, not a clipping rowgroup.
  addEventListener('scroll', positionTooltip, {capture: true, passive: true});
  disclosure.addEventListener('toggle', () => {
    dismiss(); workspace.classList.toggle('radar-expanded', disclosure.open && mobile.matches); measure();
  });
  function adaptPanel() { disclosure.open = !mobile.matches; dismiss(); }
  mobile.addEventListener('change', adaptPanel);
  new IntersectionObserver(entries => {
    panel.classList.toggle('in-table', entries[0].isIntersecting);
    if (!entries[0].isIntersecting) dismiss();
  }).observe(table);
  panel.hidden = false; adaptPanel();

  function measure() {
    table.style.setProperty('--header-height', head.getBoundingClientRect().height + 'px');
    table.style.setProperty('--scroll-gutter', (pinned.hidden ? 0 : pinned.offsetWidth - pinned.clientWidth) + 'px');
    positionTooltip();
  }
  new ResizeObserver(measure).observe(head);
  new ResizeObserver(measure).observe(pinned);
  addEventListener('resize', measure);

  function filter() {
    dismiss();
    let matches = 0, selected = 0, retained = 0;
    rows.forEach((row, index) => {
      const match = (kind === 'all' || row.dataset.kind === kind) && row.dataset.search.includes(input.value.trim().toLowerCase());
      const pin = checkboxes[index].checked;
      if (match) matches++;
      if (pin) selected++;
      if (pin && !match) retained++;
      row.hidden = !match && !pin;
      panel.querySelector('[data-series="' + row.dataset.approach + '"]').toggleAttribute('hidden', !pin);
      panel.querySelector('[data-legend="' + row.dataset.approach + '"]').hidden = !pin;
    });
    highlight(null);
    document.querySelector('#series-count').textContent = selected + ' selected';
    document.querySelector('#radar-empty').hidden = selected > 0;
    pinned.hidden = selected === 0;
    pinned.tabIndex = selected ? 0 : -1;
    clear.disabled = selected === 0;
    pinStatus.textContent = selected + ' selected' + (selected ? ' · scroll pinned rows' : ' · select rows to compare');
    status.textContent = matches + ' of ' + rows.length + ' approaches match' + (selected ? ' · ' + selected + ' selected (' + retained + ' outside filter, kept visible)' : '') + (matches ? '' : ' — try another name or clear the search.');
    measure();
  }
  function moveRows(active) {
    dismiss();
    // Reinsert only when parent/order differs. Preserve focus and independent scroll.
    for (const body of [pinned, normal]) {
      const expected = rows.filter((row, index) => checkboxes[index].checked === (body === pinned));
      expected.forEach((row, index) => {
        if (body.children[index] !== row) body.insertBefore(row, body.children[index] || null);
      });
    }
    filter();
    if (active && !active.closest('tr').hidden) {
      active.focus({preventScroll: true});
      if (pinned.contains(active)) {
        const row = active.closest('tr');
        pinned.scrollTop = row.offsetTop - pinned.offsetTop;
      }
    } else if (active) {
      (clear.disabled ? table.querySelector('.leave-comparison') : clear).focus({preventScroll: true});
    }
  }
  checkboxes.forEach(checkbox => {
    checkbox.disabled = false;
    const name = checkbox.getAttribute('aria-label').replace(/^Pin /, '').replace(/ for comparison$/, '');
    checkbox.addEventListener('change', () => {
      checkbox.setAttribute('aria-label', (checkbox.checked ? 'Unpin ' : 'Pin ') + name + ' for comparison');
      checkbox.nextElementSibling.textContent = checkbox.checked ? 'Unpin' : 'Pin';
      moveRows(checkbox);
    });
  });
  clear.addEventListener('click', () => {
    checkboxes.forEach(checkbox => {
      checkbox.checked = false;
      checkbox.setAttribute('aria-label', checkbox.getAttribute('aria-label').replace(/^Unpin /, 'Pin '));
      checkbox.nextElementSibling.textContent = 'Pin';
    });
    moveRows();
  });
  document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
    kind = button.dataset.filter;
    document.querySelectorAll('[data-filter]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    filter();
  }));
  input.addEventListener('input', filter);
  for (const selector of ['.controls', '#filter-status', '#pin-help', '.selection-toolbar']) document.querySelector(selector).hidden = false;
  function openTarget() {
    const id = location.hash.slice(1);
    if (oldStoryHashes.has(id)) { location.replace('story.html'+location.hash); return; }
    const target = document.getElementById(id);
    if (target?.tagName === 'DETAILS') {
      target.open = true;
      requestAnimationFrame(() => target.scrollIntoView({block: 'start'}));
    }
  }
  addEventListener('hashchange', openTarget);
  openTarget(); filter();
})();
