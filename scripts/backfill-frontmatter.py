#!/usr/bin/env python3
"""One-shot front-matter backfill for the content migration PR (spec §6.2).

Migration aid, not a permanent part of the pipeline: seeds `title` (from the
first H1), `description` (from the first sentence of the first paragraph),
and `doc_type` (from the destination section) on pages that don't have them
yet. `weight` is deliberately never generated — leaf pages fall back to
Hugo's alphabetical ordering, and the required weight on `_index.md` pages is
a human editorial call the migration PR's reviewer makes, not something to
guess mechanically.

Run once against the migrated tree; the diff (especially `description`) gets
human review in that PR before merging — see docs-website.md §6.2, §15.
"""
import re
import sys
from pathlib import Path

SECTION_DOC_TYPE = {
    "getting-started": "getting-started",
    "concepts": "concept",
    "tasks": "task",
    "tutorials": "tutorial",
    "reference": "reference",
    "contribution": "contribution",
}

SENTENCE_END = re.compile(r"(?<=[.!?])\s")


def has_frontmatter(text):
    return text.startswith("---\n") or text.startswith("---\r\n")


def split_frontmatter(text):
    """Return (frontmatter_lines, body) if front matter exists, else ([], text)."""
    if not has_frontmatter(text):
        return [], text
    lines = text.splitlines(keepends=True)
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "".join(lines[i + 1 :])
    return [], text


def existing_keys(fm_lines):
    keys = set()
    for line in fm_lines:
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):", line)
        if m:
            keys.add(m.group(1))
    return keys


def first_h1(body):
    for line in body.splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m:
            return m.group(1).strip()
    return None


def first_description_sentence(body, title):
    in_code_fence = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if title and stripped == f"# {title}":
            continue
        parts = SENTENCE_END.split(stripped, maxsplit=1)
        return parts[0].strip()
    return None


def yaml_scalar(value):
    if any(c in value for c in ':#{}[]&*!|>\'"%@`') or value.strip() != value:
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def section_for(path, docs_root):
    try:
        rel = path.relative_to(docs_root)
    except ValueError:
        return None
    return rel.parts[0] if rel.parts else None


def backfill_file(path, docs_root, warnings):
    text = path.read_text(encoding="utf-8")
    fm_lines, body = split_frontmatter(text)
    keys = existing_keys(fm_lines)

    new_fields = []
    if "title" not in keys:
        title = first_h1(body) or path.stem
        new_fields.append(f"title: {yaml_scalar(title)}")
    else:
        title = None

    if "description" not in keys:
        desc = first_description_sentence(body, title) or ""
        if not desc:
            warnings.append(f"{path}: could not derive a description — needs manual review")
        new_fields.append(f"description: {yaml_scalar(desc)}")

    section = section_for(path, docs_root)
    if "doc_type" not in keys and section in SECTION_DOC_TYPE:
        new_fields.append(f"doc_type: {SECTION_DOC_TYPE[section]}")

    if path.name == "_index.md" and "weight" not in keys:
        warnings.append(f"{path}: _index.md is missing 'weight' — add one during review")

    if not new_fields:
        return False

    if fm_lines:
        merged = "".join(fm_lines) + "\n".join(new_fields) + "\n"
    else:
        merged = "\n".join(new_fields) + "\n"
    path.write_text(f"---\n{merged}---\n{body}", encoding="utf-8")
    return True


def main(argv):
    if len(argv) != 2:
        print(f"usage: {argv[0]} <content-dir>", file=sys.stderr)
        return 2
    content_dir = Path(argv[1])
    docs_root = content_dir / "en" / "docs"
    warnings = []
    changed = 0
    for md_path in sorted(content_dir.rglob("*.md")):
        if backfill_file(md_path, docs_root, warnings):
            changed += 1
    print(f"Backfilled front matter on {changed} file(s).")
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
