from __future__ import annotations
import time
from dataclasses import dataclass
import httpx
from .config import settings


class RedditComplianceError(RuntimeError):
    pass


class RedditAuthError(RuntimeError):
    pass


@dataclass
class TokenCache:
    access_token: str = ""
    expires_at: float = 0.0


_cache = TokenCache()


def _require_commercial_approval() -> None:
    if not settings.reddit_commercial_api_approved:
        raise RedditComplianceError(
            "Reddit API is disabled. This project is intended to support a commercial website, so set "
            "REDDIT_COMMERCIAL_API_APPROVED=true only after you have the permissions/agreement Reddit requires."
        )


def _token() -> str:
    _require_commercial_approval()
    if _cache.access_token and _cache.expires_at > time.time() + 60:
        return _cache.access_token
    missing = [k for k, v in {
        "REDDIT_CLIENT_ID": settings.reddit_client_id,
        "REDDIT_CLIENT_SECRET": settings.reddit_client_secret,
        "REDDIT_REFRESH_TOKEN": settings.reddit_refresh_token,
    }.items() if not v]
    if missing:
        raise RedditAuthError("Missing Reddit OAuth settings: " + ", ".join(missing))
    with httpx.Client(timeout=20) as client:
        r = client.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(settings.reddit_client_id, settings.reddit_client_secret),
            data={"grant_type": "refresh_token", "refresh_token": settings.reddit_refresh_token},
            headers={"User-Agent": settings.reddit_user_agent},
        )
        r.raise_for_status()
        data = r.json()
    if "access_token" not in data:
        raise RedditAuthError(f"Reddit token exchange failed: {data}")
    _cache.access_token = data["access_token"]
    _cache.expires_at = time.time() + int(data.get("expires_in", 3600))
    return _cache.access_token


def _headers() -> dict[str, str]:
    return {"Authorization": f"bearer {_token()}", "User-Agent": settings.reddit_user_agent}


def search(query: str, subreddit: str | None = None, limit: int = 25, sort: str = "new", time_filter: str = "week") -> list[dict]:
    endpoint = f"https://oauth.reddit.com/r/{subreddit}/search" if subreddit else "https://oauth.reddit.com/search"
    params = {"q": query, "restrict_sr": "on" if subreddit else "off", "sort": sort, "t": time_filter, "limit": min(limit, 100), "raw_json": 1}
    with httpx.Client(timeout=30) as client:
        r = client.get(endpoint, params=params, headers=_headers())
        r.raise_for_status()
        children = r.json().get("data", {}).get("children", [])
    out = []
    for child in children:
        d = child.get("data", {})
        out.append({
            "reddit_id": d.get("name") or ("t3_" + d.get("id", "")),
            "id": d.get("id"),
            "thread_url": "https://www.reddit.com" + d.get("permalink", ""),
            "subreddit": d.get("subreddit"),
            "title": d.get("title", ""),
            "body": d.get("selftext", ""),
            "author": d.get("author"),
            "created_utc": d.get("created_utc"),
            "num_comments": d.get("num_comments", 0),
            "ups": d.get("ups", 0),
            "over_18": d.get("over_18", False),
            "locked": d.get("locked", False),
        })
    return out


def subreddit_rules(subreddit: str) -> list[dict]:
    with httpx.Client(timeout=20) as client:
        r = client.get(f"https://oauth.reddit.com/r/{subreddit}/about/rules", headers=_headers(), params={"raw_json": 1})
        r.raise_for_status()
        data = r.json()
    return [{"short_name": x.get("short_name"), "description": x.get("description"), "kind": x.get("kind")} for x in data.get("rules", [])]


def comment(parent_fullname: str, text: str) -> dict:
    _require_commercial_approval()
    if not settings.auto_publish_enabled:
        raise RedditComplianceError("Publishing is disabled. Set AUTO_PUBLISH_ENABLED=true only after testing and approval.")
    with httpx.Client(timeout=30) as client:
        r = client.post(
            "https://oauth.reddit.com/api/comment",
            headers=_headers(),
            data={"thing_id": parent_fullname, "text": text, "api_type": "json", "raw_json": 1},
        )
        r.raise_for_status()
        data = r.json()
    errors = data.get("json", {}).get("errors", [])
    if errors:
        raise RuntimeError(f"Reddit comment failed: {errors}")
    things = data.get("json", {}).get("data", {}).get("things", [])
    if not things:
        return {"ok": True, "raw": data}
    thing = things[0].get("data", {})
    cid = thing.get("name") or thing.get("id", "")
    permalink = thing.get("permalink")
    return {"ok": True, "comment_id": cid, "url": ("https://www.reddit.com" + permalink) if permalink else None}
