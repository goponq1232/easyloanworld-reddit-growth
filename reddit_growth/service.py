from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Iterable
from .config import settings
from . import db
from .drafter import draft_reply as make_reply
from .reddit_client import search as reddit_search, subreddit_rules, comment as reddit_comment
from .scoring import score_opportunity
from .site_matcher import match_page, refresh_sitemap


def ingest(items: Iterable[dict], source: str = "needle") -> list[dict]:
    saved = []
    for raw in items:
        item = dict(raw)
        item["source"] = item.get("source") or source
        score, breakdown = score_opportunity(item)
        item["score"] = max(int(item.get("external_score") or 0), score)
        item["score_breakdown"] = breakdown
        match = match_page(f"{item.get('title','')} {item.get('body','')}")
        if match:
            item["matched_url"] = match["url"]
            item["matched_reason"] = f"lexical similarity {match['similarity']}"
        oid = db.upsert_opportunity(item)
        saved.append({"id": oid, "score": item["score"], "thread_url": item["thread_url"], "matched_url": item.get("matched_url")})
    return saved


def scan_reddit(keywords: list[str] | None = None, subreddits: list[str] | None = None, limit_per_query: int = 15) -> list[dict]:
    keywords = keywords or settings.default_keywords
    subreddits = subreddits or settings.default_subreddits
    collected: dict[str, dict] = {}
    for subreddit in subreddits:
        for kw in keywords:
            for item in reddit_search(kw, subreddit=subreddit, limit=limit_per_query, sort="new", time_filter="week"):
                if item.get("over_18") or item.get("locked"):
                    continue
                collected[item["thread_url"]] = item
    return ingest(collected.values(), source="reddit_api")


def opportunity_queue(min_score: int | None = None, status: str | None = None, limit: int = 50) -> list[dict]:
    return db.list_opportunities(min_score=min_score if min_score is not None else settings.min_opportunity_score, status=status, limit=limit)


def draft(opportunity_id: int, include_link: bool = False) -> dict:
    opp = db.get_opportunity(opportunity_id)
    if not opp:
        raise KeyError(f"Opportunity {opportunity_id} not found")
    rules_text = ""
    # Rules retrieval may be unavailable when Reddit API access is intentionally disabled.
    try:
        rules = subreddit_rules(opp.get("subreddit") or "") if opp.get("subreddit") else []
        rules_text = "\n".join(f"- {r.get('short_name')}: {r.get('description')}" for r in rules)
        lowered = rules_text.lower()
        if any(x in lowered for x in ["self promotion", "self-promotion", "no promotion", "no advertising", "no spam", "no links"]):
            include_link = False
    except Exception:
        # Unknown rules => conservative: no promotional link.
        include_link = False

    match = None
    if opp.get("matched_url"):
        match = {"url": opp["matched_url"]}
    else:
        match = match_page(f"{opp.get('title','')} {opp.get('body','')}")
    result = make_reply(opp, match, include_link=include_link, rules_text=rules_text)
    did = db.create_draft(opportunity_id, result["body"], result["include_link"], result["target_url"], result["utm_url"])
    return {"draft_id": did, **result, "thread_url": opp["thread_url"], "score": opp["score"]}


def approve(draft_id: int, approved: bool = True) -> dict:
    d = db.get_draft(draft_id)
    if not d:
        raise KeyError(f"Draft {draft_id} not found")
    db.approve_draft(draft_id, approved)
    return {"draft_id": draft_id, "approval_status": "approved" if approved else "rejected"}


def publish(draft_id: int) -> dict:
    d = db.get_draft(draft_id)
    if not d:
        raise KeyError(f"Draft {draft_id} not found")
    if d["approval_status"] != "approved":
        raise PermissionError("Draft must be explicitly approved before publishing.")
    if int(d.get("include_link") or 0) and not settings.allow_promotional_links:
        raise PermissionError("Draft contains a promotional link, but ALLOW_PROMOTIONAL_LINKS=false.")
    fullname = d.get("reddit_id")
    if not fullname:
        raise ValueError("Missing Reddit parent fullname; cannot publish automatically.")
    result = reddit_comment(fullname, d["body"])
    cid = result.get("comment_id") or "unknown"
    url = result.get("url") or d["thread_url"]
    db.mark_published(draft_id, cid, url)
    return {"draft_id": draft_id, "published": True, "comment_id": cid, "url": url}


def run_daily(source: str = "reddit_api", max_drafts: int | None = None) -> dict:
    max_drafts = max_drafts or settings.max_drafts_per_day
    discovered = []
    notes = []
    if source == "reddit_api":
        discovered = scan_reddit()
    elif source == "queue_only":
        notes.append("No discovery source called; drafted from existing queue.")
    else:
        raise ValueError("source must be reddit_api or queue_only")

    queue = opportunity_queue(min_score=settings.min_opportunity_score, status="new", limit=max_drafts)
    drafts = []
    for opp in queue:
        # Daily automation drafts without links by default. A human can approve a link-bearing redraft later.
        try:
            drafts.append(draft(opp["id"], include_link=False))
        except Exception as e:
            notes.append(f"Draft failed for opportunity {opp['id']}: {e}")
    db.record_run(source, len(discovered), len(queue), len(drafts), 0, " | ".join(notes))
    return {
        "run_date": datetime.now(timezone.utc).date().isoformat(),
        "source": source,
        "discovered": len(discovered),
        "qualified": len(queue),
        "drafted": len(drafts),
        "drafts": drafts,
        "notes": notes,
    }


def dashboard() -> dict:
    return {
        "top_opportunities": opportunity_queue(limit=20),
        "pending_drafts": db.list_drafts(status="pending", limit=20),
        "approved_drafts": db.list_drafts(status="approved", limit=20),
        "recent_runs": db.recent_runs(),
        "settings": {
            "reddit_api_enabled": settings.reddit_commercial_api_approved,
            "auto_publish_enabled": settings.auto_publish_enabled,
            "allow_promotional_links": settings.allow_promotional_links,
            "min_opportunity_score": settings.min_opportunity_score,
        },
    }
