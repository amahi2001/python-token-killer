"""Concurrency tests — thread safety of singleton minimizers."""

import threading

import ptk


class TestConcurrency:
    def test_concurrent_minimize_dict(self):
        results: list[str] = [None] * 10  # type: ignore[list-item]
        errors: list[Exception] = []

        def worker(idx: int) -> None:
            try:
                d = {f"key_{idx}_{j}": j for j in range(50)}
                d["empty"] = None
                results[idx] = ptk.minimize(d)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        assert not errors, f"Thread errors: {errors}"
        assert all(isinstance(r, str) for r in results)

    def test_concurrent_minimize_mixed_types(self):
        inputs = [
            {"a": 1},
            [1, 2, 3],
            "def foo(): pass",
            "[ERROR] crash",
            "diff --git a/f b/f\n--- a/f\n+++ b/f\n@@ -1 +1 @@\n-a\n+b",
            "just text",
        ]
        results: list[str] = [None] * len(inputs)  # type: ignore[list-item]
        errors: list[Exception] = []

        def worker(idx: int) -> None:
            try:
                results[idx] = ptk.minimize(inputs[idx])
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(len(inputs))]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        assert not errors, f"Thread errors: {errors}"
        assert all(isinstance(r, str) for r in results)

    def test_concurrent_stats(self):
        errors: list[Exception] = []

        def worker() -> None:
            try:
                for _ in range(20):
                    ptk.stats({"a": 1, "b": None})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        assert not errors
