"""Opt-in native Zellij regression test: python3 tests/smoke_zellij.py.

Requires the built WASM plugin and Zellij 0.44.3. Creates an isolated session,
approves its plugin prompt, sends real Alt keypresses, and closes the test session.
Temporary logs are kept under /tmp for debugging.
"""
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import tempfile
import termios
import time

root = Path(__file__).resolve().parents[1]
scratch = Path(tempfile.mkdtemp(prefix='hive-plugin-smoke-'))
env = {k: v for k, v in os.environ.items() if not k.startswith('ZELLIJ')}
env.update(XDG_CACHE_HOME=str(scratch / 'cache'), XDG_RUNTIME_DIR=str(scratch / 'run'), TERM='xterm-256color')
(scratch / 'run').mkdir(mode=0o700)
wasm = root / 'plugins/hive-orchestrator/target/wasm32-wasip1/debug/hive-orchestrator.wasm'
config = (root / 'zellij/config.kdl').read_text().replace('file:~/.config/zellij/plugins/hive-orchestrator.wasm', f'file:{wasm}')
(scratch / 'config.kdl').write_text(config)
(scratch / 'layout.kdl').write_text('''layout {
    tab name="edit" { pane name="Editor - smoke" command="bash"; }
    tab name="git" { pane name="Git - smoke" command="bash"; }
}''')
session = f'hive-smoke-{os.getpid()}'
master, slave = pty.openpty()
fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 60, 100, 0, 0))
def terminal_session():
    os.setsid()
    fcntl.ioctl(0, termios.TIOCSCTTY, 0)

proc = subprocess.Popen(['zellij', '--config', str(scratch / 'config.kdl'), '--session', session, '--new-session-with-layout', str(scratch / 'layout.kdl')], env=env, stdin=slave, stdout=slave, stderr=slave, preexec_fn=terminal_session)
os.close(slave)

def drain(seconds=1):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if select.select([master], [], [], .1)[0]:
            try:
                output = os.read(master, 65536)
            except OSError:
                break
            with (scratch / 'terminal.log').open('ab') as log:
                log.write(output)

def action(*args):
    result = subprocess.run(['zellij', '--session', session, 'action', *args], env=env, capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout

def panes():
    return [p for p in json.loads(action('list-panes', '--json', '--all')) if not p['is_plugin']]

def focused_tab():
    return next(t['name'] for t in json.loads(action('list-tabs', '--json')) if t['active'])

def key(value):
    os.write(master, b'\x1b' + value.encode())
    drain(1)

def check_split(agent_title):
    state = panes()
    assert {p['id'] for p in state} == original_ids, state
    editor = next(p for p in state if p['title'] == 'Editor - smoke')
    agent = next(p for p in state if p['title'] == agent_title)
    assert editor['tab_id'] == agent['tab_id'], state
    assert editor['pane_x'] > agent['pane_x'], state
    assert editor['pane_y'] == agent['pane_y'], state
    assert editor['pane_rows'] == agent['pane_rows'] == 60, state
    print('PASS split:', agent_title, flush=True)

def check_unsplit(agent_title):
    state = panes()
    assert {p['id'] for p in state} == original_ids, state
    editor = next(p for p in state if p['title'] == 'Editor - smoke')
    agent = next(p for p in state if p['title'] == agent_title)
    assert editor['tab_name'] == 'edit', state
    assert agent['pane_columns'] == 100 and agent['is_focused'], state
    assert focused_tab() == agent['tab_name'], state
    print('PASS unsplit:', agent_title, flush=True)

try:
    drain(5)
    print('scratch:', scratch, flush=True)
    os.write(master, b'y')
    drain(2)
    for tab, title in [('codex:1', 'Codex - smoke'), ('claude:1', 'Claude - smoke')]:
        action('new-tab', '--layout', str(root / 'zellij/layouts/hive-assistant.kdl'), '--name', tab, '--', 'bash')
        drain(1)
        action('rename-pane', title)
    action('go-to-tab-name', 'codex:1')
    drain(1)
    original_ids = {p['id'] for p in panes()}
    assert len(original_ids) == 4
    key('s')
    check_split('Codex - smoke')
    key('s')
    check_unsplit('Codex - smoke')
    key('1')
    assert focused_tab() == 'claude:1'
    key('s')
    check_split('Claude - smoke')
    key('1')
    check_split('Codex - smoke')
    key('s')
    check_unsplit('Codex - smoke')
    key('2')
    assert focused_tab() == 'edit'
    key('s')
    check_split('Codex - smoke')
    key('f')
    assert any(p['is_fullscreen'] for p in panes())
    key('s')
    check_unsplit('Codex - smoke')
    key('3')
    assert focused_tab() == 'git'
    key('s')
    check_split('Codex - smoke')
    key('s')
    check_unsplit('Codex - smoke')
    # A new agent while unsplit should remain full width.
    action('new-tab', '--layout', str(root / 'zellij/layouts/hive-assistant.kdl'), '--name', 'codex:2', '--', 'bash')
    drain(1)
    action('rename-pane', 'Codex 2 - smoke')
    drain(1)
    new_ids = {p['id'] for p in panes()}
    assert original_ids < new_ids and len(new_ids - original_ids) == 1
    original_ids = new_ids
    check_unsplit('Codex 2 - smoke')
    key('s')
    check_split('Codex 2 - smoke')
    # Reproduce Alt-a's new-tab then asynchronous Hive pane rename.
    action('new-tab', '--layout', str(root / 'zellij/layouts/hive-assistant.kdl'), '--name', 'codex:3', '--', 'bash')
    drain(1)
    action('rename-pane', 'Codex 3 - smoke')
    drain(1)
    new_ids = {p['id'] for p in panes()}
    assert original_ids < new_ids and len(new_ids - original_ids) == 1
    original_ids = new_ids
    check_split('Codex 3 - smoke')
    assert focused_tab() == 'codex:3'
    assert next(p for p in panes() if p['title'] == 'Codex 3 - smoke')['is_focused']
    key('s')
    check_unsplit('Codex 3 - smoke')
    key('x')
    assert not any(p['title'] == 'Codex 3 - smoke' for p in panes())
    original_ids = {p['id'] for p in panes()}
    action('go-to-tab-name', 'codex:2')
    drain(1)
    key('s')
    check_split('Codex 2 - smoke')
    key('x')
    state = panes()
    assert not any(p['title'] == 'Codex 2 - smoke' for p in state), state
    assert next(p for p in state if p['title'] == 'Editor - smoke')['tab_name'] == 'edit', state
    action('go-to-tab-name', 'codex:1')
    drain(1)
    key('x')
    assert any(p['title'] == 'Codex - smoke' for p in panes())
    print('PASS native keybindings, including assistant close', flush=True)
finally:
    subprocess.run(['zellij', 'kill-session', session], env=env, capture_output=True, timeout=10)
    drain(1)
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=3)
    os.close(master)
