"""
Phase 3 — Email domain analysis to find agent vs consumer signal.

Now confirmed: agentIDs = IDs of agents connected to this consumer.
  → Users WITH agentIDs = consumers (have an assigned agent)
  → Users WITHOUT agentIDs = potentially agents (or unmatched consumers)

Question: do email domains reveal which group is made up of agents?
Hypothesis: agents use brokerage/professional domains; consumers use Gmail/Yahoo/etc.
"""
import sys, ast, re
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

import pandas as pd

CSV = Path(__file__).parent / "data" / "raw" / "user-export-2175557-2026_05_04_04_25_20.csv"

# Known personal/free email providers — strong signal for CONSUMER
PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "me.com", "mac.com", "live.com", "msn.com",
    "ymail.com", "googlemail.com", "comcast.net", "att.net", "verizon.net",
    "sbcglobal.net", "cox.net", "charter.net", "protonmail.com", "proton.me",
}

print("Loading CSV...")
df = pd.read_csv(CSV, low_memory=False)
df = df.replace("undefined", pd.NA)
total = len(df)
print(f"  {total:,} users loaded.")


def parse_list(val):
    if pd.isna(val):
        return []
    try:
        r = ast.literal_eval(val)
        return r if isinstance(r, list) else [r]
    except Exception:
        return [str(val)]


df["agentIDs_count"] = df["agentIDs"].apply(lambda v: len(parse_list(v)))

# confirmed: has_agent_ids → consumer; no agent_ids → unknown (possibly agent)
consumers = df[df["agentIDs_count"] > 0]   # have assigned agents → consumer
unknown   = df[df["agentIDs_count"] == 0]   # no assigned agents → agent or unmatched consumer

print(f"\n  Consumers (agentIDs populated): {len(consumers):,} ({100*len(consumers)/total:.1f}%)")
print(f"  Unknown   (agentIDs empty):     {len(unknown):,} ({100*len(unknown)/total:.1f}%)")


def domain(email):
    try:
        return str(email).split("@")[1].strip().lower()
    except Exception:
        return None


consumers = consumers.copy()
unknown   = unknown.copy()

email_col = "email" if "email" in df.columns else "$email"

consumers["domain"] = consumers[email_col].apply(domain)
unknown["domain"]   = unknown[email_col].apply(domain)

# ── 1. Overall email coverage ─────────────────────────────────────────────────
print("\n=== 1. Email coverage ===")
print(f"  Consumers with email: {consumers[email_col].notna().sum():,} / {len(consumers):,} ({100*consumers[email_col].notna().mean():.1f}%)")
print(f"  Unknown   with email: {unknown[email_col].notna().sum():,} / {len(unknown):,} ({100*unknown[email_col].notna().mean():.1f}%)")

# ── 2. Top 30 domains in each group ──────────────────────────────────────────
print("\n=== 2. Top 30 email domains — Consumers (have agentIDs) ===")
c_domains = consumers["domain"].value_counts().head(30)
print(c_domains.to_string())

print("\n=== 2. Top 30 email domains — Unknown (no agentIDs) ===")
u_domains = unknown["domain"].value_counts().head(30)
print(u_domains.to_string())

# ── 3. Personal vs professional split ────────────────────────────────────────
print("\n=== 3. Personal vs professional email split ===")
for label, grp in [("Consumers", consumers), ("Unknown", unknown)]:
    with_email = grp["domain"].notna()
    personal = grp.loc[with_email, "domain"].isin(PERSONAL_DOMAINS).sum()
    professional = with_email.sum() - personal
    total_with = with_email.sum()
    print(f"  {label}:  personal={personal:,} ({100*personal/total_with:.1f}%)  professional={professional:,} ({100*professional/total_with:.1f}%)  [of {total_with:,} with email]")

# ── 4. Domains that appear heavily in Unknown but NOT in Consumers ─────────────
print("\n=== 4. Domains overrepresented in 'Unknown' group (potential agent domains) ===")
c_dom_pct = (consumers["domain"].value_counts(normalize=True) * 100).rename("consumer_pct")
u_dom_pct = (unknown["domain"].value_counts(normalize=True) * 100).rename("unknown_pct")
comparison = pd.concat([u_dom_pct, c_dom_pct], axis=1).fillna(0)
comparison["ratio"] = comparison["unknown_pct"] / (comparison["consumer_pct"] + 0.001)
# filter to domains with at least 50 users in unknown group
u_counts = unknown["domain"].value_counts()
comparison = comparison[u_counts.reindex(comparison.index, fill_value=0) >= 50]
comparison = comparison.sort_values("ratio", ascending=False).head(30)
print(comparison.to_string())

# ── 5. Domains overrepresented in Consumers ────────────────────────────────────
print("\n=== 5. Domains overrepresented in 'Consumer' group ===")
comparison2 = pd.concat([c_dom_pct, u_dom_pct], axis=1).fillna(0)
comparison2["ratio"] = comparison2["consumer_pct"] / (comparison2["unknown_pct"] + 0.001)
c_counts = consumers["domain"].value_counts()
comparison2 = comparison2[c_counts.reindex(comparison2.index, fill_value=0) >= 50]
comparison2 = comparison2.sort_values("ratio", ascending=False).head(30)
print(comparison2.to_string())

# ── 6. Domains with most users that look like real-estate brokerages ──────────
print("\n=== 6. Top 'professional' (non-personal) domains in Unknown group ===")
u_prof = unknown[~unknown["domain"].isin(PERSONAL_DOMAINS) & unknown["domain"].notna()]
print(u_prof["domain"].value_counts().head(50).to_string())

print("\n=== 7. Top 'professional' (non-personal) domains in Consumer group ===")
c_prof = consumers[~consumers["domain"].isin(PERSONAL_DOMAINS) & consumers["domain"].notna()]
print(c_prof["domain"].value_counts().head(50).to_string())

