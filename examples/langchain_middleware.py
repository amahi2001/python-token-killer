#!/usr/bin/env python3
"""LangChain/LangGraph integration — minimize tool outputs before they reach the LLM.

This example shows how to use ptk as a post-processing step in a LangGraph
workflow to reduce token usage from tool calls (API responses, code lookups, etc.)

Requirements: pip install python-token-killer langchain-core langgraph
"""

from __future__ import annotations

import ptk

# ── Option 1: Simple function node for LangGraph ────────────────────────

def minimize_context(state: dict) -> dict:
    """LangGraph node that compresses tool output before the next LLM call."""
    if "tool_output" in state:
        state["tool_output"] = ptk.minimize(state["tool_output"], aggressive=True)
    return state


# Usage in a LangGraph workflow:
#
#   from langgraph.graph import StateGraph
#
#   graph = StateGraph(AgentState)
#   graph.add_node("call_tool", call_tool_node)
#   graph.add_node("compress", minimize_context)     # <-- ptk node
#   graph.add_node("agent", agent_node)
#
#   graph.add_edge("call_tool", "compress")
#   graph.add_edge("compress", "agent")


# ── Option 2: Callable wrapper for any retriever output ─────────────────

class TokenMinimizer:
    """Wraps any callable and minimizes its output.

    Works with LangChain retrievers, tool functions, or any callable
    that returns data destined for an LLM context window.
    """

    def __init__(self, fn: callable, *, aggressive: bool = False, **ptk_kwargs):
        self.fn = fn
        self.aggressive = aggressive
        self.ptk_kwargs = ptk_kwargs

    def __call__(self, *args, **kwargs):
        result = self.fn(*args, **kwargs)
        return ptk.minimize(result, aggressive=self.aggressive, **self.ptk_kwargs)


# Usage:
#
#   from langchain_community.tools import DuckDuckGoSearchResults
#   search = DuckDuckGoSearchResults()
#   compressed_search = TokenMinimizer(search.invoke, aggressive=True)
#   results = compressed_search("python async best practices")


# ── Option 3: Minimize a batch of documents ─────────────────────────────

def minimize_docs(docs: list[dict], *, aggressive: bool = False) -> str:
    """Minimize a list of retrieved documents into a compact context block.

    Each document is expected to have 'content' and optional 'metadata' keys.
    Returns a single string ready for injection into an LLM prompt.
    """
    cleaned = []
    for doc in docs:
        content = ptk.minimize(doc.get("content", ""), aggressive=aggressive)
        source = doc.get("metadata", {}).get("source", "unknown")
        cleaned.append(f"[{source}] {content}")
    return "\n\n".join(cleaned)


# ── Demo ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # simulate a tool returning a JSON API response
    tool_output = {
        "results": [
            {"id": i, "title": f"Document {i}", "body": f"Content for document {i}",
             "author": None, "tags": [], "metadata": {}}
            for i in range(20)
        ],
        "total": 20,
        "page": 1,
        "errors": None,
    }

    original = ptk.stats(tool_output)
    print(f"Original:  {original['original_tokens']} tokens")
    print(f"Minimized: {original['minimized_tokens']} tokens ({original['savings_pct']}% saved)")
    print(f"\nOutput:\n{original['output'][:500]}...")
