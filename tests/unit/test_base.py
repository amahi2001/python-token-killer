"""Tests for _base.py — strip_nullish, dedup_lines, MinResult."""

import pytest

from ptk._base import MinResult, dedup_lines, strip_nullish


class TestStripNullish:
    """Recursive nullish value stripping."""

    def test_removes_none(self):
        assert strip_nullish({"a": 1, "b": None}) == {"a": 1}

    def test_removes_empty_string(self):
        assert strip_nullish({"a": "hi", "b": ""}) == {"a": "hi"}

    def test_removes_empty_list(self):
        assert strip_nullish({"a": 1, "b": []}) == {"a": 1}

    def test_removes_empty_dict(self):
        assert strip_nullish({"a": 1, "b": {}}) == {"a": 1}

    def test_recursive_nested_dict(self):
        assert strip_nullish({"a": {"b": None, "c": 1}}) == {"a": {"c": 1}}

    def test_removes_fully_empty_nested_dict(self):
        assert strip_nullish({"a": {"b": None}}) == {}

    def test_recursive_list_of_dicts(self):
        result = strip_nullish({"items": [{"a": 1, "b": None}, {"c": "", "d": 2}]})
        assert result == {"items": [{"a": 1}, {"d": 2}]}

    def test_preserves_zero(self):
        assert strip_nullish({"a": 0}) == {"a": 0}

    def test_preserves_false(self):
        assert strip_nullish({"a": False}) == {"a": False}

    def test_preserves_nonempty_list(self):
        assert strip_nullish({"a": [1, 2]}) == {"a": [1, 2]}

    def test_deeply_nested(self):
        d = {"a": {"b": {"c": {"d": None, "e": "val"}}}}
        assert strip_nullish(d) == {"a": {"b": {"c": {"e": "val"}}}}

    def test_empty_input(self):
        assert strip_nullish({}) == {}

    def test_all_nullish(self):
        assert strip_nullish({"a": None, "b": "", "c": [], "d": {}}) == {}


class TestDedupLines:
    """Consecutive line deduplication."""

    def test_collapses_duplicates(self):
        assert dedup_lines("ok\nok\nok\ndone") == "ok (x3)\ndone"

    def test_threshold_not_met(self):
        assert dedup_lines("a\na\nb", threshold=3) == "a\na\nb"

    def test_single_line(self):
        assert dedup_lines("hello") == "hello"

    def test_empty_string(self):
        assert dedup_lines("") == ""

    def test_no_duplicates(self):
        text = "a\nb\nc\nd"
        assert dedup_lines(text) == text

    def test_multiple_groups(self):
        result = dedup_lines("a\na\na\nb\nb\nc")
        assert "a (x3)" in result
        assert "b (x2)" in result
        assert "c" in result

    def test_all_same(self):
        result = dedup_lines("x\n" * 100 + "x")
        assert "(x101)" in result

    def test_empty_lines_dedup(self):
        assert "(x3)" in dedup_lines("\n\n\nfoo")


class TestMinResult:
    def test_savings_pct(self):
        r = MinResult(output="x", original_len=100, minimized_len=30)
        assert r.savings_pct == 70.0

    def test_zero_original(self):
        r = MinResult(output="", original_len=0, minimized_len=0)
        assert r.savings_pct == 0.0

    def test_frozen(self):
        r = MinResult(output="x", original_len=10, minimized_len=5)
        with pytest.raises(AttributeError):
            r.output = "y"  # type: ignore[misc]
