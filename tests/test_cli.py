import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from store import IntentStore


ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def test_listing_options_cli(self):
        all_rows = json.loads(self.run_cli('options').stdout)['options']
        listing = all_rows[0]['listing_id']
        filtered = self.run_cli('options', '--listing-id', listing)
        self.assertEqual(filtered.returncode, 0, filtered.stderr)
        self.assertEqual(json.loads(filtered.stdout)['options'],
                         [row for row in all_rows if row['listing_id'] == listing])
        missing = self.run_cli('options', '--listing-id', 'missing')
        self.assertEqual(json.loads(missing.stdout)['options'], [])

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
