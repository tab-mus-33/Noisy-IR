"""
Constructs TREC-format relevance judgements (qrels) for the 30 topic pairs.

Strategy — two complementary sources:

1. Retrieval pooling (primary):
   Run BM25 with both name variants (A and B) for each topic against the raw
   index. Pool the top-100 results from each run. This ensures both naming
   conventions are represented in the judged set.

2. LLM judging:
   Each (topic, abstract) pair in the pool is sent to Claude for a relevance
   score on the TREC 0-4 scale. This replaces human assessors.

Output: standard TREC qrels format (one judgement per line):
  <topic_num> 0 <docno> <relevance>

where relevance is 0 (not relevant), 1 (fair), 2 (good), 3 (excellent).

Run order: build_indices → build_qrels
"""

import json
import pandas as pd
import pyterrier as pt
from pathlib import Path
from tqdm import tqdm

from matsci.config import CONFIG
from matsci.evaluation.llm_judge import judge_batch
from matsci.topics.topic_builder import TOPICS


POOL_DEPTH = 100    # top-N from each retrieval run to include in judging pool


def _load_topics_df(variant: str) -> pd.DataFrame:
    """Load topic XML into a PyTerrier-compatible dataframe."""
    topics_dir = Path(CONFIG["topics_xml"]).parent
    xml_path = topics_dir / f"matsci_topics_{variant}.xml"

    import xml.etree.ElementTree as ET
    tree = ET.parse(xml_path)
    rows = []
    for top in tree.findall("top"):
        rows.append({
            "qid":   top.find("num").text.strip(),
            "query": top.find("title").text.strip(),
        })
    return pd.DataFrame(rows)


def _pool_results(raw_index_ref) -> pd.DataFrame:
    """
    Run BM25 with both name variants and pool top-POOL_DEPTH results per topic.

    Returns a dataframe with columns [qid, docno, text] — the judging pool.
    """
    if not pt.started():
        pt.init()

    raw_index = pt.IndexFactory.of(raw_index_ref)
    bm25 = pt.BatchRetrieve(
        raw_index,
        wmodel="BM25",
        num_results=POOL_DEPTH,
        metadata=["docno", "text"],
    )

    topics_a = _load_topics_df("a")
    topics_b = _load_topics_df("b")

    results_a = bm25.transform(topics_a)
    results_b = bm25.transform(topics_b)

    # Pool: combine both runs, deduplicate per topic
    pooled = pd.concat([results_a, results_b], ignore_index=True)
    pooled = pooled.drop_duplicates(subset=["qid", "docno"])

    print(f"Pool size: {len(pooled):,} (query, document) pairs across {pooled['qid'].nunique()} topics")
    return pooled[["qid", "docno", "text"]]


def build_qrels(
    raw_index_ref,
    output_path: Path | None = None,
) -> Path:
    """
    Build qrels by pooling BM25 results and judging with Claude.

    Parameters
    ----------
    raw_index_ref : PyTerrier IndexRef for the raw (unenriched) index
    output_path   : where to write the qrels file

    Returns
    -------
    Path to the written qrels file
    """
    output_path = Path(output_path or CONFIG["qrels_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build topic descriptions for the judge (it needs the full information need)
    topic_descriptions = {
        str(num): description
        for num, _, _, _, description in TOPICS
    }

    # Pool results from both name variants
    pool = _pool_results(raw_index_ref)

    # Judge each pair
    print(f"\nJudging {len(pool):,} pairs with {CONFIG['llm_judge_model']}...")
    judgements = judge_batch(pool, topic_descriptions)

    # Write TREC qrels format: qid 0 docno relevance
    written = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for _, row in judgements.iterrows():
            if row["relevance"] >= 0:
                f.write(f"{row['qid']} 0 {row['docno']} {row['relevance']}\n")
                written += 1

    print(f"Qrels written: {written:,} judgements → {output_path}")
    return output_path


if __name__ == "__main__":
    from matsci.indexing.build_indices import build_all
    raw_ref, _ = build_all()
    build_qrels(raw_ref)
