# Deployment checklist

## Fastest path today

### 1) Keep Needle connected
Use Needle for public-conversation discovery and buying/problem-solving intent. The included `NEEDLE_TO_PLUGIN_PROMPT.txt` is the discovery brief.

### 2) Deploy this backend
Good targets: Railway, Render, Fly.io, a small VPS, or any Docker host with HTTPS.

Minimum environment variables:

- `APP_API_KEY`
- `OPENAI_API_KEY`
- `SITE_BASE_URL=https://easyloanworld.com`
- `SITEMAP_URL=https://easyloanworld.com/sitemap_index.xml`

Start with:

- `REDDIT_COMMERCIAL_API_APPROVED=false`
- `AUTO_PUBLISH_ENABLED=false`
- `ALLOW_PROMOTIONAL_LINKS=false`

### 3) Refresh EasyLoanWorld URLs
Run once after deployment:

```bash
curl -X POST "https://YOUR-DOMAIN/v1/site/refresh" -H "X-API-Key: YOUR_KEY"
```

### 4) Import Needle results
Send normalized Reddit opportunities to `/v1/opportunities/ingest`, or use the MCP tool `ingest_needle_opportunities` on an eligible ChatGPT workspace.

### 5) Automate the daily queue
Run this every day:

```bash
python scripts/daily_run.py --source queue_only
```

This creates no-link drafts for new qualified opportunities. It does not publish.

### 6) Review and approve
Review pending drafts in `/v1/dashboard` or through the MCP tools. Approve only comments that are genuinely useful and fit the subreddit rules.

## Native ChatGPT custom-app route

OpenAI's current custom MCP app path is through Developer Mode on eligible managed workspaces. Deploy the MCP server over HTTPS, then add the server endpoint:

```text
https://YOUR-DOMAIN/mcp
```

If your account/workspace does not expose custom MCP app creation, use the standalone backend + Needle + scheduled workflow instead.

## Existing GPT Action route

If you already have an editable GPT that supports Actions, replace `https://YOUR-DOMAIN.example` in `openapi.yaml` with your deployed domain and import the schema into the GPT Action editor. Configure `X-API-Key` authentication.

## Reddit API route — only after approval

This project is for commercial traffic acquisition. Before enabling direct Reddit API discovery/posting, obtain whatever commercial/API approval or agreement Reddit requires for the use case.

After approval:

1. Register the Reddit app and obtain OAuth credentials/refresh token.
2. Fill `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_REFRESH_TOKEN`, and a truthful `REDDIT_USER_AGENT`.
3. Set `REDDIT_COMMERCIAL_API_APPROVED=true`.
4. Keep `AUTO_PUBLISH_ENABLED=false` while testing discovery/rules.
5. Only after reviewing behavior, set `AUTO_PUBLISH_ENABLED=true`.
6. Publishing still requires each draft to have `approval_status=approved`.

## Recommended operating targets

- 30–100 candidate threads/day discovered.
- 10–20 opportunities/day scoring 65+.
- 5–12 high-quality reply drafts/day.
- Most replies should be no-link.
- 0–3 link-bearing replies/day, only where subreddit rules and context support it.
- Measure sessions, engaged sessions, calculator use, email signups, and downstream value — not raw backlink count.
