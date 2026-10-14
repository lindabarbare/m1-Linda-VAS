"""Backlog-compatible entry point for the root accessibility checker."""
from pathlib import Path
import runpy


checker = Path(__file__).resolve().parents[1] / "a11y_check.py"
runpy.run_path(str(checker), run_name="__main__")
