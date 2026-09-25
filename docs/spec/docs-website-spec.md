# Docs Website Spec

**Ticket:** KRO-1248 (under feature tracker KRO-1247)
**Repo:** kropath-docs
**Type:** Documentation infrastructure spec (not a CRD resource spec)

> This spec follows the kropath SDD Resource Spec structure — Context, Scope, structure surface,
> Acceptance criteria, Open questions — with the CRD-specific sections (provider concept mapping,
> `<ResourceFamily>Config` additions, `KropathConfig` additions, naming exemptions) omitted because
> they do not apply. The acceptance-criteria table replaces the Chainsaw scenario column with a
> **Verification** column naming the `make` target, CI job, or manual check that proves each
> criterion, since this work ships no RGDs and therefore no Chainsaw tests.

---

## 1. Context

`kropath-docs` holds 292 markdown files of customer-facing documentation — 269 AWS resource pages
under `docs/aws/`, 20 pages under `docs/resources/`, and one task guide under `docs/guides/` — and
today none of it is published. The repository is public, but it has no static site generator, no
navigation, no search, no CI, no `Makefile`, and no branch protection. Readers can only browse raw
markdown on GitHub; there is no way to move between a concept and the reference page it depends on,
and nothing stops a PR from landing with broken links, a deprecated API group, or a
provider-prefixed kind name.

