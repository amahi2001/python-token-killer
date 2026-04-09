"""Comprehensive tests for ptk — python-token-killer.

Test patterns inspired by claw-compactor's 1600+ test suite, adapted for ptk's
API and minimizer architecture.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import ptk
from ptk._base import MinResult, dedup_lines, strip_nullish
from ptk._types import ContentType, detect

# ═══════════════════════════════════════════════════════════════════════
# Type Detection (inspired by Cortex tests)
# ═══════════════════════════════════════════════════════════════════════


class TestDetection:
    """Content type auto-detection — maps to claw-compactor's Cortex stage."""

    # ── Python ──
    def test_dict(self):
        assert detect({"a": 1}) == ContentType.DICT

    def test_list(self):
        assert detect([1, 2, 3]) == ContentType.LIST

    def test_tuple(self):
        assert detect((1, 2)) == ContentType.LIST

    # ── Code detection (multi-language) ──
    def test_code_python_def(self):
        assert detect("def hello():\n    pass") == ContentType.CODE

    def test_code_python_class(self):
        assert detect("class Foo:\n    pass") == ContentType.CODE

    def test_code_python_import(self):
        assert detect("import os\nimport sys\ndef foo(): pass") == ContentType.CODE

    def test_code_python_shebang(self):
        assert detect("#!/usr/bin/env python3\nimport sys\nprint(sys.argv)") == ContentType.CODE

    def test_code_js_function(self):
        assert detect("function hello() {\n  return 1;\n}") == ContentType.CODE

    def test_code_js_const(self):
        assert detect("const x = 1;\nfunction hello() {}") == ContentType.CODE

    def test_code_js_export(self):
        assert detect("export default function foo() {}") == ContentType.CODE

    def test_code_rust_fn(self):
        assert detect('fn main() {\n    println!("hi");\n}') == ContentType.CODE

    def test_code_go_func(self):
        assert (
            detect('package main\n\nfunc main() {\n\tfmt.Println("hello")\n}') == ContentType.CODE
        )

    def test_code_go_import(self):
        assert detect('package main\nimport "fmt"\nfunc main() {}') == ContentType.CODE

    # ── Log detection ──
    def test_log_bracketed(self):
        assert detect("[INFO] Server started\n[ERROR] Crash") == ContentType.LOG

    def test_log_spaced(self):
        assert detect("2024-01-01 INFO Starting up\n2024-01-01 ERROR Fail") == ContentType.LOG

    def test_log_colon_format(self):
        assert detect("INFO: Starting\nERROR: Failed\nDEBUG: Done") == ContentType.LOG

    def test_log_warning(self):
        assert detect("WARNING: disk full\nCRITICAL: shutdown") == ContentType.LOG

    # ── Diff detection ──
    def test_diff_standard(self):
        diff = "diff --git a/f.py b/f.py\n--- a/f.py\n+++ b/f.py\n@@ -1,3 +1,3 @@\n-old\n+new"
        assert detect(diff) == ContentType.DIFF

    def test_diff_needs_hunk_header(self):
        # --- and +++ without @@ should NOT match as diff
        assert detect("--- some text\n+++ more text") == ContentType.TEXT

    # ── Plain text / fallback ──
    def test_plain_text(self):
        assert detect("Hello world, this is a sentence.") == ContentType.TEXT

    def test_non_string_int(self):
        assert detect(42) == ContentType.TEXT

    def test_non_string_float(self):
        assert detect(3.14) == ContentType.TEXT

    def test_non_string_bool(self):
        assert detect(True) == ContentType.TEXT

    def test_empty_string(self):
        assert detect("") == ContentType.TEXT

    def test_short_ambiguous(self):
        assert detect("hello") == ContentType.TEXT

    def test_detect_type_api(self):
        assert ptk.detect_type({"a": 1}) == "dict"
        assert ptk.detect_type([1]) == "list"
        assert ptk.detect_type("hello world") == "text"


# ═══════════════════════════════════════════════════════════════════════
# Base Helpers
# ═══════════════════════════════════════════════════════════════════════


