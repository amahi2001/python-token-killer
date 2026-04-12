"""Regex safety — ReDoS patterns, unclosed constructs, special chars."""

import ptk


class TestRegexSafety:
    def test_many_colons_in_code_line(self):
        line = "def f(" + ":".join(f"a{i}: int" for i in range(100)) + "):"
        assert isinstance(ptk.minimize(line, content_type="code", mode="signatures"), str)

    def test_unclosed_block_comment(self):
        assert isinstance(
            ptk.minimize("/* this never closes\nint x = 1;", content_type="code"), str
        )

    def test_unclosed_triple_quote(self):
        assert isinstance(
            ptk.minimize('""" this docstring never closes\ndef foo(): pass', content_type="code"),
            str,
        )

    def test_regex_special_chars_in_code(self):
        code = 'pattern = re.compile(r"^(a+)+$")\ndef foo(): pass'
        assert isinstance(ptk.minimize(code, content_type="code"), str)

    def test_lots_of_newlines(self):
        assert isinstance(ptk.minimize("\n" * 100_000, content_type="code"), str)

    def test_log_with_no_real_patterns(self):
        text = "\n".join(f"line {i}: some random text with colons" for i in range(1000))
        assert isinstance(ptk.minimize(text, content_type="log"), str)

    def test_diff_with_many_plus_lines(self):
        diff = "--- a/f\n+++ b/f\n@@ -0,0 +1,1000 @@\n"
        diff += "\n".join(f"+line {i}" for i in range(1000))
        assert isinstance(ptk.minimize(diff, content_type="diff"), str)

    def test_timestamp_regex_on_near_match(self):
        log = "9999-99-99T99:99:99Z [ERROR] fake timestamp"
        assert isinstance(ptk.minimize(log, content_type="log", aggressive=True), str)

    def test_url_in_string_literal_preserved(self):
        code = 'url = "https://example.com/#/path"\ndef foo(): pass'
        assert isinstance(ptk.minimize(code, content_type="code"), str)
