from __future__ import annotations
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from .config import settings


def add_utm(url: str, *, subreddit: str, thread_id: str) -> str:
    parts = urlsplit(url)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    q.update({
        "utm_source": "reddit",
        "utm_medium": "organic",
        "utm_campaign": "reddit_growth",
        "utm_content": f"{subreddit}_{thread_id}"[:120],
    })
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


def draft_reply(opportunity: dict, matched_page: dict | None, include_link: bool = False, rules_text: str = "") -> dict:
    if include_link and not settings.allow_promotional_links:
        include_link = False

    target_url = matched_page.get("url") if matched_page else None
    utm_url = add_utm(target_url, subreddit=opportunity.get("subreddit") or "reddit", thread_id=str(opportunity.get("reddit_id") or opportunity.get("id") or "thread")) if target_url else None

    if not settings.openai_api_key:
        return {
            "body": _fallback(opportunity, utm_url if include_link else None),
            "include_link": include_link and bool(utm_url),
            "target_url": target_url,
            "utm_url": utm_url,
            "used_ai": False,
        }

    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)
    link_instruction = (
        f"A relevant EasyLoanWorld resource is {utm_url}. Include it only once, naturally, after giving the answer. "
        "Disclose the relationship plainly (for example, 'I work on EasyLoanWorld')."
        if include_link and utm_url else
        "Do not include or mention EasyLoanWorld or any URL."
    )
    prompt = f"""
You are drafting a Reddit reply for a finance discussion. The goal is to be genuinely useful first; traffic is secondary.

Thread title: {opportunity.get('title','')}
Thread body: {opportunity.get('body','')}
Subreddit: r/{opportunity.get('subreddit','')}
Subreddit rules/context: {rules_text or 'Unknown. Be conservative.'}

Requirements:
- Answer the user's actual question directly and specifically.
- Sound like a normal knowledgeable Reddit user, not an SEO article or sales copy.
- No fabricated personal experience, credentials, numbers, rates, laws, or lender claims.
- Do not tell the user to DM.
- No keyword stuffing, no hype, no repeated brand mentions.
- If the question needs current lender rates/laws and they are not provided, say the user should verify current terms rather than inventing them.
- Prefer 120-260 words unless the thread clearly needs less.
- {link_instruction}
- If subreddit rules appear to prohibit self-promotion, links, or commercial content, do not include a link even if one was requested.

Return only the final Reddit comment text.
""".strip()
    resp = client.responses.create(model=settings.openai_model, input=prompt)
    body = resp.output_text.strip()
    link_in_body = bool(utm_url and utm_url in body)
    return {
        "body": body,
        "include_link": link_in_body,
        "target_url": target_url,
        "utm_url": utm_url,
        "used_ai": True,
    }


def _fallback(opportunity: dict, url: str | None) -> str:
    title = opportunity.get("title", "your question")
    body = (
        f"For {title.lower()}, I’d separate the decision into three parts: total cost, monthly cash-flow impact, "
        "and the downside if your situation changes. Compare the APR/fees rather than only the payment, check "
        "whether there are prepayment or origination charges, and run the numbers under a conservative scenario. "
        "If you share the amount, term, approximate credit range, and the offers you’re comparing, people here can "
        "usually give much more specific feedback."
    )
    if url:
        body += f" I work on EasyLoanWorld; this related guide may help with the calculations/details: {url}"
    return body
