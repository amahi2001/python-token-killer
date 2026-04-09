## What

<!-- One sentence: what does this PR do? -->

## Why

<!-- What problem does it solve? Link to issue if applicable. -->

## Type of Change

- [ ] Bug fix
- [ ] New minimizer
- [ ] Improvement to existing minimizer
- [ ] Documentation
- [ ] Tests
- [ ] Other: <!-- describe -->

## Checklist

- [ ] `make check` passes (lint + typecheck + tests)
- [ ] New code has tests in `test_ptk.py` (feature) and/or `test_adversarial.py` (edge cases)
- [ ] No new required dependencies added (optional extras are fine)
- [ ] Docstrings on new public classes/methods
- [ ] CHANGELOG.md updated under `[Unreleased]` if user-facing

## For New Minimizers Only

- [ ] Detection heuristic added to `_types.py`
- [ ] Registered in `_ROUTER` in `__init__.py`
- [ ] Exported from `minimizers/__init__.py`
- [ ] Sample input added to `TestAPIContracts.SAMPLE_INPUTS`
- [ ] Content type mismatch test added
- [ ] Benchmark data included in PR description