This spec defines the documentation website that fixes that: a published site modelled on
[kubernetes.io/docs](https://kubernetes.io/docs/home/) in both information architecture and
tooling, a build/lint/publish pipeline that gates every PR, `make` targets so contributors do not
have to memorise tool invocations, and branch protection that makes those gates mandatory.

The website is also the delivery surface for the integration-test user stories now in flight. The
platform-shared-namespace story (KRO-1176) and the data-team story (KRO-1182) each produce a
narrative that is a **Task** page in Kubernetes-docs terms; `docs/guides/onboard-data-team-namespace-and-resources.md`
is already the first of them. The Tasks section defined here is the permanent home for that class
of content, and the spec fixes the rule by which future story trackers map onto Task pages so the
Documenter does not have to reinvent the placement each time.

---

## 2. Scope

**In scope — `kropath-docs` only:**

- Site generator selection, configuration, and theme.
- Information architecture: the six top-level sections and their ordering.
- Migration mapping for all existing content into that architecture.
- Front-matter contract and a scripted backfill for existing pages.
- `Makefile` contributor surface.
- GitHub Actions workflow: lint, build, and publish to GitHub Pages.
- Branch protection configuration on `main`.
- House-rule lint that mechanically enforces the rules currently written in prose in
  `CLAUDE.md` / `docs/STANDARDS.md`.

**Out of scope:**

- Writing new page content for the empty sections (Getting Started, Concepts, Tutorials,
  Contribution). This spec defines the slots, the front-matter contract, and the placement rules;
  authoring is Documenter work under separate tickets.
- Changes to any other repo. No `kropath-core`, `kropath-aws`, `kropath-controller`, or
  `kropath-idp` change is required or permitted by this spec.
- Autogenerating reference pages from CRD schemas (see Open questions).
- A custom domain (see Open questions).

---

## 3. Site generator decision

### Decision

**Hugo (extended) + the Docsy theme, wired in as a Hugo Module.**

### Rationale

- kubernetes.io itself is Hugo + Docsy. Matching the toolchain is the cheapest way to match the
  look, the left-nav behaviour, the section-landing pattern, and the page-level furniture
  (breadcrumbs, table of contents, "last modified", edit-this-page links) that the tracker asks for.
- Hugo builds the current 292-page corpus in low single-digit seconds and will not degrade as the
  reference section grows past a thousand pages; build time is a real constraint here because the
  reference section is generated per resource kind and grows with every family.
- Hugo is a single static binary, so the CI job is a download plus a build — no runtime language
  server, no framework upgrade treadmill.
- Docsy ships exactly the section-oriented IA this site needs (`docs/` tree, foldable left nav,
  per-section landing pages, offline search) without custom layout work.

### Alternatives considered

| Option | Why not |
|---|---|
| MkDocs + Material | Excellent tool, but the IA idiom and page furniture differ visibly from kubernetes.io, and it adds a Python runtime to CI for no gain here. |
| Docusaurus | React/Node build, MDX authoring model, and a versioning scheme heavier than this repo needs. Contributors would be writing docs in a JS app. |
| GitHub Pages default (Jekyll) | No usable multi-section nav, no offline search, weak large-tree performance. |
| Raw markdown on GitHub (status quo) | No navigation, no search, no link checking — the problem being solved. |

### Consequences to accept

- Docsy compiles its SCSS through PostCSS, so **Node.js and `npm` are build-time dependencies** in
  addition to Hugo. Both are pinned (§7).
- Docsy-as-Hugo-Module requires the **Go toolchain** in CI and in the contributor environment. This
  is preferred over a git submodule: `go.mod` pins the theme to an exact version, `hugo mod get -u`
  is an ordinary reviewable diff, and contributors never hit the "submodule not initialised" build
  failure.
- Hugo **extended** is mandatory (SCSS). A non-extended binary must fail the build with a clear
  message rather than a SCSS stack trace.

---

## 4. Information architecture

Six top-level sections under `/docs/`, in this order, matching the tracker and kubernetes.io:

| # | Section | URL | Weight | Purpose | Initial state |
|---|---|---|---|---|---|
| 1 | Getting Started | `/docs/getting-started/` | 10 | Prerequisites, install, first governed resource, "is kropath for me" | New — landing page + placeholders |
| 2 | Concepts | `/docs/concepts/` | 20 | How kropath thinks: governance tiers, config profiles, naming, labels, policy composition | Seeded from 3 existing pages |
| 3 | Tasks | `/docs/tasks/` | 30 | One concrete goal, start to finish | Seeded from the existing guide; grows from integration-test stories |
| 4 | Tutorials | `/docs/tutorials/` | 40 | Longer end-to-end learning paths that chain several tasks | New — landing page only |
| 5 | Reference | `/docs/reference/` | 50 | Field-by-field resource documentation, per provider | Seeded from all 286 existing reference pages |
| 6 | Contribution | `/docs/contribution/` | 60 | Style guide, local preview, PR process, review expectations | New — landing page + style guide |

Section semantics follow the Kubernetes docs content-type definitions, and every page declares which
type it is via `doc_type` front matter (§6). The distinction that matters most in review: a **Task**
achieves one goal and assumes the reader knows why they want it; a **Tutorial** teaches and may
build throwaway resources; a **Concept** explains and contains no step list; **Reference** is
exhaustive and is not read top to bottom.

### 4.1 Reference sub-tree

```
/docs/reference/
├── aws/
│   ├── <service>/              # e.g. s3, iam, ec2, keyspaces, backup
│   │   ├── _index.md           # service landing: what the family covers, kind list
│   │   ├── <kind>.md           # one page per resource kind
│   │   └── <subgroup>/         # only where a service already has subgroups (EC2)
│   │       ├── _index.md
│   │       └── <kind>.md
│   ├── gcp/                    # created when GCP families ship
│   └── azure/                  # created when Azure families ship
└── platform/                   # provider-neutral: KropathConfig, effectiveConfig, controller behaviour
```

Provider directories are created only when that provider has content; empty section stubs are not
published.

### 4.2 Tasks sub-tree and the story-to-task rule

```
/docs/tasks/
├── onboarding/                 # namespace onboarding, cross-account access
├── platform-shared/            # platform-team foundation resources
├── data-processing/            # storage → eventing → compute → messaging flows
└── operations/                 # day-2: rotation, backup verification, teardown
```

**Rule (normative):** every integration-test user-story tracker yields **at least one Task page**.
The story's narrative becomes the page body; the story's "Verify in AWS" sub-issue supplies the
page's verification steps; the story's "Find gaps" sub-issue supplies the page's limitations or
prerequisites. The page lives in the sub-tree matching the story's domain, and its `_index.md`
lists it.

Applying the rule to the two stories named in the tracker:

| Story tracker | Task page | Source |
|---|---|---|
| KRO-1176 — platform engineer, platform-shared namespace | `tasks/onboarding/onboard-a-namespace.md` | Onboarding template + namespace annotations for cross-account access |
| KRO-1176 | `tasks/platform-shared/provision-shared-platform-resources.md` | `central-logging` bucket, per-account `artifacts` bucket |
| KRO-1182 — data engineer, data-team namespace and resources | `tasks/data-processing/onboard-data-team-namespace-and-resources.md` | **Existing** `docs/guides/onboard-data-team-namespace-and-resources.md` |
| KRO-1182 (sub-issue KRO-1190) | `tasks/data-processing/build-and-promote-a-lambda-artifact.md` | Lambda build repo and artifact promotion pipeline |

Only the third row has content today. The other three are section-listed placeholders that this
spec reserves; authoring them is Documenter work under the respective story trackers, not part of
the website build.

---

## 5. Content migration mapping

Existing content is **moved** into `content/en/docs/` with `git mv` in a single dedicated migration
PR, not mounted in place via Hugo module mounts. Two competing content trees would confuse
contributors permanently, Docsy needs `_index.md` section pages interleaved with the content, and a
front-matter backfill is required either way — so the one-time move is the cheaper path and `git mv`
preserves per-file history.

The site has never been published, so **no URL redirects are required**. This is the one moment
where the tree can be reshaped for free.

### 5.1 `docs/guides/` → Tasks

| Source | Destination |
|---|---|
| `docs/guides/onboard-data-team-namespace-and-resources.md` | `content/en/docs/tasks/data-processing/onboard-data-team-namespace-and-resources.md` |

This page already carries `doc_type: task` front matter and a hand-written "Document type" banner
paragraph. The banner prose is **removed**; the Docsy layout renders it from `doc_type` instead
(§6.2), so the statement cannot drift from the metadata.

### 5.2 `docs/resources/` → Concepts and Reference

Three of the twenty pages explain platform behaviour rather than document a resource kind, and
belong in Concepts:

| Source | Destination | Section |
|---|---|---|
| `docs/resources/naming-template-dynamic-tags.md` | `content/en/docs/concepts/naming/dynamic-tag-fields-in-naming-templates.md` | Concepts |
| `docs/resources/controller-label-operator.md` | `content/en/docs/concepts/controller/label-operator.md` | Concepts |
| `docs/resources/aws-policy-document.md` | `content/en/docs/concepts/iam/policy-documents.md` | Concepts |

The remaining seventeen are reference pages for AWS families that have no directory under
`docs/aws/` yet. Each gets a service directory with an `_index.md`:

| Source | Destination |
|---|---|
| `docs/resources/aws-backup-backupconfig.md` | `content/en/docs/reference/aws/backup/backupconfig.md` |
| `docs/resources/aws-backup-backupplan.md` | `content/en/docs/reference/aws/backup/backupplan.md` |
| `docs/resources/aws-backup-backupselection.md` | `content/en/docs/reference/aws/backup/backupselection.md` |
| `docs/resources/aws-backup-backupvault.md` | `content/en/docs/reference/aws/backup/backupvault.md` |
| `docs/resources/aws-keyspaces-config.md` | `content/en/docs/reference/aws/keyspaces/keyspacesconfig.md` |
| `docs/resources/aws-keyspaces-keyspace.md` | `content/en/docs/reference/aws/keyspaces/keyspaceskeyspace.md` |
| `docs/resources/aws-keyspaces-table.md` | `content/en/docs/reference/aws/keyspaces/keyspacestable.md` |
| `docs/resources/aws-s3advanced-config.md` | `content/en/docs/reference/aws/s3advanced/s3advancedconfig.md` |
| `docs/resources/aws-s3control-accesspoint.md` | `content/en/docs/reference/aws/s3advanced/s3controlaccesspoint.md` |
| `docs/resources/aws-s3files-accesspoint.md` | `content/en/docs/reference/aws/s3advanced/s3filesaccesspoint.md` |
| `docs/resources/aws-s3files-filesystem.md` | `content/en/docs/reference/aws/s3advanced/s3filesfilesystem.md` |
| `docs/resources/aws-s3files-mounttarget.md` | `content/en/docs/reference/aws/s3advanced/s3filesmounttarget.md` |
| `docs/resources/aws-s3tables-namespace.md` | `content/en/docs/reference/aws/s3advanced/s3tablesnamespace.md` |
| `docs/resources/aws-s3tables-table.md` | `content/en/docs/reference/aws/s3advanced/s3tablestable.md` |
| `docs/resources/aws-s3tables-tablebucket.md` | `content/en/docs/reference/aws/s3advanced/s3tablestablebucket.md` |
| `docs/resources/aws-s3vectors-index.md` | `content/en/docs/reference/aws/s3advanced/s3vectorsindex.md` |
| `docs/resources/aws-s3vectors-vectorbucket.md` | `content/en/docs/reference/aws/s3advanced/s3vectorsvectorbucket.md` |

The seven S3 Tables / Vectors / Files / Control pages are grouped under a single `s3advanced`
service directory because they share one governance resource, `S3AdvancedConfig`. They are
deliberately **not** merged into `reference/aws/s3/`, which documents core bucket resources and a
separate config kind.

File names are the lowercased kind name, so the page slug matches the kind the reader typed into
their manifest.

### 5.3 `docs/aws/` → Reference

Rule-based, not enumerated — 269 files:

- `docs/aws/<service>/<kind>.md` → `content/en/docs/reference/aws/<service>/<kind>.md`
- The service landing page becomes `_index.md`. Today this file is inconsistently named: some
  services use `index.md` (e.g. `apigateway`, `ecr`), some use `<service>.md` (e.g. `s3/s3.md`,
  `ecs/ecs.md`, `bedrock/bedrock.md`), and some have both (`ec2/ec2.md` alongside `ec2/ec2config.md`).
  Normalisation: whichever of `index.md` or `<service>.md` is a landing page becomes `_index.md`;
  a `<service>.md` that is actually a kind page (e.g. `ec2/ec2config.md` is the `EC2Config` kind)
  stays a leaf page. Services with **no** landing page get a generated `_index.md` stub listing
  their kinds.
- EC2's existing subgroup directories (`networking-core/`, `connectivity-compute/`,
  `advanced-networking/`) are preserved as sub-sections, each with a generated `_index.md`, because
  a flat EC2 nav of 15+ kinds is unusable.