class TestStripNullish:
    """Recursive nullish value stripping — used by DictMinimizer and ListMinimizer."""

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
    """Consecutive line deduplication — used by LogMinimizer."""

    def test_collapses_duplicates(self):
        text = "ok\nok\nok\ndone"
        assert dedup_lines(text) == "ok (x3)\ndone"

    def test_threshold_not_met(self):
        text = "a\na\nb"
        assert dedup_lines(text, threshold=3) == "a\na\nb"

    def test_single_line(self):
        assert dedup_lines("hello") == "hello"

    def test_empty_string(self):
        assert dedup_lines("") == ""

    def test_no_duplicates(self):
        text = "a\nb\nc\nd"
        assert dedup_lines(text) == text

    def test_multiple_groups(self):
        text = "a\na\na\nb\nb\nc"
        result = dedup_lines(text)
        assert "a (x3)" in result
        assert "b (x2)" in result
        assert "c" in result

    def test_all_same(self):
        text = "x\n" * 100 + "x"
        result = dedup_lines(text)
        assert "(x101)" in result

    def test_empty_lines_dedup(self):
        text = "\n\n\nfoo"
        result = dedup_lines(text)
        assert "(x3)" in result


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
            r.output = "y"


# ═══════════════════════════════════════════════════════════════════════
# DictMinimizer (maps to Ionizer + RLE)
# ═══════════════════════════════════════════════════════════════════════


class TestDictMinimizer:
    """Dict/JSON compression — null stripping, key shortening, formatting."""

    def test_basic_compact_json(self):
        d = {"name": "Alice", "age": 30, "email": None}
        result = ptk.minimize(d)
        parsed = json.loads(result)
        assert "email" not in parsed
        assert parsed["name"] == "Alice"

    def test_nested_null_strip(self):
        d = {"user": {"name": "Bob", "bio": "", "meta": {"x": None}}}
        result = ptk.minimize(d)
        parsed = json.loads(result)
        assert "bio" not in parsed["user"]
        assert "meta" not in parsed["user"]

    def test_deeply_nested_nulls(self):
        d = {"a": {"b": {"c": {"d": None, "e": {"f": None}}, "g": "keep"}}}
        result = ptk.minimize(d)
        parsed = json.loads(result)
        assert parsed["a"]["b"]["g"] == "keep"
        assert "d" not in parsed["a"]["b"].get("c", {})

    def test_preserves_zero_and_false(self):
        d = {"count": 0, "active": False, "name": "test"}
        result = ptk.minimize(d)
        parsed = json.loads(result)
        assert parsed["count"] == 0
        assert parsed["active"] is False

    # ── aggressive mode ──
    def test_aggressive_flattens_single_children(self):
        d = {"config": {"database": {"host": "localhost"}}}
        result = ptk.minimize(d, aggressive=True)
        parsed = json.loads(result)
        assert "cfg.db.host" in parsed

    def test_aggressive_shortens_keys(self):
        d = {"description": "A thing", "timestamp": "2024-01-01"}
        result = ptk.minimize(d, aggressive=True)
        parsed = json.loads(result)
        assert "desc" in parsed
        assert "ts" in parsed

    def test_aggressive_flattens_and_shortens_combined(self):
        d = {"configuration": {"environment": "production"}}
        result = ptk.minimize(d, aggressive=True)
        parsed = json.loads(result)
        assert "cfg.env" in parsed

    def test_aggressive_does_not_flatten_multi_child(self):
        d = {"settings": {"host": "localhost", "port": 8080}}
        result = ptk.minimize(d, aggressive=True)
        parsed = json.loads(result)
        # multi-child dicts should NOT be flattened
        assert "settings" in parsed
        assert parsed["settings"]["host"] == "localhost"

    # ── output formats ──
    def test_kv_format(self):
        d = {"name": "Alice", "age": 30}
        result = ptk.minimize(d, format="kv")
        assert "name:Alice" in result
        assert "age:30" in result

    def test_tabular_format(self):
        d = {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}
        result = ptk.minimize(d, format="tabular")
        assert "users[2]{name,age}:" in result
        assert "Alice,30" in result
        assert "Bob,25" in result

    # ── edge cases ──
    def test_empty_dict(self):
        result = ptk.minimize({})
        assert result == "{}"

    def test_single_key(self):
        result = ptk.minimize({"a": 1})
        assert json.loads(result) == {"a": 1}

    def test_unicode_keys_and_values(self):
        d = {"名前": "太郎", "город": "Москва"}
        result = ptk.minimize(d)
        parsed = json.loads(result)
        assert parsed["名前"] == "太郎"

    def test_large_nested_dict(self):
        """Deep nesting doesn't crash or produce invalid JSON."""
        d = {"level": 0}
        current = d
        for i in range(1, 20):
            current["child"] = {"level": i}
            current = current["child"]
        result = ptk.minimize(d)
        parsed = json.loads(result)
        assert parsed["level"] == 0

    def test_numeric_values_preserved(self):
        d = {"int": 42, "float": 3.14, "neg": -1, "big": 10**18}
        result = ptk.minimize(d)
        parsed = json.loads(result)
        assert parsed["int"] == 42
        assert parsed["float"] == 3.14


