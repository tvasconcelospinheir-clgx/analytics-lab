# OneHome Persona Discovery
Last updated: 2026-05-03

**Goal:** Understand the most common flows of users and agents in OneHome using cluster-analysis-style behavioral grouping to identify personas and explain what each does in OneHome.

---

## ⚠️ Critical: Mixpanel Query Rules for This Project

The Mixpanel project (ID 2175557) contains events from 12+ apps (Matrix, OneHome, Realist, Agent Portal, etc.).

**Every query for this project MUST filter by `appId = OneHome`.**

- **API (JQL):** filter with `e.properties.appId === 'OneHome'`
- **Connector method:** always use `client.event_counts_by_app(app_id='OneHome', ...)` — never `event_counts_last_n_days()`, which has no appId filter and returns cross-app data.
- **UI (Mixpanel):** apply filter `appId = OneHome` AND `Basic Event Cleaner = True`.
- `Basic Event Cleaner` is a UI-only Data View filter — it cannot be applied in JQL. API counts will be slightly higher than UI counts (~0.2% gap confirmed in Phase 1).

**Forgetting this filter returns cross-app totals and completely wrong numbers.**

---

## Execution Order & Gates

```
Phase 0 ✅ DONE — simulation completed
    ↓
Phase 1 ✅ PASSED — API vs UI within 0.2%
    ↓
Phase 2 ✅ PASSED — all properties confirmed
    ↓
Phase 3 — [You export Users CSV with groupId]
    GATE: agent differentiator found or ruled out
    ↓
Phase 4 — [Me write segmentation strategy]
    GATE: you approve the strategy
    ↓
Phase 5 — [Me write exact Flow configs] + [You run Flows + export CSVs]
    GATE: CSVs received (up to ~20 files)
    ↓
Phase 6 — [Me cluster analysis]
    GATE: clusters approved by you
    ↓
Phase 7 — [Me API validation] + [optional: you simulate again]
    GATE: clusters pass validation
    ↓
Phase 8 — [Me persona cards]
```

---

## Phase 0 — Manual Simulation ✅ COMPLETED

**Goal:** Discover events and properties from the ground up before touching any API.

**Findings:**
- `groupId` — likely the key property to distinguish agents from consumers. Update Phase 3 accordingly.
- `deviceType` — potentially interesting for platform split (may complement or replace `isMobileApp`).
- Anchor events confirmed: the ones in our custom bundles appear to be the right signal events.
- `authenticated` observed to flip from `false` → `true` after login — confirms it is an **event-level property** (session state), not a user property.
- Hypothesis: `registered` may be a **user/people property** (static, set once after signup) while `authenticated` is dynamic per session.

**Open question carried to Phase 2:** Confirm `registered` is a People property and what values it takes.

---

## Phase 1 — Validate API Access ✅ PASSED

**Goal:** Confirm API data matches what you see in Mixpanel UI.

**Result:** Top events matched in order, volumes within 0.2%. Phase 1 gate passed.

**Required filters:**
- API: `e.properties.appId === 'OneHome'` in JQL
- UI: `appId = OneHome` AND `Basic Event Cleaner = True`

**Top events confirmed (7-day, appId=OneHome):**

| # | Event | API count |
|---|---|---|
| 1 | Property Details - Photo Viewer - Right Arrow Click | 37,299,437 |
| 2 | Property Details - Landed | 13,530,397 |
| 3 | Entry Link - Session Not Logged In | 7,679,107 |
| 4 | Rateplug - Rateplug Failure - API Error | 6,645,218 |
| 5 | Initial App Load | 5,841,042 |

---

## Phase 2 — Open Property Questions ✅ COMPLETED

| # | Question | Answer |
|---|---|---|
| Q1 | Does `registered` exist as a People property? What values? | ✅ Yes — user-level property. Values: `true` / `false`. Stable sign-up status, set once. |
| Q2 | Does `ViewMode` exist as an event property? Values? | ✅ Yes — values: `1` (1,825,544) · `3` (1,182,000) · `4` (231,657) · `2` (3,595) · `5` (1) |
| Q3a | Does `isMobileApp` exist? | ✅ Yes — `false`: 3,140,143 · `true`: 1,866. Very skewed; use `deviceType` as primary. |
| Q3b | Does `deviceType` exist? | ✅ Yes — `mobile`: 2,696,946 · `desktop`: 751,817 · `tablet`: 156,727 · `unknown`: 5. Use alongside `isMobileApp`. |
| Q4 | Any other interesting properties? | None surfaced beyond what was already known. |
| Q5 | Is `authenticated` stable per user or event-level? | ✅ Event-level property (flips per session). `registered` is the stable user-level property (sign-up status). |

