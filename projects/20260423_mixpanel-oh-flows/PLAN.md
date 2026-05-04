# OneHome Persona Discovery — Master Plan
Last updated: 2026-05-03

---

## Phase 0 — Manual Simulation (You as the Customer) ✅ COMPLETED

**Goal:** Discover events and properties from the ground up before touching any API.

**Findings:**
- `groupId` — likely the key property to distinguish agents from consumers. Update Phase 3 accordingly.
- `deviceType` — potentially interesting for platform split (may complement or replace `isMobileApp`).
- Anchor events confirmed: the ones in our custom bundles appear to be the right signal events.
- `authenticated` observed to flip from `false` → `true` after login — confirms it is an **event-level property** (session state), not a user property.
- Hypothesis: `registered` may be a **user/people property** (static, set once after signup) while `authenticated` is dynamic per session. This matters: `registered` could be used as a stable user-level segmenter in cohort analysis, while `authenticated` is better for session-level Flows.

**Open question carried to Phase 2:** Confirm `registered` is a People property and what values it takes.

---

## Phase 1 — Validate API Access (Debug Checkpoint)

**Goal:** Confirm my API data matches what you see in Mixpanel UI before trusting any number I produce.

**What I do:** Pull top 10 events by count, last 30 days via API → print ranked table.

**What you do [UI]:** Mixpanel → Events report → last 30 days → rank by total.

**Pass criteria:** Top 3 events match in order, within ~5% volume.
**Gate:** Nothing proceeds until this passes. If off, we debug first.

---

## Phase 2 — Open Property Questions (Mixed: You UI + Me API)

| # | Question | Who | Method |
|---|---|---|---|
| Q1 | Does `registered` exist as a People property? What values? | **[You → UI]** | Mixpanel → Users report → add `registered` column, note distinct values |
| Q2 | Does `ViewMode` exist as an event property? Values 1/3/4? | **[You → UI]** | Events breakdown table, property = `ViewMode`, any large event |
| Q3 | Does `isMobileApp` exist? True/false? Or use `deviceType` instead? | **[You → UI]** | Breakdown table, property = `isMobileApp` then `deviceType` |
| Q4 | Any other properties surfaced in Phase 0 simulation | **[You → UI]** | Breakdown on the most interesting new events found |
| Q5 | Is `authenticated` stable per user across sessions, or does it flip within a session? | **[Me → API]** | 1 JQL query — sample `distinct_id`s with >1 session, check value distribution |

You paste Q1–Q4 results back in a sentence each. I run Q5 and report.

---

## Phase 3 — Agent vs Consumer Differentiator Investigation

**Updated hypothesis from Phase 0:** `groupId` may be the key differentiator.

**What you do [UI]:** Run a **Users/People report** in Mixpanel:
- Columns: `distinct_id`, `AgentID`, `groupId`, any email/name/username field visible
- No filter
- Export top 200 rows as CSV → send me

**What I look for:**
- Is `groupId` populated only for agents? Does it correlate with `AgentID`?
- Does `distinct_id == AgentID` for any rows? (agents logged in as themselves)
- Is `distinct_id` an email for some and a numeric ID for others?
- Do `AgentID` values follow a recognizable pattern (e.g., all 6-digit MLS member IDs)?
- Is there a `$email` or `$name` super property that distinguishes types?

**Output:** Either we find a differentiator (likely `groupId`) and add it to segmentation strategy, or we conclude `authenticated` is the best proxy and note the limitation explicitly.

---

## Phase 4 — Segmentation Strategy Decision

**Input:** Answers from Phases 2 and 3.

**What I do:** Write a single paragraph — the agreed segmentation strategy. Primary split, secondary splits, what we're treating as proxies and why.

**Gate:** You approve this before any Flow is configured.

---

## Phase 5 — Build Flows

**Segmentation strategy:** TBD after Phase 4.
- Likely primary split: `authenticated` (session-level) or `groupId`/`registered` (user-level)
- Likely secondary splits: `ViewMode` (entry context), `deviceType` or `isMobileApp` (platform)

### The Flows

---

