import json
from contextlib import closing
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from store import IntentStore


ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def test_status_does_not_initialize_or_repair_existing_files(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'inspect.db'
            unrelated = Path(temp) / 'unrelated.db'
            with closing(sqlite3.connect(unrelated)) as connection:
                connection.execute('CREATE TABLE other(value TEXT)')
                connection.commit()
            for content in (b'', b'not a SQLite database', unrelated.read_bytes()):
                with self.subTest(content=content):
                    path.write_bytes(content)
                    result = self.run_cli('status', 'request-001', '--actor', 'person', '--db', str(path))
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, '')
                    self.assertNotIn('Traceback', result.stderr)
                    self.assertEqual(path.read_bytes(), content)

    def test_valid_status_inspection_preserves_bytes_and_actor_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'intents.db'
            store = IntentStore(path, lambda: 100)
            store.propose('request-001', 'person', 'web',
                          {'listing_id': 'home-1', 'slot_id': 'one', 'provider': 'demo'})
            before = path.read_bytes()
            result = self.run_cli('status', 'request-001', '--actor', 'person', '--db', str(path))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(json.loads(result.stdout)['events']), 1)
            denied = self.run_cli('status', 'request-001', '--actor', 'other', '--db', str(path))
            self.assertEqual(denied.returncode, 2)
            with self.assertRaisesRegex(sqlite3.OperationalError, 'readonly'):
                IntentStore(path, read_only=True).propose('request-002', 'person', 'web',
                    {'listing_id': 'home-1', 'slot_id': 'one', 'provider': 'demo'})
            self.assertEqual(path.read_bytes(), before)
    def run_cli(self, *args):
        return subprocess.run([sys.executable, 'cli.py', *args], cwd=ROOT, capture_output=True, text=True)

    def test_options_and_existing_intent(self):
        listed = self.run_cli('options')
        self.assertEqual(listed.returncode, 0)
        self.assertGreater(len(json.loads(listed.stdout)['options']), 0)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'intents.db'
            self.assertNotEqual(self.run_cli('status', 'request-001', '--actor', 'person', '--db', str(path)).returncode, 0)
            self.assertFalse(path.exists())
            store = IntentStore(path, lambda: 100)
            store.propose('request-001', 'person', 'web', {'listing_id': 'home-1', 'slot_id': 'one', 'provider': 'demo'})
            shown = self.run_cli('status', 'request-001', '--actor', 'person', '--db', str(path))
            self.assertEqual(shown.returncode, 0)
            self.assertEqual(json.loads(shown.stdout)['intent']['status'], 'PROPOSED')
