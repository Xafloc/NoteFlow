"""Unit tests for NoteFlow performance / safety / capability improvements."""
from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path

from noteflow import ai as ai_module
from noteflow import folders as folders_module
from noteflow.noteflow import (
    NoteManager,
    _safe_upload_filename,
    _unique_path,
    normalize_list_markers,
    parse_markdown,
    set_task_lookup,
)


class SafeUploadTests(unittest.TestCase):
    def test_strips_path_components(self):
        self.assertEqual(_safe_upload_filename("../../etc/passwd"), "passwd")
        self.assertEqual(_safe_upload_filename("a/b/c.png"), "c.png")

    def test_rejects_dot_names(self):
        name = _safe_upload_filename("..")
        self.assertNotIn("..", name)
        self.assertTrue(name)

    def test_unique_path_increments(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "photo.png").write_bytes(b"x")
            p = _unique_path(d, "photo.png")
            self.assertEqual(p.name, "photo-1.png")
            p.write_bytes(b"y")
            p2 = _unique_path(d, "photo.png")
            self.assertEqual(p2.name, "photo-2.png")


class NoteManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.nm = NoteManager(self.base)

    def tearDown(self):
        self.tmp.cleanup()

    def test_atomic_save_creates_notes_md(self):
        self.nm.add_note("t", "- [ ] task one\n")
        self.nm.save()
        path = self.base / "notes.md"
        self.assertTrue(path.exists())
        self.assertFalse(path.with_suffix(".md.tmp").exists())
        text = path.read_text(encoding="utf-8")
        self.assertIn("task one", text)
        self.assertTrue(text.startswith("## "))

    def test_reindex_after_update_is_contiguous(self):
        self.nm.add_note("a", "- [ ] alpha\n- [ ] beta\n")
        self.nm.add_note("b", "- [ ] gamma\n")
        self.nm.save()
        # Two notes: newest first. Indices should be 0,1 on first note, 2 on second.
        indexes = [t.index for n in self.nm.notes for t in n.tasks]
        self.assertEqual(indexes, list(range(len(indexes))))

        # Update the second note (older) — reindex should keep contiguous ids.
        self.nm.notes[1].update("a", "- [ ] alpha only\n")
        self.nm.save()
        indexes = [t.index for n in self.nm.notes for t in n.tasks]
        self.assertEqual(indexes, list(range(len(indexes))))
        self.assertEqual(len(indexes), 2)  # gamma + alpha only

    def test_task_toggle_persists(self):
        self.nm.add_note("", "- [ ] buy milk\n")
        self.nm.save()
        idx = self.nm.notes[0].tasks[0].index
        self.assertTrue(self.nm.update_task(idx, True))
        self.nm.save()
        text = (self.base / "notes.md").read_text(encoding="utf-8")
        self.assertIn("[x]", text)
        self.assertTrue(self.nm.notes[0].tasks[0].checked)

    def test_reload_picks_up_external_edit(self):
        self.nm.add_note("", "hello world\n")
        self.nm.save()
        path = self.base / "notes.md"
        # External writer appends a note.
        time.sleep(0.02)  # ensure mtime advances on coarse FS clocks
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        extra = f"\n<!-- note -->\n## {stamp} - external\n\nfrom disk\n"
        path.write_text(path.read_text(encoding="utf-8") + extra, encoding="utf-8")
        # Nudge mtime explicitly for filesystems with low resolution.
        os.utime(path, None)
        self.assertTrue(self.nm.disk_changed())
        self.assertTrue(self.nm.reload_if_changed())
        titles = [n.title for n in self.nm.notes]
        self.assertTrue(any("external" in (t or "") for t in titles) or any(
            "from disk" in n.content for n in self.nm.notes
        ))

    def test_reload_skipped_when_dirty(self):
        self.nm.add_note("", "local\n")
        self.nm.save()
        path = self.base / "notes.md"
        time.sleep(0.02)
        path.write_text(path.read_text(encoding="utf-8") + "\nTAMPER\n", encoding="utf-8")
        os.utime(path, None)
        self.nm.needs_save = True  # pretend user is mid-edit
        self.assertFalse(self.nm.reload_if_changed())
        self.assertNotIn("TAMPER", self.nm.notes[0].content)

    def test_html_cache_reused(self):
        self.nm.add_note("", "plain **bold** text\n")
        set_task_lookup(self.nm.build_task_lookup())
        h1 = self.nm.notes[0].rendered_html()
        h2 = self.nm.notes[0].rendered_html()
        self.assertEqual(h1, h2)
        self.assertIs(self.nm.notes[0]._html_cache[1], h2)
        self.nm.notes[0].content = "changed"
        self.nm.notes[0]._html_cache = None
        h3 = self.nm.notes[0].rendered_html()
        self.assertNotEqual(h1, h3)


