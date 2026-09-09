import os
from pathlib import Path

COLORS: dict[str, str] = {
    "red": "\033[31m",
    "green": "\033[32m",
    "blue": "\033[34m",
    "yellow": "\033[33m",
    "reset": "\033[0m",
}

PROGRESS_SYMBOLS: dict[str, str] = {
    "ok": f"{COLORS['green']}✓{COLORS['reset']}",
    "fail": f"{COLORS['red']}✗{COLORS['reset']}",
}

IMAP_BASE_DIR: Path = Path(os.environ.get("IMAP_BASE_DIR", "~/imap")).expanduser()

IMAP_REPOS = [
    "imap_processing",
    "imap_L3_processing",
    "imap-data-access",
    "sds-data-manager",
]