# ═══════════════════════════════════════════════════════════════════════
# ListMinimizer (maps to Ionizer array handling)
# ═══════════════════════════════════════════════════════════════════════


class TestListMinimizer:
    """List/array compression — tabular, dedup, sampling."""

    def test_uniform_dicts_tabular(self):
        items = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        result = ptk.minimize(items)
        assert "[2]{id,name}:" in result
        assert "1,A" in result

    def test_dedup_primitives(self):
        items = ["error", "error", "error", "ok"]
        result = ptk.minimize(items)
        assert "error (x3)" in result
        assert "ok" in result

    def test_empty_list(self):
        assert ptk.minimize([]) == "[]"

    def test_single_item_list(self):
        result = ptk.minimize([{"id": 1}])
        assert "[1]{id}:" in result

    # ── sampling (inspired by Ionizer front/back preservation) ──
    def test_sampling_large_list(self):
        items = [{"id": i} for i in range(200)]
        result = ptk.minimize(items, aggressive=True)
        lines = result.strip().split("\n")
        assert len(lines) <= 52  # header + 50 sampled rows

    def test_sampling_preserves_first_and_last(self):
        """Ionizer pattern: front and back items always in output."""
        items = [{"id": i, "name": f"item_{i}"} for i in range(100)]
        result = ptk.minimize(items, aggressive=True)
        assert "0,item_0" in result  # first
        assert "99,item_99" in result  # last

    # ── edge cases from Ionizer tests ──
    def test_null_items_stripped(self):
        items = [None, {"id": 1}, None, {"id": 2}]
        result = ptk.minimize(items)
        assert "None" not in result
        assert "1" in result

    def test_mixed_type_list(self):
        """Mixed types should still produce valid output (not crash)."""
        items = [1, "two", {"three": 3}, [4], True]
        result = ptk.minimize(items)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_string_array_with_duplicates(self):
        """From Ionizer: string array deduplication."""
        items = ["apple", "banana", "apple", "cherry", "banana", "apple", "date"]
        result = ptk.minimize(items)
        assert "apple (x3)" in result
        assert "banana (x2)" in result
        assert "cherry" in result
        assert "date" in result

    def test_large_string_array(self):
        items = [f"log line {i}" for i in range(200)]
        result = ptk.minimize(items)
        assert isinstance(result, str)
        assert len(result) < len(json.dumps(items))

    def test_uniform_dicts_union_fields(self):
        """Tabular output should include union of all keys."""
        items = [{"a": 1, "b": 2}, {"a": 3, "c": 4}]
        result = ptk.minimize(items)
        assert "a" in result
        assert "b" in result
        assert "c" in result

    def test_list_of_tuples(self):
        result = ptk.minimize((1, 2, 3))
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════════════
# CodeMinimizer (maps to Neurosyntax + StructuralCollapse)
# ═══════════════════════════════════════════════════════════════════════


