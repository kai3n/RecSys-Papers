"""
SQLite-backed paper storage.
Table: papers
"""

import json
import sqlite3
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS papers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    authors     TEXT,           -- JSON list
    abstract    TEXT,
    date        TEXT,
    year        INTEGER,
    venue       TEXT,
    source      TEXT,
    url         TEXT,
    arxiv_id    TEXT,
    doi         TEXT,
    score       INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now'))
)
"""

INSERT_PAPER = """
INSERT OR IGNORE INTO papers
    (title, authors, abstract, date, year, venue, source, url, arxiv_id, doi, score)
VALUES
    (:title, :authors, :abstract, :date, :year, :venue, :source, :url, :arxiv_id, :doi, :score)
"""


class PaperDB:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(CREATE_TABLE)
        self.conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_title ON papers(title)"
        )
        self.conn.commit()
        logger.info(f"DB opened: {db_path}")

    def save(self, papers: List[Dict]) -> int:
        rows = []
        for p in papers:
            rows.append(
                {
                    "title": p.get("title", ""),
                    "authors": json.dumps(p.get("authors", [])),
                    "abstract": p.get("abstract", ""),
                    "date": p.get("date", ""),
                    "year": p.get("year"),
                    "venue": p.get("venue", ""),
                    "source": p.get("source", ""),
                    "url": p.get("url", ""),
                    "arxiv_id": p.get("arxiv_id", ""),
                    "doi": p.get("doi", ""),
                    "score": p.get("score", 0),
                }
            )
        with self.conn:
            cursor = self.conn.executemany(INSERT_PAPER, rows)
        inserted = cursor.rowcount
        logger.info(f"DB: inserted {inserted} new papers (attempted {len(rows)})")
        return inserted

    def load_all(self) -> List[Dict]:
        cursor = self.conn.execute(
            "SELECT * FROM papers ORDER BY score DESC, date DESC"
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["authors"] = json.loads(d["authors"] or "[]")
            result.append(d)
        return result

    def close(self):
        self.conn.close()
