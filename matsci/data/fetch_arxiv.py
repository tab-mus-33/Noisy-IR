"""
Downloads materials science paper metadata (title + abstract) from arXiv.

Targets three categories:
  - cond-mat.mtrl-sci  (materials science)
  - physics.app-ph     (applied physics)
  - cond-mat.supr-con  (superconductors — relevant for YBCO-type nomenclature)

Output: one JSONL file with one paper per line:
  {"docno": "arxiv_XXXXXXX", "title": "...", "abstract": "..."}

Rate-limited to 3 requests/second per arXiv API policy.
For 100k papers this takes roughly 3-4 hours; run overnight.
"""

import json
import time
from pathlib import Path

import arxiv
from tqdm import tqdm

from matsci.config import CONFIG


CATEGORIES = CONFIG["arxiv_categories"]
MAX_PAPERS = CONFIG["max_papers"]
PER_CATEGORY = MAX_PAPERS // len(CATEGORIES)
RATE_LIMIT_DELAY = 3.0  # seconds between requests (arXiv policy: max 3/s)


def _paper_to_dict(paper: arxiv.Result) -> dict:
    arxiv_id = paper.entry_id.split("/")[-1].replace(".", "_")
    return {
        "docno": f"arxiv_{arxiv_id}",
        "title": paper.title.replace("\n", " ").strip(),
        "abstract": paper.summary.replace("\n", " ").strip(),
    }


def fetch_category(
    category: str,
    max_results: int,
    output_path: Path,
    resume: bool = True,
) -> int:
    """
    Fetch up to max_results papers from one arXiv category, writing to a JSONL file.
    If resume=True and the file exists, skips already-fetched papers.

    Returns number of papers written.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Resume: load already-fetched docnos to skip duplicates
    seen: set[str] = set()
    if resume and output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    seen.add(json.loads(line)["docno"])

    remaining = max_results - len(seen)
    if remaining <= 0:
        print(f"  {category}: already complete ({len(seen)} papers)")
        return 0

    client = arxiv.Client(
        page_size=500,
        delay_seconds=RATE_LIMIT_DELAY,
        num_retries=5,
    )
    search = arxiv.Search(
        query=f"cat:{category}",
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    written = 0
    with open(output_path, "a", encoding="utf-8") as f:
        for paper in tqdm(
            client.results(search),
            total=remaining,
            desc=f"  {category}",
            unit="paper",
        ):
            doc = _paper_to_dict(paper)
            if doc["docno"] in seen:
                continue
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
            seen.add(doc["docno"])
            written += 1
            if len(seen) >= max_results:
                break

    return written


def fetch_all(output_dir: Path | None = None) -> Path:
    """
    Fetch papers from all configured categories, merge into one JSONL file.

    Returns path to merged JSONL.
    """
    raw_dir = output_dir or CONFIG["raw_corpus_dir"]
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    merged_path = raw_dir / "corpus.jsonl"

    print(f"Fetching up to {MAX_PAPERS:,} papers across {len(CATEGORIES)} categories")
    print(f"Output: {merged_path}\n")

    total_written = 0
    for category in CATEGORIES:
        cat_path = raw_dir / f"{category.replace('.', '_')}.jsonl"
        n = fetch_category(category, PER_CATEGORY, cat_path)
        total_written += n
        print(f"  → {n} new papers written for {category}")
        time.sleep(1)

    # Merge category files into one corpus, deduplicating by docno
    print(f"\nMerging category files → {merged_path}")
    seen: set[str] = set()
    total_merged = 0
    with open(merged_path, "w", encoding="utf-8") as out:
        for category in CATEGORIES:
            cat_path = raw_dir / f"{category.replace('.', '_')}.jsonl"
            if not cat_path.exists():
                continue
            with open(cat_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    doc = json.loads(line)
                    if doc["docno"] not in seen:
                        out.write(line + "\n")
                        seen.add(doc["docno"])
                        total_merged += 1

    print(f"Merged corpus: {total_merged:,} unique papers → {merged_path}")
    return merged_path


if __name__ == "__main__":
    fetch_all()