class TestCodeMinimizer:
    """Code compression — comments, docstrings, signatures, pragma preservation."""

    # ── basic comment stripping ──
    def test_strips_python_comments(self):
        code = "# this is a comment\nx = 1  # inline\ny = 2"
        result = ptk.minimize(code, content_type="code")
        assert "# this is a comment" not in result
        assert "# inline" not in result
        assert "x = 1" in result

    def test_strips_block_comments(self):
        code = "/* block */\nint x = 1;"
        result = ptk.minimize(code, content_type="code")
        assert "/* block */" not in result

    def test_strips_js_inline_comments(self):
        code = "// this is a comment\nconst x = 1;"
        result = ptk.minimize(code, content_type="code")
        assert "// this is a comment" not in result
        assert "const x = 1" in result

    # ── pragma preservation (from Neurosyntax tests) ──
    def test_preserves_noqa(self):
        code = "import os  # noqa\ndef bar(): pass"
        result = ptk.minimize(code, content_type="code")
        assert "# noqa" in result

    def test_preserves_type_ignore(self):
        code = "x = foo()  # type: ignore\ndef bar(): pass"
        result = ptk.minimize(code, content_type="code")
        assert "# type: ignore" in result

    def test_preserves_todo(self):
        code = "# TODO: fix this later\ndef foo():\n    pass"
        result = ptk.minimize(code, content_type="code")
        assert "# TODO" in result

    def test_preserves_fixme(self):
        code = "# FIXME: broken\nx = 1"
        result = ptk.minimize(code, content_type="code")
        assert "# FIXME" in result

    def test_preserves_eslint_disable(self):
        code = "// eslint-disable-next-line no-console\nconsole.log('hi');"
        result = ptk.minimize(code, content_type="code")
        assert "eslint-disable" in result

    def test_preserves_eslint_block_comment(self):
        code = "/* eslint-disable */\nconst z = 3;"
        result = ptk.minimize(code, content_type="code")
        assert "eslint-disable" in result

    # ── docstring handling ──
    def test_collapses_docstring_to_first_line(self):
        code = 'def f():\n    """Process items, filtering them.\n\n    This function filters items based on length\n    and applies transformation.\n    """\n    return 42'
        result = ptk.minimize(code, content_type="code")
        assert "Process items" in result
        assert "applies transformation" not in result
        assert "return 42" in result

    def test_strips_empty_docstring(self):
        code = 'def f():\n    """"""\n    return 1'
        result = ptk.minimize(code, content_type="code")
        assert '""""""' not in result

    # ── signatures mode ──
    def test_signatures_mode(self):
        code = (
            "def hello(name: str) -> str:\n"
            "    '''Say hi.'''\n"
            "    return f'hi {name}'\n\n"
            "def goodbye():\n"
            "    pass\n"
        )
        result = ptk.minimize(code, content_type="code", mode="signatures")
        assert "def hello(name: str) -> str:" in result
        assert "def goodbye():" in result
        assert "return" not in result

    def test_signatures_class(self):
        code = "class MyClass:\n    def method(self):\n        pass"
        result = ptk.minimize(code, content_type="code", mode="signatures")
        assert "class MyClass:" in result

    def test_signatures_async_def(self):
        code = "async def fetch_data(url: str) -> dict:\n    pass"
        result = ptk.minimize(code, content_type="code", mode="signatures")
        assert "async def fetch_data" in result

    def test_signatures_rust(self):
        code = "pub async fn handle(req: Request) -> Response {\n    todo!()\n}"
        result = ptk.minimize(code, content_type="code", mode="signatures")
        assert "pub async fn handle" in result

    def test_signatures_go(self):
        code = "func (s *Server) Start(port int) error {\n\treturn nil\n}"
        result = ptk.minimize(code, content_type="code", mode="signatures")
        assert "func (s *Server) Start" in result

    # ── safety guarantees (from Neurosyntax) ──
    def test_string_literals_untouched(self):
        code = 'x = "import os; import sys"\ndef foo(): pass'
        result = ptk.minimize(code, content_type="code")
        assert '"import os; import sys"' in result

    def test_no_identifier_shortening(self):
        code = "def calculate_average_value(data_points):\n    total_sum = sum(data_points)\n    return total_sum"
        result = ptk.minimize(code, content_type="code")
        assert "calculate_average_value" in result
        assert "data_points" in result
        assert "total_sum" in result

    # ── whitespace normalization ──
    def test_collapses_blank_lines(self):
        code = "x = 1\n\n\n\n\ny = 2"
        result = ptk.minimize(code, content_type="code")
        assert "\n\n\n" not in result

    def test_strips_trailing_whitespace(self):
        code = "def foo():   \n    return 1   \n"
        result = ptk.minimize(code, content_type="code")
        for line in result.split("\n"):
            assert line == line.rstrip()

    # ── edge cases ──
    def test_empty_code(self):
        result = ptk.minimize("", content_type="code")
        assert result == ""

    def test_code_only_comments(self):
        code = "# comment 1\n# comment 2\n# comment 3"
        result = ptk.minimize(code, content_type="code")
        assert result == ""

    def test_realistic_python_module(self):
        """Full module test from Neurosyntax real-world samples."""
        code = """# Module-level comment
import os
import sys
from typing import List

# Helper utility
def process_items(items: List[str], max_count: int = 100) -> List[str]:
    \"\"\"Process a list of items, filtering and transforming them.

    This function filters items based on length and applies
    a transformation to each qualifying item.
    \"\"\"
    # filter step
    filtered = [item for item in items if len(item) <= max_count]
    result = []
    for item in filtered:
        # normalise each item
        normalised = item.strip().lower()
        if normalised:  # noqa: SIM102
            result.append(normalised)
    return result
"""
        result = ptk.minimize(code, content_type="code")
        assert "def process_items" in result
        assert "import os" in result
        assert "# noqa" in result
        # pure comments removed
        assert "# Module-level comment" not in result
        assert "# Helper utility" not in result
        assert "# filter step" not in result
        # no triple blank lines
        assert "\n\n\n" not in result


