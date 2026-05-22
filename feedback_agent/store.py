"""SQLite layer. Dedupes by id, keeps the latest fetched_at."""
import sqlite3
import json
import datetime as dt
from pathlib import Path
from .ingest.app_store import Review


DB_PATH = Path("data/reviews.sqlite")


SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    text TEXT NOT NULL,
    rating INTEGER,
    created_at TEXT,
    url TEXT,
    raw TEXT,
    fetched_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_source ON reviews(source);
CREATE INDEX IF NOT EXISTS idx_created ON reviews(created_at);
"""


def _conn(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path)
    c.executescript(SCHEMA)
    return c


def save(reviews: list[Review], path: Path = DB_PATH) -> int:
    """Upsert reviews. Returns number of new rows."""
    now = dt.datetime.utcnow().isoformat()
    new = 0
    with _conn(path) as c:
        for r in reviews:
            cur = c.execute("SELECT 1 FROM reviews WHERE id = ?", (r.id,))
            if cur.fetchone():
                continue
            c.execute(
                "INSERT INTO reviews (id, source, text, rating, created_at, url, raw, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (r.id, r.source, r.text, r.rating, r.created_at, r.url, json.dumps(r.raw), now),
            )
            new += 1
    return new


def load_all(path: Path = DB_PATH) -> list[dict]:
    with _conn(path) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT id, source, text, rating, created_at, url FROM reviews").fetchall()
    return [dict(r) for r in rows]


def count(path: Path = DB_PATH) -> int:
    with _conn(path) as c:
        return c.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
