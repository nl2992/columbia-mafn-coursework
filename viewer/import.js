class ImportWorkspace {
  constructor({notify, refreshed}) {
    this.notify = notify;
    this.refreshed = refreshed;
    this.loaded = false;
    this.pollTimer = null;
    this.extensions = [];
    this.limits = {files:20, file_bytes:64 * 1024 * 1024, batch_bytes:128 * 1024 * 1024};
    this.lastStates = new Map();
  }

  $(id) { return document.getElementById(id); }
  escape(value) { return String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch])); }
  size(bytes) { return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`; }

  async json(url, options) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    return data;
  }

  async load() {
    const data = await this.json('/api/import');
    this.loaded = true;
    this.extensions = data.extensions || [];
    this.limits = data.limits || this.limits;
    const select = this.$('import-folder');
    const current = select.value;
    select.innerHTML = '<option value="">Choose an existing folder…</option>';
    for (const folder of data.folders || []) {
      const option = document.createElement('option');
      option.value = folder; option.textContent = folder; select.appendChild(option);
    }
    if ([...select.options].some(option => option.value === current)) select.value = current;
    const repo = data.repository || {};
    this.$('import-publish-target').textContent = repo.automatic_publish
      ? `After verification, files are committed and pushed to ${repo.branch} at ${repo.remote}.`
      : 'Automatic publishing needs a checked-out Git branch and an origin remote.';
    this.$('import-limits').textContent = `Up to ${data.limits.files} files per batch · ${this.size(data.limits.file_bytes)} each · ${this.size(data.limits.batch_bytes)} total`;
    this.renderJobs(data.jobs || []);
    this.validate();
    this.schedulePoll(data.jobs || []);
  }

  renderFiles() {
    const files = [...this.$('import-files').files];
    this.$('import-file-list').innerHTML = files.length
      ? files.map(file => `<li><strong>${this.escape(file.name)}</strong><span>${this.size(file.size)}</span></li>`).join('')
      : '<li class="import-empty">No documents selected yet.</li>';
    this.validate();
  }

  validate() {
    const files = [...this.$('import-files').files];
    const problems = [];
    if (!this.$('import-folder').value) problems.push('Choose a destination folder.');
    if (!files.length) problems.push('Choose at least one document.');
    for (const file of files) {
      const extension = '.' + (file.name.split('.').pop() || '').toLowerCase();
      if (!this.extensions.includes(extension)) problems.push(`${file.name} is not a supported document type.`);
      if (file.size > this.limits.file_bytes) problems.push(`${file.name} is larger than ${this.size(this.limits.file_bytes)}.`);
    }
    if (files.length > this.limits.files) problems.push(`Choose no more than ${this.limits.files} files.`);
    if (files.reduce((sum, file) => sum + file.size, 0) > this.limits.batch_bytes) problems.push(`The selected batch is larger than ${this.size(this.limits.batch_bytes)}.`);
    this.$('import-submit').disabled = Boolean(problems.length);
    this.$('import-validation').textContent = problems[0] || `${files.length} document${files.length === 1 ? '' : 's'} ready for local verification.`;
  }

  async record(file) {
    const bytes = await file.arrayBuffer();
    const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))]
      .map(value => value.toString(16).padStart(2, '0')).join('');
    const data = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error(`Could not read ${file.name}`));
      reader.onload = () => resolve(String(reader.result).split(',', 2)[1]);
      reader.readAsDataURL(file);
    });
    return {name: file.name, size: file.size, sha256: digest, data};
  }

  async submit(event) {
    event.preventDefault();
    const button = this.$('import-submit');
    button.disabled = true; button.textContent = 'Verifying files…';
    try {
      const files = [];
      for (const file of this.$('import-files').files) files.push(await this.record(file));
      const job = await this.json('/api/import', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({folder:this.$('import-folder').value, files})});
      this.$('import-files').value = '';
      this.renderFiles();
      this.notify('Documents saved locally. Indexing and publishing have started.');
      await this.load();
      this.lastStates.set(job.id, job.state);
    } catch (error) {
      this.$('import-validation').textContent = error.message;
      this.notify(error.message);
    } finally {
      button.textContent = 'Import, verify & publish';
      this.validate();
    }
  }

  renderJobs(jobs) {
    this.$('import-jobs').innerHTML = jobs.length ? jobs.map(job => {
      const complete = job.state === 'complete';
      const failed = job.state === 'failed';
      return `<article class="import-job ${complete ? 'is-complete' : failed ? 'is-failed' : 'is-running'}">
        <div class="import-job-heading"><strong>${this.escape(job.stage.replaceAll('_', ' '))}</strong><span>${this.escape(job.state)}</span></div>
        <p>${this.escape(job.message || '')}</p>
        <div class="import-job-files">${(job.files || []).map(file => `<span>${this.escape(file)}</span>`).join('')}</div>
        ${job.error ? `<details><summary>Show error</summary><pre>${this.escape(job.error)}</pre></details>` : ''}
      </article>`;
    }).join('') : '<div class="import-empty-panel">No document intake jobs yet.</div>';
    for (const job of jobs) {
      const prior = this.lastStates.get(job.id);
      if (prior && prior !== job.state && job.state === 'complete') {
        this.notify('Documents are indexed and published to GitHub.'); this.refreshed();
      }
      this.lastStates.set(job.id, job.state);
    }
  }

  schedulePoll(jobs) {
    clearTimeout(this.pollTimer);
    if (jobs.some(job => ['queued','running'].includes(job.state))) {
      this.pollTimer = setTimeout(() => this.load().catch(error => this.notify(error.message)), 2500);
    }
  }

  bind() {
    this.$('import-files').addEventListener('change', () => this.renderFiles());
    this.$('import-folder').addEventListener('change', () => this.validate());
    this.$('import-form').addEventListener('submit', event => this.submit(event));
    this.$('import-refresh').addEventListener('click', () => this.load().catch(error => this.notify(error.message)));
  }
}
