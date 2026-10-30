"""M9: sort every wrong answer (first test run of each main version) into a failure type.

"not sure" answers are sorted by rule. All others are sorted by gpt-5, which sees the question, the trap, the
correct SQL and result, and the wrong SQL and result. A sample of its labels was checked by hand (see README).

Run from the project folder:
    .venv/bin/python harness/failures.py     # writes results/failures.jsonl and results/failures.md
"""
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path += [str(PROJECT / "agent"), str(PROJECT / "harness")]
from llm import ask  # noqa: E402
from stats import MAIN, load_runs  # noqa: E402

MODEL = "gpt-5"
BENCH = PROJECT / "benchmark"
OUT = PROJECT / "results"

TYPES = {
    "wrong_lookalike": "used a similar-looking table that gives a different answer (all vs valid traffic, hourly vs "
                       "daily, impressions vs unique people, live vs final)",
    "missing_connecting_table": "did not use a lookup table needed for the join (e.g. dim_ad for brand/category, "
                                "dim_user for gender/age)",
    "wrong_join": "joined tables but on the wrong key, or the join duplicated/lost rows",
    "too_many_tables": "used extra tables that changed the answer",
    "made_up_column": "used a column or table that does not exist",
    "wrong_time_window": "wrong date, week, hours, or used incomplete today",
    "wrong_calculation": "right tables, but wrong measure, filter, grouping, ranking or arithmetic",
    "strict_grading": "the answer is right in substance but the grader's format rules marked it wrong "
                      "(e.g. a missing extra column the gold answer requires)",
    "not_sure": "gave no SQL",
}

PROMPT = """A text-to-SQL assistant answered a question wrongly. Pick the ONE failure type that best explains why.

Types:
{types}

Question: {question}
Known trap for this question: {trap}
Correct SQL:
{gold_sql}
Correct result (first rows): {gold}

Assistant's SQL:
{sql}
Assistant's result (first rows, values stored as text - ignore number vs text): {result}
Error: {error}
Tables the assistant was shown: {shown}

Reply with JSON only: {{"type": "<one type name>", "why": "one short sentence"}}"""


def classify(item):
    name, r, q = item
    if r["error"].startswith("no SQL"):
        return {"version": name, "id": r["id"], "tier": r["tier"], "type": "not_sure", "why": "gave no SQL",
                "question": r["question"]}
    text = PROMPT.format(types="\n".join(f"- {k}: {v}" for k, v in TYPES.items()), question=r["question"],
                         trap=q["trap"] or "(none)", gold_sql=(BENCH / q["gold_sql"]).read_text().strip(),
                         gold=r["gold"][:5], sql=r["sql"], result=r["result"][:5], error=r["error"] or "(none)",
                         shown=r["tables_shown"])
    reply, _ = ask(MODEL, "You analyse SQL failures. Reply with JSON only.", text)
    try:
        label = json.loads(reply[reply.index("{"): reply.rindex("}") + 1])
    except ValueError:
        label = {"type": "other", "why": reply[:100]}
    return {"version": name, "id": r["id"], "tier": r["tier"], "type": label.get("type", "other"),
            "why": label.get("why", ""), "question": r["question"]}


def main():
    questions = {q["id"]: q for q in map(json.loads, (BENCH / "questions.jsonl").read_text().splitlines())}
    wrong = [(name, r, questions[r["id"]]) for name in MAIN for runs in [load_runs(name)] if runs
             for r in runs[0].values() if not r["correct"]]
    with ThreadPoolExecutor(8) as pool:
        labels = list(pool.map(classify, wrong))
    (OUT / "failures.jsonl").write_text("".join(json.dumps(x) + "\n" for x in labels))

    versions = [n for n in MAIN if any(x["version"] == n for x in labels)]
    counts = Counter((x["version"], x["type"]) for x in labels)
    lines = ["| Failure type | " + " | ".join(versions) + " | All |", "|---" * (len(versions) + 2) + "|"]
    for t in sorted({x["type"] for x in labels}, key=lambda t: -sum(counts[(v, t)] for v in versions)):
        row = [counts[(v, t)] for v in versions]
        lines.append(f"| {t} | " + " | ".join(map(str, row)) + f" | {sum(row)} |")
    lines.append("| **wrong answers** | " + " | ".join(str(sum(x["version"] == v for x in labels)) for v in versions) + f" | {len(labels)} |")
    lines += ["", "**Examples (first per version and type):**", ""]
    seen = set()
    for x in labels:
        if (x["version"], x["type"]) not in seen:
            seen.add((x["version"], x["type"]))
            lines.append(f"- **{x['version']} / {x['type']}** ({x['id']}, {x['tier']}): {x['question']} → {x['why']}")
    (OUT / "failures.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
