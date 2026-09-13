"""hivelib — the logic behind the `hive` command (zellij assistant workspace).

Process orchestration (launching tools, zellij actions) stays thin; this package
holds the data + logic: worktree-agent discovery, status, stream-json formatting,
and the fzf pickers. The `hive` entry point (bin/hive) adds the repo to sys.path
and calls hivelib.cli.main.
"""
