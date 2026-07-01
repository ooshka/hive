"""hive — single entry point for the zellij assistant workspace.

Subcommands:
  assistant                  create the first tab's Codex/Claude panes
  assistant-shell <name>     run one assistant pane
  assistant-toggle           rotate between Codex/Claude tabs
  fleet [--watch|--json]      agent overview (sessions + worktree agents)
  pane <label> <cmd> [args…]  title the pane "<label> - <project>", then exec cmd
  open [query]                open/attach a project session (run from a shell)
  switch                      open or switch projects (inside zellij; Alt-s)
  close                       close current project, stay in zellij (Alt-w)
  agents                      manage worktree agents (inside zellij; Alt-g)
  wt log|kill|edit <path>     act on one worktree agent
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from . import assistants, fleet, projects, worktrees, zellij
from .picker import fzf
from .streamfmt import view
from .util import paint, run, proc_alive, GREEN, RED, DIM


# ── assistant tab ──────────────────────────────────────────────────────────
def cmd_assistant(args: argparse.Namespace) -> int:
    return assistants.bootstrap()


def cmd_assistant_shell(args: argparse.Namespace) -> int:
    return assistants.shell(args.name)


def cmd_assistant_toggle(args: argparse.Namespace) -> int:
    return assistants.toggle()


# ── fleet ─────────────────────────────────────────────────────────────────
def cmd_fleet(args: argparse.Namespace) -> int:
    if args.json:
        fleet.main_json()
    elif args.watch:
        fleet.main_watch()
    else:
        print(fleet.render())
    return 0


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


# ── agents: manage worktree agents (the old `wtagents`) ─────────────────────
_ICON = {"running": paint(GREEN, "●"), "done": paint(GREEN, "✓"), "failed": paint(RED, "✗")}


def cmd_agents(args: argparse.Namespace) -> int:
    if not zellij.inside():
        print("hive agents only works inside zellij (Alt-g).", file=sys.stderr)
        return 1
    agents = worktrees.collect()
    if not agents:
        print(f"No worktree agents under {worktrees.WT_BASE}.")
        print('Spawn one with the worktree skill (create … --launch "<task>").')
        input("(press Enter to close) ")
        return 0
    lines: list[str] = []
    for a in agents:
        icon = _ICON.get(a["status"], paint(DIM, "·"))
        act = a["activity"].replace("\t", " ").replace("\n", " ")[:48]
        disp = f"{icon} {a['repo']}/{a['name']}  [{a['status']} {a['age']}]  {act}"
        lines.append(f"{disp}\t{a['path']}")
    res = fzf(lines, prompt="worktree agent> ", delimiter="\t", with_nth="1",
              expect=("ctrl-k", "ctrl-e"),
              preview="hive wt log {2} --no-follow", preview_window="right,58%,wrap",
              header="enter=log (Ctrl-c closes)   ctrl-k=kill   ctrl-e=nvim edit")
    if not res:
        return 0
    key, sel = res
    path = sel.split("\t")[-1]
    name = os.path.basename(path)
    if key == "ctrl-k":
        if input(f'Kill worktree agent "{name}" ? [y/N] ').strip().lower() == "y":
            _wt_kill(path)
            input("(press Enter) ")
        return 0
    if key == "ctrl-e":
        return _wt_edit(path)
    zellij.exec_new_pane(["hive", "wt", "log", path], floating=True,
                         close_on_exit=True, name=f"log:{name}")
    return 0  # unreachable


# ── wt log / kill / edit ────────────────────────────────────────────────────
def _resolve_log(target: str) -> str | None:
    if os.path.isfile(target):
        return target
    if not os.path.isdir(target):
        print(f"hive wt log: not found: {target}", file=sys.stderr)
        return None
    # A worktree dir: honour the breadcrumb's current run, else newest per-run log.
    breadcrumb_log = worktrees.parse_session_file(
        os.path.join(target, ".claude", "agent-session"))[1]
    log = worktrees.resolve_log(target, breadcrumb_log)
    if not log or not os.path.isfile(log):
        print(f"hive wt log: no log under {target}/.claude (agent may not have started)",
              file=sys.stderr)
        return None
    return log


def cmd_wt_log(args: argparse.Namespace) -> int:
    log = _resolve_log(args.path)
    if not log:
        return 1
    return view(log, raw=args.raw, follow=not args.no_follow)


def _wt_kill(path: str) -> int:
    sid = worktrees.session_id_for(path)
    if not sid:
        print(f"hive wt kill: could not determine session id for {path}", file=sys.stderr)
        return 1
    if not proc_alive(sid):
        print(f"No running agent for session {sid} (already stopped).")
        return 0
    print(f"Stopping agent {sid} (SIGTERM)…")
    run(["pkill", "-TERM", "-f", sid])
    for _ in range(5):
        if not proc_alive(sid):
            print("Stopped.")
            return 0
        time.sleep(0.4)
    print("Still alive after SIGTERM; sending SIGKILL…")
    run(["pkill", "-KILL", "-f", sid])
    time.sleep(0.3)
    print("Killed." if not proc_alive(sid) else "WARNING: agent still present.")
    return 0


def _wt_edit(path: str) -> int:
    if not os.path.isdir(path):
        print(f"hive wt edit: not a directory: {path}", file=sys.stderr)
        return 1
    name = os.path.basename(path)
    if zellij.inside():
        zellij.exec_new_pane(["nvim"], floating=True, cwd=path,
                             name=f"edit:{name}", close_on_exit=True)
    else:
        os.chdir(path)
        os.execvp("nvim", ["nvim"])
    return 0  # unreachable


def cmd_wt_kill(args: argparse.Namespace) -> int:
    return _wt_kill(args.path)


def cmd_wt_edit(args: argparse.Namespace) -> int:
    return _wt_edit(args.path)


def cmd_wt_help(args: argparse.Namespace) -> int:
    print("usage: hive wt {log|kill|edit} <worktree-path>", file=sys.stderr)
    return 2


# ── dispatch ─────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    p = argparse.ArgumentParser(
        prog="hive", description="zellij assistant workspace. "
        "Run `hive` with no subcommand to open the project switcher.")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("assistant", help="focus configured Codex/Claude assistant tab").set_defaults(
        func=cmd_assistant)
    ash = sub.add_parser("assistant-shell", help="run one assistant pane (layout use)")
    ash.add_argument("name")
    ash.set_defaults(func=cmd_assistant_shell)
    sub.add_parser("assistant-toggle", help="rotate between Codex/Claude tabs").set_defaults(
        func=cmd_assistant_toggle)

    f = sub.add_parser("fleet", help="agent overview (sessions + worktree agents)")
    f.add_argument("--watch", action="store_true", help="refresh every 2s")
    f.add_argument("--json", action="store_true", help="machine-readable output")
    f.set_defaults(func=cmd_fleet)

    pa = sub.add_parser("pane", help="title the pane, then exec a tool (layout use)")
    pa.add_argument("label")
    pa.add_argument("cmd", nargs=argparse.REMAINDER)
    pa.set_defaults(func=cmd_pane)

    o = sub.add_parser("open", help="open/attach a project session (from a shell)")
    o.add_argument("query", nargs="?")
    o.set_defaults(func=cmd_open)

    sub.add_parser("switch", help="open or switch projects (inside zellij)").set_defaults(func=cmd_switch)
    sub.add_parser("close", help="close current project, stay in zellij").set_defaults(func=cmd_close)
    sub.add_parser("agents", help="manage worktree agents (inside zellij)").set_defaults(func=cmd_agents)

    wt = sub.add_parser("wt", help="worktree agent helpers (log/kill/edit)")
    wt.set_defaults(func=cmd_wt_help)  # `hive wt` with no sub → usage
    wtsub = wt.add_subparsers(dest="wtcmd")
    wl = wtsub.add_parser("log", help="tail an agent's stream-json log")
    wl.add_argument("path")
    wl.add_argument("--raw", action="store_true", help="full JSON instead of formatted")
    wl.add_argument("--no-follow", dest="no_follow", action="store_true", help="print tail and exit")
    wl.set_defaults(func=cmd_wt_log)
    wk = wtsub.add_parser("kill", help="stop an agent (pkill -f <session-id>)")
    wk.add_argument("path")
    wk.set_defaults(func=cmd_wt_kill)
    we = wtsub.add_parser("edit", help="open nvim on the worktree")
    we.add_argument("path")
    we.set_defaults(func=cmd_wt_edit)

    args = p.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        # bare `hive` → open the project switcher (same as `hive open`)
        return cmd_open(argparse.Namespace(query=None))
    return func(args) or 0
