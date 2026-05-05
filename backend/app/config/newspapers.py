"""
Newspaper configuration and URL management.
"""
from typing import Dict, List
from pydantic import BaseModel, HttpUrl


class NewspaperConfig(BaseModel):
    """Configuration for a single newspaper source."""
    name: str
    key: str  # Identifier used in code (e.g., "prothom_alo")
    base_url: str
    language: str  # "bengali" or "english"
    enabled: bool = True
    scraper_type: str  # Type of scraper to use
    selectors: Dict[str, str]  # CSS selectors for scraping


# Newspaper configurations
NEWSPAPER_CONFIGS: Dict[str, NewspaperConfig] = {
    "prothom_alo": NewspaperConfig(
        name="প্রথম আলো",
        key="prothom_alo",
        base_url="https://www.prothomalo.com",
        language="bengali",
        enabled=True,
        scraper_type="prothom_alo",
        selectors={
            "article_list": ".story-card",
            "article_title": "h1.headline",
            "article_content": ".story-content",
            "article_date": ".publish-time"
        }
    ),
    "daily_star": NewspaperConfig(
        name="ডেইলি স্টার",
        key="daily_star",
        base_url="https://bangla.thedailystar.net",
        language="bengali",
        enabled=True,
        scraper_type="daily_star",
        selectors={
            "article_list": ".article-item",
            "article_title": "h1",
            "article_content": ".article-body",
            "article_date": ".date"
        }
    ),
    "jugantor": NewspaperConfig(
        name="যুগান্তর",
        key="jugantor",
        base_url="https://www.jugantor.com",
        language="bengali",
        enabled=True,
        scraper_type="jugantor",
        selectors={
            "article_list": ".news-item",
            "article_title": "h1",
            "article_content": ".news-content",
            "article_date": ".date"
        }
    ),
    "samakal": NewspaperConfig(
        name="সমকাল",
        key="samakal",
        base_url="https://samakal.com",
        language="bengali",
        enabled=True,
        scraper_type="samakal",
        selectors={
            "article_list": ".article",
            "article_title": "h1.title",
            "article_content": ".article-content",
            "article_date": ".publish-date"
        }
    ),
    "naya_diganta": NewspaperConfig(
        name="নয়া দিগন্ত",
        key="naya_diganta",
        base_url="https://dailynayadiganta.com",
        language="bengali",
        enabled=True,
        scraper_type="naya_diganta",
        selectors={
            "article_list": ".post-title",
            "article_title": "h1.post-title",
            "article_content": ".post-body",
            "article_date": "time"
        }
    ),
    "ittefaq": NewspaperConfig(
        name="ইত্তেফাক",
        key="ittefaq",
        base_url="https://www.ittefaq.com.bd",
        language="bengali",
        enabled=True,
        scraper_type="ittefaq",
        selectors={
            "article_list": ".content_detail_each_group",
            "article_title": "h1",
            "article_content": ".content_detail_each_group",
            "article_date": "script[type='application/ld+json']"
        }
    )
}


def get_enabled_newspapers() -> List[NewspaperConfig]:
    """Get list of enabled newspapers."""
    return [config for config in NEWSPAPER_CONFIGS.values() if config.enabled]


def get_newspaper_config(key: str) -> NewspaperConfig:
    """Get configuration for a specific newspaper."""
    config = NEWSPAPER_CONFIGS.get(key)
    if not config:
        raise ValueError(f"Unknown newspaper: {key}")
    return config


def get_all_newspaper_keys() -> List[str]:
    """Get list of all newspaper keys."""
    return list(NEWSPAPER_CONFIGS.keys())
