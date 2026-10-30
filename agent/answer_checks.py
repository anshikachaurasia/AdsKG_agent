"""Small checks on the agent's tool results and answers (plain Python, so they are easy to unit-test).

  fit_rows        a long tool result is shortened by dropping LIST ITEMS (SQL rows, search hits, columns ...),
                  so it stays valid JSON for the agent (cutting the text in the middle broke the JSON: a query then
                  counted as a failed run, and tables in a cut search result were missed)
  unrun_sql       the answer shows SQL that was never actually run (the agent is sent back to run it)
  RUN_IT          the message that sends it back; it only matters for the current question (drop_old_run_it)
  says_not_sure   the answer is an abstention ("not sure ..."), not a real answer with a caveat
"""
import json
import re

MAX_RESULT_CHARS = 4000   # keep tool results short so the agent's context stays small
RUN_IT = ("Your answer shows SQL that you have not run. Run it with run_sql now, then answer from its actual "
          "result (or say \"not sure\").")


def _shortened(data, keep):
    """`data` with its list cut to `keep` items, plus a note saying so."""
    if isinstance(data, list):
        return data[:keep] + [{"note": f"only the first {keep} of {len(data)} results are shown"}]
    key = "rows" if isinstance(data.get("rows"), list) else max(
        (k for k, v in data.items() if isinstance(v, list)), key=lambda k: len(data[k]))
    return {**data, key: data[key][:keep], f"{key}_shown": keep,
            "note": f"only the first {keep} of {len(data[key])} {key} are shown"}


def fit_rows(data, limit=MAX_RESULT_CHARS):
    """JSON text of a tool result that fits in `limit` characters, shortening its longest list if needed."""
    if isinstance(data, str):            # an error message: plain text
        return data[:limit]
    text = json.dumps(data, default=str)
    if len(text) <= limit:
        return text
    if isinstance(data, list):
        size = len(data)
    elif isinstance(data, dict) and any(isinstance(v, list) and v for v in data.values()):
        size = len(data["rows"]) if isinstance(data.get("rows"), list) and data["rows"] else \
            max(len(v) for v in data.values() if isinstance(v, list))
    else:
        return text[:limit]
    keep = size
    while keep > 0:
        keep = keep * 3 // 4
        text = json.dumps(_shortened(data, keep), default=str)
        if len(text) <= limit:
            return text
    return text


def normalize_sql(sql):
    """Ignore case, spacing and a final semicolon when comparing two queries."""
    return re.sub(r"\s+", " ", sql).strip().rstrip(";").strip().lower()


def sql_blocks(text):
    """The ```sql code blocks in an answer."""
    return [b.strip() for b in re.findall(r"```sql\s*(.*?)```", text or "", flags=re.S | re.I) if b.strip()]


def unrun_sql(answer, ran_ok):
    """True if the answer shows SQL that is not one of the queries that ran without an error."""
    ran = {normalize_sql(s) for s in ran_ok}
    return any(normalize_sql(b) not in ran for b in sql_blocks(answer))


def drop_old_run_it(messages, question_start):
    """Keep the "run your SQL" message only for the current question (from `question_start` on), not later turns."""
    return [m for i, m in enumerate(messages) if i >= question_start or getattr(m, "content", None) != RUN_IT]


def says_not_sure(answer):
    """An abstention STARTS with "not sure" (a caveat later in a real answer doesn't count)."""
    start = re.sub(r"^[\s*_#>`-]+", "", (answer or "").lower())
    return start.startswith(("not sure", "i'm not sure", "i am not sure", "i’m not sure"))
