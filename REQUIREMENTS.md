# Requirements

The workflow needs the tools below on your `PATH`. `install.sh` does **not**
install them — it only checks and tells you which are missing. Install them
yourself with the commands here, then run `./install.sh`.

Target platform: **WSL2 / Ubuntu** (x86_64). Adjust for other distros as needed.

## Quick reference

| Tool        | Role                          | In apt? | Notes |
|-------------|-------------------------------|---------|-------|
| bash        | scripts (`proj`, `zswitch`)   | ✓ (preinstalled) | |
| python3     | `fleet` overview              | ✓ (preinstalled) | stdlib only, no pip deps |
| git         | version control + `proj`/lazygit | ✓ | |
| curl        | downloading release tarballs  | ✓ | only needed to fetch the binaries below |
| fzf         | fuzzy project/session picker  | ✓ | apt version is fine |
| neovim      | editor tab                    | ⚠️ old in apt | want ≥ 0.10; use PPA or release tarball |
| zellij      | terminal multiplexer          | ✗ | release binary or cargo |
| lazygit     | git TUI tab                   | ✗ | release binary or PPA |
| delta       | syntax-highlighting diff pager for lazygit | ✗ | release binary; lazygit's config routes diffs through it |
| claude      | optional assistant CLI        | ✗ | install per Claude Code docs |
| codex       | optional assistant CLI        | ✗ | install per Codex docs |

> **Clipboard:** the zellij config's `copy_command` pushes yanks to the host
> clipboard using `pbcopy` on macOS, `win32yank.exe` on WSL, `wl-copy` on
> Wayland, or `xclip` on X11. Install the one for your platform if it is not
> already present.

## apt packages (one command)

```bash
sudo apt-get update
sudo apt-get install -y bash python3 git curl fzf
```

> `bash`, `python3`, and `git` are almost certainly already present — listed for
> completeness. `fleet` uses only the Python standard library, so there is no
> `pip install` step.

## Tools not in apt (release binaries → `~/.local/bin`)

These are single static binaries; drop them on your `PATH`. `~/.local/bin` is
already added to `PATH` by the workflow's shell block.

### zellij
```bash
curl -fL https://github.com/zellij-org/zellij/releases/latest/download/zellij-x86_64-unknown-linux-musl.tar.gz \
  | tar -xz -C ~/.local/bin zellij
```

### lazygit
```bash
LG_VER=$(curl -fsSL https://api.github.com/repos/jesseduffield/lazygit/releases/latest | grep -Po '"tag_name": "v\K[^"]*')
curl -fL "https://github.com/jesseduffield/lazygit/releases/download/v${LG_VER}/lazygit_${LG_VER}_Linux_x86_64.tar.gz" \
  | tar -xz -C ~/.local/bin lazygit
```

### delta
The lazygit config (`lazygit/config.yml`, symlinked by `install.sh`) routes
diffs through `delta`, so it needs to be on `PATH` or lazygit's diff panel will
error. delta tags carry no `v` prefix.
```bash
DELTA_VER=$(curl -fsSL https://api.github.com/repos/dandavison/delta/releases/latest | grep -Po '"tag_name": "\K[^"]*')
curl -fL "https://github.com/dandavison/delta/releases/download/${DELTA_VER}/delta-${DELTA_VER}-x86_64-unknown-linux-gnu.tar.gz" \
  | tar -xz --strip-components=1 -C ~/.local/bin "delta-${DELTA_VER}-x86_64-unknown-linux-gnu/delta"
```

### neovim (release tarball — newer than apt)
```bash
curl -fL https://github.com/neovim/neovim/releases/latest/download/nvim-linux-x86_64.tar.gz \
  | tar -xz -C ~/.local/opt
ln -sfn ~/.local/opt/nvim-linux-x86_64/bin/nvim ~/.local/bin/nvim
```
> Or, if you prefer apt and a recent enough version is acceptable:
> `sudo add-apt-repository ppa:neovim-ppa/unstable && sudo apt-get install -y neovim`

### assistant CLI: Claude and/or Codex
Install at least one assistant CLI on `PATH`:

- `claude` for Claude Code
- `codex` for Codex

The assistant area launches through `hive assistant`. It creates separate Codex
and Claude tabs, so both can stay alive while the inactive assistant is fully
hidden. `Alt-a` rotates between them. If one tool is not installed, its tab stays
open with a clear message and a shell instead of failing with a bare
`command not found`.

Set the initially selected assistant with `HIVE_AGENT_DEFAULT`. Claude is the
default when the variable is unset:

```bash
export HIVE_AGENT_DEFAULT=claude
export HIVE_AGENT_DEFAULT=codex
```

## Clipboard

The zellij config copies yanked text to the system clipboard via a portable
shell wrapper:

```
copy_command "bash -lc 'if command -v pbcopy >/dev/null 2>&1; then pbcopy; elif command -v win32yank.exe >/dev/null 2>&1; then win32yank.exe -i --crlf; elif command -v wl-copy >/dev/null 2>&1; then wl-copy; elif command -v xclip >/dev/null 2>&1; then xclip -selection clipboard; else cat >/dev/null; fi'"
```

- **macOS:** `pbcopy` is built in.
- **WSL:** `win32yank.exe` is usually provided by the neovim setup. If it is on
  `PATH`, copying to the Windows clipboard works.
- **Linux:** install `wl-copy` for Wayland or `xclip` for X11.
- **Fallback:** delete the `copy_command`/`copy_clipboard` lines to use zellij's
  built-in OSC52 behavior instead.

## Versions known to work

Captured from the original work setup (newer is generally fine):

| tool    | version |
|---------|---------|
| neovim  | 0.12.2  |
| zellij  | 0.44.3  |
| lazygit | 0.62.1  |
| delta   | 0.18.2  |
| fzf     | 0.73.1  |
