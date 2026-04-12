"""Lint tool output — ruff, eslint."""

import ptk


class TestLintOutput:
    RUFF_OUTPUT = (
        "src/myapp/utils.py:12:1: F401 `os` imported but unused\n"
        "src/myapp/utils.py:15:80: E501 Line too long (92 > 88 characters)\n"
        "src/myapp/models.py:7:1: F401 `datetime` imported but unused\n"
        "src/myapp/models.py:34:1: F401 `typing.List` imported but unused\n"
        "src/myapp/api/routes.py:3:1: F401 `flask` imported but unused\n"
        "src/myapp/api/routes.py:8:1: F401 `json` imported but unused\n"
        "Found 6 errors.\n"
    )

    ESLINT_OUTPUT = (
        "/home/user/app/src/index.js\n"
        "   3:1   error  'React' is defined but never used  no-unused-vars\n"
        "  12:5   error  'console' statements are not allowed  no-console\n"
        "  12:5   error  'console' statements are not allowed  no-console\n"
        "  12:5   error  'console' statements are not allowed  no-console\n"
        "  45:15  warning  Expected '===' and instead saw '=='  eqeqeq\n\n"
        "/home/user/app/src/utils.js\n"
        "  7:1    error  'lodash' is defined but never used  no-unused-vars\n\n"
        "✖ 7 problems (6 errors, 1 warning)\n"
    )

    def test_ruff_output_compresses(self):
        result = ptk.minimize(self.RUFF_OUTPUT, content_type="log")
        assert isinstance(result, str)
        assert len(result) <= len(self.RUFF_OUTPUT)

    def test_eslint_repeated_lines_collapse(self):
        assert "(x3)" in ptk.minimize(self.ESLINT_OUTPUT, content_type="log")

    def test_eslint_unique_errors_preserved(self):
        assert "no-unused-vars" in ptk.minimize(self.ESLINT_OUTPUT, content_type="log")

    def test_lint_output_compresses_less_than_original(self):
        assert len(ptk.minimize(self.ESLINT_OUTPUT, content_type="log")) < len(self.ESLINT_OUTPUT)
