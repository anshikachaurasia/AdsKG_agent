"""Small checks on the agent's tool results and answers (plain Python, so they are easy to unit-test).

  fit_rows        a long SQL result is shortened by dropping ROWS, so it stays valid JSON for the agent
                  (cutting the text in the middle broke the JSON, and the query then counted as a failed run)
  unrun_sql       the answer shows SQL that was never actually run (the agent is sent back to run it)
  says_not_sure   the answer is an abstention ("not sure ..."), not a real answer with a caveat
"""
import json
import re

MAX_RESULT_CHARS = 4000   # keep tool results short so the agent's context stays small


def fit_rows(data, limit=MAX_RESULT_CHARS):
    """JSON text of a tool result that fits in `limit` characters, shortening its row list if needed."""
    if isinstance(data, str):            # an error message: plain text
        return data[:limit]
    text = json.dumps(data, default=str)
    if len(text) <= limit or not isinstance(data, dict) or not data.get("rows"):
        return text[:limit]
    rows, keep = data["rows"], len(data["rows"])
    while keep > 0:
        keep = keep * 3 // 4
        shorter = {**data, "rows": rows[:keep], "rows_shown": keep,
                   "note": f"only the first {keep} of {len(rows)} rows are shown"}
        text = json.dumps(shorter, default=str)
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


def says_not_sure(answer):
    """An abstention STARTS with "not sure" (a caveat later in a real answer doesn't count)."""
    start = re.sub(r"^[\s*_#>`-]+", "", (answer or "").lower())
    return start.startswith(("not sure", "i'm not sure", "i am not sure", "i’m not sure"))
