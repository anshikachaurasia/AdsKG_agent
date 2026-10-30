"""Safety rules for running SQL written by the AI.

Used by every version now, and by the MCP server's run_sql tool in M6.
  - the database is opened READ-ONLY (nothing can be changed)
  - exactly ONE statement, and it must be a SELECT (checked with sqlglot, a real SQL parser)
  - at most 1,000 rows come back
  - a query is stopped after 20 seconds
"""
import threading

import sqlglot
from sqlglot import exp

MAX_ROWS = 1000
TIMEOUT_SECONDS = 20


def check_sql(sql):
    """Return '' if the SQL is allowed, otherwise the reason it is blocked."""
    try:
        statements = [s for s in sqlglot.parse(sql, read="duckdb") if s is not None]
    except sqlglot.errors.ParseError as e:
        return f"cannot parse SQL: {e}"
    if len(statements) != 1:
        return "exactly one SQL statement is allowed"
    if not isinstance(statements[0], (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        return "only SELECT queries are allowed"
    return ""


def run_sql(con, sql):
    """Run one safe SELECT on a read-only connection. Returns (rows, columns, error)."""
    problem = check_sql(sql)
    if problem:
        return [], [], problem

    timer = threading.Timer(TIMEOUT_SECONDS, con.interrupt)   # stop slow queries
    timer.start()
    try:
        cursor = con.execute(sql)
        columns = [d[0] for d in cursor.description]
        rows = cursor.fetchmany(MAX_ROWS)
        return rows, columns, ""
    except Exception as e:
        return [], [], f"{type(e).__name__}: {e}"
    finally:
        timer.cancel()


def tables_in_sql(sql):
    """Names of the real tables a query reads (CTE names are not counted)."""
    try:
        tree = sqlglot.parse_one(sql, read="duckdb")
    except sqlglot.errors.ParseError:
        return []
    cte_names = {cte.alias for cte in tree.find_all(exp.CTE)}
    return sorted({t.name for t in tree.find_all(exp.Table)} - cte_names)
