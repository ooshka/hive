"""The fleet overview: interactive sessions with worktree agents nested beneath."""
from __future__ import annotations

import json
import sys
import time
from typing import Any

from . import sessions, worktrees
from .util import color, trunc, BOLD, DIM, GREEN, YELLOW, CYAN, RED


def _agent_dot(status: str) -> str:
    return {
        "running": color(GREEN, "●"),
        "done": color(GREEN, "✓"),
        "failed": color(RED, "✗"),
    }.get(status, color(DIM, "·"))


def render() -> str:
    sess = sessions.collect()
    agents = worktrees.collect()

    # Group both by project/repo name, preserving first-seen order.
    groups: dict[str, dict[str, list[Any]]] = {}
    order: list[str] = []

    def grp(key: str) -> dict[str, list[Any]]:
        if key not in groups:
            groups[key] = {"sessions": [], "agents": []}
            order.append(key)
        return groups[key]

    for s in sess:
        grp(s["project"])["sessions"].append(s)
    for a in agents:
        grp(a["repo"])["agents"].append(a)

    out = [color(BOLD, "Claude fleet — local sessions") + color(DIM, f"   {time.strftime('%H:%M:%S')}")]
    if not order:
        out.append(color(DIM, "  (no local Claude sessions or worktree agents running)"))
        out.append(color(DIM, "  Scheduled/remote agents → Claude desktop app."))
        return "\n".join(out)

    cols = (f"{'PROJECT':<16} {'STATUS':<7} {'KIND':<11} {'BRANCH':<16} "
            f"{'AGE':>6}  {'CURRENT TASK / ACTIVITY':<34}")
    out.append(color(BOLD, "    " + cols))
    for proj in order:
        g = groups[proj]
        if g["sessions"]:
            for r in g["sessions"]:
                dot = (color(GREEN, "●") if r["status"] == "busy"
                       else color(YELLOW, "○") if r["status"] == "idle" else "·")
                mark = color(CYAN, "→") if r["here"] else " "
                body = (f"{trunc(r['project'], 16):<16} {r['status']:<7} {trunc(r['kind'], 11):<11} "
                        f"{trunc(r['branch'], 16):<16} {r['age']:>6}  {trunc(r['task'], 34):<34}")
                out.append(f"{dot} {mark} {body}")
        else:
            out.append(f"·   {trunc(proj, 16):<16} {color(DIM, '(no live session)')}")
        for a in g["agents"]:
            out.append(f"      └ {_agent_dot(a['status'])} {trunc(a['branch'], 18):<18} "
                       f"{a['status']:<8} {a['age']:>6}  {color(DIM, trunc(a['activity'], 36))}")

    out.append("")
    out.append(color(DIM, "  → this session  ● busy/running  ○ idle  ✓ done  ✗ failed  · stopped"
                      "   |   Alt-g: manage worktree agents"))
    return "\n".join(out)


def main_json() -> None:
    print(json.dumps({"sessions": sessions.collect(), "worktrees": worktrees.collect()}, indent=2))


def main_watch() -> None:
    try:
        while True:
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.write(render() + "\n")
            sys.stdout.flush()
            time.sleep(2)
    except KeyboardInterrupt:
        pass
