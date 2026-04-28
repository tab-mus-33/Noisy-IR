# Concept-Enriched Information Retrieval for Materials Science Literature

## Overview

This project adapts a noisy information retrieval (IR) architecture — originally developed for searching ASR-transcribed podcast audio — to the problem of searching materials science literature. The central argument is that **materials science has a severe vocabulary fragmentation problem that is structurally identical to the noise problem in spoken-word retrieval**, and that the same class of solution — enriching documents and queries with canonical concept tokens from an external knowledge source — measurably improves retrieval quality.

The work is framed around three experiments that together constitute a complete research contribution targeting *Digital Discovery* (RSC) or *npj Computational Materials* (Nature Portfolio).

---

## Research Motivation

### The Vocabulary Mismatch Problem

When a researcher searches for papers about a material, they use one name. The papers they are looking for may use a completely different name for the same substance. Standard search engines — including Google Scholar, Semantic Scholar, and institutional databases — treat these as different queries with no overlap.

The same material routinely appears under four to six distinct identities in the literature simultaneously:

| Material | Common name | Mineral name | Formula | IUPAC name | Abbreviation |
|---|---|---|---|---|---|
| α-Al₂O₃ | alumina | corundum | Al₂O₃ | aluminium oxide | — |
| TiO₂ | titania | rutile / anatase | TiO₂ | titanium dioxide | — |
| YBa₂Cu₃O₇ | — | — | YBa₂Cu₃O₇ | yttrium barium copper oxide | YBCO / Y123 |
| LiFePO₄ | — | — | LiFePO₄ | lithium iron phosphate | LFP |
| ITO | indium tin oxide | — | In₂O₃:Sn | — | ITO |

A search for "corundum deformation mechanisms" will miss papers about "alumina plasticity" and "Al₂O₃ slip systems", even though they discuss the same material. This is not a failure of the researcher — it is a structural failure of the retrieval system.

### Why Current Tools Do Not Solve This

Modern AI-powered search tools (Elicit, Consensus, Semantic Scholar) use dense retrieval: they encode queries and documents as vectors and retrieve by semantic similarity. These tools handle synonym variation well on general text, but fail in two materials-specific scenarios:

1. **Formula-to-name mismatch**: "Fe₂O₃" and "hematite" have similar meaning but very different surface forms. Dense models trained on general scientific text often fail to link them reliably because the two strings never co-occur in the same sentence in training data.

2. **OCR-corrupted legacy literature**: A large fraction of important materials science papers (pre-1995) exists only as scanned PDFs. OCR errors corrupt chemical formulas systematically — "α-Al₂O₃" becomes "a-A1203", subscripts are lost, Greek letters become ASCII. Dense retrieval models trained on clean text break completely on this noise. Every current tool assumes clean input.

### The Proposed Solution

This work directly adapts the concept enrichment approach from a 2022 UCL MSc dissertation (*"Make the Noise Wik(i): Proactive Information Retrieval using Wikipedia Concepts"*) to the materials science domain. The original thesis showed that:

- Appending Wikipedia concept tokens to podcast transcripts and queries significantly improved retrieval over noisy ASR text
- Classical probabilistic retrieval (BM25/PL2) consistently outperformed neural re-ranking on noisy text
- The combination of an unenriched and enriched index, with linearly combined scores, produced the best results

Here, Wikipedia is replaced by a materials-specific knowledge graph (PubChem + Materials Project), and ASR transcripts are replaced by materials science abstracts — with a controlled synthetic OCR noise layer for the third experiment.

---

## Research Contribution

Three claims, each supported by one experiment:

### Experiment 1 — Quantifying the Gap
**Claim**: Vocabulary fragmentation measurably and significantly hurts retrieval in materials science literature.

**Method**: 30 paired topics are constructed, each expressing the same information need using two different name variants for the same material (e.g., "corundum thermal conductivity" vs "Al₂O₃ thermal conductivity"). BM25 is run against both variants on the same corpus. The drop in NDCG between the two variants quantifies the gap caused by name fragmentation alone.

