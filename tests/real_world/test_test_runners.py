"""Test runner output — pytest, cargo test, go test."""

import ptk
from ptk._types import ContentType, detect


class TestPytestOutput:
    PASSING_RUN = (
        "============================= test session starts ==============================\n"
        "platform linux -- Python 3.12.0, pytest-8.1.0\ncollected 322 items\n\n"
        "tests/test_ptk.py::TestDetection::test_dict PASSED\n"
        "tests/test_ptk.py::TestDetection::test_list PASSED\n"
        "tests/test_ptk.py::TestDictMinimizer::test_basic PASSED\n\n"
        "============================== 3 passed in 0.23s ==============================\n"
    )

    FAILING_RUN = (
        "============================= test session starts ==============================\n"
        "platform linux -- Python 3.12.0, pytest-8.1.0\ncollected 10 items\n\n"
        "tests/test_ptk.py::TestDictMinimizer::test_basic_compact_json PASSED\n"
        "tests/test_ptk.py::TestDictMinimizer::test_aggressive FAILED\n"
        "tests/test_ptk.py::TestListMinimizer::test_tabular FAILED\n\n"
        "=================================== FAILURES ===================================\n"
        "_________________ TestDictMinimizer::test_aggressive _________________\n\n"
        "    def test_aggressive():\n"
        ">       result = ptk.minimize({'a': 1}, aggressive=True)\n"
        "E       AssertionError: assert 'a:1' == '{\"a\":1}'\n\n"
        "tests/test_ptk.py:42: AssertionError\n"
        "=========================== 2 failed, 8 passed in 0.31s ===========================\n"
    )

    def test_pytest_detected_as_log(self):
        assert detect(self.FAILING_RUN) == ContentType.LOG

    def test_passing_run_compresses(self):
        result = ptk.minimize(self.PASSING_RUN, content_type="log")
        assert "PASSED" in result
        assert len(result) < len(self.PASSING_RUN)

    def test_failing_run_keeps_failures(self):
        result = ptk.minimize(self.FAILING_RUN, content_type="log", aggressive=True)
        assert "FAILED" in result
        assert "AssertionError" in result

    def test_failing_run_drops_passing(self):
        result = ptk.minimize(self.FAILING_RUN, content_type="log", aggressive=True)
        lines = [ln.strip() for ln in result.split("\n") if ln.strip()]
        assert not [ln for ln in lines if ln.endswith("PASSED")]


class TestCargoTestOutput:
    CARGO_MIXED = (
        "   Compiling myapp v0.1.0 (/home/user/myapp)\n"
        "    Finished test [unoptimized + debuginfo] target(s) in 2.34s\n"
        "running 8 tests\n"
        "test tests::test_parse_valid ... ok\n"
        "test tests::test_parse_empty ... ok\n"
        "test tests::test_roundtrip ... FAILED\n"
        "test tests::test_edge_case ... FAILED\n\n"
        "failures:\n"
        "---- tests::test_roundtrip stdout ----\n"
        "thread 'tests::test_roundtrip' panicked at 'assertion failed', src/main.rs:42:5\n\n"
        "test result: FAILED. 6 passed; 2 failed; 0 ignored\n"
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
        result = ptk.minimize(self.CARGO_MIXED, content_type="log")
        assert result.count("\n") < self.CARGO_MIXED.count("\n")


class TestGoTestOutput:
    GO_MIXED = (
        "--- PASS: TestParseValid (0.00s)\n"
        "--- PASS: TestParseEmpty (0.00s)\n"
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
        assert "FAIL" in ptk.minimize(self.GO_MIXED, content_type="log", aggressive=True)

    def test_go_passing_lines_removable(self):
        result = ptk.minimize(self.GO_MIXED, content_type="log", aggressive=True)
        lines = [ln.strip() for ln in result.split("\n") if ln.strip()]
        assert not [ln for ln in lines if ln.startswith("--- PASS")]

    def test_go_failure_details_kept(self):
        result = ptk.minimize(self.GO_MIXED, content_type="log", aggressive=True)
        assert "got" in result or "nil pointer" in result
