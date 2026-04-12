"""Edge cases — empty inputs, deep nesting, circular refs, unicode, encoding."""

import json

import ptk


class TestCircularAndDeep:
    def test_circular_dict(self):
        d: dict = {"a": 1}
        d["self"] = d
        assert isinstance(ptk.minimize(d), str)

    def test_circular_list(self):
        lst: list = [1, 2, 3]
        lst.append(lst)
        assert isinstance(ptk.minimize(lst), str)

    def test_deeply_nested_dict(self):
        d: dict = {}
        current = d
        for i in range(100):
            current["child"] = {"level": i}
            current = current["child"]
        assert isinstance(ptk.minimize(d), str)

    def test_deeply_nested_dict_aggressive(self):
        d: dict = {}
        current = d
        for i in range(100):
            current["child"] = {"level": i}
            current = current["child"]
        assert isinstance(ptk.minimize(d, aggressive=True), str)

    def test_deeply_nested_list(self):
        lst: list = [1]
        current = lst
        for _ in range(100):
            inner: list = [1]
            current.append(inner)
            current = inner
        assert isinstance(ptk.minimize(lst), str)

    def test_wide_dict(self):
        d = {f"key_{i}": i for i in range(10_000)}
        result = ptk.minimize(d)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_wide_list(self):
        assert isinstance(ptk.minimize(list(range(10_000))), str)

    def test_kv_format_deeply_nested(self):
        d: dict = {}
        current = d
        for i in range(200):
            current["child"] = {"level": i}
            current = current["child"]
        assert isinstance(ptk.minimize(d, format="kv"), str)


class TestEmptyAndBoundary:
    def test_empty_string(self):
        assert ptk.minimize("") == ""

    def test_empty_dict(self):
        assert ptk.minimize({}) == "{}"

    def test_empty_list(self):
        assert ptk.minimize([]) == "[]"

    def test_whitespace_only_string(self):
        assert isinstance(ptk.minimize("   \n\n\t  "), str)

    def test_newlines_only(self):
        assert isinstance(ptk.minimize("\n\n\n\n\n"), str)

    def test_single_char(self):
        assert ptk.minimize("x") == "x"

    def test_single_space(self):
        assert isinstance(ptk.minimize(" "), str)

    def test_single_newline(self):
        assert isinstance(ptk.minimize("\n"), str)

    def test_dict_all_nullish(self):
        assert ptk.minimize({"a": None, "b": "", "c": [], "d": {}}) == "{}"

    def test_list_of_all_none(self):
        assert ptk.minimize([None, None, None]) == "[]"

    def test_single_item_dict(self):
        assert json.loads(ptk.minimize({"a": 1})) == {"a": 1}

    def test_single_item_list(self):
        assert isinstance(ptk.minimize([42]), str)

    def test_single_dict_in_list(self):
        assert "[1]" in ptk.minimize([{"id": 1}])

    def test_code_whitespace_only(self):
        assert ptk.minimize("   \n   \n   ", content_type="code") == ""

    def test_log_whitespace_only(self):
        assert ptk.minimize("   \n   ", content_type="log") == ""

    def test_diff_whitespace_only(self):
        assert isinstance(ptk.minimize("   \n   ", content_type="diff"), str)


class TestUnicode:
    def test_emoji_in_dict_values(self):
        assert "😀" in json.loads(ptk.minimize({"mood": "😀😂🎉"}))["mood"]

    def test_emoji_in_keys(self):
        assert isinstance(ptk.minimize({"🔑": "key"}), str)

    def test_cjk_characters(self):
        assert json.loads(ptk.minimize({"名前": "太郎"}))["名前"] == "太郎"

    def test_arabic_rtl(self):
        assert "مرحبا" in ptk.minimize("مرحبا بالعالم", content_type="text")

    def test_mixed_scripts(self):
        result = ptk.minimize("Hello 你好 مرحبا Привет", content_type="text")
        assert "Hello" in result
        assert "你好" in result

    def test_null_byte_in_string(self):
        assert isinstance(ptk.minimize("hello\x00world", content_type="text"), str)

    def test_escape_sequences(self):
        d = {"tab": "a\tb", "newline": "a\nb", "backslash": "a\\b"}
        assert json.loads(ptk.minimize(d))["tab"] == "a\tb"

    def test_surrogate_pairs(self):
        assert isinstance(ptk.minimize("𝕳𝖊𝖑𝖑𝖔 𝕿𝖍𝖊𝖗𝖊", content_type="text"), str)

    def test_combining_characters(self):
        assert "caf" in ptk.minimize("café résumé naïve", content_type="text")

    def test_very_long_unicode_string(self):
        assert isinstance(ptk.minimize("日本語テスト " * 10_000, content_type="text"), str)

    def test_zero_width_characters(self):
        assert isinstance(ptk.minimize("hello\u200bworld\u200b", content_type="text"), str)

    def test_bom_marker(self):
        assert isinstance(ptk.minimize("\ufeffhello world", content_type="text"), str)
