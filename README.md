# zellij-agent-workflow

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
| `bin/zswitch`               | fzf picker to switch between **live** sessions (Alt-s; switch-only) |
| `bin/fleet`                 | local Claude agent overview (powers the fleet tab) |
| `zellij/config.kdl`         | base config: `Alt-1..4` tab jumps, `Alt-s` switch, `Alt-d` detach |
| `zellij/layouts/agent.kdl`  | the four-tab layout |
| `shell/agent-workflow.sh`   | sourced from `~/.bashrc`: PATH, `EDITOR`, fzf, `lg`/`agent` aliases, `PROJ_ROOTS` |
| `git/attributes`            | optional global gitattributes (LF normalization for WSL/Windows) |
| `install.sh` / `uninstall.sh` | symlink things into place / back out cleanly |
| `REQUIREMENTS.md`           | the tools you need and how to install them |

## Install

```bash
git clone <your-remote>/zellij-agent-workflow ~/projects/zellij-agent-workflow
cd ~/projects/zellij-agent-workflow

# 1. Install the tools (see REQUIREMENTS.md). To preview what's missing:
./install.sh --check

# 2. Lay down symlinks + the ~/.bashrc source line:
./install.sh                 # add --git-config to also set LF line-ending rules

# 3. Pick up the shell changes:
source ~/.bashrc             # or open a new terminal
```

`install.sh` is idempotent: it backs up any existing file to `<file>.bak`
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
| `Alt-s` | switch between **live** sessions (fzf picker — never creates) |
| `Alt-d` | detach (session keeps running in the background) |
| `Ctrl-q` | quit / end the session |

Switching tabs is instant and never relaunches the tool — each tab's process
keeps running in the background.

## Managing sessions: leave alive vs. end

Every project is a named zellij session. The key distinction:

| Action | How | Result |
|--------|-----|--------|
| **Switch to another live session** | `Alt-s` (fzf, switch-only) | Jumps there; the one you leave keeps running |
| **Leave it running (no switch)** | `Alt-d` (detach) | Session + processes keep running in the background |
| **Create a session** | `proj <name>` **from a shell** (detach first if inside zellij) | New project session with the agent layout |
| **End it** | `Ctrl-q`, close the terminal, or `zellij kill-session <name>` | Stops cleanly — no lingering `(EXITED)` stub (`session_serialization false`) |

So "close a session without killing it" → **switch away** (`Alt-s`) or **detach**
(`Alt-d`). Come back via `Alt-s`, `proj <name>`, or `zellij attach <name>`.

`proj` only *reattaches* to a **live** session; a closed/absent name is rebuilt
**fresh** from `agent.kdl`. `proj` runs from a shell — *inside* zellij use `Alt-s`.

> Changed `agent.kdl`? A *live* session keeps the old layout until you end it
> (`Ctrl-q` / `zellij kill-session <name>`); then `proj <name>` rebuilds it fresh.

## The fleet overview (`fleet`)

Reads `~/.claude/sessions/<pid>.json` (one per running Claude process), prunes
dead PIDs, and shows each live session: project (cwd), busy/idle status, kind,
git branch, age, and current in-progress task (from `~/.claude/tasks/<sessionId>/`).
`→` marks the current session. `fleet` prints once; `fleet --watch` live-refreshes
(the Alt-4 tab uses `--watch`).

> **Local only.** These are Claude processes on this machine. Scheduled/remote
> agents run on Anthropic's infra and aren't on disk — use the desktop app's
> FleetView for those.

## Configuration

- **Project roots** — `proj` scans `~/projects` by default. Override per-shell
  with `export PROJ_ROOTS="/path/a:/path/b"`, or uncomment the line in
  `shell/agent-workflow.sh`.
- **Clipboard** — the zellij `copy_command` uses `win32yank.exe` on WSL (provided
  by your neovim setup). On non-WSL machines, change it in `zellij/config.kdl`
  (see `REQUIREMENTS.md`).
- **Line endings** — `./install.sh --git-config` installs `git/attributes`
  globally and sets `core.autocrlf=false`, keeping WSL/Windows checkouts free of
  CRLF/LF diff noise. Opt-in because it changes global git behavior.

## Syncing changes between machines

Because everything is symlinked, edits to the scripts/configs *are* edits to the
repo. Commit and push, then `git pull` on the other machine — no reinstall needed
(unless you added a new file, in which case re-run `./install.sh` to link it).
