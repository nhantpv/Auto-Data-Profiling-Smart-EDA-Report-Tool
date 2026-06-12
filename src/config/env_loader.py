from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_project_dotenv(project_root: Path | None = None) -> bool:
    """Load local .env once per process without overriding real environment vars."""
    root = project_root or Path(__file__).resolve().parents[2]
    return load_dotenv(dotenv_path=root / ".env", override=False)
