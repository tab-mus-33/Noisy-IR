"""
Query-side concept enrichment — mirrors the document-side enrichment in enrich.py.

For each topic query, identifies material mentions and appends synonym tokens
so the query vocabulary matches the enriched document index.

Example:
  input:  "corundum thermal conductivity high temperature"
  output: "corundum thermal conductivity high temperature
           mat_aluminium_oxide mat_al2o3 mat_aluminum_oxide mat_alumina"

This is the query equivalent of what enrich.py does to documents.
Both must use the same synonym tokens for the dual-index score combination
to work correctly.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from matsci.config import CONFIG
from matsci.enrichment.pubchem_client import get_synonyms as pubchem_synonyms
from matsci.enrichment.matproj_client import formula_to_synonyms as mp_synonyms
from matsci.enrichment.synonym_cache import make_synonym_cache, normalise_key
from matsci.topics.topic_builder import TOPICS


_PREFIX = CONFIG["synonym_token_prefix"]


def _to_token(synonym: str) -> str:
    return _PREFIX + re.sub(r"\s+", "_", synonym.strip().lower())


def _get_synonyms(entity: str, cache) -> list[str]:
    key = normalise_key(entity)
    if key in cache:
        return cache.get(key)

    synonyms: list[str] = []
    synonyms.extend(pubchem_synonyms(entity))
    for s in mp_synonyms(entity):
        if s not in synonyms:
            synonyms.append(s)

    entity_lower = entity.lower()
    seen = {entity_lower}
    unique = [s for s in synonyms if s.lower() not in seen and not seen.add(s.lower())]

    cache.set(key, unique)
    return unique


def enrich_query(query: str, name_a: str, name_b: str, cache) -> str:
    """
    Append synonym tokens for both name variants of the topic material.

    Uses the explicit name_a / name_b from the topic definition rather than
    running NER on the query — queries are short and NER on 5-word strings
    is unreliable. The topic definition tells us exactly which material
    the query is about.
    """
    tokens: set[str] = set()

    for name in (name_a, name_b):
        for synonym in _get_synonyms(name, cache):
            tokens.add(_to_token(synonym))

    if not tokens:
        return query

    return query + " " + " ".join(sorted(tokens))


def build_enriched_topics_xml(
    output_path: str | Path,
    cache_path: str | Path | None = None,
) -> Path:
    """
    Write a TREC topics XML file where every query has synonym tokens appended.

    Used as input to the enriched-index retrieval pipeline (Experiment 2).

    Parameters
    ----------
    output_path : where to write the enriched topics XML
    cache_path  : synonym cache (defaults to config value)

    Returns
    -------
    Path to the written XML file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cache = make_synonym_cache(cache_path or CONFIG["synonym_cache_path"])

    root = ET.Element("topics")

    for num, name_a, name_b, title_a, description in TOPICS:
        enriched_title = enrich_query(title_a, name_a, name_b, cache)

        top = ET.SubElement(root, "top")
        ET.SubElement(top, "num").text = str(num)
        ET.SubElement(top, "title").text = enriched_title
        ET.SubElement(top, "description").text = description

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="unicode", xml_declaration=False)

    print(f"Enriched topics written → {output_path}")
    return output_path


if __name__ == "__main__":
    out = Path(CONFIG["topics_xml"]).parent / "matsci_topics_enriched.xml"
    build_enriched_topics_xml(out)

    # Preview first topic
    tree = ET.parse(out)
    first = tree.findall("top")[0]
    print(f"\nTopic {first.find('num').text}:")
    print(f"  {first.find('title').text[:120]}")
