from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _csv(name: str, default: str) -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "EasyLoanWorld Reddit Growth Copilot")
    app_base_url: str = os.getenv("APP_BASE_URL", "http://localhost:8000")
    app_api_key: str = os.getenv("APP_API_KEY", "")
    database_path: str = os.getenv("DATABASE_PATH", "./data/reddit_growth.db")
    site_base_url: str = os.getenv("SITE_BASE_URL", "https://easyloanworld.com")
    sitemap_url: str = os.getenv("SITEMAP_URL", "https://easyloanworld.com/sitemap_index.xml")

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5")

    reddit_commercial_api_approved: bool = _bool("REDDIT_COMMERCIAL_API_APPROVED", False)
    reddit_client_id: str = os.getenv("REDDIT_CLIENT_ID", "")
    reddit_client_secret: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    reddit_refresh_token: str = os.getenv("REDDIT_REFRESH_TOKEN", "")
    reddit_user_agent: str = os.getenv("REDDIT_USER_AGENT", "EasyLoanWorldGrowth/1.0")

    auto_publish_enabled: bool = _bool("AUTO_PUBLISH_ENABLED", False)
    allow_promotional_links: bool = _bool("ALLOW_PROMOTIONAL_LINKS", False)
    max_drafts_per_day: int = _int("MAX_DRAFTS_PER_DAY", 12)
    max_publishes_per_day: int = _int("MAX_PUBLISHES_PER_DAY", 3)
    min_opportunity_score: int = _int("MIN_OPPORTUNITY_SCORE", 65)

    default_subreddits: list[str] = None  # type: ignore[assignment]
    default_keywords: list[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        object.__setattr__(self, "default_subreddits", _csv(
            "DEFAULT_SUBREDDITS",
            "personalfinance,StudentLoans,CreditCards,CRedit,Debt,loans,FirstTimeHomeBuyer,Mortgages,smallbusiness",
        ))
        object.__setattr__(self, "default_keywords", _csv(
            "DEFAULT_KEYWORDS",
            "personal loan,debt consolidation,credit score,mortgage refinance,student loan,HELOC,bad credit loan,business loan",
        ))
        Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
