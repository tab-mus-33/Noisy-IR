"""
Pre-warms the synonym cache for all 30 topic materials.

Runs PubChem + Materials Project lookups for every name variant in the
topic list and stores results in the synonym cache. When the full enrichment
pipeline runs later, all topic-relevant terms will be served from cache
rather than making live API calls.

Safe to run at any time — already-cached entries are skipped.
"""

from matsci.config import CONFIG
from matsci.enrichment.pubchem_client import get_synonyms as pubchem_synonyms
from matsci.enrichment.matproj_client import formula_to_synonyms as mp_synonyms
from matsci.enrichment.synonym_cache import make_synonym_cache, normalise_key
from matsci.topics.topic_builder import TOPICS
from tqdm import tqdm


def _all_topic_names() -> list[str]:
    """Extract every unique name variant across all 30 topics."""
    names: set[str] = set()
    for _, name_a, name_b, title_a, _ in TOPICS:
        names.add(name_a)
        names.add(name_b)
        # also extract any additional names embedded in the title
        for word in title_a.split():
            if len(word) > 3:
                names.add(word.lower())
    return sorted(names)


def warm(cache_path: str | None = None) -> None:
    cache = make_synonym_cache(cache_path or CONFIG["synonym_cache_path"])

    names = _all_topic_names()
    print(f"Pre-warming synonym cache for {len(names)} name variants")
    print(f"Cache: {CONFIG['synonym_cache_path']}\n")

    for name in tqdm(names, unit="entity"):
        key = normalise_key(name)
        if key in cache:
            continue

        synonyms: list[str] = []

        pc = pubchem_synonyms(name)
        synonyms.extend(pc)

        mp = mp_synonyms(name)
        for s in mp:
            if s not in synonyms:
                synonyms.append(s)

        cache.set(key, synonyms)

    print(f"\nDone. {len(cache)} entries in cache.")


if __name__ == "__main__":
    warm()
