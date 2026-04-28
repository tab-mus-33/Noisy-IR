"""
Builds two PyTerrier indices from the corpus:
  - raw index:      original arXiv text, no enrichment
  - enriched index: text with mat_ synonym tokens appended

Both indices use Porter stemming, stopword removal, and block-level
indexing (required for Bo1 proximity-based query expansion).

Run order: fetch_arxiv → matbert_ner → enrich → build_indices
"""

import json
from pathlib import Path

import pyterrier as pt

from matsci.config import CONFIG
from matsci.data.build_trec_xml import docs_to_trec_xml


def _init_terrier() -> None:
    if not pt.started():
        pt.init()


def _jsonl_to_trec(jsonl_path: Path, xml_path: Path) -> int:
    """Convert a JSONL corpus to TREC-XML. Returns document count."""
    def _iter():
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    return docs_to_trec_xml(
        _iter(),
        xml_path,
        docno_field="docno",
        text_fields=["title", "abstract"],
    )


def build_index(xml_path: Path, index_path: str, label: str) -> object:
    """
    Build a single PyTerrier index from a TREC-XML file.

    Parameters
    ----------
    xml_path   : path to TREC-XML corpus file
    index_path : directory where the index will be written
    label      : human-readable label for progress output

    Returns
    -------
    PyTerrier IndexRef
    """
    _init_terrier()

    Path(index_path).mkdir(parents=True, exist_ok=True)

    print(f"Building {label} index...")
    print(f"  Source:  {xml_path}")
    print(f"  Target:  {index_path}")

    indexer = pt.TRECCollectionIndexer(
        index_path,
        blocks=True,                          # needed for Bo1 query expansion
        meta={"docno": 50, "text": 8192},     # store docno + full text for snippets
        stemmer="porter",
        stopwords="terrier",
        overwrite=True,
    )
    index_ref = indexer.index(str(xml_path))

    index = pt.IndexFactory.of(index_ref)
    stats = index.getCollectionStatistics()
    print(f"  Done. {stats.getNumberOfDocuments():,} documents indexed.\n")
    return index_ref


def build_all(
    raw_jsonl: Path | None = None,
    enriched_jsonl: Path | None = None,
) -> tuple:
    """
    Build both raw and enriched indices.

    Parameters
    ----------
    raw_jsonl      : path to corpus.jsonl (defaults to config)
    enriched_jsonl : path to corpus_enriched.jsonl (defaults to config)

    Returns
    -------
    (raw_index_ref, enriched_index_ref)
    """
    raw_dir = Path(CONFIG["raw_corpus_dir"])

    raw_jsonl      = raw_jsonl      or raw_dir / "corpus.jsonl"
    enriched_jsonl = enriched_jsonl or raw_dir / "corpus_enriched.jsonl"

    # Convert JSONL → TREC-XML (intermediate files, not committed)
    raw_xml      = raw_dir / "corpus_raw.xml"
    enriched_xml = raw_dir / "corpus_enriched.xml"

    print("Converting JSONL → TREC-XML...")
    n_raw = _jsonl_to_trec(raw_jsonl, raw_xml)
    print(f"  Raw corpus:      {n_raw:,} documents → {raw_xml}")

    n_enriched = _jsonl_to_trec(enriched_jsonl, enriched_xml)
    print(f"  Enriched corpus: {n_enriched:,} documents → {enriched_xml}\n")

    raw_ref      = build_index(raw_xml,      CONFIG["raw_index_path"],      "raw")
    enriched_ref = build_index(enriched_xml, CONFIG["enriched_index_path"], "enriched")

    return raw_ref, enriched_ref


if __name__ == "__main__":
    build_all()
