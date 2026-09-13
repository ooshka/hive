"""hivelib — the logic behind the `hive` command (zellij assistant workspace).

Process orchestration (launching tools, zellij actions) stays thin; this package
holds the data + logic: project discovery, assistant tab control, zellij helpers,
and the fzf picker. The `hive` entry point (bin/hive) adds the repo to sys.path
and calls hivelib.cli.main.
"""
