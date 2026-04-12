"""Performance tests — large inputs must complete in < 5 seconds."""

import time

import ptk


class TestPerformance:
    def test_large_json_payload(self):
        records = [{f"field_{j}": f"value_{i}_{j}" for j in range(10)} for i in range(1000)]
        payload = [{**r, "empty1": None, "empty2": "", "empty3": []} for r in records]
        start = time.time()
        result = ptk.minimize(payload)
        assert time.time() - start < 5.0
        assert isinstance(result, str)

    def test_large_code_file(self):
        lines = []
        for i in range(1000):
            lines += [
                f"# Function {i}",
                f"def func_{i}(x: int, y: int) -> int:",
                f'    """Compute something for {i}."""',
                f"    return x + y + {i}",
                "",
            ]
        start = time.time()
        result = ptk.minimize("\n".join(lines), content_type="code")
        assert time.time() - start < 5.0
        assert isinstance(result, str)

    def test_large_log_file(self):
        lines = []
        for i in range(10_000):
            level = "DEBUG" if i % 10 != 0 else "ERROR"
            lines.append(f"2024-01-01T00:00:{i:05d}Z [{level}] Message {i % 100}")
        start = time.time()
        ptk.minimize("\n".join(lines), content_type="log")
        assert time.time() - start < 5.0

    def test_large_diff(self):
        parts = ["diff --git a/f b/f\n--- a/f\n+++ b/f\n"]
        for hunk in range(10):
            parts.append(f"@@ -{hunk * 500},{500} +{hunk * 500},{501} @@\n")
            for j in range(500):
                parts.append(
                    f"-old_{hunk}\n+new_{hunk}\n" if j == 250 else f" context_{hunk}_{j}\n"
                )
        start = time.time()
        ptk.minimize("".join(parts), content_type="diff")
        assert time.time() - start < 5.0

    def test_large_text_with_abbreviations(self):
        words = [
            "implementation",
            "configuration",
            "production",
            "environment",
            "application",
            "infrastructure",
            "authentication",
            "repository",
        ]
        start = time.time()
        ptk.minimize(" ".join(words * 1000), content_type="text")
        assert time.time() - start < 5.0


class TestIdempotency:
    def test_dict_idempotent(self):
        import json

        d = {"a": 1, "b": 2}
        first = ptk.minimize(d)
        assert first == ptk.minimize(json.loads(first))

    def test_text_idempotent(self):
        text = "The implementation of the configuration is complete."
        first = ptk.minimize(text, content_type="text")
        assert first == ptk.minimize(first, content_type="text")

    def test_code_clean_idempotent(self):
        code = "def foo():\n    return 1\n\ndef bar():\n    return 2"
        first = ptk.minimize(code, content_type="code")
        assert first == ptk.minimize(first, content_type="code")

    def test_log_idempotent(self):
        log = "[INFO] hello\n[ERROR] world"
        first = ptk.minimize(log, content_type="log")
        assert first == ptk.minimize(first, content_type="log")

    def test_minimize_never_expands_dict(self):
        d = {"a": 1, "b": None, "c": "", "d": [None], "e": {}}
        s = ptk.stats(d)
        assert s["minimized_len"] <= s["original_len"]
