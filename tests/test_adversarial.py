"""Adversarial QA tests for ptk — every possible way to break it.

A senior QA engineer's attempt to crash, corrupt, or confuse ptk.
Every test must either:
  (a) produce a valid string result without raising, OR
  (b) raise a clear, documented exception (not a raw traceback from internals)
"""

import copy
import json
import sys
import os
import re
import threading
import time
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from typing import NamedTuple

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import ptk
from ptk._types import ContentType, detect
from ptk._base import strip_nullish, dedup_lines, _serialize


# ═══════════════════════════════════════════════════════════════════════
# 1. TYPE CHAOS — every Python type that could be passed in
# ═══════════════════════════════════════════════════════════════════════

class TestTypeChaos:
    """Pass every conceivable Python type through ptk.minimize()."""

    def test_none(self):
        result = ptk.minimize(None)
        assert isinstance(result, str)

    def test_bool_true(self):
        result = ptk.minimize(True)
        assert isinstance(result, str)

    def test_bool_false(self):
        result = ptk.minimize(False)
        assert isinstance(result, str)

    def test_int_zero(self):
        result = ptk.minimize(0)
        assert isinstance(result, str)

    def test_int_negative(self):
        result = ptk.minimize(-42)
        assert isinstance(result, str)

    def test_int_huge(self):
        result = ptk.minimize(10**100)
        assert isinstance(result, str)

    def test_float(self):
        result = ptk.minimize(3.14159)
        assert isinstance(result, str)

    def test_float_inf(self):
        result = ptk.minimize(float("inf"))
        assert isinstance(result, str)

    def test_float_neg_inf(self):
        result = ptk.minimize(float("-inf"))
        assert isinstance(result, str)

    def test_float_nan(self):
        result = ptk.minimize(float("nan"))
        assert isinstance(result, str)

    def test_complex(self):
        result = ptk.minimize(complex(1, 2))
        assert isinstance(result, str)

    def test_bytes(self):
        result = ptk.minimize(b"hello bytes")
        assert isinstance(result, str)

    def test_bytearray(self):
        result = ptk.minimize(bytearray(b"hello"))
        assert isinstance(result, str)

    def test_set(self):
        result = ptk.minimize({1, 2, 3})
        assert isinstance(result, str)

    def test_frozenset(self):
        result = ptk.minimize(frozenset({1, 2, 3}))
        assert isinstance(result, str)

    def test_range(self):
        result = ptk.minimize(range(10))
        assert isinstance(result, str)

    def test_tuple(self):
        result = ptk.minimize((1, 2, 3))
        assert isinstance(result, str)

    def test_empty_tuple(self):
        result = ptk.minimize(())
        assert isinstance(result, str)

    def test_generator(self):
        """Generators are consumed — should not crash."""
        gen = (i for i in range(5))
        result = ptk.minimize(gen)
        assert isinstance(result, str)

    def test_lambda(self):
        result = ptk.minimize(lambda x: x)
        assert isinstance(result, str)

    def test_class_type(self):
        result = ptk.minimize(int)
        assert isinstance(result, str)

    def test_module(self):
        import json as j
        result = ptk.minimize(j)
        assert isinstance(result, str)

    def test_exception_object(self):
        result = ptk.minimize(ValueError("test error"))
        assert isinstance(result, str)

    # ── custom objects ──

    def test_custom_class_with_str(self):
        class MyObj:
            def __str__(self):
                return "MyObj(custom)"
        result = ptk.minimize(MyObj())
        assert isinstance(result, str)

    def test_custom_class_without_str(self):
        """Objects with only default __str__ should still work."""
        class Bare:
            pass
        result = ptk.minimize(Bare())
        assert isinstance(result, str)

    def test_custom_class_with_broken_str(self):
        """Object whose __str__ raises should be handled gracefully."""
        class Broken:
            def __str__(self):
                raise RuntimeError("I'm broken")
        # This will propagate — at minimum it shouldn't be a confusing error
        with pytest.raises(RuntimeError, match="I'm broken"):
            ptk.minimize(Broken())

    def test_custom_class_with_repr_only(self):
        class ReprOnly:
            def __repr__(self):
                return "ReprOnly(42)"
        result = ptk.minimize(ReprOnly())
        assert isinstance(result, str)

    def test_dataclass(self):
        @dataclass
        class Point:
            x: int
            y: int
        result = ptk.minimize(Point(1, 2))
        assert isinstance(result, str)

    def test_namedtuple(self):
        class Coord(NamedTuple):
            x: int
            y: int
        result = ptk.minimize(Coord(1, 2))
        assert isinstance(result, str)

    def test_ordered_dict(self):
        d = OrderedDict([("z", 1), ("a", 2)])
        result = ptk.minimize(d)
        parsed = json.loads(result)
        assert parsed["z"] == 1

    def test_defaultdict(self):
        d = defaultdict(list, {"a": [1, 2]})
        result = ptk.minimize(d)
        assert isinstance(result, str)

    # ── dicts with weird keys ──

    def test_dict_with_int_keys(self):
        result = ptk.minimize({1: "a", 2: "b"})
        assert isinstance(result, str)

    def test_dict_with_bool_keys(self):
        result = ptk.minimize({True: "yes", False: "no"})
        assert isinstance(result, str)

    def test_dict_with_none_key(self):
        result = ptk.minimize({None: "value"})
        assert isinstance(result, str)

    def test_dict_with_tuple_key(self):
        """json.dumps will fail on tuple keys — should handle gracefully."""
        result = ptk.minimize({(1, 2): "value"})
        assert isinstance(result, str)

    # ── dicts with weird values ──

    def test_dict_with_bytes_value(self):
        result = ptk.minimize({"data": b"binary"})
        assert isinstance(result, str)

    def test_dict_with_set_value(self):
        result = ptk.minimize({"tags": {"a", "b", "c"}})
        assert isinstance(result, str)

    def test_dict_with_date_value(self):
        from datetime import datetime, date
        result = ptk.minimize({"ts": datetime.now(), "d": date.today()})
        assert isinstance(result, str)

    def test_dict_with_mixed_value_types(self):
        d = {
            "str": "hello",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "list": [1, 2, 3],
            "nested": {"a": 1},
        }
        result = ptk.minimize(d)
        assert isinstance(result, str)

    # ── lists with weird contents ──

    def test_list_of_none(self):
        result = ptk.minimize([None, None, None])
        assert isinstance(result, str)

    def test_list_with_nested_lists(self):
        result = ptk.minimize([[1, 2], [3, 4], [5, 6]])
        assert isinstance(result, str)

    def test_list_with_bytes_items(self):
        result = ptk.minimize([b"a", b"b", b"c"])
        assert isinstance(result, str)

    def test_list_with_sets(self):
        result = ptk.minimize([{1, 2}, {3, 4}])
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════════════
# 2. CIRCULAR REFERENCES & RECURSION BOMBS
# ═══════════════════════════════════════════════════════════════════════

