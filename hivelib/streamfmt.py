"""Render a worktree agent's stream-json log into readable lines.

Replaces the old jq formatter (which lived in a bash heredoc). Each log line is a
standalone JSON event (system/init, assistant, user, result, …); non-JSON lines
(e.g. the stdin warning the agent emits at startup) are passed through dimmed.
ANSI is always emitted — output is shown in a pane or rendered by fzf's preview.
"""
from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from .util import paint, DIM, GREEN, RED, CYAN


def format_event(ev: dict[str, Any]) -> str | None:
    """One readable line for a parsed event, or None to skip it."""
    t = ev.get("type")

    if t == "system" and ev.get("subtype") == "init":
        tools = len(ev.get("tools") or [])
        return paint(DIM, f"▸ init  model={ev.get('model', '?')}  tools={tools}")

    if t == "assistant":
        parts: list[str] = []
        for b in (ev.get("message", {}).get("content") or []):
            bt = b.get("type")
            if bt == "text" and (b.get("text") or "").strip():
                parts.append(b["text"].strip())
            elif bt == "tool_use":
                inp = json.dumps(b.get("input", {}))[:80]
                parts.append(paint(CYAN, f"⚙ {b.get('name', '?')}") + f"({inp})")
        body = "  ".join(p for p in parts if p)
        return f"🗣 {body}" if body else None

    if t == "user":
        parts = []
        for b in (ev.get("message", {}).get("content") or []):
            if b.get("type") == "tool_result":
                c = b.get("content")
                if isinstance(c, list):
                    text = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                else:
                    text = str(c)
                err = paint(RED, "ERR ") if b.get("is_error") else ""
                parts.append(paint(DIM, "← ") + err + text[:80])
        return "  ".join(parts) if parts else None

    if t == "result":
        head = paint(GREEN, "✓") if not ev.get("is_error") else paint(RED, "✗")
        cost = round((ev.get("total_cost_usd") or 0) * 1000) / 1000
        res = (ev.get("result") or "")[:60]
        return f"{head} {ev.get('subtype', '')}  turns={ev.get('num_turns', '?')}  ${cost}  \"{res}\""

    if t == "rate_limit_event":
        return None

    return paint(DIM, f"· [{t}]")


def format_line(raw: str) -> str | None:
    raw = raw.rstrip("\n")
    try:
        ev = json.loads(raw)
    except Exception:
        return paint(DIM, f"  · {raw}") if raw.strip() else None
    if not isinstance(ev, dict):
        return paint(DIM, f"  · {raw}")
    return format_event(ev)


def view(log: str, raw: bool = False, follow: bool = True, tail_lines: int = 60) -> int:
    """Print the log (formatted, or full JSON with --raw), optionally following.
    Ctrl-c exits cleanly (which, in a pane with close_on_exit, closes the pane)."""
    cmd = ["tail", "-n", "200", "-f", log] if follow else ["tail", "-n", str(tail_lines), log]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    except Exception as e:
        print(f"hive wt log: {e}", file=sys.stderr)
        return 1
    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            if raw:
                try:
                    print(json.dumps(json.loads(line), indent=2))
                except Exception:
                    print(line.rstrip("\n"))
            else:
                out = format_line(line)
                if out is not None:
                    print(out, flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
    return 0