#### OH-01 — Post App Load (All Sessions)
**Anchor A:** Initial App Load
**Steps after A:** 5
**Counting:** Sessions
**Hide:** `What's New - Flow - "Next" Click`, `What's New - Welcome Screen Pop Up`, `What's New - Flow - Cancel Click`
*(returning-user onboarding noise that drowns behavioral signal)*
**View:** Top Paths — expand to top 10 rows
**Save as:** `OH-01 - Post App Load (All Sessions)`

---

#### OH-02 — Entry Context by Referral Type (ViewMode splits)
*Conditional: only if Q2 in Phase 2 confirms ViewMode exists with values 1/3/4*

Build 4 parallel flows — same config, different filters:
- **OH-02a:** Filter `ViewMode = 1` → Entry via Matrix Email
- **OH-02b:** Filter `ViewMode = 3` → Entry via Agent-Shared Link
- **OH-02c:** Filter `ViewMode = 4` → Entry via Consumer-Shared Link
- **OH-02d:** No ViewMode filter → Entry Direct/Organic

For each:
**Anchor A:** First `Property Details - Landed` after entry
**Steps after A:** 5
**Counting:** Sessions

**Key questions:** Do Matrix-email sessions go straight to photo scroll and exit? Do agent-link sessions have higher research depth? Do consumer-link sessions have more comparison behavior?

---

#### OH-03 — Post App Load: Mobile vs Web
*Conditional: only if `isMobileApp` or `deviceType` confirmed in Phase 2*

Duplicate OH-01, add breakdown by `isMobileApp` (true/false) or `deviceType`.
**Save as:** `OH-03 - Post App Load: Mobile vs Web`

---

#### OH-04 — Browse to Property Details Journey
**Anchor A:** `Browse Properties - Landed`
**Anchor B:** `Property Details - Landed`
**Steps between A and B:** show all
**Steps after B:** 5
**Counting:** Sessions
**Hide between steps:** `[Custom] Photo Browsing` *(reduces noise to expose navigation intent)*
**Tip:** Expand "Other events" between A and B — intermediate steps reveal search refinement behaviors.
**Save as:** `OH-04 - Browse to Property Details`

---

#### OH-05a — Property Details Full Behavior (Unfiltered)
**Anchor A:** `Property Details - Landed`
**Steps after A:** 7
**Counting:** Sessions
**Do NOT hide anything** — let `[Custom] Photo Browsing` dominate; you need to see its raw weight vs. other behaviors.
**Save as:** `OH-05a - Property Details (All)`

---

#### OH-05b — Property Details Excluding Photo Scrollers ← KEY PERSONA SEPARATOR
Duplicate OH-05a, add:
**Exclusion step:** users who did `[Custom] Photo Browsing` at any step after A

Now Top Paths shows only the non-photo-scroll population → this is your Researcher and Shortlister population. This flow is where persona clusters will be most visible.
**Save as:** `OH-05b - Property Details (Excluding Photo Scrollers)`

---

#### OH-06 — Paths to High-Intent Actions (3 end-anchored flows)
- **OH-06a:** End anchor = `[Custom] High Intent Action`, steps before: 5, Counting: Uniques
- **OH-06b:** End anchor = `Property Details - "Favorite" Click`, steps before: 5, Counting: Uniques
- **OH-06c:** End anchor = `Property Details - Schedule a Tour Click`, steps before: 5, Counting: Uniques *(small volume, very high signal)*

---

#### OH-07 — Authentication Friction After Anonymous Entry
*Conditional: only if `authenticated` confirmed as stable enough in Phase 2 Q5*

**Anchor A:** `Entry Link - Session Not Logged In`
**Steps after A:** 5
**Counting:** Sessions
**Add breakdown by:** `isMobileApp` if available — auth UX often differs on mobile
**Key events to watch for:** `Authentication Required - Create Account Dialog Shown`, `Authentication Required - Sign in Dialog Shown`, `Sign In - Sign In Click`, `Authentication - Authentication Successful`, `Authentication Unsuccessful`
**Save as:** `OH-07 - Auth Friction After Anonymous Entry`

---

