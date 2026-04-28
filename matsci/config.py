import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # loads .env from repo root if present

ROOT = Path(__file__).parent.parent

CONFIG = {
    # --- Paths ---
    "raw_corpus_dir":       ROOT / "data" / "raw",
    "raw_index_path":       str(ROOT / "data" / "indices" / "raw"),
    "enriched_index_path":  str(ROOT / "data" / "indices" / "enriched"),
    "topics_xml":           str(ROOT / "data" / "topics" / "matsci_topics.xml"),
    "qrels_path":           str(ROOT / "data" / "qrels" / "matsci.qrels"),
    "results_dir":          ROOT / "data" / "results",
    "ner_cache_path":       ROOT / "data" / "cache" / "ner_cache.json",
    "synonym_cache_path":   ROOT / "data" / "cache" / "synonym_cache.json",
    "raw_xml_path":         str(ROOT / "data" / "raw" / "corpus_raw.xml"),
    "enriched_xml_path":    str(ROOT / "data" / "raw" / "corpus_enriched.xml"),

    # --- API Keys (fill in before running Phases 4+) ---
    "matproject_api_key":   os.environ.get("MP_API_KEY", None),
    "anthropic_api_key":    os.environ.get("ANTHROPIC_API_KEY", None),

    # --- Corpus settings ---
    "arxiv_categories":     ["cond-mat.mtrl-sci", "physics.app-ph", "cond-mat.supr-con"],
    "max_papers":           100_000,

    # --- NER settings ---
    "ner_model":            "m3rg-iitd/matscibert",
    "ner_batch_size":       64,   # larger batch for GPU
    "ner_device":           0,    # GPU device index; set to -1 for CPU
    "ner_confidence_threshold": 0.85,
    "ner_entity_label":     "MAT",

    # --- Synonym filtering ---
    "max_synonyms_per_entity":  15,
    "max_synonym_length":       40,    # characters; filters out InChI strings, long IUPAC names
    "synonym_token_prefix":     "mat_",

    # --- Retrieval hyperparameters (tuned from thesis) ---
    "bm25_b":               0.75,
    "bm25_k1":              1.2,
    "pl2_c":                20.0,
    "bo1_fb_terms":         15,
    "bo1_fb_docs":          6,
    "score_alpha":          0.5,       # weight: raw index vs enriched index

    # --- Experiment 3: OCR noise levels ---
    "noise_levels":         [0.0, 0.05, 0.10, 0.20, 0.30],

    # --- Evaluation ---
    "eval_metrics":         ["map", "ndcg", "ndcg_cut_30", "P_10"],
    "retrieval_depth":      1000,
    "llm_judge_model":      "claude-haiku-4-5-20251001",
    "llm_judge_batch_size": 50,
}