class TestCircularAndDeep:
    """Self-referencing structures and extreme nesting."""

    def test_circular_dict(self):
        """Circular dict reference — json.dumps raises ValueError."""
        d: dict = {"a": 1}
        d["self"] = d
        # Should not crash with a confusing traceback
        result = ptk.minimize(d)
        assert isinstance(result, str)

    def test_circular_list(self):
        """Circular list reference."""
        lst: list = [1, 2, 3]
        lst.append(lst)
        result = ptk.minimize(lst)
        assert isinstance(result, str)

    def test_deeply_nested_dict(self):
        """100 levels deep — tests recursion safety."""
        d: dict = {}
        current = d
        for i in range(100):
            current["child"] = {"level": i}
            current = current["child"]
        result = ptk.minimize(d)
        assert isinstance(result, str)

    def test_deeply_nested_dict_aggressive(self):
        """Aggressive mode on deep dict — flatten + shorten recurse."""
        d: dict = {}
        current = d
        for i in range(100):
            current["child"] = {"level": i}
            current = current["child"]
        result = ptk.minimize(d, aggressive=True)
        assert isinstance(result, str)

    def test_deeply_nested_list(self):
        """100 levels of nested lists."""
        lst: list = [1]
        current = lst
        for _ in range(100):
            inner: list = [1]
            current.append(inner)
            current = inner
        result = ptk.minimize(lst)
        assert isinstance(result, str)

    def test_wide_dict(self):
        """Dict with 10,000 keys."""
        d = {f"key_{i}": i for i in range(10_000)}
        result = ptk.minimize(d)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_wide_list(self):
        """List with 10,000 items."""
        lst = list(range(10_000))
        result = ptk.minimize(lst)
        assert isinstance(result, str)

    def test_kv_format_deeply_nested(self):
        """_to_kv recurses with no depth limit — test it."""
        d: dict = {}
        current = d
        for i in range(200):
            current["child"] = {"level": i}
            current = current["child"]
        result = ptk.minimize(d, format="kv")
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════════════
# 3. EMPTY & BOUNDARY INPUTS
# ═══════════════════════════════════════════════════════════════════════

