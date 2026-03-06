"""
Main entry point for the CTR/CVR RecSys paper crawler.

Usage:
    python main.py                    # full run
    python main.py --arxiv-only       # skip conference crawl
    python main.py --conf-only        # skip arXiv crawl
    python main.py --export-only      # skip crawl, re-export from DB
    python main.py --min-score 2      # override minimum relevance score
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml

from crawlers import arxiv_crawler, conference_crawler
from parsers.keyword_filter import filter_and_score
from storage.db import PaperDB
from exporters import to_html, to_markdown

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.yaml"
DB_PATH = BASE_DIR / "output" / "papers.db"


def load_config(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def run(args):
    config = load_config(CONFIG_PATH)

    if args.min_score is not None:
        config.setdefault("scoring", {})["min_score"] = args.min_score

    output_dir = BASE_DIR / config["output"]["directory"].lstrip("./")
    output_dir.mkdir(parents=True, exist_ok=True)

    db = PaperDB(str(DB_PATH))

    if not args.export_only:
        all_raw = []

        if not args.conf_only and config["sources"]["arxiv"]["enabled"]:
            logger.info("=== Crawling arXiv ===")
            arxiv_papers = arxiv_crawler.fetch(config)
            all_raw.extend(arxiv_papers)

        if not args.arxiv_only and config["sources"]["conferences"]["enabled"]:
            logger.info("=== Crawling Conferences ===")
            conf_papers = conference_crawler.fetch(config)
            all_raw.extend(conf_papers)

        logger.info(f"Total raw papers collected: {len(all_raw)}")

        logger.info("=== Filtering & Scoring ===")
        scored = filter_and_score(all_raw, config)

        logger.info("=== Saving to DB ===")
        db.save(scored)

    logger.info("=== Loading from DB ===")
    papers = db.load_all()
    db.close()

    if not papers:
        logger.warning("No papers in DB. Nothing to export.")
        sys.exit(0)

    logger.info(f"Exporting {len(papers)} papers...")

    html_path = output_dir / config["output"]["html"]
    md_path = output_dir / config["output"]["markdown"]

    to_html.export(papers, str(html_path))
    to_markdown.export(papers, str(md_path))

    print(f"\nDone! Outputs:")
    print(f"  HTML     -> {html_path}")
    print(f"  Markdown -> {md_path}")
    print(f"  Database -> {DB_PATH}")


def main():
    parser = argparse.ArgumentParser(description="CTR/CVR RecSys Paper Crawler")
    parser.add_argument("--arxiv-only", action="store_true", help="Only crawl arXiv")
    parser.add_argument("--conf-only", action="store_true", help="Only crawl conferences")
    parser.add_argument("--export-only", action="store_true", help="Skip crawl, re-export from DB")
    parser.add_argument("--min-score", type=int, default=None, help="Minimum relevance score")
    args = parser.parse_args()

    if args.arxiv_only and args.conf_only:
        print("Error: --arxiv-only and --conf-only cannot be used together.")
        sys.exit(1)

    run(args)


if __name__ == "__main__":
    main()