**Expected result**: Significant NDCG degradation (estimated 20–40%) when using the non-dominant name variant. This establishes that the problem is real and large.

### Experiment 2 — Concept Enrichment as the Fix
**Claim**: Enriching documents and queries with canonical synonym tokens from PubChem and the Materials Project closes the retrieval gap.

**Method**: MatSciBERT NER identifies material mentions in each abstract. PubChem and Materials Project APIs return all known synonyms and formula variants for each mention. These are appended as `mat_`-prefixed tokens. A dual-index pipeline retrieves from both the original and enriched index, combining scores linearly. This is compared against: BM25 alone, BM25 + query expansion (Bo1/PL2), and dense retrieval (SciBERT embeddings).

**Expected result**: The dual-index enriched pipeline outperforms all baselines on NDCG and P@10. Dense retrieval underperforms classical methods — replicating the thesis finding in a new domain.

### Experiment 3 — Robustness to OCR Noise
**Claim**: Classical probabilistic retrieval + concept enrichment degrades more gracefully than dense retrieval as OCR noise increases.

**Method**: The clean arXiv corpus is corrupted at five noise levels (0%, 5%, 10%, 20%, 30% character error rate) using a systematic OCR noise simulator that models real failure modes (0/O confusion, subscript loss, Greek letter mangling, hyphen removal). Both the probabilistic pipeline and a dense retrieval baseline are re-run at each noise level. NDCG is plotted as a function of error rate.

**Expected result**: Classical + enrichment degrades gracefully and approximately linearly; dense retrieval collapses rapidly at higher error rates, particularly on formula-heavy queries. This is the most novel finding of the three and has not been demonstrated for materials science literature.

---

## The 30 Topic Pairs

Each topic is designed around a material with well-documented name fragmentation. The information need is specific enough (property + application context) to have a clear relevant document set. Topics span the main classes of materials science literature on arXiv.

| # | Name A (common/mineral) | Name B (formula/IUPAC) | Information need |
|---|---|---|---|
| 1 | corundum | Al2O3 | thermal conductivity at high temperature |
| 2 | titania | TiO2 | photocatalytic water splitting |
| 3 | silica | SiO2 | glass viscosity and thermal properties |
| 4 | hematite | Fe2O3 | photoelectrochemical water oxidation |
| 5 | magnetite | Fe3O4 | magnetic nanoparticles for hyperthermia |
| 6 | zincite | ZnO | piezoelectric nanowire nanogenerators |
| 7 | cassiterite | SnO2 | resistive gas sensing |
| 8 | ceria | CeO2 | oxygen storage in catalysis |
| 9 | zirconia | ZrO2 | thermal barrier coatings |
| 10 | periclase | MgO | refractory sintering |
| 11 | barium titanate | BaTiO3 | piezoelectric energy harvesting |
| 12 | strontium titanate | SrTiO3 | dielectric thin films |
| 13 | bismuth ferrite | BiFeO3 | room-temperature multiferroics |
| 14 | lead zirconate titanate | PZT | MEMS actuators |
| 15 | lanthanum cuprate | La2CuO4 | antiferromagnetic parent compound |
| 16 | YBCO | YBa2Cu3O7 | flux pinning and critical current |
| 17 | BSCCO | Bi2Sr2CaCu2O8 | intrinsic Josephson junctions |
| 18 | hexagonal boron nitride | h-BN | dielectric substrate for graphene |
| 19 | gallium nitride | GaN | high-electron-mobility transistors |
| 20 | silicon nitride | Si3N4 | fracture toughness of structural ceramics |
| 21 | carborundum | SiC | wide-bandgap power semiconductors |
| 22 | tungsten carbide | WC | hardness and wear-resistant coatings |
| 23 | monolayer graphene | single-layer graphene | electronic mobility and charge transport |
| 24 | molybdenite | MoS2 | two-dimensional field-effect transistors |
| 25 | tungstenite | WS2 | photoluminescence and valley polarisation |
| 26 | lithium iron phosphate | LFP | cathode cycle stability |
| 27 | NMC | lithium nickel manganese cobalt oxide | high-voltage cathode degradation |
| 28 | galena | PbS | quantum dot infrared photodetectors |
| 29 | greenockite | CdS | thin-film solar cell buffer layers |
| 30 | indium tin oxide | ITO | transparent conducting electrodes |