### 5.4 Files that are **not** published

These are internal engineering records, not customer-facing documentation. They stay under `docs/`
and are excluded from the build:

| Path | Disposition |
|---|---|
| `docs/spec/**` (including this file) | Internal. Not published. |
| `docs/STANDARDS.md` | Internal. Not published. |
| `docs/engineering-standards.md` | Internal. Not published. Contributor-relevant excerpts are rewritten for readers in `contribution/`, never linked or copied wholesale. |
| `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` | Internal agent instructions. Not published. |

After migration, `docs/` contains only internal material and `content/en/docs/` contains everything
published. The build must **fail** if a markdown file appears under `content/` that is not reachable
from a section, and must **ignore** everything under `docs/`.

---

## 6. Structure surface

### 6.1 Repository layout after implementation

```
kropath-docs/
├── Makefile
├── versions.env                  # single source of truth for all pinned tool versions
├── hugo.toml                     # site config
├── go.mod / go.sum               # Docsy pinned as a Hugo Module
├── package.json / package-lock.json   # PostCSS toolchain for Docsy SCSS
├── .markdownlint-cli2.jsonc
├── .htmltest.yml
├── .github/workflows/docs.yml
├── scripts/
│   ├── check-frontmatter.py      # front-matter contract
│   ├── check-house-rules.py      # kropath authoring rules
│   └── backfill-frontmatter.py   # one-shot migration helper
├── content/en/
│   ├── _index.md                 # site home
│   └── docs/
│       ├── _index.md
│       ├── getting-started/_index.md
│       ├── concepts/_index.md
│       ├── tasks/_index.md
│       ├── tutorials/_index.md
│       ├── reference/_index.md
│       └── contribution/_index.md
├── layouts/                      # local Docsy overrides (doc_type banner partial)
├── static/                       # images, favicon
└── docs/                         # internal only; excluded from the build
    ├── spec/
    ├── STANDARDS.md
    └── engineering-standards.md
```

