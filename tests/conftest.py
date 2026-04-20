"""Pytest fixtures for KDP niche scorer tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def strong_niche_books() -> list[dict]:
    """Top 10 books for a healthy niche — decent BSR, moderate reviews, good pricing."""
    return [
        {"asin": "B0001", "title": "Pick One Niche Beginner", "bsr": 25_000,  "review_count": 45,  "price": 7.99, "independent": True,  "pub_date": "2025-06-01"},
        {"asin": "B0002", "title": "Pick One Complete Guide", "bsr": 38_000,  "review_count": 28,  "price": 8.99, "independent": True,  "pub_date": "2025-03-10"},
        {"asin": "B0003", "title": "Pick One Workbook",        "bsr": 62_000,  "review_count": 12,  "price": 6.99, "independent": True,  "pub_date": "2025-01-15"},
        {"asin": "B0004", "title": "Another Title",            "bsr": 75_000,  "review_count": 40,  "price": 7.49, "independent": False, "pub_date": "2024-09-01"},
        {"asin": "B0005", "title": "Niche Fundamentals",       "bsr": 88_000,  "review_count": 18,  "price": 6.99, "independent": True,  "pub_date": "2025-08-20"},
        {"asin": "B0006", "title": "A Niche Journal",          "bsr": 92_000,  "review_count": 22,  "price": 7.99, "independent": True,  "pub_date": "2024-12-01"},
        {"asin": "B0007", "title": "Niche Handbook",           "bsr": 115_000, "review_count": 8,   "price": 8.49, "independent": False, "pub_date": "2024-06-10"},
        {"asin": "B0008", "title": "Niche Planner",            "bsr": 130_000, "review_count": 15,  "price": 6.99, "independent": True,  "pub_date": "2025-11-01"},
        {"asin": "B0009", "title": "Niche Mastery",            "bsr": 160_000, "review_count": 10,  "price": 9.99, "independent": False, "pub_date": "2023-05-10"},
        {"asin": "B0010", "title": "Niche for Dummies",        "bsr": 210_000, "review_count": 5,   "price": 7.99, "independent": True,  "pub_date": "2025-02-01"},
    ]


@pytest.fixture
def saturated_niche_books() -> list[dict]:
    """Top 10 for a saturated niche — huge review counts, priced too high."""
    return [
        {"asin": "S0001", "title": "Saturated Bestseller 1", "bsr": 800,   "review_count": 8_500, "price": 14.99, "independent": False, "pub_date": "2020-01-01"},
        {"asin": "S0002", "title": "Saturated Bestseller 2", "bsr": 2_500, "review_count": 5_200, "price": 16.99, "independent": False, "pub_date": "2021-01-01"},
        {"asin": "S0003", "title": "Saturated Bestseller 3", "bsr": 4_800, "review_count": 3_100, "price": 17.99, "independent": False, "pub_date": "2019-06-01"},
        {"asin": "S0004", "title": "Saturated 4",            "bsr": 12_000, "review_count": 1_200, "price": 15.49, "independent": False, "pub_date": "2022-03-01"},
        {"asin": "S0005", "title": "Saturated 5",            "bsr": 18_000, "review_count":   900, "price": 14.99, "independent": False, "pub_date": "2022-05-01"},
        {"asin": "S0006", "title": "Saturated 6",            "bsr": 25_000, "review_count":   750, "price": 16.49, "independent": False, "pub_date": "2021-09-01"},
        {"asin": "S0007", "title": "Saturated 7",            "bsr": 35_000, "review_count":   600, "price": 15.99, "independent": False, "pub_date": "2020-11-01"},
        {"asin": "S0008", "title": "Saturated 8",            "bsr": 48_000, "review_count":   520, "price": 18.99, "independent": False, "pub_date": "2021-04-01"},
        {"asin": "S0009", "title": "Saturated 9",            "bsr": 70_000, "review_count":   480, "price": 19.99, "independent": False, "pub_date": "2019-10-01"},
        {"asin": "S0010", "title": "Saturated 10",           "bsr": 95_000, "review_count":   410, "price": 16.99, "independent": False, "pub_date": "2022-07-01"},
    ]


@pytest.fixture
def dominated_niche_books() -> list[dict]:
    """Top 3 crush positions 4-10 — classic dominance penalty case."""
    return [
        {"asin": "D0001", "title": "Giant 1", "bsr": 500,     "review_count": 4_000, "price": 7.99, "independent": False},
        {"asin": "D0002", "title": "Giant 2", "bsr": 800,     "review_count": 2_500, "price": 8.99, "independent": False},
        {"asin": "D0003", "title": "Giant 3", "bsr": 1_200,   "review_count": 1_800, "price": 6.99, "independent": False},
        {"asin": "D0004", "title": "Minnow 4", "bsr": 150_000, "review_count": 20,   "price": 7.99, "independent": True},
        {"asin": "D0005", "title": "Minnow 5", "bsr": 180_000, "review_count": 15,   "price": 8.49, "independent": True},
        {"asin": "D0006", "title": "Minnow 6", "bsr": 220_000, "review_count": 10,   "price": 6.99, "independent": True},
        {"asin": "D0007", "title": "Minnow 7", "bsr": 260_000, "review_count":  8,   "price": 7.99, "independent": True},
        {"asin": "D0008", "title": "Minnow 8", "bsr": 300_000, "review_count":  5,   "price": 6.99, "independent": True},
        {"asin": "D0009", "title": "Minnow 9", "bsr": 340_000, "review_count":  3,   "price": 7.49, "independent": True},
        {"asin": "D0010", "title": "Minnow 10", "bsr": 400_000, "review_count": 2,   "price": 8.99, "independent": True},
    ]


@pytest.fixture
def no_bsr_books() -> list[dict]:
    """Amazon blocked BSR enrichment — should trigger the review-based demand fallback."""
    return [
        {"asin": f"N{i:04}", "title": f"Book {i}", "bsr": None, "review_count": rc, "price": 7.99, "independent": True}
        for i, rc in enumerate([150, 120, 90, 80, 70, 55, 40, 30, 25, 22])
    ]
