# KDP Niche Scorer MCP

AI-native Amazon KDP niche scoring — feed a keyword, get BSR, competitor count, page count, review velocity, and estimated monthly sales as one opinionated score.

[![Available on MCPize](https://img.shields.io/badge/MCPize-Available-blue)](https://mcpize.com/mcp/kdp-niche-scorer-mcp)

Built for self-published Kindle authors who want their AI agent (Claude, ChatGPT, Cursor) to pick their next book niche on real data — not vibes. Competes with Publisher Rocket ($199), KDSPY ($47), Helium 10 ($39–249/mo). This one lives inside your LLM workflow.

## Install (hosted on MCPize)

The fastest way to use it — no local setup, OAuth handled for you:

```bash
# Claude Code
claude mcp add --transport http kdp-niche-scorer https://kdp-niche-scorer-mcp.mcpize.run/mcp

# Cursor
cursor mcp add kdp-niche-scorer https://kdp-niche-scorer-mcp.mcpize.run/mcp

# Windsurf
windsurf mcp add kdp-niche-scorer https://kdp-niche-scorer-mcp.mcpize.run/mcp
```

Or grab it from the marketplace: **https://mcpize.com/mcp/kdp-niche-scorer-mcp**

### Pricing (hosted)

- **Free** — 5 requests/day. Enough to score a couple of niches per session.
- **Pro $9/mo** — 30 requests/day (~900/mo). For active indie authors.
- **Author $29/mo** — 150 requests/day (~4,500/mo). Multi-niche / agency use.

## Tools

| Tool | What it does |
|------|--------------|
| `score_niche` | Full opinionated 0–100 score for a KDP keyword (demand + competition + pricing + indie/recency − top-3 dominance). |
| `get_top_competitors` | Top N Kindle search results with BSR, price, reviews, page count, est. monthly revenue. |
| `estimate_sales_from_bsr` | BSR + price → est. monthly copies and royalty revenue (Kindle 70% default; paperback opt-in). |

## Scoring formula

Ported verbatim from the `KDP Research` Chrome extension. Out of 100:

- **Demand (35)** — share of top 10 selling well by BSR. Falls back to review-count signals when BSR isn't exposed by the search endpoint.
- **Competition (30)** — median review count of top 10 (fewer = easier).
- **Pricing (15)** — average price in the $5.99–$9.99 low-content sweet spot.
- **Indie + Recency (10)** — indie wins + recent publication bonuses.
- **Top-3 Dominance (−25)** — if top 3 books hoard sales vs positions 4–10.

Bands: Excellent (85+), Great (70+), Good (55+), Okay (40+), Weak (25+), Poor (<25).

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- A [RapidAPI](https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-amazon-data) key for the **Real-Time Amazon Data** API. Free tier = 100 req/mo, no card.

## Quick Start

```bash
# Install dependencies
uv sync

# Set up your .env
cp .env.example .env
# edit .env and paste your RAPIDAPI_KEY

# Start the server with hot reload + interactive playground
mcpize dev --playground
```

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `RAPIDAPI_KEY` | ✅ | Your Real-Time Amazon Data key. [Sign up free](https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-amazon-data). |
| `RAPIDAPI_HOST` | ❌ | Override API host (default `real-time-amazon-data.p.rapidapi.com`). |
| `PORT` | ❌ | Server port (default 8080 in production, 3000 under `mcpize dev`). |
| `ENV` | ❌ | Set to `production` to disable colorized dev logging. |

## Development

```bash
uv run pytest            # Unit tests (22 offline tests covering the scoring formula)
uv run ruff check .      # Lint
uv run ruff format .     # Format
mcpize dev               # Hot-reload server on :3000
mcpize dev --playground  # Same + browser playground via public tunnel
mcpize doctor            # Sanity-check the build before deploy
bash test-mcp.sh         # MCP protocol smoke test (server must be running)
```

## Deploy

```bash
mcpize login                                # once
mcpize secrets set RAPIDAPI_KEY your-key    # set production secret
mcpize deploy                               # ship
```

## Data sources

**v1 (this server)**: RapidAPI Real-Time Amazon Data `/search` endpoint only. Gets title, price, review count, rating per result. BSR is not returned by the search endpoint — the scoring formula's built-in review-based demand fallback handles this gracefully.

**v2 (future)**: Keepa API for historical BSR + review velocity; Amazon Creators API once eligible.

## Example

```
score_niche(keyword="low content journal", marketplace="US")
→ {
    score: 62,
    band: "Good",
    verdict: "worth_considering",
    signals: { demand: 21, competition: 25, pricing: 15, indie_recency: 1, penalty: 0, ... },
    top_competitors: [ { asin, title, price, review_count, est_monthly_revenue }, ... ]
  }
```

## License

MIT