### 6.2 Front-matter contract

Every published page — including every `_index.md` — carries:

```yaml
---
title: S3Config                  # required; page H1 and browser title
linkTitle: S3Config              # optional; left-nav label when it differs from title
description: >
  Mandatory and default settings applied to S3 buckets in a namespace.
                                 # required; one sentence, used in section listings and search
weight: 30                       # required on _index.md; optional on leaf pages
doc_type: reference              # required; one of the six values below
---
```

`doc_type` enum: `getting-started` | `concept` | `task` | `tutorial` | `reference` | `contribution`.
It must match the section the page sits in — a `doc_type: task` page under `concepts/` is a lint
failure.

A Docsy layout override renders the document-type banner from `doc_type`, replacing the hand-written
banner paragraph currently in the data-team guide. The banner text is defined once, in the layout.

Existing pages carry no front matter (one of 292 does). `scripts/backfill-frontmatter.py` seeds it:
`title` from the first H1, `description` from the first sentence of the first paragraph truncated at
a sentence boundary, `doc_type` from the destination section, `weight` unset on leaf pages so Hugo
falls back to alphabetical ordering. The backfill is a **migration aid with human review of the
diff**, not a permanent part of the pipeline — descriptions it generates are reviewed and edited in
the migration PR, and the script is retained only for bulk imports.

