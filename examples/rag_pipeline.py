#!/usr/bin/env python3
"""RAG Pipeline — compress retrieved documents before they enter the prompt.

This is the highest-value use case for ptk in production.
Every RAG system retrieves full documents; most of those tokens are structural
noise (nulls, metadata, boilerplate). ptk strips them before they hit the LLM.

Run: python examples/rag_pipeline.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import ptk

# ── Simulated retrieval results (realistic shape) ────────────────────────────
# In production these come from your vector DB (Pinecone, Weaviate, pgvector…)

RETRIEVED_DOCS = [
    {
        "id": "doc_001",
        "score": 0.94,
        "source": "engineering-wiki/deployment.md",
        "content": """# Deployment Guide

## Overview

This document describes the deployment process for the main application service.
It is important to note that all deployments must go through the CI/CD pipeline.

## Prerequisites

In order to deploy, you need access to the production environment.
Furthermore, you must have the configuration set up on your local machine.
Due to the fact that deployments affect live traffic, all changes should be
reviewed by at least one other engineer before proceeding.

## Steps

1. Run `make build` to build the Docker image
2. Push to the container registry: `docker push registry.example.com/app:latest`
3. Apply the Kubernetes manifests: `kubectl apply -f k8s/`
4. Monitor rollout: `kubectl rollout status deployment/app`

## Rollback

In the event that a deployment fails, run:
`kubectl rollout undo deployment/app`
""",
        "metadata": {
            "author": None,
            "last_updated": "2024-08-01",
            "tags": [],
            "department": None,
            "review_status": None,
            "word_count": 142,
        },
    },
    {
        "id": "doc_002",
        "score": 0.89,
        "source": "runbooks/database-failover.md",
        "content": """# Database Failover Runbook

## When to Use This

Use this runbook in the event that the primary database becomes unavailable.

## Automatic Failover

The majority of failover scenarios are handled automatically by RDS.
Having said that, manual intervention may be required if the automatic
failover does not complete within 60 seconds.

## Manual Failover Steps

1. Check current primary: `aws rds describe-db-instances`
2. Promote replica: `aws rds promote-read-replica --db-instance-identifier replica-1`
3. Update connection string in Secrets Manager
4. Restart application pods: `kubectl rollout restart deployment/app`

## Verification

Monitor these metrics for 10 minutes after failover:
- Query latency (should return to baseline within 2 minutes)
- Error rate (should drop to < 0.1% within 30 seconds)
- Connection pool utilization (should stabilize below 80%)
""",
        "metadata": {
            "author": "ops-team",
            "last_updated": "2024-07-15",
            "tags": ["database", "ops"],
            "department": None,
            "review_status": None,
            "word_count": 168,
        },
    },
    {
        "id": "doc_003",
        "score": 0.81,
        "source": "engineering-wiki/on-call.md",
        "content": """# On-Call Guide

## Responsibilities

The on-call engineer is responsible for responding to production incidents.
It is worth noting that response time SLAs are: P0 = 5 min, P1 = 15 min, P2 = 1 hour.

## Tools

- PagerDuty: incident routing
- Datadog: metrics and alerting
- Grafana: dashboards
- Runbook index: https://wiki.internal/runbooks

## Escalation

Furthermore, if an incident cannot be resolved within 30 minutes,
escalate to the on-call manager. Additionally, for any customer-facing
impact, notify #incidents in Slack immediately.
""",
        "metadata": {
            "author": None,
            "last_updated": None,
            "tags": [],
            "department": "engineering",
            "review_status": "draft",
            "word_count": None,
        },
    },
]


def build_context_naive(docs: list[dict]) -> str:
    """Naive approach: dump everything as-is."""
    import json

    return json.dumps(docs, indent=2)


def build_context_with_ptk(docs: list[dict]) -> str:
    """ptk approach: compress each doc, strip metadata noise."""
    chunks = []
    for doc in docs:
        # compress the content (text abbreviation, filler removal)
        compressed = ptk.minimize(doc["content"], content_type="text")
        # strip nullish metadata
        meta = ptk.minimize(doc["metadata"])

        chunks.append(
            f"[Source: {doc['source']} | Relevance: {doc['score']:.0%}]\n{compressed}\nMeta: {meta}"
        )
    return "\n\n---\n\n".join(chunks)


def main() -> None:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")

        def count(text: str) -> int:
            return len(enc.encode(text))
    except ImportError:

        def count(text: str) -> int:  # type: ignore[misc]
            return len(text) // 4  # ~4 chars/token heuristic

    naive = build_context_naive(RETRIEVED_DOCS)
    compressed = build_context_with_ptk(RETRIEVED_DOCS)

    naive_tokens = count(naive)
    compressed_tokens = count(compressed)
    saved = round((1 - compressed_tokens / naive_tokens) * 100, 1)

    print("=" * 60)
    print("RAG Context: Before vs After ptk")
    print("=" * 60)

    print("\n── NAIVE (raw JSON dump) ──────────────────────────────")
    print(f"Tokens: {naive_tokens:,}")
    print(f"Preview:\n{naive[:400]}...\n")

    print("── WITH ptk ───────────────────────────────────────────")
    print(f"Tokens: {compressed_tokens:,}")
    print(f"Preview:\n{compressed[:400]}...\n")

    print("=" * 60)
    print(f"Saved {saved}% ({naive_tokens:,} → {compressed_tokens:,} tokens)")
    print(f"That's {naive_tokens - compressed_tokens:,} tokens per query.")
    print("=" * 60)

    # Cost estimate (GPT-4o: $2.50 per 1M input tokens)
    cost_before = naive_tokens / 1_000_000 * 2.50
    cost_after = compressed_tokens / 1_000_000 * 2.50
    print("\nAt GPT-4o pricing ($2.50/1M tokens):")
    print(f"  Before: ${cost_before:.5f} per query")
    print(f"  After:  ${cost_after:.5f} per query")
    daily_queries = 10_000
    monthly_savings = (cost_before - cost_after) * daily_queries * 30
    print(f"  At {daily_queries:,} queries/day: ${monthly_savings:.2f}/month saved")


if __name__ == "__main__":
    main()
