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

_CODE_MARKERS = frozenset({
    "def ", "class ", "import ", "from ", "function ", "const ", "let ",
    "var ", "public ", "private ", "async ", "await ", "return ",
    "if __name__", "#!/", "package ", "func ", "fn ", "impl ",
    "module ", "export ", "interface ", "struct ",
})

_DIFF_PREFIXES = ("diff --git", "---", "+++", "@@")

_LOG_PATTERNS = frozenset({
    "[INFO]", "[WARN]", "[ERROR]", "[DEBUG]", "[TRACE]",
    " INFO ", " WARN ", " ERROR ", " DEBUG ", " TRACE ",
    "INFO:", "WARN:", "ERROR:", "DEBUG:", "TRACE:",
    "WARNING:", "CRITICAL:",
})


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

    # diff detection — very specific prefix patterns
    if any(head.startswith(p) or f"\n{p}" in head for p in _DIFF_PREFIXES) and "@@" in head:
        return ContentType.DIFF

    # log detection — any log-level marker in first chunk
    if any(m in head for m in _LOG_PATTERNS):
        return ContentType.LOG

    # code detection — any code keyword at start of a line
    lines = head.split("\n", 30)  # only check first ~30 lines
    for line in lines:
        stripped = line.lstrip()
        if any(stripped.startswith(k) for k in _CODE_MARKERS):
            return ContentType.CODE

    return ContentType.TEXT
