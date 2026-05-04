# Copilot Instructions for Mixpanel Analysis Starter

- Use environment variables for all credentials; do not hardcode secrets.
- Keep scripts in `src/` and outputs in `data/`.
- Prefer incremental analyses and persist intermediate outputs as JSON or CSV.
- When adding new analysis scripts, include a short section in `README.md` with run instructions.
- If adding API calls, include basic error handling and request timeouts.

## Session Bootstrap

- At the start of each new chat in this repository, read `README.md` first.
- If work is in a request folder, also read that folder's local README (for example `projects/20260423_mixpanel-oh-flows/README.md`) before proposing analysis steps.
- If the user asks for the general source README or shared-code context, read `src/README.md`.
- At the start of each new chat in this repository, read `references/README.md` first.
- If the task is Mixpanel implementation quality, identity, or instrumentation, also read `references/onehome-mixpanel-implementation-audit.md` before proposing changes.
- If `references/confluence/README.md` exists, read it at chat start for documentation context, then read specific files under `references/confluence/` as needed.
- Treat `references/` as project memory for architecture decisions, prior audits, and analytics conventions.

## Project Goal Memory

- For the OneHome personas request, keep this goal explicit in planning and outputs: understand the most common flows of users and agents in OneHome, using cluster-analysis-style behavior grouping to identify personas and explain what they do in OneHome.
