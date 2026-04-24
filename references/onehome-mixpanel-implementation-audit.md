# OneHome Mixpanel Implementation Audit
**Date:** 2026-04-23  
**Scope:** `corelogic-private/real_estate_us-aotf-frontend_apps` (NX monorepo)  
**Source:** Code inspection via GitHub API + Mixpanel documentation review  
**Project ID:** 2175557

---

## 1. Architecture Overview

The Mixpanel implementation is **centralized** — not scattered. All event dispatch flows through a single Angular shared library:

```
real_estate_us-aotf-frontend_apps/
└── libs/shared-ui/src/lib/modules/analytics/
    ├── analytics.service.ts        ← orchestrator (single gateway to all trackers)
    ├── analytics.models.ts         ← types
    ├── analytics.config.ts         ← token injection + login status constants
    ├── analytics-message.service.ts ← message bus (components push events here)
    ├── analytics-timer.service.ts   ← session timer logic
    └── trackers/
        ├── mixpanel.ts             ← thin wrapper: init, identify, register, track, people.*
        └── index.ts                ← multi-tracker registry (supports future trackers)
```

**Two applications** consume this shared service:
- `projects/onehome/` — the consumer-facing OneHome app
- `projects/agent-portal/` — the agent-facing portal

Both call `analytics.init(user.id)` identically from their respective `app.container.ts`.

**One separate implementation** exists in `real_estate_us-aotf-onehome_marketing` — the marketing landing site — with its own analytics service, its own Mixpanel init, and no shared identity state with the main app. It also runs GTM alongside Mixpanel.

**Backend repos:** No Mixpanel usage was found in any backend or mobile service repos (`analytics_service`, `onehome_mobile`, all other aotf services).

---

## 2. Identity Management — Against Mixpanel Best Practices

> **Reference:** https://docs.mixpanel.com/docs/tracking-methods/id-management/identifying-users-simplified

### 2.1 What the code does

```
Step 1 — init(user.id)
   └─ identify(user.id)
         └─ mixpanel.identify(userID)   ← sets $user_id = internal DB UUID

Step 2 — setupAgentListener()
   └─ doForAllTrackers('register', { AgentID, MLSID, ... })
         └─ mixpanel.register(superProperties)  ← stamped on all events

Step 3 — updateUserProfile()
   └─ people.set({ UUID, email, agentIDs, mlsIds, totalGroups, ... })
         └─ mixpanel.people.set(properties)
```

The `user.id` used for `identify()` is the internal consumer UUID from the user database. This is **the correct field to use** per Mixpanel docs, which recommend "a database ID that is unique to each user and does not change."

### 2.2 What is done right (conforming to best practices)

| Practice | Docs recommendation | Implementation |
|---|---|---|
| Use a stable, opaque DB ID as `$user_id` | ✅ Recommended | ✅ `user.id` (UUID from user DB) |
| Call `identify()` on login / app re-open in authenticated state | ✅ Required | ✅ Called in `ngAfterViewInit` after user resolves |
| Register super properties for context on all events | ✅ Recommended | ✅ `register()` used for agent/mls context, device info, feature flags |
| Set user profile with `people.set()` | ✅ Recommended after identify | ✅ Called with email, groups, counts |
| Use `set_once` for properties that shouldn't be overwritten | ✅ Recommended | ✅ `setUserPropertyOnce('email', ...)` for unauthenticated users |
| Increment counters with `people.increment` | ✅ Recommended | ✅ Used for `numPlannerUpdates`, `numOnboardingUpdates` |
| Cache events before SDK is ready | ✅ Docs pattern | ✅ `this.cache[]` holds events until `ready = true` |
| Use group analytics for multi-entity tracking | ✅ Available | ✅ `set_group('groupId', groupIds)` used |
| Fetch SDK key at runtime (not hardcoded) | ✅ Security best practice | ✅ Key retrieved via GraphQL `GetAuthToken` |

### 2.3 What is missing or deviates from best practices

#### ❌ `reset()` is not called on logout

Mixpanel docs:
> "Call `.reset()` upon logout or when an app leaves an authenticated state. By calling `.reset()` at logout, you generate a new `$device_id` for your user, ensuring that multiple users that are sharing a single device would not be incorrectly considered as a single user."

The `analytics.service.ts` subscribes to `signIn$` but there is no corresponding `signOut$` / logout handler calling `reset()`. The `$device_id` persists across sessions. On shared devices or after session expiry and re-login as a different account, pre-reset events will be attributed to the wrong user's ID cluster.

#### ❌ `identify()` is skipped in ShareView mode — with no fallback

The code explicitly skips `identify()` when `viewMode === AgentShare`:
```typescript
// We shouldn't identify the user when in ShareView mode 
// because we don't know the email.
if (viewMode !== ViewMode.AgentShare) {
  TRACKERS[tracker].identify(userIdOverride ? userIdOverride : userID);
}
```

