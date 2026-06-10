"""Discover headless worktree agents (from the `worktree` skill).

Agents live at $WORKTREE_BASE/<repo>/<name>/ (default ~/projects/worktrees), each
with .claude/agent-session (the breadcrumb: current run's session id + log path).
The skill writes one stream-json log per run under .claude/agents/ and rewrites the
breadcrumb to point at the latest, so we read the breadcrumb's log (falling back to
the newest per-run log, then a legacy .claude/agent.log). Liveness is
`pgrep -f <session-id>`, matching how the skill stops them.
"""
from __future__ import annotations

import os
import glob
import json
from typing import Any, TypedDict

from .util import human_age, proc_alive

HOME = os.path.expanduser("~")
WT_BASE = os.environ.get("WORKTREE_BASE", os.path.join(HOME, "projects", "worktrees"))


class Agent(TypedDict):
    repo: str
    name: str
    branch: str
    path: str
    session_id: str
    log: str
    status: str
    age: str
    activity: str


def parse_session_file(path: str) -> tuple[str | None, str | None]:
    """Return (session_id, log). Tolerates a JSON breadcrumb or key=value lines."""
    try:
        raw = open(path, encoding="utf-8").read()
    except Exception:
        return None, None
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return (obj.get("session_id") or obj.get("sessionId")), obj.get("log")
    except Exception:
        pass
    sid = log = None
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("session_id="):
            sid = line.split("=", 1)[1].strip()
        elif line.startswith("log="):
            log = line.split("=", 1)[1].strip()
    return sid, log


def session_id_for(path: str) -> str | None:
    return parse_session_file(os.path.join(path, ".claude", "agent-session"))[0]


def resolve_log(wt: str, breadcrumb_log: str | None) -> str | None:
    """Pick the log to read for a worktree, newest-known first.

    The launcher writes one log per run under .claude/agents/ and points the
    breadcrumb at the current run, so the breadcrumb path is authoritative when it
    exists. Fall back to the newest per-run log, then the legacy single agent.log,
    so older worktrees (and a stale breadcrumb) still resolve to *something* real.
    """
    if breadcrumb_log and os.path.exists(breadcrumb_log):
        return breadcrumb_log
    runs = sorted(glob.glob(os.path.join(wt, ".claude", "agents", "*.log")))
    if runs:
        return runs[-1]
    legacy = os.path.join(wt, ".claude", "agent.log")
    return legacy if os.path.exists(legacy) else None


def tail_events(log: str, maxbytes: int = 65536) -> list[dict[str, Any]]:
    """Parse the last chunk of a stream-json log into events."""
    try:
        sz = os.path.getsize(log)
        with open(log, "rb") as fh:
            if sz > maxbytes:
                fh.seek(-maxbytes, os.SEEK_END)
            data = fh.read().decode("utf-8", "replace")
    except Exception:
        return []
    evs: list[dict[str, Any]] = []
    for line in data.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue  # tolerate the leading stdin warning / non-JSON noise
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                evs.append(obj)
        except Exception:
            continue
    return evs


def _activity(events: list[dict[str, Any]]) -> str:
    for e in reversed(events):
        t = e.get("type")
        if t == "assistant":
            for b in reversed(e.get("message", {}).get("content") or []):
                if b.get("type") == "text" and (b.get("text") or "").strip():
                    return b["text"].strip()
                if b.get("type") == "tool_use":
                    return f"⚙ {b.get('name', '?')}"
        elif t == "result":
            return (e.get("result") or "").strip() or "(done)"
    return "—"


def collect() -> list[Agent]:
    agents: list[Agent] = []
    pattern = os.path.join(WT_BASE, "*", "*", ".claude", "agent-session")
    for sess_file in sorted(glob.glob(pattern)):
        wt = os.path.dirname(os.path.dirname(sess_file))
        name = os.path.basename(wt)
        repo = os.path.basename(os.path.dirname(wt))
        sid, log = parse_session_file(sess_file)
        log = resolve_log(wt, log) or os.path.join(wt, ".claude", "agent.log")
        running = proc_alive(sid)
        events = tail_events(log) if os.path.exists(log) else []
        if running:
            status = "running"
        else:
            status = "stopped"
            for e in reversed(events):
                if e.get("type") == "result":
                    status = "failed" if e.get("is_error") else "done"
                    break
        try:
            started = os.path.getmtime(sess_file) * 1000
        except Exception:
            started = 0.0
        agents.append(Agent(
            repo=repo, name=name, branch=f"wt/{name}", path=wt,
            session_id=sid or "", log=log, status=status,
            age=human_age(started), activity=_activity(events),
        ))
    return agents
