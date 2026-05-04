# Copilot Instructions for Mixpanel Analysis Starter

- Use environment variables for all credentials; do not hardcode secrets.
- Keep scripts in `src/` and outputs in `data/`.
- Prefer incremental analyses and persist intermediate outputs as JSON or CSV.
- When adding new analysis scripts, include a short section in `README.md` with run instructions.
- If adding API calls, include basic error handling and request timeouts.

## Session Bootstrap

- At the start of each new chat in this repository, read `README.md` first.
- If work is in a request folder, read that folder's README (for example `projects/20260423_mixpanel-oh-flows/README.md`) before proposing analysis steps. This README is the single source of truth — it contains the full plan, phase status, flow configurations, and Mixpanel query rules. Do not look for a separate PLAN.md.
- If the user asks for the general source README or shared-code context, read `src/README.md`.
- At the start of each new chat in this repository, read `references/README.md` first.
- If the task is Mixpanel implementation quality, identity, or instrumentation, also read `references/onehome-mixpanel-implementation-audit.md` before proposing changes.
- If `references/confluence/README.md` exists, read it at chat start for documentation context, then read specific files under `references/confluence/` as needed.
- Treat `references/` as project memory for architecture decisions, prior audits, and analytics conventions.

## Project Goal Memory

- For the OneHome personas request, keep this goal explicit in planning and outputs: understand the most common flows of users and agents in OneHome, using cluster-analysis-style behavior grouping to identify personas and explain what they do in OneHome.

## OneHome Mixpanel Query Rules

- The Mixpanel project (ID 2175557) contains events from 12+ different apps (Matrix, OneHome, Realist, Agent Portal, etc.). ALL API queries for OneHome analysis MUST filter by `e.properties.appId === 'OneHome'` in JQL, or `app_id='OneHome'` via `event_counts_by_app()`. Never use `event_counts_last_n_days()` for OneHome — it has no appId filter and returns cross-app data.
- In the Mixpanel UI, always apply two filters when building OneHome reports: `appId = OneHome` AND `Basic Event Cleaner = True`. The Basic Event Cleaner is a UI-only Data View filter and cannot be replicated in JQL; API counts will be slightly higher than UI counts as a result.
- Phase 1 validation (API vs UI) confirmed: with `appId=OneHome` applied, counts match within ~0.2%. Any larger discrepancy means the appId filter is missing or broken.