class TestEmptyAndBoundary:
    """The boring edge cases that always bite in production."""

    def test_empty_string(self):
        assert ptk.minimize("") == ""

    def test_empty_dict(self):
        result = ptk.minimize({})
        assert result == "{}"

    def test_empty_list(self):
        assert ptk.minimize([]) == "[]"

    def test_whitespace_only_string(self):
        result = ptk.minimize("   \n\n\t  \n  ")
        assert isinstance(result, str)

    def test_newlines_only(self):
        result = ptk.minimize("\n\n\n\n\n")
        assert isinstance(result, str)

    def test_single_char(self):
        assert ptk.minimize("x") == "x"

    def test_single_space(self):
        result = ptk.minimize(" ")
        assert isinstance(result, str)

    def test_single_newline(self):
        result = ptk.minimize("\n")
        assert isinstance(result, str)

    def test_dict_with_all_nullish_values(self):
        d = {"a": None, "b": "", "c": [], "d": {}}
        result = ptk.minimize(d)
        assert result == "{}"

    def test_list_of_all_none(self):
        result = ptk.minimize([None, None, None])
        assert result == "[]"

    def test_single_item_dict(self):
        result = ptk.minimize({"a": 1})
        assert json.loads(result) == {"a": 1}

    def test_single_item_list(self):
        result = ptk.minimize([42])
        assert isinstance(result, str)

    def test_single_dict_in_list(self):
        result = ptk.minimize([{"id": 1}])
        assert "[1]" in result

    def test_code_with_only_whitespace(self):
        result = ptk.minimize("   \n   \n   ", content_type="code")
        assert result == ""

    def test_log_with_only_whitespace(self):
        result = ptk.minimize("   \n   ", content_type="log")
        assert result == ""

    def test_diff_with_only_whitespace(self):
        result = ptk.minimize("   \n   ", content_type="diff")
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════════════
# 4. UNICODE, EMOJI, ENCODING EDGE CASES
# ═══════════════════════════════════════════════════════════════════════

class TestUnicode:
    """Encoding edge cases that surface in real-world data."""

    def test_emoji_in_dict_values(self):
        d = {"mood": "😀😂🎉", "name": "Alice"}
        result = ptk.minimize(d)
        parsed = json.loads(result)
        assert "😀" in parsed["mood"]

    def test_emoji_in_keys(self):
        d = {"🔑": "key", "📊": "chart"}
        result = ptk.minimize(d)
        assert isinstance(result, str)

    def test_cjk_characters(self):
        d = {"名前": "太郎", "住所": "東京都渋谷区"}
        result = ptk.minimize(d)
        parsed = json.loads(result)
        assert parsed["名前"] == "太郎"

    def test_arabic_rtl(self):
        text = "مرحبا بالعالم"
        result = ptk.minimize(text, content_type="text")
        assert "مرحبا" in result

    def test_mixed_scripts(self):
        text = "Hello 你好 مرحبا Привет こんにちは"
        result = ptk.minimize(text, content_type="text")
        assert "Hello" in result
        assert "你好" in result

    def test_null_byte_in_string(self):
        text = "hello\x00world"
        result = ptk.minimize(text, content_type="text")
        assert isinstance(result, str)

    def test_null_bytes_in_dict(self):
        d = {"key\x00": "val\x00ue"}
        result = ptk.minimize(d)
        assert isinstance(result, str)

    def test_escape_sequences(self):
        d = {"tab": "a\tb", "newline": "a\nb", "backslash": "a\\b"}
        result = ptk.minimize(d)
        parsed = json.loads(result)
        assert parsed["tab"] == "a\tb"

    def test_surrogate_pairs(self):
        """Supplementary plane characters (emoji, math symbols)."""
        text = "𝕳𝖊𝖑𝖑𝖔 𝕿𝖍𝖊𝖗𝖊"
        result = ptk.minimize(text, content_type="text")
        assert isinstance(result, str)

    def test_combining_characters(self):
        """Characters with combining diacriticals (e.g., é = e + ́)."""
        text = "café résumé naïve"
        result = ptk.minimize(text, content_type="text")
        assert "caf" in result

    def test_very_long_unicode_string(self):
        text = "日本語テスト " * 10_000
        result = ptk.minimize(text, content_type="text")
        assert isinstance(result, str)

    def test_zero_width_characters(self):
        text = "hello\u200bworld\u200b"  # zero-width space
        result = ptk.minimize(text, content_type="text")
        assert isinstance(result, str)

    def test_bom_marker(self):
        text = "\ufeffhello world"  # UTF-8 BOM
        result = ptk.minimize(text, content_type="text")
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════════════
# 5. REGEX SAFETY — ReDoS & special characters
# ═══════════════════════════════════════════════════════════════════════

