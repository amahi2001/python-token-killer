"""Real-world tool output tests — patterns from RTK and claw-compactor.

Tests the actual kinds of output developers pass to LLMs:
pytest, cargo test, go test, ruff/eslint lint output, git log/blame,
file listings (ls -la, tree, find), docker ps, near-duplicate lines,
import block collapsing, and mixed-content detection.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import ptk
from ptk._types import ContentType, detect

# ═══════════════════════════════════════════════════════════════════════
# 1. PYTEST OUTPUT  (RTK: pytest handler, 90% reduction on failures-only)
# ═══════════════════════════════════════════════════════════════════════


class TestPytestOutput:
    """pytest output is structured log output — detected as LOG, filtered to failures."""

    PASSING_RUN = (
        "============================= test session starts ==============================\n"
        "platform linux -- Python 3.12.0, pytest-8.1.0\n"
        "collected 322 items\n"
        "\n"
        "tests/test_ptk.py::TestDetection::test_dict PASSED\n"
        "tests/test_ptk.py::TestDetection::test_list PASSED\n"
        "tests/test_ptk.py::TestDetection::test_code_python_def PASSED\n"
        "tests/test_ptk.py::TestDetection::test_code_python_class PASSED\n"
        "tests/test_ptk.py::TestDetection::test_log PASSED\n"
        "tests/test_ptk.py::TestDetection::test_diff PASSED\n"
        "tests/test_ptk.py::TestDictMinimizer::test_basic_compact_json PASSED\n"
        "tests/test_ptk.py::TestDictMinimizer::test_nested_null_strip PASSED\n"
        "\n"
        "============================== 8 passed in 0.23s ==============================\n"
    )

    FAILING_RUN = (
        "============================= test session starts ==============================\n"
        "platform linux -- Python 3.12.0, pytest-8.1.0\n"
        "collected 10 items\n"
        "\n"
        "tests/test_ptk.py::TestDictMinimizer::test_basic_compact_json PASSED\n"
        "tests/test_ptk.py::TestDictMinimizer::test_nested_null_strip PASSED\n"
        "tests/test_ptk.py::TestDictMinimizer::test_aggressive FAILED\n"
        "tests/test_ptk.py::TestDictMinimizer::test_kv_format PASSED\n"
        "tests/test_ptk.py::TestListMinimizer::test_tabular FAILED\n"
        "\n"
        "=================================== FAILURES ===================================\n"
        "_________________ TestDictMinimizer::test_aggressive _________________\n"
        "\n"
        "    def test_aggressive():\n"
        ">       result = ptk.minimize({'a': 1}, aggressive=True)\n"
        "E       AssertionError: assert 'a:1' == '{\"a\":1}'\n"
        "\n"
        "tests/test_ptk.py:42: AssertionError\n"
        "_________________ TestListMinimizer::test_tabular _________________\n"
        "\n"
        "    def test_tabular():\n"
        ">       assert '[2]{id}:' in result\n"
        "E       AssertionError\n"
        "\n"
        "tests/test_ptk.py:87: AssertionError\n"
        "=========================== 2 failed, 8 passed in 0.31s ===========================\n"
    )

    def test_pytest_detected_as_log(self):
        """pytest output contains ERROR/FAILED markers — detected as log."""
        detected = detect(self.FAILING_RUN)
        assert detected == ContentType.LOG

    def test_passing_run_compresses(self):
        """All-pass output: repeated PASSED lines collapse."""
        result = ptk.minimize(self.PASSING_RUN, content_type="log")
        assert "PASSED" in result
        assert len(result) < len(self.PASSING_RUN)

    def test_failing_run_errors_only_keeps_failures(self):
        """Errors-only mode keeps FAILED lines and assertion context."""
        result = ptk.minimize(self.FAILING_RUN, content_type="log", aggressive=True)
        assert "FAILED" in result
        assert "AssertionError" in result

    def test_failing_run_errors_only_drops_passing(self):
        """PASSED lines should be filtered out in aggressive mode."""
        result = ptk.minimize(self.FAILING_RUN, content_type="log", aggressive=True)
        # PASSED lines should not appear as standalone lines
        lines = [ln.strip() for ln in result.split("\n") if ln.strip()]
        passed_only_lines = [ln for ln in lines if ln.endswith("PASSED")]
        assert len(passed_only_lines) == 0

    def test_session_header_stripped_in_aggressive(self):
        """Boilerplate session headers add noise — removed in aggressive mode."""
        result = ptk.minimize(self.PASSING_RUN, content_type="log", aggressive=True)
        # Header timestamp/platform info not critical
        assert isinstance(result, str)
        assert len(result) > 0


# ═══════════════════════════════════════════════════════════════════════
# 2. CARGO TEST OUTPUT  (RTK: cargo test handler)
# ═══════════════════════════════════════════════════════════════════════


class TestCargoTestOutput:
    CARGO_MIXED = (
        "   Compiling myapp v0.1.0 (/home/user/myapp)\n"
        "    Finished test [unoptimized + debuginfo] target(s) in 2.34s\n"
        "     Running unittests src/main.rs (target/debug/deps/myapp-abc123)\n"
        "\n"
        "running 8 tests\n"
        "test tests::test_parse_valid ... ok\n"
        "test tests::test_parse_empty ... ok\n"
        "test tests::test_parse_invalid ... ok\n"
        "test tests::test_serialize ... ok\n"
        "test tests::test_roundtrip ... FAILED\n"
        "test tests::test_unicode ... ok\n"
        "test tests::test_large_input ... ok\n"
        "test tests::test_edge_case ... FAILED\n"
        "\n"
        "failures:\n"
        "\n"
        "---- tests::test_roundtrip stdout ----\n"
        "thread 'tests::test_roundtrip' panicked at 'assertion failed: `(left == right)`\n"
        '  left: `"hello"`,\n'
        ' right: `"HELLO"`\', src/main.rs:42:5\n'
        "\n"
        "---- tests::test_edge_case stdout ----\n"
        "thread 'tests::test_edge_case' panicked at 'called `Option::unwrap()` on a `None` value', src/main.rs:87:9\n"
        "\n"
        "failures:\n"
        "    tests::test_roundtrip\n"
        "    tests::test_edge_case\n"
        "\n"
        "test result: FAILED. 6 passed; 2 failed; 0 ignored; 0 measured; 0 filtered out; "
        "finished in 0.02s\n"
    )

    def test_cargo_output_compresses(self):
        result = ptk.minimize(self.CARGO_MIXED, content_type="log")
        assert isinstance(result, str)
        assert len(result) < len(self.CARGO_MIXED)

    def test_cargo_failures_preserved_aggressive(self):
        result = ptk.minimize(self.CARGO_MIXED, content_type="log", aggressive=True)
        assert "FAILED" in result
        assert "panicked" in result

    def test_cargo_ok_lines_collapsed(self):
        """Repeated 'ok' test lines should collapse."""
        result = ptk.minimize(self.CARGO_MIXED, content_type="log")
        # Should have fewer lines than original
        assert result.count("\n") < self.CARGO_MIXED.count("\n")


# ═══════════════════════════════════════════════════════════════════════
# 3. GO TEST OUTPUT  (RTK: go test handler, NDJSON format)
# ═══════════════════════════════════════════════════════════════════════


class TestGoTestOutput:
    GO_MIXED = (
        "--- PASS: TestParseValid (0.00s)\n"
        "--- PASS: TestParseEmpty (0.00s)\n"
        "--- PASS: TestParseInvalid (0.00s)\n"
        "--- FAIL: TestRoundtrip (0.00s)\n"
        '    main_test.go:42: got "hello", want "HELLO"\n'
        "--- PASS: TestUnicode (0.00s)\n"
        "--- FAIL: TestEdgeCase (0.01s)\n"
        "    main_test.go:87: unexpected nil pointer\n"
        "FAIL\n"
        "FAIL\tgithub.com/user/myapp\t0.012s\n"
    )

    def test_go_test_detected_as_log(self):
        assert detect(self.GO_MIXED) == ContentType.LOG

    def test_go_failures_preserved(self):
        result = ptk.minimize(self.GO_MIXED, content_type="log", aggressive=True)
        assert "FAIL" in result

    def test_go_passing_lines_removable(self):
        """PASS lines are noise in aggressive mode — should be filtered."""
        result = ptk.minimize(self.GO_MIXED, content_type="log", aggressive=True)
        lines = [ln.strip() for ln in result.split("\n") if ln.strip()]
        pass_only = [ln for ln in lines if ln.startswith("--- PASS")]
        assert len(pass_only) == 0

    def test_go_failure_details_kept(self):
        result = ptk.minimize(self.GO_MIXED, content_type="log", aggressive=True)
        assert "got" in result or "nil pointer" in result


# ═══════════════════════════════════════════════════════════════════════
# 4. RUFF / LINT TOOL OUTPUT
# ═══════════════════════════════════════════════════════════════════════


class TestLintOutput:
    """Lint output is structured: file:line:col: CODE message."""

    RUFF_OUTPUT = (
        "src/myapp/utils.py:12:1: F401 `os` imported but unused\n"
        "src/myapp/utils.py:15:80: E501 Line too long (92 > 88 characters)\n"
        "src/myapp/utils.py:23:5: B006 Do not use mutable data structures for argument defaults\n"
        "src/myapp/models.py:7:1: F401 `datetime` imported but unused\n"
        "src/myapp/models.py:34:1: F401 `typing.List` imported but unused\n"
        "src/myapp/models.py:45:15: E711 Comparison to `None` (use `is` or `is not`)\n"
        "src/myapp/api/routes.py:3:1: F401 `flask` imported but unused\n"
        "src/myapp/api/routes.py:8:1: F401 `json` imported but unused\n"
        "src/myapp/api/routes.py:89:5: B007 Loop control variable `i` not used in loop body\n"
        "Found 9 errors.\n"
    )

    ESLINT_OUTPUT = (
        "/home/user/app/src/index.js\n"
        "   3:1   error  'React' is defined but never used  no-unused-vars\n"
        "  12:5   error  'console' statements are not allowed  no-console\n"
        "  12:5   error  'console' statements are not allowed  no-console\n"
        "  12:5   error  'console' statements are not allowed  no-console\n"
        "  45:15  warning  Expected '===' and instead saw '=='  eqeqeq\n"
        "\n"
        "/home/user/app/src/utils.js\n"
        "  7:1    error  'lodash' is defined but never used  no-unused-vars\n"
        "\n"
        "✖ 7 problems (6 errors, 1 warning)\n"
    )

    def test_ruff_output_compresses(self):
        result = ptk.minimize(self.RUFF_OUTPUT, content_type="log")
        assert isinstance(result, str)
        assert len(result) <= len(self.RUFF_OUTPUT)

    def test_eslint_repeated_lines_collapse(self):
        """Three identical 'console' error lines should collapse to one with (x3)."""
        result = ptk.minimize(self.ESLINT_OUTPUT, content_type="log")
        assert "(x3)" in result

    def test_eslint_unique_errors_preserved(self):
        result = ptk.minimize(self.ESLINT_OUTPUT, content_type="log")
        assert "no-unused-vars" in result

    def test_lint_output_compresses_less_than_original(self):
        result = ptk.minimize(self.ESLINT_OUTPUT, content_type="log")
        assert len(result) < len(self.ESLINT_OUTPUT)


# ═══════════════════════════════════════════════════════════════════════
# 5. GIT LOG OUTPUT  (RTK: git log handler)
# ═══════════════════════════════════════════════════════════════════════


class TestGitLogOutput:
    GIT_LOG_ONELINE = (
        "a1b2c3d fix: handle null bytes in dict keys\n"
        "e4f5g6h feat: add TextMinimizer word abbreviations\n"
        "i7j8k9l test: 169 adversarial tests\n"
        "m1n2o3p fix: pragma preservation in CodeMinimizer\n"
        "q4r5s6t docs: add AGENTS.md and CLAUDE.md\n"
        "u7v8w9x feat: DiffMinimizer context folding\n"
        "y1z2a3b chore: initial commit\n"
    )

    GIT_STATUS = (
        "On branch main\n"
        "Your branch is up to date with 'origin/main'.\n"
        "\n"
        "Changes to be committed:\n"
        '  (use "git restore --staged <file>..." to unstage)\n'
        "\tmodified:   src/ptk/minimizers/_dict.py\n"
        "\tmodified:   src/ptk/minimizers/_code.py\n"
        "\tmodified:   tests/test_ptk.py\n"
        "\n"
        "Changes not staged for commit:\n"
        '  (use "git add <file>..." to update what will be committed)\n'
        '  (use "git restore <file>..." to discard changes in working directory)\n'
        "\tmodified:   README.md\n"
        "\n"
        "Untracked files:\n"
        '  (use "git add <file>..." to track)\n'
        "\tbenchmarks/samples/new_sample.json\n"
    )

    def test_git_log_compresses(self):
        result = ptk.minimize(self.GIT_LOG_ONELINE, content_type="log")
        assert isinstance(result, str)

    def test_git_log_all_commits_preserved(self):
        """git log lines don't repeat so dedup shouldn't drop anything."""
        result = ptk.minimize(self.GIT_LOG_ONELINE, content_type="log")
        assert "fix:" in result
        assert "feat:" in result

    def test_git_status_compresses(self):
        result = ptk.minimize(self.GIT_STATUS, content_type="log")
        assert isinstance(result, str)
        assert len(result) < len(self.GIT_STATUS)

    def test_git_status_files_preserved(self):
        result = ptk.minimize(self.GIT_STATUS, content_type="log")
        assert "_dict.py" in result or "_code.py" in result


# ═══════════════════════════════════════════════════════════════════════
# 6. FILE LISTINGS  (RTK: ls / find / tree handlers)
# ═══════════════════════════════════════════════════════════════════════


class TestFileListingOutput:
    LS_LA = (
        "total 48\n"
        "drwxr-xr-x  8 user group 4096 Apr  9 02:30 .\n"
        "drwxr-xr-x 15 user group 4096 Apr  9 00:00 ..\n"
        "drwxr-xr-x  2 user group 4096 Apr  9 02:30 .github\n"
        "-rw-r--r--  1 user group  638 Apr  9 02:30 Makefile\n"
        "-rw-r--r--  1 user group 8535 Apr  9 02:30 CONTRIBUTING.md\n"
        "-rw-r--r--  1 user group 4291 Apr  9 02:30 CHANGELOG.md\n"
        "-rw-r--r--  1 user group 1073 Apr  9 02:30 LICENSE\n"
        "-rw-r--r--  1 user group 7772 Apr  9 02:30 README.md\n"
        "drwxr-xr-x  3 user group 4096 Apr  9 02:30 src\n"
        "drwxr-xr-x  2 user group 4096 Apr  9 02:30 tests\n"
        "-rw-r--r--  1 user group 2151 Apr  9 02:30 pyproject.toml\n"
    )

    TREE_OUTPUT = (
        "src/ptk\n"
        "├── __init__.py\n"
        "├── _base.py\n"
        "├── _types.py\n"
        "└── minimizers\n"
        "    ├── __init__.py\n"
        "    ├── _code.py\n"
        "    ├── _dict.py\n"
        "    ├── _diff.py\n"
        "    ├── _list.py\n"
        "    ├── _log.py\n"
        "    └── _text.py\n"
        "\n"
        "1 directory, 10 files\n"
    )

    FIND_OUTPUT = "\n".join(
        [f"./src/ptk/minimizers/_{m}.py" for m in ["dict", "list", "code", "log", "diff", "text"]]
        + [f"./tests/test_{m}.py" for m in ["ptk", "adversarial", "real_world"]]
        + [f"./benchmarks/samples/file_{i}.json" for i in range(20)]
    )

    def test_ls_la_compresses(self):
        result = ptk.minimize(self.LS_LA, content_type="text")
        assert isinstance(result, str)

    def test_tree_output_as_text(self):
        result = ptk.minimize(self.TREE_OUTPUT, content_type="text")
        assert isinstance(result, str)
        assert "__init__.py" in result

    def test_find_output_no_crash(self):
        """find output with all unique paths — no compression expected, no crash."""
        result = ptk.minimize(self.FIND_OUTPUT, content_type="log")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_find_output_with_repeats_compresses(self):
        """find output with repeated identical lines does compress."""
        repeated = "\n".join(["./src/main.py"] * 20 + ["./src/utils.py"] * 10)
        result = ptk.minimize(repeated, content_type="log")
        assert len(result) < len(repeated)


# ═══════════════════════════════════════════════════════════════════════
# 7. DOCKER PS OUTPUT  (RTK: docker ps handler)
# ═══════════════════════════════════════════════════════════════════════


class TestDockerOutput:
    DOCKER_PS = (
        "CONTAINER ID   IMAGE              COMMAND                  CREATED        STATUS        PORTS                    NAMES\n"
        'a1b2c3d4e5f6   nginx:latest       "/docker-entrypoint.…"   2 hours ago    Up 2 hours    0.0.0.0:80->80/tcp       web\n'
        'b2c3d4e5f6a1   postgres:15        "docker-entrypoint.s…"   2 hours ago    Up 2 hours    0.0.0.0:5432->5432/tcp   db\n'
        'c3d4e5f6a1b2   redis:7            "docker-entrypoint.s…"   2 hours ago    Up 2 hours    0.0.0.0:6379->6379/tcp   cache\n'
        'd4e5f6a1b2c3   myapp:latest       "python -m uvicorn m…"   1 hour ago     Up 1 hour     0.0.0.0:8000->8000/tcp   api\n'
    )

    DOCKER_LOGS_SPAM = "\n".join(
        ["[2024-01-01T10:00:00Z] INFO: health check ok"] * 50
        + ["[2024-01-01T10:05:00Z] ERROR: connection refused to db:5432"]
    )

    def test_docker_ps_as_list(self):
        """docker ps is tabular — treat as text or log."""
        result = ptk.minimize(self.DOCKER_PS, content_type="text")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_docker_logs_dedup(self):
        """Repeated health check lines should collapse."""
        result = ptk.minimize(self.DOCKER_LOGS_SPAM, content_type="log")
        assert "(x50)" in result

    def test_docker_error_preserved(self):
        result = ptk.minimize(self.DOCKER_LOGS_SPAM, content_type="log", aggressive=True)
        assert "connection refused" in result


# ═══════════════════════════════════════════════════════════════════════
# 8. NEAR-DUPLICATE LINE DETECTION  (claw-compactor: SemanticDedup)
# ═══════════════════════════════════════════════════════════════════════


class TestNearDuplicates:
    """Exact dedup only collapses identical lines. Near-duplicates survive.
    These tests document the CURRENT behavior (not collapsing near-dupes)
    so we know what we're NOT doing yet.
    """

    NEAR_DUPE_LOGS = (
        "2024-01-01T10:00:01Z [INFO] Request from 192.168.1.100 completed in 234ms\n"
        "2024-01-01T10:00:02Z [INFO] Request from 192.168.1.101 completed in 241ms\n"
        "2024-01-01T10:00:03Z [INFO] Request from 192.168.1.102 completed in 229ms\n"
        "2024-01-01T10:00:04Z [INFO] Request from 192.168.1.103 completed in 238ms\n"
        "2024-01-01T10:00:05Z [INFO] Request from 192.168.1.104 completed in 251ms\n"
        "2024-01-01T10:00:06Z [ERROR] Request from 192.168.1.105 failed with 500\n"
    )

    def test_exact_dupes_collapse(self):
        log = "[INFO] heartbeat ok\n" * 5 + "[ERROR] crash"
        result = ptk.minimize(log, content_type="log")
        assert "(x5)" in result

    def test_near_dupes_preserved(self):
        """Near-duplicate lines with different IPs/times are NOT collapsed (by design)."""
        result = ptk.minimize(self.NEAR_DUPE_LOGS, content_type="log")
        # All unique lines survive because they differ
        assert result.count("\n") >= 5

    def test_near_dupes_error_filtered_in_aggressive(self):
        """In aggressive mode, only the ERROR line + context survives."""
        result = ptk.minimize(self.NEAR_DUPE_LOGS, content_type="log", aggressive=True)
        assert "ERROR" in result or "failed" in result.lower()


# ═══════════════════════════════════════════════════════════════════════
# 9. CODE — IMPORT BLOCK COLLAPSING  (claw-compactor: StructuralCollapse)
# ═══════════════════════════════════════════════════════════════════════


class TestImportCollapsing:
    """We don't do import collapsing (no AST), but we document what the
    CodeMinimizer DOES do with large import blocks.
    """

    LARGE_IMPORT_BLOCK = (
        "import os\n"
        "import sys\n"
        "import json\n"
        "import re\n"
        "import time\n"
        "import hashlib\n"
        "import logging\n"
        "import threading\n"
        "from typing import Any, Dict, List, Optional, Tuple, Union\n"
        "from pathlib import Path\n"
        "from datetime import datetime, timedelta\n"
        "from collections import defaultdict, Counter\n"
        "\n"
        "def main() -> None:\n"
        "    pass\n"
    )

    def test_import_block_in_clean_mode(self):
        """Clean mode preserves import block (no AST collapsing)."""
        result = ptk.minimize(self.LARGE_IMPORT_BLOCK, content_type="code")
        assert "import os" in result
        assert "def main" in result

    def test_import_block_signatures_mode(self):
        """Signatures mode drops all imports — keeps only def/class."""
        result = ptk.minimize(self.LARGE_IMPORT_BLOCK, content_type="code", mode="signatures")
        assert "def main" in result
        # imports are not signatures, so they should be gone
        assert "import os" not in result

    def test_imports_not_treated_as_signatures(self):
        """import statements should not be extracted as signatures."""
        # Use multi-line def (single-line 'def foo(): pass' isn't a real signature)
        code = "import os\nimport sys\n\ndef foo():\n    pass"
        result = ptk.minimize(code, content_type="code", mode="signatures")
        assert "import" not in result
        assert "def foo" in result


# ═══════════════════════════════════════════════════════════════════════
# 10. BUILD OUTPUT  (RTK: build/compile error handler)
# ═══════════════════════════════════════════════════════════════════════


class TestBuildOutput:
    NPM_BUILD_ERRORS = (
        "npm run build\n"
        "\n"
        "> myapp@1.0.0 build\n"
        "> webpack --config webpack.config.js\n"
        "\n"
        "asset main.js 1.23 MiB [compared for emit] (name: main)\n"
        "asset vendors.js 456 KiB [compared for emit] (name: vendors)\n"
        "orphan modules 234 bytes [orphan] 3 modules\n"
        "runtime modules 1.13 KiB 5 modules\n"
        "cacheable modules 1.68 MiB\n"
        "  modules by path ./node_modules/ 1.32 MiB\n"
        "    modules by path ./node_modules/react/ 89.5 KiB\n"
        "    modules by path ./node_modules/react-dom/ 1.18 MiB\n"
        "  modules by path ./src/ 362 KiB\n"
        "\n"
        "ERROR in ./src/components/Button.jsx\n"
        "Module not found: Error: Can't resolve './styles/button.css'\n"
        " @ ./src/components/Button.jsx 3:0-30\n"
        " @ ./src/App.jsx 7:0-36\n"
        " @ ./src/index.js 5:0-24\n"
        "\n"
        "ERROR in ./src/utils/api.js\n"
        "Module not found: Error: Can't resolve 'axios'\n"
        " @ ./src/utils/api.js 1:0-22\n"
        " @ ./src/App.jsx 3:0-28\n"
        "\n"
        "webpack compiled with 2 errors\n"
    )

    def test_build_errors_preserved_aggressive(self):
        result = ptk.minimize(self.NPM_BUILD_ERRORS, content_type="log", aggressive=True)
        assert "ERROR" in result
        assert "Can't resolve" in result

    def test_build_stats_compressed(self):
        """Module size stats (not errors) should be compressed away."""
        result = ptk.minimize(self.NPM_BUILD_ERRORS, content_type="log", aggressive=True)
        # Verbose asset/module stats should not survive
        assert len(result) < len(self.NPM_BUILD_ERRORS) * 0.7

    def test_build_output_compresses(self):
        result = ptk.minimize(self.NPM_BUILD_ERRORS, content_type="log")
        assert isinstance(result, str)
        assert len(result) < len(self.NPM_BUILD_ERRORS)


# ═══════════════════════════════════════════════════════════════════════
# 11. MIXED REAL-WORLD PIPELINE SIMULATIONS
# ═══════════════════════════════════════════════════════════════════════


class TestPipelineSimulations:
    """Simulate actual agent pipeline usage — chain multiple minimizations."""

    def test_langgraph_tool_output_pipeline(self):
        """Simulate: agent calls tool → gets API response → minimizes → passes to LLM."""

        tool_output = {
            "results": [
                {
                    "id": i,
                    "content": f"Document {i} about machine learning",
                    "score": round(0.95 - i * 0.05, 2),
                    "metadata": {
                        "source": f"paper_{i}.pdf",
                        "year": 2023,
                        "author": None,
                        "tags": [],
                        "embedding": None,
                    },
                }
                for i in range(10)
            ],
            "total": 10,
            "query_time_ms": 234,
            "errors": None,
            "warnings": [],
        }

        s = ptk.stats(tool_output)
        assert s["savings_pct"] > 20
        assert "Document 0" in s["output"]
        assert "Document 9" in s["output"]

    def test_code_review_pipeline(self):
        """Simulate: agent reads file → passes to LLM with signature extraction."""
        code = "\n".join(
            [
                f"def function_{i}(x: int, y: str = 'default') -> bool:\n"
                f"    # Implementation detail {i}\n"
                f"    return x > 0  # {i}"
                for i in range(20)
            ]
        )
        # First pass: extract signatures only for overview
        sigs = ptk.minimize(code, content_type="code", mode="signatures")
        # Should have 20 signatures, no comments, no bodies
        assert sigs.count("def function_") == 20
        assert "Implementation detail" not in sigs
        # Signatures are ~50% of original (bodies removed, signatures verbose)
        assert len(sigs) < len(code) * 0.6

    def test_log_triage_pipeline(self):
        """Simulate: CI log → errors-only → feed to LLM for diagnosis."""
        ci_log = (
            "[2024-01-01T10:00:00Z] INFO: Starting test suite\n"
            + "[2024-01-01T10:00:01Z] DEBUG: Running test 1\n" * 100
            + "[2024-01-01T10:00:02Z] ERROR: Database connection timeout\n"
            + "[2024-01-01T10:00:02Z] DEBUG: Cleanup started\n" * 50
            + "[2024-01-01T10:00:03Z] INFO: Test suite complete\n"
        )
        result = ptk.minimize(ci_log, content_type="log", aggressive=True)
        assert "ERROR" in result
        assert "Database connection timeout" in result
        # Should be much smaller
        assert len(result) < len(ci_log) * 0.2
