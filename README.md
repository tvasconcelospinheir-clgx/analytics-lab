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

## Connector Setup (Mixpanel for Current Request)

If you are running the current Mixpanel request, fill these in `.env`:

- `MIXPANEL_PROJECT_ID`
- `MIXPANEL_SERVICE_ACCOUNT_USERNAME`
- `MIXPANEL_SERVICE_ACCOUNT_SECRET`
- `MIXPANEL_VERIFY_SSL=true`
- `MIXPANEL_CA_BUNDLE=` (optional org CA bundle path)

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
