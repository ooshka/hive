# hive-orchestrator

Zellij plugin for Hive's live assistant/editor choreography.

It receives `MessagePlugin` keybinds from `zellij/config.kdl`. Alt-s moves the
existing `Editor - ...` pane to the active assistant's right and focuses it.
Pressing Alt-s again returns that pane to `edit` and focuses the full-width
assistant. Alt-1 cycles assistants, carrying the editor along when split.
Spawning an assistant with Alt-a also carries the split editor to the new tab
and leaves keyboard focus on the new agent.
Alt-x closes the active assistant tab while preserving the first one. If the
editor is split beside it, the editor returns to its own tab before closing.

Zellij 0.44.3 mixes tab positions and stable IDs in its break-to-existing-tab
implementation. This plugin instead groups panes by their pane IDs with
`stack_panes`, then applies the native `hive-side-by-side` swap layout to unstack
them. The layout lives in `zellij/layouts/hive-assistant.kdl`, which Hive uses
when spawning assistants. Neither tool process is restarted.

The crate is intentionally built as a WASI binary, matching Zellij's Rust plugin
example. Cargo writes the plugin artifact to
`target/wasm32-wasip1/debug/hive-orchestrator.wasm`.

## Build

```bash
rustup target add wasm32-wasip1
cargo build --locked --manifest-path plugins/hive-orchestrator/Cargo.toml --target wasm32-wasip1
./install.sh
```

Accept the native Zellij permission prompt on first launch. After upgrading
from the Python keybinds or an older plugin, start a fresh Hive session so the
background plugin and assistant swap layout are loaded together. Existing
sessions keep their loaded WASM and layouts.

## Verification

```bash
python3 -m unittest discover -v
python3 tests/smoke_zellij.py
```

The opt-in smoke test requires Zellij 0.44.3 and the built WASM. It creates its
own temporary session, approves that session's plugin prompt, sends real Alt
keypresses, and verifies pane IDs, geometry, and focus across repeated toggles
and assistant cycling. It closes only its own session and retains logs in `/tmp`.