class MarkdownTests(unittest.TestCase):
    def test_bullet_lookalike_normalized(self):
        src = "• item one\n– item two\n"
        out = normalize_list_markers(src)
        self.assertTrue(out.startswith("- item one"))
        self.assertIn("- item two", out)

    def test_parse_markdown_checkbox_uses_lookup(self):
        # Task text is captured from the checkbox position (no list marker),
        # matching Note._extract_task_text / build_task_lookup.
        set_task_lookup({"[ ] demo task": 7})
        html = parse_markdown("- [ ] demo task\n")
        self.assertIn('data-checkbox-index="7"', html)


class FoldersExtractTests(unittest.TestCase):
    def test_extract_tasks_skips_code_and_is_linear(self):
        content = (
            "## 2024-01-01 00:00:00 - demo\n\n"
            "- [ ] real task\n"
            "```\n"
            "- [ ] fake in code\n"
            "```\n"
            "- [x] done task\n"
            "inline `- [ ] not a task` here\n"
        )
        tasks = folders_module.FolderRegistry._extract_tasks(content)
        texts = [t["content"] for t in tasks]
        self.assertEqual(len(tasks), 2)
        self.assertTrue(any("real task" in t for t in texts))
        self.assertTrue(any("done task" in t for t in texts))
        self.assertFalse(any("fake in code" in t for t in texts))


class AIContextTests(unittest.TestCase):
    def test_recent_notes(self):
        sep = ai_module.NOTE_SEPARATOR
        notes = sep.join([
            "## 2024-01-03 00:00:00 - third\n\nC\n",
            "## 2024-01-02 00:00:00 - second\n\nB\n",
            "## 2024-01-01 00:00:00 - first\n\nA\n",
        ])
        out = ai_module.select_context(notes, "recent:2")
        self.assertIn("third", out)
        self.assertIn("second", out)
        self.assertNotIn("first", out)

    def test_note_index(self):
        sep = ai_module.NOTE_SEPARATOR
        notes = sep.join(["## t1\n\none\n", "## t2\n\ntwo\n"])
        out = ai_module.select_context(notes, "note:1")
        self.assertIn("two", out)
        self.assertNotIn("one", out)

    def test_none_and_selection(self):
        self.assertEqual(ai_module.select_context("abc", "none"), "")
        self.assertEqual(
            ai_module.select_context("abc", "selection", selection="just this"),
            "just this",
        )

    def test_char_budget_truncates(self):
        big = "x" * (ai_module.CONTEXT_CHAR_BUDGET + 5000)
        out = ai_module.select_context(big, "all")
        self.assertLessEqual(len(out), ai_module.CONTEXT_CHAR_BUDGET + 80)
        self.assertIn("truncated", out)

    def test_build_messages_roles(self):
        msgs = ai_module.build_messages(
            [{"role": "user", "content": "hi"}],
            "none",
            notes_text="",
        )
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[1]["content"], "hi")
        self.assertIn("opted out", msgs[0]["content"])


if __name__ == "__main__":
    unittest.main()
