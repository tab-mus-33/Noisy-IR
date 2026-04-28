"""
Downloads materials science paper metadata (title + abstract) from arXiv.

Uses the arXiv API directly via requests rather than the arxiv library,
giving full control over rate limiting and exponential backoff on 429s.

arXiv API policy:
  - Max 3 requests/second in normal use
  - For bulk access use 15s+ between requests
  - On 429: back off exponentially before retrying

Targets three categories:
  - cond-mat.mtrl-sci  (materials science)
  - physics.app-ph     (applied physics)
  - cond-mat.supr-con  (superconductors)

Output: one JSONL file per category + merged corpus.jsonl
Fully resumable: re-running skips already-fetched papers.
"""

import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from tqdm import tqdm

from matsci.config import CONFIG


CATEGORIES = CONFIG["arxiv_categories"]
MAX_PAPERS  = CONFIG["max_papers"]
PER_CATEGORY = MAX_PAPERS // len(CATEGORIES)

PAGE_SIZE       = 100    # results per API request (keep low to avoid 429)
PAGE_DELAY      = 16.0   # seconds between successful page requests
BACKOFF_INITIAL = 60     # seconds to wait on first 429
BACKOFF_MAX     = 3600   # cap backoff at 1 hour

ARXIV_API = "https://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom"}


def _parse_feed(xml_text: str) -> list[dict]:
    """Parse an arXiv Atom feed page into a list of document dicts."""
    root = ET.fromstring(xml_text)
    docs = []
    for entry in root.findall("atom:entry", NS):
        # entry id looks like: http://arxiv.org/abs/2301.00001v1
        raw_id = entry.find("atom:id", NS)
        if raw_id is None:
            continue
        arxiv_id = raw_id.text.split("/abs/")[-1].split("v")[0].replace(".", "_")

        title = entry.find("atom:title", NS)
        summary = entry.find("atom:summary", NS)

        docs.append({
            "docno":    f"arxiv_{arxiv_id}",
            "title":    (title.text or "").replace("\n", " ").strip(),
            "abstract": (summary.text or "").replace("\n", " ").strip(),
        })
    return docs


def _fetch_page(category: str, start: int) -> list[dict]:
    """
    Fetch one page of results with exponential backoff on 429.
    Returns list of parsed docs, or empty list on unrecoverable error.
    """
    params = {
        "search_query": f"cat:{category}",
        "start":        start,
        "max_results":  PAGE_SIZE,
        "sortBy":       "submittedDate",
        "sortOrder":    "descending",
    }
    backoff = BACKOFF_INITIAL

    while True:
        try:
            resp = requests.get(ARXIV_API, params=params, timeout=30)
        except requests.RequestException as e:
            print(f"\n  Connection error at start={start}: {e}. Retrying in {backoff}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, BACKOFF_MAX)
            continue

        if resp.status_code == 200:
            return _parse_feed(resp.text)

        if resp.status_code == 429:
            print(f"\n  429 rate limit at start={start}. Waiting {backoff}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, BACKOFF_MAX)
            continue

        # Other HTTP error — log and skip this page
        print(f"\n  HTTP {resp.status_code} at start={start}. Skipping page.")
        return []


def fetch_category(
    category: str,
    max_results: int,
    output_path: Path,
    resume: bool = True,
) -> int:
    """
    Fetch up to max_results papers from one arXiv category.
    Appends to output_path and skips already-fetched docnos if resume=True.
    Returns number of new papers written.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    if resume and output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    seen.add(json.loads(line)["docno"])

    if len(seen) >= max_results:
        print(f"  {category}: already complete ({len(seen):,} papers cached)")
        return 0

    print(f"  {category}: resuming from {len(seen):,} papers, target {max_results:,}")

    written = 0
    start = len(seen)   # start from where we left off

    with open(output_path, "a", encoding="utf-8") as f:
        with tqdm(total=max_results - len(seen), desc=f"  {category}", unit="paper") as pbar:
            while len(seen) < max_results:
                docs = _fetch_page(category, start)

                if not docs:
                    # Empty page means we've exhausted the category
                    break

                for doc in docs:
                    if doc["docno"] not in seen and len(seen) < max_results:
                        f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                        seen.add(doc["docno"])
                        written += 1
                        pbar.update(1)

                start += PAGE_SIZE
                time.sleep(PAGE_DELAY)

    return written


def fetch_all(output_dir: Path | None = None) -> Path:
    """
    Fetch papers from all configured categories and merge into one JSONL.
    Returns path to merged corpus.
    """
    raw_dir = Path(output_dir or CONFIG["raw_corpus_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    merged_path = raw_dir / "corpus.jsonl"

    print(f"Fetching up to {MAX_PAPERS:,} papers across {len(CATEGORIES)} categories")
    print(f"Page size: {PAGE_SIZE} | Delay: {PAGE_DELAY}s | Output: {merged_path}\n")

    for category in CATEGORIES:
        cat_path = raw_dir / f"{category.replace('.', '_')}.jsonl"
        n = fetch_category(category, PER_CATEGORY, cat_path)
        print(f"  → {n:,} new papers written for {category}\n")

    # Merge and deduplicate
    print(f"Merging → {merged_path}")
    seen: set[str] = set()
    total = 0
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
                        total += 1

    print(f"Done. {total:,} unique papers → {merged_path}")
    return merged_path


if __name__ == "__main__":
    fetch_all()
