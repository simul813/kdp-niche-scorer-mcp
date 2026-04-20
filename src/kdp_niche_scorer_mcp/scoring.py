"""Niche scoring + revenue estimation.

Ported verbatim from the KDP Research Chrome extension:
  lib/niche-score.js -> score_books()
  lib/revenue.js     -> daily_copies(), royalty helpers, estimate_revenue()

Niche score (0-100):
  Demand          35 pts — how many of top 10 sell well by BSR
  Competition     30 pts — median review count (fewer = easier)
  Pricing         15 pts — average price calibrated for low-content books
  Indie + Recency 10 pts — indie wins + recent publication bonuses
  Top-3 Penalty  -25 pts — if top 3 books hoard sales
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

BSR_SELLING_WELL = 100_000
BSR_GREAT = 30_000

PRICE_MIN_GOOD = 5.99
PRICE_MAX_GOOD = 9.99

TWELVE_MONTHS_MS = 365 * 24 * 60 * 60 * 1000
EIGHTEEN_MONTHS_MS = 548 * 24 * 60 * 60 * 1000


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _parse_pub_date_ms(value: Any) -> int | None:
    """Parse a pub date value into milliseconds since epoch, or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Assume milliseconds; accept seconds too if clearly too small
        v = float(value)
        if v < 1e11:  # seconds
            v *= 1000
        return int(v)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except ValueError:
            return None
    return None


