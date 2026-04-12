"""Version control output — git log, git status, near-duplicate lines."""

import ptk


class TestGitLogOutput:
    GIT_LOG = (
        "a1b2c3d fix: handle null bytes in dict keys\n"
        "e4f5g6h feat: add TextMinimizer word abbreviations\n"
        "i7j8k9l test: 169 adversarial tests\n"
        "m1n2o3p fix: pragma preservation in CodeMinimizer\n"
        "q4r5s6t docs: add AGENTS.md and CLAUDE.md\n"
    )

    GIT_STATUS = (
        "On branch main\n"
        "Your branch is up to date with 'origin/main'.\n\n"
        "Changes to be committed:\n"
        '  (use "git restore --staged <file>..." to unstage)\n'
        "\tmodified:   src/ptk/minimizers/_dict.py\n"
        "\tmodified:   src/ptk/minimizers/_code.py\n\n"
        "Untracked files:\n"
        '  (use "git add <file>..." to track)\n'
        "\tbenchmarks/samples/new_sample.json\n"
    )

    def test_git_log_compresses(self):
        assert isinstance(ptk.minimize(self.GIT_LOG, content_type="log"), str)

    def test_git_log_all_commits_preserved(self):
        result = ptk.minimize(self.GIT_LOG, content_type="log")
        assert "fix:" in result
        assert "feat:" in result

    def test_git_status_compresses(self):
        result = ptk.minimize(self.GIT_STATUS, content_type="log")
        assert len(result) < len(self.GIT_STATUS)

    def test_git_status_files_preserved(self):
        result = ptk.minimize(self.GIT_STATUS, content_type="log")
        assert "_dict.py" in result or "_code.py" in result


class TestNearDuplicates:
    NEAR_DUPE_LOGS = (
        "2024-01-01T10:00:01Z [INFO] Request from 192.168.1.100 completed in 234ms\n"
        "2024-01-01T10:00:02Z [INFO] Request from 192.168.1.101 completed in 241ms\n"
        "2024-01-01T10:00:03Z [INFO] Request from 192.168.1.102 completed in 229ms\n"
        "2024-01-01T10:00:06Z [ERROR] Request from 192.168.1.105 failed with 500\n"
    )

    def test_exact_dupes_collapse(self):
        log = "[INFO] heartbeat ok\n" * 5 + "[ERROR] crash"
        assert "(x5)" in ptk.minimize(log, content_type="log")

    def test_near_dupes_preserved(self):
        result = ptk.minimize(self.NEAR_DUPE_LOGS, content_type="log")
        assert result.count("\n") >= 3

    def test_near_dupes_error_filtered_aggressive(self):
        result = ptk.minimize(self.NEAR_DUPE_LOGS, content_type="log", aggressive=True)
        assert "ERROR" in result or "failed" in result.lower()
