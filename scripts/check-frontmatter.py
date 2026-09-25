#!/usr/bin/env python3
"""Front-matter contract lint for kropath-docs (spec docs-website.md §6.2, §8).

Every published page — including every _index.md — must carry `title` and
`description`. `_index.md` pages must also carry an integer `weight`. Every
page placed under a recognised content/en/docs/<section>/ subtree must carry
`doc_type` matching that section's required value (kind naming: enum values,
not directory names).

No PyYAML dependency: front matter here is a small, well-known subset (flat
`key: value` pairs plus a `>` folded block scalar for `description`), so a
hand-rolled parser keeps `make deps` free of a pip step.
"""
import re
import sys
from pathlib import Path

DOC_TYPES = {
    "getting-started",
    "concept",
    "task",
    "tutorial",
    "reference",
    "contribution",
}

# Section directory name -> required doc_type value. Directory names are not
# identical to the enum (plural vs singular etc.), so this map is authoritative.
SECTION_DOC_TYPE = {
    "getting-started": "getting-started",
    "concepts": "concept",
    "tasks": "task",
    "tutorials": "tutorial",
    "reference": "reference",
    "contribution": "contribution",
}

REQUIRED_KEYS = ("title", "description")


class LintError(Exception):
    def __init__(self, path, line, message):
        super().__init__(f"{path}:{line}: {message}")
        self.path = path
        self.line = line
        self.message = message


def parse_frontmatter(text, path):
    """Return (dict of key -> (value, line_no), body_start_line)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise LintError(path, 1, "missing front matter (file must start with '---')")
    fm = {}
    i = 1
    n = len(lines)
    while i < n and lines[i].strip() != "---":
        line = lines[i]
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, value = m.group(1), m.group(2).strip()
        key_line = i + 1
        if value == ">" or value == "|":
            # Folded/literal block scalar: collect subsequent indented lines.
            j = i + 1
            block_lines = []
            while j < n and (lines[j].startswith("  ") or lines[j].strip() == ""):
                if lines[j].strip():
                    block_lines.append(lines[j].strip())
                j += 1
            value = " ".join(block_lines)
            i = j
            fm[key] = (value, key_line)
            continue
        # Strip inline quotes.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fm[key] = (value, key_line)
        i += 1
    if i >= n:
        raise LintError(path, n, "front matter is not terminated with a closing '---'")
    return fm, i + 1


def section_for(path, docs_root):
    """Return the top-level docs/<section> directory name, or None if the
    page is content/en/_index.md or content/en/docs/_index.md (site root
    pages, not inside any of the six sections)."""
    try:
        rel = path.relative_to(docs_root)
    except ValueError:
        return None
    parts = rel.parts
    if not parts:
        return None
    return parts[0]


def check_file(path, docs_root, errors):
    text = path.read_text(encoding="utf-8")
    try:
        fm, _ = parse_frontmatter(text, path)
    except LintError as e:
        errors.append(str(e))
        return

    for key in REQUIRED_KEYS:
        if key not in fm or not fm[key][0].strip():
            errors.append(f"{path}:1: missing required front-matter key '{key}'")

    is_index = path.name == "_index.md"
    if is_index:
        if "weight" not in fm:
            errors.append(f"{path}:1: _index.md pages require an integer 'weight'")
        else:
            raw, line = fm["weight"]
            if not re.match(r"^-?\d+$", raw):
                errors.append(f"{path}:{line}: 'weight' must be an integer, got '{raw}'")

    section = section_for(path, docs_root)
    if section in SECTION_DOC_TYPE:
        required = SECTION_DOC_TYPE[section]
        if "doc_type" not in fm:
            errors.append(
                f"{path}:1: missing required front-matter key 'doc_type' "
                f"(section '{section}' requires doc_type: {required})"
            )
        else:
            raw, line = fm["doc_type"]
            if raw not in DOC_TYPES:
                errors.append(
                    f"{path}:{line}: doc_type '{raw}' is not one of {sorted(DOC_TYPES)}"
                )
            elif raw != required:
                errors.append(
                    f"{path}:{line}: doc_type '{raw}' does not match section "
                    f"'{section}' (expected doc_type: {required})"
                )


def main(argv):
    if len(argv) != 2:
        print(f"usage: {argv[0]} <content-dir>", file=sys.stderr)
        return 2
    content_dir = Path(argv[1])
    docs_root = content_dir / "en" / "docs"
    errors = []
    for md_path in sorted(content_dir.rglob("*.md")):
        check_file(md_path, docs_root, errors)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        print(f"\n{len(errors)} front-matter violation(s) found.", file=sys.stderr)
        return 1
    print(f"Front-matter OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