# ═══════════════════════════════════════════════════════════════════════
# LogMinimizer (maps to LogCrunch)
# ═══════════════════════════════════════════════════════════════════════


class TestLogMinimizer:
    """Log compression — dedup, error filtering, stack traces."""

    SAMPLE_LOG = (
        "2024-01-15T10:00:00Z [INFO] Server started on port 8080\n"
        "2024-01-15T10:00:01Z [DEBUG] Checking configuration\n"
        "2024-01-15T10:00:02Z [DEBUG] Checking configuration\n"
        "2024-01-15T10:00:03Z [DEBUG] Checking configuration\n"
        "2024-01-15T10:00:04Z [DEBUG] Checking configuration\n"
        "2024-01-15T10:00:05Z [ERROR] Failed to connect to database\n"
        "2024-01-15T10:00:06Z [INFO] Retrying connection\n"
        "2024-01-15T10:00:07Z [WARN] Disk usage above 80%\n"
        "2024-01-15T10:00:08Z [INFO] Completed health check"
    )

    SAMPLE_TRACEBACK = (
        "ERROR An unexpected error occurred\n"
        "Traceback (most recent call last):\n"
        '  File "/app/server.py", line 42, in handle_request\n'
        "    result = process(data)\n"
        '  File "/app/processor.py", line 17, in process\n'
        "    return transform(item)\n"
        "ValueError: invalid literal for int()\n"
        "INFO Continuing after error"
    )

    def test_dedup_repeated_lines(self):
        log = "[INFO] heartbeat\n" * 10 + "[ERROR] crash"
        result = ptk.minimize(log, content_type="log")
        assert "(x10)" in result
        assert "[ERROR] crash" in result

    def test_errors_only_keeps_error_and_warn(self):
        result = ptk.minimize(self.SAMPLE_LOG, content_type="log", aggressive=True)
        assert "ERROR" in result
        assert "WARN" in result

    def test_strips_timestamps_aggressive(self):
        log = "2024-01-15T12:00:00Z [INFO] hello"
        result = ptk.minimize(log, content_type="log", aggressive=True)
        assert "2024-01-15" not in result

    def test_preserves_timestamps_non_aggressive(self):
        log = "2024-01-15T12:00:00Z [ERROR] fail"
        result = ptk.minimize(log, content_type="log")
        assert "2024-01-15" in result

    # ── stack trace preservation (from LogCrunch) ──
    def test_stack_trace_preserved(self):
        result = ptk.minimize(self.SAMPLE_TRACEBACK, content_type="log", aggressive=True)
        assert "Traceback" in result
        assert "ValueError" in result

    def test_stack_trace_file_lines_preserved(self):
        result = ptk.minimize(self.SAMPLE_TRACEBACK, content_type="log", aggressive=True)
        assert "File" in result

    # ── FATAL treated like ERROR (from LogCrunch) ──
    def test_fatal_preserved(self):
        log = "[INFO] Starting\n[FATAL] Out of memory\n[INFO] Exiting"
        result = ptk.minimize(log, content_type="log", aggressive=True)
        assert "FATAL" in result or "Out of memory" in result

    # ── "failed" keyword preserved (from LogCrunch) ──
    def test_failed_keyword_in_info_preserved(self):
        log = "[INFO] Starting\n[INFO] Connection failed\n[INFO] Done"
        result = ptk.minimize(log, content_type="log", aggressive=True)
        assert "failed" in result.lower()

    # ── edge cases ──
    def test_empty_log(self):
        result = ptk.minimize("", content_type="log")
        assert result == ""

    def test_single_line_log(self):
        result = ptk.minimize("[INFO] Server started", content_type="log")
        assert "[INFO] Server started" in result

    def test_compression_improves_with_repetition(self):
        """From LogCrunch: 50x heartbeat + error + 50x heartbeat."""
        log = "[INFO] Heartbeat OK\n" * 50 + "[ERROR] Service down\n" + "[INFO] Heartbeat OK\n" * 50
        s = ptk.stats(log, content_type="log")
        assert s["minimized_len"] < s["original_len"]

    def test_mixed_levels_no_data_loss_for_errors(self):
        """From LogCrunch: all ERROR and WARN lines must survive."""
        lines = []
        for i in range(5):
            lines.append(f"[ERROR] error_{i}")
        for i in range(30):
            lines.append(f"[DEBUG] filler_{i}")
        for i in range(5):
            lines.append(f"[WARN] warn_{i}")
        log = "\n".join(lines)
        result = ptk.minimize(log, content_type="log", aggressive=True)
        for i in range(5):
            assert f"error_{i}" in result
            assert f"warn_{i}" in result

    def test_errors_only_kwarg(self):
        log = "[INFO] ok\n[ERROR] bad"
        result = ptk.minimize(log, content_type="log", errors_only=True)
        assert "[ERROR] bad" in result


