# kropath-docs

Source for the kropath documentation website: guides, concept pages, reference material, and
tutorials for people using the kropath platform. Built with [Hugo](https://gohugo.io/) (extended
edition) and the [Docsy](https://www.docsy.dev/) theme.

Published site: https://kropath.github.io/kropath-docs/

## Requirements

All tool versions are pinned in `versions.env`, the single source of truth shared with CI:
Hugo (extended), Node, Go, Python, `markdownlint-cli2`, and `htmltest`.

```bash
make deps    # verify the pinned versions are installed, then fetch Hugo modules and npm packages
```

`make deps` fails with a specific message naming whichever tool is missing or on the wrong
version, rather than failing later with an opaque Hugo or SCSS build error.

## Serving the site locally

```bash
make serve   # serve the site locally with live reload
```

Draft and future-dated content is included when serving locally, so in-progress pages can be
previewed before they're ready to publish.

## Checking your changes

```bash
make check   # the pre-push gate — exactly what CI runs
```

`make check` runs a production build (`make build` — warnings and errors both fail the build) plus
the full lint suite (`make lint`): markdown style, front-matter contract, house-rules authoring
conventions, and internal link/anchor checks. A green `make check` locally predicts a green PR.

Individual checks can also be run on their own — `make build`, `make markdownlint`,
`make frontmatter-lint`, `make house-rules-lint`, `make link-check`. Run `make help` for the full
list of targets, including `make clean` to remove build artifacts.

## Layout

| Path | Contents |
|---|---|
| `content/en/docs/` | The published documentation content (getting started, concepts, tasks, tutorials, reference, contribution) |
| `layouts/` | Local layout overrides on top of the Docsy theme |
| `scripts/` | Python scripts backing the lint targets (front-matter and house-rules checks) and their tests |
| `packages/` | npm dependency metadata for the Docsy theme's front-end assets, managed through Hugo Modules |
| `versions.env` | Pinned tool versions shared by the Makefile and CI |
