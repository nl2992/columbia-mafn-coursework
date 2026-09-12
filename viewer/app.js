(() => {
  'use strict';

  const state = {
    filters: {},
    results: [],
    selected: null,
    query: '',
    mode: 'hybrid',
    initialView: 'search',
    view: 'search',
    conversation: [],
    pins: new Map(),
    askEpoch: 0,
    askController: null,
    filterValues: {},
    busy: false,
    viewerSource: null,
    viewerKind: null,
    viewerPage: null,
    viewerPageCount: null,
    viewerHighlightUrl: null,
    viewerCitationPage: null,
  };

  const $ = (id) => document.getElementById(id);
  const refs = {
    form: $('search-form'), query: $('query'), mode: $('mode'), results: $('results-list'),
    resultsTitle: $('results-title'), resultsCount: $('results-count'), searchNote: $('search-note'),
    viewerTitle: $('viewer-title'), viewerActions: $('viewer-actions'), pageInput: $('page-input'),
    pageKind: $('page-kind'), previousPage: $('previous-page'), nextPage: $('next-page'),
    openSource: $('open-source'), viewerEmpty: $('viewer-empty'), pdfViewer: $('pdf-viewer'),
    pdfFrame: $('pdf-frame'), textViewer: $('text-viewer'), sourceText: $('source-text'),
    textViewerKind: $('text-viewer-kind'), textLocator: $('text-viewer-locator'), imageViewer: $('image-viewer'), sourceImage: $('source-image'),
    fallbackViewer: $('fallback-viewer'), fallbackTitle: $('fallback-title'), fallbackCopy: $('fallback-copy'),
    fallbackOpen: $('fallback-open'), footnote: $('viewer-footnote'), detail: $('detail-body'),
    drawerState: $('drawer-state'), toast: $('toast'), statusDot: $('status-dot'), indexStatus: $('index-status'),
    indexDetail: $('index-detail'), coverage: $('coverage-view'), review: $('review-view'), searchView: $('search-view'), copilot: $('copilot-view'),
    coverageGrid: $('coverage-grid'), coverageNote: $('coverage-note'), reviewList: $('review-list'),
    copilotForm: $('copilot-form'), copilotQuery: $('copilot-query'), copilotMode: $('copilot-mode'), includeReview: $('include-review'),
    copilotScope: $('copilot-scope'), copilotStatus: $('copilot-status'), conversation: $('copilot-conversation'),
    sourceScope: $('copilot-source-scope'), pinnedSources: $('pinned-sources'), answerStyle: $('answer-style'), askSubmit: $('ask-submit'),
  };

  const filterIds = { course: 'course-filter', term: 'term-filter', content_type: 'content-filter', lecturer: 'lecturer-filter', file_type: 'file-filter', review: 'review-filter' };
  const emptyFilterLabels = { course: 'All courses', term: 'All terms', content_type: 'All materials', lecturer: 'All lecturers', file_type: 'All file types', review: 'All review states' };
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[ch]));
  const sourceUrl = (path) => `/api/source?${new URLSearchParams({ path }).toString()}`;
  const previewUrl = (path) => `/api/preview?${new URLSearchParams({ path }).toString()}`;
  const highlightUrl = (hit) => `/api/highlight?${new URLSearchParams({ chunk: hit.chunk_id, source: hit.source_path }).toString()}`;
  const citationUrl = (hit) => `/api/chunks/${encodeURIComponent(hit.chunk_id)}?${new URLSearchParams({ source: hit.source_path }).toString()}`;
  const labelFor = (hit) => hit?.citation?.label || `${hit?.source_path || 'Source'} · ${hit?.locator?.type || 'location'} ${hit?.locator?.value || ''}`;

  async function getJson(url) {
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    return data;
  }

  function showToast(message) {
    refs.toast.textContent = message;
    refs.toast.classList.add('is-visible');
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => refs.toast.classList.remove('is-visible'), 3200);
  }

  function setView(name) {
    state.view = name;
    const search = name === 'search';
    refs.form.classList.toggle('is-hidden', !search);
    refs.searchView.classList.toggle('is-hidden', !search);
    refs.copilot.classList.toggle('is-hidden', name !== 'copilot');
    refs.coverage.classList.toggle('is-hidden', name !== 'coverage');
    refs.review.classList.toggle('is-hidden', name !== 'review');
    document.querySelectorAll('.nav-item').forEach((button) => button.classList.toggle('is-active', button.dataset.view === name));
    $('page-title').textContent = search ? 'Search the archive' : name === 'copilot' ? 'Grounded copilot' : name === 'coverage' ? 'Coverage' : 'Review queue';
    updateUrl(state.selected);
    if (name === 'copilot') updateCopilotScope();
  }

  function populateSelect(id, rows, emptyLabel) {
    const select = $(id);
    const current = select.value;
    select.innerHTML = `<option value="">${emptyLabel}</option>`;
    (rows || []).forEach((row) => {
      const option = document.createElement('option');
      option.value = row.value;
      option.textContent = `${row.value} · ${row.searchable_documents ?? row.documents} searchable`;
      select.appendChild(option);
    });
    if ([...select.options].some((option) => option.value === current)) select.value = current;
  }

  async function loadIndexInfo() {
    try {
      const [health, filters] = await Promise.all([getJson('/api/health'), getJson('/api/filters')]);
      state.filters = filters;
      refs.statusDot.classList.add('is-ready');
      refs.indexStatus.textContent = 'Index ready';
      refs.indexDetail.textContent = `${health.chunks.toLocaleString()} chunks · private local service`;
      Object.entries(filterIds).forEach(([field, id]) => {
        populateSelect(id, filters[field], emptyFilterLabels[field]);
        $(id).value = state.filterValues[field] || '';
      });
      populateCoverage(health, filters);
      populateReview(filters);
    } catch (error) {
      refs.statusDot.classList.add('is-error');
      refs.indexStatus.textContent = 'Index unavailable';
      refs.indexDetail.textContent = 'Start the local search service';
      refs.searchNote.textContent = error.message;
      showToast(error.message);
    }
  }

  function populateCoverage(health, filters) {
    const reportCards = [
      ['Chunks', health.chunks?.toLocaleString() || '—'],
      ['Documents', health.documents?.toLocaleString() || '—'],
      ['Source paths', health.source_paths?.toLocaleString() || '—'],
      ['Paths without text', health.source_paths_without_chunks?.toLocaleString() || '—'],
      ['Terms', filters.term?.length || '—'],
    ];
    refs.coverageGrid.innerHTML = reportCards.map(([label, value]) => `<div class="coverage-card"><div class="coverage-number">${escapeHtml(value)}</div><div class="coverage-label">${escapeHtml(label)}</div></div>`).join('');
    const withoutChunks = health.source_paths_without_chunks != null
      ? `${health.source_paths_without_chunks.toLocaleString()} source paths currently have no searchable chunks`
      : 'The index report records source coverage per generation';
    refs.coverageNote.textContent = `The viewer opens verified source files only. Extracted text, image/archive catalogs, and missing-text paths are kept distinct; source locators use physical PDF pages and exact slide/range/line metadata. ${withoutChunks}.`;
  }

  function populateReview(filters) {
    const rows = filters.review || [];
    refs.reviewList.innerHTML = rows.length ? rows.map((row) => `<div class="review-row"><strong>${escapeHtml(row.value)}</strong><span>${row.documents} documents · ${row.searchable_documents ?? row.documents} searchable</span></div>`).join('') : '<div class="review-row"><strong>No review facet returned</strong><span>Use the search filter to inspect flagged material.</span></div>';
  }

  function currentFilters() {
    const filters = {};
    Object.entries(filterIds).forEach(([field, id]) => { if ($(id).value) filters[field] = [$(id).value]; });
    return filters;
  }

  function updateUrl(hit = null) {
    const params = new URLSearchParams();
    const copilot = state.view === 'copilot';
    if (copilot) params.set('view', 'copilot');
    if (!copilot && state.query) params.set('q', state.query);
    if (!copilot && state.mode !== 'hybrid') params.set('mode', state.mode);
    Object.entries(state.filterValues).forEach(([field, value]) => { if (value) params.set(field, value); });
    const hash = hit && !copilot ? new URLSearchParams({ chunk: hit.chunk_id, source: hit.source_path }).toString() : '';
    const next = `${location.pathname}${params.toString() ? `?${params}` : ''}${hash ? `#${hash}` : ''}`;
    history.replaceState(null, '', next);
  }

  function readUrlState() {
    const params = new URLSearchParams(location.search);
    state.query = params.get('q') || '';
    state.mode = ['hybrid', 'lexical', 'semantic'].includes(params.get('mode')) ? params.get('mode') : 'hybrid';
    state.initialView = params.get('view') === 'copilot' ? 'copilot' : 'search';
    refs.query.value = state.query;
    refs.mode.value = state.mode;
    refs.copilotMode.value = state.mode;
    if (state.initialView === 'copilot') refs.copilotQuery.value = state.query;
    Object.keys(filterIds).forEach((field) => {
      const value = params.get(field) || '';
      state.filterValues[field] = value;
      $(filterIds[field]).value = value;
    });
  }

  async function search(event) {
    if (event) event.preventDefault();
    if (event) setView('search');
    const query = refs.query.value.trim();
    if (!query) { showToast('Enter a search phrase first.'); refs.query.focus(); return; }
    state.query = query; state.mode = refs.mode.value; state.filterValues = {};
    const filters = currentFilters();
    Object.entries(filterIds).forEach(([field, id]) => { state.filterValues[field] = $(id).value; });
    const params = new URLSearchParams({ q: query, mode: state.mode, top_k: '12' });
    Object.entries(filters).forEach(([field, values]) => values.forEach((value) => params.append(field, value)));
    state.busy = true;
    refs.results.innerHTML = '<div class="empty-state"><div class="empty-glyph">…</div><h3>Searching locally</h3><p>Ranking exact and semantic matches.</p></div>';
    try {
      const data = await getJson(`/api/search?${params}`);
      state.results = data.results || [];
      renderResults(data);
      updateUrl(state.selected);
    } catch (error) {
      state.results = [];
      refs.results.innerHTML = `<div class="error-banner">${escapeHtml(error.message)}</div>`;
      refs.resultsTitle.textContent = 'Search failed'; refs.resultsCount.textContent = '';
    } finally { state.busy = false; }
  }

  async function ask(event) {
    if (event) event.preventDefault();
    const query = refs.copilotQuery.value.trim();
    if (!query) { showToast('Enter a question first.'); refs.copilotQuery.focus(); return; }
    if (state.askController) return;
    if (refs.sourceScope.value === 'pinned' && !state.pins.size) { showToast('Pin at least one document from Search archive first.'); return; }
    const filters = currentFilters();
    const sourcePaths = refs.sourceScope.value === 'pinned' ? [...state.pins.keys()].sort() : null;
    const policy = JSON.stringify({ filters, sourcePaths, review: refs.includeReview.checked });
    const history = [];
    for (const turn of [...state.conversation].reverse()) {
      if (turn.policy !== policy || !turn.data) break;
      if (!turn.data.abstained) history.unshift({ query: turn.query });
      if (history.length === 6) break;
    }
    const turn = { query, policy, filters, scope: updateCopilotScope(), pending: true };
    state.conversation.push(turn);
    if (state.conversation.length > 20) state.conversation.shift();
    const epoch = ++state.askEpoch;
    state.askController = new AbortController();
    refs.askSubmit.disabled = true;
    refs.copilotStatus.textContent = 'Finding evidence, composing the answer, and checking its citations…';
    renderConversation();
    const timer = setTimeout(() => { if (epoch === state.askEpoch) refs.copilotStatus.textContent = 'Still working locally. The first answer may take longer while the model loads.'; }, 12000);
    const timeout = setTimeout(() => { if (epoch === state.askEpoch) state.askController?.abort(); }, 210000);
    try {
      const response = await fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        signal: state.askController.signal,
        body: JSON.stringify({ query, mode: refs.copilotMode.value, top_k: 6, filters,
          include_review: refs.includeReview.checked, source_paths: sourcePaths, history, answer_style: refs.answerStyle.value }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not answer this question');
      if (epoch !== state.askEpoch) return;
      turn.data = data; turn.pending = false;
      refs.copilotQuery.value = '';
      refs.copilotStatus.textContent = `${data.abstained ? 'No supported answer' : 'Answer ready'} · ${(data.elapsed_ms / 1000).toFixed(1)} seconds · on this Mac`;
    } catch (error) {
      if (epoch !== state.askEpoch) return;
      turn.pending = false;
      turn.error = error.name === 'AbortError' ? 'This answer took too long. Try a narrower question or Evidence excerpts.' : error.message;
      refs.copilotStatus.textContent = turn.error;
    } finally {
      clearTimeout(timer); clearTimeout(timeout);
      if (epoch === state.askEpoch) { state.askController = null; refs.askSubmit.disabled = false; renderConversation(); }
    }
  }

  function updateCopilotScope() {
    const fields = Object.entries(currentFilters()).map(([key, values]) => `${key.replace('_', ' ')}: ${values.join(', ')}`);
    const scope = `${refs.sourceScope.value === 'pinned' ? `${state.pins.size} pinned document${state.pins.size === 1 ? '' : 's'}` : 'Searchable archive'}${fields.length ? ' · ' + fields.join(' · ') : ''} · ${refs.includeReview.checked ? 'review material enabled' : 'review material excluded'}`;
    refs.copilotScope.textContent = scope;
    return scope;
  }

  function togglePin(hit) {
    if (state.pins.has(hit.source_path)) state.pins.delete(hit.source_path);
    else if (state.pins.size < 12) state.pins.set(hit.source_path, hit);
    else { showToast('Pin up to 12 documents at a time.'); return; }
    renderPins();
    if (state.selected) renderDetail(state.selected);
    document.querySelectorAll('.pin-result').forEach((button) => {
      const pinned = state.pins.has(button.dataset.path);
      button.textContent = pinned ? 'Pinned' : 'Pin document'; button.setAttribute('aria-pressed', String(pinned));
    });
  }

  function renderPins() {
    refs.pinnedSources.innerHTML = state.pins.size ? [...state.pins.values()].map((hit) => `<button type="button" class="pinned-chip" data-path="${escapeHtml(hit.source_path)}" title="Remove ${escapeHtml(hit.source_path)}">${escapeHtml(hit.source_path.split('/').pop())} <span aria-hidden="true">×</span></button>`).join('') : '<span class="small-muted">Pin documents from search results or the source drawer, then select Pinned documents above.</span>';
    refs.pinnedSources.querySelectorAll('[data-path]').forEach((button) => button.addEventListener('click', () => togglePin(state.pins.get(button.dataset.path))));
    $('clear-pins').disabled = state.pins.size === 0;
    updateCopilotScope();
  }

  function citationButton(support, turnIndex) {
    return `<button type="button" class="citation-chip copilot-citation" data-turn="${turnIndex}" data-chunk="${escapeHtml(support.citation_id)}">${escapeHtml(support.citation?.label)}</button>`;
  }

  function renderConversation() {
    refs.conversation.innerHTML = state.conversation.length ? state.conversation.map((turn, turnIndex) => {
      const data = turn.data;
      const header = `<div class="conversation-question"><span class="eyebrow">YOU</span><p>${escapeHtml(turn.query)}</p><small>${escapeHtml(turn.scope)}</small></div>`;
      if (!data) return `<article class="conversation-turn">${header}<div class="copilot-answer-card" role="status">${turn.pending ? 'Finding sources and checking the answer…' : escapeHtml(turn.error)}</div></article>`;
      const claims = [...(data.claims || []), ...(data.conflicts || [])].map((claim) => `<div class="answer-claim${claim.kind === 'conflict' ? ' claim-conflict' : ''}">${claim.kind === 'conflict' ? '<span class="eyebrow">SOURCES DISAGREE</span>' : ''}<p>${escapeHtml(claim.text)}</p><div class="claim-citations">${claim.supports.map((support) => citationButton(support, turnIndex)).join('')}</div><details class="claim-support"><summary>${claim.kind === 'excerpt' ? 'Source excerpt' : 'Supporting quotations · checked against the source'}</summary>${claim.supports.map((s) => `<blockquote>${escapeHtml(s.quote)}</blockquote>`).join('')}${claim.kind !== 'excerpt' ? '<small>Passed a separate local model support check. Inspect the original for equations and context.</small>' : ''}</details></div>`).join('');
      const evidence = (data.citations || []).map((hit) => `<div class="retrieved-evidence">${citationButton(hit, turnIndex)}<div class="small-muted">${escapeHtml(hit.metadata?.term)} · ${escapeHtml(hit.metadata?.course || 'Program-wide')}${hit.metadata?.version_label ? ` · version ${escapeHtml(hit.metadata.version_label)}` : ''}</div><p>${escapeHtml((hit.excerpt || hit.text).slice(0, 600))}</p><button class="quiet-button pin-result" data-path="${escapeHtml(hit.source_path)}" data-turn="${turnIndex}" data-pin="${escapeHtml(hit.citation_id)}" aria-pressed="${state.pins.has(hit.source_path)}">${state.pins.has(hit.source_path) ? 'Pinned' : 'Pin document'}</button></div>`).join('');
      return `<article class="conversation-turn">${header}<div class="copilot-answer-card"><div class="eyebrow">${data.provider === 'local-extractive' ? 'EVIDENCE EXCERPTS' : 'CITED ANSWER'}</div>${data.abstained || data.provider === 'local-extractive' ? `<p class="copilot-answer">${escapeHtml(data.answer)}</p>` : ''}${claims}<div class="copilot-warnings">${(data.warnings || []).map((w) => `<div class="warning-banner">${escapeHtml(w)}</div>`).join('')}</div><details class="retrieved-matches"><summary>Retrieved evidence · ${data.citations.length} passages</summary>${evidence || '<p>No sources met this scope. Check Coverage for missing text.</p>'}<p class="small-muted">${escapeHtml(data.note)} Coverage: ${data.coverage?.source_paths_without_chunks ?? '—'} archive paths lack searchable text.</p></details><div class="answer-footer">${data.model ? escapeHtml(data.model) + ' · ' : ''}${(data.elapsed_ms / 1000).toFixed(1)} s · ${data.validation?.rejected_claims || 0} unsupported proposals omitted</div></div></article>`;
    }).join('') : '<div class="copilot-empty"><h3>Your sources, in conversation</h3><p>Ask a question below. Follow-ups use earlier questions in this tab; every answer retrieves and checks its evidence again.</p></div>';
    refs.conversation.querySelectorAll('.copilot-citation').forEach((button) => button.addEventListener('click', () => {
      const turn = state.conversation[Number(button.dataset.turn)];
      const hit = turn?.data?.citations.find((r) => r.citation_id === button.dataset.chunk);
      if (!hit) return;
      state.query = turn.query; refs.query.value = turn.query;
      state.mode = turn.data.retrieval.mode; refs.mode.value = state.mode;
      Object.entries(filterIds).forEach(([field, id]) => { $(id).value = turn.filters[field]?.[0] || ''; state.filterValues[field] = $(id).value; });
      state.results = turn.data.citations;
      renderResults({ ...turn.data.retrieval, results: state.results, note: 'Evidence retrieved for this conversation. Open a citation or pin a document.' });
      setView('search'); openHit(hit);
    }));
    refs.conversation.querySelectorAll('[data-pin]').forEach((button) => button.addEventListener('click', () => {
      const hit = state.conversation[Number(button.dataset.turn)]?.data?.citations.find((r) => r.citation_id === button.dataset.pin);
      if (hit) togglePin(hit);
    }));
  }

  function newChat() {
    state.askEpoch++;
    state.askController?.abort(); state.askController = null;
    state.conversation = []; refs.copilotQuery.value = ''; refs.askSubmit.disabled = false;
    refs.copilotStatus.textContent = 'New conversation. Your pins and filters are still selected.';
    renderConversation(); updateUrl(); refs.copilotQuery.focus();
  }

  async function loadCopilotStatus() {
    try {
      const data = await getJson('/api/copilot/status');
      refs.copilotStatus.textContent = data.available ? 'Local answer model ready. Ask a question to begin.' : 'Local answer model is offline. Evidence excerpts are still available.';
    } catch { refs.copilotStatus.textContent = 'Connect the local service to begin.'; }
  }

  function renderResults(data) {
    refs.resultsTitle.textContent = state.query;
    refs.resultsCount.textContent = `${data.results.length} of ${data.eligible_chunks.toLocaleString()} eligible`;
    refs.searchNote.textContent = data.note || `${data.mode} retrieval · ${data.elapsed_ms} ms · locators preserved from ingestion`;
    if (!data.results.length) {
      refs.results.innerHTML = '<div class="empty-state"><div class="empty-glyph">⌕</div><h3>No matching evidence</h3><p>Try a broader phrase or remove a filter. Missing-text files are reported in Coverage.</p></div>';
      return;
    }
    refs.results.innerHTML = data.results.map((hit, index) => {
      const meta = [hit.metadata?.course, hit.metadata?.term, hit.metadata?.content_type].filter(Boolean);
      if (hit.metadata?.review === 'review_required') meta.push('review required');
      return `<article class="result-card${state.selected?.chunk_id === hit.chunk_id ? ' is-selected' : ''}" data-chunk="${escapeHtml(hit.chunk_id)}">
        <span class="result-rank">${index + 1}</span><div class="result-title">${escapeHtml(hit.source_path.split('/').pop())}</div>
        <div class="result-path" title="${escapeHtml(hit.source_path)}">${escapeHtml(hit.source_path)}</div>
        <div class="result-excerpt">${escapeHtml(hit.excerpt || hit.text)}</div>
        <button type="button" class="citation-chip">${escapeHtml(labelFor(hit))}</button>
        <div class="result-meta">${meta.map((item) => `<span class="meta-pill${item === 'review required' ? ' review' : ''}">${escapeHtml(item)}</span>`).join('')}</div>
        <button type="button" class="quiet-button pin-result" data-path="${escapeHtml(hit.source_path)}" aria-pressed="${state.pins.has(hit.source_path)}">${state.pins.has(hit.source_path) ? 'Pinned' : 'Pin document'}</button>
      </article>`;
    }).join('');
    refs.results.querySelectorAll('.result-card').forEach((card) => card.addEventListener('click', () => {
      const hit = state.results.find((item) => item.chunk_id === card.dataset.chunk);
      if (hit) openHit(hit);
    }));
    refs.results.querySelectorAll('.pin-result').forEach((button) => button.addEventListener('click', (event) => {
      event.stopPropagation();
      const hit = state.results.find((item) => item.source_path === button.dataset.path);
      if (hit) togglePin(hit);
    }));
  }

  async function openHit(hit, options = {}) {
    try {
      refs.drawerState.textContent = 'Verifying source…';
      const resolved = await getJson(citationUrl(hit));
      state.selected = { ...hit, ...resolved, source_path: resolved.source_path || hit.source_path };
      updateUrl(state.selected);
      renderSelected();
      if (!options.silent) refs.viewerTitle.scrollIntoView({ block: 'nearest' });
    } catch (error) { showToast(error.message); refs.drawerState.textContent = 'Unable to resolve'; }
  }

  function resetViewer() {
    [refs.viewerEmpty, refs.pdfViewer, refs.textViewer, refs.imageViewer, refs.fallbackViewer].forEach((node) => node.classList.add('is-hidden'));
    refs.viewerActions.hidden = true;
    refs.openSource.href = '#';
    state.viewerSource = null;
    state.viewerKind = null;
    state.viewerPage = null;
    state.viewerPageCount = null;
    state.viewerHighlightUrl = null;
    state.viewerCitationPage = null;
  }

  function selectedIsCurrent(hit) { return (hit.source_states || []).length > 0 && hit.source_states.every((item) => item.state === 'current'); }

  function renderSelected() {
    const hit = state.selected;
    if (!hit) { resetViewer(); refs.viewerEmpty.classList.remove('is-hidden'); refs.viewerTitle.textContent = 'No source selected'; refs.drawerState.textContent = 'Awaiting source'; renderDetail(null); return; }
    refs.viewerTitle.textContent = hit.source_path.split('/').pop();
    refs.drawerState.textContent = selectedIsCurrent(hit) ? 'Verified source' : 'Source needs review';
    renderDetail(hit);
    resetViewer();
    const current = selectedIsCurrent(hit);
    const kind = hit.locator?.type || '';
    const source = sourceUrl(hit.source_path);
    refs.openSource.href = source;
    if (!current) {
      showFallback(hit, 'Source changed or missing', 'The live file no longer matches the indexed artifact. Refresh ingestion before opening it.');
      refs.footnote.textContent = 'Opening is paused because the live source hash does not match the citation.';
      return;
    }
    refs.footnote.textContent = hit.locator_warning || 'Source verified against the indexed artifact hash.';
    if (kind === 'pdf_page') {
      const page = Math.max(1, Number.parseInt(hit.locator.value, 10) || 1);
      state.viewerSource = source; state.viewerKind = 'pdf'; state.viewerPage = page;
      state.viewerPageCount = Number.parseInt(hit.provenance?.page_count, 10) || null;
      state.viewerHighlightUrl = highlightUrl(hit); state.viewerCitationPage = page;
      refs.viewerActions.hidden = false; refs.pageInput.value = page; refs.pageKind.textContent = 'physical page';
      refs.previousPage.disabled = page <= 1; refs.nextPage.disabled = Boolean(state.viewerPageCount && page >= state.viewerPageCount);
      refs.pdfViewer.classList.remove('is-hidden');
      refs.pdfFrame.src = `${state.viewerHighlightUrl}#page=${page}&zoom=page-width`;
      refs.footnote.textContent = 'Cited physical page with extracted text coordinates highlighted; the verified original remains available above.';
    } else if (kind === 'image_asset') {
      refs.imageViewer.classList.remove('is-hidden'); refs.sourceImage.src = source; refs.sourceImage.alt = hit.source_path.split('/').pop();
    } else if (kind === 'line_range') {
      refs.textViewer.classList.remove('is-hidden'); refs.textViewerKind.textContent = 'Focused source text'; refs.textLocator.textContent = `lines ${hit.locator.value}`; loadText(source, hit);
    } else if (kind === 'pptx_slide') {
      const slide = Math.max(1, Number.parseInt(hit.locator.value, 10) || 1);
      state.viewerSource = previewUrl(hit.source_path); state.viewerKind = 'pptx'; state.viewerPage = slide;
      refs.viewerActions.hidden = false; refs.pageInput.value = slide; refs.pageKind.textContent = 'slide';
      refs.previousPage.disabled = slide <= 1; refs.nextPage.disabled = false;
      showFallback(hit, `Preparing slide ${slide}`, 'Rendering a local PowerPoint preview…');
      loadPptxPreview(hit, slide);
    } else if (kind === 'spreadsheet_range' || kind === 'dataset_schema' || kind === 'notebook_cell' || kind === 'docx_block') {
      showEvidenceText(hit, formatLocator(kind, hit.locator.value), formatLocator(kind, hit.locator.value));
    } else {
      showFallback(hit, 'Source file', 'The extracted evidence and locator are shown in the drawer. Open the verified original for the full file.');
    }
    refs.results.querySelectorAll('.result-card').forEach((card) => card.classList.toggle('is-selected', card.dataset.chunk === hit.chunk_id));
  }

  function formatLocator(type, value) {
    return ({ spreadsheet_range: `Sheet / range ${value}`, dataset_schema: 'Dataset schema', notebook_cell: `Notebook cell ${value}`, docx_block: `Document block ${value}` }[type] || `${type} ${value}`);
  }

  async function loadText(url, hit) {
    try {
      const response = await fetch(url); if (!response.ok) throw new Error('Source text could not be opened');
      refs.sourceText.textContent = await response.text();
    } catch (error) { refs.sourceText.textContent = `${hit.text}\n\n[${error.message}]`; }
  }

  function showEvidenceText(hit, title, locator) {
    refs.textViewer.classList.remove('is-hidden');
    refs.textViewerKind.textContent = title;
    refs.textLocator.textContent = locator;
    refs.sourceText.textContent = hit.text || 'No extracted evidence was stored for this citation.';
    refs.footnote.textContent = 'Showing the extracted evidence for the exact locator; the verified original remains available above.';
  }

  async function loadPptxPreview(hit, slide) {
    const url = previewUrl(hit.source_path);
    try {
      const response = await fetch(url, { method: 'HEAD' });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || `Preview request failed (${response.status})`);
      }
      const pageCount = Number.parseInt(response.headers.get('X-Preview-Pages') || '', 10);
      if (!state.selected || state.selected.chunk_id !== hit.chunk_id) return;
      state.viewerSource = url; state.viewerKind = 'pptx'; state.viewerPage = slide;
      state.viewerPageCount = Number.isFinite(pageCount) ? pageCount : null;
      refs.viewerActions.hidden = false; refs.pageInput.value = slide; refs.pageKind.textContent = 'slide';
      refs.previousPage.disabled = slide <= 1;
      refs.nextPage.disabled = state.viewerPageCount ? slide >= state.viewerPageCount : false;
      refs.pdfViewer.classList.remove('is-hidden'); refs.fallbackViewer.classList.add('is-hidden');
      refs.pdfFrame.src = `${url}#page=${slide}&zoom=page-width`;
      refs.footnote.textContent = 'Rendered local PowerPoint preview; the verified original deck remains available above.';
    } catch (error) {
      if (state.selected && state.selected.chunk_id === hit.chunk_id) {
        showFallback(hit, `Slide ${slide}`, `Inline preview could not be rendered. ${error.message} Open the verified original deck.`);
        refs.viewerActions.hidden = true;
        refs.footnote.textContent = 'The exact slide locator remains preserved in the evidence drawer.';
      }
    }
  }

  function showFallback(hit, title, copy) {
    refs.fallbackViewer.classList.remove('is-hidden'); refs.fallbackTitle.textContent = title;
    refs.fallbackCopy.textContent = `${copy} Citation: ${labelFor(hit)}.`; refs.fallbackOpen.href = sourceUrl(hit.source_path);
  }

  function renderDetail(hit) {
    if (!hit) { refs.detail.innerHTML = '<div class="detail-empty"><div class="detail-empty-mark">◌</div><p>Select a result to inspect its evidence, source path, and version context.</p></div>'; return; }
    const metadata = hit.metadata || {};
    const stateRows = (hit.source_states || []).map((item) => `<div class="source-state ${item.state !== 'current' ? `is-${item.state}` : ''}"><span class="source-state-dot"></span><span>${escapeHtml(item.state)} · ${escapeHtml(item.path)}</span></div>`).join('');
    const aliases = (hit.sources || []).map((source) => `<button type="button" class="source-alias${source.path === hit.source_path ? ' is-current' : ''}" data-source-path="${escapeHtml(source.path)}">${escapeHtml(source.path)}${source.version_label ? ` · v${escapeHtml(source.version_label)}` : ''}</button>`).join('');
    const versions = (hit.related_versions || []).map((source) => `<div><button type="button" class="version-link" data-source-path="${escapeHtml(source.path)}">${escapeHtml(source.path)}${source.version_label ? ` · v${escapeHtml(source.version_label)}` : ''}</button></div>`).join('');
    refs.detail.innerHTML = `<div class="detail-title">${escapeHtml(hit.source_path.split('/').pop())}</div>
      <div class="detail-path">${escapeHtml(hit.source_path)}</div>
      <button type="button" id="pin-selected" class="quiet-button pin-result" data-path="${escapeHtml(hit.source_path)}" aria-pressed="${state.pins.has(hit.source_path)}">${state.pins.has(hit.source_path) ? 'Pinned' : 'Pin document'}</button>
      ${metadata.review === 'review_required' ? '<div class="warning-banner detail-warning">Review required: this material is labeled as an assessment or solution.</div>' : ''}
      <div class="detail-section"><div class="detail-label">Citation</div><div class="citation-chip">${escapeHtml(labelFor(hit))}</div><div class="detail-value detail-spaced-value">${escapeHtml(hit.locator?.type)} · ${escapeHtml(hit.locator?.value)}</div></div>
      <div class="detail-section"><div class="detail-label">Evidence</div><div class="evidence-block">${escapeHtml(hit.text)}</div><div class="evidence-note">${escapeHtml(hit.locator?.type === 'pdf_page' ? 'Stored excerpt from Stage 3; the cited PDF preview adds text-coordinate overlays when available.' : 'Stored excerpt from the Stage 3 record. Other formats remain evidence-first rather than pixel-highlighted.')}</div></div>
      <div class="detail-section"><div class="detail-label">Archive context</div><div class="detail-value">${escapeHtml(metadata.course_label || metadata.course || 'Program-wide')}<br>${escapeHtml(metadata.term || 'Term unknown')} · ${escapeHtml(metadata.content_type || 'material')} · ${escapeHtml(metadata.file_type || 'file')}</div>${metadata.lecturer ? `<div class="detail-value detail-spaced-value-small">Lecturer · ${escapeHtml(metadata.lecturer)}</div>` : ''}</div>
      <div class="detail-section"><div class="detail-label">Live source check</div>${stateRows || '<div class="source-state"><span class="source-state-dot"></span><span>Verified when opened</span></div>'}</div>
      ${aliases ? `<div class="detail-section"><div class="detail-label">Source aliases</div>${aliases}</div>` : ''}
      ${versions ? `<div class="detail-section"><div class="detail-label">Related versions</div>${versions}</div>` : ''}
      <div class="detail-section"><div class="detail-label">Artifact version</div><div class="detail-path">${escapeHtml(hit.artifact_version)}</div></div>`;
    refs.detail.querySelectorAll('[data-source-path]').forEach((button) => button.addEventListener('click', () => switchSource(button.dataset.sourcePath)));
    $('pin-selected').addEventListener('click', () => togglePin(hit));
  }

  async function switchSource(path) {
    if (!state.selected || path === state.selected.source_path) return;
    const base = state.results.find((hit) => hit.chunk_id === state.selected.chunk_id) || state.selected;
    await openHit({ ...base, source_path: path });
  }

  function movePage(delta) {
    if (!state.selected || !['pdf', 'pptx'].includes(state.viewerKind)) return;
    jumpToPage((Number.parseInt(refs.pageInput.value, 10) || 1) + delta);
  }

  function jumpToPage(value) {
    if (!state.selected || !['pdf', 'pptx'].includes(state.viewerKind)) return;
    const max = state.viewerPageCount || Number.POSITIVE_INFINITY;
    const page = Math.min(max, Math.max(1, Number.parseInt(value, 10) || 1));
    state.viewerPage = page; refs.pageInput.value = page;
    refs.previousPage.disabled = page <= 1;
    refs.nextPage.disabled = Boolean(state.viewerPageCount && page >= state.viewerPageCount);
    const url = state.viewerSource || sourceUrl(state.selected.source_path);
    const frameUrl = state.viewerKind === 'pdf' && page === state.viewerCitationPage && state.viewerHighlightUrl
      ? state.viewerHighlightUrl : url;
    refs.pdfFrame.src = `${frameUrl}#page=${page}&zoom=page-width`;
    if (state.viewerKind === 'pdf') {
      refs.footnote.textContent = page === state.viewerCitationPage
        ? 'Cited physical page with extracted text coordinates highlighted; the verified original remains available above.'
        : 'Showing an adjacent physical page; return to the cited page to see extracted text coordinates highlighted.';
    }
    if (state.viewerKind === 'pdf') {
      updateUrl({ ...state.selected, locator: { ...state.selected.locator, value: String(page) } });
    }
  }

  function bind() {
    refs.form.addEventListener('submit', search);
    refs.copilotForm.addEventListener('submit', ask);
    refs.mode.addEventListener('change', () => { if (state.query) search(); });
    const filtersChanged = () => {
      Object.entries(filterIds).forEach(([field, id]) => { state.filterValues[field] = $(id).value; });
      updateCopilotScope(); updateUrl(state.selected);
      if (state.view === 'search' && state.query) search();
    };
    Object.values(filterIds).forEach((id) => $(id).addEventListener('change', filtersChanged));
    $('clear-filters').addEventListener('click', () => { Object.values(filterIds).forEach((id) => { $(id).value = ''; }); filtersChanged(); });
    $('new-chat').addEventListener('click', newChat);
    $('clear-pins').addEventListener('click', () => { const pins = [...state.pins.values()]; pins.forEach(togglePin); });
    refs.sourceScope.addEventListener('change', updateCopilotScope);
    refs.includeReview.addEventListener('change', updateCopilotScope);
    refs.copilotQuery.addEventListener('keydown', (event) => { if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) { event.preventDefault(); ask(); } });
    $('clear-selection').addEventListener('click', () => { state.selected = null; updateUrl(null); renderSelected(); });
    refs.previousPage.addEventListener('click', () => movePage(-1)); refs.nextPage.addEventListener('click', () => movePage(1));
    refs.pageInput.addEventListener('change', () => jumpToPage(refs.pageInput.value));
    document.querySelectorAll('.nav-item').forEach((button) => button.addEventListener('click', () => setView(button.dataset.view)));
    document.querySelectorAll('.prompt-chip').forEach((button) => button.addEventListener('click', () => { refs.copilotQuery.value = button.dataset.prompt; refs.copilotQuery.focus(); }));
    $('back-to-search').addEventListener('click', () => setView('search')); $('review-search').addEventListener('click', () => { setView('search'); $('review-filter')?.focus(); });
    document.addEventListener('keydown', (event) => { if (event.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) { event.preventDefault(); (state.view === 'copilot' ? refs.copilotQuery : refs.query).focus(); } });
  }

  async function openDeepLink() {
    const hash = new URLSearchParams(location.hash.slice(1)); const chunk = hash.get('chunk');
    if (state.initialView === 'copilot') {
      setView('copilot');
      if (state.query) await ask();
    } else if (state.query) await search();
    if (!chunk) return;
    setView('search');
    try { await openHit({ chunk_id: chunk, source_path: hash.get('source') || '' }, { silent: true }); }
    catch (error) { showToast(error.message); }
  }

  bind(); readUrlState(); renderPins(); renderConversation();
  loadIndexInfo().then(async () => { await loadCopilotStatus(); await openDeepLink(); });
})();
