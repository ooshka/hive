"""Pre-seed zellij's plugin permission cache.

hive-orchestrator loads as a headless background plugin (see `load_plugins`
in zellij/config.kdl), which gives zellij's interactive permission prompt no
pane to render into. install.sh calls this to grant its permissions
non-interactively instead, writing the same cache file zellij itself would
write after a successful interactive grant.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PERMISSIONS = ["ReadCliPipes", "ReadApplicationState", "ChangeApplicationState"]


def grant(cache_path: Path, plugin_path: str) -> None:
    block = '"%s" {\n    %s\n}\n' % (plugin_path, "\n    ".join(PERMISSIONS))

    existing = cache_path.read_text() if cache_path.exists() else ""
    pattern = re.compile(r'^"%s"\s*\{[^}]*\}\n?' % re.escape(plugin_path), re.MULTILINE)
    existing = pattern.sub("", existing)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(existing + block)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: zellij_permissions.py <cache_path> <plugin_path>", file=sys.stderr)
        return 2
    grant(Path(argv[0]), argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