# ═══════════════════════════════════════════════════════════════════════
# DiffMinimizer (maps to DiffCrunch)
# ═══════════════════════════════════════════════════════════════════════


class TestDiffMinimizer:
    """Diff compression — context folding, noise stripping."""

    SAMPLE_DIFF = (
        "diff --git a/f.py b/f.py\n"
        "--- a/f.py\n"
        "+++ b/f.py\n"
        "@@ -1,16 +1,16 @@\n"
        " context1\n"
        " context2\n"
        " context3\n"
        " context4\n"
        " context5\n"
        " context6\n"
        " context7\n"
        " context8\n"
        "-old line\n"
        "+new line\n"
        " context9\n"
        " context10\n"
        " context11\n"
        " context12\n"
    )

    CLAW_DIFF = (
        "diff --git a/src/server.py b/src/server.py\n"
        "index abc1234..def5678 100644\n"
        "--- a/src/server.py\n"
        "+++ b/src/server.py\n"
        "@@ -1,10 +1,12 @@\n"
        " import os\n"
        " import sys\n"
        "-import json\n"
        "+import json  # added comment\n"
        " \n"
        " def start():\n"
        '+    log.info("starting")\n'
        '     host = os.environ.get("HOST", "0.0.0.0")\n'
        '     port = int(os.environ.get("PORT", 8080))\n'
        "     context_line_1 = True\n"
        "     context_line_2 = True\n"
        "     context_line_3 = True\n"
    )

    def test_keeps_added_lines(self):
        result = ptk.minimize(self.CLAW_DIFF, content_type="diff")
        assert "+import json" in result
        assert '+    log.info("starting")' in result

    def test_keeps_removed_lines(self):
        result = ptk.minimize(self.CLAW_DIFF, content_type="diff")
        assert "-import json" in result

    def test_keeps_hunk_header(self):
        result = ptk.minimize(self.SAMPLE_DIFF, content_type="diff")
        assert "@@" in result

    def test_keeps_file_headers(self):
        result = ptk.minimize(self.SAMPLE_DIFF, content_type="diff")
        assert "--- a/f.py" in result
        assert "+++ b/f.py" in result

    def test_folds_large_context(self):
        result = ptk.minimize(self.SAMPLE_DIFF, content_type="diff")
        assert "..." in result  # context lines folded

    def test_aggressive_strips_index_line(self):
        result = ptk.minimize(self.CLAW_DIFF, content_type="diff", aggressive=True)
        assert "index abc1234" not in result

    def test_aggressive_strips_mode_lines(self):
        diff = "diff --git a/f b/f\nold mode 100644\nnew mode 100755\n--- a/f\n+++ b/f\n@@ -1 +1 @@\n-a\n+b"
        result = ptk.minimize(diff, content_type="diff", aggressive=True)
        assert "old mode" not in result

    # ── from DiffCrunch tests ──
    def test_no_newline_indicator_preserved(self):
        diff = "--- a/f\n+++ b/f\n@@ -1 +1 @@\n-a\n+b\n\\ No newline at end of file"
        result = ptk.minimize(diff, content_type="diff")
        assert "No newline" in result

    def test_empty_diff(self):
        result = ptk.minimize("", content_type="diff")
        assert result == ""

    def test_small_diff_not_over_truncated(self):
        """DiffCrunch: 1-2 context lines should be preserved."""
        diff = "--- a/f\n+++ b/f\n@@ -1,3 +1,3 @@\n one\n-two\n+TWO\n three"
        result = ptk.minimize(diff, content_type="diff")
        assert " one" in result
        assert " three" in result

    def test_large_diff_reduces_tokens(self):
        """DiffCrunch: large diffs with lots of context get compressed."""
        context = "\n".join(f" context_{i}" for i in range(40))
        diff = f"--- a/f\n+++ b/f\n@@ -1 +1 @@\n{context}\n+new_feature_line\n{context}"
        s = ptk.stats(diff, content_type="diff")
        assert s["savings_pct"] > 0
        assert "+new_feature_line" in s["output"]


