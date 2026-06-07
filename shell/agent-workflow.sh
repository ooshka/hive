# ===== AGENT WORKFLOW (zellij/claude) =====
# Sourced from ~/.bashrc by install.sh. Edit this file in the repo, then
# `git pull` on other machines to sync — no need to re-touch ~/.bashrc.

# Ensure ~/.local/bin (where install.sh symlinks proj/zswitch/fleet and drops
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

# `proj` (fuzzy project switcher) lives in ~/.local/bin.
# Project roots for `proj` (colon-separated); default is ~/projects.
# Override per-machine by uncommenting / editing:
# export PROJ_ROOTS="$HOME/projects:/mnt/c/Users/$USER/IdeaProjects"
# ===== end agent workflow =====
