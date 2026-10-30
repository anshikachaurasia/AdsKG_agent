"""Scoring: is the answer right, and were the right tables used?

Execution accuracy (the main score):
  The predicted query's result must contain the gold result.
  - row order does not matter
  - numbers are compared after rounding to 4 decimals
  - EXTRA columns are allowed (e.g. returning clicks AND ctr when only ctr was asked),
    but every gold column must be there and the rows must line up.
"""


def normalize(value):
    """Make values comparable: numbers -> rounded floats ('2' and 2 become 2.0), the rest -> text."""
    if value is None:
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return str(value)


def results_match(gold_rows, pred_rows):
    if not gold_rows or len(gold_rows) != len(pred_rows):
        return False
    gold = [[normalize(v) for v in row] for row in gold_rows]
    pred = [[normalize(v) for v in row] for row in pred_rows]

    # for every gold column, the predicted columns holding the same values (there can be several)
    gold_cols = list(zip(*gold))
    pred_cols = list(zip(*pred))
    candidates = [[i for i, p in enumerate(pred_cols) if sorted(p, key=str) == sorted(g, key=str)] for g in gold_cols]
    gold_sorted = sorted((tuple(row) for row in gold), key=str)

    def lines_up(chosen):
        """The chosen columns must also line up row by row."""
        return sorted((tuple(row[i] for i in chosen) for row in pred), key=str) == gold_sorted

    def try_columns(chosen):
        """Try every way of pairing gold columns with predicted ones (backtracking), not just the first match."""
        if len(chosen) == len(gold_cols):
            return lines_up(chosen)
        return any(try_columns(chosen + [i]) for i in candidates[len(chosen)] if i not in chosen)

    return try_columns([])


def table_scores(used, gold):
    """Precision, recall and F1 of the tables the query used vs the gold tables."""
    used, gold = set(used), set(gold)
    hits = len(used & gold)
    precision = hits / len(used) if used else 0.0
    recall = hits / len(gold) if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return round(precision, 3), round(recall, 3), round(f1, 3)
