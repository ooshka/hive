#!/usr/bin/env bash
# install.sh — symlink the zellij/claude agent workflow into place.
#
#   ./install.sh               symlink scripts + zellij config, wire up ~/.bashrc
#   ./install.sh --git-config  also install global gitattributes (line endings)
#   ./install.sh --check       only report dependency / link status, change nothing
#
# Idempotent: existing non-symlink files are backed up to <file>.bak before
# linking; the ~/.bashrc source line is added once (marker-guarded). Tools are
# NOT installed — see REQUIREMENTS.md. Run from anywhere; paths resolve to the
# repo this script lives in.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
ZELLIJ_DIR="$HOME/.config/zellij"
GITCFG_DIR="$HOME/.config/git"
BASHRC="$HOME/.bashrc"
MARKER="# >>> hive >>>"
MARKER_END="# <<< hive <<<"
# Pre-rename markers, cleaned up on install so moving/renaming the repo self-heals.
LEGACY_MARKER="# >>> zellij-agent-workflow >>>"
LEGACY_MARKER_END="# <<< zellij-agent-workflow <<<"

DO_GIT=0; CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --git-config) DO_GIT=1 ;;
    --check)      CHECK_ONLY=1 ;;
    -h|--help)    grep -E '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

green() { printf '\033[32m%s\033[0m\n' "$1"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$1"; }
dim()   { printf '\033[2m%s\033[0m\n'  "$1"; }

# link <src> <dest>: symlink src→dest, backing up any pre-existing real file.
link() {
  local src="$1" dest="$2"
  if [ -L "$dest" ] && [ "$(readlink -f "$dest")" = "$(readlink -f "$src")" ]; then
    dim "  = $dest (already linked)"; return
  fi
  mkdir -p "$(dirname "$dest")"
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    mv "$dest" "$dest.bak"
    yellow "  ~ backed up existing $dest → $dest.bak"
  fi
  ln -s "$src" "$dest"
  green "  + $dest → $src"
}

check_deps() {
  echo "Dependency check:"
  local missing=0
  for t in bash python3 git zellij fzf lazygit nvim claude; do
    if command -v "$t" >/dev/null 2>&1; then
      dim "  ✓ $t ($(command -v "$t"))"
    else
      yellow "  ✗ $t — missing"; missing=1
    fi
  done
  [ "$missing" -eq 1 ] && yellow "  → install missing tools per REQUIREMENTS.md, then re-run."
  return 0
}

if [ "$CHECK_ONLY" -eq 1 ]; then
  check_deps
  exit 0
fi

echo "Installing from $REPO"
echo
echo "Linking scripts → $BIN_DIR"
for f in "$REPO"/bin/*; do
  link "$f" "$BIN_DIR/$(basename "$f")"
done

echo "Linking zellij config → $ZELLIJ_DIR"
link "$REPO/zellij/config.kdl"        "$ZELLIJ_DIR/config.kdl"
link "$REPO/zellij/layouts/agent.kdl" "$ZELLIJ_DIR/layouts/agent.kdl"

echo "Wiring up $BASHRC"
# Rewrite the block on every run so the path always matches the repo's current
# location (renaming/moving the repo then re-running install.sh self-heals).
# Strip any current- or legacy-marker block, trim trailing blanks, re-append.
touch "$BASHRC"
had_block=0
grep -qF "$MARKER" "$BASHRC" && had_block=1
grep -qF "$LEGACY_MARKER" "$BASHRC" && had_block=1
tmp="$(mktemp)"
sed -e "/$MARKER/,/$MARKER_END/d" -e "/$LEGACY_MARKER/,/$LEGACY_MARKER_END/d" "$BASHRC" \
  | awk 'NF{last=NR} {line[NR]=$0} END{for(i=1;i<=last;i++) print line[i]}' > "$tmp"
{
  echo ""
  echo "$MARKER"
  echo "source \"$REPO/shell/agent-workflow.sh\""
  echo "$MARKER_END"
} >> "$tmp"
mv "$tmp" "$BASHRC"
if [ "$had_block" -eq 1 ]; then
  green "  + refreshed source block → $REPO/shell/agent-workflow.sh"
else
  green "  + added source line to $BASHRC"
fi

if [ "$DO_GIT" -eq 1 ]; then
  echo "Installing global gitattributes (line endings)"
  link "$REPO/git/attributes" "$GITCFG_DIR/attributes"
  git config --global core.attributesfile "$GITCFG_DIR/attributes"
  git config --global core.autocrlf false
  green "  + git core.attributesfile / autocrlf set"
else
  dim "Skipping global git config (pass --git-config to enable line-ending rules)"
fi

echo
check_deps
echo
green "Done. Open a new shell (or 'source ~/.bashrc'), then run: proj"
