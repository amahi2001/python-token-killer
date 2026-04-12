# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.1.x | ✅ |

## Reporting a Vulnerability

**Please do not file a public GitHub issue for security vulnerabilities.**

Report vulnerabilities privately via [GitHub's private vulnerability reporting](https://github.com/amahi2001/python-token-killer/security/advisories/new).

Include:
- A description of the vulnerability and its potential impact
- Steps to reproduce (code snippet or test case preferred)
- Your assessment of severity (if known)

You'll receive an acknowledgment within 48 hours. If the vulnerability is confirmed, a patch will be released as soon as possible and you'll be credited in the changelog (unless you prefer to stay anonymous).

## Scope

ptk is a pure Python compression library with zero required network calls and no execution of user-provided code. The primary risk surface is:

- **Regex denial-of-service (ReDoS)** — inputs designed to cause catastrophic backtracking. All regexes are precompiled and have been tested against pathological inputs (see `tests/test_adversarial.py::TestRegexSafety`).
- **Circular reference handling** — inputs with circular references are caught and fall back to `str()` gracefully.
- **Dependency vulnerabilities** — tiktoken (optional) is the only non-stdlib dependency. Security updates are automated via Dependabot.
