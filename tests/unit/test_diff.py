"""DiffMinimizer tests — context folding, noise stripping."""

import ptk


class TestDiffMinimizer:
    SAMPLE_DIFF = (
        "diff --git a/f.py b/f.py\n"
        "--- a/f.py\n"
        "+++ b/f.py\n"
        "@@ -1,16 +1,16 @@\n"
        " context1\n context2\n context3\n context4\n"
        " context5\n context6\n context7\n context8\n"
        "-old line\n"
        "+new line\n"
        " context9\n context10\n context11\n context12\n"
    )

    CLAW_DIFF = (
        "diff --git a/src/server.py b/src/server.py\n"
        "index abc1234..def5678 100644\n"
        "--- a/src/server.py\n"
        "+++ b/src/server.py\n"
        "@@ -1,10 +1,12 @@\n"
        " import os\n import sys\n"
        "-import json\n"
        "+import json  # added comment\n"
        " \n def start():\n"
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
        assert "-import json" in ptk.minimize(self.CLAW_DIFF, content_type="diff")

    def test_keeps_hunk_header(self):
        assert "@@" in ptk.minimize(self.SAMPLE_DIFF, content_type="diff")

    def test_keeps_file_headers(self):
        result = ptk.minimize(self.SAMPLE_DIFF, content_type="diff")
        assert "--- a/f.py" in result
        assert "+++ b/f.py" in result

    def test_folds_large_context(self):
        assert "..." in ptk.minimize(self.SAMPLE_DIFF, content_type="diff")

    def test_aggressive_strips_index_line(self):
        result = ptk.minimize(self.CLAW_DIFF, content_type="diff", aggressive=True)
        assert "index abc1234" not in result

    def test_aggressive_strips_mode_lines(self):
        diff = "diff --git a/f b/f\nold mode 100644\nnew mode 100755\n--- a/f\n+++ b/f\n@@ -1 +1 @@\n-a\n+b"
        assert "old mode" not in ptk.minimize(diff, content_type="diff", aggressive=True)

    def test_no_newline_indicator_preserved(self):
        diff = "--- a/f\n+++ b/f\n@@ -1 +1 @@\n-a\n+b\n\\ No newline at end of file"
        assert "No newline" in ptk.minimize(diff, content_type="diff")

    def test_empty_diff(self):
        assert ptk.minimize("", content_type="diff") == ""

    def test_small_diff_not_over_truncated(self):
        diff = "--- a/f\n+++ b/f\n@@ -1,3 +1,3 @@\n one\n-two\n+TWO\n three"
        result = ptk.minimize(diff, content_type="diff")
        assert " one" in result
        assert " three" in result

    def test_large_diff_reduces_tokens(self):
        context = "\n".join(f" context_{i}" for i in range(40))
        diff = f"--- a/f\n+++ b/f\n@@ -1 +1 @@\n{context}\n+new_feature_line\n{context}"
        s = ptk.stats(diff, content_type="diff")
        assert s["savings_pct"] > 0
        assert "+new_feature_line" in s["output"]
