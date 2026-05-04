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
Phase 3 ✅ CLOSED — no differentiator found, proceeding without agent/consumer split
    ↓
Phase 4 — [Segmentation strategy agreed — proceed to Flows]
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

## Phase 3 — Agent vs Consumer Differentiator Investigation ✅ COMPLETED (no differentiator found)

**Inputs:** Two user exports — `user-export-2175557-2026_05_04_04_01_24.csv` (441K rows) and `user-export-2175557-2026_05_04_04_25_20.csv` (406K rows, with email).

**What we investigated:**

| Signal | Finding | Verdict |
|---|---|---|
| `agentIDs` | JSON list of **MLS IDs of agents connected to this consumer** — confirmed via business logic | ❌ Identifies consumers-with-an-agent, NOT whether the visitor IS an agent |
| `groupId` | UUID(s), populated for 100% of ALL users | ❌ Not a differentiator |
| `AgentID` (singular) | Empty for every profile row | ❌ Lives only as an event super property, not in profiles |
| `agentIDs` × `distinct_id` cross-ref | `agentIDs` values are external MLS member IDs — zero overlap with Mixpanel UUIDs | ❌ Different ID systems entirely |
| Email domains | Both groups ~90%+ personal emails (Gmail/Yahoo/Hotmail) | ❌ No signal |
| `ViewMode` | 1 = Matrix Email entry, 3 = Agent-Shared Link, 4 = Consumer-Shared Link — **all can be consumers** | ❌ Describes entry context, not user type |

**Correct interpretation of `agentIDs`:**
- Users **with** `agentIDs` populated = consumers who have ≥1 assigned agent (51.5% of users)
- Users **without** `agentIDs` = unknown — could be agents using OneHome, unmatched consumers, or anonymous
- `agentIDs` values are external MLS member IDs (e.g. `"65919"`, `"C2013002397"`) — not Mixpanel user IDs

**Root cause:** The implementation audit explicitly flagged this as Priority 2 — `userType` / `portalType` was never added to the tracking plan. There is no user-level property that identifies whether a OneHome visitor is an agent or consumer. This is a known instrumentation gap.

**Decision:** No reliable agent vs consumer split exists in Mixpanel. Proceed to Phase 4 without it. Segment by behavior (the actual goal). Note `agentIDs` populated = confirmed consumer-with-agent as a partial signal where useful.

**Phase 3 gate: CLOSED — no differentiator found, proceeding anyway.**

---

## Phase 4 — Segmentation Strategy Decision 🔲 Next

**Input:** Answers from Phases 2 and 3.

**Context from Phase 3:** No user-level agent vs consumer split is available in Mixpanel. The implementation never added a `userType` property.

**Agreed segmentation approach:**
- **Primary behavioral split:** Segment by `agentIDs` populated (confirmed consumer-with-agent, 51.5%) vs not populated (unknown, 48.5%). Use as a partial lens, not a definitive agent flag.
- **Entry context:** `ViewMode` — 1 (Matrix Email), 3 (Agent-Shared Link), 4 (Consumer-Shared Link). Describes how a session started, not who the user is.
- **Session state:** `authenticated` (event-level property — was user logged in for that event?)
- **Platform:** `deviceType` (mobile / desktop / tablet) and `isMobileApp` (true/false)
- **Accept the gap:** We cannot cleanly separate agents from consumers. Persona clusters will be behavioral, not role-based. Role inference can be a post-hoc interpretation if clusters naturally split.

**Gate:** Approved implicitly — proceed to Phase 5 Flows.

---

## Phase 5 — Build Flows 🔲 Pending

**Segmentation dimensions available (confirmed in Phase 2):**

