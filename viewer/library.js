/* Personal data lives in the local service database, not the browser cache. */
window.PersonalLibrary = class {
  constructor(hooks) {
    this.hooks = hooks;
    this.id = crypto.randomUUID(); this.revision = 0; this.items = [];
    this.ready = false; this.dirty = false; this.version = 0; this.awaiting = false;
    this.key = 'mafn-active-conversation-v1';
    this.escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  async request(url, body) {
    const response = await fetch(url, body === undefined ? {} : {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) { const error = new Error(data.error || 'Local storage unavailable'); error.status = response.status; throw error; }
    return data;
  }

  status(text, failed = false) {
    const node = document.getElementById('save-status');
    node.textContent = text; node.classList.toggle('save-error', failed);
  }

  async init() {
    try {
      await this.refresh();
      this.ready = true;
      let previous;
      try { previous = localStorage.getItem(this.key); } catch {}
      const requested = new URLSearchParams(location.search).get('chat');
      const id = requested || (this.items.some(item => item.id === previous) ? previous : previous === 'new' ? null : this.items.find(item => item.kind === 'conversation')?.id);
      if (id) await this.open(id, false);
      else this.status('Ready to save on this Mac');
    } catch (error) {
      this.status('Saving unavailable. Reconnect the local service and retry.', true);
      this.hooks.notify(error.message);
    }
    document.getElementById('chat-history').addEventListener('change', event => {
      if (event.target.value) this.open(event.target.value).catch(error => this.hooks.notify(error.message));
    });
    document.getElementById('chat-title').addEventListener('input', () => this.schedule());
    document.getElementById('save-chat').addEventListener('click', () => this.flush().catch(error => this.hooks.notify(error.message)));
    document.getElementById('export-chat').addEventListener('click', () => this.exportChat());
    document.getElementById('refresh-saved').addEventListener('click', () => this.refresh().catch(error => this.hooks.notify(error.message)));
    document.getElementById('export-library').addEventListener('click', () => this.exportAll());
    document.getElementById('saved-items').addEventListener('click', event => this.savedAction(event));
    window.addEventListener('beforeunload', event => {
      if (this.dirty || this.saving) { event.preventDefault(); event.returnValue = ''; }
    });
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && this.dirty && !this.awaiting) this.flush().catch(() => {});
    });
  }

  remember(value = this.id) { try { localStorage.setItem(this.key, value); } catch {} }

  async refresh() {
    this.items = (await this.request('/api/library')).items;
    this.render();
  }

  render() {
    const history = document.getElementById('chat-history');
    history.innerHTML = '<option value="">New conversation</option>' + this.items.filter(item => item.kind === 'conversation').map(item => `<option value="${item.id}">${this.escape(item.title)}</option>`).join('');
    history.value = this.revision ? this.id : '';
    document.getElementById('saved-items').innerHTML = ['view','conversation','source','answer','calculation'].map(kind => {
      const items = this.items.filter(item => item.kind === kind);
      const heading = {view:'Saved filter views',conversation:'Conversations',source:'Saved passages',answer:'Saved answers',calculation:'Saved calculations'}[kind];
      return `<section class="saved-group"><h3>${heading} <span>${items.length}</span></h3>${items.length ? items.map(item => `<article class="saved-card" data-saved-id="${item.id}"><div><h4>${this.escape(item.title)}</h4><p>${this.escape(new Date(item.updated_at).toLocaleString())}</p></div><div class="saved-actions"><button class="quiet-button" data-action="open">Open</button><button class="quiet-button" data-action="export">Export</button><button class="quiet-button" data-action="delete">Delete</button></div></article>`).join('') : '<p class="small-muted">Nothing saved here yet.</p>'}</section>`;
    }).join('');
  }

  schedule() {
    if (!this.ready) return;
    this.dirty = true; this.version++;
    if (this.awaiting) return;
    this.status('Unsaved changes…');
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.flush().catch(() => {}), 600);
  }

  async flush() {
    clearTimeout(this.timer);
    if (this.awaiting) return;
    if (this.saving) { await this.saving; if (this.dirty) return this.flush(); return; }
    if (!this.ready) { await this.refresh(); this.ready = true; }
    const payload = this.hooks.capture();
    if (!payload.turns.length && !payload.draft && !payload.pins.length && payload.title === 'New conversation') {
      this.dirty = false; this.status('Ready to save on this Mac'); return;
    }
    const version = this.version;
    this.status('Saving…');
    this.saving = (async () => {
      let record;
      try {
        record = await this.request('/api/library/items', {item_id:this.id, kind:'conversation', revision:this.revision, payload});
      } catch (error) {
        if (error.status !== 409) throw error;
        // Preserve both editors' work when a second tab changes the same chat.
        this.id = crypto.randomUUID(); this.revision = 0;
        payload.title = payload.title.slice(0,170) + ' (another tab copy)';
        record = await this.request('/api/library/items', {item_id:this.id, kind:'conversation', revision:0, payload});
        document.getElementById('chat-title').value = payload.title;
        this.hooks.notify('This chat changed in another tab. Both versions are saved separately.');
      }
      this.revision = record.revision; this.remember();
      this.dirty = version !== this.version;
      this.status('Saved on this Mac');
      await this.refresh(); this.hooks.url();
    })();
    try { await this.saving; }
    catch (error) { this.dirty = true; this.status(`Not saved: ${error.message}`, true); throw error; }
    finally { this.saving = null; }
    if (this.dirty) return this.flush();
  }

  async open(id, navigate = true) {
    if (this.awaiting) throw new Error('The current answer is still being saved. Wait for it to finish.');
    if (this.dirty || this.saving) await this.flush();
    const record = await this.request('/api/library/items/' + encodeURIComponent(id));
    this.id = record.id; this.revision = record.revision; this.dirty = false;
    document.getElementById('chat-title').value = record.title;
    this.remember(); this.hooks.restore(record.payload, navigate);
    this.status('Saved conversation restored · source status is checked when opened');
    this.render();
    if (record.payload.turns.some(turn => turn.pending)) {
      this.setAwaiting(true); this.watch();
    }
  }

  setAwaiting(value) {
    this.awaiting = value;
    this.hooks.busy(value);
    document.getElementById('chat-history').disabled = value;
    document.getElementById('new-chat').disabled = value;
    document.getElementById('save-chat').disabled = value;
    if (value) this.status('Question saved · the reply will save automatically');
  }

  async reconcile() {
    const record = await this.request('/api/library/items/' + this.id);
    this.revision = record.revision;
    this.hooks.turns(record.payload.turns);
    if (record.payload.turns.some(turn => turn.pending)) return false;
    this.setAwaiting(false);
    this.status('Saved on this Mac');
    await this.refresh();
    return true;
  }

  watch() {
    clearTimeout(this.poll);
    this.poll = setTimeout(async () => {
      try { if (!(await this.reconcile())) this.watch(); }
      catch (error) {
        if (error.status === 404) { this.setAwaiting(false); this.status('This conversation was removed in another tab. Export this local copy or start a new chat.', true); }
        else { this.status('Cannot check the reply yet. The question is saved on this Mac.', true); this.watch(); }
      }
    }, 2000);
  }

  async newChat() {
    if (this.awaiting) return;
    if (this.dirty || this.saving) await this.flush();
    this.id = crypto.randomUUID(); this.revision = 0; this.dirty = false;
    this.remember('new');
    document.getElementById('chat-title').value = '';
    this.render(); this.status('Previous chats are in Saved');
  }

  async saveItem(kind, payload) {
    if (kind === 'source') {
      for (const item of this.items.filter(item => item.kind === kind)) {
        const stored = await this.request('/api/library/items/' + item.id);
        if (stored.payload.hit?.source_path === payload.hit.source_path && stored.payload.hit?.chunk_id === payload.hit.chunk_id) {
          this.hooks.notify('This passage is already in Saved.'); return;
        }
      }
    }
    await this.request('/api/library/items', {item_id:crypto.randomUUID(), kind, revision:0, payload});
    await this.refresh(); this.hooks.notify(kind === 'calculation' ? 'Calculation saved with its recipe and source.' : kind === 'answer' ? 'Answer saved.' : 'Passage saved with its source citation.');
  }

  download(name, value, type = 'application/json') {
    const url = URL.createObjectURL(new Blob([type === 'application/json' ? JSON.stringify(value, null, 2) : value], {type}));
    const link = document.createElement('a'); link.href = url; link.download = name; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  exportChat() {
    const payload = this.hooks.capture();
    this.download('mafn-conversation.json', {schema_version:1, kind:'conversation', exported_at:new Date().toISOString(), payload});
  }

  async exportAll() {
    try {
      if (this.dirty && !this.awaiting) await this.flush();
      await this.refresh();
      const items = await Promise.all(this.items.map(item => this.request('/api/library/items/' + item.id)));
      this.download('mafn-saved-library.json', {schema_version:1, exported_at:new Date().toISOString(), items});
    } catch (error) { this.hooks.notify(error.message); }
  }

  async savedAction(event) {
    const button = event.target.closest('[data-action]');
    const card = button?.closest('[data-saved-id]');
    if (!card) return;
    try {
      const item = await this.request('/api/library/items/' + card.dataset.savedId);
      if (button.dataset.action === 'export') this.download('mafn-' + item.kind + '.json', {schema_version:1,...item});
      else if (button.dataset.action === 'delete') {
        if (item.id === this.id && this.awaiting) throw new Error('Wait for the current answer before deleting its conversation.');
        const dialog = document.getElementById('delete-saved-dialog');
        dialog.returnValue = '';
        document.getElementById('delete-saved-title').textContent = item.title;
        dialog.showModal();
        dialog.addEventListener('close', async () => {
          if (dialog.returnValue !== 'delete') return;
          try {
            await this.request('/api/library/delete', {item_id:item.id, revision:item.revision});
            if (item.id === this.id) {
              this.dirty = false; await this.newChat(); this.hooks.restore({turns:[],pins:[],draft:''}, false);
            }
            await this.refresh();
          } catch (error) { this.hooks.notify(error.message); }
        }, {once:true});
      } else if (item.kind === 'view') this.hooks.view(item.payload);
      else if (item.kind === 'conversation') await this.open(item.id);
      else if (item.kind === 'source') this.hooks.source(item.payload.hit);
      else if (item.kind === 'calculation') this.hooks.calculation(item.payload.result);
      else this.hooks.answer(item.payload);
    } catch (error) { this.hooks.notify(error.message); }
  }
};