---

## Implementation Plan

### Phase 1 — Scaffolding ✅ Complete
All configuration, caching, XML conversion, noise simulation, and topic generation infrastructure. No external dependencies required beyond the package install.

| File | Purpose |
|---|---|
| `matsci/config.py` | Central configuration: all paths, hyperparameters, API key loading |
| `matsci/data/build_trec_xml.py` | Converts document dicts to TREC-XML for PyTerrier indexing |
| `matsci/indexing/noise_simulator.py` | Injects OCR-style errors at controlled character error rates |
| `matsci/topics/topic_builder.py` | Generates paired TREC topic XML files for Experiment 1 |
| `matsci/ner/entity_cache.py` | Thread-safe JSON cache preventing re-running expensive NER inference |
| `matsci/enrichment/synonym_cache.py` | Same cache mechanism for API synonym lookups |

### Phase 2 — Data Acquisition
Download 100,000 abstracts from three arXiv categories: `cond-mat.mtrl-sci`, `physics.app-ph`, and `cond-mat.supr-con`. Papers are fetched with resumable download (safe to interrupt and restart). Output is a single deduplicated JSONL file.

**Estimated time**: 3–4 hours (rate-limited to comply with arXiv API policy).

```bash
uv run python matsci/data/fetch_arxiv.py
```

Output: `data/raw/corpus.jsonl` (~100,000 papers, ~500 MB)

### Phase 3 — Named Entity Recognition
MatSciBERT (`m3rg-iitd/matscibert`) identifies material entity spans (`MAT` label) in each title + abstract. Results are written to a JSON cache keyed by `docno`. Already-cached documents are skipped, so the process is safely resumable.

**Estimated time**: 20–40 minutes on GPU (TITAN V).

```bash
uv run python matsci/ner/matbert_ner.py
```

Output: `data/cache/ner_cache.json`

### Phase 4 — Concept Enrichment
For each unique material entity found by NER:
1. Query PubChem for all known synonyms and common names
2. Query Materials Project for canonical formula variants
3. Filter out InChI strings, SMILES, CAS numbers, and excessively long entries
4. Append as `mat_`-prefixed tokens to the document text

Results are cached so API calls are never repeated.

**Estimated time**: 2–4 hours (PubChem rate limit: 5 requests/second).

```bash
uv run python matsci/enrichment/enrich.py
```

Output: `data/raw/corpus_enriched.jsonl`

### Phase 5 — Indexing
Build two PyTerrier indices: one from the original corpus, one from the enriched corpus. Both use Porter stemming, stopword removal, and block-level indexing (required for proximity-based query expansion).

```bash
uv run python matsci/indexing/build_indices.py
```

Output: `data/indices/raw/`, `data/indices/enriched/`

### Phase 6 — Retrieval Pipelines
Four pipelines are implemented in `matsci/retrieval/pipelines.py`:

1. **BM25 (raw)** — vanilla keyword retrieval, baseline
2. **QE + PL2 (raw)** — BM25 first stage → Bo1 query expansion (15 terms, 6 docs) → PL2 rerank
3. **Dual-index (enriched)** — QE+PL2 on raw + QE+PL2 on enriched, scores normalised and combined 50/50
4. **Dense (SciBERT)** — sentence-transformer embeddings, semantic similarity baseline

### Phase 7 — Evaluation
Relevance judgements are constructed from two sources:
- **Materials Project paper links**: each material entry cites the papers that characterised it, providing ground-truth relevance at scale without human annotation
- **LLM-generated judgements**: Claude Haiku scores (query, abstract) pairs on a 0–4 relevance scale for documents not covered by Materials Project links

