# ECRPublicConfig — Governance for Public Container Repositories

`ECRPublicConfig` is a governance CRD that platform teams deploy to enforce organization-wide controls on ECR Public repositories. It defines mandatory naming conventions, required tags, and synchronized labels/annotations for all public repositories created within its scope.

## When to Use ECRPublicConfig

- **Platform teams** define naming standards (e.g., `{namespace}/{name}`) and mandatory tags (e.g., `org: my-company`)
- **Multiple profiles** enable different governance tiers (e.g., `general-policy` for permissive use, `open-source` for strict tagging)
- **Application teams** select a profile via `ECRPublicRepository.spec.configRef` and inherit those controls

## Core Concepts

### Mandatory vs Defaults Tiers

Each `ECRPublicConfig` has two governance tiers:

| Tier | Behavior | Example |
|---|---|---|
| **Mandatory** | Enforced on all repositories using this profile; cannot be overridden by application teams | Org ownership tag (`org: my-company`), naming pattern requiring project prefix |
| **Defaults** | Applied only when the repository instance omits a field; can be overridden by the instance | Default naming pattern (`{namespace}/{name}`), default tags like `visibility: public` |

When you create an `ECRPublicRepository`, the governance cascade resolves fields as:
```
mandatory > instance spec > defaults
```

### Profile Selection

Application teams select a governance profile when creating a repository:

```yaml
spec:
  configRef: general-policy  # Selects ECRPublicConfig/general-policy
```

If the referenced profile does not exist, the system falls through to `general-policy` (the built-in default). This ensures that repositories always have some governance applied even if a custom profile is misconfigured or deleted.

## Core Fields

### Naming Governance

| Field | Type | Tier | Purpose |
|---|---|---|---|
| `namingTemplate` | string | mandatory or defaults | Template for deriving the cloud repository name from Kubernetes metadata. Empty string = not enforced |

**Naming template tokens:**

| Token | Resolves to | Example |
|---|---|---|
| `{name}` | `metadata.name` of the ECRPublicRepository | `{name}` → `my-app` |
| `{namespace}` | Kubernetes namespace | `{namespace}` → `default` |
| `{configRef}` | The selected profile name | `{configRef}` → `general-policy` |
| `{account_id}` | AWS account ID from `KropathConfig` | `{account_id}` → `123456789012` |
| `{region}` | AWS region from `KropathConfig` | `{region}` → `us-east-1` |
| `{tag.KEY}` | Value of a cloud tag or synced label | `{tag.team}` → `backend` |

**Default naming template:** `{namespace}/{name}`

ECR Public repositories natively support forward slashes (`/`) in repository names, so hierarchical naming like `project-a/nginx-web-app` is both valid and encouraged for organizational clarity.

**Character constraints:** ECR Public repository names must match the regex `^(?:[a-z0-9]+(?:[._-][a-z0-9]+)*/)*[a-z0-9]+(?:[._-][a-z0-9]+)*$`. Repository names are lowercase-only; no uppercase letters.

**Immutability:** The `namingTemplate` cannot be set in both `mandatory` and `defaults` tiers simultaneously — only one tier may specify it.

### Tag Governance

| Field | Type | Tier | Purpose |
|---|---|---|---|
| `tags` | map[string]string | mandatory or defaults | Cloud tags applied to the repository in AWS |

When an application team creates an `ECRPublicRepository`, the final tag set is the additive merge of mandatory tags, instance tags, and default tags:

```
finalTags = mandatory.tags + instance.spec.tags + defaults.tags
```

On key collision, **mandatory tags always win**, ensuring platform teams can enforce critical tracking tags (e.g., `owner: platform-team`, `compliance: pci-required`).

### Synced Labels and Annotations

| Field | Type | Tier | Purpose |
|---|---|---|---|
| `syncedLabels` | map[string]string | mandatory or defaults | Kubernetes labels also synced to AWS cloud tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map[string]string | mandatory or defaults | Kubernetes annotations synced to cloud resource tags (prefixed `aws.kropath.run/`) |

These fields enable bidirectional metadata sync between Kubernetes and AWS. For example:

```yaml
spec:
  mandatory:
    syncedLabels:
      data-classification: public
      team: platform
```

Results in both Kubernetes labels and AWS cloud tags containing `aws.kropath.run/data-classification: public` and `aws.kropath.run/team: platform`.

## Status Fields

After you create an `ECRPublicConfig`, the `status` block contains:

| Field | Type | Purpose |
|---|---|---|
| `observedGeneration` | integer | Generation of the spec most recently reconciled by kropath-controller |
| `syncedTimestamp` | string | RFC3339 timestamp of the last successful reconcile |
| `conditions` | array | Standard Kubernetes conditions (e.g., `Ready`, `Available`) |
| `effectiveConfig` | object | Pre-merged governance config; RGDs read exclusively from this field |

The `effectiveConfig` is written by `kropath-controller` and represents the final merged configuration from both `KropathConfig` (organization-wide) and `ECRPublicConfig` (profile-specific) tiers. RGDs never read `spec` directly — they read only `status.effectiveConfig` to ensure consistent behavior across all resources using the profile.

## Example: Default Profile

A permissive default profile with no mandatory enforcement:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPublicConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    namingTemplate: "{namespace}/{name}"
    tags: {}
```

All repositories using `general-policy` will have names like `default/my-app` (namespace/name) and no enforced tags.

## Example: Strict Profile with Org Ownership

A restrictive profile that mandates organization ownership and a specific naming pattern:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPublicConfig
metadata:
  name: open-source
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: open-source
spec:
  mandatory:
    namingTemplate: "{configRef}/{namespace}/{name}"
    tags:
      org: my-company
      visibility: public
    syncedLabels:
      governance: platform-managed
  defaults: {}
```

All repositories using `open-source` will:
- Have names like `open-source/team-a/my-app` (profile/namespace/name)
- Include mandatory tags `org: my-company` and `visibility: public`
- Have the Kubernetes label `governance: platform-managed` (also synced to AWS tags)
- Application teams cannot override these mandatory fields

## Creating and Updating Profiles

Platform teams deploy `ECRPublicConfig` CRs once, then application teams reference them by name. To create a new profile:

```bash
kubectl apply -f general-policy.yaml
```

To update an existing profile (e.g., add a new mandatory tag):

```bash
kubectl patch ecrpublicconfig general-policy \
  --type=merge \
  -p '{"spec":{"mandatory":{"tags":{"new-tag":"new-value"}}}}'
```

All repositories referencing the updated profile will automatically adopt the new governance the next time they reconcile.

## Best Practices

1. **Keep `general-policy` permissive** — use it as the fallback for development and experimentation
2. **Use specific profiles for compliance** — e.g., `open-source` for projects that must publish to the public gallery with strict ownership tracking
3. **Avoid frequent profile changes** — changing mandatory fields affects all repositories using the profile
4. **Document profile intent** — add comments in each profile YAML explaining its purpose and intended audience
5. **Test profile changes locally** — verify new naming patterns and tags work as expected before deploying to production
