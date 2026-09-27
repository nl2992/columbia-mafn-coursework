// Static edition of the Columbia MAFN Source Library: Pagefind search, a WebLLM Copilot and a
// SheetJS data workspace, all running in the visitor's browser.
const WEBLLM_URL = 'https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm@0.2.85/+esm';
const SHEETJS_URL = 'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js';
const PAGE_SIZE = 20;
const STOPWORDS = new Set(('a an the and or of in on at to for from with as is are was were be been this that these those how what which ' +
  'when where why does do did can could would should i me my you your please explain describe show find give about it its into by ' +
  'using use used between vs versus there their them they we our us than then so if not no yes any all some such').split(' '));

const $ = (id) => document.getElementById(id);
const state = { pagefind: null, stats: null, results: [], shown: 0, selected: null, engine: null, engineModel: null,
  workbook: null, dataset: null, datasets: [], lastData: null };

function esc(text) {
  return String(text ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function decodeEntities(text) {
  const node = document.createElement('textarea');
  node.innerHTML = text;
  return node.value;
}
// Pagefind excerpts wrap matches in <mark>; keep only those tags and escape everything else.
function safeExcerpt(html) {
  return String(html || '').split(/(<\/?mark>)/).map((part) => (part === '<mark>' || part === '</mark>' ? part : esc(decodeEntities(part)))).join('');
}
function keywords(text) {
  return [...new Set(String(text).toLowerCase().match(/[\p{L}\p{N}][\p{L}\p{N}'’\-]*/gu) || [])]
    .filter((w) => w.length > 1 && !STOPWORDS.has(w));
}
function highlight(text, terms) {
  let html = esc(text);
  for (const term of terms.filter((t) => t.length > 2).slice(0, 8)) {
    html = html.replace(new RegExp(`(${esc(term).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'), '<mark>$1</mark>');
  }
  return html;
}
function toast(message) {
  const node = $('toast');
  node.textContent = message; node.hidden = false;
  clearTimeout(toast.timer); toast.timer = setTimeout(() => { node.hidden = true; }, 3200);
}
function setStatus(text, detail, kind) {
  $('index-status').textContent = text;
  if (detail) $('index-detail').textContent = detail;
  $('status-dot').className = 'status-dot' + (kind ? ` is-${kind}` : '');
}

/* ---------- Views and URL state ---------- */
function showView(name) {
  for (const button of document.querySelectorAll('.nav-item')) {
    const active = button.dataset.view === name;
    button.classList.toggle('is-active', active);
    button.toggleAttribute('aria-current', active);
  }
  for (const view of ['library', 'copilot', 'data', 'about']) $(`view-${view}`).hidden = view !== name;
  const params = new URLSearchParams(location.search);
  if (name === 'library') params.delete('view'); else params.set('view', name);
  history.replaceState(null, '', `${location.pathname}${params.toString() ? '?' + params : ''}${location.hash}`);
  if (name === 'data') initData();
  if (name === 'copilot') checkWebGPU();
}
document.querySelectorAll('.nav-item').forEach((b) => b.addEventListener('click', () => showView(b.dataset.view)));

function libraryFilters(prefix = 'f', reviewId = 'f-review') {
  const filters = {};
  for (const key of ['course', 'term', 'material', 'file_type']) {
    const node = $(`${prefix}-${key}`);
    if (node && node.value) filters[key] = node.value;
  }
  if (!$(reviewId).checked) filters.review = 'not_reviewed';
  return filters;
}
function syncUrl() {
  const params = new URLSearchParams();
  const q = $('query').value.trim();
  if (q) params.set('q', q);
  for (const key of ['course', 'term', 'material', 'file_type']) if ($(`f-${key}`).value) params.set(key, $(`f-${key}`).value);
  if ($('f-review').checked) params.set('review', '1');
  history.replaceState(null, '', `${location.pathname}${params.toString() ? '?' + params : ''}`);
}

/* ---------- Library ---------- */
async function initLibrary() {
  try {
    const [pagefind, stats] = await Promise.all([import('./pagefind/pagefind.js'), fetch('data/stats.json').then((r) => r.json())]);
    await pagefind.options({ excerptLength: 34 });
    await pagefind.init();
    state.pagefind = pagefind; state.stats = stats;
    const filters = await pagefind.filters();
    fillSelect('f-course', filters.course); fillSelect('c-course', filters.course);
    fillSelect('f-term', filters.term); fillSelect('c-term', filters.term);
    fillSelect('f-material', filters.material); fillSelect('f-file_type', filters.file_type);
    setStatus('Library ready', `${stats.documents.toLocaleString()} documents · in your browser`, 'ready');
    renderStats(stats);
    restoreFromUrl();
  } catch (error) {
    console.error(error);
    setStatus('Library unavailable', 'The search index could not load', 'error');
  }
}
function fillSelect(id, counts = {}) {
  const node = $(id);
  for (const [value, count] of Object.entries(counts).sort(([a], [b]) => a.localeCompare(b))) {
    node.add(new Option(`${value.replaceAll('_', ' ')} (${count.toLocaleString()})`, value));
  }
}
function restoreFromUrl() {
  const params = new URLSearchParams(location.search);
  for (const key of ['course', 'term', 'material', 'file_type']) if (params.get(key)) $(`f-${key}`).value = params.get(key);
  $('f-review').checked = params.get('review') === '1';
  if (params.get('q')) { $('query').value = params.get('q'); runSearch(); }
  if (params.get('view')) showView(params.get('view'));
}

async function runSearch() {
  const query = $('query').value.trim();
  syncUrl();
  if (!state.pagefind || !query) return;
  $('results').innerHTML = '<div class="empty"><h3>Searching…</h3></div>';
  const search = await state.pagefind.search(query, { filters: libraryFilters() });
  state.results = search.results; state.shown = 0; state.query = query;
  $('results').innerHTML = '';
  $('results-count').textContent = `${search.results.length.toLocaleString()} passages`;
  if (!search.results.length) {
    $('results').innerHTML = '<div class="empty"><h3>No matching passages</h3><p>Try fewer or different words, or clear a filter. Search matches the words you type, not paraphrases.</p></div>';
    $('more').hidden = true;
    return;
  }
  await showMore();
  if (!state.selected) openResult(0);
}
async function showMore() {
  const batch = state.results.slice(state.shown, state.shown + PAGE_SIZE);
  const data = await Promise.all(batch.map((r) => r.data()));
  data.forEach((item, i) => {
    const index = state.shown + i;
    state.results[index].loaded = item;
    const m = item.meta;
    const card = document.createElement('button');
    card.type = 'button'; card.className = 'result'; card.dataset.index = index;
    card.innerHTML = `<div class="result-kicker"><span>${esc(m.file_type.toUpperCase())}</span><span>${String(index + 1).padStart(2, '0')}</span></div>
      <div class="result-title">${esc(m.title)}</div>
      <div class="result-excerpt">${safeExcerpt(item.excerpt)}</div>
      <div class="pills"><span class="pill loc">${esc(m.locator)}</span><span class="pill">${esc(m.course_label.split(' - ')[0] || 'Program-wide')}</span>
      <span class="pill">${esc(m.term)}</span><span class="pill">${esc(m.material.replaceAll('_', ' '))}</span>${m.review === 'review_required' ? '<span class="pill review">solution / exam</span>' : ''}</div>`;
    card.addEventListener('click', () => openResult(index));
    $('results').appendChild(card);
  });
  state.shown += batch.length;
  $('more').hidden = state.shown >= state.results.length;
}
$('more').addEventListener('click', showMore);
$('search-form').addEventListener('submit', (e) => { e.preventDefault(); state.selected = null; runSearch(); });
document.querySelectorAll('#filters select, #f-review').forEach((n) => n.addEventListener('change', () => { state.selected = null; runSearch(); }));

async function openResult(index) {
  const ref = state.results[index];
  if (!ref) return;
  const item = ref.loaded || await ref.data();
  state.selected = index;
  document.querySelectorAll('.result').forEach((n) => n.classList.toggle('is-selected', Number(n.dataset.index) === index));
  showSource(item, keywords(state.query || ''));
}
function showSource(item, terms = []) {
  const m = item.meta;
  $('reader-title').textContent = `${m.title} · ${m.locator}`;
  $('reader-path').textContent = m.path;
  $('reader-actions').hidden = false;
  $('reader-open').href = m.file || m.github;
  $('reader-github').href = m.github;
  const passage = `<details ${m.file_type === 'pdf' && m.file ? '' : 'open'}><summary style="margin:14px 20px 0">Matching passage</summary><div class="passage">${highlight(item.content, terms)}</div></details>`;
  let stage;
  if (m.file_type === 'pdf' && m.file) {
    const page = m.locator_type === 'pdf_page' ? `#page=${encodeURIComponent(m.locator_value)}` : '';
    stage = `<div class="reader-note">PDF page ${esc(m.locator_value)} · shown in your browser's PDF viewer</div><iframe title="${esc(m.title)}" src="${esc(m.file + page)}"></iframe>${passage}`;
  } else if (['png', 'jpg', 'jpeg', 'gif'].includes(m.file_type) && m.file) {
    stage = `<div style="padding:20px;text-align:center;background:#fff"><img src="${esc(m.file)}" alt="${esc(m.title)}" style="max-width:100%;max-height:60vh"></div>${passage}`;
  } else {
    const where = m.file ? 'Use Open original for the full file.' : 'This file opens on GitHub.';
    stage = `<div class="reader-note">${esc(m.locator)} · ${where}</div>${passage}`;
  }
  $('reader-stage').innerHTML = stage;
}

/* ---------- Copilot ---------- */
async function checkWebGPU() {
  const notice = $('webgpu-notice');
  let ok = 'gpu' in navigator;
  if (ok) { try { ok = Boolean(await navigator.gpu.requestAdapter()); } catch { ok = false; } }
  notice.hidden = ok;
  if (!ok) notice.textContent = 'This browser has no WebGPU, so the Copilot cannot run here. Use a current version of Chrome, Edge, or Safari on a computer. Library search and Data still work.';
  $('ask-submit').disabled = !ok;
  return ok;
}
async function loadEngine() {
  const model = $('model').value;
  if (state.engine && state.engineModel === model) return state.engine;
  const webllm = await import(WEBLLM_URL);
  $('model-progress').hidden = false;
  const report = ({ progress, text }) => {
    $('model-progress-bar').style.width = `${Math.round((progress || 0) * 100)}%`;
    $('model-status').textContent = text || 'Loading the model…';
  };
  if (state.engine) { await state.engine.reload(model); } else {
    state.engine = await webllm.CreateMLCEngine(model, { initProgressCallback: report });
  }
  state.engineModel = model;
  $('model-progress').hidden = true;
  $('model-status').textContent = `${model.split('-q')[0]} is loaded on this device.`;
  return state.engine;
}

async function retrieve(question, filters, k = 6) {
  const terms = keywords(question);
  if (!terms.length) return [];
  const ranked = new Map();
  const add = (results, weight) => results.forEach((r, i) => {
    const entry = ranked.get(r.id) || { ref: r, score: 0, hits: 0 };
    entry.score += weight * (1 / (i + 5)); entry.hits += 1; ranked.set(r.id, entry);
  });
  add((await state.pagefind.search(terms.join(' '), { filters })).results.slice(0, 40), 3);
  // Pagefind matches every word, so long questions also search each term and reward overlap.
  if (terms.length > 1) {
    for (const term of terms.slice(0, 8)) add((await state.pagefind.search(term, { filters })).results.slice(0, 40), 1);
  }
  const ordered = [...ranked.values()].sort((a, b) => b.hits - a.hits || b.score - a.score).slice(0, 40);
  const passages = []; const perDoc = new Map();
  for (const entry of ordered) {
    const data = await entry.ref.data();
    const count = perDoc.get(data.meta.path) || 0;
    if (count >= 2) continue;
    perDoc.set(data.meta.path, count + 1);
    passages.push(data);
    if (passages.length >= k) break;
  }
  return passages;
}
function passageWindow(text, terms, size = 1300) {
  if (text.length <= size) return text;
  const lower = text.toLowerCase();
  const at = Math.max(0, Math.min(...terms.map((t) => lower.indexOf(t)).filter((i) => i >= 0), text.length) - 250);
  return text.slice(at, at + size);
}
const normalize = (s) => String(s).normalize('NFKC').toLowerCase().replace(/[‘’]/g, "'").replace(/[“”]/g, '"').replace(/[‐-―−]/g, '-').replace(/\s+/g, ' ').trim();

const ANSWER_SCHEMA = JSON.stringify({
  type: 'object',
  properties: {
    insufficient: { type: 'boolean' },
    claims: { type: 'array', items: { type: 'object', properties: { text: { type: 'string' }, source: { type: 'integer' }, quote: { type: 'string' } }, required: ['text', 'source', 'quote'] } },
  },
  required: ['insufficient', 'claims'],
});

async function ask(question) {
  const turn = document.createElement('article');
  turn.className = 'panel turn';
  turn.innerHTML = `<div class="turn-question"><div class="eyebrow">YOU</div><p>${esc(question)}</p></div><div class="turn-body"><div class="muted">Finding evidence…</div></div>`;
  $('conversation').appendChild(turn);
  turn.scrollIntoView({ behavior: 'smooth', block: 'start' });
  const body = turn.querySelector('.turn-body');
  const started = performance.now();
  const filters = libraryFilters('c', 'c-review');
  delete filters.material; delete filters.file_type;
  const passages = await retrieve(question, filters);
  if (!passages.length) {
    body.innerHTML = '<p class="abstain">No archive passages matched this question. Try naming the concept directly, or widen the course and term filters.</p>';
    return;
  }
  body.innerHTML = '<div class="muted">Composing the answer on this device…</div>';
  const terms = keywords(question);
  const context = passages.map((p, i) => `[${i + 1}] ${p.meta.title} (${p.meta.locator})\n${passageWindow(p.content, terms)}`).join('\n\n');
  const engine = await loadEngine();
  body.innerHTML = '<div class="muted">Composing the answer on this device…</div>';
  const reply = await engine.chat.completions.create({
    temperature: 0, max_tokens: 900,
    response_format: { type: 'json_object', schema: ANSWER_SCHEMA },
    extra_body: { enable_thinking: false },
    messages: [
      { role: 'system', content: 'You answer questions about Columbia MAFN course materials using only the numbered passages provided. ' +
        'Return JSON. Each claim must be one sentence supported by a single passage. "source" is that passage number, and "quote" is copied word for word from that passage (at least five words) to prove the claim. ' +
        'Use at most five claims. If the passages do not answer the question, set "insufficient" to true and return no claims. Never use outside knowledge.' },
      { role: 'user', content: `Passages:\n\n${context}\n\nQuestion: ${question}` },
    ],
  });
  let parsed;
  // Qwen3 may prefix an empty <think></think> block; parse the JSON object that follows it.
  const raw = reply.choices[0].message.content.replace(/<think>[\s\S]*?<\/think>/g, '');
  try { parsed = JSON.parse(raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1)); } catch { parsed = { insufficient: true, claims: [] }; }
  // Keep only claims whose quotation appears verbatim in the cited passage.
  const kept = []; let rejected = 0;
  for (const claim of parsed.claims || []) {
    const passage = passages[claim.source - 1];
    const quote = normalize(claim.quote || '');
    if (passage && quote.split(' ').length >= 4 && normalize(passage.content).includes(quote)) kept.push({ ...claim, passage });
    else rejected += 1;
  }
  const seconds = ((performance.now() - started) / 1000).toFixed(1);
  const evidence = `<details><summary>Retrieved evidence · ${passages.length} passages</summary>${passages.map((p, i) =>
    `<button type="button" class="cite" data-p="${i}">[${i + 1}] ${esc(p.meta.title)} · ${esc(p.meta.locator)}</button>`).join('')}</details>`;
  const claims = kept.map((c) => `<div class="claim"><div>${esc(c.text)}</div>
      <button type="button" class="cite" data-p="${c.source - 1}">${esc(c.passage.meta.title)} · ${esc(c.passage.meta.locator)}</button>
      <details><summary>Supporting quotation · checked against the source</summary><blockquote>${esc(c.quote)}</blockquote></details></div>`).join('');
  body.innerHTML = `<div class="eyebrow">CITED ANSWER</div>${kept.length ? claims : '<p class="abstain">The retrieved passages don’t clearly answer this, so no answer is given. Open the evidence below, or rephrase with the exact term used in the course.</p>'}
    ${evidence}<div class="meta-line">${esc(state.engineModel.split('-q')[0])} in your browser · ${seconds} s · ${rejected} unsupported ${rejected === 1 ? 'claim' : 'claims'} removed</div>`;
  body.querySelectorAll('.cite').forEach((button) => button.addEventListener('click', () => {
    showView('library'); showSource(passages[Number(button.dataset.p)], terms);
    $('reader-stage').scrollIntoView({ behavior: 'smooth' });
  }));
}
$('ask-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const question = $('ask').value.trim();
  if (!question || !state.pagefind) return;
  if (!(await checkWebGPU())) return;
  $('ask-submit').disabled = true; $('ask').value = '';
  try { await ask(question); } catch (error) {
    console.error(error);
    const last = $('conversation').lastElementChild?.querySelector('.turn-body');
    if (last) last.innerHTML = `<p class="abstain">The in-browser model could not answer: ${esc(error.message || error)}. If your device ran out of GPU memory, choose the lighter Qwen3 1.7B model.</p>`;
    $('model-progress').hidden = true;
  } finally { $('ask-submit').disabled = false; }
});
$('ask').addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) $('ask-form').requestSubmit(); });

/* ---------- Data ---------- */
function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (window.XLSX) return resolve();
    const node = document.createElement('script');
    node.src = src; node.onload = resolve; node.onerror = () => reject(new Error('SheetJS failed to load'));
    document.head.appendChild(node);
  });
}
async function initData() {
  if (state.datasets.length) return;
  state.datasets = await fetch('data/datasets.json').then((r) => r.json());
  fillDatasets();
}
function fillDatasets() {
  const node = $('d-path');
  const include = $('d-review').checked;
  node.innerHTML = '<option value="">Choose a workbook or dataset…</option>';
  state.datasets.filter((d) => include || d.review !== 'review_required')
    .forEach((d) => node.add(new Option(`${d.path}`, d.path)));
}
$('d-review').addEventListener('change', fillDatasets);
$('d-path').addEventListener('change', async () => {
  const dataset = state.datasets.find((d) => d.path === $('d-path').value);
  state.workbook = null; state.dataset = dataset; $('d-result').hidden = true;
  $('d-sheet').innerHTML = ''; $('d-sheet').disabled = true;
  if (!dataset) return;
  $('d-status').textContent = 'Downloading and reading the original file…';
  try {
    await loadScript(SHEETJS_URL);
    const response = await fetch(dataset.url);
    if (!response.ok) throw new Error(`download failed (${response.status})`);
    const buffer = await response.arrayBuffer();
    const text = ['csv', 'tsv'].includes(dataset.file_type);
    state.workbook = text ? XLSX.read(new TextDecoder().decode(buffer), { type: 'string', FS: dataset.file_type === 'tsv' ? '\t' : ',', raw: false })
      : XLSX.read(buffer, { type: 'array', cellDates: true });
    for (const name of state.workbook.SheetNames) {
      const ref = state.workbook.Sheets[name]['!ref'];
      const range = ref ? XLSX.utils.decode_range(ref) : null;
      $('d-sheet').add(new Option(range ? `${name} · ${range.e.r + 1} rows × ${range.e.c + 1} columns` : `${name} · empty`, name));
    }
    $('d-sheet').disabled = false;
    $('d-original').href = dataset.github;
    $('d-status').textContent = `Source loaded (${(buffer.byteLength / 1048576).toFixed(1)} MB). Choose a range and operation.`;
  } catch (error) {
    $('d-status').textContent = `Could not read this file: ${error.message}.`;
  }
});

