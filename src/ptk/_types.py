"""Content type detection — pure builtins, no deps."""

from __future__ import annotations

from enum import Enum, auto


class ContentType(Enum):
    DICT = auto()
    LIST = auto()
    CODE = auto()
    LOG = auto()
    DIFF = auto()
    TEXT = auto()


# ── fast heuristics (order matters — first match wins) ──────────────────

_CODE_MARKERS = frozenset(
    {
        "def ",
        "class ",
        "import ",
        "from ",
        "function ",
        "const ",
        "let ",
        "var ",
        "public ",
        "private ",
        "async ",
        "await ",
        "return ",
        "if __name__",
        "#!/",
        "package ",
        "func ",
        "fn ",
        "impl ",
        "module ",
        "export ",
        "interface ",
        "struct ",
    }
)

_LOG_PATTERNS = frozenset(
    {
        # structured log levels
        "[INFO]",
        "[WARN]",
        "[ERROR]",
        "[DEBUG]",
        "[TRACE]",
        " INFO ",
        " WARN ",
        " ERROR ",
        " DEBUG ",
        " TRACE ",
        "INFO:",
        "WARN:",
        "ERROR:",
        "DEBUG:",
        "TRACE:",
        "WARNING:",
        "CRITICAL:",
        # test runner output (pytest, cargo test, go test, jest)
        "PASSED",
        "FAILED",
        "ERRORS",
        "--- PASS:",
        "--- FAIL:",  # go test
        "test result: ",  # cargo test
        " passed",
        " failed",  # pytest summary
        "✓",
        "✗",
        "✕",  # jest / vitest
    }
)


def _looks_like_diff(head: str) -> bool:
    """Detect unified diff format. Requires @@ hunk header + file headers or diff --git."""
    if "@@" not in head:
        return False
    # strong signal: diff --git header
    if head.startswith("diff --git") or "\ndiff --git" in head:
        return True
    # also accept: --- line followed by +++ line (unified diff without git header)
    has_minus = head.startswith("--- ") or "\n--- " in head
    has_plus = "\n+++ " in head
    return has_minus and has_plus


def detect(obj: object) -> ContentType:
    """Detect content type from a Python object. O(1) for non-str types."""
    if isinstance(obj, dict):
        return ContentType.DICT
    if isinstance(obj, (list, tuple)):
        return ContentType.LIST
    if not isinstance(obj, str):
        # fallback: stringify anything else and treat as text
        return ContentType.TEXT

    # ── string heuristics (check first ~2KB for speed) ──────────────
    head = obj[:2048]

    # diff detection — requires real unified diff structure, not just --- or @@
    if _looks_like_diff(head):
        return ContentType.DIFF

    # log detection runs BEFORE code — log patterns are more specific.
    # e.g. pytest output contains 'def test_foo():' which would trigger
    # code detection, but the PASSED/FAILED markers identify it as log first.
    if any(m in head for m in _LOG_PATTERNS):
        return ContentType.LOG

    # code detection — any code keyword at start of a line
    lines = head.split("\n", 30)  # only check first ~30 lines
    for line in lines:
        stripped = line.lstrip()
        if any(stripped.startswith(k) for k in _CODE_MARKERS):
            return ContentType.CODE

    return ContentType.TEXT