ShareView represents real product interactions (a consumer browsing agent-shared listings). These sessions get Mixpanel's auto-generated anonymous `$device_id` as Distinct ID and are **permanently unlinked** from the consumer's profile. There is no `alias` call or deferred `identify` to merge them later.

Per Mixpanel docs: "as long as you always call `.identify` when the user logs in, all of that activity will be stitched together." — ShareView sessions break this contract deliberately, and the stitching is lost.

The **intent** of the ShareView skip may be valid (you don't want to misidentify someone accessing a share link from an email), but the result in Mixpanel is a permanent anonymous session — worth being explicit about in reporting.

#### ⚠️ Super properties are set asynchronously after `identify()`

`identify()` is called immediately when the user resolves. `setupAgentListener()` — which registers `AgentID`, `MLSID`, `AssociationID`, etc. — is triggered only after the agent data observable emits, which happens slightly later. Events fired in the brief window between `identify()` resolving and the agent observable emitting will lack these super properties.

This is a timing issue, not an architectural one. Mixpanel docs note: "Track the unique identifier as a super property and user property to assist in troubleshooting." The data for early-session events (like `App Load`) may therefore be incomplete.

#### ⚠️ Marketing site is a separate identity island

`real_estate_us-aotf-onehome_marketing` initializes Mixpanel with its own config and performs no `identify()` call tied to the main app's `user.id`. A user who visits the marketing site before signing up gets an anonymous `$device_id`. After signing up and using the main app, `identify()` in the app will stitch that UUID to their pre-login device ID — **but only for the main app's events**. The marketing site's events are tracked under a different anonymous `$device_id` with no cross-site stitching. The two journeys are not connected.

Mixpanel's ID Merge can handle cross-platform stitching if both surfaces call `identify(same_user_id)` after the user logs in. Currently the marketing site has no `identify()` call at all.

#### ⚠️ Two property names refer to two different identifier systems

In the event payload, two distinct properties appear:
- **`AgentID`** (PascalCase) — super property, value = `agent.memberMlsId` (the MLS member ID from the MLS system)
- **`agentId`** (camelCase) — manually set on specific events, value = `agent.id` (internal graph DB ID)

These are different values from different systems. Neither is documented in a tracking plan. Any analysis that conflates them will produce incorrect cohorts.

---

## 3. What to Check in Project Settings First

Before doing any analysis, verify these in the Mixpanel UI under **Project Settings**:

### 3.1 Identity Merge API version
Navigate to: `Settings → Project → Identity Management`

- **Simplified ID Merge** (post-2023): `identify()` sets `$user_id`, the SDK handles `$device_id` → `$user_id` cluster automatically. Canonical Distinct ID = `$user_id`.
- **Original ID Merge** (pre-2023): Required explicit `alias()` calls. The code does not use `alias()` at all, which is correct for Simplified but would be broken for Original.

**Action:** Confirm which version the OneHome project uses. The behavior of ID Merge, retroactive event attribution, and the Distinct ID displayed in the UI all depend on this.

### 3.2 Developer environments mixed with production data
Check if `USER_ID_OVERRIDE` is set in any active environments. The code has:
```typescript
// Override user ID to prevent dev/UAT users from counting towards total users
const userIdOverride = this.CONFIG.TRACKER_CONFIG[tracker].USER_ID_OVERRIDE || null;
```

This is the right intent, but verify it is correctly configured in all non-production environments. If UAT or staging is pointing to the same Mixpanel project without an override, test traffic inflates user counts and pollutes funnels.

**Mixpanel recommendation:** Use separate projects per environment, or use `opt_out_tracking()` for internal users/QA. Mixpanel also supports a "service account" filter to exclude known internal IPs.

### 3.3 Data Volume and Lexicon hygiene
With 592 distinct event names and 1.25B events over 90 days, review Lexicon (Data Governance → Lexicon) for:
- Duplicate or redundant events (case variants, legacy names)
- Events with no description or owner
- Properties with no consistent type (e.g., `AgentID` sometimes a string, sometimes null)

Mixpanel docs: "Be intentional with your data. Tracking everything and anything can lead to unnecessary development effort and unused data."

---

## 4. Gaps and Suggested Improvements

### Priority 1 — Add `reset()` on logout
**What:** Call `mixpanel.reset()` when a user logs out or a session times out.  
**Where:** `analytics.service.ts` — add a `signOut$` subscription alongside the existing `signIn$`.  
**Why:** Without this, a new user logging in on the same device inherits the `$device_id` of the previous session, causing event streams to merge incorrectly. Mixpanel docs call this out explicitly as a required step.  
**Impact:** Low code change, high data quality impact.

### Priority 2 — Add a stable `userType` or `portalType` user profile property
**What:** Call `people.set({ portal: this.userService.currentPortal })` at login time.  
**Where:** `analytics.service.ts` → `updateUserProfile()`.  
**Why:** `currentPortal` is already registered as a super property (`appId`). Promoting it to a user profile property enables cohort filtering in the Users tab and retroactive segmentation on all historical events via the query-time join. Mixpanel docs note that user profile properties are joined retroactively with all past events.  
**Impact:** Zero SDK changes, one-line addition.

### Priority 3 — Standardize `AgentID` vs `agentId` naming
**What:** Audit all `analyticsMessage.track()` calls in the codebase for manual `agentId` vs `AgentID` usage and converge on one.  
**Where:** Spread across `projects/onehome/` and `projects/agent-portal/` component files.  
**Why:** Two property names, two different ID systems, no documentation. Any funnel or cohort filtering on "agent identifier" is currently unreliable.  
**Impact:** Requires a tracking plan decision: which ID is canonical? MLS member ID (`AgentID` / `memberMlsId`) is more portable; internal graph ID (`agentId`) is more database-coupled.

### Priority 4 — Handle marketing site identity
**What:** Call `identify(user.id)` in `onehome_marketing` when a user creates an account or signs in.  
**Where:** `real_estate_us-aotf-onehome_marketing/src/app/_@core/analytics/analytics.service.ts`.  
**Why:** Mixpanel's ID Merge only links cross-surface sessions if `identify()` is called with the same `$user_id` on both surfaces. Without this, marketing-to-app conversion attribution is permanently lost.  
**Impact:** Requires coordination with the marketing site team. The user registration/login flow in the marketing site would need to surface the user's DB UUID.

### Priority 5 — Create a Tracking Plan document
**What:** A shared spreadsheet (or equivalent) listing every event name, its trigger, its required properties, and the owning team.  
**Why:** With 592 events and no schema enforcement, the implementation has drifted. Mixpanel explicitly recommends this as a prerequisite for accurate analysis: "a centralized document that should serve as the source of truth on your Mixpanel implementation."  
**Reference:** https://docs.mixpanel.com/docs/tracking-best-practices/tracking-plan

### Lower priority — Evaluate Group Analytics for the agent-consumer relationship
**What:** The existing `setGroup('groupId', groupIds)` usage is a start, but the agent-consumer group relationship could be modeled more explicitly using Mixpanel's Group Analytics add-on.  
**Why:** One consumer can be associated with multiple agents (via `groups`). Group Analytics allows you to run reports "for each agent-consumer relationship" rather than "for each consumer" — which maps directly to OneHome's data model.  
**Reference:** https://docs.mixpanel.com/docs/data-structure/group-analytics

---

## 5. What Is Not a Problem (Removed Bias)

The previous assessment framed the absence of a `userType` differentiator as an identity management problem. Strictly speaking:

- The identity implementation is **not broken** from Mixpanel's perspective. `identify(user.id)` is called correctly with a stable DB UUID. The ID cluster is formed correctly. The profile receives correct attributes.
- The **`AgentID` super property** is a valid way to add contextual segmentation — it is not required for identity management.
- The **lack of a `userType` property** is a **data quality / tracking plan gap**, not an identity management failure. Mixpanel does not require user type labeling; it is an analytics convenience that the implementation doesn't provide yet.
- The **ShareView anonymous session** is a deliberate product decision and is functionally correct — the implementation follows what the comment says. The gap is that these anonymous sessions are unquantified and uncounted in any reporting, which is worth noting but is not a Mixpanel mis-implementation.

---

## 6. Summary Table

| Dimension | Assessment | Severity |
|---|---|---|
| `identify()` called with stable DB UUID | ✅ Correct per docs | — |
| `identify()` called at login / app open | ✅ Correct per docs | — |
| `reset()` called at logout | ❌ Missing | High |
| Super properties registered | ✅ Comprehensive | — |
| `people.set()` called post-identify | ✅ Correct per docs | — |
| `set_once` used where appropriate | ✅ Used | — |
| ShareView sessions anonymous permanently | ⚠️ Deliberate but untracked | Medium |
| Marketing site cross-stitching | ❌ Not implemented | Medium |
| `AgentID` vs `agentId` naming collision | ⚠️ Two different values | Medium |
| Super properties timing (early events) | ⚠️ Possible missing context | Low |
| Dev/UAT environment separation | ⚠️ Needs verification | Medium |
| Tracking plan / Lexicon documentation | ❌ Not exists | High |
| ID Merge API version confirmed | ❓ Check project settings | Prerequisite |

---

*Sources: GitHub code inspection of `real_estate_us-aotf-frontend_apps` (develop branch, 2026-04-23); Mixpanel documentation at docs.mixpanel.com (accessed 2026-04-23).*
