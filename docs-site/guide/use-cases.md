# Use Cases

## RAG pipelines

Your retriever returns full documents. The chunks carry metadata scaffolding, null fields, and repeated structure the LLM doesn't need.

Drop `ptk` between retrieval and prompt assembly:

```python
import ptk

def build_context(docs: list[dict]) -> str:
    chunks = []
    for doc in docs:
        content = ptk.minimize(doc["content"])
        chunks.append(f"[{doc['source']}]\n{content}")
    return "\n\n---\n\n".join(chunks)
```

Each chunk passes through the right minimizer automatically. A JSON document strips nulls. A code snippet loses its comments. A log chunk keeps only errors.

Full demo with token counts: [`examples/rag_pipeline.py`](https://github.com/amahi2001/python-token-killer/blob/main/examples/rag_pipeline.py)

---

## LangGraph / LangChain

Tool outputs accumulate in the message list between nodes. By the time you call the LLM again, the context window carries the full raw output of every tool — timestamps, null fields, repeated headers.

Add a compression node between the tool call and the next LLM call:

```python
import ptk

def compress_tool_output(state: dict) -> dict:
    state["messages"][-1]["content"] = ptk.minimize(
        state["messages"][-1]["content"], aggressive=True
    )
    return state
```

Wire it into your graph:

```python
from langgraph.graph import StateGraph

graph = StateGraph(AgentState)
graph.add_node("tools", tool_node)
graph.add_node("compress", compress_tool_output)   # ← insert here
graph.add_node("agent", agent_node)

graph.add_edge("tools", "compress")
graph.add_edge("compress", "agent")
```

`aggressive=True` strips timestamps, deduplicates repeated lines, and extracts only error messages from log-shaped outputs. On a tool that returns CI output, this cuts 80%+ of tokens before they reach the next LLM call.

Full agent loop demo: [`examples/langgraph_agent.py`](https://github.com/amahi2001/python-token-killer/blob/main/examples/langgraph_agent.py)

---

## CI log triage

A failing CI run produces 10,000 lines. The LLM needs the 40 lines that failed. Everything else is noise.

```python
import ptk

with open("ci-output.log") as f:
    ci_log = f.read()

errors = ptk.minimize(ci_log, content_type="log", aggressive=True)
# Keeps: ERROR lines, CRITICAL lines, stack traces, test failure summaries.
# Drops: INFO, DEBUG, passed tests, progress bars, timestamps.
```

At 83% savings on a typical CI log, you fit 6x more diagnostic runs into one context window — useful for an agent that diagnoses flaky tests across multiple runs.

Demo with before/after diff: [`examples/log_triage.py`](https://github.com/amahi2001/python-token-killer/blob/main/examples/log_triage.py)

---

## Pasting into ChatGPT / Claude

You're debugging a production issue and want to paste context into a chat window. The raw API response or log is too long.

Run it through ptk first:

```python
import ptk

compressed = ptk.minimize(raw_context)
print(compressed)
# Paste this instead
```

Or check your savings before pasting:

```python
result = ptk.stats(raw_context)
print(f"{result['savings_pct']:.0f}% saved — paste {result['minimized_tokens']} tokens instead of {result['original_tokens']}")
```

This fits more context into the free-tier context window and speeds up the response.

---

## Compressing code before review

You want an LLM to review a module but the full source is too long. Extract just the signatures:

```python
import ptk

with open("src/ptk/minimizers/_dict.py") as f:
    source = f.read()

signatures = ptk.minimize(source, mode="signatures")
# Returns: class DictMinimizer(Minimizer): / def _minimize(self, obj, **kw) → str: / ...
```

The LLM sees the full public interface without reading every implementation line. This cuts 89% on a typical module.
