#!/usr/bin/env python3
"""Log Triage — paste only what matters to your LLM.

CI pipelines produce thousands of log lines. Most are noise.
ptk strips them to just failures and stack traces in milliseconds,
so you can paste directly into Claude or GPT without blowing your context.

Run: python examples/log_triage.py
Or:  cat your_ci.log | python examples/log_triage.py --stdin
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import ptk

# ── Simulated CI log (realistic 10,000-line output condensed) ────────────────

def make_ci_log() -> str:
    lines = []

    # Setup phase — lots of noise
    lines += [
        "##[group]Set up job",
        "Current runner version: '2.314.1'",
        "Operating System: Ubuntu 24.04.1 LTS",
        "Runner Image: ubuntu-24.04",
        "##[endgroup]",
        "##[group]Checkout repo",
        "Syncing repository: amahi2001/python-token-killer",
        "Getting Git version info",
        "Initializing the repository",
        "Setting up auth",
        "Fetching the repository",
        "Determining the checkout info",
        "Checking out the ref",
        "##[endgroup]",
        "##[group]Install uv",
        "Downloading uv 0.11.6",
        "Verifying checksum",
        "Extracting uv",
        "Added uv to PATH",
        "##[endgroup]",
        "##[group]uv sync --locked --only-group test",
    ]

    # Dependency install — verbose but ignorable
    for pkg in ["pytest", "pluggy", "iniconfig", "packaging", "pytest-anyio"]:
        lines.append(f"  Downloading {pkg}...")
        lines.append(f"  Installed {pkg}")

    lines += [
        "Installed 6 packages",
        "##[endgroup]",
        "##[group]Run tests",
        "============================= test session starts ==============================",
        "platform linux -- Python 3.12.8, pytest-9.0.3, pluggy-1.6.0",
        "rootdir: /home/runner/work/python-token-killer",
        "configfile: pyproject.toml",
        "collecting ...",
        "collected 361 items",
        "",
    ]

    # 340 passing tests — repetitive noise
    for i in range(340):
        module = ["test_ptk", "test_adversarial", "test_real_world"][i % 3]
        lines.append(f"tests/{module}.py::TestClass{i % 10}::test_case_{i} PASSED")

    # 2 failures — the only important part
    lines += [
        "tests/test_ptk.py::TestDictMinimizer::test_aggressive_flattens FAILED",
        "tests/test_real_world.py::TestPipelineSimulations::test_cost_pipeline FAILED",
        "",
        "=================================== FAILURES ===================================",
        "______________ TestDictMinimizer.test_aggressive_flattens ______________",
        "",
        "    def test_aggressive_flattens():",
        ">       result = ptk.minimize({'config': {'db': {'host': 'localhost'}}}, aggressive=True)",
        ">       assert 'cfg.db.host' in json.loads(result)",
        "E       AssertionError: 'cfg.db.host' not in {'config.db.host': 'localhost'}",
        "E       Key was flattened but not shortened: 'config' → expected 'cfg'",
        "",
        "tests/test_ptk.py:254: AssertionError",
        "______________ TestPipelineSimulations.test_cost_pipeline ______________",
        "",
        "    def test_cost_pipeline():",
        ">       assert savings > 20",
        "E       AssertionError: assert 18.3 > 20",
        "E       Savings dropped below threshold: 18.3% < 20%",
        "",
        "tests/test_real_world.py:589: AssertionError",
        "",
        "=========================== short test summary info ============================",
        "FAILED tests/test_ptk.py::TestDictMinimizer::test_aggressive_flattens",
        "FAILED tests/test_real_world.py::TestPipelineSimulations::test_cost_pipeline",
        "========================= 2 failed, 359 passed in 2.34s =========================",
    ]

    return "\n".join(lines)


def token_count(text: str) -> int:
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except ImportError:
        return len(text) // 4


def main() -> None:
    log = sys.stdin.read() if "--stdin" in sys.argv else make_ci_log()

    triaged = ptk.minimize(log, content_type="log", aggressive=True)

    orig_tok = token_count(log)
    triage_tok = token_count(triaged)
    saved = round((1 - triage_tok / orig_tok) * 100, 1)
    orig_lines = log.count("\n") + 1
    triage_lines = triaged.count("\n") + 1

    print("=" * 60)
    print("CI Log Triage")
    print("=" * 60)
    print(f"\nOriginal:  {orig_lines:>5} lines   {orig_tok:>5} tokens")
    print(f"Triaged:   {triage_lines:>5} lines   {triage_tok:>5} tokens")
    print(f"Saved:     {saved}% — only failures + stack traces remain")
    print()
    print("── Triaged output (paste this to your LLM) ─────────────")
    print(triaged)
    print("─" * 60)


if __name__ == "__main__":
    main()
