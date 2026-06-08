"""Project discovery for the `open`/`switch` pickers (mirrors the old `proj`)."""
from __future__ import annotations

import os
import re

HOME = os.path.expanduser("~")


def roots() -> list[str]:
    """Project root dirs (colon-separated PROJ_ROOTS, default ~/projects)."""
    raw = os.environ.get("PROJ_ROOTS") or os.path.join(HOME, "projects")
    return [p for p in raw.split(":") if p]


def sanitize(path: str) -> str:
    """zellij session names allow [A-Za-z0-9_-]; map everything else to '_'."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", os.path.basename(path.rstrip("/")))


def list_projects() -> list[str]:
    """Immediate subdirectories of every root, sorted, as absolute paths."""
    out: list[str] = []
    for root in roots():
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            p = os.path.join(root, name)
            if os.path.isdir(p):
                out.append(p)
    return out
