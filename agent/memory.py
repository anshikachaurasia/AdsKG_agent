"""Long-term memory: questions the agent answered CORRECTLY, reused as examples for similar new questions.

  remember(question, sql)   save one confirmed-correct example
  recall(question, k)       the k most similar saved examples (search by meaning, like M2)

Rule (from the design doc): the agent only learns from PRACTICE questions, never from test questions,
so its memory can't contain test answers.

Stored in memory/examples.jsonl (one example per line).
"""
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT / "catalog"))
from load_qdrant import embed  # noqa: E402

MEMORY_PATH = PROJECT / "memory" / "examples.jsonl"


def load_examples():
    if not MEMORY_PATH.exists():
        return []
    return [json.loads(line) for line in MEMORY_PATH.read_text().splitlines()]


def remember(question, sql, source_id):
    """Save one confirmed-correct example (source_id = the practice question it came from)."""
    MEMORY_PATH.parent.mkdir(exist_ok=True)
    with open(MEMORY_PATH, "a") as f:
        f.write(json.dumps({"question": question, "sql": sql, "source": source_id}) + "\n")


def recall(question, k=2, min_score=0.75):
    """The k saved examples most similar to the question (only if similar enough)."""
    examples = load_examples()
    if not examples:
        return []
    vectors = embed([question] + [e["question"] for e in examples])
    q, rest = vectors[0], vectors[1:]
    scored = sorted(((sum(a * b for a, b in zip(q, v)), e) for v, e in zip(rest, examples)),
                    key=lambda pair: -pair[0])
    return [e for score, e in scored[:k] if score >= min_score]


def clear():
    if MEMORY_PATH.exists():
        MEMORY_PATH.unlink()
