import os
import tempfile
import unittest
from unittest.mock import patch

from hivelib import projects


class ProjectTests(unittest.TestCase):
    def test_roots_reads_colon_separated_env(self):
        with patch.dict(os.environ, {"PROJ_ROOTS": "/one::/two"}, clear=False):
            self.assertEqual(projects.roots(), ["/one", "/two"])

    def test_sanitize_uses_basename_and_zellij_safe_chars(self):
        self.assertEqual(projects.sanitize("/tmp/my project/main.app/"), "main_app")
        self.assertEqual(projects.sanitize("/tmp/ok_name-1"), "ok_name-1")

    def test_list_projects_returns_immediate_subdirectories_sorted_per_root(self):
        with tempfile.TemporaryDirectory() as root_a, tempfile.TemporaryDirectory() as root_b:
            os.mkdir(os.path.join(root_a, "zeta"))
            os.mkdir(os.path.join(root_a, "alpha"))
            open(os.path.join(root_a, "README.md"), "w", encoding="utf-8").close()
            os.mkdir(os.path.join(root_b, "beta"))

            with patch.dict(os.environ, {"PROJ_ROOTS": f"{root_a}:{root_b}"}, clear=False):
                self.assertEqual(projects.list_projects(), [
                    os.path.join(root_a, "alpha"),
                    os.path.join(root_a, "zeta"),
                    os.path.join(root_b, "beta"),
                ])


if __name__ == "__main__":
    unittest.main()
