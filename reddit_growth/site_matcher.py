from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import httpx
from .config import settings
from .db import get_site_pages, replace_site_pages
from .scoring import lexical_similarity, tokenize


def _title_hint_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    slug = path.split("/")[-1] if path else "home"
    return re.sub(r"[-_]+", " ", slug)


def _locs(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    out = []
    for elem in root.iter():
        if elem.tag.endswith("loc") and elem.text:
            out.append(elem.text.strip())
    return out


def refresh_sitemap(max_sitemaps: int = 50, max_urls: int = 10000) -> int:
    seen_sitemaps: set[str] = set()
    pages: set[str] = set()
    queue = [settings.sitemap_url]
    with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "EasyLoanWorldGrowth/1.0"}) as client:
        while queue and len(seen_sitemaps) < max_sitemaps and len(pages) < max_urls:
            url = queue.pop(0)
            if url in seen_sitemaps:
                continue
            seen_sitemaps.add(url)
            r = client.get(url)
            r.raise_for_status()
            locs = _locs(r.text)
            if "<sitemapindex" in r.text.lower():
                for loc in locs:
                    if loc not in seen_sitemaps:
                        queue.append(loc)
            else:
                for loc in locs:
                    if loc.startswith(settings.site_base_url) and len(pages) < max_urls:
                        pages.add(loc)
    rows = []
    for url in sorted(pages):
        title = _title_hint_from_url(url)
        rows.append((url, title, " ".join(sorted(tokenize(title + " " + url)))))
    return replace_site_pages(rows)


def match_page(query: str, min_similarity: float = 0.06) -> dict | None:
    pages = get_site_pages()
    if not pages:
        try:
            refresh_sitemap()
            pages = get_site_pages()
        except Exception:
            pages = []
    best = None
    best_score = 0.0
    for p in pages:
        hay = f"{p.get('title_hint','')} {p.get('tokens','')} {p['url']}"
        score = lexical_similarity(query, hay)
        if score > best_score:
            best_score = score
            best = p
    if best and best_score >= min_similarity:
        return {"url": best["url"], "title_hint": best.get("title_hint"), "similarity": round(best_score, 4)}
    return None
