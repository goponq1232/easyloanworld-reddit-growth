from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterable
from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  reddit_id TEXT,
  thread_url TEXT NOT NULL UNIQUE,
  subreddit TEXT,
  title TEXT NOT NULL,
  body TEXT,
  author TEXT,
  created_utc REAL,
  score INTEGER NOT NULL DEFAULT 0,
  score_breakdown TEXT NOT NULL DEFAULT '{}',
  matched_url TEXT,
  matched_reason TEXT,
  status TEXT NOT NULL DEFAULT 'new',
  discovered_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_opportunities_score ON opportunities(score DESC);
CREATE INDEX IF NOT EXISTS idx_opportunities_status ON opportunities(status);

CREATE TABLE IF NOT EXISTS drafts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  opportunity_id INTEGER NOT NULL,
  body TEXT NOT NULL,
  include_link INTEGER NOT NULL DEFAULT 0,
  target_url TEXT,
  utm_url TEXT,
  approval_status TEXT NOT NULL DEFAULT 'pending',
  published_comment_id TEXT,
  published_url TEXT,
  created_at TEXT NOT NULL,
  approved_at TEXT,
  published_at TEXT,
  FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
);
CREATE INDEX IF NOT EXISTS idx_drafts_approval ON drafts(approval_status);

CREATE TABLE IF NOT EXISTS daily_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_date TEXT NOT NULL,
  source TEXT NOT NULL,
  discovered INTEGER NOT NULL DEFAULT 0,
  qualified INTEGER NOT NULL DEFAULT 0,
  drafted INTEGER NOT NULL DEFAULT 0,
  published INTEGER NOT NULL DEFAULT 0,
  notes TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS site_pages (
  url TEXT PRIMARY KEY,
  title_hint TEXT,
  tokens TEXT,
  refreshed_at TEXT NOT NULL
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect():
    con = sqlite3.connect(settings.database_path)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with connect() as con:
        con.executescript(SCHEMA)


def upsert_opportunity(item: dict[str, Any]) -> int:
    with connect() as con:
        con.execute(
            """
            INSERT INTO opportunities
              (source, reddit_id, thread_url, subreddit, title, body, author, created_utc,
               score, score_breakdown, matched_url, matched_reason, status, discovered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(thread_url) DO UPDATE SET
              source=excluded.source,
              reddit_id=COALESCE(excluded.reddit_id, opportunities.reddit_id),
              subreddit=COALESCE(excluded.subreddit, opportunities.subreddit),
              title=excluded.title,
              body=COALESCE(excluded.body, opportunities.body),
              author=COALESCE(excluded.author, opportunities.author),
              created_utc=COALESCE(excluded.created_utc, opportunities.created_utc),
              score=MAX(excluded.score, opportunities.score),
              score_breakdown=excluded.score_breakdown,
              matched_url=COALESCE(excluded.matched_url, opportunities.matched_url),
              matched_reason=COALESCE(excluded.matched_reason, opportunities.matched_reason)
            """,
            (
                item.get("source", "manual"), item.get("reddit_id"), item["thread_url"],
                item.get("subreddit"), item.get("title", ""), item.get("body"), item.get("author"),
                item.get("created_utc"), int(item.get("score", 0)),
                json.dumps(item.get("score_breakdown", {})), item.get("matched_url"),
                item.get("matched_reason"), item.get("status", "new"), utcnow(),
            ),
        )
        row = con.execute("SELECT id FROM opportunities WHERE thread_url=?", (item["thread_url"],)).fetchone()
        return int(row["id"])


def list_opportunities(min_score: int = 0, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    query = "SELECT * FROM opportunities WHERE score >= ?"
    params: list[Any] = [min_score]
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY score DESC, discovered_at DESC LIMIT ?"
    params.append(limit)
    with connect() as con:
        rows = con.execute(query, params).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["score_breakdown"] = json.loads(d.get("score_breakdown") or "{}")
        out.append(d)
    return out


def get_opportunity(opportunity_id: int) -> dict[str, Any] | None:
    with connect() as con:
        row = con.execute("SELECT * FROM opportunities WHERE id=?", (opportunity_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["score_breakdown"] = json.loads(d.get("score_breakdown") or "{}")
    return d


def create_draft(opportunity_id: int, body: str, include_link: bool, target_url: str | None, utm_url: str | None) -> int:
    with connect() as con:
        cur = con.execute(
            """INSERT INTO drafts(opportunity_id, body, include_link, target_url, utm_url, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (opportunity_id, body, int(include_link), target_url, utm_url, utcnow()),
        )
        con.execute("UPDATE opportunities SET status='drafted' WHERE id=?", (opportunity_id,))
        return int(cur.lastrowid)


def get_draft(draft_id: int) -> dict[str, Any] | None:
    with connect() as con:
        row = con.execute(
            """SELECT d.*, o.thread_url, o.subreddit, o.title AS thread_title, o.reddit_id
               FROM drafts d JOIN opportunities o ON o.id=d.opportunity_id WHERE d.id=?""",
            (draft_id,),
        ).fetchone()
    return dict(row) if row else None


def list_drafts(status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    query = """SELECT d.*, o.thread_url, o.subreddit, o.title AS thread_title
               FROM drafts d JOIN opportunities o ON o.id=d.opportunity_id"""
    params: list[Any] = []
    if status:
        query += " WHERE d.approval_status=?"
        params.append(status)
    query += " ORDER BY d.created_at DESC LIMIT ?"
    params.append(limit)
    with connect() as con:
        return [dict(r) for r in con.execute(query, params).fetchall()]


def approve_draft(draft_id: int, approved: bool) -> None:
    with connect() as con:
        con.execute(
            "UPDATE drafts SET approval_status=?, approved_at=? WHERE id=?",
            ("approved" if approved else "rejected", utcnow() if approved else None, draft_id),
        )


def mark_published(draft_id: int, comment_id: str, comment_url: str) -> None:
    with connect() as con:
        con.execute(
            "UPDATE drafts SET approval_status='published', published_comment_id=?, published_url=?, published_at=? WHERE id=?",
            (comment_id, comment_url, utcnow(), draft_id),
        )
        con.execute(
            "UPDATE opportunities SET status='published' WHERE id=(SELECT opportunity_id FROM drafts WHERE id=?)",
            (draft_id,),
        )


def replace_site_pages(rows: Iterable[tuple[str, str, str]]) -> int:
    now = utcnow()
    rows = list(rows)
    with connect() as con:
        con.execute("DELETE FROM site_pages")
        con.executemany(
            "INSERT INTO site_pages(url,title_hint,tokens,refreshed_at) VALUES(?,?,?,?)",
            [(u, t, tok, now) for u, t, tok in rows],
        )
    return len(rows)


def get_site_pages() -> list[dict[str, Any]]:
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM site_pages").fetchall()]


def record_run(source: str, discovered: int, qualified: int, drafted: int, published: int = 0, notes: str = "") -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    with connect() as con:
        con.execute(
            """INSERT INTO daily_runs(run_date,source,discovered,qualified,drafted,published,notes,created_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (today, source, discovered, qualified, drafted, published, notes, utcnow()),
        )


def recent_runs(limit: int = 14) -> list[dict[str, Any]]:
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM daily_runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()]
