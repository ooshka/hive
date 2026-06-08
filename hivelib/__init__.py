"""hivelib — the logic behind the `hive` command (zellij/Claude agent workspace).

Process orchestration (launching tools, zellij actions) stays thin; this package
holds the data + logic: session/worktree-agent discovery, status, stream-json
formatting, the fleet view, and the fzf pickers. The `hive` entry point (bin/hive)
adds the repo to sys.path and calls hivelib.cli.main.
"""