#### OH-08 — Compare Feature Adoption
**Anchor A:** `Compare Page - Landed` (~1.76M events — substantial)
**Steps before A:** 4
**Steps after A:** 4
**Counting:** Sessions
**Key question:** Does compare behavior follow `[Custom] Detail Deep Read` or `[Custom] Cost Research`? This signals whether Compare users are financial researchers vs. feature comparers.
**Save as:** `OH-08 - Compare Feature Adoption`

---

#### OH-09 — PropertyFit Onboarding Drop-off
*Conditional: only if recent PropertyFit activity confirmed via API*

**Anchor A:** `PropertyFit Onboarding - Flow - What describes you best? - Choice Selection`
**Anchor B:** `PropertyFit Onboarding - Flow - Skip Click` OR `PropertyFit Onboarding - Rank Features - Rank Features Click`
**Steps between:** show all
**View:** Sankey (NOT Top Paths) to see where drop-off happens
**Counting:** Uniques
**Save as:** `OH-09 - PropertyFit Onboarding Drop-off`

---

#### OH-10 — Browsing Landed to Property Details Landed ← restored from previous plan
**Anchor A:** `Browsing - Landed`
**Anchor B:** `Property Details - Landed`
**Steps between A and B:** show all
**Steps after B:** 3
**Counting:** Sessions
**Key question:** What happens between generic browsing arrival and a specific listing being opened? This exposes search refinement and filter behavior.
**Save as:** `OH-10 - Browsing Landed to Property Details Landed`

---

**For each flow (where applicable):** Run once for `authenticated=false` and once for `authenticated=true`. Export Top Paths CSV per run.

**What I do:** Provide exact configuration for each flow above for you to enter in the UI.
**What you do [UI]:** Run and export Top Paths CSVs.

---

## Phase 6 — Cluster Analysis

**Input:** Top Paths CSVs from Phase 5.

**What I do:** Parse all path sequences, compute edit-distance similarity, identify 3–7 natural clusters. For each cluster, describe:
- Typical entry event
- Which custom bundles appear in the path
- Path depth (shallow = 1–3 steps, deep = 6+)
- Whether a High Intent event appears

**Rule:** No persona names yet. Behavior descriptions only. You review and confirm before we name anything.

---

## Phase 7 — Validation (Simulation Revisited)

**Goal:** Test that clusters actually predict behavior on fresh data.

**What I do:** For each cluster, write a classification rule. Run it against a fresh 7-day API sample. Report:
- How many users fit each cluster
- What % of each cluster hits a High Intent event

**Pass criteria:** Each cluster covers >2% of users AND has a meaningfully different conversion rate from the others. Clusters that don't pass get merged before naming.

**Optional:** You repeat the Phase 0 manual simulation as a logged-in user → we check which cluster your session would fall into.

---

## Phase 8 — Persona Synthesis

**Input:** Validated clusters from Phase 7.

**What I do:** Write persona cards — one per cluster. Each card includes:
- Behavior pattern description
- Entry context (ViewMode, referral type)
- Platform (mobile/web if available)
- Path depth and breadth
- Conversion likelihood
- Recommended product intervention

**Naming happens here, after behavior is confirmed.**

---

## Execution Order & Gates

```
Phase 0 ✅ DONE — simulation completed
    ↓
Phase 1 — [Me API] + [You UI check]
    GATE: top events match within 5%?
    ↓
Phase 2 — [You UI × 4] + [Me API × 1]
    GATE: property list agreed (registered, ViewMode, isMobileApp/deviceType confirmed)
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

## Open Decisions Log

| Decision | Status | Notes |
|---|---|---|
| Primary user segmenter | OPEN | `groupId` (agent flag?) vs `authenticated` vs `registered` |
| `ViewMode` confirmed real? | OPEN | Phase 2 Q2 |
| `registered` is user property? | OPEN | Phase 2 Q1 |
| `isMobileApp` vs `deviceType` | OPEN | Phase 2 Q3 |
| `authenticated` stable per user? | OPEN | Phase 2 Q5 (me via API) |
| Agent vs consumer differentiator | OPEN | Phase 3 — groupId investigation |
| PropertyFit recency | OPEN | Need API check before running OH-09 |