class TestRegexSafety:
    """Inputs designed to break or slow down regex patterns."""

    def test_many_colons_in_code_line(self):
        """Python sig regex has .*?: which could backtrack on many colons."""
        line = "def f(" + ":".join(f"a{i}: int" for i in range(100)) + "):"
        result = ptk.minimize(line, content_type="code", mode="signatures")
        assert isinstance(result, str)

    def test_unclosed_block_comment(self):
        code = "/* this never closes\nint x = 1;"
        result = ptk.minimize(code, content_type="code")
        assert isinstance(result, str)

    def test_unclosed_triple_quote(self):
        code = '""" this docstring never closes\ndef foo(): pass'
        result = ptk.minimize(code, content_type="code")
        assert isinstance(result, str)

    def test_regex_special_chars_in_code(self):
        code = 'pattern = re.compile(r"^(a+)+$")\ndef foo(): pass'
        result = ptk.minimize(code, content_type="code")
        assert isinstance(result, str)

    def test_lots_of_newlines(self):
        """Blank lines regex: \\n{3,} on 100k newlines."""
        code = "\n" * 100_000
        result = ptk.minimize(code, content_type="code")
        assert isinstance(result, str)

    def test_log_with_no_real_patterns(self):
        """Lots of lines that almost look like logs but aren't."""
        lines = [f"line {i}: some random text with colons" for i in range(1000)]
        text = "\n".join(lines)
        # force log detection
        result = ptk.minimize(text, content_type="log")
        assert isinstance(result, str)

    def test_diff_with_many_plus_lines(self):
        """All + lines, no context."""
        diff = "--- a/f\n+++ b/f\n@@ -0,0 +1,1000 @@\n"
        diff += "\n".join(f"+line {i}" for i in range(1000))
        result = ptk.minimize(diff, content_type="diff")
        assert isinstance(result, str)

    def test_timestamp_regex_on_non_timestamp(self):
        """Strings that look almost like timestamps."""
        log = "9999-99-99T99:99:99Z [ERROR] fake timestamp"
        result = ptk.minimize(log, content_type="log", aggressive=True)
        assert isinstance(result, str)

    def test_code_with_string_containing_comment_markers(self):
        """String literals that contain # or // should not be stripped."""
        code = 'url = "https://example.com/#/path"\ndef foo(): pass'
        result = ptk.minimize(code, content_type="code")
        # The URL is inside a string — ideally preserved, but at minimum no crash
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════════════
# 6. API CONTRACT TESTS — return type & structure guarantees
# ═══════════════════════════════════════════════════════════════════════

