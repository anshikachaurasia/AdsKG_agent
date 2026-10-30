"""M9: final numbers from the TEST runs (3 runs per version), with error bars and significance tests.

  - accuracy = mean over all 3 runs x 80 questions
  - 95% bootstrap confidence interval: re-draw the 80 questions with replacement 10,000 times
    (each question keeps its 3 runs), and take the middle 95% of the accuracies
  - McNemar test (exact): compares two versions on the SAME questions. A question counts as "right" for a
    version if it was right in at least 2 of 3 runs. Only questions where the two versions disagree matter.
    p < 0.05 = the difference is unlikely to be luck. With 8 comparisons, some p < 0.05 happen by luck alone, so
    we also show the stricter Bonferroni check: p < 0.05 / 8 = 0.00625.
  - only COMPLETE runs are used (a quick --limit try is skipped, so it can't skew the numbers)

Run from the project folder:
    .venv/bin/python harness/stats.py          # prints tables, writes results/final_summary.json
"""
import glob
import json
import random
import statistics
from math import comb
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
RESULTS = PROJECT / "results"
BENCH = PROJECT / "benchmark"

MAIN = ["A", "B", "C", "D", "E", "E_memory"]
# post-hoc: the agent re-run with the fixes made after the code review (reported apart from the frozen results)
POSTHOC = ["E_fixed", "E_memory_fixed"]
POSTHOC_PAIRS = [("A", "E_memory"), ("E", "E_fixed"), ("E_memory", "E_memory_fixed"), ("A", "E_memory_fixed")]
PAIRS = [("A", "B"), ("B", "C"), ("C", "D"), ("D", "E"), ("B", "D"), ("A", "D"), ("A", "E"), ("E", "E_memory")]


def expected_count(suffix):
    """How many answers a complete run has: questions in the split, or turns for conversations."""
    split, kind = suffix.split("_")[0], "conversations" if "_conv" in suffix else "questions"
    items = [json.loads(line) for line in (BENCH / f"{kind}.jsonl").read_text().splitlines()]
    items = [x for x in items if x["split"] == split]
    return sum(len(x["turns"]) for x in items) if kind == "conversations" else len(items)


def load_runs(name, suffix="test"):
    """All COMPLETE runs of one config: a list of runs, each {question id: record}."""
    runs, expected = [], expected_count(suffix)
    for folder in sorted(glob.glob(str(RESULTS / f"*_{name}_{suffix}"))):
        lines = Path(folder, "answers.jsonl").read_text().splitlines()
        if len(lines) != expected:
            print(f"  (skipped incomplete run {Path(folder).name}: {len(lines)} of {expected} answers)")
            continue
        runs.append({r["id"]: r for r in map(json.loads, lines)})
    return runs


def per_question(runs, ids):
    """Fraction of runs that got each question right."""
    return {i: sum(run[i]["correct"] for run in runs) / len(runs) for i in ids}


def bootstrap_ci(scores, n=10_000, seed=42):
    rng = random.Random(seed)
    values = list(scores.values())
    means = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n)]


def mcnemar(right_a, right_b):
    """Exact McNemar test. right_a / right_b: {question id: True/False}. Returns (only A right, only B right, p)."""
    only_a = sum(right_a[i] and not right_b[i] for i in right_a)
    only_b = sum(right_b[i] and not right_a[i] for i in right_a)
    n = only_a + only_b
    if n == 0:
        return only_a, only_b, 1.0
    tail = sum(comb(n, k) for k in range(min(only_a, only_b) + 1)) / 2 ** n
    return only_a, only_b, min(1.0, 2 * tail)


def describe(runs, tiers=("easy", "medium", "tricky")):
    records = [r for run in runs for r in run.values()]
    mean = lambda key, rs: round(sum(r[key] for r in rs) / len(rs), 3) if rs else None
    ids = list(runs[0])
    lo, hi = bootstrap_ci(per_question(runs, ids))
    out = {"runs": len(runs), "questions": len(ids), "accuracy": mean("correct", records),
           "ci_low": round(lo, 3), "ci_high": round(hi, 3),
           "run_accuracies": [round(sum(r["correct"] for r in run.values()) / len(run), 3) for run in runs]}
    for tier in tiers:
        out[f"accuracy_{tier}"] = mean("correct", [r for r in records if r["tier"] == tier])
    hard = [r for r in records if r["tier"] in ("medium", "tricky")]
    out.update({
        "accuracy_hard": mean("correct", hard),
        "table_f1": mean("table_f1", records),
        "gold_tables_shown": mean("gold_tables_shown", records),
        "not_sure": round(sum(r["error"].startswith("no SQL") for r in records) / len(runs), 1),
        "median_seconds": round(statistics.median(r["seconds"] for r in records), 1),
        "median_cost_usd": round(statistics.median(r["cost_usd"] for r in records), 4),
        "avg_cost_usd": round(sum(r["cost_usd"] for r in records) / len(records), 5),
    })
    return out


