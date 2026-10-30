"""M9: the AI grader (qualitative check) and the agreement test.

A different, larger model (gpt-5) reads each answer WITHOUT knowing which version wrote it and WITHOUT the
gold answer. It only gets the question, the warehouse rules, the SQL, its result and (for E) the written answer.
It scores 1-5 on relevance, caveats (traps such as suspicious clicks, today being incomplete) and faithfulness
(does the written answer match the result; E only), plus "acceptable: yes/no".

Run from the project folder:
    .venv/bin/python harness/judge.py             # grade the first test run of every main version
    .venv/bin/python harness/judge.py --sheet     # write 30 answers for YOU to grade (results/human_grading.csv)
    .venv/bin/python harness/judge.py --kappa     # after grading: agreement between you and the AI grader
"""
import argparse
import csv
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path += [str(PROJECT / "agent"), str(PROJECT / "harness")]
from llm import ask  # noqa: E402
from stats import MAIN, load_runs  # noqa: E402

JUDGE_MODEL = "gpt-5"
OUT = PROJECT / "results" / "judge"
SHEET = PROJECT / "results" / "human_grading.csv"
SHEET_KEY = PROJECT / "results" / "human_grading_key.json"
RULES = (PROJECT / "warehouse" / "rules.md").read_text()

PROMPT = """You grade answers from an ads-analytics assistant. Be strict but fair.

Warehouse rules:
{rules}

Question: {question}

SQL the assistant ran:
{sql}

Result ({n} rows, first 10 shown), columns {columns}:
{rows}

Written answer: {answer}

Score each 1-5 (5 = best):
- relevance: does the query answer exactly what was asked (right measure, entity, time window, filters)?
- caveats: does it respect the rules that matter here (valid vs all traffic, today/live incomplete, reach is
  unique people, weekly days_in_week, ...)? 5 if nothing special applies and nothing is broken.
- faithfulness: does the written answer match the result? Use null if there is no written answer.
acceptable: "yes" if a business user would be correctly served by this answer, otherwise "no".

Reply with JSON only: {{"relevance": n, "caveats": n, "faithfulness": n or null, "acceptable": "yes"/"no", "reason": "one sentence"}}"""


def judge_one(record):
    no_answer = "(none: this version returns only the query result)"
    text = PROMPT.format(rules=RULES, question=record["question"], sql=record["sql"] or "(no SQL: said 'not sure')",
                         n=len(record["result"]), columns=record["columns"], rows=record["result"][:10],
                         answer=record.get("answer") or no_answer)
    reply, usage = ask(JUDGE_MODEL, "You are a careful grader. Reply with JSON only.", text)
    try:
        grade = json.loads(reply[reply.index("{"): reply.rindex("}") + 1])
    except ValueError:
        grade = {"acceptable": "no", "reason": f"unreadable grade: {reply[:100]}"}
    return {"id": record["id"], "correct": record["correct"], **grade, **usage}


def run_judge():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in MAIN:
        runs = load_runs(name)
        path = OUT / f"{name}.jsonl"
        if not runs or path.exists():
            continue
        records = list(runs[0].values())
        with ThreadPoolExecutor(8) as pool:
            grades = list(pool.map(judge_one, records))
        path.write_text("".join(json.dumps(g) + "\n" for g in grades))
        print(f"{name}: graded {len(grades)}")
    summarize()


def cohen_kappa(a, b):
    """Agreement between two yes/no graders, corrected for agreement by chance (1 = perfect, 0 = chance)."""
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    p_a, p_b = sum(a) / n, sum(b) / n
    chance = p_a * p_b + (1 - p_a) * (1 - p_b)
    return 1.0 if chance == 1 else (observed - chance) / (1 - chance)


def load_grades(name):
    path = OUT / f"{name}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def summarize():
    summary = {}
    print(f"\n{'version':10s} acceptable  relevance  caveats  faithful  agree-with-exec-accuracy (kappa)")
    for name in MAIN:
        grades = load_grades(name)
        if not grades:
            continue
        mean = lambda key: round(sum(g[key] for g in grades if g.get(key) is not None) /
                                 max(1, sum(g.get(key) is not None for g in grades)), 2)
        ok = [g.get("acceptable") == "yes" for g in grades]
        kappa = cohen_kappa(ok, [g["correct"] for g in grades])
        summary[name] = {"acceptable": round(sum(ok) / len(ok), 3), "relevance": mean("relevance"),
                         "caveats": mean("caveats"), "faithfulness": mean("faithfulness") if name.startswith("E") else None,
                         "kappa_vs_exec_accuracy": round(kappa, 2)}
        s = summary[name]
        print(f"{name:10s} {s['acceptable']:.3f}       {s['relevance']:.2f}       {s['caveats']:.2f}     "
              f"{s['faithfulness'] if s['faithfulness'] is not None else '-':>5}     {kappa:.2f}")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))


def make_sheet():
    """30 answers (5 per version, fixed seed), shuffled, version hidden. Fill in the column your_acceptable."""
    rng = random.Random(42)
    picked = []
    for name in MAIN:
        runs = load_runs(name)
        picked += [(name, r) for r in rng.sample(list(runs[0].values()), 5)]
    rng.shuffle(picked)
    with open(SHEET, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item", "question", "sql", "result_first_rows", "written_answer", "your_acceptable (yes/no)", "your_note"])
        for k, (_, r) in enumerate(picked, start=1):
            w.writerow([k, r["question"], r["sql"], json.dumps(r["result"][:10]), r.get("answer", ""), "", ""])
    SHEET_KEY.write_text(json.dumps({k: [name, r["id"]] for k, (name, r) in enumerate(picked, start=1)}, indent=1))
    print(f"Wrote {SHEET}. Open it in Excel/Numbers, fill 'your_acceptable' with yes/no (use warehouse/rules.md), save as CSV.")


def kappa_with_human():
    key = json.loads(SHEET_KEY.read_text())
    human, ai = [], []
    for row in csv.DictReader(open(SHEET)):
        mine = row["your_acceptable (yes/no)"].strip().lower()
        if mine not in ("yes", "no"):
            continue
        name, qid = key[row["item"]]
        grade = next(g for g in load_grades(name) if g["id"] == qid)
        human.append(mine == "yes")
        ai.append(grade.get("acceptable") == "yes")
    if not human:
        raise SystemExit("No grades found yet - fill in the 'your_acceptable' column first.")
    agree = sum(h == a for h, a in zip(human, ai))
    print(f"{len(human)} answers graded by you. Same verdict as the AI grader: {agree}/{len(human)}. "
          f"Cohen's kappa = {cohen_kappa(human, ai):.2f} (target >= 0.6)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet", action="store_true")
    parser.add_argument("--kappa", action="store_true")
    args = parser.parse_args()
    make_sheet() if args.sheet else kappa_with_human() if args.kappa else run_judge()
