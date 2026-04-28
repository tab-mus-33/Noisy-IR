"""
Runs all three experiments and writes results tables.

Experiment 1 — Nomenclature fragmentation gap
  Show that querying with name_a vs name_b for the same material produces
  significantly different retrieval quality on a shared relevant document set.
  Metric: NDCG, MAP, P@10 for BM25 under both name variants.

Experiment 2 — Concept enrichment closes the gap
  Compare four pipelines on the primary (name_a) topics:
    - BM25 raw
    - QE + PL2 raw
    - Dual-index enriched
    - Dense (SciBERT)
  Metric: NDCG, NDCG@30, MAP, P@10

Experiment 3 — OCR noise robustness
  Rebuild indices at five noise levels (0%, 5%, 10%, 20%, 30%).
  Compare QE+PL2 and dense pipeline on degradation curve.
  Metric: NDCG vs error rate.

Run order: build_indices → build_qrels → run_experiments
"""

import json
from pathlib import Path

import pandas as pd
import pyterrier as pt

from matsci.config import CONFIG
from matsci.indexing.build_indices import build_index, _jsonl_to_trec
from matsci.indexing.noise_simulator import corrupt_corpus
from matsci.retrieval.pipelines import bm25_raw, qe_pl2_raw, qe_pl2_dual, dense_scibert


RESULTS_DIR = Path(CONFIG["results_dir"])
METRICS     = CONFIG["eval_metrics"]


def _init():
    if not pt.started():
        pt.init()


def _load_topics(variant: str) -> pd.DataFrame:
    import xml.etree.ElementTree as ET
    topics_dir = Path(CONFIG["topics_xml"]).parent
    tree = ET.parse(topics_dir / f"matsci_topics_{variant}.xml")
    rows = []
    for top in tree.findall("top"):
        rows.append({
            "qid":   top.find("num").text.strip(),
            "query": top.find("title").text.strip(),
        })
    return pd.DataFrame(rows)


def _load_qrels() -> pd.DataFrame:
    qrels_path = Path(CONFIG["qrels_path"])
    if not qrels_path.exists():
        raise FileNotFoundError(
            f"Qrels not found at {qrels_path}. Run build_qrels.py first."
        )
    return pt.io.read_qrels(str(qrels_path))


def _save(df: pd.DataFrame, name: str) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"  Saved → {path}")


# ── Experiment 1 ──────────────────────────────────────────────────────────────

def experiment_1(raw_index_ref) -> pd.DataFrame:
    """
    Quantify the retrieval gap caused by nomenclature fragmentation.
    Runs BM25 with name_a and name_b variants on the raw index.
    """
    _init()
    print("\n=== Experiment 1: Nomenclature Fragmentation Gap ===")

    raw_index = pt.IndexFactory.of(raw_index_ref)
    bm25 = bm25_raw(raw_index)
    qrels = _load_qrels()

    topics_a = _load_topics("a")
    topics_b = _load_topics("b")

    results = pt.Experiment(
        [bm25, bm25],
        [topics_a, topics_b],
        qrels,
        eval_metrics=METRICS,
        names=["BM25 (name_a — common)", "BM25 (name_b — formula)"],
        correction="t",      # paired t-test for significance
    )

    print(results.to_string())
    _save(results, "exp1_fragmentation_gap")
    return results


# ── Experiment 2 ──────────────────────────────────────────────────────────────

def experiment_2(raw_index_ref, enriched_index_ref) -> pd.DataFrame:
    """
    Compare four retrieval pipelines to show concept enrichment closes the gap.
    """
    _init()
    print("\n=== Experiment 2: Concept Enrichment vs Baselines ===")

    raw_index      = pt.IndexFactory.of(raw_index_ref)
    enriched_index = pt.IndexFactory.of(enriched_index_ref)
    qrels          = _load_qrels()
    topics         = _load_topics("a")

    bm25        = bm25_raw(raw_index)
    qe_pl2      = qe_pl2_raw(raw_index)
    dual        = qe_pl2_dual(raw_index, enriched_index)
    dense       = dense_scibert(CONFIG["enriched_index_path"])

    pipelines = [bm25, qe_pl2, dual]
    names     = ["BM25 (raw)", "QE+PL2 (raw)", "Dual-index (enriched)"]

    if dense is not None:
        pipelines.append(dense)
        names.append("Dense (SciBERT)")

    results = pt.Experiment(
        pipelines,
        topics,
        qrels,
        eval_metrics=METRICS,
        names=names,
        baseline=0,      # significance vs BM25
        correction="t",
    )

    print(results.to_string())
    _save(results, "exp2_enrichment_vs_baselines")
    return results


# ── Experiment 3 ──────────────────────────────────────────────────────────────

def experiment_3(raw_jsonl: Path) -> pd.DataFrame:
    """
    OCR noise robustness: rebuild indices at each noise level, compare pipelines.
    """
    _init()
    print("\n=== Experiment 3: OCR Noise Robustness ===")

    qrels  = _load_qrels()
    topics = _load_topics("a")
    rows   = []

    # Load clean corpus once
    docs = []
    with open(raw_jsonl, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))

    for noise_level in CONFIG["noise_levels"]:
        print(f"\n  Noise level: {noise_level:.0%}")

        # Corrupt corpus at this noise level
        corrupted = corrupt_corpus(docs, noise_level, seed=42)

        # Write to temp TREC-XML and build a temporary index
        tmp_xml   = Path("data/raw/tmp_noisy.xml")
        tmp_index = f"data/indices/noisy_{int(noise_level*100):02d}"

        from matsci.data.build_trec_xml import docs_to_trec_xml
        docs_to_trec_xml(corrupted, tmp_xml)
        index_ref = build_index(tmp_xml, tmp_index, label=f"noisy-{noise_level:.0%}")
        index     = pt.IndexFactory.of(index_ref)

        # Probabilistic pipeline
        prob_results = pt.Experiment(
            [qe_pl2_raw(index)],
            topics, qrels,
            eval_metrics=["ndcg", "map"],
            names=["QE+PL2"],
        )

        row = {"noise_level": noise_level}
        row["qe_pl2_ndcg"] = prob_results.loc[0, "ndcg"]
        row["qe_pl2_map"]  = prob_results.loc[0, "map"]

        # Dense pipeline (if available)
        dense = dense_scibert(tmp_index)
        if dense is not None:
            dense_results = pt.Experiment(
                [dense], topics, qrels,
                eval_metrics=["ndcg", "map"],
                names=["Dense"],
            )
            row["dense_ndcg"] = dense_results.loc[0, "ndcg"]
            row["dense_map"]  = dense_results.loc[0, "map"]

        rows.append(row)
        print(f"    QE+PL2 NDCG={row['qe_pl2_ndcg']:.4f}  MAP={row['qe_pl2_map']:.4f}")

    results = pd.DataFrame(rows)
    print("\n", results.to_string())
    _save(results, "exp3_ocr_noise_robustness")
    return results


# ── Entry point ───────────────────────────────────────────────────────────────

def run_all():
    """Run all three experiments in sequence."""
    import pyterrier as pt
    _init()

    raw_ref      = pt.IndexRef.of(CONFIG["raw_index_path"])
    enriched_ref = pt.IndexRef.of(CONFIG["enriched_index_path"])
    raw_jsonl    = Path(CONFIG["raw_corpus_dir"]) / "corpus.jsonl"

    experiment_1(raw_ref)
    experiment_2(raw_ref, enriched_ref)
    experiment_3(raw_jsonl)

    print(f"\nAll results saved to {RESULTS_DIR}")


if __name__ == "__main__":
    run_all()
