"""Shared pytest configuration — adds src/ to sys.path for all test packages."""

import sys
from pathlib import Path

# Ensure ptk is importable from the src/ layout without installing
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
