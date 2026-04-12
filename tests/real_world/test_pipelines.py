"""End-to-end pipeline simulations — RAG, agent loops, log triage."""

import ptk


class TestPipelineSimulations:
    def test_langgraph_tool_output_pipeline(self):
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
        code = "\n".join(
            f"def function_{i}(x: int, y: str = 'default') -> bool:\n"
            f"    # Implementation detail {i}\n"
            f"    return x > 0  # {i}"
            for i in range(20)
        )
        sigs = ptk.minimize(code, content_type="code", mode="signatures")
        assert sigs.count("def function_") == 20
        assert "Implementation detail" not in sigs
        assert len(sigs) < len(code) * 0.6

    def test_log_triage_pipeline(self):
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
        assert len(result) < len(ci_log) * 0.2
