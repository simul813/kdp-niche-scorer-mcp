"""RapidAPI Real-Time Amazon Data client.

Wraps the /search endpoint at real-time-amazon-data.p.rapidapi.com.
Defensive parsing — real responses routinely omit fields the docs list.

The search endpoint does NOT return BSR per-product. score_books() already
handles that by falling back to review-count-based demand when <40% of tiles
have BSR — that's the documented reviews-fallback path from the extension.
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx
from cachetools import TTLCache

# 24-hour cache on search results — BSR fluctuates hourly but author-level
# niche decisions don't, and search-page data is nearly static over a day.
_search_cache: TTLCache = TTLCache(maxsize=500, ttl=86_400)


# Kindle Store browse-node IDs by marketplace.
# Passing these as category_id narrows the search to Kindle-only results.
# Source: Amazon browse-node reference.
KINDLE_CATEGORY_IDS: dict[str, str] = {
    "US": "133140011",
    "UK": "341677031",
    "GB": "341677031",
    "DE": "530484031",
    "CA": "2980423011",
    "AU": "4851985051",
}


class RapidApiError(Exception):
    """Error from the RapidAPI client — includes an LLM-friendly suggestion."""

    def __init__(self, message: str, suggestion: str = ""):
        super().__init__(message)
        self.suggestion = suggestion


def _parse_price(value: Any) -> float | None:
    """Parse '$7.99', '7,99 €', '£5.49' etc. to float. Returns None if unparseable."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    # Strip everything except digits, dot, and comma; normalize EU decimal comma.
    cleaned = re.sub(r"[^\d.,]", "", value)
    if not cleaned:
        return None
    # "7,99" (EU) vs "1,299.99" (US with thousands separator)
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_int(value: Any) -> int | None:
    """Parse '1,234' or 1234 to int. Returns None if unparseable."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        cleaned = re.sub(r"[^\d]", "", value)
        if cleaned:
            try:
                return int(cleaned)
            except ValueError:
                return None
    return None


def _parse_float(value: Any) -> float | None:
    """Parse '4.5' or 4.5 to float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _normalize_product(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a RapidAPI product dict to the shape scoring.score_books() expects.

    Fields guaranteed to be present:
      asin, title, price, review_count, rating, url
    Optional (may be None):
      bsr, page_count, author, pub_date, independent
    """
    return {
        "asin": raw.get("asin") or raw.get("ASIN") or "",
        "title": raw.get("product_title") or raw.get("title") or "",
        "author": raw.get("product_byline") or raw.get("author"),
        "price": _parse_price(
            raw.get("product_price")
            or raw.get("price")
            or raw.get("product_minimum_offer_price")
        ),
        "review_count": _parse_int(raw.get("product_num_ratings") or raw.get("reviews_count")) or 0,
        "rating": _parse_float(raw.get("product_star_rating") or raw.get("rating")),
        "url": raw.get("product_url") or raw.get("url"),
        "image": raw.get("product_photo") or raw.get("image"),
        # Search endpoint does not return these — included as keys so downstream
        # code can rely on the shape. score_books() handles None gracefully.
        "bsr": None,
        "page_count": None,
        "pub_date": None,
        "independent": False,
        # Demand-signal hint from the search tile when the API exposes it.
        "sales_volume_hint": raw.get("sales_volume"),
        "is_best_seller": bool(raw.get("is_best_seller")),
        "is_amazon_choice": bool(raw.get("is_amazon_choice")),
    }


def _marketplace_code(marketplace: str) -> str:
    """Normalize marketplace to the 2-letter country code RapidAPI expects."""
    mp = (marketplace or "US").upper().strip()
    # Accept both UK and GB — the API uses GB
    if mp == "UK":
        return "GB"
    return mp


async def search_kindle_books(
    keyword: str,
    marketplace: str = "US",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search Amazon Kindle Store for a keyword, return normalized product list.

    Args:
        keyword: Search keyword (e.g. "low content journal").
        marketplace: Country code — US, UK (alias GB), DE, CA, AU.
        limit: Max products to return (1-40).

    Raises:
        RapidApiError: if the API is misconfigured, unauthorized, or unreachable.
    """
    if not keyword or not keyword.strip():
        raise RapidApiError(
            "keyword is required",
            "Pass a non-empty search keyword, e.g. 'low content journal'.",
        )

    api_key = os.getenv("RAPIDAPI_KEY", "").strip()
    if not api_key:
        raise RapidApiError(
            "RAPIDAPI_KEY is not configured",
            "Set it locally in .env for dev, or run: mcpize secrets set RAPIDAPI_KEY your-key. "
            "Get a free key at https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-amazon-data",
        )

    host = os.getenv("RAPIDAPI_HOST", "real-time-amazon-data.p.rapidapi.com").strip()
    country = _marketplace_code(marketplace)
    limit = max(1, min(40, limit))

    cache_key = f"search:{country}:{keyword.lower().strip()}:{limit}"
    cached = _search_cache.get(cache_key)
    if cached is not None:
        return cached

    params = {
        "query": keyword,
        "country": country,
        "page": "1",
        "sort_by": "RELEVANCE",
    }
    category_id = KINDLE_CATEGORY_IDS.get(country)
    if category_id:
        params["category_id"] = category_id

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": host,
    }
    url = f"https://{host}/search"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)
    except httpx.TimeoutException:
        raise RapidApiError(
            "RapidAPI request timed out after 30 seconds",
            "The upstream service may be slow. Try again in a moment.",
        ) from None
    except httpx.RequestError as e:
        raise RapidApiError(
            f"Network error contacting RapidAPI: {e}",
            "Check your internet connection.",
        ) from e

    if response.status_code == 401 or response.status_code == 403:
        raise RapidApiError(
            f"RapidAPI rejected the request (HTTP {response.status_code})",
            "Verify RAPIDAPI_KEY is correct and that you're subscribed to the "
            "'Real-Time Amazon Data' API on rapidapi.com.",
        )
    if response.status_code == 429:
        raise RapidApiError(
            "RapidAPI rate limit exceeded (HTTP 429)",
            "Free tier is 100 req/mo. Wait for monthly reset or upgrade the plan.",
        )
    if response.status_code >= 400:
        raise RapidApiError(
            f"RapidAPI returned HTTP {response.status_code}",
            f"Response body: {response.text[:200]}",
        )

    try:
        payload = response.json()
    except ValueError:
        raise RapidApiError(
            "RapidAPI returned a non-JSON response",
            f"Body preview: {response.text[:200]}",
        ) from None

    # Defensive extraction — 'data.products' is the documented shape, but some
    # API versions return 'products' at the top level.
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    products_raw = data.get("products") if isinstance(data, dict) else None
    if not isinstance(products_raw, list):
        # Not an error case — just no results. Cache empty so we don't retry.
        _search_cache[cache_key] = []
        return []

    normalized = [_normalize_product(p) for p in products_raw[:limit] if isinstance(p, dict)]
    _search_cache[cache_key] = normalized
    return normalized
