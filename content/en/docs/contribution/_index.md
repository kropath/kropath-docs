---
title: Contribution
linkTitle: Contribution
description: >
  Style guide, local preview, PR process, and review expectations for kropath-docs contributors.
weight: 60
doc_type: contribution
---

This section covers how to write, preview, and submit changes to this documentation site.

## Getting started as a contributor

### Prerequisites

- Familiarity with Markdown and YAML front matter
- A local development environment with the tools listed below
- A GitHub account with access to the kropath-docs repository

### Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/kropath/kropath-docs.git
cd kropath-docs
make deps
```

The `make deps` command installs Hugo, Node.js, and Python tools pinned in `versions.env`.
See the documentation on local preview below if setup encounters issues.

### Local preview

Start a local development server with live reload:

```bash
make serve
```

Visit `http://localhost:1313` in your browser. The site rebuilds whenever you save a file,
so you can see your changes immediately.

## Writing guidelines

### Audience and scope

Write for the **end user of kropath**, not for the engineers who built it. Describe the
product's observable behavior and user-facing design, not internal implementation.

- Do not reference Multica tickets, ADRs, or internal decision records
- Do not link to internal repositories or internal documentation
- Do not include internal implementation details like RGD IDs or controller architecture
- Explain *why* a design choice exists in terms the reader understands, not by citing its source

### Document types

Every page declares its type via the `doc_type` front-matter field. Use one of these:

| Type | Use for | Example |
|---|---|---|
| `getting-started` | Onboarding and quick-start material | First time setup |
| `concept` | Explaining ideas and background | How governance tiers work |
| `task` | Step-by-step instructions for one goal | Provisioning an S3 bucket |
| `tutorial` | Longer learning paths chaining multiple tasks | Building a complete pipeline |
| `reference` | Exhaustive API documentation, field-by-field | Schema documentation |
| `contribution` | Guide for contributors | This page |

### Linking

- Use relative links to other pages in the same section: `[link text](../other-page.md)`
- Use Hugo shortcodes for cross-section navigation: `[link text]({{< relref "/docs/concepts" >}})`
- Link only to the public internet (AWS, Kubernetes, kro documentation) for external references
- Verify all links resolve before submitting your PR

### Code examples

- Use the actual field names and defaults from the resource schema
- Always specify the API group: `aws.kropath.run/v1alpha1`, never bare `kropath.run`
- Use `selector.matchLabels` for `externalRef` lookups, never CEL expressions
- Use unprefixed kind names: `S3Config`, not `AWSS3Config`
- Include a working, self-contained example that readers can copy and run

## Submitting changes

1. Create a new branch: `git checkout -b feature/your-change`
2. Make your changes and preview with `make serve`
3. Run the linter: `make check`
4. Commit with a descriptive message
5. Push your branch and open a pull request

All pull requests run automated checks:
- **lint:** Markdown style, front-matter validity, link resolution, and house rules
- **build:** Full site build with no warnings or errors

Both checks must pass before your PR merges.

## Getting help

If you have questions about:
- **Markdown or Hugo syntax:** See the [Hugo documentation](https://gohugo.io/documentation/)
- **Docsy theme:** See the [Docsy documentation](https://www.docsy.dev/)
- **kropath concepts:** See the [Concepts]({{< relref "/docs/concepts" >}}) section
- **PR process or this site:** Open an issue or ask on the community forum
