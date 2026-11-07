/* The staging build alone loads this review layer. */
(() => {
  'use strict';

  const app = document.querySelector('.hb-app');
  const page = document.querySelector('meta[name="handbook-review-page"]')?.content;
  const tools = app?.querySelector('.hb-section-tools');
  const sidebar = app?.querySelector('.hb-sidebar');
  if (!tools || !sidebar || !['index', 'sailing-skills', 'equipment-reference'].includes(page) ||
      typeof HTMLDialogElement === 'undefined') return;

  const desktop = matchMedia('(min-width: 992px)');
  const shortcuts = sidebar.querySelector('.hb-contents');
  const identityKey = 'csc-handbook-review-name';
  const endpoint = `api/comments?page=${encodeURIComponent(page)}`;
  const MAX_IMAGES = 3;
  const MAX_BYTES = 5 * 1024 * 1024;
  const types = new Map([
    ['png', 'image/png'], ['jpg', 'image/jpeg'], ['jpeg', 'image/jpeg'],
    ['gif', 'image/gif'], ['webp', 'image/webp'],
  ]);
  const allowedTypes = new Set(types.values());
  const locations = new Map([['page', { title: 'This chapter' }]]);
  for (const section of app.querySelectorAll('.hb-section[data-topic][id]')) {
    const title = section.querySelector('.hb-section-label strong')?.textContent.trim();
    const body = section.querySelector('.hb-section-body');
    if (title && body) locations.set(section.id, { title, section, body });
  }

  function element(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  }

  function button(text, classes = 'btn btn-default', action) {
    const el = element('button', classes, text);
    el.type = 'button';
    if (action) el.addEventListener('click', action);
    return el;
  }

  function field(tag, id, labelText) {
    const row = element('div', 'hbr-field');
    const label = element('label', '', labelText);
    const input = element(tag, 'form-control');
    label.htmlFor = input.id = id;
    row.append(label, input);
    return { row, input };
  }

  function readName() {
    try { return (localStorage.getItem(identityKey) || '').trim().slice(0, 80); }
    catch { return ''; }
  }

  let reviewer = readName();
  let records = [];
  let loaded = false;
  let loading = false;
  let posting = false;
  let recordVersion = 0;
  let opener;
  let selectedId;
  let target;
  const drafts = new Map();

  const launch = button('Review comments', 'btn btn-primary hbr-launch', () => showPanel(launch));
  launch.setAttribute('aria-haspopup', 'dialog');
  launch.setAttribute('aria-controls', 'hbr-panel');
  launch.setAttribute('aria-expanded', 'false');
  (tools.querySelector('.hb-controls') || tools).append(launch);

  const panel = element('dialog', 'hbr-panel');
  panel.id = 'hbr-panel';
  panel.setAttribute('aria-labelledby', 'hbr-title');
  const header = element('header', 'hbr-header');
  const title = element('h2', '', 'Review comments');
  title.id = 'hbr-title';
  title.tabIndex = -1;
  const close = button('Close', 'btn btn-default', () => hidePanel());
  close.setAttribute('aria-label', 'Close review comments');
  header.append(title, close);

  const scroller = element('div', 'hbr-panel-body');
  const actions = element('div', 'hbr-actions');
  const add = button('Add comment', 'btn btn-primary', () => compose('page', null));
  const reload = button('Refresh', 'btn btn-default', () => refresh());
  reload.setAttribute('aria-label', 'Refresh comments');
  actions.append(add, reload);
  const identity = element('div', 'hbr-identity');
  const identityText = element('span');
  const changeName = button('Change name', 'btn btn-default', () => {
    nameEditor.hidden = false;
    editName.input.value = reviewer;
    editName.input.setCustomValidity('');
    editName.input.focus();
  });
  identity.append(identityText, changeName);

  const nameEditor = element('form', 'hbr-name-editor');
  nameEditor.hidden = true;
  const editName = field('input', 'hbr-edit-name', 'Your name');
  editName.input.type = 'text';
  editName.input.maxLength = 80;
  editName.input.required = true;
  editName.input.autocomplete = 'name';
  editName.input.addEventListener('input', () => editName.input.setCustomValidity(''));
  const nameActions = element('div', 'hbr-actions');
  const saveName = button('Save name', 'btn btn-primary');
  saveName.type = 'submit';
  const cancelName = button('Cancel', 'btn btn-default', () => {
    nameEditor.hidden = true;
    changeName.focus();
  });
  nameActions.append(saveName, cancelName);
  nameEditor.append(editName.row, nameActions);
  nameEditor.addEventListener('submit', event => {
    event.preventDefault();
    const name = editName.input.value.trim();
    if (!name) {
      editName.input.setCustomValidity('Enter your name.');
      editName.input.reportValidity();
      return;
    }
    setName(name);
    nameEditor.hidden = true;
    changeName.focus();
  });

  const composer = element('form', 'hbr-composer');
  composer.hidden = true;
  const composeTitle = element('h3', '', 'New comment');
  const inputs = element('fieldset', 'hbr-inputs');
  const locationField = field('select', 'hbr-target', 'Comment on');
  for (const [id, location] of locations) {
    const option = element('option', '', location.title);
    option.value = id;
    locationField.input.append(option);
  }
  locationField.input.addEventListener('change', () => compose(locationField.input.value, null, false));
  const firstName = field('input', 'hbr-name', 'Your name');
  firstName.input.type = 'text';
  firstName.input.maxLength = 80;
  firstName.input.autocomplete = 'name';
  firstName.input.addEventListener('input', () => firstName.input.setCustomValidity(''));
  const message = field('textarea', 'hbr-message', 'Comment');
  message.input.rows = 4;
  message.input.maxLength = 4000;
  message.input.setAttribute('aria-describedby', 'hbr-image-hint');
  message.input.addEventListener('input', () => {
    if (target) draftFor(target).text = message.input.value;
  });

  const fileRow = field('input', 'hbr-files', 'Attach images');
  fileRow.input.className = 'hbr-file-input';
  fileRow.input.type = 'file';
  fileRow.input.multiple = true;
  fileRow.input.accept = [...allowedTypes].join(',');
  fileRow.input.setAttribute('aria-describedby', 'hbr-image-hint');
  const imageHint = element('p', 'hbr-help', 'Choose files or paste a screenshot into the comment. Up to 3 PNG, JPEG, GIF, or WebP images, 5 MiB each.');
  imageHint.id = 'hbr-image-hint';
  fileRow.row.append(imageHint);
  const previews = element('ul', 'hbr-previews');
  previews.setAttribute('aria-label', 'Images to attach');
  fileRow.input.addEventListener('change', () => {
    attachFiles([...fileRow.input.files]);
    fileRow.input.value = '';
  });
  composer.addEventListener('paste', event => {
    if (!event.clipboardData) return;
    const clipboard = event.clipboardData;
    const files = [...clipboard.files];
    if (!files.length) {
      for (const item of clipboard.items || []) {
        if (item.kind === 'file') {
          const file = item.getAsFile();
          if (file) files.push(file);
        }
      }
    }
    if (files.length) {
      event.preventDefault();
      attachFiles(files);
    }
  });

  const composeActions = element('div', 'hbr-actions');
  const submit = button('Post comment', 'btn btn-primary');
  submit.type = 'submit';
  const cancel = button('Close draft', 'btn btn-default', () => {
    composer.hidden = true;
    add.focus();
  });
  composeActions.append(submit, cancel);
  const composeStatus = element('p', 'hbr-status');
  composeStatus.setAttribute('role', 'status');
  inputs.append(locationField.row, firstName.row, message.row, fileRow.row, previews, composeActions);
  composer.append(composeTitle, inputs, composeStatus);
  composer.addEventListener('submit', post);

  const status = element('p', 'hbr-status hbr-load-status');
  status.setAttribute('role', 'status');
  const threads = element('ol', 'hbr-threads');
  threads.setAttribute('aria-label', 'Comment threads');
  scroller.append(actions, identity, nameEditor, status, composer, threads);
  panel.append(header, scroller);
  sidebar.append(panel);
  app.classList.add('hbr-enabled');
  updateIdentity();

  for (const [id, location] of locations) {
    const row = element('div', 'hbr-anchors');
    const markers = element('div', 'hbr-markers');
    const trigger = button(id === 'page' ? 'Comment on this chapter' : 'Comment on this section', 'btn btn-default hbr-add-at', () => {
      showPanel(trigger, false);
      compose(id, null);
    });
    trigger.setAttribute('aria-haspopup', 'dialog');
    trigger.setAttribute('aria-controls', panel.id);
    trigger.setAttribute('aria-label', `Add comment on ${location.title}`);
    row.append(markers, trigger);
    Object.assign(location, { row, markers, markerNodes: new Map() });
    if (location.body) location.body.prepend(row);
    else tools.after(row);
  }

  panel.addEventListener('cancel', event => {
    event.preventDefault();
    hidePanel();
  });
  panel.addEventListener('keydown', event => {
    if (desktop.matches && event.key === 'Escape') {
      event.stopPropagation();
      hidePanel();
    }
  });
  panel.addEventListener('close', () => {
    if (!panel.open) resetPanelState();
  });
  desktop.addEventListener('change', () => {
    if (!panel.open) return;
    const active = panel.contains(document.activeElement) ? document.activeElement : title;
    panel.close();
    openPanelMode();
    active.focus({preventScroll: true});
  });

  function openPanelMode() {
    app.classList.toggle('hbr-docked', desktop.matches);
    if (desktop.matches) panel.show();
    else panel.showModal();
    launch.setAttribute('aria-expanded', 'true');
  }

  function showPanel(trigger, focus = true) {
    if (trigger) opener = trigger;
    if (!panel.open) {
      openPanelMode();
      refresh();
    }
    if (focus) title.focus({preventScroll: true});
  }

  function resetPanelState() {
    app.classList.remove('hbr-docked');
    launch.setAttribute('aria-expanded', 'false');
  }

  function hidePanel(restoreFocus = true) {
    if (!panel.open) return;
    panel.close();
    resetPanelState();
    if (restoreFocus) {
      const origin = opener?.isConnected && opener.getClientRects().length ? opener : launch;
      origin.focus({preventScroll: true});
    }
    opener = undefined;
  }

  function updateIdentity() {
    identityText.textContent = reviewer ? `Posting as ${reviewer}` : 'Enter your name with your first comment.';
    changeName.hidden = !reviewer;
    firstName.row.hidden = Boolean(reviewer);
    firstName.input.required = !reviewer;
  }

  function setName(name) {
    reviewer = name;
    try { localStorage.setItem(identityKey, name); }
    catch { /* The current page still remembers the name when storage is disabled. */ }
    updateIdentity();
  }

  function draftFor(destination) {
    if (!drafts.has(destination.key)) drafts.set(destination.key, { text: '', images: [] });
    return drafts.get(destination.key);
  }

  function compose(section, parentId, focus = true) {
    if (posting) {
      title.focus({preventScroll: true});
      return;
    }
    target = { section, parentId, key: parentId === null ? `section:${section}` : `reply:${parentId}` };
    composeTitle.textContent = parentId === null ? 'New comment' : `Reply to #${parentId}`;
    submit.textContent = parentId === null ? 'Post comment' : 'Post reply';
    locationField.row.hidden = parentId !== null;
    locationField.input.value = section;
    message.input.value = draftFor(target).text;
    composer.hidden = false;
    composeStatus.textContent = '';
    renderPreviews();
    if (focus) (reviewer ? message.input : firstName.input).focus();
  }

  function attachFiles(files) {
    if (!target || posting) return;
    const draft = draftFor(target);
    const errors = new Set();
    for (const original of files) {
      if (draft.images.length === MAX_IMAGES) {
        errors.add(`Attach up to ${MAX_IMAGES} images.`);
        break;
      }
      const type = original.type || types.get(original.name.split('.').pop().toLowerCase());
      if (!allowedTypes.has(type)) {
        errors.add('Choose PNG, JPEG, GIF, or WebP images.');
        continue;
      }
      if (!original.size || original.size > MAX_BYTES) {
        errors.add('Images must be nonempty and 5 MiB or smaller.');
        continue;
      }
      const file = original.type ? original : new File([original], original.name, { type, lastModified: original.lastModified });
      draft.images.push({ file, url: URL.createObjectURL(file) });
    }
    composeStatus.textContent = [...errors].join(' ');
    renderPreviews();
  }

  function renderPreviews() {
    const draft = draftFor(target);
    previews.hidden = draft.images.length === 0;
    previews.replaceChildren();
    for (const image of draft.images) {
      const item = element('li');
      const thumb = element('img');
      thumb.src = image.url;
      thumb.alt = '';
      const remove = button('Remove', 'btn btn-default', () => {
        const index = draft.images.indexOf(image);
        if (index < 0 || posting) return;
        URL.revokeObjectURL(image.url);
        draft.images.splice(index, 1);
        composeStatus.textContent = 'Attachment removed.';
        renderPreviews();
        fileRow.input.focus();
      });
      remove.setAttribute('aria-label', `Remove ${image.file.name}`);
      item.append(thumb, element('span', '', image.file.name), remove);
      previews.append(item);
    }
  }

  function cleanRecord(value) {
    if (!value || value.page !== page || !locations.has(value.section) ||
        !Number.isSafeInteger(value.id) || value.id < 1 ||
        (value.parentId !== null && (!Number.isSafeInteger(value.parentId) || value.parentId < 1))) return null;
    return value;
  }

  async function jsonRequest(url, options) {
    const response = await fetch(url, options);
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(typeof body?.error === 'string' ? body.error : 'The comment server did not respond successfully.');
    }
    return body;
  }

  async function refresh() {
    if (loading) return;
    loading = true;
    const version = recordVersion;
    let repeat = false;
    reload.setAttribute('aria-disabled', 'true');
    threads.setAttribute('aria-busy', 'true');
    status.textContent = loaded ? 'Refreshing comments…' : 'Loading comments…';
    try {
      const result = await jsonRequest(endpoint, { cache: 'no-store', headers: { Accept: 'application/json' } });
      if (!Array.isArray(result)) throw new Error('The comment server returned an unreadable list.');
      if (version !== recordVersion) {
        repeat = true;
      } else {
        records = result.map(cleanRecord).filter(Boolean);
        loaded = true;
        renderThreads();
        status.textContent = records.length ? 'Comments are up to date.' : 'No comments yet. Start a thread on this chapter or a section.';
      }
    } catch (error) {
      status.textContent = `Could not load comments. ${error.message} Use Refresh to try again.`;
    } finally {
      loading = false;
      reload.removeAttribute('aria-disabled');
      threads.removeAttribute('aria-busy');
      if (repeat) refresh();
    }
  }

  async function post(event) {
    event.preventDefault();
    if (posting || !target) return;
    const destination = target;
    const draft = draftFor(destination);
    const author = reviewer || firstName.input.value.trim();
    const text = message.input.value.trim();
    if (!author) {
      firstName.input.setCustomValidity('Enter your name.');
      firstName.input.reportValidity();
      return;
    }
    if (!text && !draft.images.length) {
      composeStatus.textContent = 'Write a comment or attach an image before posting.';
      message.input.focus();
      return;
    }
    const data = new FormData();
    data.append('page', page);
    data.append('section', destination.section);
    if (destination.parentId !== null) data.append('parentId', String(destination.parentId));
    data.append('author', author);
    data.append('text', text);
    for (const {file} of draft.images) data.append('images', file, file.name);
    posting = inputs.disabled = true;
    composer.setAttribute('aria-busy', 'true');
    composeStatus.textContent = 'Posting…';
    try {
      const result = cleanRecord(await jsonRequest('api/comments', {
        method: 'POST', headers: { Accept: 'application/json', 'X-Handbook-Review': '1' }, body: data,
      }));
      if (!result) throw new Error('The comment server did not return a readable confirmation.');
      recordVersion++;
      records = [...records.filter(record => record.id !== result.id), result];
      if (!reviewer) setName(author);
      for (const image of draft.images) URL.revokeObjectURL(image.url);
      drafts.delete(destination.key);
      previews.replaceChildren();
      composer.hidden = true;
      renderThreads();
      status.textContent = destination.parentId === null ? 'Comment posted.' : 'Reply posted.';
      if (panel.open && (panel.contains(document.activeElement) || document.activeElement === document.body)) {
        focusThread(result.parentId ?? result.id);
      }
    } catch (error) {
      composeStatus.textContent = `Could not post. ${error.message} Your draft is still here.`;
    } finally {
      posting = inputs.disabled = false;
      composer.removeAttribute('aria-busy');
      if (panel.open && !composer.hidden && document.activeElement === document.body) submit.focus();
    }
  }

  function renderEntry(record) {
    const entry = element('article', 'hbr-entry');
    const byline = element('div', 'hbr-byline');
    byline.append(element('strong', '', String(record.author ?? '')));
    const date = new Date(record.createdAt);
    if (Number.isFinite(date.getTime())) {
      const time = element('time', '', date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }));
      time.dateTime = date.toISOString();
      byline.append(time);
    }
    entry.append(byline);
    if (record.text) entry.append(element('p', 'hbr-message-text', String(record.text)));
    if (Array.isArray(record.images) && record.images.length) {
      const attachments = element('ul', 'hbr-attachments');
      attachments.setAttribute('aria-label', 'Attached images');
      for (const image of record.images) {
        if (typeof image?.id !== 'string' || !/^[\w-]+$/.test(image.id)) continue;
        const url = `api/images/${encodeURIComponent(image.id)}`;
        const item = element('li');
        const link = element('a');
        link.href = url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.dataset.hbrFocus = `image-${record.id}-${image.id}`;
        const thumb = element('img');
        thumb.src = url;
        thumb.loading = 'lazy';
        thumb.alt = `Open attached image: ${image.name || 'image'} (new tab)`;
        link.append(thumb);
        item.append(link);
        attachments.append(item);
      }
      if (attachments.childElementCount) entry.append(attachments);
    }
    return entry;
  }

  function renderThreads() {
    const list = [...records].sort((a, b) => a.id - b.id);
    const roots = list.filter(record => record.parentId === null);
    const replies = new Map();
    for (const record of list) {
      if (record.parentId === null) continue;
      if (!replies.has(record.parentId)) replies.set(record.parentId, []);
      replies.get(record.parentId).push(record);
    }
    const oldFocus = threads.contains(document.activeElement) ? document.activeElement.dataset.hbrFocus : null;
    const oldScroll = scroller.scrollTop;
    const cards = document.createDocumentFragment();
    for (const root of roots) {
      const location = locations.get(root.section);
      const card = element('li', 'hbr-thread');
      card.id = `hbr-thread-${root.id}`;
      card.toggleAttribute('data-selected', selectedId === root.id);
      const heading = element('h3', 'hbr-thread-title', `#${root.id} · ${location.title}`);
      heading.tabIndex = -1;
      heading.dataset.hbrFocus = `thread-${root.id}`;
      card.append(heading, renderEntry(root));
      if (replies.has(root.id)) {
        const responseList = element('ol', 'hbr-replies');
        responseList.setAttribute('aria-label', `Replies to #${root.id}`);
        for (const reply of replies.get(root.id)) {
          const item = element('li');
          item.append(renderEntry(reply));
          responseList.append(item);
        }
        card.append(responseList);
      }
      const threadActions = element('div', 'hbr-actions');
      const reply = button('Reply', 'btn btn-default', () => compose(root.section, root.id));
      reply.setAttribute('aria-label', `Reply to #${root.id}`);
      reply.dataset.hbrFocus = `reply-${root.id}`;
      const jump = button('Show in handbook', 'btn btn-default', () => jumpTo(root));
      jump.setAttribute('aria-label', `Show #${root.id} in the handbook`);
      jump.dataset.hbrFocus = `jump-${root.id}`;
      threadActions.append(reply, jump);
      card.append(threadActions);
      cards.append(card);
    }
    threads.replaceChildren(cards);
    scroller.scrollTop = oldScroll;
    if (oldFocus) threads.querySelector(`[data-hbr-focus="${oldFocus}"]`)?.focus({preventScroll: true});
    launch.textContent = `Review comments (${roots.length})`;
    renderMarkers(roots);
  }

  function renderMarkers(roots) {
    for (const [section, location] of locations) {
      const ids = new Set(roots.filter(root => root.section === section).map(root => root.id));
      for (const [id, marker] of location.markerNodes) {
        if (!ids.has(id)) {
          marker.remove();
          location.markerNodes.delete(id);
        }
      }
      for (const id of ids) {
        if (location.markerNodes.has(id)) continue;
        const marker = button(`#${id}`, 'btn btn-default hbr-marker', () => {
          showPanel(marker, false);
          focusThread(id);
        });
        marker.id = `hbr-marker-${id}`;
        marker.setAttribute('aria-label', `Open comment thread #${id} on ${location.title}`);
        marker.setAttribute('aria-haspopup', 'dialog');
        marker.setAttribute('aria-controls', panel.id);
        location.markerNodes.set(id, marker);
        location.markers.append(marker);
      }
      location.markers.hidden = ids.size === 0;
    }
  }

  function focusThread(id) {
    const thread = document.getElementById(`hbr-thread-${id}`);
    if (!thread) return;
    selectedId = id;
    for (const card of threads.children) card.toggleAttribute('data-selected', card === thread);
    thread.querySelector('h3').focus({preventScroll: true});
    scroller.scrollTop += thread.getBoundingClientRect().top - scroller.getBoundingClientRect().top - 10;
  }

  function jumpTo(root) {
    const location = locations.get(root.section);
    const marker = location.markerNodes.get(root.id);
    if (!marker) return;
    if (!desktop.matches) {
      hidePanel(false);
      if (shortcuts) shortcuts.open = false;
    }
    if (location.section) location.section.open = true;
    requestAnimationFrame(() => {
      (location.section || location.row).scrollIntoView({block: 'start'});
      requestAnimationFrame(() => {
        const box = marker.getBoundingClientRect();
        const menuBottom = parseFloat(getComputedStyle(app).getPropertyValue('--hb-section-top')) || 0;
        const headingBottom = location.section?.querySelector(':scope > summary')?.getBoundingClientRect().bottom || 0;
        if (box.top < Math.max(menuBottom, headingBottom) || box.bottom > innerHeight) {
          marker.scrollIntoView({block: 'center'});
        }
        marker.focus({preventScroll: true});
      });
    });
  }

  refresh();
})();
