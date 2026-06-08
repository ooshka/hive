# hive

A keyboard-driven, multi-session workspace for running and monitoring Claude
Code agents, built on **zellij**. Each project gets a named session with four
full-screen tabs — **claude / nvim / lazygit / fleet** — and you jump between
projects and tabs without the mouse.

Portable across machines: clone, install missing tools, run `./install.sh`.
The setup is symlink-based, so edits live in this repo and sync via `git pull`.

```
Tab 1 [claude]   Tab 2 [edit]   Tab 3 [git]    Tab 4 [fleet]
  claude           nvim           lazygit        agent overview
   Alt-1            Alt-2          Alt-3           Alt-4
```

## What's in here

| Path | What |
|------|------|
| `bin/hive`                  | the one entry point (symlinked onto PATH); resolves the repo and dispatches to `hivelib` |
| `hivelib/`                  | the logic, as a small Python package (one concern per module) — see [Architecture](#architecture) |
| `zellij/config.kdl`         | base config: `Alt-1..4` tab jumps, `Alt-s` open/switch, `Alt-w` close, `Alt-g` agents, `Alt-d` detach |
| `zellij/layouts/agent.kdl`  | the four-tab layout (each tab launched via `hive pane`) |
| `shell/agent-workflow.sh`   | sourced from `~/.bashrc`: PATH, `EDITOR`, fzf, `lg`/`agent`/`proj`/`fleet` aliases, `PROJ_ROOTS` |
| `git/attributes`            | optional global gitattributes (LF normalization for WSL/Windows) |
| `install.sh` / `uninstall.sh` | symlink things into place / back out cleanly |
| `REQUIREMENTS.md`           | the tools you need and how to install them |

Everything is one CLI: run `hive --help`. The shell aliases `proj` (→ `hive open`)
and `fleet` (→ `hive fleet`) are there for muscle memory; keybinds call the rest.

## Architecture

One Python CLI (`hive`), not a pile of shell scripts. `bin/hive` is a tiny entry
point that follows its install symlink back to the repo, puts it on `sys.path`,
and dispatches into the `hivelib` package. The guiding split: **logic and data in
Python; shell out only for spawning tools** (zellij, fzf, git, tail, nvim, claude).

| Module | Responsibility |
|--------|----------------|
| `hivelib/cli.py`        | argparse dispatch + the subcommand handlers |
| `hivelib/util.py`       | ANSI colour, age/string formatting, `run()`, `pgrep` |
| `hivelib/projects.py`   | project-root scanning, name sanitisation |
| `hivelib/zellij.py`     | thin zellij CLI wrappers (sessions, switch, rename-pane, new-pane) |
| `hivelib/sessions.py`   | interactive session discovery (`~/.claude/sessions`) |
| `hivelib/worktrees.py`  | worktree-agent discovery + status (`pgrep` / last `result` event) |
| `hivelib/streamfmt.py`  | stream-json → readable lines (the `wt log` formatter) |
| `hivelib/fleet.py`      | the grouped fleet tree / `--watch` / `--json` |
| `hivelib/picker.py`     | shared fzf wrapper (open / switch / agents) |

Subcommands: `fleet`, `pane` (layout launcher), `open` (shell-side), `switch` /
`close` / `agents` (in-zellij, bound to `Alt-s`/`Alt-w`/`Alt-g`), and
`wt log|kill|edit`. The zellij config calls `hive` directly — e.g. the layout runs
`command "hive"  args "pane" "Claude" "claude"`, and `Alt-g` runs `Run "hive" "agents"`.
Because `hive` resolves the repo from its symlink, only `bin/hive` is symlinked;
the package stays in the repo, so a `git pull` updates the logic with no reinstall.

## Install

```bash
git clone git@github.com:ooshka/hive.git ~/projects/hive
cd ~/projects/hive

# 1. Install the tools (see REQUIREMENTS.md). To preview what's missing:
./install.sh --check

# 2. Lay down symlinks + the ~/.bashrc source line:
./install.sh                 # add --git-config to also set LF line-ending rules

# 3. Pick up the shell changes:
source ~/.bashrc             # or open a new terminal
```

`install.sh` is idempotent: it backs up any existing real file to `<file>.bak`
before linking, and adds the `~/.bashrc` source line only once. It never
installs tools — that stays manual (see `REQUIREMENTS.md`). `./uninstall.sh`
removes the links and the source block (restoring any `.bak`).

## Daily use

```sh
proj                 # = hive open: fuzzy-pick a project → open/attach its session
proj webapp          # pre-filtered (auto-selects on a single match)
agent                # ad-hoc agent workspace in the current dir (zellij --layout agent)
hive --help          # everything else
```

Inside a session:

| Key | Action |
|-----|--------|
| `Alt-1` | claude tab |
| `Alt-2` | editor (nvim) tab |
| `Alt-3` | git (lazygit) tab |
| `Alt-4` | fleet tab (agent overview, self-refreshes every 2s) |
| `Alt-s` | **open or switch** projects (fzf picker — opens unopened projects too) |
| `Alt-w` | **close** the current project, switching to another live one (stays in zellij) |
| `Alt-g` | **manage worktree agents** (fzf picker: live log preview, kill, edit) |
| `Alt-d` | detach (session keeps running in the background) |
| `Ctrl-q` | quit zellij entirely (drops to a shell) |

Switching tabs is instant and never relaunches the tool — each tab's process
keeps running in the background. Each tab's terminal title shows `<tool> - <project>`
(e.g. `Claude - dev-globe`) so you can tell which project you're in.

## Managing sessions: leave alive vs. end

Every project is a named zellij session. The key distinction:

| Action | How | Result |
|--------|-----|--------|
| **Open a project** (new or existing) | `Alt-s` inside zellij, or `proj` from a shell | Switches to it; starts a fresh `agent` session if it wasn't running |
| **Switch to another open project** | `Alt-s` | Jumps there; the one you leave keeps running |
| **Leave it running (no switch)** | `Alt-d` (detach) | Session + processes keep running in the background |
| **Close the current project** | `Alt-w` | Switches to another live session, then ends this one — stays in zellij |
| **End + leave zellij** | `Ctrl-q`, close the terminal, or `zellij kill-session <name>` | Stops cleanly — no lingering `(EXITED)` stub (`session_serialization false`) |

So "close a session without killing it" → **switch away** (`Alt-s`) or **detach**
(`Alt-d`). To **end** it but stay in hive, use `Alt-w`. Come back to a detached
session via `Alt-s`, `proj <name>`, or `zellij attach <name>`.

Both `proj` (shell) and `Alt-s` (in-zellij) only *reattach* to a **live**
session; a closed/absent name is rebuilt **fresh** from `agent.kdl`.

> Changed `agent.kdl`? A *live* session keeps the old layout until you end it
> (`Ctrl-q` / `zellij kill-session <name>`); then `proj <name>` rebuilds it fresh.

## The fleet overview (`fleet`)

Reads `~/.claude/sessions/<pid>.json` (one per running Claude process), prunes
dead PIDs, and shows each live session: project (cwd), busy/idle status, kind,
git branch, age, and current in-progress task (from `~/.claude/tasks/<sessionId>/`).
`→` marks the current session. `fleet` prints once; `fleet --watch` live-refreshes
(the Alt-4 tab uses `--watch`); `fleet --json` emits `{sessions, worktrees}` for tooling.

**Worktree agents** (headless background agents from the `worktree` skill) appear
as a **sub-tree under their repo**:

```
○   webapp           idle    interactive main    58m  —
      └ ● wt/login-fix    running  3m   editing auth.py
      └ ✓ wt/index-bug    done     1h   result: ok
```

fleet discovers them by scanning `$WORKTREE_BASE/<repo>/<name>/.claude/agent-session`
(default `~/projects/worktrees`). Status: `pgrep -f <session-id>` → **running**;
otherwise the log's last `result` event → **✓ done** / **✗ failed**, or **· stopped**.

> **Local only.** These are Claude processes on this machine. Scheduled/remote
> agents run on Anthropic's infra and aren't on disk — use the desktop app's
> FleetView for those.

## Worktree agents: control (`Alt-g`)

`fleet` is read-only visibility; **`Alt-g`** runs `hive agents`, an fzf picker over
the worktree agents with a **live log preview** and actions:

| Key | Action |
|-----|--------|
| `enter`  | open the agent's log — live tail, readable stream-json (`Ctrl-c` closes the pane; scroll with zellij's scroll mode / mouse wheel) |
| `ctrl-k` | **kill** the agent (`pkill -f <session-id>`, with confirmation) |
| `ctrl-e` | open **nvim** on the worktree in a floating pane |

