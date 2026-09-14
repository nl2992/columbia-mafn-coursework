/* Explicit local data operations; historical results never silently recalculate. */
window.DataWorkspace = class {
  constructor(hooks) {
    this.hooks = hooks; this.result = null; this.datasets = []; this.scope = null; this.epoch = 0;
    this.$ = id => document.getElementById(id);
    this.escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    this.$('data-path').addEventListener('change', () => this.select());
    this.$('data-review').addEventListener('change', () => this.load());
    this.$('data-all').addEventListener('click', () => this.load());
    this.$('data-form').addEventListener('submit', event => { event.preventDefault(); this.run(); });
    this.$('data-export').addEventListener('click', () => { if (this.result) hooks.download('mafn-data-result.json', this.result); });
    this.$('data-save').addEventListener('click', () => {
      if (this.result) hooks.save({title: `${this.result.operation} · ${this.result.citation.label}`.slice(0,200), result:this.result}).catch(error => this.status(error.message, true));
    });
  }

  async request(url, body) {
    const response = await fetch(url, body ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)} : {});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Data request failed');
    return data;
  }

  status(text, error=false) { this.$('data-status').textContent = text; this.$('data-status').classList.toggle('save-error', error); }

  async load(candidates=null, includeReview=false) {
    const epoch = ++this.epoch;
    this.status('Loading available datasets…');
    this.$('data-run').disabled = true;
    this.scope = candidates;
    if (candidates) this.$('data-review').checked = includeReview;
    try {
      const datasets = candidates || (await this.request('/api/data?include_review='+this.$('data-review').checked)).datasets;
      if (epoch !== this.epoch) return;
      this.datasets = datasets;
      this.$('data-path').innerHTML = '<option value="">Choose a workbook or dataset…</option>' + datasets.map(d => `<option value="${this.escape(d.path)}">${this.escape(d.path)}</option>`).join('');
      this.$('data-scope').textContent = `${datasets.length} sources · ${candidates ? 'From your Copilot filters and pins' : 'Full archive data catalog'} · ${this.$('data-review').checked ? 'review material included' : 'review material excluded'}`;
      this.$('data-sheet').innerHTML = '<option value="">Choose a file first</option>';
      this.status('Select a file to inspect its sheets. Set the range and operation before running.');
    } catch (error) { this.status(error.message, true); }
  }

  async select() {
    const path = this.$('data-path').value;
    const epoch = ++this.epoch;
    this.$('data-run').disabled = true;
    if (!path) return;
    this.status('Verifying the original file and reading sheet names…');
    try {
      const data = await this.request('/api/data/schema?' + new URLSearchParams({path,include_review:this.$('data-review').checked}));
      if (epoch !== this.epoch) return;
      this.$('data-sheet').innerHTML = data.sheets.map(s => `<option value="${this.escape(s.name)}">${this.escape(s.name)}${s.rows ? ` · ${s.rows.toLocaleString()} rows × ${s.columns} columns` : ''}</option>`).join('');
      this.$('data-run').disabled = false;
      this.status('Source verified. Start with Preview to inspect cells, headers, and formula caches.');
    } catch (error) { this.status(error.message, true); }
  }

  async run() {
    const request = {path:this.$('data-path').value,sheet:this.$('data-sheet').value,
      range:this.$('data-range').value.trim(),header:this.$('data-header').checked,
      operation:this.$('data-operation').value,column:this.$('data-column').value.trim().toUpperCase(),
      date_format:this.$('data-date-format').value,include_review:this.$('data-review').checked};
    if (this.$('data-filter-column').value.trim()) request.filter = {
      column:this.$('data-filter-column').value.trim().toUpperCase(),type:this.$('data-filter-type').value,
      min:this.$('data-min').value.trim(),max:this.$('data-max').value.trim()};
    this.$('data-run').disabled = true;
    this.status('Reading verified source rows and calculating locally…');
    try {
      const result = await this.request('/api/data/query',request);
      this.render(result);
      this.status('Complete. Save this result to keep the values, exact source range, and reproducible recipe.');
    } catch (error) { this.status(error.message, true); }
    finally { this.$('data-run').disabled = !this.$('data-path').value; }
  }

  async openResult(result) {
    this.render(result, true);
    this.status('Checking whether this saved result still matches the original file…');
    try {
      const data = await this.request('/api/data/schema?' + new URLSearchParams({path:result.source_path,include_review:result.recipe.include_review || false}));
      this.status(data.source.content_hash === result.source_hash ? 'Saved snapshot · source still matches. No calculation was rerun.' : 'Saved snapshot · source version differs. Keep the old result; rerun explicitly for current values.', data.source.content_hash !== result.source_hash);
    } catch (error) { this.status('Saved snapshot · source cannot currently be verified: '+error.message, true); }
  }

  render(result, historical=false) {
    this.result = result;
    const e = this.escape;
    this.$('data-result').classList.remove('is-hidden');
    this.$('data-summary').innerHTML = `<div><div class="eyebrow">${historical ? 'SAVED SNAPSHOT' : 'VERIFIED LOCAL RESULT'}</div><h2>${e(result.operation === 'preview' ? 'Source preview' : `${result.operation}: ${result.value ?? 'No numeric result'}`)}</h2><p>${e(result.citation.label)}</p><p class="small-muted">${result.rows_matched.toLocaleString()} matching rows · ${result.numeric_values.toLocaleString()} numeric values · ${(result.elapsed_ms/1000).toFixed(2)} seconds</p></div>`;
    this.$('data-original').href = '/api/source?'+new URLSearchParams({path:result.source_path});
    this.$('data-warnings').innerHTML = result.warnings.map(w=>`<p>${e(w)}</p>`).join('');
    this.$('data-schema').innerHTML = `<table><thead><tr><th>Column</th><th>Header</th><th>Unit</th><th>Numeric / filled</th><th>Date coverage of selected range</th></tr></thead><tbody>${result.schema.map(c=>`<tr><th>${e(c.column)}</th><td>${e(c.label)}</td><td>${e(c.unit)}</td><td>${c.numeric} / ${c.nonempty}</td><td>${e(c.date_min ? `${c.date_min} → ${c.date_max}` : 'Not identified in selected date format')}</td></tr>`).join('')}</tbody></table>`;
    this.$('data-table').innerHTML = `<table><thead><tr><th>Source row</th>${result.schema.map(c=>`<th>${e(c.column)} · ${e(c.label)}</th>`).join('')}</tr></thead><tbody>${result.preview.map(row=>`<tr><th>${row.row}</th>${result.schema.map(c=> {
      const cell = row.cells.find(v=>v.cell === c.column+row.row);
      return `<td title="${e(result.sheet+'!'+c.column+row.row)}">${e(cell?.value)}${cell?.formula ? `<code>${e(cell.formula)}</code><small>Stored value above; not recalculated</small>` : ''}</td>`;
    }).join('')}</tr>`).join('')}</tbody></table>`;
    this.$('data-recipe').textContent = JSON.stringify({recipe:result.recipe,source_sha256:result.source_hash,engine:result.engine,replay:result.replay},null,2);
  }
};
