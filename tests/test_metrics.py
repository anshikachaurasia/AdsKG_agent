"""Execution accuracy: the predicted result must contain the gold result."""
from metrics import results_match, table_scores


def test_same_result():
    assert results_match([(1, 0.5)], [(1, 0.5)])


def test_row_order_and_rounding_ignored():
    assert results_match([(1, 0.123456)], [(1.0, 0.1234561)])
    assert results_match([(1,), (2,)], [(2,), (1,)])


def test_extra_columns_allowed_but_all_gold_columns_needed():
    assert results_match([(0.5,)], [("campaign 7", 0.5)])
    assert not results_match([(7, 0.5)], [(0.5,)])


def test_wrong_value_or_row_count():
    assert not results_match([(1, 0.5)], [(1, 0.6)])
    assert not results_match([(1,)], [(1,), (2,)])
    assert not results_match([], [])


def test_two_columns_with_the_same_values_backtracks():
    """Columns 0 and 1 both hold {1, 2}; only column 1 lines up with the gold rows. A greedy match took column 0."""
    gold = [(1, "a"), (2, "b")]
    pred = [(2, 1, "a"), (1, 2, "b")]
    assert results_match(gold, pred)


def test_table_scores():
    assert table_scores(["a", "b"], ["a"]) == (0.5, 1.0, 0.667)
