"""fzf wrapper shared by the open / switch / agents pickers."""
from __future__ import annotations

import subprocess
from collections.abc import Sequence


def fzf(lines: Sequence[str], *, prompt: str = "> ", header: str | None = None,
        delimiter: str | None = None, with_nth: str | None = None,
        expect: Sequence[str] = (), preview: str | None = None,
        preview_window: str | None = None, ansi: bool = True,
        height: str = "100%", query: str | None = None,
        select_1: bool = False, exit_0: bool = False) -> tuple[str, str] | None:
    """Run fzf over `lines`. Returns (key, selected_line), or None if cancelled.

    `key` is "" for Enter, or the name of an --expect key (e.g. "ctrl-k"). fzf
    draws its UI on /dev/tty, so this works fine from inside a (piped) script.
    """
    args = ["fzf", "--reverse", "--no-multi", "--height", height, "--prompt", prompt]
    if header:
        args += ["--header", header]
    if delimiter:
        args += ["--delimiter", delimiter]
    if with_nth:
        args += ["--with-nth", with_nth]
    if expect:
        args += ["--expect", ",".join(expect)]
    if preview:
        args += ["--preview", preview]
    if preview_window:
        args += ["--preview-window", preview_window]
    if ansi:
        args.append("--ansi")
    if query:
        args += ["--query", query]
    if select_1:
        args.append("--select-1")
    if exit_0:
        args.append("--exit-0")
    try:
        r = subprocess.run(args, input="\n".join(lines), text=True, stdout=subprocess.PIPE)
    except FileNotFoundError:
        return None
    out = r.stdout.splitlines()
    if not out:
        return None
    if expect:
        key = out[0]
        sel = out[1] if len(out) > 1 else ""
        return (key, sel) if sel else None
    return "", out[0]
