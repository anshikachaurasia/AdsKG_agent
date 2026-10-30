"""M5 done-test: does get_join_path find the right bridge tables on 10 checks?

Run from the project folder (Neo4j must be running):
    .venv/bin/python catalog/check_graph.py
"""
from graph import get_join_path

# (from, to, the route must go through one of these tables; [] = they join directly)
CHECKS = [
    ("dim_user", "agg_campaign_daily", ["fact_ad_events"]),
    ("agg_brand_daily", "agg_category_daily", ["dim_ad"]),
    ("agg_campaign_daily", "dim_date", []),
    ("agg_ad_daily", "dim_advertiser", ["dim_ad", "dim_campaign"]),
    ("ref_suspicious_user_hours", "fact_ad_events", []),
    ("dim_user", "dim_ad", ["fact_ad_events"]),
    ("reach_campaign_total", "dim_advertiser", ["dim_campaign"]),
    ("live_campaign_last6h", "dim_campaign", []),
    ("agg_campaign_daily_by_audience", "dim_user", ["fact_ad_events"]),
    ("dim_user", "dim_placement", ["fact_ad_events"]),
]


def run_checks():
    passed = 0
    for a, b, bridges in CHECKS:
        path = get_join_path(a, b)
        middle = path[1:-1]
        ok = bool(path) and (middle == [] if not bridges else any(t in middle for t in bridges))
        passed += ok
        print(f"{'OK  ' if ok else 'FAIL'} {a} -> {b}\n      route: {' -> '.join(path) or 'none'}")
    print(f"\nPassed {passed}/{len(CHECKS)}")


if __name__ == "__main__":
    run_checks()
