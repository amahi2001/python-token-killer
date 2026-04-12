"""Public API tests — minimize(), stats(), ptk(), detect_type()."""

import pytest

import ptk
from ptk._types import ContentType


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
        for key in (
            "output",
            "original_len",
            "minimized_len",
            "original_tokens",
            "minimized_tokens",
        ):
            assert key in s

    def test_stats_token_counts_are_non_negative(self):
        s = ptk.stats({"a": 1})
        assert s["original_tokens"] >= 0
        assert s["minimized_tokens"] >= 0

    def test_content_type_override_string(self):
        assert isinstance(ptk.minimize("some text", content_type="text"), str)

    def test_content_type_override_enum(self):
        assert isinstance(ptk.minimize("some text", content_type=ContentType.TEXT), str)

    def test_invalid_content_type_raises(self):
        with pytest.raises(KeyError):
            ptk.minimize("text", content_type="nonexistent")

    def test_version(self):
        assert ptk.__version__ == "0.1.1"

    def test_non_string_non_dict_non_list(self):
        assert isinstance(ptk.minimize(42), str)
