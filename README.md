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
| `bin/proj`                  | fuzzy project switcher (fzf over `~/projects`) → opens/attaches a session |
| `bin/zswitch`               | fzf picker to **open or switch** projects from inside zellij (Alt-s) |
| `bin/zclose`                | close the current project but stay in zellij (Alt-w) |
| `bin/hive-pane`             | launcher that titles each tab `"<tool> - <project>"` |
| `bin/fleet`                 | local agent overview — interactive sessions + worktree agents (`--json` for tooling) |
| `bin/wtagents`              | manage worktree agents: fzf picker w/ live log preview (Alt-g) |
| `bin/wtlog`                 | tail a worktree agent's stream-json log through a readable formatter |
| `bin/wtkill`                | stop a worktree agent (`pkill -f <session-id>`) |
| `bin/wtedit`                | open nvim on a worktree in a floating pane |
| `zellij/config.kdl`         | base config: `Alt-1..4` tab jumps, `Alt-s` open/switch, `Alt-w` close, `Alt-g` agents, `Alt-d` detach |
| `zellij/layouts/agent.kdl`  | the four-tab layout (each tab launched via `hive-pane`) |
| `shell/agent-workflow.sh`   | sourced from `~/.bashrc`: PATH, `EDITOR`, fzf, `lg`/`agent` aliases, `PROJ_ROOTS` |
| `git/attributes`            | optional global gitattributes (LF normalization for WSL/Windows) |
| `install.sh` / `uninstall.sh` | symlink things into place / back out cleanly |
| `REQUIREMENTS.md`           | the tools you need and how to install them |

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
proj                 # fuzzy-pick a project → opens/attaches its agent session
proj webapp          # pre-filtered (auto-selects on a single match)
agent                # ad-hoc agent workspace in the current dir
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

`fleet` is read-only visibility; **`Alt-g`** opens `wtagents`, an fzf picker over
the worktree agents with a **live log preview** and actions:

| Key | Action |
|-----|--------|
| `enter`  | open the agent's log — live tail, readable stream-json, in a pager (`q` closes the pane; `Ctrl-c` pauses follow to scroll/search) |
| `ctrl-k` | **kill** the agent (`pkill -f <session-id>`, with confirmation) |
| `ctrl-e` | open **nvim** on the worktree in a floating pane |

The same actions are standalone scripts, usable from any shell:

```sh
wtlog  <worktree-path> [--raw] [--no-follow]   # readable stream-json (or full JSON)
wtkill <worktree-path>                          # SIGTERM the agent, SIGKILL fallback
wtedit <worktree-path>                          # nvim (floating inside zellij)
```

Worktree agents are **headless and non-interactive** — there's intentionally no
"attach" (two clients on one session corrupts it; see the `worktree` skill). To
take over, `wtkill` it and start a fresh session in the worktree. lazygit (`Alt-3`)
already shows a repo's worktrees in its branches view, so there's no separate git
pane here.

## Configuration

- **Project roots** — `proj` scans `~/projects` by default. Override per-shell
  with `export PROJ_ROOTS="/path/a:/path/b"`, or uncomment the line in
  `shell/agent-workflow.sh`.
- **Clipboard** — the zellij `copy_command` uses `win32yank.exe` on WSL (provided
  by your neovim setup). On non-WSL machines, change it in `zellij/config.kdl`
  (see `REQUIREMENTS.md`).
- **Pane titles** — each tab launches via `hive-pane <label> <tool>`, which
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
