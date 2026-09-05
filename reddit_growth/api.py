from __future__ import annotations
from typing import Any
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from .config import settings
from .db import init_db, list_drafts
from .service import ingest, opportunity_queue, draft, approve, publish, run_daily, dashboard
from .site_matcher import refresh_sitemap, match_page

app = FastAPI(title=settings.app_name, version="0.1.0", description="Reddit opportunity discovery, scoring, drafting and approval workflow for EasyLoanWorld.")
init_db()


def auth(x_api_key: str | None):
    if settings.app_api_key and x_api_key != settings.app_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


class OpportunityIn(BaseModel):
    thread_url: str
    title: str
    body: str = ""
    subreddit: str | None = None
    reddit_id: str | None = None
    author: str | None = None
    created_utc: float | None = None
    num_comments: int = 0
    ups: int = 0
    external_score: int = Field(default=0, ge=0, le=100)


class IngestRequest(BaseModel):
    source: str = "needle"
    items: list[OpportunityIn]


class DraftRequest(BaseModel):
    opportunity_id: int
    include_link: bool = False


class ApprovalRequest(BaseModel):
    draft_id: int
    approved: bool = True


@app.get("/health")
def health():
    return {"ok": True, "name": settings.app_name}


@app.get("/privacy")
def privacy():
    return {
        "summary": "This self-hosted service stores only opportunity metadata, generated drafts, workflow status and site-page mappings in its configured database. Credentials stay in environment variables. Reddit data should be retained only as permitted by Reddit and your approved use case."
    }


@app.post("/v1/opportunities/ingest")
def ingest_endpoint(req: IngestRequest, x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    return {"saved": ingest([x.model_dump() for x in req.items], source=req.source)}


@app.get("/v1/opportunities")
def opportunities(min_score: int | None = None, status: str | None = None, limit: int = 50, x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    return {"items": opportunity_queue(min_score=min_score, status=status, limit=min(limit, 100))}


@app.post("/v1/drafts")
def make_draft(req: DraftRequest, x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    try:
        return draft(req.opportunity_id, req.include_link)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/v1/drafts")
def drafts(status: str | None = None, limit: int = 50, x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    return {"items": list_drafts(status=status, limit=min(limit, 100))}


@app.post("/v1/drafts/approve")
def approve_endpoint(req: ApprovalRequest, x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    try:
        return approve(req.draft_id, req.approved)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/drafts/{draft_id}/publish")
def publish_endpoint(draft_id: int, x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    try:
        return publish(draft_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/daily-run")
def daily_run(source: str = "reddit_api", max_drafts: int | None = None, x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    try:
        return run_daily(source=source, max_drafts=max_drafts)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/site/refresh")
def refresh_site(x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    try:
        return {"pages": refresh_sitemap()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/v1/site/match")
def site_match(q: str, x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    return {"match": match_page(q)}


@app.get("/v1/dashboard")
def dashboard_endpoint(x_api_key: str | None = Header(default=None)):
    auth(x_api_key)
    return dashboard()
