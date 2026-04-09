"""Text minimizer — whitespace normalization, stopword removal, abbreviation."""

from __future__ import annotations

import re
from typing import Any

from ptk._base import Minimizer

# ── precompiled ─────────────────────────────────────────────────────────

_MULTI_SPACE = re.compile(r'[ \t]+')
_MULTI_NEWLINE = re.compile(r'\n{3,}')

# high-frequency English stopwords that add tokens but rarely carry meaning
# in LLM context (intentionally conservative — we never want to destroy meaning)
_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "that", "which",
    "who", "whom", "this", "these", "those", "am", "its", "very",
    "just", "also", "really", "quite", "rather",
})

# common long phrases → shorter equivalents
_PHRASE_ABBREVIATIONS: tuple[tuple[str, str], ...] = (
    ("in order to", "to"),
    ("as well as", "&"),
    ("due to the fact that", "because"),
    ("in the event that", "if"),
    ("at this point in time", "now"),
    ("for the purpose of", "to"),
    ("in addition to", "also"),
    ("with regard to", "re:"),
    ("a large number of", "many"),
    ("the majority of", "most"),
    ("in the process of", "while"),
    ("on the other hand", "however"),
    ("take into account", "consider"),
    ("it is important to note that", "note:"),
    ("please note that", "note:"),
    ("it should be noted that", "note:"),
)

# single-word abbreviations (applied via regex word boundaries)
_WORD_ABBREVIATIONS: dict[str, str] = {
    "implementation": "impl",
    "implementations": "impls",
    "configuration": "config",
    "configurations": "configs",
    "production": "prod",
    "development": "dev",
    "environment": "env",
    "environments": "envs",
    "application": "app",
    "applications": "apps",
    "infrastructure": "infra",
    "authentication": "auth",
    "authorization": "authz",
    "repository": "repo",
    "repositories": "repos",
    "documentation": "docs",
    "specification": "spec",
    "specifications": "specs",
    "requirements": "reqs",
    "approximately": "~",
    "notification": "notif",
    "notifications": "notifs",
}

# filler phrases stripped entirely (claw-compactor Abbrev pattern)
_FILLER_PHRASES: tuple[str, ...] = (
    "Furthermore, ",
    "Furthermore,",
    "In addition, ",
    "In addition,",
    "Moreover, ",
    "Moreover,",
    "Additionally, ",
    "Additionally,",
    "Having said that, ",
    "Having said that,",
    "It is worth noting that ",
    "As mentioned earlier, ",
    "As previously stated, ",
)

_WORD_ABBREV_RE = re.compile(
    r'\b(' + '|'.join(re.escape(w) for w in _WORD_ABBREVIATIONS) + r')\b',
    re.IGNORECASE,
)


class TextMinimizer(Minimizer):
    """Compress natural language text for LLM consumption.

    Strategies:
    1. Normalize whitespace (always)
    2. Apply phrase abbreviations (always)
    3. Remove stopwords (aggressive) — safe for context/instructions, not prose
    """

    def _minimize(self, obj: Any, *, aggressive: bool = False, **kw: Any) -> str:
        text = obj if isinstance(obj, str) else str(obj)

        # normalize whitespace
        text = _MULTI_SPACE.sub(" ", text)
        text = _MULTI_NEWLINE.sub("\n\n", text)

        # strip filler phrases
        for filler in _FILLER_PHRASES:
            text = text.replace(filler, "")

        # abbreviate common phrases
        for long, short in _PHRASE_ABBREVIATIONS:
            text = text.replace(long, short)

        # abbreviate common words (case-preserving)
        text = _WORD_ABBREV_RE.sub(_word_abbrev_replace, text)

        if aggressive:
            text = _remove_stopwords(text)

        return text.strip()


def _word_abbrev_replace(m: re.Match[str]) -> str:
    """Replace matched word with its abbreviation, preserving leading case."""
    word = m.group(0)
    abbrev = _WORD_ABBREVIATIONS[word.lower()]
    return abbrev.capitalize() if word[0].isupper() else abbrev


def _remove_stopwords(text: str) -> str:
    """Remove stopwords while preserving line structure."""
    lines: list[str] = []
    for line in text.split("\n"):
        words = line.split()
        filtered = [w for w in words if w.lower().strip(".,;:!?") not in _STOPWORDS]
        lines.append(" ".join(filtered))
    return "\n".join(lines)
