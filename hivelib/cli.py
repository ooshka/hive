"""hive — single entry point for the zellij assistant workspace.

Subcommands:
  assistant                  focus/cycle HIVE_AGENT_DEFAULT assistant tabs
  assistant-shell <name>     run one assistant pane
  assistant-spawn            create another HIVE_AGENT_DEFAULT assistant tab
  pane <label> <cmd> [args…]  title the pane "<label> - <project>", then exec cmd
  tab <name>                  focus a named tab
  open [query]                open/attach a project session (run from a shell)
  switch                      open or switch projects (inside zellij; Alt-s)
  close                       close current project, stay in zellij (Alt-w)
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from . import assistants, projects, zellij
from .picker import fzf
from .util import paint, run, GREEN


# ── assistant tab ──────────────────────────────────────────────────────────
def cmd_assistant(args: argparse.Namespace) -> int:
    return assistants.focus()


def cmd_assistant_shell(args: argparse.Namespace) -> int:
    return assistants.shell(args.name)


def cmd_assistant_toggle(args: argparse.Namespace) -> int:
    return assistants.toggle()


def cmd_assistant_spawn(args: argparse.Namespace) -> int:
    return assistants.spawn()


# ── pane: title the pane, then exec the tool (layout launcher) ──────────────
def cmd_pane(args: argparse.Namespace) -> int:
    cmd = args.cmd
    if not cmd:
        print("hive pane: need a command to run", file=sys.stderr)
        return 2
    title = f"{args.label} - {zellij.session_name() or 'shell'}"
    pid = zellij.pane_id()
    if pid:
        zellij.rename_pane(pid, title)         # zellij pane frame label (pinned)
    sys.stdout.write(f"\033]0;{title}\007")     # host terminal window title
    sys.stdout.flush()
    os.execvp(cmd[0], cmd)
    return 0  # unreachable


def cmd_tab(args: argparse.Namespace) -> int:
    if not zellij.inside():
        print("hive tab only works inside zellij.", file=sys.stderr)
        return 1
    return zellij.go_to_tab_name(args.name)


# ── open: shell-side project launcher (the old `proj`) ──────────────────────
def cmd_open(args: argparse.Namespace) -> int:
    if zellij.inside():
        print("Inside zellij — use Alt-s to open/switch projects.", file=sys.stderr)
        return 1
    if args.query and os.path.isdir(args.query):
        selected = os.path.realpath(args.query)
    else:
        picked = fzf(projects.list_projects(), prompt="project> ", height="40%",
                     query=args.query, select_1=True, exit_0=True)
        if not picked:
            return 0
        selected = os.path.realpath(picked[1])
    name = projects.sanitize(selected)
    os.chdir(selected)
    if zellij.is_live(name):
        os.execvp("zellij", ["zellij", "attach", name])
    else:
        os.execvp("zellij", ["zellij", "-s", name, "-n", "agent"])
    return 0  # unreachable


# ── switch: open OR switch projects from inside zellij (the old `zswitch`) ──
def cmd_switch(args: argparse.Namespace) -> int:
    if not zellij.inside():
        print("hive switch only works inside zellij.", file=sys.stderr)
        return 1
    current = zellij.session_name()
    live = set(zellij.live_sessions())
    lines: list[str] = []
    seen: set[str] = set()
    for p in projects.list_projects():
        name = projects.sanitize(p)
        if name == current:
            continue
        seen.add(name)
        icon = paint(GREEN, "●") if name in live else " "
        lines.append(f"{icon} {name}\t{name}\t{p}")
    for s in sorted(live):
        if s == current or s in seen:
            continue
        lines.append(f"{paint(GREEN, '●')} {s}\t{s}\t")

    if not lines:
        print("No other projects or live sessions to open/switch to.")
        input("(press Enter to close) ")
        return 0
    res = fzf(lines, prompt="open/switch> ", delimiter="\t", with_nth="1")
    if not res:
        return 0
    fields = res[1].split("\t")
    name, path = fields[1], (fields[2] if len(fields) > 2 else "")
    if name in live or not path:
        zellij.exec_switch_session(name)             # live → just switch
    else:
        zellij.exec_switch_session(name, cwd=path, layout="agent")  # new → create + switch
    return 0  # unreachable


# ── close: end the current project, switch to another (the old `zclose`) ────
def cmd_close(args: argparse.Namespace) -> int:
    if not zellij.inside():
        print("hive close only works inside zellij.", file=sys.stderr)
        return 1
    current = zellij.session_name()
    others = [s for s in zellij.live_sessions() if s != current]
    if not others:
        print(f"Closing '{current}' would leave no live session to land on.")
        print("Open another first with Alt-s, or quit zellij with Ctrl-q.")
        input("(press Enter to cancel) ")
        return 0
    if len(others) == 1:
        target = others[0]
    else:
        res = fzf(others, prompt=f"close '{current}' → land on> ")
        if not res:
            return 0
        target = res[1]
    # Switch the client away first, THEN kill the session we left (it's now
    # backgrounded). The brief sleep lets the client finish switching.
    run(["zellij", "action", "switch-session", target])
    time.sleep(0.4)
    zellij.kill_session(current)
    return 0


# ── dispatch ─────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    p = argparse.ArgumentParser(
        prog="hive", description="zellij assistant workspace. "
        "Run `hive` with no subcommand to open the project switcher.")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("assistant", help="focus/cycle HIVE_AGENT_DEFAULT assistant tabs").set_defaults(
        func=cmd_assistant)
    ash = sub.add_parser("assistant-shell", help="run one assistant pane (layout use)")
    ash.add_argument("name")
    ash.set_defaults(func=cmd_assistant_shell)
    sub.add_parser("assistant-spawn", help="create another HIVE_AGENT_DEFAULT assistant tab").set_defaults(
        func=cmd_assistant_spawn)
    sub.add_parser("assistant-toggle", help="compatibility alias for assistant-spawn").set_defaults(
        func=cmd_assistant_toggle)

    pa = sub.add_parser("pane", help="title the pane, then exec a tool (layout use)")
    pa.add_argument("label")
    pa.add_argument("cmd", nargs=argparse.REMAINDER)
    pa.set_defaults(func=cmd_pane)

    tab = sub.add_parser("tab", help="focus a named tab")
    tab.add_argument("name")
    tab.set_defaults(func=cmd_tab)

    o = sub.add_parser("open", help="open/attach a project session (from a shell)")
    o.add_argument("query", nargs="?")
    o.set_defaults(func=cmd_open)

    sub.add_parser("switch", help="open or switch projects (inside zellij)").set_defaults(func=cmd_switch)
    sub.add_parser("close", help="close current project, stay in zellij").set_defaults(func=cmd_close)

    args = p.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        # bare `hive` → open the project switcher (same as `hive open`)
        return cmd_open(argparse.Namespace(query=None))
    return func(args) or 0
