"""The agent's result shortening, "did it run its SQL?" and "is this an abstention?" checks."""
import json

from answer_checks import RUN_IT, drop_old_run_it, fit_rows, says_not_sure, unrun_sql


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


def test_long_search_list_stays_valid_json():
    """search_tables / list_lookalikes return a LIST; cut mid-text, tables in it were missed."""
    hits = [{"table": f"table_{i}", "score": 0.5, "description": "x" * 300} for i in range(40)]
    parsed = json.loads(fit_rows(hits))
    assert parsed[-1]["note"].startswith("only the first")
    assert [h["table"] for h in parsed[:-1]] == [f"table_{i}" for i in range(len(parsed) - 1)]


def test_long_description_keeps_table_name():
    """describe_table returns a dict with a long column list; its "table" key must survive."""
    card = {"table": "fact_ad_events", "description": "events",
            "columns": [{"name": f"c{i}", "type": "BIGINT", "meaning": "y" * 80} for i in range(80)]}
    parsed = json.loads(fit_rows(card))
    assert parsed["table"] == "fact_ad_events" and 0 < parsed["columns_shown"] < 80


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


class Msg:
    def __init__(self, content):
        self.content = content


def test_run_it_note_only_for_the_current_question():
    old_turn = [Msg("question 1"), Msg(RUN_IT), Msg("answer 1")]
    this_turn = [Msg("question 2"), Msg(RUN_IT)]
    kept = drop_old_run_it(old_turn + this_turn, question_start=len(old_turn))
    assert [m.content for m in kept] == ["question 1", "answer 1", "question 2", RUN_IT]