### 6.3 Left navigation

- Docsy foldable sidebar (`sidebar_menu_foldable = true`), collapsed below the active section, so
  the 269-page reference tree never floods the nav.
- Ordering by `weight`, then alphabetical.
- `sidebar_search_disable = false`; offline search enabled (§8, Open questions covers the backend).
- Breadcrumbs and a right-hand page table of contents on every page, as on kubernetes.io.

---

## 7. Version pinning

All tool versions live in **one** checked-in file, `versions.env`, which both the `Makefile` and the
CI workflow read. No version is written twice.

```sh
HUGO_VERSION=0.148.2          # extended
DOCSY_VERSION=v0.12.0         # also pinned in go.mod
NODE_VERSION=22.x
GO_VERSION=1.24.x
MARKDOWNLINT_CLI2_VERSION=0.18.1
HTMLTEST_VERSION=0.17.0
PYTHON_VERSION=3.12
```

Exact patch versions are chosen at implementation time against what is current; the requirement is
that they are pinned, single-sourced, and upgraded as a deliberate reviewable commit. A version
drift between the local `Makefile` and CI is a defect — if `make check` passes locally, the PR must
pass CI.

---

## 8. Lint requirements

`make lint` runs all of the following; any failure fails the target and the CI job.

| Check | Tool | Enforces |
|---|---|---|
| Markdown style | `markdownlint-cli2`, config checked in | Heading hierarchy, list style, no trailing whitespace, fenced code blocks declare a language, line length (relaxed inside tables and code) |
| Front matter | `scripts/check-frontmatter.py` | Required keys present, `doc_type` in enum, `doc_type` matches section, `weight` integer, `description` non-empty and single-sentence |
| Internal links and anchors | `htmltest` over the built `public/` | Every internal link and anchor resolves; every referenced image exists |
| House rules | `scripts/check-house-rules.py` | The authoring rules in `docs/STANDARDS.md`, mechanically (below) |
| Build integrity | `hugo` with `refLinksErrorLevel = "ERROR"` | Broken `ref`/`relref` shortcodes fail the build instead of warning |

**House rules enforced by `scripts/check-house-rules.py`** — each of these is currently prose that a
reviewer has to remember:

1. No bare `kropath.run/` API group in examples; must be `<provider>.kropath.run/`.
2. No provider-prefixed kind names (`AWSS3Config`, `GCPServiceAccount`, `AzureManagedIdentity`) —
   KRO-433.
