# kropath-docs Standards

**Shared engineering standards** (CRD/RGD schema, API groups, kind naming, label/annotation
conventions, wiring, effectiveConfig cascade): see
`kropath-core/docs/standards/engineering-standards.md`.

---

## This Repository

`kropath-docs` — Customer-facing documentation only; no runnable code.

- Guides, API references, and tutorials for kropath platform users
- References specs and ADRs from `kropath-core` as the authoritative design record
- Link to implementation details; never copy them here
- No CRDs, kro RGDs, or Go code

---

## Documentation-Specific Rules

- **Link, don't copy.** Reference ADRs and specs by path from `kropath-core`. Do not
  duplicate implementation content in this repo.
- **API group in examples.** Use `<provider>.kropath.run` (e.g. `aws.kropath.run/v1alpha1`).
  The bare `kropath.run` group is deprecated and must not appear in new examples.
- **ExternalRef in examples.** All code examples must use `selector.matchLabels` for
  `externalRef` lookups — never `metadata.name` with a CEL expression. (Theme 28, KRO-221)
- **Kind names in examples.** No provider prefix in kind — `S3Config`, not
  `AWSS3BucketConfig`; `KropathConfig`, not `AWSKropathConfig`.

---

## Metadata Key Convention

All agents use these standard keys in the Multica issue metadata bag. Keys outside this table
require justification.

| Key | Type | Set by | Read by | Meaning |
|---|---|---|---|---|
| `pr_url` | string | Implementer | Reviewer | The PR to review |
| `pr_number` | number | Implementer | Reviewer | GitHub PR number |
| `blocked_by` | string | Issue creator | All agents | Prerequisite issue ID |
| `waiting_on` | string | Any | Any | Current blocker role or description |
| `completed_steps` | string (JSON array) | Any | Same agent on re-entry | Steps completed in a multi-step task |

### Usage rules

- **Read on entry.** Run `multica issue metadata list <id> --output json` at the start of
  every run. Check `blocked_by` first — if set, verify its status is `done` before proceeding.
- **Write sparingly.** Pin a value only when BOTH are true: (a) it is materially important to
  this issue's progress, AND (b) a future run on this same issue is likely to read it rather
  than re-derive it from comments or code.
- **Clean up stale keys on exit.** Overwrite or delete stale keys before exiting.
- **Never pin secrets, tokens, or API keys.**

---

## Other Standards

- **Security First:** Default to secure; mandatory config overrides user input.
- **Licensing:** Apache 2.0 headers in every RGD and script.
- **CEL:** Use `${}` for all dynamic values.
