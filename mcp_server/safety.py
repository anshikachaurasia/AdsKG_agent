"""Safety rules for running SQL written by the AI.

Used by every version, and by the MCP server's run_sql tool.
  - the database is opened READ-ONLY, and with NO ACCESS TO FILES outside it
    (DuckDB can otherwise read any file with SELECT ... FROM read_text('.env') or read_csv(...))
  - exactly ONE statement, and it must be a SELECT (checked with sqlglot, a real SQL parser)
  - it may only read the 28 warehouse tables (no table functions, no other tables)
  - at most 1,000 rows come back
  - a query is stopped after 20 seconds
"""
import threading
from pathlib import Path

import duckdb
import sqlglot
from sqlglot import exp

MAX_ROWS = 1000
TIMEOUT_SECONDS = 20
CARDS_DIR = Path(__file__).resolve().parent.parent / "catalog" / "cards"
KNOWN_TABLES = {p.stem for p in CARDS_DIR.glob("*.yaml")}   # the 28 warehouse tables


def connect(db_path):
    """Open the warehouse read-only, with file access switched off and the settings locked."""
    con = duckdb.connect(str(db_path), read_only=True)
    con.execute("SET enable_external_access = false")   # no read_text / read_csv / glob / COPY on files
    con.execute("SET lock_configuration = true")         # and the query can't switch it back on
    return con


def check_sql(sql):
    """Return '' if the SQL is allowed, otherwise the reason it is blocked."""
    try:
        statements = [s for s in sqlglot.parse(sql, read="duckdb") if s is not None]
    except sqlglot.errors.ParseError as e:
        return f"cannot parse SQL: {e}"
    if len(statements) != 1:
        return "exactly one SQL statement is allowed"
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        return "only SELECT queries are allowed"
    cte_names = {cte.alias for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        if table.name not in KNOWN_TABLES and table.name not in cte_names:
            return f"only the {len(KNOWN_TABLES)} warehouse tables can be read, not '{table.sql(dialect='duckdb')}'"
    return ""


def run_sql(con, sql, max_rows=MAX_ROWS):
    """Run one safe SELECT on a read-only connection. Returns (rows, columns, error)."""
    problem = check_sql(sql)
    if problem:
        return [], [], problem

    timer = threading.Timer(TIMEOUT_SECONDS, con.interrupt)   # stop slow queries
    timer.start()
    try:
        cursor = con.execute(sql)
        columns = [d[0] for d in cursor.description]
        rows = cursor.fetchmany(max_rows)
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
