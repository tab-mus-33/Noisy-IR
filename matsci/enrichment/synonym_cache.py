"""
Synonym cache: reuses entity_cache infrastructure for synonym lookups.

Keyed by normalised entity string (lowercased, stripped).
Values are lists of synonym strings.
"""

from matsci.ner.entity_cache import JsonCache


def make_synonym_cache(path: str) -> JsonCache:
    return JsonCache(path)


def normalise_key(entity: str) -> str:
    """Consistent cache key from an entity string."""
    return entity.lower().strip()
