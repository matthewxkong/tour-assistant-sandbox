import unittest

from core import options, parse_suggestion


SLOTS = [
    {'listing_id': 'home-1', 'slot_id': 'morning', 'provider': 'demo-a', 'start_at': 300,
     'expires_at': 200, 'version': 1},
    {'listing_id': 'home-1', 'slot_id': 'morning', 'provider': 'demo-a', 'start_at': 300,
     'expires_at': 80, 'version': 2},
    {'listing_id': 'home-1', 'slot_id': 'afternoon', 'provider': 'demo-b', 'start_at': 500,
     'expires_at': 250, 'version': 1},
]


class DiscoveryTests(unittest.TestCase):
    def test_padded_listing_filter_matches_the_normalized_listing(self):
        rows = [{'listing_id': ' home-a ', 'slot_id': 'one', 'provider': 'demo',
                 'start_at': 300, 'expires_at': 200, 'version': 1}]
        expected = options(rows, 100, 'home-a')
        self.assertEqual(len(expected), 1)
        self.assertEqual(options(rows, 100, ' home-a '), expected)
        self.assertEqual(rows[0]['listing_id'], ' home-a ')
        with self.assertRaises(ValueError):
            options(rows, 100, '   ')
    def test_latest_version_can_revoke_cached_availability(self):
        self.assertEqual([row['slot_id'] for row in options(SLOTS, 100)], ['afternoon'])

    def test_model_can_only_propose_current_option(self):
        available = options(SLOTS, 100)
        proposal = parse_suggestion('{"listing_id":"home-1","slot_id":"afternoon","reason":"Soon"}', available)
        self.assertEqual(proposal['authority'], 'proposal-only')
        for raw in ('{"listing_id":"home-1","slot_id":"morning","reason":"Soon"}',
                    '{"listing_id":"home-1","slot_id":"afternoon","reason":"Soon","consent":true}',
                    '{"listing_id":"home-1","slot_id":"afternoon","reason":"a","reason":"b"}'):
            with self.assertRaises(ValueError):
                parse_suggestion(raw, available)