The same actions are `hive` subcommands, usable from any shell:

```sh
hive wt log  <worktree-path> [--raw] [--no-follow]   # readable stream-json (or full JSON)
hive wt kill <worktree-path>                          # SIGTERM the agent, SIGKILL fallback
hive wt edit <worktree-path>                          # nvim (floating inside zellij)
```

Worktree agents are **headless and non-interactive** — there's intentionally no
"attach" (two clients on one session corrupts it; see the `worktree` skill). To
take over, `hive wt kill` it and start a fresh session in the worktree. lazygit (`Alt-3`)
already shows a repo's worktrees in its branches view, so there's no separate git
pane here.

## Configuration

- **Project roots** — `hive open`/`switch` scan `~/projects` by default. Override
  per-shell with `export PROJ_ROOTS="/path/a:/path/b"`, or uncomment the line in
  `shell/agent-workflow.sh`.
- **Worktree base** — `hive fleet`/`agents` discover agents under `~/projects/worktrees`;
  override with `export WORKTREE_BASE=...` (matches the `worktree` skill).
- **Clipboard** — the zellij `copy_command` uses `win32yank.exe` on WSL (provided
  by your neovim setup). On non-WSL machines, change it in `zellij/config.kdl`
  (see `REQUIREMENTS.md`).
- **Pane titles** — each tab launches via `hive pane <label> <tool>`, which
  renames the zellij pane to `"<label> - $ZELLIJ_SESSION_NAME"` (e.g.
  `Claude - dev-globe`) and sets the host terminal's window title to match.
  Renaming pins the pane frame label, so the tool can't clobber it. Change the
  labels in `zellij/layouts/agent.kdl`.
- **Line endings** — `./install.sh --git-config` installs `git/attributes`
  globally and sets `core.autocrlf=false`, keeping WSL/Windows checkouts free of
  CRLF/LF diff noise. Opt-in because it changes global git behavior.

## Syncing changes between machines

Because everything is symlinked, edits to the scripts/configs *are* edits to the
repo. Commit and push, then `git pull` on the other machine — no reinstall needed
(unless you added a new file, in which case re-run `./install.sh` to link it).
