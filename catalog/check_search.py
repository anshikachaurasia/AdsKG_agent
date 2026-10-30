"""M2 done-test: do 10 sample questions find the right table in the top 5?

These are quick sanity checks only - NOT the real test questions (those are written in M3).

Run from the project folder:
    .venv/bin/python catalog/check_search.py
"""
from qdrant_client import QdrantClient

from load_qdrant import QDRANT_PATH
from search import search_tables

# (question, the table that should be found)
SAMPLES = [
    ("What was the CTR for campaign 359520 yesterday?", "agg_campaign_daily"),
    ("How many clicks did campaign 359520 get each hour today?", "agg_campaign_hourly"),
    ("How many unique people saw campaign 83237 in the last 6 hours?", "live_reach_campaign_last6h"),
    ("Total unique users reached by campaign 359520 over the whole week", "reach_campaign_total"),
    ("Clicks for brand 95471 per day", "agg_brand_daily"),
    ("Campaign 359520 clicks with bot traffic removed", "agg_campaign_daily_valid"),
    ("Split campaign 359520 CTR by age and gender", "agg_campaign_daily_by_audience"),
    ("Which advertiser owns campaign 83237?", "dim_campaign"),
    ("Which product category had the most clicks yesterday?", "agg_category_daily"),
    ("Which users clicked suspiciously many times in one hour?", "ref_suspicious_user_hours"),
]


def run_checks(k=5):
    client = QdrantClient(path=str(QDRANT_PATH))
    top1 = top_k = 0
    for question, expected in SAMPLES:
        found = [table for table, _ in search_tables(question, k=k, client=client)]
        rank = found.index(expected) + 1 if expected in found else None
        top1 += rank == 1
        top_k += rank is not None
        mark = "OK " if rank else "MISS"
        print(f"{mark} rank={rank}  {question}\n       expected {expected}; got {found[:3]}")
    client.close()
    print(f"\nRight table ranked 1st: {top1}/{len(SAMPLES)}   in top {k}: {top_k}/{len(SAMPLES)}")


if __name__ == "__main__":
    run_checks()
