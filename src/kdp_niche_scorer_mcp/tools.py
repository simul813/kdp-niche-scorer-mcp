"""MCP tools for KDP niche scoring.

Pure functions — all MCP wiring lives in server.py.
"""

from __future__ import annotations

from typing import Any

from .rapidapi_client import RapidApiError, search_kindle_books
from .scoring import estimate_revenue, score_books


async def score_niche(
    keyword: str,
    marketplace: str = "US",
    royalty_mode: str = "kindle",
) -> dict[str, Any]:
    """Score a KDP niche keyword on real Amazon Kindle search data.

    Aggregates the top ~20 Kindle search results into a single 0-100 score:
    demand (35), competition (30), pricing (15), indie/recency (10), minus
    up to 25 for top-3 dominance. Pairs the score with estimated monthly
    sales + revenue for each top competitor.

    Args:
        keyword: Search keyword (e.g. "low content journal", "tarot for beginners").
        marketplace: Amazon country code — US, UK, DE, CA, AU (default US).
        royalty_mode: "kindle" (70% royalty, default) or "paperback" (60% - $2.80 print cost).

    Returns:
        {
          keyword, marketplace, score (0-100), band, verdict,
          signals: {demand, competition, pricing, indie_recency, penalty,
                    median_reviews, avg_price, selling_well_count, ...},
          top_competitors: [{asin, title, bsr, price, review_count, est_monthly_revenue}, ...],
          meta: {books_analyzed, source}
        }
    """
    try:
        books = await search_kindle_books(keyword, marketplace=marketplace, limit=20)
    except RapidApiError as e:
        return {
            "error": str(e),
            "suggestion": e.suggestion,
            "keyword": keyword,
        }

    if not books:
        return {
            "keyword": keyword,
            "marketplace": marketplace,
            "score": None,
            "verdict": "no_data",
            "reason": "no_results",
            "suggestion": "Try a broader keyword, or check that the marketplace code is valid.",
        }

    result = score_books(books, keyword)

    competitors = []
    for b in books[:10]:
        bsr = b.get("bsr")
        if bsr:
            revenue = estimate_revenue(bsr, b.get("price"), mode=royalty_mode)
            est_copies = revenue["monthly_copies"]
            est_rev = revenue["monthly_revenue"]
        else:
            est_copies = None
            est_rev = None
        competitors.append({
            "asin": b.get("asin"),
            "title": b.get("title"),
            "bsr": bsr,
            "price": b.get("price"),
            "review_count": b.get("review_count"),
            "rating": b.get("rating"),
            "page_count": b.get("page_count"),
            "independent": b.get("independent", False),
            "est_monthly_copies": est_copies,
            "est_monthly_revenue": est_rev,
        })

    return {
        "keyword": keyword,
        "marketplace": marketplace,
        "score": result["score"],
        "band": result["band"],
        "verdict": _verdict(result["score"]),
        "signals": result["breakdown"],
        "top_competitors": competitors,
        "meta": {
            "books_analyzed": len(books),
            "source": "rapidapi_real_time_amazon_data",
            "royalty_mode": royalty_mode,
            "bsr_available": any(b.get("bsr") for b in books),
            "notes": (
                "Search-endpoint data only. BSR is not returned by /search, so "
                "per-competitor revenue estimates are null and the score falls "
                "back to review-count-based demand. Add /product-details enrichment "
                "(paid tier) for per-ASIN BSR + accurate revenue estimates."
            ),
        },
    }


async def get_top_competitors(
    keyword: str,
    n: int = 10,
    marketplace: str = "US",
    royalty_mode: str = "kindle",
) -> dict[str, Any]:
    """Return the top N Kindle search results for a keyword with full signal data.

    Each result includes ASIN, title, BSR, price, review count, page count,
    rating, and estimated monthly revenue. Useful for drill-down after
    score_niche returns an interesting keyword.

    Args:
        keyword: Search keyword.
        n: Number of competitors to return (1-20, default 10).
        marketplace: Amazon country code — US, UK, DE, CA, AU (default US).
        royalty_mode: "kindle" (default) or "paperback".

    Returns:
        {keyword, marketplace, competitors: [...], meta}
    """
    n = max(1, min(20, n))
    try:
        books = await search_kindle_books(keyword, marketplace=marketplace, limit=n)
    except RapidApiError as e:
        return {
            "error": str(e),
            "suggestion": e.suggestion,
            "keyword": keyword,
        }

    competitors = []
    for b in books[:n]:
        bsr = b.get("bsr")
        if bsr:
            revenue = estimate_revenue(bsr, b.get("price"), mode=royalty_mode)
            est_copies = revenue["monthly_copies"]
            est_rev = revenue["monthly_revenue"]
        else:
            est_copies = None
            est_rev = None
        competitors.append({
            "asin": b.get("asin"),
            "title": b.get("title"),
            "author": b.get("author"),
            "bsr": bsr,
            "price": b.get("price"),
            "review_count": b.get("review_count"),
            "rating": b.get("rating"),
            "page_count": b.get("page_count"),
            "independent": b.get("independent", False),
            "url": b.get("url"),
            "est_monthly_copies": est_copies,
            "est_monthly_revenue": est_rev,
        })

    return {
        "keyword": keyword,
        "marketplace": marketplace,
        "competitors": competitors,
        "meta": {
            "requested": n,
            "returned": len(competitors),
            "source": "rapidapi_real_time_amazon_data",
            "royalty_mode": royalty_mode,
        },
    }


def estimate_sales_from_bsr(
    bsr: int,
    price: float = 6.99,
    mode: str = "kindle",
) -> dict[str, Any]:
    """Estimate monthly copies and revenue for a single ASIN from BSR + price.

    Uses the calibrated BSR-to-sales lookup from the KDP Research Chrome
    extension (Books category baseline). Royalty applied per mode.

    Args:
        bsr: Amazon Best Sellers Rank in the Books category (lower = more sales).
        price: Book list price in USD (default 6.99, within Kindle 70% window).
        mode: "kindle" (70% royalty, default) or "paperback" (60% - $2.80 print cost).

    Returns:
        {bsr, price, mode, daily_copies, monthly_copies, monthly_revenue,
         royalty_per_copy, confidence}
    """
    if bsr is None or bsr <= 0:
        return {
            "error": "bsr must be a positive integer",
            "suggestion": "Pass the Amazon BSR (e.g., 45000). Lower BSR = more sales.",
        }

    est = estimate_revenue(bsr, price, mode=mode)
    return {
        "bsr": bsr,
        "price": price,
        **est,
        "confidence": _bsr_confidence(bsr),
        "notes": (
            "Estimate uses a calibrated BSR-to-sales lookup from the KDP Research "
            "Chrome extension baseline, recalibrated Nov 2025. Not an official "
            "Amazon figure. Accuracy ±30% typical."
        ),
    }


def _verdict(score: int) -> str:
    if score >= 70:
        return "strong_opportunity"
    if score >= 55:
        return "worth_considering"
    if score >= 40:
        return "marginal"
    return "skip"


def _bsr_confidence(bsr: int) -> str:
    """Rough confidence band — BSR lookup is most accurate in the middle ranges."""
    if bsr <= 100 or bsr > 1_000_000:
        return "low"  # power-law breaks at extremes
    if bsr <= 30_000:
        return "high"
    if bsr <= 250_000:
        return "medium"
    return "low"
