"""Thin wrappers around the zellij CLI — the process-orchestration layer."""
from __future__ import annotations

import os

from .util import run


def inside() -> bool:
    return bool(os.environ.get("ZELLIJ"))


def session_name() -> str:
    return os.environ.get("ZELLIJ_SESSION_NAME", "")


def pane_id() -> str | None:
    return os.environ.get("ZELLIJ_PANE_ID") or None


def live_sessions() -> list[str]:
    """Names of live sessions (drops the EXITED resurrection stubs)."""
    rc, out = run(["zellij", "list-sessions", "--no-formatting"], timeout=2)
    if rc != 0:
        return []
    names: list[str] = []
    for line in out.splitlines():
        if "Created" in line and "EXITED" not in line:
            parts = line.split()
            if parts:
                names.append(parts[0])
    return names


def is_live(name: str) -> bool:
    return name in live_sessions()


def rename_pane(pid: str, title: str) -> None:
    run(["zellij", "action", "rename-pane", "--pane-id", pid, title], timeout=2)


def kill_session(name: str) -> None:
    run(["zellij", "kill-session", name], timeout=5)


def exec_switch_session(name: str, cwd: str | None = None, layout: str | None = None) -> None:
    """Switch to (or create, if absent) a session, replacing this process."""
    args = ["zellij", "action", "switch-session"]
    if cwd:
        args += ["-c", cwd]
    if layout:
        args += ["-l", layout]
    args.append(name)
    os.execvp("zellij", args)


def exec_new_pane(cmd: list[str], *, floating: bool = False, cwd: str | None = None,
                  name: str | None = None, close_on_exit: bool = False) -> None:
    """Open a new pane running `cmd`, replacing this process."""
    args = ["zellij", "action", "new-pane"]
    if floating:
        args.append("--floating")
    if close_on_exit:
        args.append("--close-on-exit")
    if cwd:
        args += ["--cwd", cwd]
    if name:
        args += ["--name", name]
    args.append("--")
    args += cmd
    os.execvp("zellij", args)
