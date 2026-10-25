import io
import os
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from hivelib import assistants


class AssistantTests(unittest.TestCase):
    def test_spawn_uses_native_assistant_layout_and_keeps_command(self):
        with patch.object(assistants, "_default", return_value="codex"), \
                patch.object(assistants, "_next_tab_name", return_value="codex:2"), \
                patch.object(assistants.os, "getcwd", return_value="/tmp/project"), \
                patch.object(assistants, "run", return_value=(0, "7")) as run, \
                patch.object(assistants, "_close_bootstrap") as close_bootstrap:
            self.assertEqual(assistants.spawn(), 0)

        run.assert_called_once_with([
            "zellij", "action", "new-tab", "--layout", "hive-assistant",
            "--name", "codex:2", "-c", "/tmp/project", "--",
            "hive", "pane", "Codex 2", "hive", "assistant-shell", "codex",
        ], timeout=5)
        close_bootstrap.assert_called_once_with()

    def test_start_spawns_assistant_then_focuses_editor(self):
        with patch.object(assistants, "_spawn", return_value=0) as spawn, \
                patch.object(assistants, "run", return_value=(0, "")) as run, \
                patch.object(assistants, "_close_bootstrap") as close_bootstrap:
            self.assertEqual(assistants.start(), 0)

        spawn.assert_called_once_with(close_bootstrap=False)
        run.assert_called_once_with(
            ["zellij", "action", "go-to-tab-name", "edit"], timeout=5)
        close_bootstrap.assert_called_once_with()

    def test_start_does_not_change_focus_when_spawn_fails(self):
        with patch.object(assistants, "_spawn", return_value=1), \
                patch.object(assistants, "run") as run, \
                patch.object(assistants, "_close_bootstrap") as close_bootstrap:
            self.assertEqual(assistants.start(), 1)

        run.assert_not_called()
        close_bootstrap.assert_not_called()

    def test_default_uses_claude_when_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(assistants._default(), "claude")

    def test_default_rejects_invalid_value(self):
        err = io.StringIO()
        with patch.dict(os.environ, {"HIVE_AGENT_DEFAULT": "vim"}, clear=False), redirect_stderr(err):
            self.assertIsNone(assistants._default())
        self.assertIn("Invalid HIVE_AGENT_DEFAULT", err.getvalue())

    def test_next_tab_name_uses_first_slot_when_none_exist(self):
        with patch.object(assistants, "_tabs", return_value=[]):
            self.assertEqual(assistants._next_tab_name("codex"), "codex:1")

    def test_next_tab_name_increments_existing_numbered_tabs(self):
        tabs = [{"name": "codex"}, {"name": "codex:2"}, {"name": "claude:9"}]
        with patch.object(assistants, "_tabs", return_value=tabs):
            self.assertEqual(assistants._next_tab_name("codex"), "codex:3")

    def test_active_tab_name_accepts_zellij_active_shapes(self):
        with patch.object(assistants, "_tabs", return_value=[
            {"name": "codex"},
            {"tab_name": "claude", "is_active": True},
        ]):
            self.assertEqual(assistants._active_tab_name(), "claude")


if __name__ == "__main__":
    unittest.main()
