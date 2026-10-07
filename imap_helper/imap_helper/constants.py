import os
from pathlib import Path

COLORS: dict[str, str] = {
    "red": "\033[31m",
    "green": "\033[32m",
    "blue": "\033[34m",
    "orange": "\033[38;5;208m",
    "yellow": "\033[33m",
    "reset": "\033[0m",
}

SYMBOLS: dict[str, str] = {
    "ok": f"{COLORS['green']}✓{COLORS['reset']}",
    "fail": f"{COLORS['red']}✗{COLORS['reset']}",
    "sync": f"{COLORS['blue']}{COLORS['reset']}",
    "push": f"{COLORS['orange']}{COLORS['reset']}",
    "add": f"{COLORS['green']}+{COLORS['reset']}",
    "prune": f"{COLORS['red']}-{COLORS['reset']}",
}

IMAP_BASE_DIR: Path = Path(os.environ.get("IMAP_BASE_DIR", "~/imap")).expanduser()

IMAP_REPOS = [
    "imap_processing",
    "imap_L3_processing",
    "imap-data-access",
    "sds-data-manager",
    "swapi-tools",
]
