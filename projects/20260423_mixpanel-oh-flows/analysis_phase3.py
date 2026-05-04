"""
Phase 3 — Agent vs Consumer Differentiator Analysis
Input: data/raw/user-export-2175557-2026_05_04_04_01_24.csv
"""
import sys, ast
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

import pandas as pd

CSV = Path(__file__).parent / "data" / "raw" / "user-export-2175557-2026_05_04_04_01_24.csv"

df = pd.read_csv(CSV, low_memory=False)
df = df.replace("undefined", pd.NA)

total = len(df)
distinct_id_col = "$distinct_id"
email_col = "$email"


def list_len(val):
    if pd.isna(val):
        return 0
    try:
        return len(ast.literal_eval(val))
    except Exception:
        return 0


df["agentIDs_count"] = df["agentIDs"].apply(list_len)
df["mlsIds_count"] = df["mlsIds"].apply(list_len)
df["groupId_count"] = df["groupId"].apply(list_len)

agents = df[df["agentIDs_count"] > 0]
consumers = df[df["agentIDs_count"] == 0]

print("=== POPULATION RATES ===")
for col in ["AgentID", "agentIDs", "groupId", "board_group_id", "mlsIds"]:
    n = df[col].notna().sum()
    print(f"  {col:<20} {n:>8,}  ({100*n/total:.1f}%)")

print(f"\n=== AGENT vs CONSUMER split via agentIDs ===")
print(f"  Agents   (agentIDs populated): {len(agents):>8,}  ({100*len(agents)/total:.1f}%)")
print(f"  Consumers (agentIDs empty):    {len(consumers):>8,}  ({100*len(consumers)/total:.1f}%)")

print(f"\n=== agentIDs count distribution (agents only) ===")
print(agents["agentIDs_count"].describe())

gid_col = "groupId"
print(f"\n=== Among agents: groupId populated? ===")
agent_gid = agents[gid_col].notna().sum()
print(f"  Agents with groupId: {agent_gid:,} / {len(agents):,}")

print(f"\n=== Among consumers: groupId populated? ===")
consumer_gid = consumers[gid_col].notna().sum()
print(f"  Consumers with groupId: {consumer_gid:,} / {len(consumers):,}")

print(f"\n=== groupId count per user ===")
print("Agents:", agents["groupId_count"].value_counts().sort_index().to_dict())
print("Consumers:", consumers["groupId_count"].value_counts().sort_index().to_dict())


def domain(email):
    try:
        return str(email).split("@")[1].lower()
    except Exception:
        return None


print(f"\n=== Agent top email domains (10) ===")
print(agents[email_col].dropna().apply(domain).value_counts().head(10).to_string())

print(f"\n=== Consumer top email domains (10) ===")
print(consumers[email_col].dropna().apply(domain).value_counts().head(10).to_string())

print(f"\n=== Sample distinct_ids (agents) ===")
print(agents[distinct_id_col].head(5).tolist())

print(f"\n=== Sample agentIDs values (agents) ===")
print(agents["agentIDs"].head(10).tolist())

