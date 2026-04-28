"""
LLM-based relevance judgements using Claude.

Judges (query, abstract) pairs on the TREC 0-3 relevance scale:
  0 — not relevant
  1 — marginally relevant (mentions the topic but not the specific need)
  2 — relevant (addresses the information need)
  3 — highly relevant (directly and thoroughly addresses the need)

Uses claude-haiku for cost efficiency on bulk judgements (~$0.003 per pair).
Batches requests and caches results to avoid re-judging the same pair.
"""

import json
import re
import time
from pathlib import Path

import anthropic
import pandas as pd
from tqdm import tqdm

from matsci.config import CONFIG


_SYSTEM = """\
You are a relevance assessor for a materials science information retrieval study.
You will be given an information need and a paper abstract.
Score the abstract's relevance to the information need on this scale:
  0 — not relevant
  1 — marginally relevant (topic mentioned but information need not addressed)
  2 — relevant (addresses the information need)
  3 — highly relevant (directly and thoroughly addresses the information need)
Reply with a single integer 0, 1, 2, or 3. Nothing else."""

_USER_TEMPLATE = """\
Information need: {description}

Abstract:
{abstract}

Relevance score (0-3):"""

_CACHE_PATH = Path("data/cache/llm_judgements.json")


def _load_cache() -> dict:
    if _CACHE_PATH.exists():
        with open(_CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f)


def _cache_key(qid: str, docno: str) -> str:
    return f"{qid}|{docno}"


def _parse_score(response_text: str) -> int:
    """Extract integer 0-3 from model response. Returns -1 on parse failure."""
    match = re.search(r"\b([0-3])\b", response_text.strip())
    return int(match.group(1)) if match else -1


def judge_pair(
    client: anthropic.Anthropic,
    description: str,
    abstract: str,
) -> int:
    """
    Judge one (query, abstract) pair. Returns relevance score 0-3.
    Returns -1 if the model response cannot be parsed.
    """
    prompt = _USER_TEMPLATE.format(
        description=description,
        abstract=abstract[:2000],   # truncate very long abstracts
    )
    try:
        msg = client.messages.create(
            model=CONFIG["llm_judge_model"],
            max_tokens=4,
            temperature=0,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_score(msg.content[0].text)
    except Exception as e:
        print(f"\n  Judge API error: {e}")
        return -1


def judge_batch(
    pool: pd.DataFrame,
    topic_descriptions: dict[str, str],
    batch_size: int | None = None,
) -> pd.DataFrame:
    """
    Judge all rows in pool dataframe. Returns pool with added 'relevance' column.

    Parameters
    ----------
    pool               : dataframe with columns [qid, docno, text]
    topic_descriptions : dict mapping qid → information need description
    batch_size         : rows to process before saving cache (default from config)

    Returns
    -------
    pool dataframe with 'relevance' column added
    """
    batch_size = batch_size or CONFIG["llm_judge_batch_size"]
    api_key = CONFIG["anthropic_api_key"]
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set in .env")

    client = anthropic.Anthropic(api_key=api_key)
    cache = _load_cache()

    scores = []
    unsaved = 0

    for _, row in tqdm(pool.iterrows(), total=len(pool), desc="Judging", unit="pair"):
        key = _cache_key(row["qid"], row["docno"])

        if key in cache:
            scores.append(cache[key])
            continue

        description = topic_descriptions.get(row["qid"], "")
        score = judge_pair(client, description, row.get("text", ""))
        cache[key] = score
        scores.append(score)
        unsaved += 1

        if unsaved >= batch_size:
            _save_cache(cache)
            unsaved = 0

        time.sleep(0.1)  # light rate limiting

    if unsaved:
        _save_cache(cache)

    result = pool.copy()
    result["relevance"] = scores
    return result
