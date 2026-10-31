# hive

A keyboard-driven, multi-session workspace for running and monitoring coding
agents, built on **zellij**. Each project gets a named session with assistant,
nvim, and lazygit tabs, and you jump between projects and tabs without the mouse.
Hive starts one assistant tab using `HIVE_AGENT_DEFAULT`; `Alt-a` creates another
tab of that same assistant, and `Alt-1` cycles through assistant tabs. `Alt-s`
toggles moving the live editor pane beside the active assistant.

Portable across machines: clone, install missing tools, run `./install.sh`.
The setup is symlink-based, so edits live in this repo and sync via `git pull`.

```
Tab 1 [assistant] Tab 2 [edit]   Tab 3 [git]
  claude/codex      nvim           lazygit
   Alt-1 / Alt-a    Alt-2          Alt-3
   Alt-s pairs tab 1 + live nvim
```

## What's in here

| Path | What |
|------|------|
| `bin/hive`                  | the one entry point (symlinked onto PATH); resolves the repo and dispatches to `hivelib` |
| `hivelib/`                  | the logic, as a small Python package (one concern per module) — see [Architecture](#architecture) |
| `zellij/config.kdl`         | base config: `Alt-1..3` tab jumps, `Alt-s` editor split, `Alt-w` close, `Alt-d` detach |
| `zellij/layouts/agent.kdl`  | the three-tab layout (each tab launched via `hive pane`) |
| `plugins/hive-orchestrator` | Zellij plugin for moving/focusing the live editor pane without helper panes |
| `shell/agent-workflow.sh`   | sourced from `~/.bashrc`: PATH, `EDITOR`, fzf, `lg`/`agent` aliases, `PROJ_ROOTS` |
| `git/attributes`            | optional global gitattributes (LF normalization for WSL/Windows) |
| `install.sh` / `uninstall.sh` | symlink things into place / back out cleanly |
| `REQUIREMENTS.md`           | the tools you need and how to install them |

Everything is one CLI: run `hive --help`. Bare **`hive`** opens the project
switcher; the rest are zellij keybinds.

## Architecture

One Python CLI (`hive`), not a pile of shell scripts. `bin/hive` is a tiny entry
point that follows its install symlink back to the repo, puts it on `sys.path`,
and dispatches into the `hivelib` package. The guiding split: **logic and data in
Python; shell out only for spawning tools** (zellij, fzf, git, tail, nvim, codex, claude).
Live pane choreography is handled by a small Zellij plugin so keybinds can move
and focus existing panes without launching temporary command panes.

| Module | Responsibility |
|--------|----------------|
| `hivelib/cli.py`        | argparse dispatch + the subcommand handlers |
| `hivelib/assistants.py` | default assistant tab spawning, focus/cycle, and missing-tool messages |
| `hivelib/util.py`       | ANSI colour, age/string formatting, `run()`, `pgrep` |
| `hivelib/projects.py`   | project-root scanning, name sanitisation |
| `hivelib/zellij.py`     | thin zellij CLI wrappers (sessions, switch, rename-pane, new-pane) |
| `hivelib/picker.py`     | shared fzf wrapper (open / switch) |
| `hivelib/zellij_permissions.py` | pre-seeds `hive-orchestrator`'s permission grant for `install.sh` |
| `plugins/hive-orchestrator` | Rust/WASM Zellij plugin for assistant/editor split focus |

Subcommands: `pane` (layout launcher), `tab` (named tab focus), `open`
(shell-side), and `switch` / `close` (in-zellij; `close` is bound to `Alt-w`). The
zellij config calls `hive` directly — e.g. the layout runs
`command "hive"  args "assistant"`.
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
installs tools — that stays manual (see `REQUIREMENTS.md`). Rust and the
`wasm32-wasip1` target are required to build and link the Hive Zellij plugin.
`install.sh` also grants `hive-orchestrator` its Zellij permissions
(`ReadCliPipes`, `ReadApplicationState`, `ChangeApplicationState`) directly in
`~/.cache/zellij/permissions.kdl` — it's loaded as a headless background
plugin (`load_plugins` in `zellij/config.kdl`), so there's no pane for
Zellij's interactive permission prompt to render into. `./uninstall.sh`
removes the links and the source block (restoring any `.bak`).

## Daily use

```sh
hive                 # fuzzy-pick a project → open/attach its session
hive open webapp     # pre-filtered (auto-selects on a single match)
agent                # ad-hoc agent workspace in the current dir (zellij --layout agent)
hive --help          # everything else
```

Inside a session:

| Key | Action |
|-----|--------|
| `Alt-1` | focus the assistant area; cycle assistants when already on an assistant tab |
| `Alt-a` | create another `HIVE_AGENT_DEFAULT` assistant tab, carrying the editor along if split |
| `Alt-x` | close the active assistant tab, except the first; return a split editor to `edit` |
| `Alt-s` | move the live editor to the assistant's right; press again to return it to `edit` and focus the full-width agent |
| `Alt-2` | focus the live editor pane; uses the editor tab when not split |
| `Alt-3` | focus git (lazygit) tab |
| `Alt-f` | toggle focused pane fullscreen |
| `Alt-w` | **close** the current project, switching to another live one (stays in zellij) |
| `Alt-d` | detach (session keeps running in the background) |
| `Ctrl-q` | quit zellij entirely (drops to a shell) |

Switching tabs is instant and never relaunches the tool — each tab's process
keeps running in the background. Each tab's terminal title shows `<tool> - <project>`
(e.g. `Claude - dev-globe`) so you can tell which project you're in.

## Testing

```sh
python3 -m unittest discover
```

The tests use Python's standard-library `unittest` runner and mock external
processes, so they do not need zellij, fzf, Claude, or Codex to be running.

## Managing sessions: leave alive vs. end

Every project is a named zellij session. The key distinction:

| Action | How | Result |
|--------|-----|--------|
| **Open a project** (new or existing) | `hive switch` inside zellij, or `hive` from a shell | Switches to it; starts a fresh `agent` session if it wasn't running |
| **Switch to another open project** | `hive switch` | Jumps there; the one you leave keeps running |
| **Leave it running (no switch)** | `Alt-d` (detach) | Session + processes keep running in the background |
| **Close the current project** | `Alt-w` | Switches to another live session, then ends this one — stays in zellij |
| **End + leave zellij** | `Ctrl-q`, close the terminal, or `zellij kill-session <name>` | Stops cleanly — no lingering `(EXITED)` stub (`session_serialization false`) |

So "close a session without killing it" → **switch away** (`hive switch`) or **detach**
(`Alt-d`). To **end** it but stay in hive, use `Alt-w`. Come back to a detached
session via `hive switch`, `hive open <name>`, or `zellij attach <name>`.

Both `hive`/`hive open` (shell) and `hive switch` (in-zellij) only *reattach* to a
**live** session; a closed/absent name is rebuilt **fresh** from `agent.kdl`.

> Changed `agent.kdl`? A *live* session keeps the old layout until you end it
> (`Ctrl-q` / `zellij kill-session <name>`); then `hive open <name>` rebuilds it fresh.

## Configuration

- **Project roots** — `hive open`/`switch` scan `~/projects` by default. Override
  per-shell with `export PROJ_ROOTS="/path/a:/path/b"`, or uncomment the line in
  `shell/agent-workflow.sh`.
- **Assistant tabs** — set `HIVE_AGENT_DEFAULT=claude` or `codex` to choose
  which assistant Hive launches. Claude is the default when the variable is
  unset. `Alt-a` creates another tab of that same assistant; `Alt-1` focuses the
  assistant area and cycles through assistant tabs when already there. If the
  configured tool is not installed, the tab stays open with an explanatory shell.
- **Clipboard** — the zellij `copy_command` copies to the host clipboard using
  `pbcopy` on macOS, `win32yank.exe` on WSL, `wl-copy` on Wayland, or `xclip` on
  X11 (see `REQUIREMENTS.md`).
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
