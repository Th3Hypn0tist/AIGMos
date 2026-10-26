"""Stdlib-only regression tests for terminal cell utilities."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "system/layout/lib/textcells.py"
spec = importlib.util.spec_from_file_location("aigmos_textcells_stdlib_test", MODULE_PATH)
assert spec is not None and spec.loader is not None
textcells = importlib.util.module_from_spec(spec)
spec.loader.exec_module(textcells)


class TextCellsStdlibTests(unittest.TestCase):
    def test_single_char_width(self):
        self.assertEqual(textcells.char_cells("A"), 1)
        self.assertEqual(textcells.char_cells("界"), 2)
        self.assertEqual(textcells.char_cells("😀"), 2)
        # Existing char_cells contract clamps zero/negative wcwidth to 1.
        self.assertEqual(textcells.char_cells("\u0301"), 1)
        self.assertEqual(textcells.char_cells("\t"), 1)
        self.assertEqual(textcells.char_cells(""), 1)

    def test_text_clipping_padding_and_cursor(self):
        self.assertEqual(textcells.text_cells("a界b"), 4)
        self.assertEqual(textcells.clip_cells("a界b", 2), "a")
        self.assertEqual(textcells.clip_cells("a界b", 3), "a界")
        self.assertEqual(textcells.ljust_cells("a界", 5), "a界  ")
        self.assertEqual(textcells.cursor_insert_index_for_cells("a界b", 2), 2)
        self.assertEqual(textcells.insert_cursor_marker("a界b", 3), "a界|b")


if __name__ == "__main__":
    unittest.main()
