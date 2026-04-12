"""API contract guarantees — return types, dict completeness, content type overrides."""

import pytest

import ptk
from ptk._base import _serialize
from ptk._types import ContentType

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


class TestAPIContracts:
    @pytest.mark.parametrize("obj", SAMPLE_INPUTS)
    def test_minimize_always_returns_str(self, obj):
        assert isinstance(ptk.minimize(obj), str)

    @pytest.mark.parametrize("obj", SAMPLE_INPUTS)
    def test_stats_always_returns_complete_dict(self, obj):
        s = ptk.stats(obj)
        assert isinstance(s, dict)
        for key in (
            "output",
            "original_len",
            "minimized_len",
            "savings_pct",
            "content_type",
            "original_tokens",
            "minimized_tokens",
        ):
            assert key in s, f"Missing key: {key}"
        assert isinstance(s["output"], str)
        assert isinstance(s["original_len"], int)
        assert isinstance(s["minimized_len"], int)
        assert isinstance(s["savings_pct"], (int, float))
        assert isinstance(s["content_type"], str)
        assert s["original_len"] >= 0
        assert s["minimized_len"] >= 0

    @pytest.mark.parametrize("obj", SAMPLE_INPUTS)
    def test_detect_type_always_returns_valid_string(self, obj):
        assert ptk.detect_type(obj) in {"dict", "list", "code", "log", "diff", "text"}

    @pytest.mark.parametrize("obj", SAMPLE_INPUTS)
    def test_callable_module_matches_minimize(self, obj):
        assert ptk(obj) == ptk.minimize(obj)

    def test_content_type_override_all_types(self):
        for ct in ("dict", "list", "code", "log", "diff", "text"):
            assert isinstance(ptk.minimize("test input", content_type=ct), str)

    def test_content_type_enum_override(self):
        for ct in ContentType:
            assert isinstance(ptk.minimize("test input", content_type=ct), str)

    def test_invalid_content_type_raises(self):
        with pytest.raises(KeyError):
            ptk.minimize("text", content_type="nonexistent")

    def test_aggressive_with_all_types(self):
        for obj in SAMPLE_INPUTS:
            assert isinstance(ptk.minimize(obj, aggressive=True), str)

    def test_stats_savings_pct_non_negative_for_nullish(self):
        s = ptk.stats({"a": 1, "b": None, "c": "", "d": [], "e": {}, "f": "keep"})
        assert s["savings_pct"] >= 0

    def test_version_is_string(self):
        assert isinstance(ptk.__version__, str)
        assert "." in ptk.__version__


class TestSerialize:
    """_serialize must never raise."""

    def test_serialize_string(self):
        assert _serialize("hello") == "hello"

    def test_serialize_dict(self):
        assert _serialize({"a": 1}) == '{"a":1}'

    def test_serialize_list(self):
        assert _serialize([1, 2]) == "[1,2]"

    def test_serialize_tuple(self):
        assert _serialize((1, 2)) == "[1,2]"

    def test_serialize_int(self):
        assert _serialize(42) == "42"

    def test_serialize_none(self):
        assert _serialize(None) == "None"

    def test_serialize_dict_with_non_serializable(self):
        assert isinstance(_serialize({"data": b"bytes"}), str)

    def test_serialize_dict_with_sets(self):
        assert isinstance(_serialize({"tags": {1, 2, 3}}), str)

    def test_serialize_circular_dict(self):
        d: dict = {"a": 1}
        d["self"] = d
        assert isinstance(_serialize(d), str)


class TestContentTypeMismatch:
    """Forcing wrong content_type degrades gracefully, never crashes."""

    def test_dict_as_code(self):
        assert isinstance(ptk.minimize({"a": 1}, content_type="code"), str)

    def test_dict_as_log(self):
        assert isinstance(ptk.minimize({"a": 1}, content_type="log"), str)

    def test_dict_as_diff(self):
        assert isinstance(ptk.minimize({"a": 1}, content_type="diff"), str)

    def test_dict_as_text(self):
        assert isinstance(ptk.minimize({"a": 1}, content_type="text"), str)

    def test_list_as_code(self):
        assert isinstance(ptk.minimize([1, 2, 3], content_type="code"), str)

    def test_code_as_dict(self):
        assert isinstance(ptk.minimize("def foo(): pass", content_type="dict"), str)

    def test_int_as_dict(self):
        assert isinstance(ptk.minimize(42, content_type="dict"), str)

    def test_int_as_list(self):
        assert isinstance(ptk.minimize(42, content_type="list"), str)

    def test_none_as_code(self):
        assert isinstance(ptk.minimize(None, content_type="code"), str)

    def test_none_as_dict(self):
        assert isinstance(ptk.minimize(None, content_type="dict"), str)

    def test_none_as_list(self):
        assert isinstance(ptk.minimize(None, content_type="list"), str)
