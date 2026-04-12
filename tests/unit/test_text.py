"""TextMinimizer tests — phrase/word abbreviation, filler removal, stopwords."""

import ptk


class TestTextMinimizer:
    LONG_TEXT = (
        "Furthermore, the implementation of the distributed architecture requires "
        "extensive experience in infrastructure management and database configuration. "
        "In addition, the development team should have approximately 5 years of "
        "experience with Kubernetes and continuous integration. "
        "Moreover, the documentation for all applications must be updated regularly. "
        "The production environment is located in the headquarters offices. "
        "Authentication and authorization are handled by the security module. "
        "The repository contains the complete specification and requirements for "
        "the deployment process."
    )

    # ── whitespace normalization ──
    def test_normalizes_spaces(self):
        assert "    " not in ptk.minimize("hello    world", content_type="text")

    def test_normalizes_newlines(self):
        assert "\n\n\n" not in ptk.minimize("hello\n\n\n\n\ngoodbye", content_type="text")

    # ── phrase abbreviation ──
    def test_abbreviates_phrases(self):
        text = "in order to do this, due to the fact that we need it"
        result = ptk.minimize(text, content_type="text")
        assert "in order to" not in result
        assert "to do this" in result

    # ── word abbreviation ──
    def test_abbreviates_implementation(self):
        assert "impl" in ptk.minimize(
            "The implementation of config management.", content_type="text"
        )

    def test_abbreviates_configuration(self):
        assert "config" in ptk.minimize("The configuration is complex.", content_type="text")

    def test_abbreviates_production(self):
        assert "prod" in ptk.minimize("Deploy to production now.", content_type="text")

    def test_abbreviates_infrastructure(self):
        assert "infra" in ptk.minimize("The infrastructure needs updates.", content_type="text")

    def test_preserves_case_on_abbreviation(self):
        assert "Impl" in ptk.minimize("Implementation is key.", content_type="text")

    # ── filler removal ──
    def test_removes_furthermore(self):
        assert "Furthermore," not in ptk.minimize(
            "Furthermore, the system works well.", content_type="text"
        )

    def test_removes_in_addition(self):
        assert "In addition," not in ptk.minimize("In addition, it scales.", content_type="text")

    def test_removes_moreover(self):
        assert "Moreover," not in ptk.minimize("Moreover, the team is ready.", content_type="text")

    def test_removes_additionally(self):
        assert "Additionally," not in ptk.minimize(
            "Additionally, we need backups.", content_type="text"
        )

    # ── compression ──
    def test_long_text_gets_compressed(self):
        assert ptk.stats(self.LONG_TEXT, content_type="text")["savings_pct"] > 0

    # ── aggressive stopword removal ──
    def test_aggressive_removes_stopwords(self):
        text = "the quick brown fox is very fast and also quite nimble"
        result = ptk.minimize(text, content_type="text", aggressive=True)
        assert "the" not in result.split()
        assert "very" not in result.split()
        assert "quick" in result
        assert "fox" in result

    # ── edge cases ──
    def test_empty_text(self):
        assert ptk.minimize("", content_type="text") == ""

    def test_unicode_preserved(self):
        result = ptk.minimize("中文内容 English content 日本語", content_type="text")
        assert "中文" in result
        assert "English" in result

    def test_does_not_abbreviate_code(self):
        """CodeMinimizer should NOT do word abbreviation."""
        assert "implementation" in ptk.minimize("def implementation(): pass", content_type="code")
