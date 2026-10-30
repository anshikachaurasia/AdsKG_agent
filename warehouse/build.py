"""M1: build the 28 warehouse tables and print their row counts.

Run from the project folder:
    .venv/bin/python warehouse/build.py
"""
from pathlib import Path

import duckdb

PROJECT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT / "data" / "ads.duckdb"
SQL_PATH = PROJECT / "warehouse" / "build_tables.sql"

RAW_TABLES = ["raw_sample", "ad_feature", "user_profile"]


def build():
    con = duckdb.connect(str(DB_PATH))
    print("Building tables (takes a minute or two)...")
    con.execute(SQL_PATH.read_text())
    return con


def row_counts(con):
    tables = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_type = 'BASE TABLE' ORDER BY table_name"
    ).fetchall()
    built = [t for (t,) in tables if t not in RAW_TABLES]
    print(f"\n{len(built)} warehouse tables:")
    for name in built:
        n = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"  {name:32s} {n:>12,}")
    return built


def checks(con):
    """Simple sanity checks: totals must match the raw data."""
    raw_views, raw_clicks = con.execute("SELECT COUNT(*), SUM(clk) FROM raw_sample").fetchone()
    fact_views, fact_clicks = con.execute("SELECT COUNT(*), SUM(is_click) FROM fact_ad_events").fetchone()
    hourly_clicks = con.execute("SELECT SUM(clicks) FROM agg_campaign_hourly").fetchone()[0]
    daily_clicks = con.execute("SELECT SUM(clicks) FROM agg_campaign_daily").fetchone()[0]
    today_clicks = con.execute(
        "SELECT SUM(is_click) FROM fact_ad_events WHERE event_date = DATE '2017-05-13'"
    ).fetchone()[0]

    print("\nChecks:")
    print("  every raw impression is in fact_ad_events:", raw_views == fact_views and raw_clicks == fact_clicks)
    print("  hourly clicks = all clicks:               ", hourly_clicks == raw_clicks)
    print("  daily clicks = all clicks minus today:    ", daily_clicks == raw_clicks - today_clicks)


if __name__ == "__main__":
    con = build()
    row_counts(con)
    checks(con)
    con.close()
