"""M3 step 3: double-check gold answers a second, independent way.

The gold SQL uses the warehouse tables built in M1. Here the same answers are recomputed
straight from the RAW tables (raw_sample + ad_feature), without using any M1 table.
If both ways agree, the gold answer AND the warehouse build are very likely right.

Run from the project folder:
    .venv/bin/python benchmark/cross_check.py
"""
import json
from pathlib import Path

import duckdb

PROJECT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT / "data" / "ads.duckdb"
BENCH = PROJECT / "benchmark"

# China-time date of a raw impression
RAW_DATE = "CAST(to_timestamp(r.time_stamp) AT TIME ZONE 'Asia/Shanghai' AS DATE)"
RAW = "raw_sample r JOIN ad_feature a ON a.adgroup_id = r.adgroup_id"

# template -> SQL on the raw tables only
RAW_SQL = {
    "E1": f"SELECT SUM(r.clk) / COUNT(*) FROM {RAW} WHERE a.campaign_id = {{campaign}} AND {RAW_DATE} = '{{date}}'",
    "E2": f"SELECT SUM(r.clk) FROM raw_sample r WHERE r.adgroup_id = {{ad}} AND {RAW_DATE} = '{{date}}'",
    "E3": f"SELECT COUNT(*) FROM {RAW} WHERE a.brand = {{brand}} AND {RAW_DATE} = '{{date}}'",
    "E7": "SELECT price FROM ad_feature WHERE adgroup_id = {ad}",
    "T2": f"SELECT COUNT(DISTINCT r.user_id) FROM {RAW} WHERE a.campaign_id = {{campaign}} AND {RAW_DATE} <= '2017-05-12'",
    "T3": f"SELECT COUNT(DISTINCT r.user_id) FROM {RAW} WHERE a.campaign_id = {{campaign_live}} "
          "AND to_timestamp(r.time_stamp) AT TIME ZONE 'Asia/Shanghai' >= TIMESTAMP '2017-05-13 18:00:00'",
    "T7": f"SELECT COUNT(DISTINCT r.user_id) FROM {RAW} WHERE a.brand = {{brand}} AND {RAW_DATE} = '2017-05-12'",
}


def cross_check():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    questions = [json.loads(line) for line in (BENCH / "questions.jsonl").read_text().splitlines()]
    gold = {r["id"]: r["rows"] for r in map(json.loads, (BENCH / "gold_results.jsonl").read_text().splitlines())}

    agree = disagree = 0
    for q in questions:
        if q["template"] not in RAW_SQL:
            continue
        raw_answer = con.execute(RAW_SQL[q["template"]].format(**q["values"])).fetchone()[0]
        gold_answer = gold[q["id"]][0][0]
        same = abs(float(raw_answer) - float(gold_answer)) < 1e-9
        agree += same
        disagree += not same
        print(f"{'OK  ' if same else 'DIFF'} {q['id']} {q['template']}  gold={gold_answer}  raw={raw_answer}")
    con.close()
    print(f"\nAgree: {agree}   Disagree: {disagree}")


if __name__ == "__main__":
    cross_check()
