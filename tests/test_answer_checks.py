"""The agent's result shortening, "did it run its SQL?" and "is this an abstention?" checks."""
import json

from answer_checks import fit_rows, says_not_sure, unrun_sql


def test_short_result_unchanged():
    data = {"columns": ["n"], "rows": [["1"]], "row_count": 1, "error": ""}
    assert json.loads(fit_rows(data)) == data


def test_long_result_loses_rows_not_json():
    rows = [[f"2017-05-{d:02d}", str(d * 1000), "0.0512345678"] for d in range(1, 13)] * 30
    data = {"columns": ["day", "clicks", "ctr"], "rows": rows, "row_count": len(rows), "error": ""}
    text = fit_rows(data)
    parsed = json.loads(text)                  # still valid JSON: the query is not counted as a failed run
    assert len(text) <= 4000
    assert parsed["error"] == "" and parsed["row_count"] == len(rows)
    assert 0 < parsed["rows_shown"] < len(rows) and parsed["rows"] == rows[:parsed["rows_shown"]]


def test_error_text_passes_through():
    assert fit_rows("unknown table 'x'") == "unknown table 'x'"


def test_unrun_sql():
    ran = ["SELECT sum(clicks) FROM agg_campaign_daily WHERE campaign_id = 1"]
    shown = "Total clicks = 42.\n```sql\nselect SUM(clicks)\nfrom agg_campaign_daily where campaign_id = 1;\n```"
    assert not unrun_sql(shown, ran)                        # same query, different spacing/case/semicolon
    assert unrun_sql("Total = the result of this query\n```sql\nSELECT 1 FROM dim_ad\n```", ran)
    assert unrun_sql("```sql\nSELECT 1 FROM dim_ad\n```", [])
    assert not unrun_sql("No SQL here, just words.", [])


def test_says_not_sure():
    assert says_not_sure("Not sure: there is no table with advertiser names.")
    assert says_not_sure("**I'm not sure** which week you mean.")
    assert not says_not_sure("CTR was 0.031. Caveat: I'm not sure the profile data is complete.")
