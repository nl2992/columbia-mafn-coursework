"""Durable personal library, independent of rebuildable retrieval generations."""
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone


class LibraryConflict(ValueError):
    pass


class LibraryStore:
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
                raise RuntimeError('Unsupported personal library version; preserve the database')
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('''CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL,
                revision INTEGER NOT NULL, payload TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted INTEGER NOT NULL DEFAULT 0)''')
            db.execute('PRAGMA user_version=1')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def valid_id(value):
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value):
            raise ValueError('Invalid saved item ID')
        return value

    @staticmethod
    def timestamp():
        return datetime.now(timezone.utc).isoformat()

    def list(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute(
                'SELECT id,kind,title,revision,created_at,updated_at FROM items WHERE deleted=0 ORDER BY updated_at DESC,id')]

    def get(self, item_id):
        self.valid_id(item_id)
        with self.connect() as db:
            row = db.execute('SELECT * FROM items WHERE id=? AND deleted=0', (item_id,)).fetchone()
        if row is None:
            raise KeyError('Saved item not found')
        result = dict(row)
        result['payload'] = json.loads(result['payload'])
        return result

    def save(self, item_id, kind, revision, payload):
        self.valid_id(item_id)
        if kind not in ('conversation', 'source', 'answer', 'calculation', 'view') or not isinstance(payload, dict):
            raise ValueError('Invalid saved item')
        if type(revision) is not int or revision < 0:
            raise ValueError('Invalid saved item revision')
        title = payload.get('title')
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200:
            raise ValueError('Use a title between 1 and 200 characters')
        if kind == 'view':
            filters = payload.get('filters', {})
            allowed = {'course', 'term', 'content_type', 'lecturer', 'file_type', 'review'}
            if (not isinstance(filters, dict) or set(filters)-allowed
                    or any(not isinstance(v, str) or len(v)>500 for v in filters.values())
                    or payload.get('mode') not in ('hybrid','lexical','semantic')
                    or not isinstance(payload.get('query'), str) or len(payload['query'])>2000):
                raise ValueError('Invalid saved filter view')
        if kind == 'conversation':
            turns = payload.get('turns')
            if not isinstance(turns, list) or len(turns) > 1000:
                raise ValueError('A conversation can hold up to 1,000 turns; start a new chat')
            ids = []
            for turn in turns:
                if not isinstance(turn, dict) or not isinstance(turn.get('query'), str) or len(turn['query']) > 2000:
                    raise ValueError('Invalid conversation turn')
                ids.append(self.valid_id(turn.get('id')))
            if len(ids) != len(set(ids)):
                raise ValueError('Duplicate conversation turn IDs')
        raw = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        if len(raw.encode()) > 8_000_000:
            raise ValueError('Saved item exceeds 8 MB; export this chat and start a new one')
        stamp = self.timestamp()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT revision,deleted,kind FROM items WHERE id=?', (item_id,)).fetchone()
            if row and (row['deleted'] or row['revision'] != revision or row['kind'] != kind):
                raise LibraryConflict('This item changed in another tab. Your local copy has not overwritten it.')
            if row is None and revision != 0:
                raise LibraryConflict('Saved item is no longer available')
            db.execute('''INSERT INTO items (id,kind,title,revision,payload,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                title=excluded.title, revision=excluded.revision, payload=excluded.payload, updated_at=excluded.updated_at''',
                (item_id, kind, title.strip(), revision+1, raw, stamp, stamp))
        return self.get(item_id)

    def delete(self, item_id, revision):
        self.valid_id(item_id)
        if type(revision) is not int:
            raise ValueError('Invalid saved item revision')
        with self.connect() as db:
            changed = db.execute('UPDATE items SET deleted=1,revision=revision+1,updated_at=? WHERE id=? AND revision=? AND deleted=0',
                                 (self.timestamp(), item_id, revision)).rowcount
            if not changed:
                raise LibraryConflict('This item changed or was already deleted; refresh Saved')
        return {'deleted': True}

    def begin_turn(self, item_id, turn_id, query):
        """Claim a persisted question once before inference, including across tabs."""
        self.valid_id(item_id); self.valid_id(turn_id)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM items WHERE id=? AND kind=? AND deleted=0', (item_id, 'conversation')).fetchone()
            if not row:
                raise ValueError('Save the conversation before asking')
            payload = json.loads(row['payload'])
            turn = next((t for t in payload['turns'] if t['id'] == turn_id), None)
            if not turn or turn['query'] != query or not turn.get('pending') or turn.get('running'):
                raise ValueError('Question is missing, already running, or completed')
            turn['running'] = True
            db.execute('UPDATE items SET payload=?,revision=revision+1,updated_at=? WHERE id=?',
                       (json.dumps(payload), self.timestamp(), item_id))
        return turn['query']

    def finish_turn(self, item_id, turn_id, data=None, error=None):
        """Persist replies even if the requesting browser closes; never revive deleted chats."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM items WHERE id=? AND deleted=0', (item_id,)).fetchone()
            if not row:
                return None
            payload = json.loads(row['payload'])
            turn = next((t for t in payload['turns'] if t['id'] == turn_id), None)
            if not turn:
                return None
            turn.update(pending=False, running=False)
            if payload.get('draft') == turn['query']:
                payload['draft'] = ''
            if data is not None:
                turn['data'] = data
            if error:
                turn['error'] = error
            revision = row['revision']+1
            db.execute('UPDATE items SET payload=?,revision=?,updated_at=? WHERE id=?',
                       (json.dumps(payload), revision, self.timestamp(), item_id))
        return revision

    def recover_pending(self):
        """Called once at server startup: interrupted jobs are saved as retryable questions."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for row in db.execute("SELECT * FROM items WHERE kind='conversation' AND deleted=0").fetchall():
                payload = json.loads(row['payload'])
                changed = False
                for turn in payload['turns']:
                    if turn.get('pending'):
                        turn.update(pending=False, running=False, error='The service restarted before this reply completed. Your question is saved; ask it again to retry.')
                        changed = True
                if changed:
                    db.execute('UPDATE items SET payload=?,revision=revision+1,updated_at=? WHERE id=?',
                               (json.dumps(payload), self.timestamp(), row['id']))