# ═══════════════════════════════════════════════════════════════════════
# TextMinimizer (maps to Abbrev + TokenOpt)
# ═══════════════════════════════════════════════════════════════════════


class TestTextMinimizer:
    """Text compression — phrase abbreviation, word abbreviation, filler removal."""

    LONG_TEXT = (
        "Furthermore, the implementation of the distributed architecture requires "
        "extensive experience in infrastructure management and database configuration. "
        "In addition, the development team should have approximately 5 years of "
        "experience with Kubernetes and continuous integration. "
        "Moreover, the documentation for all applications must be updated regularly. "
        "The production environment is located in the headquarters offices. "
        "Authentication and authorization are handled by the security module. "
        "The repository contains the complete specification and requirements for "
        "the deployment process."
    )

    # ── whitespace normalization ──
    def test_normalizes_spaces(self):
        text = "hello    world"
        result = ptk.minimize(text, content_type="text")
        assert "    " not in result

    def test_normalizes_newlines(self):
        text = "hello\n\n\n\n\ngoodbye"
        result = ptk.minimize(text, content_type="text")
        assert "\n\n\n" not in result

    # ── phrase abbreviation ──
    def test_abbreviates_phrases(self):
        text = "in order to do this, due to the fact that we need it"
        result = ptk.minimize(text, content_type="text")
        assert "in order to" not in result
        assert "to do this" in result

    # ── word abbreviation (from Abbrev tests) ──
    def test_abbreviates_implementation(self):
        result = ptk.minimize("The implementation of config management.", content_type="text")
        assert "impl" in result

    def test_abbreviates_configuration(self):
        result = ptk.minimize("The configuration is complex.", content_type="text")
        assert "config" in result

    def test_abbreviates_production(self):
        result = ptk.minimize("Deploy to production now.", content_type="text")
        assert "prod" in result

    def test_abbreviates_infrastructure(self):
        result = ptk.minimize("The infrastructure needs updates.", content_type="text")
        assert "infra" in result

    def test_preserves_case_on_abbreviation(self):
        result = ptk.minimize("Implementation is key.", content_type="text")
        assert "Impl" in result  # capital preserved

    # ── filler phrase removal (from Abbrev tests) ──
    def test_removes_furthermore(self):
        text = "Furthermore, the system works well."
        result = ptk.minimize(text, content_type="text")
        assert "Furthermore," not in result

    def test_removes_in_addition(self):
        text = "In addition, it scales."
        result = ptk.minimize(text, content_type="text")
        assert "In addition," not in result

    def test_removes_moreover(self):
        text = "Moreover, the team is ready."
        result = ptk.minimize(text, content_type="text")
        assert "Moreover," not in result

    def test_removes_additionally(self):
        text = "Additionally, we need backups."
        result = ptk.minimize(text, content_type="text")
        assert "Additionally," not in result

    # ── verbose text gets shorter ──
    def test_long_text_gets_compressed(self):
        s = ptk.stats(self.LONG_TEXT, content_type="text")
        assert s["savings_pct"] > 0

    # ── aggressive stopword removal ──
    def test_aggressive_removes_stopwords(self):
        text = "the quick brown fox is very fast and also quite nimble"
        result = ptk.minimize(text, content_type="text", aggressive=True)
        assert "the" not in result.split()
        assert "very" not in result.split()
        assert "quick" in result
        assert "brown" in result
        assert "fox" in result

    # ── edge cases ──
    def test_empty_text(self):
        result = ptk.minimize("", content_type="text")
        assert result == ""

    def test_unicode_preserved(self):
        text = "中文内容 English content 日本語"
        result = ptk.minimize(text, content_type="text")
        assert "中文" in result
        assert "English" in result

    def test_does_not_abbreviate_code(self):
        """Abbrev should only fire on text, not code strings."""
        code = "def implementation(): pass"
        result = ptk.minimize(code, content_type="code")
        # CodeMinimizer should NOT do word abbreviation
        assert "implementation" in result


