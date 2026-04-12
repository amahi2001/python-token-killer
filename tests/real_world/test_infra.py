"""Infrastructure output — docker, file listings, build errors, import blocks."""

import ptk


class TestDockerOutput:
    DOCKER_PS = (
        "CONTAINER ID   IMAGE              COMMAND                  CREATED        STATUS        PORTS                    NAMES\n"
        'a1b2c3d4e5f6   nginx:latest       "/docker-entrypoint."   2 hours ago    Up 2 hours    0.0.0.0:80->80/tcp       web\n'
        'b2c3d4e5f6a1   postgres:15        "docker-entrypoint.s"   2 hours ago    Up 2 hours    0.0.0.0:5432->5432/tcp   db\n'
        'd4e5f6a1b2c3   myapp:latest       "python -m uvicorn m"   1 hour ago     Up 1 hour     0.0.0.0:8000->8000/tcp   api\n'
    )

    DOCKER_LOGS_SPAM = "\n".join(
        ["[2024-01-01T10:00:00Z] INFO: health check ok"] * 50
        + ["[2024-01-01T10:05:00Z] ERROR: connection refused to db:5432"]
    )

    def test_docker_ps_as_text(self):
        result = ptk.minimize(self.DOCKER_PS, content_type="text")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_docker_logs_dedup(self):
        assert "(x50)" in ptk.minimize(self.DOCKER_LOGS_SPAM, content_type="log")

    def test_docker_error_preserved(self):
        result = ptk.minimize(self.DOCKER_LOGS_SPAM, content_type="log", aggressive=True)
        assert "connection refused" in result


class TestFileListingOutput:
    LS_LA = (
        "total 48\n"
        "drwxr-xr-x  8 user group 4096 Apr  9 02:30 .\n"
        "-rw-r--r--  1 user group  638 Apr  9 02:30 Makefile\n"
        "-rw-r--r--  1 user group 7772 Apr  9 02:30 README.md\n"
        "drwxr-xr-x  3 user group 4096 Apr  9 02:30 src\n"
        "drwxr-xr-x  2 user group 4096 Apr  9 02:30 tests\n"
    )

    TREE_OUTPUT = (
        "src/ptk\n├── __init__.py\n├── _base.py\n├── _types.py\n"
        "└── minimizers\n    ├── _code.py\n    ├── _dict.py\n    └── _text.py\n"
        "\n1 directory, 7 files\n"
    )

    def test_ls_la_compresses(self):
        assert isinstance(ptk.minimize(self.LS_LA, content_type="text"), str)

    def test_tree_output_preserved(self):
        result = ptk.minimize(self.TREE_OUTPUT, content_type="text")
        assert "__init__.py" in result

    def test_find_output_no_crash(self):
        find = "\n".join(f"./src/ptk/minimizers/_{m}.py" for m in ["dict", "list", "code"])
        result = ptk.minimize(find, content_type="log")
        assert isinstance(result, str)

    def test_find_output_with_repeats_compresses(self):
        repeated = "\n".join(["./src/main.py"] * 20 + ["./src/utils.py"] * 10)
        assert len(ptk.minimize(repeated, content_type="log")) < len(repeated)


class TestBuildOutput:
    NPM_BUILD_ERRORS = (
        "npm run build\n\n> myapp@1.0.0 build\n> webpack --config webpack.config.js\n\n"
        "asset main.js 1.23 MiB [compared for emit] (name: main)\n"
        "cacheable modules 1.68 MiB\n  modules by path ./node_modules/ 1.32 MiB\n\n"
        "ERROR in ./src/components/Button.jsx\n"
        "Module not found: Error: Can't resolve './styles/button.css'\n"
        " @ ./src/App.jsx 7:0-36\n\n"
        "ERROR in ./src/utils/api.js\n"
        "Module not found: Error: Can't resolve 'axios'\n\n"
        "webpack compiled with 2 errors\n"
    )

    def test_build_errors_preserved_aggressive(self):
        result = ptk.minimize(self.NPM_BUILD_ERRORS, content_type="log", aggressive=True)
        assert "ERROR" in result
        assert "Can't resolve" in result

    def test_build_stats_compressed(self):
        result = ptk.minimize(self.NPM_BUILD_ERRORS, content_type="log", aggressive=True)
        assert len(result) < len(self.NPM_BUILD_ERRORS) * 0.7

    def test_build_output_compresses(self):
        result = ptk.minimize(self.NPM_BUILD_ERRORS, content_type="log")
        assert len(result) < len(self.NPM_BUILD_ERRORS)


class TestImportCollapsing:
    LARGE_IMPORT_BLOCK = (
        "import os\nimport sys\nimport json\nimport re\nimport time\n"
        "from typing import Any, Dict, List, Optional\n"
        "from pathlib import Path\n\n"
        "def main() -> None:\n    pass\n"
    )

    def test_import_block_in_clean_mode(self):
        result = ptk.minimize(self.LARGE_IMPORT_BLOCK, content_type="code")
        assert "import os" in result
        assert "def main" in result

    def test_import_block_signatures_mode(self):
        result = ptk.minimize(self.LARGE_IMPORT_BLOCK, content_type="code", mode="signatures")
        assert "def main" in result
        assert "import os" not in result

    def test_imports_not_treated_as_signatures(self):
        code = "import os\nimport sys\n\ndef foo():\n    pass"
        result = ptk.minimize(code, content_type="code", mode="signatures")
        assert "import" not in result
        assert "def foo" in result
