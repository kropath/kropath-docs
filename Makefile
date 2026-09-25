# kropath-docs — Hugo + Docsy documentation site.
#
# All tool versions come from versions.env, the single source of truth shared
# with .github/workflows/docs.yml. `make check` is the pre-push gate and is
# exactly what CI runs — a green `make check` locally predicts a green PR.

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c
.DEFAULT_GOAL := help

include versions.env
export

# Docsy's SCSS pipeline needs the `sass` (sass-embedded) and `postcss`
# binaries that `npm install` places in node_modules/.bin.
export PATH := $(CURDIR)/node_modules/.bin:$(PATH)

.PHONY: help deps serve build markdownlint frontmatter-lint house-rules-lint link-check link-check-external lint check clean publish

help: ## Show this help
	@echo "kropath-docs — available targets:"
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sort | \
		sed -E 's/^([a-zA-Z_-]+):.*## (.*)$$/\1|\2/' | \
		awk -F'|' '{printf "  %-14s %s\n", $$1, $$2}'

deps: ## Verify pinned Hugo/Node/Go/Python, then fetch Hugo modules and npm packages
	@fail=0; \
	if ! command -v hugo >/dev/null 2>&1; then \
		echo "MISSING: hugo (required: $(HUGO_VERSION) extended) — https://gohugo.io/installation/"; fail=1; \
	else \
		hv=$$(hugo version); \
		if ! echo "$$hv" | grep -q "extended"; then \
			echo "MISMATCH: hugo is installed but not the 'extended' edition (required: $(HUGO_VERSION) extended)."; \
			echo "  SCSS builds will fail with an opaque error later — install the extended binary now."; fail=1; \
		elif ! echo "$$hv" | grep -q "v$(HUGO_VERSION)"; then \
			echo "MISMATCH: hugo version does not match versions.env (required: $(HUGO_VERSION) extended). Found: $$hv"; fail=1; \
		fi; \
	fi; \
	if ! command -v node >/dev/null 2>&1; then \
		echo "MISSING: node (required: $(NODE_VERSION)) — https://nodejs.org/"; fail=1; \
	else \
		nv=$$(node --version | sed 's/^v//'); \
		nv_major=$${nv%%.*}; req_major=$${NODE_VERSION%%.*}; \
		if [ "$$nv_major" != "$$req_major" ]; then \
			echo "MISMATCH: node major version does not match versions.env (required: $(NODE_VERSION)). Found: $$nv"; fail=1; \
		fi; \
	fi; \
	if ! command -v go >/dev/null 2>&1; then \
		echo "MISSING: go (required: $(GO_VERSION)) — https://go.dev/dl/"; fail=1; \
	else \
		gv=$$(go version | awk '{print $$3}' | sed 's/^go//'); \
		gv_minor=$$(echo "$$gv" | cut -d. -f1,2); req_minor=$$(echo "$(GO_VERSION)" | cut -d. -f1,2); \
		if [ "$$(printf '%s\n%s\n' "$$req_minor" "$$gv_minor" | sort -V | head -1)" != "$$req_minor" ]; then \
			echo "MISMATCH: go version is older than versions.env requires (required: $(GO_VERSION)+). Found: $$gv"; fail=1; \
		fi; \
	fi; \
	if ! command -v python3 >/dev/null 2>&1; then \
		echo "MISSING: python3 (required: $(PYTHON_VERSION)) — https://www.python.org/downloads/"; fail=1; \
	else \
		pv=$$(python3 --version | awk '{print $$2}'); pv_minor=$$(echo "$$pv" | cut -d. -f1,2); \
		if [ "$$pv_minor" != "$(PYTHON_VERSION)" ]; then \
			echo "MISMATCH: python3 minor version does not match versions.env (required: $(PYTHON_VERSION)). Found: $$pv"; fail=1; \
		fi; \
	fi; \
	if [ "$$fail" -ne 0 ]; then \
		echo ""; echo "make deps: one or more tools are missing or mismatched (see above). Exiting non-zero."; \
		exit 1; \
	fi; \
	echo "All pinned tools present and matching versions.env."
	hugo mod get
	hugo mod npm pack
	npm ci || npm install

serve: ## Serve the site locally with live reload (drafts and future content included)
	hugo server --buildDrafts --buildFuture

build: ## Production build to public/ — warnings and errors both fail the build
	@rm -f .hugo-build.log
	@hugo --gc --minify 2>&1 | tee .hugo-build.log; \
	status=$${PIPESTATUS[0]}; \
	if [ "$$status" -ne 0 ]; then \
		echo "hugo build failed (exit $$status)"; exit 1; \
	fi; \
	if grep -qE '^(WARN|ERROR)' .hugo-build.log; then \
		echo ""; echo "Build produced warnings or errors — treated as failures (spec AC-3):"; \
		grep -E '^(WARN|ERROR)' .hugo-build.log; \
		rm -f .hugo-build.log; exit 1; \
	fi; \
	rm -f .hugo-build.log
	@echo ""; echo "Checking no internal-only file leaked into public/ (spec §5.4, AC-15) ..."
	@if find public -type f | grep -qE '(^|/)(STANDARDS|engineering-standards)\.html$$'; then \
		echo "FAIL: an internal-only file was published under public/"; \
		find public -type f | grep -E '(^|/)(STANDARDS|engineering-standards)\.html$$'; exit 1; \
	fi
	@echo "OK: no internal-only file published."

markdownlint: ## Markdown style check
	npx --yes markdownlint-cli2@$(MARKDOWNLINT_CLI2_VERSION) "content/**/*.md"

frontmatter-lint: ## Front-matter contract check
	python3 scripts/check-frontmatter.py content

house-rules-lint: ## kropath authoring house-rules check
	python3 scripts/check-house-rules.py content

# htmltest has no concept of hugo.toml's baseURL, so it cannot resolve the
# absolute-path hrefs a GitHub Pages project-site build produces (e.g.
# /kropath-docs/docs/concepts/) against a public/ directory that has no
# kropath-docs/ subfolder on disk. Rebuilding with a root baseURL here keeps
# link-checking self-consistent without changing the real deploy artifact
# that `make build`/`make publish` produce for hugo.toml's pinned Pages URL.
link-check: ## Internal link/anchor check (rebuilds with a root baseURL for local resolution)
	hugo --gc --minify --baseURL "/" --destination public
	htmltest --conf .htmltest.yml

link-check-external: ## Weekly-only, non-blocking external link check (never part of `lint`)
	hugo --gc --minify --baseURL "/" --destination public
	htmltest --conf .htmltest-external.yml

lint: markdownlint frontmatter-lint house-rules-lint link-check ## All lint checks in spec §8
	@echo "All lint checks passed."

check: build lint ## The pre-push gate — exactly what CI runs

clean: ## Remove all build artifacts
	rm -rf public resources/_gen .hugo_build.lock .hugo-build.log tmp/.htmltest

publish: ## Produce the deployable artifact (CI-only unless ALLOW_LOCAL_PUBLISH=1)
	@if [ "$$CI" != "true" ] && [ "$$ALLOW_LOCAL_PUBLISH" != "1" ]; then \
		echo "make publish is intended to run in CI only."; \
		echo "Set ALLOW_LOCAL_PUBLISH=1 if you really want to build the deployable artifact locally."; \
		exit 1; \
	fi
	$(MAKE) build