**Key decisions from Phase 2:**
- Use `ViewMode` values: `1` = Matrix email, `3` = Agent-shared link, `4` = Consumer-shared link. OH-02 flows confirmed.
- Use `deviceType` as primary platform split (`mobile` / `desktop` / `tablet`). Keep `isMobileApp` as secondary cross-check.
- `registered` (People property, true/false) → use for user-level cohort segmentation.
- `authenticated` (event property, flips per session) → use for session-level Flow splits.
- OH-03 and OH-07 confirmed viable.

**Phase 2 gate: PASSED. Proceeding to Phase 3.**

---

## Phase 3 — Agent vs Consumer Differentiator Investigation 🔲 NEXT

**Updated hypothesis from Phase 0:** `groupId` may be the key differentiator.

**What you do [UI]:** Run a **Users/People report** in Mixpanel:
- Columns: `distinct_id`, `AgentID`, `groupId`, any email/name/username field visible
- No filter
- Export top 200 rows as CSV → send me

**What I look for:**
- Is `groupId` populated only for agents? Does it correlate with `AgentID`?
- Does `distinct_id == AgentID` for any rows?
- Do `AgentID` values follow a recognizable pattern (e.g., all 6-digit MLS member IDs)?
- Is there a `$email` or `$name` super property that distinguishes types?

---

## Phase 4 — Segmentation Strategy Decision 🔲 Pending

**Input:** Answers from Phases 2 and 3.

**What I do:** Write a single paragraph — the agreed segmentation strategy. Primary split, secondary splits, what we're treating as proxies and why.

**Gate:** You approve this before any Flow is configured.

---

## Phase 5 — Build Flows 🔲 Pending

**Segmentation strategy:** TBD after Phase 4.
- Likely primary split: `authenticated` (session-level) or `groupId`/`registered` (user-level)
- Likely secondary splits: `ViewMode` (entry context), `deviceType` or `isMobileApp` (platform)

**For each flow (where applicable):** Run once for `authenticated=false` and once for `authenticated=true`. Export Top Paths CSV per run.

### OH-01 — Post App Load (All Sessions)
**Anchor A:** `Initial App Load` | **Steps after A:** 5 | **Counting:** Sessions
**Hide:** `What's New - Flow - "Next" Click`, `What's New - Welcome Screen Pop Up`, `What's New - Flow - Cancel Click`
**View:** Top Paths — expand to top 10 rows | **Save as:** `OH-01 - Post App Load (All Sessions)`

### OH-02 — Entry Context by Referral Type (ViewMode splits)
*Conditional: only if Q2 in Phase 2 confirms ViewMode exists with values 1/3/4*

Build 4 parallel flows, same config, different filters:
- **OH-02a:** `ViewMode = 1` → Entry via Matrix Email
- **OH-02b:** `ViewMode = 3` → Entry via Agent-Shared Link
- **OH-02c:** `ViewMode = 4` → Entry via Consumer-Shared Link
- **OH-02d:** No ViewMode filter → Entry Direct/Organic

**Anchor A:** First `Property Details - Landed` after entry | **Steps after A:** 5 | **Counting:** Sessions

### OH-03 — Post App Load: Mobile vs Web
*Conditional: only if `isMobileApp` or `deviceType` confirmed in Phase 2*

Duplicate OH-01, add breakdown by `isMobileApp` (true/false) or `deviceType`.
**Save as:** `OH-03 - Post App Load: Mobile vs Web`

### OH-04 — Browse to Property Details Journey
**Anchor A:** `Browse Properties - Landed` | **Anchor B:** `Property Details - Landed`
**Steps between A and B:** show all | **Steps after B:** 5 | **Counting:** Sessions
**Hide between steps:** `[Custom] Photo Browsing`
**Save as:** `OH-04 - Browse to Property Details`

### OH-05a — Property Details Full Behavior (Unfiltered)
**Anchor A:** `Property Details - Landed` | **Steps after A:** 7 | **Counting:** Sessions
**Do NOT hide anything** — let `[Custom] Photo Browsing` dominate.
**Save as:** `OH-05a - Property Details (All)`

### OH-05b — Property Details Excluding Photo Scrollers ← KEY PERSONA SEPARATOR
Duplicate OH-05a, add **Exclusion step:** users who did `[Custom] Photo Browsing` at any step after A.
**Save as:** `OH-05b - Property Details (Excluding Photo Scrollers)`

### OH-06 — Paths to High-Intent Actions (3 end-anchored flows)
- **OH-06a:** End anchor = `[Custom] High Intent Action`, steps before: 5, Counting: Uniques
- **OH-06b:** End anchor = `Property Details - "Favorite" Click`, steps before: 5, Counting: Uniques
- **OH-06c:** End anchor = `Property Details - Schedule a Tour Click`, steps before: 5, Counting: Uniques

