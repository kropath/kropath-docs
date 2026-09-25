#!/usr/bin/env python3
"""Unit tests for scripts/check-frontmatter.py (spec AC-5, AC-6).

Runs the script as a subprocess against a throwaway content/ tree so the
tests exercise exactly the CLI contract `make lint` relies on, independent
of the hyphenated filename that prevents a normal `import`.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "check-frontmatter.py"


def run(content_dir):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(content_dir)],
        capture_output=True,
        text=True,
    )


class CheckFrontmatterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.content = Path(self.tmp.name) / "content"
        self.docs = self.content / "en" / "docs"
        self.docs.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel_path, text):
        path = self.docs / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_valid_page_passes(self):
        self.write(
            "reference/s3config.md",
            "---\n"
            "title: S3Config\n"
            "description: >\n"
            "  Mandatory and default settings applied to S3 buckets.\n"
            "doc_type: reference\n"
            "---\n\nBody.\n",
        )
        result = run(self.content)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_wrong_doc_type_for_section_fails(self):
        # AC-5: doc_type: task placed under concepts/ must fail, naming the
        # file, the declared doc_type, and the section it sits in.
        path = self.write(
            "concepts/misplaced.md",
            "---\n"
            "title: Misplaced\n"
            "description: >\n"
            "  A page in the wrong section.\n"
            "doc_type: task\n"
            "---\n\nBody.\n",
        )
        result = run(self.content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(path), result.stderr)
        self.assertIn("task", result.stderr)
        self.assertIn("concepts", result.stderr)

    def test_missing_title_fails_naming_the_key(self):
        # AC-6: a page missing title or description fails at path:line
        # naming the missing key.
        path = self.write(
            "reference/no-title.md",
            "---\n"
            "description: >\n"
            "  Missing a title.\n"
            "doc_type: reference\n"
            "---\n\nBody.\n",
        )
        result = run(self.content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(path), result.stderr)
        self.assertIn("title", result.stderr)

    def test_missing_description_fails_naming_the_key(self):
        path = self.write(
            "reference/no-description.md",
            "---\ntitle: No Description\ndoc_type: reference\n---\n\nBody.\n",
        )
        result = run(self.content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(path), result.stderr)
        self.assertIn("description", result.stderr)

    def test_index_without_weight_fails(self):
        path = self.write(
            "reference/_index.md",
            "---\ntitle: Reference\ndescription: >\n  Reference landing page.\ndoc_type: reference\n---\n",
        )
        result = run(self.content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(path), result.stderr)
        self.assertIn("weight", result.stderr)

    def test_non_integer_weight_fails(self):
        path = self.write(
            "reference/_index.md",
            "---\ntitle: Reference\ndescription: >\n  Reference landing page.\ndoc_type: reference\nweight: fifty\n---\n",
        )
        result = run(self.content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(path), result.stderr)
        self.assertIn("integer", result.stderr)

    def test_site_root_pages_exempt_from_doc_type(self):
        # content/en/_index.md and content/en/docs/_index.md sit outside any
        # of the six sections and are not required to declare doc_type.
        site_root = self.content / "en"
        site_root.mkdir(parents=True, exist_ok=True)
        (site_root / "_index.md").write_text(
            "---\ntitle: kropath\ndescription: >\n  Home page.\nweight: 1\n---\n",
            encoding="utf-8",
        )
        (self.docs / "_index.md").write_text(
            "---\ntitle: Documentation\ndescription: >\n  Docs root.\nweight: 1\n---\n",
            encoding="utf-8",
        )
        result = run(self.content)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
