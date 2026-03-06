"""
arXiv crawler using the official Atom feed API.
Docs: https://arxiv.org/help/api/user-manual
"""

import time
import logging
import feedparser
from datetime import datetime
from typing import List, Dict
from urllib.parse import quote

logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"


def _build_query(keywords: List[str], categories: List[str]) -> str:
    # Combine primary and secondary keywords with OR
    kw_parts = [f'all:"{kw}"' for kw in keywords]
    cat_parts = [f"cat:{cat}" for cat in categories]
    kw_query = " OR ".join(kw_parts)
    cat_query = " OR ".join(cat_parts)
    return f"({kw_query}) AND ({cat_query})"


def fetch(config: dict, known_titles: set = None) -> List[Dict]:
    arxiv_cfg = config["sources"]["arxiv"]
    all_keywords = config["keywords"]["primary"] + config["keywords"]["secondary"]
    categories = arxiv_cfg["categories"]
    max_results = arxiv_cfg.get("max_results", 300)
    start_date = datetime.strptime(config["date_range"]["start"], "%Y-%m-%d")

    end_date_str = config["date_range"].get("end")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else datetime.today()

    if known_titles is None:
        known_titles = set()

    query = _build_query(all_keywords, categories)
    papers = []
    seen_ids = set()
    batch_size = 100
    offset = 0

    logger.info(f"arXiv query: {query[:120]}...")

    while offset < max_results:
        size = min(batch_size, max_results - offset)
        url = (
            f"{ARXIV_API_URL}?search_query={quote(query)}"
            f"&start={offset}&max_results={size}"
            f"&sortBy=submittedDate&sortOrder=descending"
        )

        logger.info(f"  Fetching arXiv offset={offset} size={size}")
        feed = feedparser.parse(url)

        if not feed.entries:
            logger.info("  No more arXiv entries.")
            break

        stop_early = False
        for entry in feed.entries:
            pub_str = entry.get("published", "")
            try:
                pub_date = datetime.strptime(pub_str[:10], "%Y-%m-%d")
            except ValueError:
                pub_date = None

            if pub_date and pub_date < start_date:
                stop_early = True
                break

            if pub_date and pub_date > end_date:
                continue

            arxiv_id = entry.get("id", "").split("/abs/")[-1]
            if arxiv_id in seen_ids:
                continue
            seen_ids.add(arxiv_id)

            title = entry.get("title", "").replace("\n", " ").strip()
            if title.lower() in known_titles:
                continue

            authors = [a.name for a in entry.get("authors", [])]
            paper = {
                "title": title,
                "abstract": entry.get("summary", "").replace("\n", " ").strip(),
                "authors": authors,
                "date": pub_str[:10] if pub_str else "",
                "year": int(pub_str[:4]) if pub_str else None,
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "arxiv_id": arxiv_id,
                "doi": "",
                "source": "arxiv",
                "venue": "arXiv",
            }
            papers.append(paper)

        if stop_early:
            logger.info("  Reached papers older than start_date, stopping.")
            break

        offset += batch_size
        # arXiv API asks for 3s between requests
        time.sleep(3)

    logger.info(f"arXiv: collected {len(papers)} papers")
    return papers