# ═══════════════════════════════════════════════════════════════════════
# Top-Level API
# ═══════════════════════════════════════════════════════════════════════


class TestAPI:
    def test_minimize_returns_string(self):
        assert isinstance(ptk.minimize({"a": 1}), str)

    def test_callable_module(self):
        result = ptk({"a": 1})
        assert isinstance(result, str)
        assert "a" in result

    def test_stats_returns_full_dict(self):
        s = ptk.stats({"name": "Alice", "bio": None, "notes": ""})
        assert s["savings_pct"] > 0
        assert s["content_type"] == "dict"
        assert "output" in s
        assert isinstance(s["original_len"], int)
        assert isinstance(s["minimized_len"], int)
        assert "original_tokens" in s
        assert "minimized_tokens" in s

    def test_stats_token_counts_are_non_negative(self):
        s = ptk.stats({"a": 1})
        assert s["original_tokens"] >= 0
        assert s["minimized_tokens"] >= 0

    def test_content_type_override_string(self):
        result = ptk.minimize("some text", content_type="text")
        assert isinstance(result, str)

    def test_content_type_override_enum(self):
        result = ptk.minimize("some text", content_type=ContentType.TEXT)
        assert isinstance(result, str)

    def test_invalid_content_type_raises(self):
        with pytest.raises(KeyError):
            ptk.minimize("text", content_type="nonexistent")

    def test_version(self):
        assert ptk.__version__ == "0.1.0"

    # ── real-world integration tests ──
    def test_real_world_api_response(self):
        response = {
            "data": {
                "users": [
                    {
                        "id": 1,
                        "name": "Alice",
                        "email": "a@b.com",
                        "bio": None,
                        "avatar_url": "",
                        "metadata": {},
                        "settings": {"theme": "dark", "notifications": None},
                    },
                    {
                        "id": 2,
                        "name": "Bob",
                        "email": "b@b.com",
                        "bio": "",
                        "avatar_url": None,
                        "metadata": {},
                        "settings": {"theme": "light", "notifications": ""},
                    },
                ]
            },
            "meta": {"page": 1, "total": 2, "next_cursor": None},
            "errors": None,
        }
        result = ptk.minimize(response)
        parsed = json.loads(result)
        assert "errors" not in parsed
        assert "bio" not in parsed["data"]["users"][0]
        assert parsed["data"]["users"][0]["name"] == "Alice"

    def test_real_world_aggressive(self):
        payload = {
            "description": "User management endpoint",
            "timestamp": "2024-01-01T00:00:00Z",
            "configuration": {"environment": "production"},
        }
        result = ptk.minimize(payload, aggressive=True)
        parsed = json.loads(result)
        assert "desc" in parsed
        assert "ts" in parsed
        assert "cfg.env" in parsed

    def test_non_string_non_dict_non_list(self):
        """Objects with __str__ should be handled gracefully."""
        result = ptk.minimize(42)
        assert isinstance(result, str)

    def test_minimize_is_idempotent_for_dicts(self):
        """Minimizing already-minimal JSON should be stable."""
        d = {"a": 1, "b": 2}
        first = ptk.minimize(d)
        second = ptk.minimize(json.loads(first))
        assert first == second
