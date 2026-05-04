# Analytics Lab

Reusable analytics workspace for request-based projects.

Each request should live in its own folder under `projects/`, with isolated data, notebooks, and outputs.

## Folder Purpose

- `projects/`: request-specific work folders.
- `projects/20260423_mixpanel-oh-flows/`: current request implementation.
- `references/`: static reference material and notes.
- `scratchpad/`: temporary local experiments.
- `scripts/`: helper scripts for project scaffolding.
- `shared_data/`: cross-project shared datasets.
- `src/`: reusable shared code.
- `src/common/`: generic utilities (exports, QA helpers).
- `src/connectors/`: external-system/API connectors.

## Current Request

### Goal (OneHome Personas)

The product goal for the current request is to understand the most common flows of users and agents in OneHome, using cluster-analysis-style behavioral patterns to identify practical personas and explain what each persona is doing in OneHome.

- `projects/20260423_mixpanel-oh-flows/run.py`: main runner for this request.
- `projects/20260423_mixpanel-oh-flows/data/raw/`: raw pulled data.
- `projects/20260423_mixpanel-oh-flows/data/processed/`: cleaned outputs.
- `projects/20260423_mixpanel-oh-flows/notebooks/`: exploratory notebooks.
- `projects/20260423_mixpanel-oh-flows/outputs/`: share-ready deliverables.

## Environment Setup

1. Create `.env` from `.env.example`.
2. Create Conda environment:
   - `conda env create -f environment.yml`
   - `conda activate analytics_base`

## GitHub Push Conventions

- **Push after any significant change** — new analysis, phase completions, schema/connector updates, README edits.
- **Always push the whole workspace**, not just the active project. Both `projects/` and `src/` are updated together; a project-only push leaves the connector or shared code out of sync.
- Exclude secrets — `.env` is gitignored and must never be committed. Store credentials in session only.

```
git add .                          # stage all workspace changes (except .gitignored)
git commit -m "short description"
git push origin main
```

---

## API Rate Limit Best Practices

When querying external APIs (Mixpanel, Confluence, or any future connector), always respect published rate limits to avoid being blocked.

**Mixpanel Query API limits (as of 2026):**
- Max 5 concurrent queries
- Max 60 queries per hour
- Returns HTTP 429 when exceeded

**Required connector behavior:**
- Space requests by at least 61 seconds (`MIXPANEL_MIN_REQUEST_INTERVAL_SECONDS=61` in `.env`)
- Retry on 429 with exponential backoff, honoring `Retry-After` headers (`MIXPANEL_MAX_RETRIES=6`)
- Never fire parallel JQL queries in a loop without a delay
- Consolidate multiple filters into a single query where possible instead of running separate queries

The `MixpanelClient` in `src/connectors/mixpanel.py` implements this automatically. Do not bypass it with raw `requests` calls.

**Reference:** https://developer.mixpanel.com/reference/rate-limits

## Connector Setup (Mixpanel for Current Request)

If you are running the current Mixpanel request, fill these in `.env`:

- `MIXPANEL_PROJECT_ID`
- `MIXPANEL_SERVICE_ACCOUNT_USERNAME`
- `MIXPANEL_SERVICE_ACCOUNT_SECRET`
- `MIXPANEL_VERIFY_SSL=true`
- `MIXPANEL_CA_BUNDLE=` (optional org CA bundle path)
- `MIXPANEL_MIN_REQUEST_INTERVAL_SECONDS=61` (recommended default to respect Query API 60 queries/hour)
- `MIXPANEL_MAX_RETRIES=6` (automatic retries when API returns 429 rate-limited)

## Connector Setup (Confluence Context for Workspace Chats)

To provide Confluence documentation context in Copilot chats for this workspace, configure these variables in `.env`:

- `CONFLUENCE_BASE_URL` (example: `https://your-company.atlassian.net`)
- `CONFLUENCE_EMAIL`
- `CONFLUENCE_API_TOKEN`
- `CONFLUENCE_SPACE_KEY`
- `CONFLUENCE_PAGE_LIMIT=25`
- `CONFLUENCE_VERIFY_SSL=true`
- `CONFLUENCE_CA_BUNDLE=` (optional org CA bundle path)

Sync local Confluence context cache:

- `python scripts/sync_confluence_context.py`

This writes lightweight documentation snapshots into `references/confluence/` so chat sessions can read local context quickly.

## Run Current Request

- `python projects/20260423_mixpanel-oh-flows/run.py`

## Start a New Request Folder

- `python scripts/run_request.py <project-name>`

Example:

- `python scripts/run_request.py pendo-onboarding`
