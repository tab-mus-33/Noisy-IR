"""
PyTerrier retrieval pipelines — direct adaptation of the thesis patterns.

Four pipelines:
  1. bm25_raw          — BM25 on raw (unenriched) index, baseline
  2. qe_pl2_raw        — BM25 → Bo1 query expansion → PL2 rerank on raw index
  3. qe_pl2_dual       — qe_pl2_raw + PL2 on enriched index, scores combined
  4. dense_scibert     — dense retrieval with MatSciBERT embeddings (Exp 2 comparison)

All pipelines accept a PyTerrier topics dataframe and return a results dataframe
with columns [qid, docno, score, rank].
"""

import pyterrier as pt

from matsci.config import CONFIG


def _init():
    if not pt.started():
        pt.init()


def bm25_raw(index) -> pt.Transformer:
    _init()
    return pt.BatchRetrieve(
        index,
        wmodel="BM25",
        controls={"c": CONFIG["bm25_b"], "bm25.k_1": CONFIG["bm25_k1"]},
        num_results=CONFIG["retrieval_depth"],
    )


def qe_pl2_raw(index) -> pt.Transformer:
    """BM25 first stage → Bo1 query expansion → PL2 rerank. Thesis Experiment 3 winner."""
    _init()
    bm25 = pt.BatchRetrieve(
        index,
        wmodel="BM25",
        controls={"c": CONFIG["bm25_b"]},
        num_results=CONFIG["retrieval_depth"],
    )
    qe = pt.rewrite.Bo1QueryExpansion(
        index,
        fb_terms=CONFIG["bo1_fb_terms"],
        fb_docs=CONFIG["bo1_fb_docs"],
    )
    pl2 = pt.BatchRetrieve(
        index,
        wmodel="PL2",
        controls={"c": CONFIG["pl2_c"]},
        num_results=CONFIG["retrieval_depth"],
    )
    return bm25 >> qe >> pl2


def qe_pl2_dual(raw_index, enriched_index, alpha: float | None = None) -> pt.Transformer:
    """
    Dual-index pipeline: scores from raw and enriched index combined linearly.

    Mirrors Equation 6.1 from the thesis:
      Score(q, d) = PL2(q_text, d_text) + PL2(q_text, d_enriched)
    """
    _init()
    alpha = alpha if alpha is not None else CONFIG["score_alpha"]

    raw_pipe = qe_pl2_raw(raw_index)
    enriched_pipe = qe_pl2_raw(enriched_index)

    # Normalise each pipeline's scores to [0,1] before combining
    raw_norm = raw_pipe >> pt.pipelines.PerQueryMaxMinScoreTransformer()
    enr_norm = enriched_pipe >> pt.pipelines.PerQueryMaxMinScoreTransformer()

    return (alpha * raw_norm) + ((1 - alpha) * enr_norm)


def dense_scibert(index_path: str) -> pt.Transformer:
    """
    Dense retrieval baseline using sentence-transformers.

    Uses 'allenai/scibert_scivocab_uncased' — a scientific BERT that approximates
    MatSciBERT performance without requiring pyterrier_dr installation.
    Falls back gracefully if sentence-transformers is not installed.
    """
    _init()
    try:
        from pyterrier_sentence_transformers import SentenceTransformersRetriever
        return SentenceTransformersRetriever(
            index_path,
            model="allenai/scibert_scivocab_uncased",
            num_results=CONFIG["retrieval_depth"],
        )
    except ImportError:
        print(
            "WARNING: pyterrier_sentence_transformers not installed. "
            "Dense pipeline unavailable. Install with:\n"
            "  pip install pyterrier-sentence-transformers"
        )
        return None