### OH-07 — Authentication Friction After Anonymous Entry
*Conditional: only if `authenticated` confirmed as stable enough in Phase 2 Q5*

**Anchor A:** `Entry Link - Session Not Logged In` | **Steps after A:** 5 | **Counting:** Sessions
**Add breakdown by:** `isMobileApp` if available
**Save as:** `OH-07 - Auth Friction After Anonymous Entry`

### OH-08 — Compare Feature Adoption
**Anchor A:** `Compare Page - Landed` | **Steps before A:** 4 | **Steps after A:** 4 | **Counting:** Sessions
**Save as:** `OH-08 - Compare Feature Adoption`

### OH-09 — PropertyFit Onboarding Drop-off
*Conditional: only if recent PropertyFit activity confirmed via API*

**Anchor A:** `PropertyFit Onboarding - Flow - What describes you best? - Choice Selection`
**Anchor B:** `PropertyFit Onboarding - Flow - Skip Click` OR `PropertyFit Onboarding - Rank Features - Rank Features Click`
**View:** Sankey (NOT Top Paths) | **Counting:** Uniques
**Save as:** `OH-09 - PropertyFit Onboarding Drop-off`

### OH-10 — Browsing Landed to Property Details Landed
**Anchor A:** `Browsing - Landed` | **Anchor B:** `Property Details - Landed`
**Steps between A and B:** show all | **Steps after B:** 3 | **Counting:** Sessions
**Save as:** `OH-10 - Browsing Landed to Property Details Landed`

---

## Phase 6 — Cluster Analysis 🔲 Pending

**Input:** Top Paths CSVs from Phase 5.

**What I do:** Parse all path sequences, compute edit-distance similarity, identify 3–7 natural clusters. For each cluster describe: typical entry event, which custom bundles appear, path depth, whether a High Intent event appears.

**Rule:** No persona names yet. Behavior descriptions only. You review and confirm before we name anything.

---

## Phase 7 — Validation 🔲 Pending

**Goal:** Test that clusters actually predict behavior on fresh data.

**Pass criteria:** Each cluster covers >2% of users AND has a meaningfully different conversion rate from the others.

---

## Phase 8 — Persona Synthesis 🔲 Pending

**What I do:** Write persona cards — one per cluster. Each card: behavior pattern, entry context, platform, path depth/breadth, conversion likelihood, recommended product intervention.

**Naming happens here, after behavior is confirmed.**

---

## Custom Event Bundles (reference)

| Bundle | Events included | Approx. volume |
|---|---|---|
| `[Custom] Photo Browsing` | Photo Viewer events | ~520M |
| `[Custom] Browse Interaction` | Save, filter, sort events | ~83M |
| `[Custom] Detail Deep Read` | Scroll depth, expand section events | ~27M |
| `[Custom] Map Exploration` | Map interaction events | ~16M |
| `[Custom] High Intent Action` | Contact, tour, share, favorite events | ~7M |
| `[Custom] Serial Navigation` | Back-to-back listing navigation | ~11M |
| `[Custom] Cost Research` | Mortgage calc, affordability events | ~3M |

---

## Scripts

| Script | Purpose |
|---|---|
| `run.py` | Main runner — top events (appId=OneHome, last 7 days) |
| `explore_onehome_events.py` | Full event list, last 90 days, appId=OneHome |
| `inspect_event_properties.py` | Probe candidate user/agent properties on OneHome events |
| `search_onehome_repos.py` | GitHub code search for property names |
| `analysis_ideas.py` | Starter ideas template |

## Data Files

| File | Contents |
|---|---|
| `data/raw/top_events_7d.json` | Phase 1 raw pull — top 25 events, last 7 days, appId=OneHome |
| `data/processed/top_events_7d.csv` | Same, CSV format |
| `data/raw/onehome_events_raw.json` | Full 90-day event list (from explore script) |
| `data/processed/onehome_events.csv` | Same, CSV format |

---

## Key Findings So Far

- `appId` is a super property stamped on all events. Value `"OneHome"` has ~114M events/7 days.
- Other apps in same project: Matrix (228M), undefined (162M), APPLICATION_NAME_MLS_TOUCH (57M), Realist (15M), Agent Portal (5.5M), and more.
- `groupId` is the likely agent vs consumer differentiator (Phase 3 to confirm).
- `authenticated` is an event-level property (flips per session), not a user property.
- `registered` hypothesis: user/people property (static) — Phase 2 Q1 to confirm.
