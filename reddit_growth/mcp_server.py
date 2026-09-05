"""Remote MCP server for ChatGPT Business/Enterprise/Edu custom apps.

Run: python -m reddit_growth.mcp_server
Endpoint: /mcp
"""
from __future__ import annotations
from mcp.server.fastmcp import FastMCP
from .db import init_db, list_drafts
from .service import ingest, opportunity_queue, draft, approve, publish, run_daily, dashboard
from .site_matcher import refresh_sitemap, match_page

init_db()
mcp = FastMCP(
    "EasyLoanWorld Reddit Growth Copilot",
    instructions=(
        "Find and rank Reddit traffic opportunities for EasyLoanWorld, draft useful non-spammy replies, "
        "match relevant site resources, and manage an explicit approval queue. Never publish an unapproved draft."
    ),
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def ingest_needle_opportunities(items: list[dict]) -> dict:
    """Import Reddit opportunities discovered by Needle or another approved discovery source. Each item should include thread_url and title; subreddit/body/created_utc/engagement fields improve scoring."""
    return {"saved": ingest(items, source="needle")}


@mcp.tool()
def list_reddit_opportunities(min_score: int = 65, status: str | None = None, limit: int = 25) -> dict:
    """List the highest-value Reddit opportunities already in the queue."""
    return {"items": opportunity_queue(min_score=min_score, status=status, limit=min(limit, 100))}


@mcp.tool()
def draft_reddit_reply(opportunity_id: int, include_link: bool = False) -> dict:
    """Draft a genuinely helpful reply. include_link is treated conservatively; if subreddit rules are unavailable/unclear the service removes the promotional link."""
    return draft(opportunity_id, include_link=include_link)


@mcp.tool()
def list_reddit_drafts(status: str = "pending", limit: int = 25) -> dict:
    """Review pending/approved/published Reddit reply drafts."""
    return {"items": list_drafts(status=status, limit=min(limit, 100))}


@mcp.tool()
def approve_reddit_draft(draft_id: int, approved: bool = True) -> dict:
    """Explicitly approve or reject a Reddit draft. Approval is required before publication."""
    return approve(draft_id, approved)


@mcp.tool()
def publish_approved_reddit_draft(draft_id: int) -> dict:
    """Publish one explicitly approved draft. Requires Reddit commercial API permission, configured OAuth, AUTO_PUBLISH_ENABLED=true, and any promotional-link gate."""
    return publish(draft_id)


@mcp.tool()
def run_reddit_daily_workflow(source: str = "queue_only", max_drafts: int = 12) -> dict:
    """Run the daily workflow. queue_only drafts from existing Needle/imported opportunities. reddit_api additionally discovers via Reddit API and is disabled until Reddit commercial API approval is configured."""
    return run_daily(source=source, max_drafts=max_drafts)


@mcp.tool()
def refresh_easyloanworld_sitemap() -> dict:
    """Refresh the EasyLoanWorld URL index used to match Reddit questions with relevant published pages."""
    return {"pages": refresh_sitemap()}


@mcp.tool()
def match_easyloanworld_page(query: str) -> dict:
    """Find the most relevant EasyLoanWorld page for a Reddit question/topic."""
    return {"match": match_page(query)}


@mcp.tool()
def reddit_growth_dashboard() -> dict:
    """Return top opportunities, approval queues and recent daily-run metrics."""
    return dashboard()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