class TestAPIContracts:
    """Every public function must fulfill its documented contract."""

    SAMPLE_INPUTS = [
        {"a": 1, "b": None},
        [1, 2, 3],
        "def foo(): pass",
        "[INFO] hello\n[ERROR] world",
        "diff --git a/f b/f\n--- a/f\n+++ b/f\n@@ -1 +1 @@\n-old\n+new",
        "just some plain text here",
        42,
        None,
        "",
    ]

    @pytest.mark.parametrize("obj", SAMPLE_INPUTS)
    def test_minimize_always_returns_str(self, obj):
        result = ptk.minimize(obj)
        assert isinstance(result, str)

    @pytest.mark.parametrize("obj", SAMPLE_INPUTS)
    def test_stats_always_returns_complete_dict(self, obj):
        s = ptk.stats(obj)
        assert isinstance(s, dict)
        # all required keys present
        for key in ("output", "original_len", "minimized_len", "savings_pct",
                     "content_type", "original_tokens", "minimized_tokens"):
            assert key in s, f"Missing key: {key}"
        # type checks
        assert isinstance(s["output"], str)
        assert isinstance(s["original_len"], int)
        assert isinstance(s["minimized_len"], int)
        assert isinstance(s["savings_pct"], (int, float))
        assert isinstance(s["content_type"], str)
        assert s["original_len"] >= 0
        assert s["minimized_len"] >= 0
        assert 0.0 <= s["savings_pct"] <= 100.0 or s["savings_pct"] < 0  # expansion is possible

    @pytest.mark.parametrize("obj", SAMPLE_INPUTS)
    def test_detect_type_always_returns_valid_string(self, obj):
        result = ptk.detect_type(obj)
        assert result in {"dict", "list", "code", "log", "diff", "text"}

    @pytest.mark.parametrize("obj", SAMPLE_INPUTS)
    def test_callable_module_matches_minimize(self, obj):
        assert ptk(obj) == ptk.minimize(obj)

    def test_content_type_override_all_types(self):
        """Force every content type on a plain string — none should crash."""
        for ct in ("dict", "list", "code", "log", "diff", "text"):
            result = ptk.minimize("test input", content_type=ct)
            assert isinstance(result, str)

    def test_content_type_enum_override(self):
        for ct in ContentType:
            result = ptk.minimize("test input", content_type=ct)
            assert isinstance(result, str)

    def test_invalid_content_type_string(self):
        with pytest.raises(KeyError):
            ptk.minimize("text", content_type="nonexistent")

    def test_aggressive_with_all_types(self):
        for obj in self.SAMPLE_INPUTS:
            result = ptk.minimize(obj, aggressive=True)
            assert isinstance(result, str)

    def test_stats_savings_pct_is_reasonable(self):
        """On a real payload, savings should be non-negative."""
        d = {"a": 1, "b": None, "c": "", "d": [], "e": {}, "f": "keep"}
        s = ptk.stats(d)
        assert s["savings_pct"] >= 0

    def test_version_is_string(self):
        assert isinstance(ptk.__version__, str)
        assert "." in ptk.__version__


# ═══════════════════════════════════════════════════════════════════════
# 7. INPUT MUTATION TESTS — ptk must NEVER modify its input
# ═══════════════════════════════════════════════════════════════════════

class TestInputMutation:
    """Verify that ptk never modifies the original input object."""

    def test_dict_not_mutated(self):
        d = {"a": 1, "b": None, "c": {"d": None, "e": 2}, "f": [None, 1]}
        original = copy.deepcopy(d)
        ptk.minimize(d)
        assert d == original

    def test_dict_not_mutated_aggressive(self):
        d = {"configuration": {"environment": "production"}, "description": "test"}
        original = copy.deepcopy(d)
        ptk.minimize(d, aggressive=True)
        assert d == original

    def test_list_not_mutated(self):
        lst = [{"id": 1, "x": None}, {"id": 2}, None, "hello"]
        original = copy.deepcopy(lst)
        ptk.minimize(lst)
        assert lst == original

    def test_nested_dict_not_mutated(self):
        d = {"a": {"b": {"c": None, "d": {"e": ""}}, "f": [None, {"g": None}]}}
        original = copy.deepcopy(d)
        ptk.minimize(d, aggressive=True)
        assert d == original

    def test_stats_does_not_mutate(self):
        d = {"a": 1, "b": None}
        original = copy.deepcopy(d)
        ptk.stats(d)
        assert d == original


# ═══════════════════════════════════════════════════════════════════════
# 8. CONCURRENCY — thread safety of singleton minimizers
# ═══════════════════════════════════════════════════════════════════════

