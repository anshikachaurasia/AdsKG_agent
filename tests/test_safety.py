"""The SQL safety layer: only one SELECT, only warehouse tables, no file access, at most 1,000 rows."""
import duckdb
import pytest

from safety import MAX_ROWS, check_sql, connect, run_sql, tables_in_sql


@pytest.fixture
def con(tmp_path):
    """A tiny read-only warehouse with one real table name (dim_ad) holding 1,500 rows."""
    path = tmp_path / "tiny.duckdb"
    build = duckdb.connect(str(path))
    build.execute("CREATE TABLE dim_ad AS SELECT range AS ad_id, range % 7 AS campaign_id FROM range(1500)")
    build.execute("CREATE TABLE raw_sample AS SELECT 1 AS x")      # exists, but is not a warehouse table
    build.close()
    (tmp_path / "secret.txt").write_text("OPENAI_API_KEY=sk-test")
    return connect(path), tmp_path / "secret.txt"


def test_plain_select_runs(con):
    c, _ = con
    rows, columns, error = run_sql(c, "SELECT campaign_id, count(*) AS n FROM dim_ad GROUP BY 1 ORDER BY 1")
    assert error == "" and columns == ["campaign_id", "n"] and len(rows) == 7


@pytest.mark.parametrize("sql", [
    "DROP TABLE dim_ad",
    "DELETE FROM dim_ad",
    "SELECT 1; DROP TABLE dim_ad",
    "INSERT INTO dim_ad VALUES (1, 1)",
    "COPY dim_ad TO 'out.csv'",
    "SET enable_external_access = true",
])
def test_writes_and_settings_are_blocked(sql):
    assert check_sql(sql) != ""


@pytest.mark.parametrize("template", [
    "SELECT * FROM read_text('{f}')",
    "SELECT * FROM read_csv('{f}')",
    "SELECT * FROM glob('*')",
    "SELECT * FROM dim_ad WHERE ad_id IN (SELECT 1 FROM read_text('{f}'))",
    "WITH s AS (SELECT * FROM read_text('{f}')) SELECT * FROM s",
])
def test_file_reads_are_blocked(con, template):
    c, secret = con
    rows, _, error = run_sql(c, template.format(f=secret))
    assert error and rows == []


def test_connection_itself_refuses_file_reads(con):
    """Defence in depth: even SQL that skips check_sql cannot read files, or switch file access back on."""
    c, secret = con
    with pytest.raises(duckdb.Error):
        c.execute(f"SELECT * FROM read_text('{secret}')").fetchall()
    with pytest.raises(duckdb.Error):
        c.execute("SET enable_external_access = true")


def test_only_warehouse_tables(con):
    c, _ = con
    assert "warehouse tables" in run_sql(c, "SELECT * FROM raw_sample")[2]
    assert check_sql("WITH t AS (SELECT * FROM dim_ad) SELECT count(*) FROM t") == ""   # CTE names are fine


def test_row_limit_and_one_extra_row_for_truncation(con):
    c, _ = con
    assert len(run_sql(c, "SELECT * FROM dim_ad")[0]) == MAX_ROWS
    assert len(run_sql(c, "SELECT * FROM dim_ad", max_rows=MAX_ROWS + 1)[0]) == MAX_ROWS + 1   # 1,500 > 1,000: cut
    assert len(run_sql(c, "SELECT * FROM dim_ad LIMIT 1000", max_rows=MAX_ROWS + 1)[0]) == MAX_ROWS  # exactly 1,000: not cut


def test_tables_in_sql_skips_cte_names():
    assert tables_in_sql("WITH t AS (SELECT * FROM dim_ad) SELECT * FROM t JOIN dim_user USING (user_id)") == \
        ["dim_ad", "dim_user"]