def main():
    summary = {"questions": {}, "pairs": [], "conversations": {}, "ablation": {}, "catalog": {},
               "posthoc": {}, "posthoc_pairs": []}

    # main versions, 3 runs each
    all_runs = {name: load_runs(name) for name in MAIN}
    all_runs = {k: v for k, v in all_runs.items() if v}
    print(f"{'version':10s} runs  accuracy  95% CI          easy  medium tricky  F1    shown  med s  med $")
    for name, runs in all_runs.items():
        d = summary["questions"][name] = describe(runs)
        print(f"{name:10s} {d['runs']:4d}  {d['accuracy']:.3f}     [{d['ci_low']:.3f}, {d['ci_high']:.3f}]  "
              f"{d['accuracy_easy']:.2f}  {d['accuracy_medium']:.2f}   {d['accuracy_tricky']:.2f}   "
              f"{d['table_f1']:.2f}  {d['gold_tables_shown']:.2f}   {d['median_seconds']:5.1f}  {d['median_cost_usd']:.4f}")

    # McNemar on majority vote (right in >= 2 of 3 runs)
    bonferroni = 0.05 / len(PAIRS)
    print(f"\nMcNemar (right in >= 2 of 3 runs)       only first right  only second right  p        p < {bonferroni:.5f}?")
    for a, b in PAIRS:
        if a in all_runs and b in all_runs:
            ids = list(all_runs[a][0])
            right_a = {i: s >= 0.5 for i, s in per_question(all_runs[a], ids).items()}
            right_b = {i: s >= 0.5 for i, s in per_question(all_runs[b], ids).items()}
            only_a, only_b, p = mcnemar(right_a, right_b)
            summary["pairs"].append({"a": a, "b": b, "only_a": only_a, "only_b": only_b, "p": round(p, 4),
                                     "holds_after_bonferroni": p < bonferroni})
            print(f"  {a:9s} vs {b:9s}                   {only_a:6d}            {only_b:6d}         {p:.4f}   "
                  f"{'yes' if p < bonferroni else 'no'}")

    # follow-up conversations: chat memory on vs off
    print("\nConversations (15 x 3 turns)   all    turn1  turn2  turn3   95% CI")
    for name in ["E", "E_nochat"]:
        runs = load_runs(name, "test_conv")
        if not runs:
            continue
        records = [r for run in runs for r in run.values()]
        by_turn = [round(sum(r["correct"] for r in records if r["id"].endswith(f"_t{t}")) /
                         sum(r["id"].endswith(f"_t{t}") for r in records), 3) for t in (1, 2, 3)]
        lo, hi = bootstrap_ci(per_question(runs, list(runs[0])))
        acc = round(sum(r["correct"] for r in records) / len(records), 3)
        summary["conversations"][name] = {"runs": len(runs), "accuracy": acc, "turns": by_turn,
                                          "ci_low": round(lo, 3), "ci_high": round(hi, 3)}
        print(f"  {name:28s} {acc:.3f}  {by_turn[0]:.3f}  {by_turn[1]:.3f}  {by_turn[2]:.3f}   [{lo:.3f}, {hi:.3f}]")

    # one-run extras: C ablation and the bigger catalog
    print("\nC ablation (1 run)")
    for name in ["C_no_rewrite", "C_no_hybrid", "C_no_rerank"]:
        runs = load_runs(name)
        if runs:
            d = summary["ablation"][name] = describe(runs)
            print(f"  {name:14s} {d['accuracy']:.3f}  [{d['ci_low']:.3f}, {d['ci_high']:.3f}]  shown {d['gold_tables_shown']:.2f}")
    print("\nBigger catalog (1 run each; 28 = mean of the 3 main runs)   accuracy / avg $ per question")
    for name in ["A", "B", "C", "D"]:
        row = {28: summary["questions"].get(name)}
        for size in (100, 250):
            runs = load_runs(name, f"test_cat{size}")
            row[size] = describe(runs) if runs else None
        summary["catalog"][name] = row
        print(f"  {name}  " + "   ".join(f"{s}: {d['accuracy']:.3f} / ${d['avg_cost_usd']:.4f}" for s, d in row.items() if d))

    # post-hoc: the fixed agent (practice and test)
    fixed = {name: load_runs(name) for name in POSTHOC}
    if any(fixed.values()):
        print("\nPOST-HOC: agent with the review fixes (not part of the frozen results)")
        for name, runs in fixed.items():
            if not runs:
                continue
            d = summary["posthoc"][name] = describe(runs)
            practice = load_runs(name, "practice")
            d["practice_accuracy"] = describe(practice)["accuracy"] if practice else None
            print(f"  {name:15s} test {d['accuracy']:.3f} [{d['ci_low']:.3f}, {d['ci_high']:.3f}] ({d['runs']} runs)  "
                  f"medium {d['accuracy_medium']:.2f}  tricky {d['accuracy_tricky']:.2f}  not sure/run {d['not_sure']}  "
                  f"practice {d['practice_accuracy']}")
        everything = {**all_runs, **fixed}
        for a, b in POSTHOC_PAIRS:
            if everything.get(a) and everything.get(b):
                ids = list(everything[a][0])
                right_a = {i: s >= 0.5 for i, s in per_question(everything[a], ids).items()}
                right_b = {i: s >= 0.5 for i, s in per_question(everything[b], ids).items()}
                only_a, only_b, p = mcnemar(right_a, right_b)
                summary["posthoc_pairs"].append({"a": a, "b": b, "only_a": only_a, "only_b": only_b, "p": round(p, 4)})
                print(f"  McNemar {a} vs {b}: only first right {only_a}, only second right {only_b}, p = {p:.4f}")

    (RESULTS / "final_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nSaved to {RESULTS / 'final_summary.json'}")


if __name__ == "__main__":
    main()
