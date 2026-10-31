"""Create and focus persistent default-assistant tabs."""
from __future__ import annotations

import json
import os
import re
import shutil
import sys

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


def _tab_name(tab: dict) -> str:
    return str(tab.get("name") or tab.get("tab_name") or "")


def _active_tab_name() -> str:
    for tab in _tabs():
        if tab.get("active") or tab.get("is_active") or tab.get("focused"):
            return _tab_name(tab)
    rc, out = run(["zellij", "action", "current-tab-info", "--json"], timeout=2)
    if rc != 0 or not out:
        return ""
    try:
        info = json.loads(out)
    except json.JSONDecodeError:
        return ""
    return _tab_name(info)


def _default() -> str | None:
    default = os.environ.get("HIVE_AGENT_DEFAULT", "claude").strip().lower() or "claude"
    if default not in VALID_DEFAULTS:
        print(f"Invalid HIVE_AGENT_DEFAULT={default!r}; expected codex or claude",
              file=sys.stderr)
        return None
    return default


def _assistant_tabs(name: str) -> list[str]:
    names = [_tab_name(tab) for tab in _tabs()]
    return [n for n in names if n == name or n.startswith(f"{name}:")]


def _next_tab_name(name: str) -> str:
    nums = []
    for tab in _assistant_tabs(name):
        if tab == name:
            nums.append(1)
            continue
        match = re.fullmatch(rf"{re.escape(name)}:(\d+)", tab)
        if match:
            nums.append(int(match.group(1)))
    return f"{name}:{(max(nums) + 1) if nums else 1}"


def _close_bootstrap() -> None:
    bootstrap_id = _tab_id("assistant-start")
    if bootstrap_id:
        run(["zellij", "action", "close-tab", "--tab-id", bootstrap_id], timeout=5)


def spawn() -> int:
    """Create another tab running HIVE_AGENT_DEFAULT."""
    default = _default()
    if default is None:
        return 2
    tab_name = _next_tab_name(default)
    tool = TOOLS[default]
    label = f"{tool['label']} {tab_name.rsplit(':', 1)[-1]}"
    args = ["zellij", "action", "new-tab", "--layout", "hive-assistant", "--name", tab_name, "-c", os.getcwd(), "--",
            "hive", "pane", label, "hive", "assistant-shell", default]
    rc, _ = run(args, timeout=5)
    if rc != 0:
        return rc
    _close_bootstrap()
    return 0


def focus() -> int:
    """Focus the default assistant, cycling when already on a default-assistant tab."""
    default = _default()
    if default is None:
        return 2

    tabs = _assistant_tabs(default)
    if not tabs:
        return spawn()

    active = _active_tab_name()
    if active in tabs:
        target = tabs[(tabs.index(active) + 1) % len(tabs)]
    else:
        target = tabs[0]
    run(["zellij", "action", "go-to-tab-name", target], timeout=5)
    _close_bootstrap()
    return 0


def toggle() -> int:
    """Compatibility alias for the old Alt-a command."""
    return spawn()
