"""Read-only tour discovery and untrusted suggestion validation."""
import json


def _label(value, name, limit=80):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit or any(ord(ch) < 32 for ch in value):
        raise ValueError(name + ' must be bounded nonblank text')
    return value.strip()


def _time(value, name):
    if type(value) is not int or not 0 <= value <= 4102444800:
        raise ValueError(name + ' must be a supported Unix second')
    return value


def options(rows, now, listing_id=None):
    """Return current read-only options; cached availability is never confirmation."""
    _time(now, 'now')
    if listing_id is not None:
        listing_id = _label(listing_id, 'listing_id')
    if not isinstance(rows, list) or len(rows) > 500:
        raise ValueError('Expected at most 500 slot snapshots')
    latest = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'listing_id', 'slot_id', 'provider', 'start_at', 'expires_at', 'version'}:
            raise ValueError('Invalid slot snapshot')
        listing = _label(row['listing_id'], 'listing_id')
        slot = _label(row['slot_id'], 'slot_id')
        provider = _label(row['provider'], 'provider')
        start = _time(row['start_at'], 'start_at')
        expires = _time(row['expires_at'], 'expires_at')
        version = row['version']
        if type(version) is not int or not 1 <= version <= 1000000 or expires > start:
            raise ValueError('Invalid slot version or expiry')
        key = (listing, slot)
        normalized = {'listing_id': listing, 'slot_id': slot, 'provider': provider,
                      'start_at': start, 'expires_at': expires, 'version': version}
        prior = latest.get(key)
        if prior and prior['version'] == version and prior != normalized:
            raise ValueError('Conflicting equal-version snapshot')
        if prior is None or version > prior['version']:
            latest[key] = normalized
    current = [row for row in latest.values() if row['expires_at'] > now and row['start_at'] > now
               and (listing_id is None or row['listing_id'] == listing_id)]
    return sorted(current, key=lambda row: (row['start_at'], row['listing_id'], row['slot_id']))


def parse_suggestion(raw, available):
    """Treat a model response as a proposed selection, never booking authority."""
    if not isinstance(raw, str) or len(raw.encode('utf-8')) > 4096:
        raise ValueError('Suggestion must be bounded JSON text')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate suggestion field')
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (RecursionError, json.JSONDecodeError) as error:
        raise ValueError('Malformed suggestion JSON') from error
    if not isinstance(value, dict) or set(value) != {'listing_id', 'slot_id', 'reason'}:
        raise ValueError('Suggestion may only choose a listing and slot with a reason')
    listing = _label(value['listing_id'], 'listing_id')
    slot = _label(value['slot_id'], 'slot_id')
    reason = _label(value['reason'], 'reason', 240)
    match = next((row for row in available if row['listing_id'] == listing and row['slot_id'] == slot), None)
    if match is None:
        raise ValueError('Suggested slot is not in current availability')
    return {'option': match.copy(), 'reason': reason, 'authority': 'proposal-only'}