| Property | Type | Values | Use in flows |
|---|---|---|---|
| `authenticated` | Event-level | true / false | Filter or breakdown on flows where login state matters |
| `registered` | User-level (stable) | true / false | Filter on user property to split sign-ups vs guests |
| `ViewMode` | Event-level | 1 (Matrix Email entry) · 3 (Agent-Shared link) · 4 (Consumer-Shared link) | OH-02 filter per variant |
| `deviceType` | Event-level | mobile · desktop · tablet | Breakdown or separate runs on OH-03 and others |
| `isMobileApp` | Event-level | true · false (very skewed — 99.9% false) | Use `deviceType` instead as primary |
| `agentIDs` populated | User-level | true / false | Partial lens: confirmed consumer-with-agent vs unknown |

**Global filter on ALL flows:** `appId = OneHome` AND `Basic Event Cleaner = True`

**Export format for each flow:** Top Paths view, expand to top 10 rows, export as CSV. Name each file to match the flow ID (e.g. `OH-01_all.csv`, `OH-01_mobile.csv`).

**Note on `authenticated`:** It is an event-level property — within a single session a user can flip between authenticated and unauthenticated. Apply it as a filter at flow-build time to select sessions where the first event is authenticated=true (or false), not as a user cohort.

### OH-01 — Post App Load (All Sessions)
**Anchor A:** `Initial App Load` | **Steps after A:** 5 | **Counting:** Sessions
**Hide:** `What's New - Flow - "Next" Click`, `What's New - Welcome Screen Pop Up`, `What's New - Flow - Cancel Click`
**View:** Top Paths — expand to top 10 rows
**Segmentation:**
- Run 1: No extra filter → `OH-01_all.csv`
- Run 2: Filter `authenticated = true` → `OH-01_auth.csv`
- Run 3: Filter `authenticated = false` → `OH-01_anon.csv`

**Save report as:** `OH-01 - Post App Load (All Sessions)`

### OH-02 — Entry Context by Referral Type (ViewMode splits)
Build 4 parallel flows, same config, different filters:
- **OH-02a:** Filter `ViewMode = 1` → Entry via Matrix Email → `OH-02a.csv`
- **OH-02b:** Filter `ViewMode = 3` → Entry via Agent-Shared Link → `OH-02b.csv`
- **OH-02c:** Filter `ViewMode = 4` → Entry via Consumer-Shared Link → `OH-02c.csv`
- **OH-02d:** No ViewMode filter → Entry Direct/Organic → `OH-02d.csv`

**Anchor A:** First `Property Details - Landed` after entry | **Steps after A:** 5 | **Counting:** Sessions
**No additional segmentation needed** — ViewMode IS the segmentation here.

**Save report as:** `OH-02 - Entry Context by ViewMode`

### OH-03 — Post App Load: Mobile vs Web
Duplicate OH-01 config (same anchor, same hidden events).
**Segmentation:** Breakdown by `deviceType` (mobile / desktop / tablet) OR run 3 separate filters:
- Run 1: Filter `deviceType = mobile` → `OH-03_mobile.csv`
- Run 2: Filter `deviceType = desktop` → `OH-03_desktop.csv`
- Run 3: Filter `deviceType = tablet` → `OH-03_tablet.csv`

**Save report as:** `OH-03 - Post App Load: Mobile vs Web`

### OH-04 — Browse to Property Details Journey
**Anchor A:** `Browse Properties - Landed` | **Anchor B:** `Property Details - Landed`
**Steps between A and B:** show all | **Steps after B:** 5 | **Counting:** Sessions
**Hide between steps:** `[Custom] Photo Browsing`
**Segmentation:**
- Run 1: No extra filter → `OH-04_all.csv`
- Run 2: Breakdown by `deviceType` → `OH-04_by_device.csv`

**Save report as:** `OH-04 - Browse to Property Details`

### OH-05a — Property Details Full Behavior (Unfiltered)
**Anchor A:** `Property Details - Landed` | **Steps after A:** 7 | **Counting:** Sessions
**Do NOT hide anything** — let `[Custom] Photo Browsing` dominate.
**Segmentation:** No additional filter — this is the baseline.
→ Export: `OH-05a_all.csv`

