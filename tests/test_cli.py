import io
import unittest
from contextlib import redirect_stdout

from hivelib import cli


class CliTests(unittest.TestCase):
    def test_help_lists_current_commands_without_removed_fleet_command(self):
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as cm:
            cli.main(["--help"])

        self.assertEqual(cm.exception.code, 0)
        help_text = out.getvalue()
        self.assertIn("assistant", help_text)
        self.assertIn("switch", help_text)
        self.assertIn("close", help_text)
        self.assertNotIn("fleet", help_text)
        self.assertNotIn("agents", help_text)
        self.assertNotIn(" wt ", help_text)


if __name__ == "__main__":
    unittest.main()