3. No `externalRef` using `metadata.name` with a CEL expression; `selector.matchLabels` only.
4. No links to internal repositories (`kropath-core`, `kropath-aws`, `kropath-gcp`,
   `kropath-azure`, `kropath-controller`, `kropath-idp`, `kropath-aws-integration-tests*`) — a
   published page may link only to other kropath-docs pages and to external kro, ACK, AWS, and
   Kubernetes documentation.
5. No absolute `https://` links into the site's own domain; internal links use Hugo `relref`.

Each violation reports `path:line` and the rule name. Rules 1–4 have escape hatches only via an
explicit, reviewed inline allow comment — there is no global disable.

**External link checking is a separate, non-blocking job** on a weekly schedule, not part of the PR
gate. A third-party site going down must not block an unrelated PR from merging.

---

## 9. Makefile requirements

`make` with no target prints the target list with one-line descriptions. Every target is
idempotent and runnable from a clean checkout.

| Target | Behaviour |
|---|---|
| `make deps` | Verify/install pinned Hugo (extended), Node, Go, and Python tooling; `hugo mod get`; `npm ci`. Fails with a clear, actionable message if Hugo is non-extended or a version mismatches `versions.env`. |
| `make serve` | `hugo server --buildDrafts --buildFuture` with live reload on `http://localhost:1313`. The only command a writer needs day to day. |
| `make build` | Production build to `public/` — `--gc --minify`, warnings as errors, drafts excluded. |
| `make lint` | All checks in §8 against the current tree. Builds first if `public/` is stale, because link checking needs rendered output. |
| `make link-check` | Internal link check only, against an existing `public/`. |
| `make check` | `lint` + `build`. **The pre-push gate** — exactly what CI runs, so a green `make check` predicts a green PR. |
| `make clean` | Remove `public/`, `resources/_gen/`, and `.hugo_build.lock`. |
| `make publish` | Produce the deployable artifact. Intended for CI; run locally it refuses unless `CI=true` or `ALLOW_LOCAL_PUBLISH=1` is set, and says why. |

---

## 10. Pipeline requirements

One workflow, `.github/workflows/docs.yml`.

**Triggers**

- `pull_request` targeting `main` — jobs: `lint`, `build`.
- `push` to `main` — jobs: `lint`, `build`, then `deploy`.
- `schedule` weekly — job: `external-links` (non-blocking, opens or updates an issue on failure).
- `workflow_dispatch` — manual re-publish.

**Jobs**

| Job | Runs | Notes |
|---|---|---|
| `lint` | `make lint` | Must be independently re-runnable; annotates failures at `path:line` via GitHub problem matchers |
| `build` | `make build` | Uploads `public/` as a Pages artifact (`actions/upload-pages-artifact`) |
| `deploy` | `actions/deploy-pages` | `main` only; `environment: github-pages`; permissions `pages: write`, `id-token: write`; `contents: read` |
| `external-links` | external link check | Scheduled only; never gates a PR |

**Requirements**

- All tool versions read from `versions.env`; no version literal in the workflow file.
- Actions pinned to a major version at minimum; first-party GitHub actions preferred over
  third-party wrappers.
- `permissions:` declared at job level, least-privilege; the default `GITHUB_TOKEN` is read-only.
- `concurrency` group per ref with `cancel-in-progress: true` for PR runs; the Pages deploy uses the
  `pages` group with `cancel-in-progress: false` so a deploy is never half-cancelled.
- Hugo module cache and `node_modules` cached, keyed on `versions.env` + lockfiles.
- Job names are stable strings — branch protection references them, so renaming a job is a
  breaking change that must update protection in the same PR.
- PR runs build the site but never deploy and never write to the repo.

**Publishing target:** GitHub Pages via the Actions Pages deployment path (not a `gh-pages`
branch). The repo is already public. `baseURL` in `hugo.toml` must match the Pages URL exactly, or
every stylesheet 404s.

---

## 11. Branch protection requirements

`main` is protected. Configuration is applied through the GitHub API by a repo admin and recorded in
`docs/contribution/` so it is reproducible rather than tribal knowledge.

