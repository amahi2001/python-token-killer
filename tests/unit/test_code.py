"""CodeMinimizer tests — comments, docstrings, signatures, pragma preservation."""

import ptk


class TestCodeMinimizer:
    # ── comment stripping ──
    def test_strips_python_comments(self):
        code = "# this is a comment\nx = 1  # inline\ny = 2"
        result = ptk.minimize(code, content_type="code")
        assert "# this is a comment" not in result
        assert "# inline" not in result
        assert "x = 1" in result

    def test_strips_block_comments(self):
        code = "/* block */\nint x = 1;"
        assert "/* block */" not in ptk.minimize(code, content_type="code")

    def test_strips_js_inline_comments(self):
        code = "// this is a comment\nconst x = 1;"
        result = ptk.minimize(code, content_type="code")
        assert "// this is a comment" not in result
        assert "const x = 1" in result

    # ── pragma preservation ──
    def test_preserves_noqa(self):
        code = "import os  # noqa\ndef bar(): pass"
        assert "# noqa" in ptk.minimize(code, content_type="code")

    def test_preserves_type_ignore(self):
        code = "x = foo()  # type: ignore\ndef bar(): pass"
        assert "# type: ignore" in ptk.minimize(code, content_type="code")

    def test_preserves_todo(self):
        code = "# TODO: fix this later\ndef foo():\n    pass"
        assert "# TODO" in ptk.minimize(code, content_type="code")

    def test_preserves_fixme(self):
        code = "# FIXME: broken\nx = 1"
        assert "# FIXME" in ptk.minimize(code, content_type="code")

    def test_preserves_eslint_disable(self):
        code = "// eslint-disable-next-line no-console\nconsole.log('hi');"
        assert "eslint-disable" in ptk.minimize(code, content_type="code")

    def test_preserves_eslint_block_comment(self):
        code = "/* eslint-disable */\nconst z = 3;"
        assert "eslint-disable" in ptk.minimize(code, content_type="code")

    # ── docstrings ──
    def test_collapses_docstring_to_first_line(self):
        code = (
            'def f():\n    """Process items, filtering them.\n\n'
            "    This function filters items based on length\n"
            '    and applies transformation.\n    """\n    return 42'
        )
        result = ptk.minimize(code, content_type="code")
        assert "Process items" in result
        assert "applies transformation" not in result
        assert "return 42" in result

    def test_strips_empty_docstring(self):
        code = 'def f():\n    """"""\n    return 1'
        assert '""""""' not in ptk.minimize(code, content_type="code")

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
        assert "class MyClass:" in ptk.minimize(code, content_type="code", mode="signatures")

    def test_signatures_async_def(self):
        code = "async def fetch_data(url: str) -> dict:\n    pass"
        assert "async def fetch_data" in ptk.minimize(code, content_type="code", mode="signatures")

    def test_signatures_rust(self):
        code = "pub async fn handle(req: Request) -> Response {\n    todo!()\n}"
        assert "pub async fn handle" in ptk.minimize(code, content_type="code", mode="signatures")

    def test_signatures_go(self):
        code = "func (s *Server) Start(port int) error {\n\treturn nil\n}"
        assert "func (s *Server) Start" in ptk.minimize(
            code, content_type="code", mode="signatures"
        )

    # ── safety guarantees ──
    def test_string_literals_untouched(self):
        code = 'x = "import os; import sys"\ndef foo(): pass'
        assert '"import os; import sys"' in ptk.minimize(code, content_type="code")

    def test_no_identifier_shortening(self):
        code = "def calculate_average_value(data_points):\n    total_sum = sum(data_points)\n    return total_sum"
        result = ptk.minimize(code, content_type="code")
        assert "calculate_average_value" in result
        assert "data_points" in result
        assert "total_sum" in result

    # ── whitespace normalization ──
    def test_collapses_blank_lines(self):
        code = "x = 1\n\n\n\n\ny = 2"
        assert "\n\n\n" not in ptk.minimize(code, content_type="code")

    def test_strips_trailing_whitespace(self):
        code = "def foo():   \n    return 1   \n"
        result = ptk.minimize(code, content_type="code")
        for line in result.split("\n"):
            assert line == line.rstrip()

    # ── edge cases ──
    def test_empty_code(self):
        assert ptk.minimize("", content_type="code") == ""

    def test_code_only_comments(self):
        assert ptk.minimize("# a\n# b\n# c", content_type="code") == ""

    def test_realistic_python_module(self):
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
        assert "# Module-level comment" not in result
        assert "# filter step" not in result
        assert "\n\n\n" not in result
