@docs/STANDARDS.md

## This Repo

**kropath-docs** — Customer-facing documentation only; no runnable code.

- Pure documentation: guides, API references, tutorials for kropath users
- No CRDs, kro RGDs, or Go code — documentation repo only
- Specs and ADRs in `kropath-core` are the authoritative design record to **write from**. Consult
  them as your source; never cite or link them in a published page — the reader has no access to
  them. State the reason they capture, in the reader's own terms, and drop the citation.
- Do not copy implementation details here. Do not link to internal repositories either: a
  published page may link only to other kropath-docs pages and to external kro, ACK, AWS, and
  Kubernetes documentation. Describe internal behaviour from the reader's side instead.
- See the `kropath-docs-authoring` skill in `kropath-core` for the full authoring rules: audience
  boundary, link discipline, constraint/gap/requirement terminology, and schema fidelity.
