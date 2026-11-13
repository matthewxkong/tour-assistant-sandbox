"""Inspect synthetic tour options and locally saved intent state."""
import argparse
import json
import sqlite3
from pathlib import Path

from core import options
from server import LOGICAL_NOW, SLOTS
from store import IntentStore
from review import review_options


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('options', help='list current synthetic fixture options')
    review = sub.add_parser('review', help='explain current options against preferences')
    review.add_argument('--listing-id')
    review.add_argument('--provider')
    review.add_argument('--start-at', type=int)
    review.add_argument('--end-at', type=int)
    review.add_argument('--max-options', type=int)
    status = sub.add_parser('status', help='inspect one locally saved intent')
    status.add_argument('key')
    status.add_argument('--actor', required=True)
    status.add_argument('--db', default='intents.sqlite3')
    args = parser.parse_args(argv)
    if args.command == 'options':
        result = {'logical_now': LOGICAL_NOW, 'options': options(SLOTS, LOGICAL_NOW)}
    elif args.command == 'review':
        prefs = {key: getattr(args, key) for key in ('listing_id', 'provider', 'start_at', 'end_at', 'max_options')
                 if getattr(args, key) is not None}
        try:
            result = review_options(SLOTS, LOGICAL_NOW, prefs)
        except ValueError as error:
            parser.error(str(error))
    else:
        if not Path(args.db).is_file():
            parser.error('Intent database does not exist')
        try:
            store = IntentStore(args.db, read_only=True)
            result = {'intent': store.status(args.key, args.actor),
                      'events': store.events(args.key, args.actor)}
        except (ValueError, sqlite3.Error, OSError) as error:
            parser.error(str(error))
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
