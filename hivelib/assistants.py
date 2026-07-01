"""Create and focus persistent Codex/Claude assistant tabs."""
from __future__ import annotations

import json
import os
import shutil
import sys
import time

from .util import run


TOOLS = {
    "claude": {
        "label": "Claude",
        "bin": "claude",
        "install": "Install Claude Code, or set HIVE_AGENT_DEFAULT=codex to start Codex first.",
    },
    "codex": {
        "label": "Codex",
        "bin": "codex",
        "install": "Install Codex, or set HIVE_AGENT_DEFAULT=claude to start Claude first.",
    },
}

DEFAULT_ORDER = ("claude", "codex")
VALID_DEFAULTS = ("codex", "claude")


def _available(name: str) -> bool:
    return shutil.which(TOOLS[name]["bin"]) is not None


def _shell() -> str:
    return os.environ.get("SHELL") or "/bin/sh"


def _missing(name: str) -> int:
    tool = TOOLS[name]
    print(f"{tool['label']} is selected, but `{tool['bin']}` is not on PATH.", file=sys.stderr)
    print(tool["install"], file=sys.stderr)
    print(f"Starting {_shell()} so this pane stays available.", file=sys.stderr)
    os.execvp(_shell(), [_shell()])
    return 127  # unreachable


def shell(name: str) -> int:
    """Run one assistant CLI, or leave an explanatory shell if missing."""
    if name not in VALID_DEFAULTS:
        print(f"Invalid assistant {name!r}; expected codex or claude", file=sys.stderr)
        return 2
    if not _available(name):
        return _missing(name)
    os.execvp(TOOLS[name]["bin"], [TOOLS[name]["bin"]])
    return 127  # unreachable


def _tabs() -> list[dict]:
    rc, out = run(["zellij", "action", "list-tabs", "--json"], timeout=2)
    if rc != 0 or not out:
        return []
    try:
        tabs = json.loads(out)
    except json.JSONDecodeError:
        return []
    return tabs if isinstance(tabs, list) else []


def _tab_id(name: str) -> str | None:
    for tab in _tabs():
        tab_name = tab.get("name") or tab.get("tab_name")
        tab_id = tab.get("id") if tab.get("id") is not None else tab.get("tab_id")
        if tab_name == name and tab_id is not None:
            return str(tab_id)
    return None


def _active_tab_name() -> str:
    for tab in _tabs():
        if tab.get("active") or tab.get("is_active") or tab.get("focused"):
            return str(tab.get("name") or tab.get("tab_name") or "")
    rc, out = run(["zellij", "action", "current-tab-info", "--json"], timeout=2)
    if rc != 0 or not out:
        return ""
    try:
        info = json.loads(out)
    except json.JSONDecodeError:
        return ""
    return str(info.get("name") or info.get("tab_name") or "")


def bootstrap() -> int:
    """Focus the configured default assistant tab, then remove the bootstrap tab."""
    default = os.environ.get("HIVE_AGENT_DEFAULT", "claude").strip().lower() or "claude"
    if default not in VALID_DEFAULTS:
        print(f"Invalid HIVE_AGENT_DEFAULT={default!r}; expected codex or claude",
              file=sys.stderr)
        return 2

    bootstrap_id = _tab_id("assistant-start")
    for _ in range(20):
        if _tab_id("claude") and _tab_id("codex"):
            break
        time.sleep(0.1)

    run(["zellij", "action", "go-to-tab-name", default], timeout=5)
    if bootstrap_id:
        run(["zellij", "action", "close-tab", "--tab-id", bootstrap_id], timeout=5)
    return 0


def toggle() -> int:
    """Rotate between the two assistant tabs."""
    active = _active_tab_name()
    target = "codex" if active == "claude" else "claude"
    run(["zellij", "action", "go-to-tab-name", target], timeout=5)
    return 0
