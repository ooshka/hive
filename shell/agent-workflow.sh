# ===== AGENT WORKFLOW (zellij/claude) =====
# Sourced from ~/.bashrc by install.sh. Edit this file in the repo, then
# `git pull` on other machines to sync — no need to re-touch ~/.bashrc.

# Ensure ~/.local/bin (where install.sh symlinks the `hive` CLI and drops
# zellij/fzf/lazygit/nvim) is on PATH, without duplicating it.
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) export PATH="$HOME/.local/bin:$PATH" ;;
esac

# Editor
export EDITOR=nvim
export VISUAL=nvim

# fzf shell integration (completion + Ctrl-T / Ctrl-R / Alt-C)
command -v fzf >/dev/null && eval "$(fzf --bash)"

alias lg='lazygit'
alias agent='zellij --layout agent'   # ad-hoc agent workspace in $PWD
# Everything else is the `hive` CLI (run `hive --help`). Short aliases for the
# two you type by hand; the rest are zellij keybinds (Alt-s/w/g) or `hive wt …`.
alias proj='hive open'                # fuzzy-pick a project → open/attach its session
alias fleet='hive fleet'              # agent overview

# Project roots for `hive open`/`switch` (colon-separated); default is ~/projects.
# Override per-machine by uncommenting / editing:
# export PROJ_ROOTS="$HOME/projects:/mnt/c/Users/$USER/IdeaProjects"
# ===== end agent workflow =====