Three experiments are run via `matsci/evaluation/run_experiments.py`, producing NDCG, NDCG@30, MAP, and P@10 for each pipeline at each experimental condition.

---

## Repository Structure

```
Noisy-IR/
├── pyproject.toml              # dependencies and project metadata (uv)
├── uv.lock                     # exact pinned versions of all 134 packages
├── .python-version             # pins Python 3.12
├── .env.example                # template for API keys (copy to .env and fill in)
├── .gitignore
│
├── matsci/                     # main Python package
│   ├── config.py               # all settings in one place
│   ├── data/
│   │   ├── fetch_arxiv.py      # arXiv corpus download
│   │   └── build_trec_xml.py   # convert dicts → TREC-XML
│   ├── ner/
│   │   ├── matbert_ner.py      # MatSciBERT NER inference
│   │   └── entity_cache.py     # JSON cache for NER results
│   ├── enrichment/
│   │   ├── pubchem_client.py   # PubChem synonym lookup
│   │   ├── matproj_client.py   # Materials Project formula variants
│   │   ├── synonym_cache.py    # cache for API results
│   │   └── enrich.py           # orchestrates enrichment pipeline
│   ├── indexing/
│   │   ├── build_indices.py    # PyTerrier index construction
│   │   └── noise_simulator.py  # OCR noise injection for Experiment 3
│   ├── retrieval/
│   │   └── pipelines.py        # BM25, QE+PL2, dual-index, dense
│   ├── evaluation/
│   │   ├── build_qrels.py      # relevance judgements from Materials Project
│   │   ├── llm_judge.py        # Claude-based relevance scoring
│   │   └── run_experiments.py  # Experiments 1, 2, 3
│   └── topics/
│       └── topic_builder.py    # generates paired TREC topic XML files
│
├── data/                       # gitignored — generated locally
│   ├── raw/                    # arXiv JSONL corpus
│   ├── indices/                # PyTerrier index directories
│   ├── cache/                  # NER and synonym JSON caches
│   ├── topics/                 # generated topic XML files
│   ├── qrels/                  # relevance judgement files
│   └── results/                # experiment output tables
│
└── notebooks/                  # exploratory notebooks (not required to run)
```

---

## Environment Setup

### Prerequisites

**1. Java Development Kit (JDK) ≥ 11**

PyTerrier wraps the Terrier IR engine, which is written in Java. You must have a JDK installed before setting up the Python environment.

Check whether Java is installed:
```bash
java -version
```

If not installed, on Ubuntu/Debian:
```bash
sudo apt install default-jdk
```

On RHEL/Fedora/Rocky:
```bash
sudo dnf install java-17-openjdk-devel
```

On macOS (with Homebrew):
```bash
brew install openjdk@17
```

**2. GPU with CUDA support** (recommended, not required)

The NER step (Phase 3) uses MatSciBERT. On a CPU this takes ~3 hours for 100k abstracts; on a GPU it takes ~30 minutes. The retrieval and indexing steps are CPU-only.

This project is configured for **CUDA 12.6** wheels, compatible with driver versions 525+. If your system has an older driver, change the index URL in `pyproject.toml`:

```toml
# CUDA 11.8 (driver ≥ 450):
url = "https://download.pytorch.org/whl/cu118"

# CUDA 12.1 (driver ≥ 530):
url = "https://download.pytorch.org/whl/cu121"

# CPU only:
# Remove the [tool.uv.sources] and [[tool.uv.index]] sections entirely
```

Then re-run `uv lock` before `uv sync`.

**3. uv**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

### Installation

**Step 1 — Clone the repository**
```bash
git clone <repo-url>
cd Noisy-IR
git checkout matsci-concept-enrichment-ir
```

