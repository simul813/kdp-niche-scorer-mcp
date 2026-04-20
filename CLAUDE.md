# KDP Niche Scorer — Dev Guide

Python MCP server that scores Amazon KDP niches. Built on FastMCP 2.x with Streamable HTTP transport.

## Project Structure

```
src/kdp_niche_scorer_mcp/
  server.py           # FastMCP setup, middleware, tool registration, entry point
  tools.py            # MCP tools — score_niche, get_top_competitors, estimate_sales_from_bsr
  scoring.py          # Ported from niche-score.js + revenue.js (the moat)
  rapidapi_client.py  # Wraps Real-Time Amazon Data /search, with 24h TTL cache
  __init__.py
  py.typed
tests/
  conftest.py         # Fixtures: strong_niche_books, saturated_niche_books, dominated, no_bsr
  test_tools.py       # 22 offline tests covering scoring formula + revenue helpers
mcpize.yaml           # RAPIDAPI_KEY secret declared here
pyproject.toml        # deps: fastmcp, rich, httpx, cachetools
Dockerfile            # Multi-stage, Cloud Run ready
Makefile              # make dev / run / test / lint / format
```

## Key Commands

- `uv sync` — install deps (after editing pyproject.toml, regenerate lock: `uv lock`)
- `uv run pytest` — run all offline tests
- `uv run ruff check .` — lint
- `mcpize dev` — local server on :3000 with hot reload, auto-loads `.env`
- `mcpize dev --playground` — same + browser-based MCP playground via tunnel
- `mcpize doctor` — validate config + Dockerfile before deploy
- `mcpize secrets set RAPIDAPI_KEY your-key` — set prod secret
- `mcpize deploy` — ship to MCPize Cloud
- `mcpize diagnose` — AI-powered debugging if deploy fails
- `bash test-mcp.sh` — MCP protocol smoke test (server must be running on :3000)

## The Scoring Formula (Don't Touch Lightly)

`scoring.score_books(books, keyword)` is ported verbatim from the KDP Research Chrome extension. Constants, weights, and thresholds match the source:

- `BSR_SELLING_WELL = 100_000`, `BSR_GREAT = 30_000`
- `PRICE_MIN_GOOD = 5.99`, `PRICE_MAX_GOOD = 9.99`
- Demand max 35, Competition max 30, Pricing max 15, Indie/Recency max 10, Penalty up to −25
- Review-based demand fallback kicks in when <40% of top-10 have BSR (the common case since the search endpoint doesn't return BSR)

If you tune any coefficient, also update the corresponding test in `test_tools.py::TestScoreBooks` so the change is intentional, not silent.

## Adding a Tool

1. **Write the function in `tools.py`** — async if it hits an API. Type hints + docstring are the schema and tool description.
2. **Register in `server.py`** — add to the `.tools import ...` line and `mcp.tool()(your_tool)`.
3. **Test it** — add a test class in `test_tools.py`. If it calls RapidAPI, mock the response via `tests/fixtures/` or put it in `test_tools_live.py` (manual, opt-in).

## RapidAPI Client Notes

- `search_kindle_books(keyword, marketplace, limit)` — the only call we make today.
- 24-hour TTL cache on `(country, keyword, limit)` — BSR fluctuates hourly but author-level niche decisions don't, and this keeps us inside the 100 req/mo free tier.
- Kindle category IDs per marketplace live in `KINDLE_CATEGORY_IDS`. Passed as `category_id` to narrow to Kindle-only results.
- All error paths raise `RapidApiError` with an LLM-friendly `.suggestion` field.
- Price parsing handles `$7.99`, `7,99 €`, `£5.49` — strips currency symbols + normalizes EU decimal comma.
- `UK` marketplace is aliased to `GB` automatically (API expects ISO country codes).

## Environment

| Var | Default | Notes |
|-----|---------|-------|
| `RAPIDAPI_KEY` | — | Required. Store in `.env` locally; `mcpize secrets set` in prod. |
| `RAPIDAPI_HOST` | `real-time-amazon-data.p.rapidapi.com` | Override only if the API provider changes. |
| `PORT` | `8080` | `mcpize dev` overrides to 3000. |
| `ENV` | `development` | Set to `production` to silence dev logging middleware. |
| `LOG_LEVEL` | `INFO` | Standard Python logging level. |

## Common Pitfalls

- **Search endpoint doesn't return BSR.** That's expected — the review-count fallback path kicks in. If you want BSR enrichment, add a `/product-details` call per ASIN (doubles API cost; gate behind a paid tier).
- **Rate limits on free tier are 100 req/mo.** Cache is your friend; don't bypass it.
- **RapidAPI sometimes returns `products` at the top level instead of `data.products`.** The client handles both shapes defensively. If you see `total_found: 0` on a common query, log the raw response to see which shape came back.
- **Don't URL-encode category_id.** `httpx` handles it correctly via `params=`. Avoid constructing the URL manually.

## Publishing

After `mcpize deploy` succeeds, run `/mcpize:publish` to handle SEO, pricing tiers, logo, marketplace listing, and go-to-market content. The publish skill reads this repo and the MCPize dashboard state to do it end-to-end.
