# Launch Checklist: KDP Niche Scorer

Listing: https://mcpize.com/mcp/kdp-niche-scorer-mcp
Gateway: https://kdp-niche-scorer-mcp.mcpize.run/mcp
Edit:    https://mcpize.com/developer/servers/e3d9e592-8d2a-4412-91f4-65e5e76c9f37/manage

## Pre-Launch (done)
- [x] Server deployed to MCPize Cloud
- [x] Marketplace listing published
- [x] SEO metadata configured (Marketing category, 4 tags)
- [x] Pricing set: Free / Pro $9 / Author $29
- [x] AI logo generated
- [x] README updated with hosted install snippets + pricing
- [x] Production secret RAPIDAPI_KEY configured
- [x] No error logs from production

## Pre-Launch (to do)
- [ ] **Rotate the RapidAPI key** in rapidapi.com dashboard, then `mcpize secrets set RAPIDAPI_KEY <new-key>` (the original was pasted in chat)
- [ ] Push project to a public GitHub repo (so the README, badge, and "open source btw" tweet land)
- [ ] Upload a custom logo if you don't like the AI-generated one (dashboard > General tab)
- [ ] Email your existing **KDP Research Chrome extension users** about the MCP version with a few free Pro days

## Launch Day
- [ ] Twitter/X — post the variant B tweet (link below), then drop the marketplace URL in a reply
- [ ] r/selfpublish — "I built an AI niche scorer that ports my Chrome extension's algorithm" (offer 2 weeks Pro free for early users)
- [ ] r/KDP — same framing, audience-tuned
- [ ] r/mcp — technical Show-style post
- [ ] 20BooksTo50K Facebook group — demo screenshot of `score_niche` output

## Week 1
- [ ] Reply to "what tool do you use" threads on Kindlepreneur / Self Publishing Show comments
- [ ] LinkedIn post (drop the corporate "excited to share" — use builder voice from `/mcpize:publish`)
- [ ] Discord: MCP community, indie author servers (Self Publishing School, Kindlepreneur)
- [ ] Watch `mcpize logs --severity ERROR` daily
- [ ] Watch first subscribers via the dashboard

## Week 2
- [ ] Hacker News — "Show HN: KDP Niche Scorer — Publisher Rocket for AI agents"
- [ ] YouTube short demo: "I asked Claude to pick my next Kindle niche"

## Week 3-4
- [ ] Dev.to / Hashnode tutorial: "How I ported my Chrome extension to an MCP server in a weekend"
- [ ] Iterate scoring weights based on first 50 user runs
- [ ] Decide whether to add v1.1: `/product-details` enrichment for real BSR (paid tier feature)

## Success Markers
- **Week 1:** 50 marketplace installs, 5 paying users
- **Month 1:** 500 installs, 50 paying users (~$500/mo gross)
- **Month 3:** 2,500 installs, 250 paying users (~$2,500/mo gross)
- **Month 6:** 1,000+ paying users, $10k+ MRR
