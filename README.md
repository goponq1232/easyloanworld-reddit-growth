# EasyLoanWorld Reddit Growth Copilot

A deployable Reddit opportunity engine for **EasyLoanWorld.com**. It is designed to automate the repetitive 80–90% of Reddit traffic work without turning your account into a link-spam bot.

## What it does

1. **Discovery**
   - Accepts high-intent Reddit conversations from **Needle** through `ingest_needle_opportunities` / `/v1/opportunities/ingest`.
   - Optionally searches Reddit directly after you have the Reddit permissions/agreement required for your commercial use case.
2. **Opportunity scoring (0–100)**
   - Intent, finance/commercial relevance, freshness, engagement, whether the user is actually asking for help, and whether there is still room to contribute.
3. **EasyLoanWorld matching**
   - Reads the live EasyLoanWorld sitemap and finds the closest relevant published URL.
4. **Reply drafting**
   - Produces a useful Reddit-style answer instead of SEO copy.
   - Daily automation drafts without links by default.
   - Link-bearing drafts are conservative: if subreddit rules are unavailable/unclear, the service removes the promotional link.
5. **Approval queue**
   - Drafts must be explicitly approved before the publish tool will run.
6. **Publishing**
   - Disabled by default.
   - Requires Reddit API approval configuration + OAuth + `AUTO_PUBLISH_ENABLED=true`.
7. **Traffic attribution**
   - When a link is approved, it adds transparent `utm_source=reddit&utm_medium=organic` parameters.
8. **Daily workflow**
   - `scripts/daily_run.py` can be run by cron every morning.

## Important Reddit policy gate

This project is intended to help a commercial finance site acquire traffic. Reddit's current Data API/Developer terms restrict commercial use without the required separate agreement/approval and prohibit using the API to spam. **Do not set `REDDIT_COMMERCIAL_API_APPROVED=true` until your Reddit use case has the permissions/contract Reddit requires.**

That is why Needle/manual import works independently of direct Reddit API discovery, and why automated publishing is off by default.

## ChatGPT integration options in 2026

### Option A — ChatGPT custom MCP app (best if you have Business / Enterprise / Edu)

Run the MCP server publicly over HTTPS and add its `/mcp` URL through ChatGPT Developer Mode / Apps. The server exposes:

- `ingest_needle_opportunities`
- `list_reddit_opportunities`
- `draft_reddit_reply`
- `list_reddit_drafts`
- `approve_reddit_draft`
- `publish_approved_reddit_draft`
- `run_reddit_daily_workflow`
- `refresh_easyloanworld_sitemap`
- `match_easyloanworld_page`
- `reddit_growth_dashboard`

### Option B — existing GPT Action

`openapi.yaml` exposes the same workflow as REST endpoints. This is useful only if you already have an editable GPT that supports Actions.

### Option C — standalone daily automation (works regardless of ChatGPT plan)

Deploy the service and run:

```bash
python scripts/daily_run.py --source queue_only
```

Use Needle to discover opportunities, then ingest them into this service. Once your Reddit commercial API use is approved, you can switch to:

```bash
python scripts/daily_run.py --source reddit_api
```

## Setup

```bash
cp .env.example .env
# fill APP_API_KEY and OPENAI_API_KEY first
pip install -r requirements.txt
python -c "from reddit_growth.db import init_db; init_db()"
python -m reddit_growth.mcp_server
```

The default MCP endpoint is `http://localhost:8000/mcp`.

For the REST API instead:

```bash
uvicorn reddit_growth.api:app --host 0.0.0.0 --port 8000
```

## Needle workflow

Needle is ideal for discovery because it can surface public discussions and intent signals. Normalize each discovered Reddit result to:

```json
{
  "thread_url": "https://www.reddit.com/r/.../comments/...",
  "title": "Should I refinance my student loans?",
  "body": "...",
  "subreddit": "StudentLoans",
  "created_utc": 1780000000,
  "num_comments": 7,
  "ups": 12,
  "external_score": 82
}
```

Then call the MCP tool `ingest_needle_opportunities` or POST it to `/v1/opportunities/ingest`.

## Recommended daily operating rule

- Scan broadly, but draft only threads scoring **65+**.
- Aim for useful answers first; most comments should contain **no EasyLoanWorld link**.
- Only use a link where the thread specifically benefits from a calculator/data/guide you genuinely have.
- Disclose affiliation when linking.
- Never manufacture personal experience or claim to be a borrower/lender/customer if you are not.
- Do not vote on your own material or coordinate votes.
- Stop using a subreddit immediately if moderators/rules disallow the behavior.

## Suggested daily prompt in ChatGPT

> Use Needle to find new Reddit threads from the last 24 hours about personal loans, debt consolidation, credit scores, mortgages/home equity, student loans, and small-business finance. Prioritize people asking for advice or comparisons. Send the best opportunities into EasyLoanWorld Reddit Growth Copilot, then show me the top 10 scoring 65+ and draft useful replies for the top 5. Do not include links unless I explicitly request a link-bearing version after reviewing the subreddit rules.

## Data stored

SQLite stores opportunity metadata, scoring, drafts, workflow states, recent runs, and cached EasyLoanWorld sitemap URLs. Secrets remain in environment variables.
