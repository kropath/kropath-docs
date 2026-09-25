#!/usr/bin/env python3
"""kropath authoring house-rules lint (spec docs-website.md §8).

Six rules, each currently prose a reviewer has to remember by hand:

1. No bare `kropath.run/` API group in examples; must be `<provider>.kropath.run/`.
2. No provider-prefixed kind names (AWSS3Config, GCPServiceAccount, AzureManagedIdentity) — KRO-433.
3. No `externalRef` using `metadata.name` with a CEL expression; `selector.matchLabels` only.
4. No links to internal repositories.
5. No absolute https:// links into the site's own domain; use Hugo relref.
6. No internal-tracker or internal-decision citations in page text.

Rules 1-4 and 6 accept an explicit, reviewed escape hatch: append
`<!-- house-rules:allow=N -->` to the offending line. There is no global
disable and no escape hatch for rule 5 (spec §8).
"""
import re
import sys
from pathlib import Path

INTERNAL_REPOS = r"(core|aws|gcp|azure|controller|idp|aws-integration-tests[\w-]*)"
SITE_DOMAINS = (
    r"kropath\.github\.io/kropath-docs",
    r"docs\.kropath\.run",
)

RULES = {
    1: "bare kropath.run/ API group — must be <provider>.kropath.run/",
    2: "provider-prefixed kind name (KRO-433) — kind names carry no provider prefix",
    3: "externalRef metadata.name with a CEL expression — use selector.matchLabels",
    4: "link to an internal kropath repository",
    5: "absolute https:// link into the site's own domain — use Hugo relref",
    6: "internal tracker/decision citation (KRO-####, ADR-####, internal repo path, or mention://)",
}


def allow(line, rule_no):
    return re.search(rf"house-rules:allow={rule_no}\b", line) is not None


def check_rule1(lines):
    violations = []
    pattern = re.compile(r"(?<!\.)\bkropath\.run/")
    for i, line in enumerate(lines, start=1):
        if pattern.search(line) and not allow(line, 1):
            violations.append((i, RULES[1]))
    return violations


def check_rule2(lines):
    violations = []
    pattern = re.compile(r"\b(AWS|GCP|Azure)[A-Z][A-Za-z0-9]*\b")
    for i, line in enumerate(lines, start=1):
        if pattern.search(line) and not allow(line, 2):
            violations.append((i, RULES[2]))
    return violations


def check_rule3(lines):
    violations = []
    for i, line in enumerate(lines):
        if "externalRef:" not in line:
            continue
        window = lines[i : i + 10]
        seen_metadata = False
        for j, wline in enumerate(window):
            if re.search(r"\bmetadata:\s*$", wline):
                seen_metadata = True
                continue
            if seen_metadata and re.search(r"\bname:\s*[\"']?\$\{", wline):
                lineno = i + 1 + j
                if not allow(wline, 3):
                    violations.append((lineno, RULES[3]))
                break
    return violations


def check_rule4(lines):
    violations = []
    pattern = re.compile(
        r"(github\.com/kropath/|kropath-)" + INTERNAL_REPOS + r"(?:/|\b)"
    )
    for i, line in enumerate(lines, start=1):
        if pattern.search(line) and not allow(line, 4):
            violations.append((i, RULES[4]))
    return violations


def check_rule5(lines):
    violations = []
    pattern = re.compile(r"https://(" + "|".join(SITE_DOMAINS) + r")")
    for i, line in enumerate(lines, start=1):
        if pattern.search(line):
            violations.append((i, RULES[5]))
    return violations


def check_rule6(lines):
    violations = []
    pattern = re.compile(r"KRO-[0-9]|ADR-[0-9]|kropath-(core|aws|controller|idp)/|mention://")
    for i, line in enumerate(lines, start=1):
        if pattern.search(line) and not allow(line, 6):
            violations.append((i, RULES[6]))
    return violations


CHECKS = [check_rule1, check_rule2, check_rule3, check_rule4, check_rule5, check_rule6]


def check_file(path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    errors = []
    for check in CHECKS:
        for lineno, message in check(lines):
            errors.append(f"{path}:{lineno}: house rule violation: {message}")
    return errors


def main(argv):
    if len(argv) != 2:
        print(f"usage: {argv[0]} <content-dir>", file=sys.stderr)
        return 2
    content_dir = Path(argv[1])
    errors = []
    for md_path in sorted(content_dir.rglob("*.md")):
        errors.extend(check_file(md_path))
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        print(f"\n{len(errors)} house-rule violation(s) found.", file=sys.stderr)
        return 1
    print("House rules OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
