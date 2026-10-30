"""The test harness: run one version on a set of questions (or conversations) and score it.

Run from the project folder:
    .venv/bin/python harness/run.py configs/A.yaml --split practice
    .venv/bin/python harness/run.py configs/B.yaml --split practice --limit 5      # quick try
    .venv/bin/python harness/run.py configs/E.yaml --split practice --conversations # follow-up conversations
    .venv/bin/python harness/run.py configs/E.yaml --split practice --learn          # save correct answers to memory
    .venv/bin/python harness/run.py configs/A.yaml --split practice --catalog 250    # bigger-catalog test

Saves results/<run_id>/answers.jsonl (every question, every step) and metrics.json (the scores).
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

PROJECT = Path(__file__).resolve().parent.parent
sys.path += [str(PROJECT / "agent"), str(PROJECT / "mcp_server"), str(PROJECT / "harness")]

from metrics import results_match, table_scores  # noqa: E402
from pipelines import VERSIONS  # noqa: E402
from safety import connect, run_sql, tables_in_sql  # noqa: E402

DB_PATH = PROJECT / "data" / "ads.duckdb"
BENCH = PROJECT / "benchmark"
RESULTS = PROJECT / "results"


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def run_one(item, config, con, gold_rows, thread_id=None):
    """Run one question through one version and score it. `item` has question, gold_tables (and id, tier)."""
    start = time.time()
    try:
        out = VERSIONS[config["version"]](item["question"], config, thread_id=thread_id)
    except Exception as e:   # e.g. API error: count as wrong, keep going
        out = {"sql": "", "tables_shown": [], "tokens_in": 0, "tokens_out": 0, "error": f"{type(e).__name__}: {e}"}
    if out["sql"]:
        rows, columns, sql_error = run_sql(con, out["sql"])
    else:
        rows, columns, sql_error = [], [], out.get("error", "no SQL (not sure)")

    used = tables_in_sql(out["sql"])
    precision, recall, f1 = table_scores(used, item["gold_tables"])
    cost = (out["tokens_in"] * config["price_in_per_1m"] + out["tokens_out"] * config["price_out_per_1m"]) / 1e6

    return {
        "id": item["id"], "tier": item.get("tier", "conversation"), "template": item.get("template", ""),
        "question": item["question"],
        "sql": out["sql"], "error": sql_error,
        "result": [[str(v) for v in r] for r in rows[:20]], "columns": columns,
        "gold": gold_rows,
        "correct": not sql_error and results_match(gold_rows, rows),
        "tables_used": used, "gold_tables": item["gold_tables"],
        "table_precision": precision, "table_recall": recall, "table_f1": f1,
        "tables_shown": out["tables_shown"],
        "gold_tables_shown": set(item["gold_tables"]) <= set(out["tables_shown"]),   # recall@k for search
        "answer": out.get("answer", ""), "steps": out.get("steps", 1), "sql_errors": out.get("sql_errors", 0),
        "tool_calls": out.get("tool_calls", []),
        "tokens_in": out["tokens_in"], "tokens_out": out["tokens_out"],
        "cost_usd": round(cost, 6), "seconds": round(time.time() - start, 2),
    }


def summarize(records):
    def mean(key, rs):
        return round(sum(r[key] for r in rs) / len(rs), 4) if rs else None

    summary = {"n": len(records), "accuracy": mean("correct", records)}
    for tier in ["easy", "medium", "tricky"]:
        summary[f"accuracy_{tier}"] = mean("correct", [r for r in records if r["tier"] == tier])
    for turn in [1, 2, 3]:
        summary[f"accuracy_turn{turn}"] = mean("correct", [r for r in records if r["id"].endswith(f"_t{turn}")])
    summary.update({
        "table_f1": mean("table_f1", records),
        "gold_tables_shown": mean("gold_tables_shown", records),
        "sql_errors": sum(bool(r["error"]) for r in records),
        "not_sure": sum(r["error"].startswith("no SQL") for r in records),
        "avg_steps": mean("steps", records),
        "avg_seconds": mean("seconds", records),
        "avg_tokens_in": mean("tokens_in", records),
        "avg_cost_usd": mean("cost_usd", records),
        "total_cost_usd": round(sum(r["cost_usd"] for r in records), 4),
    })
    return {k: v for k, v in summary.items() if v is not None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--split", default="practice", choices=["practice", "test", "all"])
    parser.add_argument("--limit", type=int, default=None, help="only the first N questions (for quick tries)")
    parser.add_argument("--conversations", action="store_true", help="run the 3-turn follow-up conversations")
    parser.add_argument("--learn", action="store_true", help="save correctly answered PRACTICE questions to memory")
    parser.add_argument("--catalog", type=int, default=28, choices=[28, 100, 250],
                        help="bigger-catalog test: add distractor tables to the catalog (M8)")
    args = parser.parse_args()
    if args.learn and args.split != "practice":
        raise SystemExit("--learn is only allowed on practice questions (memory must never see test answers).")

    config = yaml.safe_load(Path(args.config).read_text())
    config["catalog_size"] = args.catalog
    gold = {r["id"]: r["rows"] for r in load_jsonl(BENCH / "gold_results.jsonl")}
    kind = "conversations" if args.conversations else "questions"
    items = load_jsonl(BENCH / f"{kind}.jsonl")
    if args.split != "all":
        items = [x for x in items if x["split"] == args.split]
    items = items[: args.limit]

    run_id = (f"{datetime.now():%Y%m%d_%H%M%S}_{Path(args.config).stem}_{args.split}"
              + ("_conv" if args.conversations else "") + (f"_cat{args.catalog}" if args.catalog != 28 else ""))
    out_dir = RESULTS / run_id
    out_dir.mkdir(parents=True)
    con = connect(DB_PATH)   # read-only, no file access

    records = []
    with open(out_dir / "answers.jsonl", "w") as f:
        for i, item in enumerate(items, start=1):
            if args.conversations:   # every turn of one conversation shares a thread (chat memory)
                turns = [{"id": f"{item['id']}_t{k}", **t} for k, t in enumerate(item["turns"], start=1)]
                results = [run_one(t, config, con, gold[t["id"]], thread_id=item["id"]) for t in turns]
            else:
                results = [run_one(item, config, con, gold[item["id"]])]
            for r in results:
                records.append(r)
                f.write(json.dumps(r) + "\n")
                print(f"[{i}/{len(items)}] {'RIGHT' if r['correct'] else 'wrong'}  {r['id']} {r['tier']:6s} {r['question'][:70]}")
                if args.learn and r["correct"] and not args.conversations:
                    from memory import remember
                    remember(r["question"], r["sql"], r["id"])
    con.close()

    summary = summarize(records)
    (out_dir / "metrics.json").write_text(json.dumps({"config": config, "split": args.split, "kind": kind, **summary}, indent=2))
    print("\n" + json.dumps(summary, indent=2))
    print(f"\nSaved to {out_dir}")


if __name__ == "__main__":
    main()