def score_books(books: list[dict[str, Any]], keyword: str = "") -> dict[str, Any]:
    """Score a niche from the top-10 Kindle search results.

    Each book dict may contain:
      title (str), bsr (int|None), review_count (int), price (float),
      pub_date (iso str or ms), independent (bool)

    Returns a dict: { score, band, breakdown: {...} }
    """
    if not books:
        return {"score": 0, "band": "No data", "breakdown": {}}

    top10 = books[:10]

    kw = (keyword or "").lower().strip()
    title_matches = (
        sum(1 for b in top10 if kw and kw in (b.get("title") or "").lower())
        if kw
        else 0
    )

    # 1. Demand (35 pts)
    selling_well = [b for b in top10 if b.get("bsr") and b["bsr"] <= BSR_SELLING_WELL]
    great_sellers = [b for b in top10 if b.get("bsr") and b["bsr"] <= BSR_GREAT]
    books_with_bsr = sum(1 for b in top10 if b.get("bsr"))

    if books_with_bsr >= len(top10) * 0.4:
        demand_ratio = len(selling_well) / len(top10)
        great_ratio = len(great_sellers) / len(top10)
        demand = round(35 * (demand_ratio * 0.7 + great_ratio * 0.3))
        demand_source = "bsr"
    else:
        reviewed = sum(1 for b in top10 if (b.get("review_count") or 0) >= 20)
        well_reviewed = sum(1 for b in top10 if (b.get("review_count") or 0) >= 100)
        demand = round(
            35 * (reviewed / len(top10) * 0.5 + well_reviewed / len(top10) * 0.5)
        )
        demand_source = "reviews"

    # 2. Competition (30 pts)
    review_counts = sorted((b.get("review_count") or 0) for b in top10)
    median = review_counts[len(review_counts) // 2] if review_counts else 0
    if median < 20:
        competition = 30
    elif median < 50:
        competition = 25
    elif median < 100:
        competition = 18
    elif median < 250:
        competition = 10
    elif median < 500:
        competition = 5
    else:
        competition = 0

    # 3. Pricing (15 pts)
    prices = [b["price"] for b in top10 if isinstance(b.get("price"), (int, float)) and b["price"] > 0]
    avg_price = sum(prices) / len(prices) if prices else 0.0
    if PRICE_MIN_GOOD <= avg_price <= PRICE_MAX_GOOD:
        pricing = 15
    elif 0 < avg_price < PRICE_MIN_GOOD:
        pricing = 6
    elif PRICE_MAX_GOOD < avg_price <= 14.99:
        pricing = 10
    elif avg_price > 14.99:
        pricing = 4
    else:
        pricing = 0

    # 4. Indie + Recency (10 pts)
    now_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    indie_recency = 0.0
    for b in top10:
        if b.get("independent"):
            indie_recency += 1
        pub_ms = _parse_pub_date_ms(b.get("pub_date"))
        bsr = b.get("bsr")
        if pub_ms and bsr and bsr <= BSR_SELLING_WELL:
            age = now_ms - pub_ms
            if age < TWELVE_MONTHS_MS:
                indie_recency += 3
            elif age < EIGHTEEN_MONTHS_MS:
                indie_recency += 1.5
    indie_recency = min(10.0, indie_recency)

    # 5. Top-3 dominance penalty (-25 pts)
    penalty = 0
    if len(top10) >= 6:
        top3_bsrs = [b["bsr"] for b in top10[:3] if b.get("bsr")]
        rest_bsrs = [b["bsr"] for b in top10[3:10] if b.get("bsr")]
        top3_avg = _average(top3_bsrs)
        rest_avg = _average(rest_bsrs)
        if top3_avg and rest_avg and top3_avg * 4 < rest_avg:
            penalty = 25
        elif top3_avg and rest_avg and top3_avg * 2 < rest_avg:
            penalty = 12

    total = max(0, min(100, demand + competition + pricing + indie_recency - penalty))
    rounded = round(total)

    return {
        "score": rounded,
        "band": band_for(rounded),
        "breakdown": {
            "demand": demand,
            "demand_source": demand_source,
            "competition": competition,
            "pricing": pricing,
            "indie_recency": round(indie_recency * 10) / 10,
            "penalty": penalty,
            "median_reviews": median,
            "avg_price": round(avg_price * 100) / 100,
            "selling_well_count": len(selling_well),
            "indie_count": sum(1 for b in top10 if b.get("independent")),
            "title_matches": title_matches,
            "title_match_ratio": title_matches / len(top10) if top10 else 0,
        },
    }


def band_for(score: int) -> str:
    """Map a numeric score to a qualitative band."""
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Great"
    if score >= 55:
        return "Good"
    if score >= 40:
        return "Okay"
    if score >= 25:
        return "Weak"
    return "Poor"


# ---------------------------------------------------------------------------
# Revenue estimation — ported from lib/revenue.js
# ---------------------------------------------------------------------------


def daily_copies(bsr: int | float | None) -> float:
    """Rough daily copies sold at a given BSR in the Books category."""
    if not bsr or bsr <= 0:
        return 0.0
    if bsr <= 100:
        return 900
    if bsr <= 500:
        return 300
    if bsr <= 1000:
        return 120
    if bsr <= 5000:
        return 35
    if bsr <= 10000:
        return 15
    if bsr <= 30000:
        return 6
    if bsr <= 50000:
        return 3
    if bsr <= 100000:
        return 1.5
    if bsr <= 250000:
        return 0.7
    if bsr <= 500000:
        return 0.3
    if bsr <= 1000000:
        return 0.1
    return 0.03


def royalty_per_copy_paperback(price: float | None) -> float:
    """KDP paperback royalty: price * 0.6 - $2.80 print cost, floored at $0.40.

    Matches the Chrome extension calc (low-content / ~100 pages assumption).
    """
    if not price or price <= 0:
        return 2.0
    return max(0.4, price * 0.6 - 2.80)


def royalty_per_copy_kindle(price: float | None) -> float:
    """KDP Kindle royalty: 70% within the $2.99–$9.99 window, 35% otherwise.

    Kindle has no print cost, so the formula is cleaner than paperback.
    """
    if not price or price <= 0:
        return 0.0
    if 2.99 <= price <= 9.99:
        return price * 0.70
    return price * 0.35


def estimate_revenue(
    bsr: int | float | None,
    price: float | None,
    mode: str = "kindle",
) -> dict[str, float | int]:
    """Estimate monthly copies and revenue from BSR + price.

    Args:
        bsr: Amazon Best Sellers Rank (lower = more sales).
        price: Book price in USD.
        mode: "kindle" (default, 70% royalty) or "paperback" (60% - $2.80 print cost).
    """
    daily = daily_copies(bsr)
    monthly_copies = round(daily * 30)

    if mode == "paperback":
        royalty = royalty_per_copy_paperback(price)
    else:
        royalty = royalty_per_copy_kindle(price)

    monthly_revenue = round(monthly_copies * royalty)
    return {
        "daily_copies": daily,
        "monthly_copies": monthly_copies,
        "monthly_revenue": monthly_revenue,
        "royalty_per_copy": round(royalty * 100) / 100,
        "mode": mode,
    }
