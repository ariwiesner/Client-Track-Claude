import re

from rapidfuzz import fuzz, process

import config


def extract_candidate_name(title, system):
    """Pull the likely client-name substring out of a window title, per the
    tracked system's configured extraction method. Returns None if it can't
    extract anything meaningful.
    """
    if system['title_pattern_type'] == 'regex':
        pattern = system.get('title_regex')
        if not pattern:
            return None
        match = re.search(pattern, title)
        if not match:
            return None
        try:
            return match.group('client').strip()
        except IndexError:
            return None  # regex has no 'client' named group

    delimiter = system.get('title_delimiter') or ''
    if not delimiter:
        return title.strip() or None
    parts = title.split(delimiter)
    index = system.get('title_delimiter_index', 0)
    if index >= len(parts):
        return None
    candidate = parts[index].strip()
    return candidate or None


def match_client(candidate, clients):
    """Fuzzy-match a candidate name string against known clients.
    Returns the matching client dict, or None if nothing clears the
    confidence threshold.
    """
    if not candidate or not clients:
        return None

    names = {c['name']: c for c in clients}
    best = process.extractOne(candidate, names.keys(), scorer=fuzz.WRatio)
    if not best:
        return None
    name, score, _ = best
    if score < config.MATCH_CONFIDENCE_THRESHOLD:
        return None
    return names[name]