| Setting | Value | Reason |
|---|---|---|
| Require a pull request before merging | on | No direct pushes to `main` — explicit tracker requirement |
| Required approvals | 1 | |
| Dismiss stale approvals on new commits | on | An approval must describe the code that merges |
| Required status checks | `lint`, `build` | The tracker's lint + build gate |
| Require branches up to date before merging | on | Prevents a semantic conflict merging green |
| Require conversation resolution | on | |
| Block force pushes | on | |
| Block branch deletion | on | |
| Enforce for administrators | on | "No one can push to main directly" means no one |
| Allow bypass actors | none | |

The `lint` and `build` checks must have run at least once on a PR before they can be selected as
required checks, so protection is applied **after** the pipeline PR merges — this ordering is a
task dependency, not an oversight.

---

## 12. Acceptance criteria

| # | Given | When | Then | Verification |
|---|---|---|---|---|
| AC-1 | A clean checkout with Hugo, Node, Go, and Python absent or mismatched | `make deps` runs | It reports each missing or mismatched tool by name with the version required by `versions.env`, and exits non-zero | Manual: run on a clean container |
| AC-2 | A clean checkout with dependencies installed | `make serve` runs | Hugo serves on `localhost:1313` and edits to any content file live-reload in under 2s | Manual |
| AC-3 | The migrated content tree | `make build` runs | It exits 0 and `public/` contains one HTML page per published markdown file; the build emits no Hugo WARN or ERROR | CI job `build` |
| AC-4 | The built site | A reader opens `/docs/` | The left nav shows exactly six sections in the order Getting Started, Concepts, Tasks, Tutorials, Reference, Contribution | Manual on the deployed preview; nav ordering asserted by `check-frontmatter.py` weights |
| AC-5 | A page with `doc_type: task` placed under `content/en/docs/concepts/` | `make lint` runs | Lint fails naming the file, the declared `doc_type`, and the section it sits in | `scripts/check-frontmatter.py` unit test |
| AC-6 | A page missing `title` or `description` front matter | `make lint` runs | Lint fails at `path:line` naming the missing key | `scripts/check-frontmatter.py` unit test |
| AC-7 | A page containing `apiVersion: kropath.run/v1alpha1` | `make lint` runs | Lint fails citing house rule 1 and the deprecated bare API group | `scripts/check-house-rules.py` unit test |
| AC-8 | A page containing the kind `AWSS3Config` | `make lint` runs | Lint fails citing house rule 2 (KRO-433) | `scripts/check-house-rules.py` unit test |
| AC-9 | A page containing `externalRef` with `metadata.name` set to a CEL expression | `make lint` runs | Lint fails citing house rule 3 | `scripts/check-house-rules.py` unit test |
| AC-10 | A page linking to `github.com/kropath/kropath-core` | `make lint` runs | Lint fails citing house rule 4 | `scripts/check-house-rules.py` unit test |
| AC-11 | A page linking to a heading anchor that does not exist | `make lint` runs | Lint fails naming the source page and the unresolved target | `htmltest` over `public/` |
| AC-12 | An external link that 404s, with no other defect in the tree | A PR runs CI | `lint` and `build` both pass; the failure surfaces only in the weekly `external-links` job | CI: scheduled job is not in the PR job set |
| AC-13 | All 286 existing reference pages after migration | `make build` runs | Every page is reachable from `/docs/reference/`, and no page 404s | `htmltest` orphan/link check + page count assertion in `build` |
| AC-14 | `docs/spec/docs-website-spec.md` and `docs/STANDARDS.md` | `make build` runs | Neither appears in `public/`; no internal-only file is published | Assertion step in `build`: grep `public/` for internal paths, fail if found |
| AC-15 | The existing data-team guide after migration | A reader opens `/docs/tasks/data-processing/onboard-data-team-namespace-and-resources/` | The page renders with a document-type banner generated from `doc_type`, and the hand-written banner paragraph is gone | Manual + `grep` assertion that no page hard-codes the banner prose |
| AC-16 | A merge to `main` with a green `lint` and `build` | The `push` workflow runs | `deploy` publishes to GitHub Pages and the live site serves the new content; stylesheets load (no `baseURL` mismatch) | CI job `deploy` + manual check of the live URL |
| AC-17 | A PR whose `lint` job fails | A maintainer attempts to merge | GitHub blocks the merge, citing the required check | Manual, after branch protection is applied |
| AC-18 | A repository administrator | They attempt `git push` directly to `main` | The push is rejected | Manual, after branch protection is applied with admin enforcement |
| AC-19 | A contributor with a passing `make check` locally | They open a PR | CI passes without further changes — no version or configuration drift between local and CI | Observed across the pipeline PR and the migration PR |
| AC-20 | The Tasks section | A reader opens `/docs/tasks/` | The landing page lists the four reserved story-derived task slots, with the three unwritten ones clearly marked as not yet available rather than rendering as broken links | Manual + `htmltest` (no broken internal links) |

