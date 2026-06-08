"""Small shared helpers: ANSI colour, time/string formatting, process checks."""
from __future__ import annotations

import sys
import time
import subprocess

# ANSI SGR codes used across the UI.
DIM, BOLD = "2", "1"
GREEN, YELLOW, CYAN, RED = "32", "33", "36", "31"

_STDOUT_TTY = sys.stdout.isatty()


def color(code: str, s: object) -> str:
    """Colour `s` only when stdout is a terminal (for direct output like fleet)."""
    return f"\033[{code}m{s}\033[0m" if _STDOUT_TTY else str(s)


def paint(code: str, s: object) -> str:
    """Always colour `s`. Use for output rendered by fzf (preview/list) or panes,
    where stdout is a pipe but ANSI is still interpreted."""
    return f"\033[{code}m{s}\033[0m"


def human_age(ms: float | None) -> str:
    """Milliseconds-since-epoch start time -> compact age like 3m, 1h08m, 2d04h."""
    if not ms:
        return "—"
    secs = max(0, int(time.time() - ms / 1000))
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m"
    if secs < 86400:
        return f"{secs // 3600}h{(secs % 3600) // 60:02d}m"
    return f"{secs // 86400}d{(secs % 86400) // 3600:02d}h"


def trunc(s: object, n: int) -> str:
    text = str(s).replace("\n", " ").replace("\t", " ").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def run(cmd: list[str], timeout: float | None = None) -> tuple[int, str]:
    """Run a command; return (returncode, stdout stripped). Never raises."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip()
    except Exception:
        return 1, ""


def proc_alive(needle: str | None) -> bool:
    """True if any process command line contains `needle` (pgrep -f)."""
    if not needle:
        return False
    rc, _ = run(["pgrep", "-f", needle], timeout=1.5)
    return rc == 0
