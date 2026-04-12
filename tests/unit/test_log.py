"""LogMinimizer tests — dedup, error filtering, stack traces."""

import ptk


class TestLogMinimizer:
    SAMPLE_LOG = (
        "2024-01-15T10:00:00Z [INFO] Server started on port 8080\n"
        "2024-01-15T10:00:01Z [DEBUG] Checking configuration\n"
        "2024-01-15T10:00:02Z [DEBUG] Checking configuration\n"
        "2024-01-15T10:00:03Z [DEBUG] Checking configuration\n"
        "2024-01-15T10:00:04Z [DEBUG] Checking configuration\n"
        "2024-01-15T10:00:05Z [ERROR] Failed to connect to database\n"
        "2024-01-15T10:00:06Z [INFO] Retrying connection\n"
        "2024-01-15T10:00:07Z [WARN] Disk usage above 80%\n"
        "2024-01-15T10:00:08Z [INFO] Completed health check"
    )

    SAMPLE_TRACEBACK = (
        "ERROR An unexpected error occurred\n"
        "Traceback (most recent call last):\n"
        '  File "/app/server.py", line 42, in handle_request\n'
        "    result = process(data)\n"
        '  File "/app/processor.py", line 17, in process\n'
        "    return transform(item)\n"
        "ValueError: invalid literal for int()\n"
        "INFO Continuing after error"
    )

    def test_dedup_repeated_lines(self):
        log = "[INFO] heartbeat\n" * 10 + "[ERROR] crash"
        result = ptk.minimize(log, content_type="log")
        assert "(x10)" in result
        assert "[ERROR] crash" in result

    def test_errors_only_keeps_error_and_warn(self):
        result = ptk.minimize(self.SAMPLE_LOG, content_type="log", aggressive=True)
        assert "ERROR" in result
        assert "WARN" in result

    def test_strips_timestamps_aggressive(self):
        result = ptk.minimize(
            "2024-01-15T12:00:00Z [INFO] hello", content_type="log", aggressive=True
        )
        assert "2024-01-15" not in result

    def test_preserves_timestamps_non_aggressive(self):
        result = ptk.minimize("2024-01-15T12:00:00Z [ERROR] fail", content_type="log")
        assert "2024-01-15" in result

    def test_stack_trace_preserved(self):
        result = ptk.minimize(self.SAMPLE_TRACEBACK, content_type="log", aggressive=True)
        assert "Traceback" in result
        assert "ValueError" in result

    def test_stack_trace_file_lines_preserved(self):
        result = ptk.minimize(self.SAMPLE_TRACEBACK, content_type="log", aggressive=True)
        assert "File" in result

    def test_fatal_preserved(self):
        log = "[INFO] Starting\n[FATAL] Out of memory\n[INFO] Exiting"
        result = ptk.minimize(log, content_type="log", aggressive=True)
        assert "FATAL" in result or "Out of memory" in result

    def test_failed_keyword_preserved(self):
        log = "[INFO] Starting\n[INFO] Connection failed\n[INFO] Done"
        result = ptk.minimize(log, content_type="log", aggressive=True)
        assert "failed" in result.lower()

    def test_empty_log(self):
        assert ptk.minimize("", content_type="log") == ""

    def test_single_line_log(self):
        assert "[INFO] Server started" in ptk.minimize("[INFO] Server started", content_type="log")

    def test_compression_improves_with_repetition(self):
        log = "[INFO] Heartbeat OK\n" * 50 + "[ERROR] Service down\n" + "[INFO] Heartbeat OK\n" * 50
        s = ptk.stats(log, content_type="log")
        assert s["minimized_len"] < s["original_len"]

    def test_mixed_levels_no_data_loss_for_errors(self):
        lines = [f"[ERROR] error_{i}" for i in range(5)]
        lines += [f"[DEBUG] filler_{i}" for i in range(30)]
        lines += [f"[WARN] warn_{i}" for i in range(5)]
        result = ptk.minimize("\n".join(lines), content_type="log", aggressive=True)
        for i in range(5):
            assert f"error_{i}" in result
            assert f"warn_{i}" in result

    def test_errors_only_kwarg(self):
        log = "[INFO] ok\n[ERROR] bad"
        assert "[ERROR] bad" in ptk.minimize(log, content_type="log", errors_only=True)