function colIndex(letters) {
  if (!letters) return null;
  if (!/^[A-Za-z]{1,3}$/.test(letters.trim())) throw new Error('Column letters must look like A, B, … AA');
  return XLSX.utils.decode_col(letters.trim().toUpperCase());
}
function cellValue(sheet, r, c) {
  const cell = sheet[XLSX.utils.encode_cell({ r, c })];
  if (!cell) return { v: null, w: '' };
  const w = cell.w ?? (cell.v instanceof Date ? cell.v.toISOString().slice(0, 10) : String(cell.v ?? ''));
  return { v: cell.v, w };
}
function numeric(value) {
  if (typeof value.v === 'number' && Number.isFinite(value.v)) return value.v;
  const parsed = Number(String(value.w).replace(/,/g, '').trim());
  return value.w !== '' && Number.isFinite(parsed) ? parsed : null;
}

$('data-form').addEventListener('submit', (e) => {
  e.preventDefault();
  const started = performance.now();
  try {
    if (!state.workbook) throw new Error('Choose a workbook first');
    const sheetName = $('d-sheet').value;
    const sheet = state.workbook.Sheets[sheetName];
    const full = XLSX.utils.decode_range(sheet['!ref']);
    const rangeText = $('d-range').value.trim().toUpperCase();
    const range = rangeText ? XLSX.utils.decode_range(rangeText) : full;
    if (rangeText && !/^[A-Z]{1,3}\d+:[A-Z]{1,3}\d+$/.test(rangeText)) throw new Error('Use a range like A2:B486');
    const op = $('d-op').value;
    const col = colIndex($('d-col').value);
    const fcol = colIndex($('d-fcol').value);
    const min = $('d-min').value.trim() === '' ? null : Number($('d-min').value);
    const max = $('d-max').value.trim() === '' ? null : Number($('d-max').value);
    if (op !== 'preview' && op !== 'count' && col === null) throw new Error('Give the numeric column letter for this operation');
    for (const c of [col, fcol]) if (c !== null && (c < range.s.c || c > range.e.c)) throw new Error('The column must be inside the range');
    const header = $('d-header').checked;
    const columns = []; for (let c = range.s.c; c <= range.e.c; c += 1) columns.push(c);
    const labels = columns.map((c) => `${XLSX.utils.encode_col(c)}${header ? ' · ' + cellValue(sheet, range.s.r, c).w : ''}`);
    const rows = []; const values = [];
    for (let r = range.s.r + (header ? 1 : 0); r <= range.e.r; r += 1) {
      if (fcol !== null) {
        const f = numeric(cellValue(sheet, r, fcol));
        if (f === null || (min !== null && f < min) || (max !== null && f > max)) continue;
      }
      const cells = columns.map((c) => cellValue(sheet, r, c));
      if (cells.every((x) => x.w === '')) continue;
      rows.push({ row: r + 1, cells });
      if (col !== null) { const n = numeric(cellValue(sheet, r, col)); if (n !== null) values.push(n); }
    }
    const mean = values.reduce((a, b) => a + b, 0) / (values.length || 1);
    const results = {
      preview: null, count: rows.length, sum: values.reduce((a, b) => a + b, 0), mean: values.length ? mean : null,
      min: values.length ? Math.min(...values) : null, max: values.length ? Math.max(...values) : null,
      stddev: values.length > 1 ? Math.sqrt(values.reduce((a, b) => a + (b - mean) ** 2, 0) / (values.length - 1)) : null,
    };
    const value = results[op];
    const usedRange = XLSX.utils.encode_range(range);
    $('d-value').textContent = op === 'preview' ? `Preview of ${sheetName}!${usedRange}` : `${op}: ${value === null ? 'no numeric values' : value}`;
    $('d-summary').textContent = `${state.dataset.path.split('/').pop()} · ${sheetName}!${usedRange} · ${rows.length.toLocaleString()} matching rows${col !== null ? ` · ${values.length.toLocaleString()} numeric values` : ''} · ${((performance.now() - started) / 1000).toFixed(2)} seconds`;
    $('d-table-title').textContent = `Source cells · first ${Math.min(30, rows.length)} matching rows`;
    $('d-table').innerHTML = `<thead><tr><th>Source row</th>${labels.map((l) => `<th>${esc(l)}</th>`).join('')}</tr></thead><tbody>${
      rows.slice(0, 30).map((row) => `<tr><td>${row.row}</td>${row.cells.map((x) => `<td>${esc(x.w)}</td>`).join('')}</tr>`).join('')}</tbody>`;
    state.lastData = { source: { path: state.dataset.path, url: state.dataset.github, sheet: sheetName, range: usedRange },
      operation: op, numeric_column: $('d-col').value.trim().toUpperCase() || null, header_row: header,
      row_filter: fcol === null ? null : { column: $('d-fcol').value.trim().toUpperCase(), min, max },
      result: op === 'preview' ? null : value, matching_rows: rows.length, numeric_values: values.length,
      engine: 'SheetJS 0.18.5 in the browser', computed_at: new Date().toISOString() };
    $('d-result').hidden = false;
    $('d-status').textContent = 'Complete. Export the result to keep the values, exact source range, and recipe.';
  } catch (error) {
    $('d-status').textContent = error.message;
  }
});
$('d-export').addEventListener('click', () => {
  if (!state.lastData) return;
  const blob = new Blob([JSON.stringify(state.lastData, null, 2)], { type: 'application/json' });
  const link = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'mafn-data-result.json' });
  link.click(); URL.revokeObjectURL(link.href);
  toast('Result exported');
});

/* ---------- About ---------- */
function renderStats(stats) {
  const cards = [[stats.chunks, 'Searchable passages'], [stats.documents, 'Documents'], [stats.source_paths, 'Source paths'],
    [stats.terms.length, 'Terms'], [stats.hosted_files, 'Files served from this site']];
  $('stats').innerHTML = cards.map(([n, label]) => `<div class="stat"><strong>${Number(n).toLocaleString()}</strong><span>${label}</span></div>`).join('') +
    `<p class="muted small" style="grid-column:1/-1;margin:0">Index generation ${esc(stats.generation.slice(0, 8))}, built from commit <a href="https://github.com/${esc(stats.repository)}/commit/${esc(stats.commit)}">${esc(stats.commit.slice(0, 7))}</a>.</p>`;
}

initLibrary();
