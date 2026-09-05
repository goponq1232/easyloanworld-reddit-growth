from __future__ import annotations
import math
import re
import time
from typing import Any

HIGH_INTENT = [
    "recommend", "best", "which", "should i", "help", "advice", "compare", "worth it",
    "how do i", "how can i", "where can i", "rate", "apr", "refinance", "consolidate",
    "pay off", "credit score", "loan", "mortgage", "heloc", "debt", "student loan",
]
COMMERCIAL_INTENT = [
    "lender", "loan", "apr", "rate", "refinance", "consolidation", "mortgage", "credit card",
    "borrow", "financing", "heloc", "home equity", "student loan", "business loan",
]
QUESTION_MARKERS = ["?", "any advice", "what should", "does anyone", "can someone", "thoughts"]
SPAMMY = ["promo code", "referral code", "dm me", "telegram", "whatsapp me"]


def _contains(text: str, phrases: list[str]) -> int:
    t = text.lower()
    return sum(1 for p in phrases if p in t)


def score_opportunity(item: dict[str, Any], now_utc: float | None = None) -> tuple[int, dict[str, Any]]:
    now = now_utc or time.time()
    text = f"{item.get('title','')} {item.get('body','')}".strip()
    age_hours = max(0.0, (now - float(item.get("created_utc") or now)) / 3600)
    comments = max(0, int(item.get("num_comments") or 0))
    upvotes = max(0, int(item.get("ups") or item.get("score") or 0))

    intent_hits = _contains(text, HIGH_INTENT)
    commercial_hits = _contains(text, COMMERCIAL_INTENT)
    question_hits = _contains(text, QUESTION_MARKERS)
    spam_hits = _contains(text, SPAMMY)

    intent = min(30, intent_hits * 6)
    commercial = min(20, commercial_hits * 4)
    question = min(12, question_hits * 6)

    if age_hours <= 2:
        freshness = 18
    elif age_hours <= 6:
        freshness = 15
    elif age_hours <= 12:
        freshness = 12
    elif age_hours <= 24:
        freshness = 8
    elif age_hours <= 72:
        freshness = 4
    else:
        freshness = 0

    engagement = min(12, int(math.log2(comments + upvotes + 2) * 2.4))
    room_to_help = 8 if comments <= 10 else 5 if comments <= 30 else 2
    length_quality = 4 if 40 <= len(text) <= 4000 else 1
    penalty = min(25, spam_hits * 10)

    total = max(0, min(100, intent + commercial + question + freshness + engagement + room_to_help + length_quality - penalty))
    breakdown = {
        "intent": intent,
        "commercial_relevance": commercial,
        "question_signal": question,
        "freshness": freshness,
        "engagement": engagement,
        "room_to_help": room_to_help,
        "content_quality": length_quality,
        "penalty": penalty,
        "age_hours": round(age_hours, 2),
    }
    return total, breakdown


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    stop = {"the", "a", "an", "to", "for", "of", "and", "or", "in", "on", "with", "is", "are", "how", "what", "this", "that", "guide", "complete"}
    return {w for w in words if len(w) > 2 and w not in stop}


def lexical_similarity(a: str, b: str) -> float:
    sa, sb = tokenize(a), tokenize(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)
