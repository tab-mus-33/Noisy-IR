"""
Runs MatSciBERT NER on a corpus of materials science abstracts.

Identifies MAT (material) entities in each document and writes results to
the NER cache. Subsequent pipeline steps read from cache rather than
re-running inference.

MatSciBERT entity labels:
  MAT  - material name (the one we want for synonym enrichment)
  PRO  - property
  SPL  - sample/descriptor
  CMT  - characterisation method
  PUT  - property unit type
  SMT  - synthesis method
  DSC  - descriptor

GPU usage: set ner_device=0 in config (or -1 for CPU).
On a single GPU, 100k abstracts takes approximately 20-40 minutes.
"""

import json
from pathlib import Path

from tqdm import tqdm
from transformers import pipeline

from matsci.config import CONFIG
from matsci.ner.entity_cache import JsonCache


def _load_model():
    return pipeline(
        "token-classification",
        model=CONFIG["ner_model"],
        aggregation_strategy="simple",
        device=CONFIG["ner_device"],
    )


def _extract_mat_entities(ner_output: list[dict], threshold: float) -> list[str]:
    """Return unique MAT entity strings above the confidence threshold."""
    seen: set[str] = set()
    entities: list[str] = []
    for ent in ner_output:
        if ent["entity_group"] == CONFIG["ner_entity_label"] and ent["score"] >= threshold:
            text = ent["word"].strip()
            if text and text.lower() not in seen:
                seen.add(text.lower())
                entities.append(text)
    return entities


def run_ner_on_corpus(
    corpus_path: str | Path,
    cache_path: str | Path | None = None,
    batch_size: int | None = None,
) -> JsonCache:
    """
    Run MatSciBERT NER over all documents in corpus_path (JSONL).

    Results are written to the NER cache keyed by docno.
    Documents already in the cache are skipped.

    Parameters
    ----------
    corpus_path : path to corpus JSONL (one doc per line with 'docno', 'title', 'abstract')
    cache_path  : where to store results (defaults to config value)
    batch_size  : inference batch size (defaults to config value)

    Returns
    -------
    Populated JsonCache instance
    """
    corpus_path = Path(corpus_path)
    cache_path = Path(cache_path or CONFIG["ner_cache_path"])
    batch_size = batch_size or CONFIG["ner_batch_size"]
    threshold = CONFIG["ner_confidence_threshold"]

    cache = JsonCache(cache_path)

    # Load corpus, skip already-cached docs
    docs = []
    with open(corpus_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)
            if doc["docno"] not in cache:
                docs.append(doc)

    if not docs:
        print(f"NER cache is complete ({len(cache):,} docs). Nothing to do.")
        return cache

    print(f"Running NER on {len(docs):,} documents (skipped {len(cache):,} cached)")
    print(f"Model: {CONFIG['ner_model']} | device={CONFIG['ner_device']} | batch={batch_size}")

    ner = _load_model()

    # Process in batches
    texts = [f"{d['title']} {d['abstract']}" for d in docs]
    docnos = [d["docno"] for d in docs]

    for i in tqdm(range(0, len(texts), batch_size), desc="NER batches", unit="batch"):
        batch_texts = texts[i : i + batch_size]
        batch_docnos = docnos[i : i + batch_size]

        try:
            results = ner(batch_texts, batch_size=batch_size)
        except Exception as e:
            # On OOM or transient error, fall back to one-by-one
            print(f"\nBatch error at {i}: {e}. Falling back to single inference.")
            results = [ner(t) for t in batch_texts]

        for docno, ner_out in zip(batch_docnos, results):
            entities = _extract_mat_entities(ner_out, threshold)
            cache.set(docno, entities)

    print(f"NER complete. {len(cache):,} documents cached at {cache_path}")
    return cache


def load_ner_cache(cache_path: str | Path | None = None) -> JsonCache:
    """Load an existing NER cache without running inference."""
    return JsonCache(cache_path or CONFIG["ner_cache_path"])


if __name__ == "__main__":
    from matsci.config import CONFIG

    corpus = Path(CONFIG["raw_corpus_dir"]) / "corpus.jsonl"
    if not corpus.exists():
        print(f"Corpus not found at {corpus}. Run fetch_arxiv.py first.")
    else:
        run_ner_on_corpus(corpus)
