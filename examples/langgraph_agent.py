#!/usr/bin/env python3
"""LangGraph Agent — drop ptk between every tool call and LLM call.

Shows a simulated agent loop where tool outputs are compressed before
re-entering the context window. Token savings are printed at each step.

No LangGraph install needed — the agent loop is simulated so you can
run this and see the numbers immediately.

Run: python examples/langgraph_agent.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import ptk

# ── Simulated tool outputs (realistic shapes from real APIs) ─────────────────

def tool_search_users(query: str) -> dict:
    """Simulates a user search API response."""
    return {
        "query": query,
        "results": [
            {
                "id": i,
                "name": f"User {i}",
                "email": f"user{i}@company.com",
                "department": ["Engineering", "Sales", "Marketing", "Design"][i % 4],
                "title": "Senior Software Engineer" if i % 2 == 0 else None,
                "phone": None,
                "bio": None,
                "avatar_url": None,
                "address": None,
                "metadata": {},
                "permissions": [],
                "last_login": "2024-08-01" if i % 3 == 0 else None,
                "is_active": True,
                "is_verified": i % 5 != 0,
                "created_at": "2023-01-15T10:30:00Z",
                "updated_at": None,
            }
            for i in range(1, 21)
        ],
        "total": 20,
        "page": 1,
        "per_page": 20,
        "next_cursor": None,
        "prev_cursor": None,
        "errors": None,
        "warnings": [],
        "request_id": "req_abc123def456",
        "cache_hit": False,
        "debug": None,
    }


def tool_get_logs(service: str) -> str:
    """Simulates fetching recent service logs."""
    return "\n".join([
        f"2024-08-01T10:00:{i:02d}Z [INFO] Health check passed" if i % 3 != 0
        else f"2024-08-01T10:00:{i:02d}Z [DEBUG] Processing request #{i}"
        for i in range(50)
    ] + [
        "2024-08-01T10:00:51Z [ERROR] Connection timeout to redis:6379",
        "2024-08-01T10:00:51Z [WARN] Retrying (attempt 1/3)",
        "2024-08-01T10:00:52Z [ERROR] Failed after 3 retries — using fallback",
        "Traceback (most recent call last):",
        '  File "/app/cache.py", line 42, in connect',
        "    raise ConnectionError('redis:6379 unreachable')",
        "ConnectionError: redis:6379 unreachable",
    ])


def tool_get_code(module: str) -> str:
    """Simulates reading a source file."""
    return '''"""
User authentication module.

This module handles all aspects of user authentication including login,
logout, token validation, and session management. It is important to note
that all passwords are hashed using bcrypt before storage.
"""

import hashlib
import secrets
import logging
from typing import Optional
from datetime import datetime, timedelta

# Module logger
logger = logging.getLogger(__name__)

# Constants
SESSION_TTL = 3600  # 1 hour
TOKEN_BYTES = 32


class AuthError(Exception):
    """Raised when authentication fails."""
    pass


class SessionExpiredError(AuthError):
    """Raised when a session has expired."""
    pass


class AuthManager:
    """
    Manages user authentication and session lifecycle.

    This class provides the primary interface for all authentication
    operations. Due to the fact that it handles sensitive data, all
    methods validate inputs before processing. Furthermore, all
    authentication failures are logged for security monitoring.
    """

    def __init__(self, db, cache=None):
        """Initialize the auth manager with database and optional cache."""
        self.db = db
        self.cache = cache
        self._failed_attempts = {}

    def login(self, username: str, password: str) -> Optional[str]:
        """Authenticate user and return a session token."""
        # Check rate limiting
        if self._is_rate_limited(username):
            raise AuthError(f"Rate limit exceeded for {username}")

        # Verify credentials
        user = self.db.get_user(username)
        if not user or not self._verify(password, user["hash"]):
            self._record_failure(username)
            raise AuthError("Invalid credentials")

        # Create session
        token = secrets.token_hex(TOKEN_BYTES)
        expiry = datetime.utcnow() + timedelta(seconds=SESSION_TTL)
        self.db.create_session(user["id"], token, expiry)
        if self.cache:
            self.cache.set(f"session:{token}", user["id"], ttl=SESSION_TTL)

        logger.info("User %s logged in", username)
        return token

    def logout(self, token: str) -> bool:
        """Invalidate a session token."""
        if self.cache:
            self.cache.delete(f"session:{token}")
        return self.db.delete_session(token)

    def validate(self, token: str) -> Optional[int]:
        """Return the user ID for a valid token, or None if invalid."""
        if self.cache:
            user_id = self.cache.get(f"session:{token}")
            if user_id:
                return user_id
        session = self.db.get_session(token)
        if not session or session["expiry"] < datetime.utcnow():
            return None
        return session["user_id"]

    def _verify(self, password: str, stored_hash: str) -> bool:
        return hashlib.sha256(password.encode()).hexdigest() == stored_hash

    def _is_rate_limited(self, username: str) -> bool:
        return self._failed_attempts.get(username, 0) >= 5

    def _record_failure(self, username: str) -> None:
        self._failed_attempts[username] = self._failed_attempts.get(username, 0) + 1
'''


# ── Agent loop ───────────────────────────────────────────────────────────────

def simulate_agent_step(step_name: str, tool_fn, *args) -> tuple[str, str]:
    """Run a tool, return (raw_output, compressed_output)."""
    raw = tool_fn(*args)
    if not isinstance(raw, str):
        raw = json.dumps(raw, indent=2)
    compressed = ptk.minimize(raw, aggressive=True)
    return raw, compressed


def token_count(text: str) -> int:
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except ImportError:
        return len(text) // 4


def main() -> None:
    print("=" * 65)
    print("Agent Loop — Token Savings with ptk")
    print("=" * 65)
    print("Each tool call's output is compressed before re-entering context.\n")

    total_raw = 0
    total_compressed = 0

    steps = [
        ("1. Search users",      tool_search_users, "engineering department"),
        ("2. Fetch service logs", tool_get_logs,     "api-gateway"),
        ("3. Read source code",   tool_get_code,     "auth.py"),
    ]

    context_window: list[str] = []

    for step_name, tool_fn, *args in steps:
        raw, compressed = simulate_agent_step(step_name, tool_fn, *args)
        raw_tok = token_count(raw)
        comp_tok = token_count(compressed)
        saved_pct = round((1 - comp_tok / raw_tok) * 100, 1)

        total_raw += raw_tok
        total_compressed += comp_tok
        context_window.append(compressed)

        print(f"  {step_name}")
        print(f"    {raw_tok:>5} tokens  →  {comp_tok:>4} tokens  ({saved_pct}% saved)")

    # Show cumulative context cost
    context_tokens = token_count("\n".join(context_window))
    naive_context = total_raw  # without ptk, all raw outputs in context

    print()
    print(f"  Cumulative context window: {naive_context:,} → {context_tokens:,} tokens")
    print(f"  Total saved: {naive_context - context_tokens:,} tokens "
          f"({round((1 - context_tokens/naive_context)*100,1)}%)")

    # At scale
    cost_raw = naive_context / 1_000_000 * 2.50
    cost_ptk = context_tokens / 1_000_000 * 2.50
    daily = 5_000
    monthly_save = (cost_raw - cost_ptk) * daily * 30
    print(f"\n  At {daily:,} agent runs/day: ~${monthly_save:.2f}/month saved (GPT-4o pricing)")
    print("=" * 65)


if __name__ == "__main__":
    main()
