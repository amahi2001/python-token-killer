"""Content type auto-detection tests — maps to claw-compactor's Cortex stage."""

import ptk
from ptk._types import ContentType, detect


class TestDetection:
    # ── Python objects ──
    def test_dict(self):
        assert detect({"a": 1}) == ContentType.DICT

    def test_list(self):
        assert detect([1, 2, 3]) == ContentType.LIST

    def test_tuple(self):
        assert detect((1, 2)) == ContentType.LIST

    # ── Code (multi-language) ──
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

    # ── Logs ──
    def test_log_bracketed(self):
        assert detect("[INFO] Server started\n[ERROR] Crash") == ContentType.LOG

    def test_log_spaced(self):
        assert detect("2024-01-01 INFO Starting up\n2024-01-01 ERROR Fail") == ContentType.LOG

    def test_log_colon_format(self):
        assert detect("INFO: Starting\nERROR: Failed\nDEBUG: Done") == ContentType.LOG

    def test_log_warning(self):
        assert detect("WARNING: disk full\nCRITICAL: shutdown") == ContentType.LOG

    # ── Diffs ──
    def test_diff_standard(self):
        diff = "diff --git a/f.py b/f.py\n--- a/f.py\n+++ b/f.py\n@@ -1,3 +1,3 @@\n-old\n+new"
        assert detect(diff) == ContentType.DIFF

    def test_diff_needs_hunk_header(self):
        assert detect("--- some text\n+++ more text") == ContentType.TEXT

    # ── Text / fallback ──
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
