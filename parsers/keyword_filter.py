"""
Keyword-based relevance scoring and filtering.

Score breakdown:
  - primary keyword match in title   -> +5 per match
  - primary keyword match in abstract -> +3 per match
  - secondary keyword match in title  -> +2 per match
  - secondary keyword match in abstract -> +1 per match
"""

import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    return text.lower()


def score_paper(paper: Dict, config: dict) -> int:
    primary = [kw.lower() for kw in config["keywords"]["primary"]]
    secondary = [kw.lower() for kw in config["keywords"]["secondary"]]

    title = _normalize(paper.get("title", ""))
    abstract = _normalize(paper.get("abstract", ""))
    score = 0

    for kw in primary:
        if kw in title:
            score += 5
        if kw in abstract:
            score += 3

    for kw in secondary:
        if kw in title:
            score += 2
        if kw in abstract:
            score += 1

    return score


def filter_and_score(papers: List[Dict], config: dict) -> List[Dict]:
    min_score = config.get("scoring", {}).get("min_score", 1)
    scored = []

    for paper in papers:
        s = score_paper(paper, config)
        if s >= min_score:
            paper["score"] = s
            scored.append(paper)

    # Deduplicate by normalized title
    seen = set()
    unique = []
    for p in scored:
        key = re.sub(r"\s+", " ", p["title"].lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(p)

    # Sort: conference first, then by score desc, then date desc
    unique.sort(key=lambda p: (-p["score"], p.get("date", ""), p["title"]))

    logger.info(
        f"Filter: {len(papers)} total -> {len(unique)} after scoring (min_score={min_score})"
    )
    return unique
