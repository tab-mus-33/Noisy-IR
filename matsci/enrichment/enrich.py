"""
Orchestrates concept enrichment: for each document, maps material entity
mentions to synonym tokens and appends them to the document text.

This is the materials science equivalent of the Wikifier step in the thesis.

Input:  raw document {"docno": ..., "title": ..., "abstract": ...}
Output: enriched document with synonym tokens appended to abstract text

Synonym tokens use the mat_ prefix to distinguish them from natural text:
  "corundum ... alumina ..."  →  "corundum ... alumina ... mat_Al2O3 mat_aluminum_oxide"

Two-source strategy:
  1. PubChem (primary) — broad coverage of inorganic and organic compounds
  2. Materials Project (secondary) — formula variants for crystalline inorganics
"""

import json
import re
from pathlib import Path

from tqdm import tqdm

from matsci.config import CONFIG
from matsci.enrichment.pubchem_client import get_synonyms as pubchem_synonyms
from matsci.enrichment.matproj_client import formula_to_synonyms as mp_synonyms
from matsci.enrichment.synonym_cache import make_synonym_cache, normalise_key
from matsci.ner.entity_cache import JsonCache


_PREFIX = CONFIG["synonym_token_prefix"]   # "mat_"


def _to_token(synonym: str) -> str:
    """Convert a synonym string to a retrieval token."""
    return _PREFIX + re.sub(r"\s+", "_", synonym.strip().lower())


def get_synonyms_for_entity(
    entity: str,
    syn_cache: JsonCache,
) -> list[str]:
    """
    Look up synonyms for one material entity, with caching.

    Queries PubChem first, then Materials Project for formula variants.
    """
    key = normalise_key(entity)
    if key in syn_cache:
        return syn_cache.get(key)

    synonyms: list[str] = []

    # PubChem lookup
    pc = pubchem_synonyms(entity)
    synonyms.extend(pc)

    # Materials Project lookup for formula-like entities
    # (heuristic: contains digits or looks like a formula)
    if re.search(r"\d", entity) or re.match(r"^[A-Z][a-z]?", entity):
        mp = mp_synonyms(entity)
        for s in mp:
            if s not in synonyms:
                synonyms.append(s)

    # Deduplicate and filter out the entity itself
    entity_lower = entity.lower()
    seen = {entity_lower}
    unique = []
    for s in synonyms:
        s_lower = s.lower()
        if s_lower not in seen:
            seen.add(s_lower)
            unique.append(s)

    syn_cache.set(key, unique)
    return unique


def enrich_document(
    doc: dict,
    ner_cache: JsonCache,
    syn_cache: JsonCache,
    text_field: str = "abstract",
) -> dict:
    """
    Return a copy of doc with synonym tokens appended to text_field.

    If no NER entities are found, returns doc unchanged.
    """
    entities: list[str] = ner_cache.get(doc["docno"]) or []
    if not entities:
        return dict(doc)

    tokens: list[str] = []
    for entity in entities:
        synonyms = get_synonyms_for_entity(entity, syn_cache)
        tokens.extend(_to_token(s) for s in synonyms)

    if not tokens:
        return dict(doc)

    enriched = dict(doc)
    enriched[text_field] = doc.get(text_field, "") + " " + " ".join(tokens)
    return enriched


def enrich_corpus(
    corpus_path: str | Path,
    output_path: str | Path,
    ner_cache_path: str | Path | None = None,
    syn_cache_path: str | Path | None = None,
) -> int:
    """
    Read corpus JSONL, enrich each document, write enriched JSONL.

    Parameters
    ----------
    corpus_path     : input JSONL (raw corpus from fetch_arxiv.py)
    output_path     : where to write enriched JSONL
    ner_cache_path  : NER results cache (from matbert_ner.py)
    syn_cache_path  : synonym lookup cache

    Returns
    -------
    Number of documents written
    """
    corpus_path = Path(corpus_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ner_cache = JsonCache(ner_cache_path or CONFIG["ner_cache_path"])
    syn_cache = make_synonym_cache(syn_cache_path or CONFIG["synonym_cache_path"])

    count = 0
    with open(corpus_path, encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:

        docs = [json.loads(l) for l in fin if l.strip()]
        for doc in tqdm(docs, desc="Enriching", unit="doc"):
            enriched = enrich_document(doc, ner_cache, syn_cache)
            fout.write(json.dumps(enriched, ensure_ascii=False) + "\n")
            count += 1

    print(f"Enriched corpus written: {count:,} documents → {output_path}")
    return count


if __name__ == "__main__":
    raw = Path(CONFIG["raw_corpus_dir"]) / "corpus.jsonl"
    out = Path(CONFIG["raw_corpus_dir"]) / "corpus_enriched.jsonl"
    enrich_corpus(raw, out)
