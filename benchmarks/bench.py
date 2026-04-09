#!/usr/bin/env python3
"""ptk benchmark suite — real token counts via tiktoken.

Run: python benchmarks/bench.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import tiktoken

import ptk

enc = tiktoken.get_encoding("cl100k_base")
SAMPLES = Path(__file__).resolve().parent / "samples"


def count_tokens(text: str) -> int:
    return len(enc.encode(text))


def bench(name: str, obj: object, *, content_type: str | None = None) -> dict:
    """Run a single benchmark and return results."""
    original_str = json.dumps(obj, indent=2, default=str) if isinstance(obj, (dict, list)) else str(obj)
    orig_tokens = count_tokens(original_str)

    # default mode
    start = time.perf_counter_ns()
    default_out = ptk.minimize(obj, content_type=content_type)
    default_ns = time.perf_counter_ns() - start
    default_tokens = count_tokens(default_out)

    # aggressive mode
    start = time.perf_counter_ns()
    aggro_out = ptk.minimize(obj, aggressive=True, content_type=content_type)
    aggro_ns = time.perf_counter_ns() - start
    aggro_tokens = count_tokens(aggro_out)

    return {
        "name": name,
        "original_tokens": orig_tokens,
        "default_tokens": default_tokens,
        "default_savings_pct": round((1 - default_tokens / orig_tokens) * 100, 1) if orig_tokens else 0,
        "default_us": round(default_ns / 1000),
        "aggressive_tokens": aggro_tokens,
        "aggressive_savings_pct": round((1 - aggro_tokens / orig_tokens) * 100, 1) if orig_tokens else 0,
        "aggressive_us": round(aggro_ns / 1000),
    }


def main() -> None:
    print(f"ptk v{ptk.__version__} benchmark (tiktoken cl100k_base)\n")
    print(f"{'Benchmark':<30} {'Original':>8} {'Default':>8} {'Saved':>7} {'Aggro':>8} {'Saved':>7} {'Time':>8}")
    print("-" * 92)

    results: list[dict] = []

    # 1. API response (JSON)
    api_data = json.loads((SAMPLES / "api_response.json").read_text())
    results.append(bench("API response (JSON)", api_data))

    # 2. Python module (code)
    code = (SAMPLES / "python_module.py").read_text()
    results.append(bench("Python module (code)", code, content_type="code"))

    # 3. Signatures-only mode
    results.append(bench("Python module (sigs)", code, content_type="code"))
    # override with signatures mode
    sig_out = ptk.minimize(code, content_type="code", mode="signatures")
    sig_tokens = count_tokens(sig_out)
    orig_tokens = results[-1]["original_tokens"]
    results[-1]["aggressive_tokens"] = sig_tokens
    results[-1]["aggressive_savings_pct"] = round((1 - sig_tokens / orig_tokens) * 100, 1)

    # 4. Server log
    log = (SAMPLES / "server_log.txt").read_text()
    results.append(bench("Server log (58 lines)", log, content_type="log"))

    # 5. List of records
    records = [
        {"id": i, "name": f"user_{i}", "email": f"u{i}@company.com",
         "active": i % 3 != 0, "role": ["admin", "member", "viewer"][i % 3],
         "last_login": None if i % 4 == 0 else f"2024-08-0{(i%9)+1}"}
        for i in range(50)
    ]
    results.append(bench("50 user records (list)", records))

    # 6. Verbose text
    text = (
        "Furthermore, the implementation of the distributed architecture requires "
        "extensive experience in infrastructure management and database configuration. "
        "In addition, the development team should have approximately 5 years of "
        "experience with Kubernetes and continuous integration. "
        "Moreover, the documentation for all applications must be updated regularly. "
        "The production environment is located in the headquarters offices. "
        "Authentication and authorization are handled by the security module. "
        "The repository contains the complete specification and requirements for "
        "the deployment process. It is important to note that the configuration "
        "of the environment must be reviewed before each release."
    )
    results.append(bench("Verbose paragraph (text)", text, content_type="text"))

    # print table
    for r in results:
        print(
            f"{r['name']:<30} "
            f"{r['original_tokens']:>8} "
            f"{r['default_tokens']:>8} "
            f"{r['default_savings_pct']:>6.1f}% "
            f"{r['aggressive_tokens']:>8} "
            f"{r['aggressive_savings_pct']:>6.1f}% "
            f"{r['default_us']:>6}μs"
        )

    # summary
    total_orig = sum(r["original_tokens"] for r in results)
    total_default = sum(r["default_tokens"] for r in results)
    total_aggro = sum(r["aggressive_tokens"] for r in results)
    print("-" * 92)
    print(
        f"{'TOTAL':<30} "
        f"{total_orig:>8} "
        f"{total_default:>8} "
        f"{(1 - total_default / total_orig) * 100:>6.1f}% "
        f"{total_aggro:>8} "
        f"{(1 - total_aggro / total_orig) * 100:>6.1f}%"
    )
    print("\nAll benchmarks use tiktoken cl100k_base (GPT-4/Claude tokenizer).")


if __name__ == "__main__":
    main()