---

## 13. Implementation phasing

The order matters — branch protection cannot reference status checks that have never run, and
linting 292 unmigrated files produces unusable noise.

| Phase | Work | Depends on |
|---|---|---|
| 1 | Scaffold: `hugo.toml`, `go.mod` with Docsy, `package.json`, `versions.env`, six empty section `_index.md` files, `Makefile`, `layouts/` doc_type banner partial | — |
| 2 | Lint tooling: `markdownlint-cli2` config, `check-frontmatter.py`, `check-house-rules.py`, `htmltest` config, unit tests for both scripts | 1 |
| 3 | CI workflow: `lint`, `build`, `deploy`, `external-links` | 1, 2 |
| 4 | Content migration: `git mv` of all 290 pages, front-matter backfill with reviewed diff, generated `_index.md` stubs, EC2 subgroup sections | 1, 2 |
| 5 | Branch protection applied and documented in `contribution/` | 3, 4 (checks must have run green) |
| 6 | Section landing pages and the contribution style guide written | 4 |

Phases 1–3 can land in one PR; phase 4 must be its own PR because it is a 290-file diff that is
reviewed for content correctness, not code. Phase 6 is Documenter work.

---

## 14. Open questions

1. **Custom domain.** Publish at the default `kropath.github.io/kropath-docs/` path, or set up
   `docs.kropath.run` with a `CNAME` and DNS? This changes `baseURL`, and switching later breaks
   every external link to the site. Recommendation: decide before the first publish.
2. **Search backend.** Docsy supports an offline Lunr index, Algolia DocSearch, and Google CSE.
   Offline Lunr needs no third-party account and works immediately, but the index grows with the
   reference tree and is downloaded by every visitor. Recommendation: start with Lunr, revisit if
   the index exceeds roughly 1 MB.
3. **Versioned documentation.** Every resource today is `v1alpha1`. When `v1beta1` ships, does the
   site need Docsy's version dropdown with a published archive of the old version, or is a
   single "latest" adequate? Deferring is cheap now and expensive after the first API version bump.
4. **`docs/engineering-standards.md`.** Kept internal by this spec. If any of it is genuinely
   contributor-facing, it should be rewritten for readers into `contribution/` rather than
   published as-is — which content, if any, is a call for the human owner.
5. **Reference page generation.** The reference section is currently hand-written per kind. If it is
   later generated from CRD schemas, the front-matter contract and lint rules here must be produced
   by the generator. No decision needed now, but the generator should not be retrofitted onto a
   hand-edited tree without planning.
6. **Contributor environment.** Docsy-as-Hugo-Module requires Go locally. If that is an unacceptable
   burden for doc-only contributors, the fallback is a devcontainer or a `make serve-docker` target.
   Recommendation: ship `make deps` first and add a container target only if contributors hit
   friction.

---

## 15. Cross-cutting notes

- Nothing in this spec changes any published page's **content**. The migration moves files, adds
  front matter, and deletes one hand-written banner paragraph. Content correctness stays with the
  Documenter.
- The house-rule lint (§8) will very likely fail on existing pages the first time it runs. Those
  failures are real defects that were previously invisible; they are fixed in the migration PR, not
  suppressed. If the volume proves large, the rules land as warnings in the migration PR and are
  promoted to errors in an immediate follow-up — but they are never left as warnings.
- `make check` is the contract with contributors. Every gate CI applies must be reachable from it;
  a CI check that cannot be run locally is a defect in this spec's implementation.
