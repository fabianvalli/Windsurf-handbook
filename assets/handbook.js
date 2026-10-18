/* Native details work without JS. Enhance direct links and mobile navigation. */
(() => {
  'use strict';
  document.body.classList.add('csc-handbook-page');
  const mobile = window.matchMedia('(max-width: 991px)');
  const phone = window.matchMedia('(max-width: 600px)');
  const app = document.querySelector('.hb-app');
  if (!app) return;
  let restoringImagePosition = false;
  const menu = app.querySelector('.hb-contents');
  const siteMenu = document.querySelector('.hb-site-menu');
  const sections = [...app.querySelectorAll('details[data-topic]')];
  const setMenus = () => {
    if (menu) menu.open = !mobile.matches;
    if (siteMenu) siteMenu.open = !phone.matches;
  };
  setMenus();
  mobile.addEventListener('change', setMenus);
  phone.addEventListener('change', setMenus);
  const findSection = hash => {
    try {
      const target = document.getElementById(decodeURIComponent(hash.replace(/^#/, '')));
      return target?.matches('details[data-topic]') ? target : target?.closest('details[data-topic]');
    } catch { return null; }
  };
  const openHash = () => {
    if (restoringImagePosition) return;
    const section = findSection(window.location.hash);
    if (!section) return;
    section.open = true;
    if (mobile.matches && menu) menu.open = false;
    requestAnimationFrame(() => section.scrollIntoView({block: 'start'}));
  };
  window.addEventListener('hashchange', openHash);
  if (window.location.hash) openHash();
  app.querySelectorAll('a[href]').forEach(link => {
    link.addEventListener('click', () => {
      const url = new URL(link.href, window.location.href);
      if (url.origin === window.location.origin && url.pathname === window.location.pathname && url.hash) {
        const section = findSection(url.hash);
        if (section) section.open = true;
      }
      if (mobile.matches && menu && menu.contains(link)) menu.open = false;
    });
  });
  app.querySelectorAll('[data-expand]').forEach(button => {
    button.addEventListener('click', () => {
      sections.forEach(section => { section.open = button.dataset.expand === 'true'; });
    });
  });

  // Keep image close-ups in the current document. A same-URL history entry
  // lets browser Back close the viewer without retriggering section anchors.
  const imageLinks = [...app.querySelectorAll('a[href]')].filter(link =>
    /\.(png|jpe?g|webp|gif)$/i.test(new URL(link.href).pathname));
  let dismissImage = () => {};
  if (imageLinks.length && typeof HTMLDialogElement !== 'undefined') {
    const viewer = document.createElement('dialog');
    viewer.className = 'hb-image-viewer';
    viewer.id = 'hb-image-viewer';
    viewer.setAttribute('aria-label', 'Image close-up');
    viewer.innerHTML = '<div class="hb-image-toolbar"><button type="button" class="btn btn-default" data-image-zoom aria-pressed="false">Enlarge</button><button type="button" class="btn btn-primary" data-image-close>Close image</button></div><div class="hb-image-stage"><img alt=""></div><p class="hb-image-caption"></p>';
    app.append(viewer);
    const picture = viewer.querySelector('img');
    const caption = viewer.querySelector('.hb-image-caption');
    const stage = viewer.querySelector('.hb-image-stage');
    const closeButton = viewer.querySelector('[data-image-close]');
    const zoomButton = viewer.querySelector('[data-image-zoom]');
    const historyKey = 'hbImageViewer';
    const owner = String(Date.now());
    let sourceLink;
    let readingPosition;
    let ownsEntry = false;
    let restoreAfterBack = false;
    const resetZoom = () => {
      viewer.classList.remove('hb-image-enlarged');
      zoomButton.textContent = 'Enlarge';
      zoomButton.setAttribute('aria-pressed', 'false');
      stage.scrollTo(0, 0);
    };
    const hide = () => {
      if (!viewer.open) return;
      viewer.close();
      sourceLink?.focus({preventScroll: true});
      if (readingPosition) window.scrollTo(readingPosition.x, readingPosition.y);
    };
    const restoreReadingPosition = () => {
      // History can apply its own stored scroll after popstate has fired.
      // Restore the actual reading position in the following rendering frame.
      restoringImagePosition = true;
      requestAnimationFrame(() => {
        if (readingPosition) window.scrollTo(readingPosition.x, readingPosition.y);
        restoringImagePosition = false;
      });
    };
    const show = data => {
      picture.src = data.src;
      picture.alt = data.alt;
      caption.textContent = data.caption;
      resetZoom();
      if (!viewer.open) viewer.showModal();
      closeButton.focus({preventScroll: true});
    };
    dismissImage = () => {
      hide();
      if (ownsEntry && history.state?.[historyKey]?.owner === owner) {
        restoreAfterBack = true;
        ownsEntry = false;
        history.back();
      }
    };
    imageLinks.forEach(link => {
      link.setAttribute('aria-haspopup', 'dialog');
      link.setAttribute('aria-controls', viewer.id);
      link.addEventListener('click', event => {
        if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        sourceLink = link;
        readingPosition = {x: window.scrollX, y: window.scrollY};
        const figure = link.closest('figure');
        const original = link.querySelector('img') || figure?.querySelector('img');
        const data = {owner, src: link.href, alt: original?.alt || 'Handbook illustration', caption: figure?.querySelector('figcaption')?.textContent.trim() || original?.alt || ''};
        try {
          history.pushState({...history.state, [historyKey]: data}, '');
          ownsEntry = true;
        } catch { ownsEntry = false; }
        show(data);
      });
    });
    window.addEventListener('popstate', () => {
      const leavingImage = viewer.open || restoreAfterBack;
      const data = history.state?.[historyKey];
      ownsEntry = data?.owner === owner;
      if (ownsEntry) show(data);
      else {
        hide();
        if (leavingImage) restoreReadingPosition();
      }
      restoreAfterBack = false;
    });
    closeButton.addEventListener('click', dismissImage);
    viewer.addEventListener('cancel', event => { event.preventDefault(); dismissImage(); });
    viewer.addEventListener('click', event => {
      if (event.target !== viewer) return;
      const bounds = viewer.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dismissImage();
    });
    zoomButton.addEventListener('click', () => {
      const enlarged = viewer.classList.toggle('hb-image-enlarged');
      zoomButton.setAttribute('aria-pressed', String(enlarged));
      zoomButton.textContent = enlarged ? 'Fit to screen' : 'Enlarge';
      stage.scrollTo(0, 0);
    });
  }

  // The examples remain ordinary figures without JavaScript. Enhance the chart
  // with mouse previews and a dismissible, non-modal panel for touch/keyboard.
  const closeRuleExamples = [];
  app.querySelectorAll('[data-rule-diagram]').forEach(diagram => {
    const controls = diagram.querySelector('.hb-flowchart-controls');
    const buttons = [...controls.querySelectorAll('[data-rule-example]')];
    const popup = document.getElementById(buttons[0].getAttribute('aria-controls'));
    const visuals = [...popup.querySelectorAll('[data-rule-visual]')];
    const closeButton = popup.querySelector('[data-rule-close]');
    const section = diagram.closest('details[data-topic]');
    let active = null;
    let pinned = false;
    let hideTimer;
    let restoringFocus = false;
    let dismissedFocus = null;
    let hoverSuppressedUntil = 0;
    let pointerSide = null;
    const cancelHide = () => clearTimeout(hideTimer);
    const position = () => {
      if (popup.hidden || !active) return;
      const bounds = active.getBoundingClientRect();
      const width = document.documentElement.clientWidth;
      const height = window.innerHeight;
      const gutter = 12;
      const panel = popup.getBoundingClientRect();
      const left = (pointerSide ?? bounds.left + bounds.width / 2) < width / 2
        ? width - panel.width - gutter : gutter;
      const top = Math.max(gutter, Math.min(bounds.top, height - panel.height - gutter));
      popup.style.left = Math.max(gutter, left) + 'px';
      popup.style.top = top + 'px';
    };
    const close = (restoreFocus = false) => {
      cancelHide();
      const previous = active;
      dismissedFocus = restoreFocus || previous === document.activeElement ? previous : null;
      // Hiding a panel can expose a hotspot beneath the close button and fire
      // pointerenter without a mouse movement. Ignore that immediate re-entry.
      if (previous) hoverSuppressedUntil = performance.now() + 250;
      popup.hidden = true;
      buttons.forEach(button => button.setAttribute('aria-expanded', 'false'));
      active = null;
      pinned = false;
      if (restoreFocus && previous) {
        restoringFocus = true;
        previous.focus({preventScroll: true});
        restoringFocus = false;
      }
    };
    const show = (button, pin = false) => {
      cancelHide();
      active = button;
      pinned = pin;
      visuals.forEach(visual => {
        visual.hidden = visual.dataset.ruleVisual !== button.dataset.ruleExample;
        if (!visual.hidden) popup.setAttribute('aria-labelledby', visual.querySelector('h3').id);
      });
      buttons.forEach(item => item.setAttribute('aria-expanded', String(item === button)));
      popup.hidden = false;
      position();
    };
    const scheduleHide = () => {
      cancelHide();
      if (pinned) return;
      hideTimer = setTimeout(() => {
        const focused = document.activeElement;
        if (!popup.matches(':hover') && !controls.matches(':hover') &&
            !popup.contains(focused) && !controls.contains(focused)) close();
      }, 180);
    };
    popup.classList.add('hb-rule-popover');
    popup.setAttribute('role', 'dialog');
    popup.setAttribute('aria-modal', 'false');
    popup.hidden = true;
    popup.querySelector('.hb-rule-example-controls').hidden = false;
    controls.hidden = false;
    diagram.closest('figure').querySelector('.hb-rule-hint').hidden = false;
    buttons.forEach(button => {
      button.addEventListener('pointerenter', event => {
        if (event.pointerType !== 'mouse' || performance.now() < hoverSuppressedUntil) return;
        pointerSide = event.clientX;
        show(button, pinned && active === button);
      });
      button.addEventListener('pointerleave', () => {
        scheduleHide();
      });
      button.addEventListener('focus', () => {
        if (restoringFocus || dismissedFocus === button) return;
        pointerSide = null;
        show(button, pinned && active === button);
      });
      button.addEventListener('click', () => {
        dismissedFocus = null;
        hoverSuppressedUntil = 0;
        if (active === button && pinned) close();
        else show(button, true);
      });
      button.addEventListener('blur', () => {
        if (dismissedFocus === button) dismissedFocus = null;
      });
    });
    controls.addEventListener('focusout', scheduleHide);
    popup.addEventListener('pointerenter', cancelHide);
    popup.addEventListener('pointerleave', scheduleHide);
    popup.addEventListener('focusout', scheduleHide);
    popup.addEventListener('load', position, true);
    closeButton.addEventListener('click', () => close(true));
    document.addEventListener('pointerdown', event => {
      if (!controls.contains(event.target) && !popup.contains(event.target)) close();
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !popup.hidden && !app.querySelector('.hb-image-viewer[open]')) {
        event.preventDefault();
        close(popup.contains(document.activeElement));
      }
    });
    section.addEventListener('toggle', () => { if (!section.open) close(); });
    // Focus can scroll a hotspot into view. Keep that keyboard preview open;
    // dismiss when the reader scrolls with a wheel or a touch gesture instead.
    window.addEventListener('scroll', () => {
      if (!active) return;
      const bounds = active.getBoundingClientRect();
      if (bounds.bottom <= 0 || bounds.top >= window.innerHeight) close();
      else position();
    }, {passive: true});
    const dismissOnScrollGesture = event => {
      if (!popup.contains(event.target)) close();
    };
    window.addEventListener('wheel', dismissOnScrollGesture, {passive: true});
    window.addEventListener('touchmove', dismissOnScrollGesture, {passive: true});
    window.addEventListener('resize', position);
    closeRuleExamples.push(close);
  });

  // Native sticky positioning carries the summary out with its section.
  // Keep it compact after passing the start, even when the section is offscreen.
  // Restoring its height at the bottom can trigger scroll anchoring and a loop.
  // A summary margin preserves the body's position while the summary shrinks.
  const headers = sections.map(section => ({
    section,
    summary: section.querySelector(':scope > summary'),
    compact: false,
  }));
  const menuSummary = menu?.querySelector(':scope > summary');
  let headerFrame = 0;
  let headerMetricsDirty = false;
  let printing = false;
  const resetHeaders = () => {
    headers.forEach(header => {
      header.section.classList.remove('hb-header-stuck');
      header.section.style.removeProperty('--hb-header-gap');
      header.compact = false;
    });
  };
  const updateHeaders = () => {
    headerFrame = 0;
    if (printing) return;
    if (headerMetricsDirty) {
      resetHeaders();
      headerMetricsDirty = false;
    }
    const top = mobile.matches && menuSummary
      ? menuSummary.getBoundingClientRect().height + (parseFloat(getComputedStyle(menu).borderBottomWidth) || 0)
      : 0;
    app.style.setProperty('--hb-section-top', top + 'px');
    headers.forEach(header => {
      const bounds = header.section.getBoundingClientRect();
      const compact = header.section.open && bounds.top < top - 1;
      if (compact === header.compact) return;
      if (compact) {
        const fullHeight = header.summary.getBoundingClientRect().height;
        header.section.classList.add('hb-header-stuck');
        const compactHeight = header.summary.getBoundingClientRect().height;
        header.section.style.setProperty('--hb-header-gap', Math.max(0, fullHeight - compactHeight) + 'px');
      } else {
        header.section.classList.remove('hb-header-stuck');
        header.section.style.removeProperty('--hb-header-gap');
      }
      header.compact = compact;
    });
  };
  const scheduleHeaders = (reset = false) => {
    headerMetricsDirty ||= reset;
    if (!headerFrame) headerFrame = requestAnimationFrame(updateHeaders);
  };
  window.addEventListener('scroll', () => scheduleHeaders(), {passive: true});
  window.addEventListener('resize', () => scheduleHeaders(true));
  sections.forEach(section => section.addEventListener('toggle', () => scheduleHeaders()));
  menu?.addEventListener('toggle', () => scheduleHeaders());
  app.addEventListener('load', () => scheduleHeaders(), true);
  if ('ResizeObserver' in window) {
    const headerResize = new ResizeObserver(() => scheduleHeaders());
    headerResize.observe(app);
    if (menuSummary) headerResize.observe(menuSummary);
  }
  document.fonts?.ready.then(() => scheduleHeaders(true));
  scheduleHeaders();

  let printState;
  window.addEventListener('beforeprint', () => {
    dismissImage();
    closeRuleExamples.forEach(close => close());
    printing = true;
    resetHeaders();
    printState = sections.map(section => section.open);
    sections.forEach(section => { section.open = true; });
  });
  window.addEventListener('afterprint', () => {
    printing = false;
    if (printState) sections.forEach((section, index) => { section.open = printState[index]; });
    scheduleHeaders(true);
  });
})();