**Step 2 — Set up API keys**
```bash
cp .env.example .env
```
Edit `.env` and fill in your keys:
```
MP_API_KEY=your_materials_project_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

- Materials Project API key: register free at [materialsproject.org](https://materialsproject.org)
- Anthropic API key: required only for Phase 7 (LLM relevance judgements); budget ~$10–20

**Step 3 — Create the environment and install all dependencies**
```bash
uv sync
```

This creates `.venv/`, installs all 134 packages at pinned versions, and installs the `matsci` package in editable mode. It reads from `uv.lock` so the exact same package versions are installed regardless of when or where this is run.

**Step 4 — Verify the installation**
```bash
uv run python -c "
import pyterrier as pt
import torch
from matsci.config import CONFIG
print('PyTerrier:', pt.__version__)
print('PyTorch:', torch.__version__)
print('CUDA available:', torch.cuda.is_available())
print('MP key loaded:', CONFIG['matproject_api_key'] is not None)
"
```

Expected output:
```
PyTerrier: 0.10.x
PyTorch: 2.6.x+cu126
CUDA available: True
MP key loaded: True
```

---

### Running the Pipeline

Run each phase in order. Each step is resumable — if interrupted, re-running skips already-completed work.

```bash
# Phase 2: download corpus (~3-4 hours, run overnight)
uv run python matsci/data/fetch_arxiv.py

# Phase 3: NER (~30 min on GPU)
uv run python matsci/ner/matbert_ner.py

# Phase 4: concept enrichment (~2-4 hours)
uv run python matsci/enrichment/enrich.py

# Phase 5: build indices (~20-40 min)
uv run python matsci/indexing/build_indices.py

# Phase 6+7: run all experiments
uv run python matsci/evaluation/run_experiments.py
```

Alternatively, activate the virtual environment once and drop the `uv run` prefix:
```bash
source .venv/bin/activate
python matsci/data/fetch_arxiv.py
# etc.
```

---

### Updating Dependencies

To add a new package:
```bash
uv add <package-name>
```

This updates both `pyproject.toml` and `uv.lock` atomically.

To update all packages to their latest compatible versions:
```bash
uv lock --upgrade
uv sync
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'matsci'`**
Run `uv sync` to install the package in editable mode. If using an external Python (not `.venv`), run `uv run python ...` instead.

**`java.lang.RuntimeException` or PyTerrier JVM errors**
Java is not installed or not on PATH. See the JDK prerequisite above.

**`CUDA out of memory` during NER**
Reduce `ner_batch_size` in `matsci/config.py` from 64 to 16 or 8.

**`MP_API_KEY not set` error**
Ensure `.env` exists and contains `MP_API_KEY=...`. The `.env.example` file shows the required format.

**PubChem returns no synonyms for a material**
PubChem covers molecular compounds well but some inorganic materials return empty results when queried by common name. Try querying by formula (e.g. `SnO2` instead of `tin oxide`). The Materials Project client covers the inorganic gap.

---

## Reproducibility Notes

- `uv.lock` pins all 134 packages to exact versions. Anyone running `uv sync` from this lockfile gets an identical environment.
- The noise simulator accepts a `seed` parameter; all experiments use `seed=42` by default.
- arXiv paper availability may change over time (papers occasionally removed). The corpus JSONL is cached locally after the first download.
- LLM relevance judgements (Phase 7) use `claude-haiku-4-5-20251001` with temperature 0 for determinism. Model responses may change across API versions.

---

## Citation

This work builds on:

> *"Make the Noise Wik(i): Proactive Information Retrieval using Wikipedia Concepts"*
> MSc Dissertation, UCL Department of Computer Science, 2022.
> Supervised by Prof. Emine Yilmaz and Sahan Bulathwela.

Key external tools:

- **PyTerrier**: Macdonald et al., CIKM 2021
- **MatSciBERT**: Gupta et al., *npj Computational Materials*, 2022
- **Materials Project**: Jain et al., *APL Materials*, 2013
- **PubChem**: Kim et al., *Nucleic Acids Research*, 2023