**Save report as:** `OH-05a - Property Details (All)`

### OH-05b — Property Details Excluding Photo Scrollers ← KEY PERSONA SEPARATOR
Duplicate OH-05a, add **Exclusion step:** users who did `[Custom] Photo Browsing` at any step after A.
**Segmentation:**
- Run 1: No extra filter → `OH-05b_all.csv`
- Run 2: Filter `authenticated = true` → `OH-05b_auth.csv`
- Run 3: Filter `authenticated = false` → `OH-05b_anon.csv`

**Save report as:** `OH-05b - Property Details (Excluding Photo Scrollers)`

### OH-06 — Paths to High-Intent Actions (3 end-anchored flows)
- **OH-06a:** End anchor = `[Custom] High Intent Action`, steps before: 5, Counting: Uniques → `OH-06a.csv`
- **OH-06b:** End anchor = `Property Details - "Favorite" Click`, steps before: 5, Counting: Uniques → `OH-06b.csv`
- **OH-06c:** End anchor = `Property Details - Schedule a Tour Click`, steps before: 5, Counting: Uniques → `OH-06c.csv`

**Segmentation on all three:** Also run with filter `registered = true` to see signed-up users only → `OH-06a_registered.csv`, etc.

**Save report as:** `OH-06 - Paths to High Intent`

### OH-07 — Authentication Friction After Anonymous Entry
**Anchor A:** `Entry Link - Session Not Logged In` | **Steps after A:** 5 | **Counting:** Sessions
**Segmentation:**
- Run 1: No extra filter → `OH-07_all.csv`
- Run 2: Breakdown by `deviceType` (mobile vs desktop) → `OH-07_by_device.csv`

**Save report as:** `OH-07 - Auth Friction After Anonymous Entry`

### OH-08 — Compare Feature Adoption
**Anchor A:** `Compare Page - Landed` | **Steps before A:** 4 | **Steps after A:** 4 | **Counting:** Sessions
**Segmentation:** No additional filter — this is a niche feature, keep unfiltered to maximize volume.
→ Export: `OH-08_all.csv`

**Save report as:** `OH-08 - Compare Feature Adoption`

### OH-09 — PropertyFit Onboarding Drop-off
**Anchor A:** `PropertyFit Onboarding - Flow - What describes you best? - Choice Selection`
**Anchor B:** `PropertyFit Onboarding - Flow - Skip Click` OR `PropertyFit Onboarding - Rank Features - Rank Features Click`
**View:** Sankey (NOT Top Paths) | **Counting:** Uniques
**Segmentation:** No additional filter — keep unfiltered (this event is already narrow).
→ Export: `OH-09_all.csv`

**Save report as:** `OH-09 - PropertyFit Onboarding Drop-off`

### OH-10 — Browsing Landed to Property Details Landed
**Anchor A:** `Browsing - Landed` | **Anchor B:** `Property Details - Landed`
**Steps between A and B:** show all | **Steps after B:** 3 | **Counting:** Sessions
**Segmentation:**
- Run 1: No extra filter → `OH-10_all.csv`
- Run 2: Filter `deviceType = mobile` → `OH-10_mobile.csv`

**Save report as:** `OH-10 - Browsing Landed to Property Details Landed`

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
- **No agent vs consumer differentiator exists** in Mixpanel. `userType` was never instrumented (known gap, audit Priority 2). `agentIDs` = list of agents connected to a consumer — NOT an agent-identity flag.
- `groupId` is 100% populated for all users — not a differentiator (hypothesis disproved in Phase 3).
- `agentIDs` populated (51.5% of users) = confirmed consumer-with-an-agent. Best partial signal available.
- `authenticated` is an event-level property (flips per session), not a user property.
- `registered` is a stable user-level property (sign-up status: true/false).
