#!/usr/bin/env python3
"""Unit tests for scripts/backfill-frontmatter.py."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "backfill-frontmatter.py"


def run(content_dir):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(content_dir)],
        capture_output=True,
        text=True,
    )


class BackfillFrontmatterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.content = Path(self.tmp.name) / "content"
        self.docs = self.content / "en" / "docs"
        self.docs.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_seeds_title_description_and_doc_type_from_h1_and_first_sentence(self):
        page = self.docs / "reference" / "s3config.md"
        page.parent.mkdir(parents=True)
        page.write_text(
            "# S3Config\n\n"
            "Mandatory and default settings applied to S3 buckets. Extra detail follows.\n",
            encoding="utf-8",
        )
        result = run(self.content)
        self.assertEqual(result.returncode, 0, result.stderr)

        text = page.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("title: S3Config", text)
        self.assertIn(
            "description: Mandatory and default settings applied to S3 buckets.", text
        )
        self.assertIn("doc_type: reference", text)
        # The H1 and body are untouched below the injected front matter.
        self.assertIn("# S3Config\n\nMandatory and default", text)

    def test_does_not_overwrite_existing_keys(self):
        page = self.docs / "tasks" / "existing.md"
        page.parent.mkdir(parents=True)
        page.write_text(
            "---\ntitle: Custom Title\n---\n\n# Ignored H1\n\nSome body text.\n",
            encoding="utf-8",
        )
        run(self.content)
        text = page.read_text(encoding="utf-8")
        self.assertIn("title: Custom Title", text)
        self.assertNotIn("Ignored H1\ntitle", text)

    def test_warns_on_index_missing_weight(self):
        index = self.docs / "reference" / "aws" / "_index.md"
        index.parent.mkdir(parents=True)
        index.write_text("# AWS\n\nAWS resources.\n", encoding="utf-8")
        result = run(self.content)
        self.assertIn("weight", result.stderr)


if __name__ == "__main__":
    unittest.main()
