"""M3 step 2: run every gold SQL, check the answers are usable, and save them.

Checks for every question / conversation turn:
  - the SQL runs
  - it returns at least one row, and the first value is not empty (NULL)
  - "top 1" questions (ending in LIMIT 1) have no tie for first place

Writes benchmark/gold_results.jsonl (the correct answer for each question / turn).

Run from the project folder:
    .venv/bin/python benchmark/check_gold.py            # check + save answers
    .venv/bin/python benchmark/check_gold.py --freeze   # ...and freeze the benchmark (after you reviewed it!)
"""
import hashlib
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "mcp_server"))
from safety import connect  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT / "data" / "ads.duckdb"
BENCH = PROJECT / "benchmark"
FROZEN = BENCH / "FROZEN.txt"


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def to_plain(value):
    """Make database values JSON-friendly (dates -> text, decimals -> float)."""
    if isinstance(value, (int, float, str)) or value is None:
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def run_gold(con, sql_file):
    """Run one gold SQL. Returns (rows, problem). problem is '' when everything is fine."""
    sql = (BENCH / sql_file).read_text().strip()
    try:
        rows = con.execute(sql).fetchall()
    except Exception as e:
        return [], f"SQL error: {e}"
    if not rows:
        return [], "no rows"
    if rows[0][0] is None:
        return rows, "answer is NULL"
    if sql.endswith("LIMIT 1"):
        top2 = con.execute(sql[: -len("LIMIT 1")] + "LIMIT 2").fetchall()
        if len(top2) == 2 and top2[0][1] == top2[1][1]:
            return rows, "tie for first place"
    return [[to_plain(v) for v in row] for row in rows], ""


def fingerprint():
    """One code that changes if any question or gold SQL changes."""
    h = hashlib.sha256()
    for path in [BENCH / "questions.jsonl", BENCH / "conversations.jsonl", *sorted((BENCH / "gold").glob("*.sql"))]:
        h.update(path.read_bytes())
    return h.hexdigest()[:16]


def check_gold():
    con = connect(DB_PATH)   # read-only, no file access (same as everywhere else)
    questions = load_jsonl(BENCH / "questions.jsonl")
    conversations = load_jsonl(BENCH / "conversations.jsonl")

    results, problems = [], []
    for q in questions:
        rows, problem = run_gold(con, q["gold_sql"])
        results.append({"id": q["id"], "rows": rows})
        if problem:
            problems.append(f"{q['id']}: {problem}")
    for c in conversations:
        for k, turn in enumerate(c["turns"], start=1):
            rows, problem = run_gold(con, turn["gold_sql"])
            results.append({"id": f"{c['id']}_t{k}", "rows": rows})
            if problem:
                problems.append(f"{c['id']}_t{k}: {problem}")
    con.close()

    with open(BENCH / "gold_results.jsonl", "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # summary
    print(f"Questions: {len(questions)}  " + str(dict(Counter((q['tier'], q['split']) for q in questions))))
    print(f"Conversations: {len(conversations)}  " + str(dict(Counter(c['split'] for c in conversations))))
    duplicates = [q for q, n in Counter(q["question"] for q in questions).items() if n > 1]
    print(f"Duplicate questions: {len(duplicates)}")
    print(f"Gold SQL run: {len(results)}   problems: {len(problems)}")
    for p in problems:
        print("  PROBLEM", p)
    print(f"Fingerprint: {fingerprint()}")
    return not problems and not duplicates


def freeze():
    FROZEN.write_text(
        f"Benchmark frozen on {date.today()}\n"
        f"Fingerprint: {fingerprint()}\n"
        "Do not edit questions.jsonl, conversations.jsonl or gold/*.sql after this point.\n"
    )
    print(f"FROZEN -> {FROZEN}")


if __name__ == "__main__":
    ok = check_gold()
    if "--freeze" in sys.argv:
        if ok:
            freeze()
        else:
            print("Not freezing: fix the problems first.")