class TestConcurrency:
    """Minimizers are singletons in _ROUTER — verify thread safety."""

    def test_concurrent_minimize_dict(self):
        """10 threads minimizing different dicts simultaneously."""
        results: list[str] = [None] * 10
        errors: list[Exception] = []

        def worker(idx):
            try:
                d = {f"key_{idx}_{j}": j for j in range(50)}
                d["empty"] = None
                results[idx] = ptk.minimize(d)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread errors: {errors}"
        assert all(isinstance(r, str) for r in results)

    def test_concurrent_minimize_mixed_types(self):
        """Threads using different minimizers at the same time."""
        inputs = [
            {"a": 1},
            [1, 2, 3],
            "def foo(): pass",
            "[ERROR] crash",
            "diff --git a/f b/f\n--- a/f\n+++ b/f\n@@ -1 +1 @@\n-a\n+b",
            "just text",
        ]
        results: list[str] = [None] * len(inputs)
        errors: list[Exception] = []

        def worker(idx):
            try:
                results[idx] = ptk.minimize(inputs[idx])
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(len(inputs))]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread errors: {errors}"
        assert all(isinstance(r, str) for r in results)

    def test_concurrent_stats(self):
        """stats() should also be thread-safe."""
        errors: list[Exception] = []

        def worker():
            try:
                for _ in range(20):
                    ptk.stats({"a": 1, "b": None})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors


# ═══════════════════════════════════════════════════════════════════════
# 9. SERIALIZATION EDGE CASES — _serialize specifically
# ═══════════════════════════════════════════════════════════════════════

class TestSerialize:
    """The _serialize function is used for length measurement — it must not crash."""

    def test_serialize_string(self):
        assert _serialize("hello") == "hello"

    def test_serialize_dict(self):
        result = _serialize({"a": 1})
        assert result == '{"a":1}'

    def test_serialize_list(self):
        result = _serialize([1, 2])
        assert result == "[1,2]"

    def test_serialize_tuple(self):
        result = _serialize((1, 2))
        assert result == "[1,2]"

    def test_serialize_int(self):
        assert _serialize(42) == "42"

    def test_serialize_none(self):
        assert _serialize(None) == "None"

    def test_serialize_dict_with_non_serializable_values(self):
        """json.dumps on dict with bytes — should not crash."""
        result = _serialize({"data": b"bytes"})
        assert isinstance(result, str)

    def test_serialize_dict_with_sets(self):
        result = _serialize({"tags": {1, 2, 3}})
        assert isinstance(result, str)

    def test_serialize_circular_dict(self):
        d: dict = {"a": 1}
        d["self"] = d
        result = _serialize(d)
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════════════
# 10. LARGE INPUT PERFORMANCE (no timeouts)
# ═══════════════════════════════════════════════════════════════════════

class TestPerformance:
    """Large inputs must complete in reasonable time (< 5 seconds)."""

    def test_large_json_payload(self):
        """1000 records with 10 fields each."""
        records = [
            {f"field_{j}": f"value_{i}_{j}" for j in range(10)}
            for i in range(1000)
        ]
        records_with_nulls = [
            {**r, "empty1": None, "empty2": "", "empty3": []}
            for r in records
        ]
        start = time.time()
        result = ptk.minimize(records_with_nulls)
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Took {elapsed:.1f}s"
        assert isinstance(result, str)

    def test_large_code_file(self):
        """1000 function defs with docstrings and comments."""
        lines = []
        for i in range(1000):
            lines.append(f"# Function {i}")
            lines.append(f"def func_{i}(x: int, y: int) -> int:")
            lines.append(f'    """Compute something for {i}."""')
            lines.append(f"    return x + y + {i}")
            lines.append("")
        code = "\n".join(lines)
        start = time.time()
        result = ptk.minimize(code, content_type="code")
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Took {elapsed:.1f}s"
        assert isinstance(result, str)

    def test_large_log_file(self):
        """10,000 log lines with lots of repeats."""
        lines = []
        for i in range(10_000):
            level = "DEBUG" if i % 10 != 0 else "ERROR"
            lines.append(f"2024-01-01T00:00:{i:05d}Z [{level}] Message {i % 100}")
        log = "\n".join(lines)
        start = time.time()
        result = ptk.minimize(log, content_type="log")
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Took {elapsed:.1f}s"

    def test_large_diff(self):
        """Diff with 5000 context lines and 10 changes."""
        parts = ["diff --git a/f b/f\n--- a/f\n+++ b/f\n"]
        for hunk in range(10):
            parts.append(f"@@ -{hunk*500},{500} +{hunk*500},{501} @@\n")
            for j in range(500):
                if j == 250:
                    parts.append(f"-old_{hunk}\n+new_{hunk}\n")
                else:
                    parts.append(f" context_{hunk}_{j}\n")
        diff = "".join(parts)
        start = time.time()
        result = ptk.minimize(diff, content_type="diff")
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Took {elapsed:.1f}s"

    def test_large_text_with_abbreviations(self):
        """10,000 word text with lots of abbreviatable words."""
        words = ["implementation", "configuration", "production", "environment",
                 "application", "infrastructure", "authentication", "repository",
                 "documentation", "specification", "requirements", "notifications"]
        text = " ".join(words * 1000)
        start = time.time()
        result = ptk.minimize(text, content_type="text")
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Took {elapsed:.1f}s"


