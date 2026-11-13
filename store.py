"""Durable sandbox intents. All provider outcomes are explicit simulations."""
from contextlib import contextmanager
import sqlite3
import time
from pathlib import Path

from core import _label


SOURCES = {'web', 'mobile', 'assistant'}


class IntentStore:
    def __init__(self, path, clock=time.time, *, read_only=False):
        self.path = str(path)
        self.clock = clock
        self.read_only = read_only
        if read_only:
            return
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS intents(
                key TEXT PRIMARY KEY, actor TEXT NOT NULL, listing TEXT NOT NULL,
                slot TEXT NOT NULL, provider TEXT NOT NULL, source TEXT NOT NULL,
                created REAL NOT NULL, status TEXT NOT NULL, receipt TEXT)''')
            db.execute('''CREATE TABLE IF NOT EXISTS history(
                id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL, at REAL NOT NULL,
                status TEXT NOT NULL, reason TEXT NOT NULL)''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(Path(self.path).resolve().as_uri() + '?mode=ro', uri=True) if self.read_only else sqlite3.connect(self.path)
        try:
            with db:
                yield db
        finally:
            db.close()

    def _row(self, key):
        with self.connect() as db:
            row = db.execute('SELECT key,actor,listing,slot,provider,source,created,status,receipt FROM intents WHERE key=?', (key,)).fetchone()
        return dict(zip(('key', 'actor', 'listing', 'slot', 'provider', 'source', 'created', 'status', 'receipt'), row)) if row else None

    def propose(self, key, actor, source, option):
        key = _label(key, 'idempotency key', 100)
        if len(key) < 8:
            raise ValueError('Idempotency key must have at least eight characters')
        actor = _label(actor, 'actor', 80)
        if source not in SOURCES:
            raise ValueError('Unknown source type')
        if not isinstance(option, dict) or not all(isinstance(option.get(field), str) for field in ('listing_id', 'slot_id', 'provider')):
            raise ValueError('A current tour option is required')
        listing, slot, provider = (_label(option[field], field) for field in ('listing_id', 'slot_id', 'provider'))
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT actor,listing,slot,provider,source FROM intents WHERE key=?', (key,)).fetchone()
            if prior:
                if prior != (actor, listing, slot, provider, source):
                    raise ValueError('Idempotency key conflicts with another intent')
                return self._row(key)
            db.execute('INSERT INTO intents VALUES(?,?,?,?,?,?,?,?,NULL)',
                       (key, actor, listing, slot, provider, source, self.clock(), 'PROPOSED'))
            db.execute('INSERT INTO history(key,at,status,reason) VALUES(?,?,?,?)',
                       (key, self.clock(), 'PROPOSED', 'Read-only suggestion recorded'))
        return self._row(key)

    def approve(self, key, actor, consent):
        if consent is not True:
            raise ValueError('Explicit human consent is required')
        actor = _label(actor, 'actor', 80)
        with self.connect() as db:
            changed = db.execute("UPDATE intents SET status='PENDING_PROVIDER' WHERE key=? AND actor=? AND status='PROPOSED'", (key, actor)).rowcount
            if changed != 1:
                raise ValueError('Intent unavailable for approval')
            db.execute('INSERT INTO history(key,at,status,reason) VALUES(?,?,?,?)',
                       (key, self.clock(), 'PENDING_PROVIDER', 'Human consent recorded in local simulation'))
        return self._row(key)

    def provider_result(self, key, outcome, receipt=None):
        if outcome not in ('confirmed', 'unknown', 'failed'):
            raise ValueError('Invalid simulated provider outcome')
        if outcome == 'confirmed':
            receipt = _label(receipt, 'provider receipt', 120)
        elif receipt is not None:
            raise ValueError('Only confirmed outcomes may carry a receipt')
        status = {'confirmed': 'CONFIRMED', 'unknown': 'RECONCILING', 'failed': 'FAILED'}[outcome]
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT status,receipt FROM intents WHERE key=?', (key,)).fetchone()
            if row and row == (status, receipt) and status in ('CONFIRMED', 'FAILED'):
                return self._row(key)
            if not row or row[0] not in ('PENDING_PROVIDER', 'RECONCILING'):
                raise ValueError('Intent unavailable for provider update')
            if row[0] == 'RECONCILING' and outcome == 'unknown':
                return self._row(key)
            db.execute('UPDATE intents SET status=?,receipt=? WHERE key=?', (status, receipt, key))
            db.execute('INSERT INTO history(key,at,status,reason) VALUES(?,?,?,?)',
                       (key, self.clock(), status, 'Simulated provider outcome: ' + outcome))
        return self._row(key)

    def cancel_proposal(self, key, actor):
        """Withdraw an unapproved proposal; never claim a remote booking was cancelled."""
        actor = _label(actor, 'actor', 80)
        with self.connect() as db:
            changed = db.execute("UPDATE intents SET status='CANCELLED' WHERE key=? AND actor=? AND status='PROPOSED'",
                                 (key, actor)).rowcount
            if changed != 1:
                raise ValueError('Only an owned unapproved proposal can be withdrawn')
            db.execute('INSERT INTO history(key,at,status,reason) VALUES(?,?,?,?)',
                       (key, self.clock(), 'CANCELLED', 'Human withdrew an unapproved local proposal'))
        return self._row(key)

    def status(self, key, actor):
        actor = _label(actor, 'actor', 80)
        row = self._row(key)
        if not row or row['actor'] != actor:
            raise ValueError('Intent unavailable')
        return row

    def events(self, key, actor):
        self.status(key, actor)
        with self.connect() as db:
            rows = db.execute('SELECT at,status,reason FROM history WHERE key=? ORDER BY id', (key,)).fetchall()
        return [dict(zip(('at', 'status', 'reason'), row)) for row in rows]
