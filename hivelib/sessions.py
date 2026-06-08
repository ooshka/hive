"""Discover interactive Claude sessions from ~/.claude/sessions/<pid>.json."""
from __future__ import annotations

import os
import glob
import json
from typing import Any, TypedDict

from .util import human_age, run

HOME = os.path.expanduser("~")
SESS_DIR = os.path.join(HOME, ".claude", "sessions")
TASKS_DIR = os.path.join(HOME, ".claude", "tasks")


class Session(TypedDict):
    project: str
    status: str
    kind: str
    branch: str
    age: str
    task: str
    pid: Any
    here: bool


def _alive(pid: Any) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def git_branch(cwd: str) -> str:
    if not cwd or not os.path.isdir(cwd):
        return "—"
    rc, out = run(["git", "-C", cwd, "symbolic-ref", "--short", "HEAD"], timeout=1.5)
    if rc == 0 and out:
        return out
    rc, out = run(["git", "-C", cwd, "rev-parse", "--short", "HEAD"], timeout=1.5)
    return out if rc == 0 and out else "—"


def current_task(session_id: str) -> str:
    d = os.path.join(TASKS_DIR, session_id)
    if not session_id or not os.path.isdir(d):
        return "—"
    for f in glob.glob(os.path.join(d, "[0-9]*.json")):
        try:
            t = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if t.get("status") == "in_progress":
            return t.get("activeForm") or t.get("subject") or "—"
    return "—"


def collect() -> list[Session]:
    here = os.path.realpath(os.getcwd())
    rows: list[Session] = []
    for f in sorted(glob.glob(os.path.join(SESS_DIR, "*.json"))):
        try:
            s = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        pid = s.get("pid")
        if not _alive(pid):
            continue  # stale file from a crashed/closed session
        cwd = s.get("cwd", "") or ""
        rows.append(Session(
            project=os.path.basename(cwd.rstrip("/")) or cwd or "?",
            status=s.get("status", "?"),
            kind=s.get("kind", "?"),
            branch=git_branch(cwd),
            age=human_age(s.get("startedAt")),
            task=current_task(s.get("sessionId", "")),
            pid=pid,
            here=(os.path.realpath(cwd) == here) if cwd else False,
        ))
    return rows
