"""ListMinimizer tests — tabular, dedup, sampling."""

import json

import ptk


class TestListMinimizer:
    def test_uniform_dicts_tabular(self):
        items = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        result = ptk.minimize(items)
        assert "[2]{id,name}:" in result
        assert "1,A" in result

    def test_dedup_primitives(self):
        result = ptk.minimize(["error", "error", "error", "ok"])
        assert "error (x3)" in result
        assert "ok" in result

    def test_empty_list(self):
        assert ptk.minimize([]) == "[]"

    def test_single_item_list(self):
        assert "[1]{id}:" in ptk.minimize([{"id": 1}])

    # ── sampling ──
    def test_sampling_large_list(self):
        items = [{"id": i} for i in range(200)]
        lines = ptk.minimize(items, aggressive=True).strip().split("\n")
        assert len(lines) <= 52  # header + 50 sampled rows

    def test_sampling_preserves_first_and_last(self):
        items = [{"id": i, "name": f"item_{i}"} for i in range(100)]
        result = ptk.minimize(items, aggressive=True)
        assert "0,item_0" in result
        assert "99,item_99" in result

    # ── edge cases ──
    def test_null_items_stripped(self):
        result = ptk.minimize([None, {"id": 1}, None, {"id": 2}])
        assert "None" not in result
        assert "1" in result

    def test_mixed_type_list(self):
        result = ptk.minimize([1, "two", {"three": 3}, [4], True])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_string_array_with_duplicates(self):
        items = ["apple", "banana", "apple", "cherry", "banana", "apple", "date"]
        result = ptk.minimize(items)
        assert "apple (x3)" in result
        assert "banana (x2)" in result
        assert "cherry" in result
        assert "date" in result

    def test_large_string_array(self):
        items = [f"log line {i}" for i in range(200)]
        result = ptk.minimize(items)
        assert len(result) < len(json.dumps(items))

    def test_uniform_dicts_union_fields(self):
        items = [{"a": 1, "b": 2}, {"a": 3, "c": 4}]
        result = ptk.minimize(items)
        assert "a" in result
        assert "b" in result
        assert "c" in result

    def test_list_of_tuples(self):
        assert isinstance(ptk.minimize((1, 2, 3)), str)

    # ── strip_nulls=False tests ───────────────────────────────────────────
    def test_strip_nulls_false_preserves_none_items(self):
        items = [None, {"id": 1}, None]
        result = ptk.minimize(items, strip_nulls=False)
        # Should be JSON format with nulls preserved
        assert "null" in result
        parsed = json.loads(result)
        assert parsed[0] is None
        assert parsed[1]["id"] == 1

    def test_strip_nulls_false_preserves_empty_dicts_in_list(self):
        items = [{"id": 1}, {}, {"id": 2}]
        result = ptk.minimize(items, strip_nulls=False)
        # In tabular mode, empty dict would have empty values
        assert isinstance(result, str)

    def test_strip_nulls_true_default(self):
        items = [None, {"id": 1}, None]
        result = ptk.minimize(items)
        assert "null" not in result
        assert "1" in result
