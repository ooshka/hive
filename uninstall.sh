#!/usr/bin/env bash
# uninstall.sh — remove the symlinks and ~/.bashrc source line that install.sh
# created. Leaves your installed tools and any <file>.bak backups untouched;
# if a backup exists where a symlink was, it is restored.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
ZELLIJ_DIR="$HOME/.config/zellij"
GITCFG_DIR="$HOME/.config/git"
BASHRC="$HOME/.bashrc"
MARKER="# >>> hive >>>"
MARKER_END="# <<< hive <<<"

dim() { printf '\033[2m%s\033[0m\n' "$1"; }

# unlink_one <dest>: remove our symlink; restore <dest>.bak if present.
unlink_one() {
  local dest="$1"
  if [ -L "$dest" ] && [[ "$(readlink -f "$dest")" == "$REPO/"* ]]; then
    rm "$dest"; echo "  - removed $dest"
    if [ -e "$dest.bak" ]; then mv "$dest.bak" "$dest"; echo "    restored $dest from .bak"; fi
  else
    dim "  · $dest not our symlink — left as-is"
  fi
}

echo "Uninstalling links that point into $REPO"
for f in "$REPO"/bin/*; do
  unlink_one "$BIN_DIR/$(basename "$f")"
done
unlink_one "$ZELLIJ_DIR/config.kdl"
unlink_one "$ZELLIJ_DIR/layouts/agent.kdl"
unlink_one "$GITCFG_DIR/attributes"

# Strip the marker block from ~/.bashrc, if present.
if grep -qF "$MARKER" "$BASHRC" 2>/dev/null; then
  tmp="$(mktemp)"
  sed "/$MARKER/,/$MARKER_END/d" "$BASHRC" > "$tmp"
  cp "$tmp" "$BASHRC"; rm -f "$tmp"
  echo "  - removed source block from $BASHRC"
else
  dim "  · no source block in $BASHRC"
fi

echo "Done. (Installed tools and global git config settings were left in place.)"
