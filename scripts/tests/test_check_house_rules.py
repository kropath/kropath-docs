#!/usr/bin/env python3
"""Unit tests for scripts/check-house-rules.py (spec AC-7 through AC-11)."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "check-house-rules.py"


def run(content_dir):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(content_dir)],
        capture_output=True,
        text=True,
    )


class CheckHouseRulesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.content = Path(self.tmp.name) / "content"
        self.content.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        path = self.content / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_clean_page_passes(self):
        self.write(
            "clean.md",
            "# Title\n\n"
            "```yaml\n"
            "apiVersion: aws.kropath.run/v1alpha1\n"
            "kind: S3Config\n"
            "```\n",
        )
        result = run(self.content)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rule1_bare_api_group_fails(self):
        # AC-7: a page containing apiVersion: kropath.run/v1alpha1 fails
        # citing house rule 1.
        path = self.write(
            "bare-group.md",
            "```yaml\napiVersion: kropath.run/v1alpha1\nkind: S3Config\n```\n",
        )
        result = run(self.content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(path), result.stderr)
        self.assertIn("kropath.run/", result.stderr)

    def test_rule1_allows_provider_prefixed_group(self):
        self.write(
            "prefixed-group.md",
            "```yaml\napiVersion: aws.kropath.run/v1alpha1\n```\n",
        )
        result = run(self.content)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rule2_provider_prefixed_kind_fails(self):
        # AC-8: a page containing the kind AWSS3Config fails citing house
        # rule 2 (KRO-433).
        path = self.write("prefixed-kind.md", "```yaml\nkind: AWSS3Config\n```\n")
        result = run(self.content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(path), result.stderr)
        self.assertIn("KRO-433", result.stderr)

    def test_rule3_externalref_cel_metadata_name_fails(self):
        # AC-9: externalRef with metadata.name set to a CEL expression fails
        # citing house rule 3.
        path = self.write(
            "cel-externalref.md",
            "```yaml\n"
            "externalRef:\n"
            "  metadata:\n"
            '    name: "${spec.configRef}"\n'
            "```\n",
        )
        result = run(self.content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(path), result.stderr)
        self.assertIn("selector.matchLabels", result.stderr)

    def test_rule3_allows_selector_matchlabels(self):
        self.write(
            "good-externalref.md",
            "```yaml\n"
            "externalRef:\n"
            "  selector:\n"
            "    matchLabels:\n"
            "      aws.kropath.run/resource-name: general-policy\n"
            "```\n",
        )
        result = run(self.content)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rule4_internal_repo_link_fails(self):
        # AC-10: a page linking to github.com/kropath/kropath-core fails
        # citing house rule 4.
        path = self.write(
            "internal-link.md",
            "See [the ADR](https://github.com/kropath/kropath-core/blob/main/docs/adrs/015.md).\n",
        )
        result = run(self.content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(path), result.stderr)

    def test_rule6_ticket_citation_fails(self):
        # AC-11: a page citing ADR-015, KRO-1248, or a mention:// link in
        # prose fails citing house rule 6.
        path = self.write("citation.md", "This behavior follows KRO-1248.\n")
        result = run(self.content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(path), result.stderr)

    def test_rule6_adr_citation_fails(self):
        path = self.write("adr-citation.md", "Required per ADR-015.\n")
        result = run(self.content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(path), result.stderr)

    def test_escape_hatch_allows_documented_exception(self):
        self.write(
            "escaped.md",
            "```yaml\napiVersion: kropath.run/v1alpha1  <!-- house-rules:allow=1 -->\n```\n",
        )
        result = run(self.content)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