# ═══════════════════════════════════════════════════════════════════════
# 11. IDEMPOTENCY & STABILITY
# ═══════════════════════════════════════════════════════════════════════

class TestIdempotency:
    """Minimizing already-minimized output should be stable."""

    def test_dict_idempotent(self):
        d = {"a": 1, "b": 2}
        first = ptk.minimize(d)
        second = ptk.minimize(json.loads(first))
        assert first == second

    def test_text_idempotent(self):
        text = "The implementation of the configuration is complete."
        first = ptk.minimize(text, content_type="text")
        second = ptk.minimize(first, content_type="text")
        assert first == second

    def test_code_clean_idempotent(self):
        code = "def foo():\n    return 1\n\ndef bar():\n    return 2"
        first = ptk.minimize(code, content_type="code")
        second = ptk.minimize(first, content_type="code")
        assert first == second

    def test_log_idempotent(self):
        log = "[INFO] hello\n[ERROR] world"
        first = ptk.minimize(log, content_type="log")
        second = ptk.minimize(first, content_type="log")
        assert first == second

    def test_minimize_never_expands_dict(self):
        """Minimized output should never be longer than input (for dicts with nulls)."""
        d = {"a": 1, "b": None, "c": "", "d": [None], "e": {}}
        s = ptk.stats(d)
        assert s["minimized_len"] <= s["original_len"]


# ═══════════════════════════════════════════════════════════════════════
# 12. CONTENT TYPE MISMATCHES
# ═══════════════════════════════════════════════════════════════════════

class TestContentTypeMismatch:
    """Forcing wrong content_type should degrade gracefully, not crash."""

    def test_dict_as_code(self):
        result = ptk.minimize({"a": 1}, content_type="code")
        assert isinstance(result, str)

    def test_dict_as_log(self):
        result = ptk.minimize({"a": 1}, content_type="log")
        assert isinstance(result, str)

    def test_dict_as_diff(self):
        result = ptk.minimize({"a": 1}, content_type="diff")
        assert isinstance(result, str)

    def test_dict_as_text(self):
        result = ptk.minimize({"a": 1}, content_type="text")
        assert isinstance(result, str)

    def test_list_as_code(self):
        result = ptk.minimize([1, 2, 3], content_type="code")
        assert isinstance(result, str)

    def test_code_as_dict(self):
        result = ptk.minimize("def foo(): pass", content_type="dict")
        assert isinstance(result, str)

    def test_int_as_dict(self):
        result = ptk.minimize(42, content_type="dict")
        assert isinstance(result, str)

    def test_int_as_list(self):
        result = ptk.minimize(42, content_type="list")
        assert isinstance(result, str)

    def test_none_as_code(self):
        result = ptk.minimize(None, content_type="code")
        assert isinstance(result, str)

    def test_none_as_dict(self):
        result = ptk.minimize(None, content_type="dict")
        assert isinstance(result, str)

    def test_none_as_list(self):
        result = ptk.minimize(None, content_type="list")
        assert isinstance(result, str)
