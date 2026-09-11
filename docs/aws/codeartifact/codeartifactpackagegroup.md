# CodeArtifactPackageGroup

`CodeArtifactPackageGroup` is a Kubernetes resource that represents an AWS CodeArtifact package group. It wraps the ACK `PackageGroup` resource and provides a higher-level interface for managing package group policies, access controls, and tagging in a way that's consistent with your organization's governance.

## Scope

This resource is AWS-only. GCP Artifact Registry and Azure Artifacts do not have package group concepts.

## What it solves

Managing CodeArtifact package groups involves several decisions:

- **Domain association** — Which domain does this package group belong to?
- **Pattern matching** — What packages does this group identify (e.g., `npm/*`, `pypi/*`)?
- **Origin controls** — What sources can packages be pulled from (upstream, external, published)?
- **Governance** — Apply org-wide tagging and compliance policies
- **Deletion policy** — What happens when the CR is deleted?

`CodeArtifactPackageGroup` solves this by providing:

- **Domain reference** — Link to a `CodeArtifactDomain` CR or directly specify domain name
- **Pattern-based identification** — Define package patterns in YAML
- **Governance integration** — Inherit tagging and compliance policies from a `CodeArtifactConfig` profile
- **Cross-account support** — Reference domains in the same AWS account
- **Status visibility** — See when the package group is ready and its origin control configuration

## Core Concepts

### Domain Reference

Each package group belongs to exactly one domain. You can reference the domain in two ways:

**1. Reference a `CodeArtifactDomain` CR in the same namespace**:
```yaml
spec:
  domainRef: shared-domain  # References CodeArtifactDomain/shared-domain
```

**2. Directly specify the domain name (for externally managed domains)**:
```yaml
spec:
  domain: my-existing-domain  # Direct domain name string
```

### Package Pattern Matching

Package groups are identified by a pattern. Patterns use simple glob syntax:

- `npm/*` — All NPM packages
- `@company/*` — All scoped packages under @company
- `pypi/*` — All Python packages
- `maven/com/example/*` — All Maven packages under com.example
- `gem-internal-*` — Ruby gems matching the pattern

The pattern is immutable after creation. If you need to change a pattern, delete and recreate the package group.

### Origin Controls

Package groups control how packages can be sourced:

- **PUBLISH** — Allow direct package publication to this group
- **UPSTREAM** — Allow pulling packages from upstream repositories
- **EXTERNAL_UPSTREAM** — Allow pulling from external upstream sources (outside your organization)
- **INTERNAL_UPSTREAM** — Allow pulling from internal upstream sources (within your organization)

**Important limitation:** Origin controls are currently read-only in kropath. You can view origin configurations in `status.originConfiguration`, but modifying them requires the AWS CLI/SDK until a future ACK controller version adds spec support (Gap G-3).

### Hierarchical Inheritance

Package groups can be organized hierarchically. Child package groups inherit origin control restrictions from parent groups. For example:
- Parent: `npm/*` (all NPM packages)
- Child: `npm/@company/*` (only company-scoped packages)

The child group inherits the parent's origin restrictions.

## Complete Example

```yaml
---
# Create a CodeArtifact domain first
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactDomain
metadata:
  name: shared-domain
  namespace: platform
spec:
  configRef: general-policy
  encryptionKey: ""
  deletionPolicy: retain

---
# Create a governance profile for package groups
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    tags:
      managed-by: kropath
    syncedLabels:
      environment: production

---
# Create an NPM package group
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactPackageGroup
metadata:
  name: npm-packages
  namespace: platform
spec:
  # Reference domain via CR
  configRef: general-policy
  domainRef: shared-domain
  
  # Pattern: match all NPM packages
  pattern: "npm/*"
  
  # Human-readable metadata
  contactInfo: "platform-team@example.com"
  description: "Internal NPM packages for company projects"
  
  # Deletion policy
  deletionPolicy: retain
  
  # Tagging for cost tracking
  tags:
    package-type: javascript
    team: platform
  
  # Labels to sync
  syncedLabels:
    environment: production
    team: platform
  
  syncedAnnotations:
    support-channel: "#platform-eng"

---
# Create a scoped NPM package group (child of npm/*)
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactPackageGroup
metadata:
  name: npm-company-packages
  namespace: platform
spec:
  configRef: general-policy
  domainRef: shared-domain
  
  # More restrictive pattern: only company-scoped packages
  pattern: "npm/@company/*"
  
  contactInfo: "company-eng@example.com"
  description: "Internal @company scoped NPM packages"
  
  deletionPolicy: retain
  
  tags:
    package-type: javascript
    team: company-engineering

---
# Create a PyPI package group
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactPackageGroup
metadata:
  name: python-packages
  namespace: platform
spec:
  configRef: general-policy
  domainRef: shared-domain
  
  pattern: "pypi/*"
  
  contactInfo: "python-team@example.com"
  description: "Internal Python packages"
  
  deletionPolicy: retain
  
  tags:
    package-type: python
    team: data-science
```

After applying this:

```bash
kubectl describe codeartifactpackagegroup npm-packages -n platform
```

You'll see:

- `status.packageGroupArn` — The full ARN of the package group
- `status.domainName` — The domain name (resolved from `domainRef` or direct `domain`)
- `status.originConfiguration` — Current origin control restrictions (read-only)
- `status.parentArn` — Parent package group ARN if this is a child group
- Standard reconciliation conditions

## Cross-Account Domain Reference

If the domain is in a different AWS account, specify both the domain name and account ID:

```yaml
spec:
  domain: "shared-org-domain"
  domainOwner: "987654321098"  # 12-digit AWS account ID
  pattern: "maven/*"
```

## Direct Domain Reference

For externally managed domains (not created via kropath), specify the domain directly:

```yaml
spec:
  domain: "my-existing-domain"
  pattern: "npm/*"
  contactInfo: "support@example.com"
```

## Reference Specification

### Spec Fields

| Field | Type | Required? | Default | Notes |
|---|---|---|---|---|
| `configRef` | string | No | `general-policy` | Profile name for governance (tagging, synced labels). |
| `domainRef` | string | No | empty | Name of `CodeArtifactDomain` CR in same namespace. Mutually exclusive with `domain`. |
| `domain` | string | No | empty | Direct domain name string. Mutually exclusive with `domainRef`. One of `domain` or `domainRef` is required. |
| `domainOwner` | string | No | empty | 12-digit AWS account ID if domain is in a different account. Only needed for cross-account references. |
| `pattern` | string | **Yes** | (required) | Pattern identifying the package group (e.g., `npm/*`, `pypi/*`). Immutable after creation. |
| `contactInfo` | string | No | empty | Contact information for the package group (email, Slack channel). |
| `description` | string | No | empty | Human-readable description of the package group. |
| `deletionPolicy` | `retain` \| `delete` | No | `retain` | Delete AWS package group when CR is deleted? |
| `tags` | map[string]string | No | `{}` | Cloud tags. Merged with profile (profile mandatory tags override). |
| `syncedLabels` | map[string]string | No | `{}` | Labels to sync to K8s and cloud tags. |
| `syncedAnnotations` | map[string]string | No | `{}` | Annotations to sync to K8s. |

### Status Fields

| Field | Type | Meaning |
|---|---|---|
| `packageGroupArn` | string | Full ARN of the package group. |
| `domainName` | string | Domain name (resolved from `domainRef` or from spec). |
| `originConfiguration` | object | Current origin control restrictions (read-only). |
| `originConfiguration.restrictions` | object | Map of restriction types (PUBLISH, UPSTREAM, etc.) to their status. |
| `parentArn` | string | ARN of parent package group in hierarchy (if child). |
| `parentPattern` | string | Pattern of parent package group (if child). |
| `conditions[]` | list | Standard reconciliation conditions (Ready, etc.). |

## Domain Resolution

When you specify `domainRef`, the package group automatically resolves the domain name from the `CodeArtifactDomain` CR's status:

```yaml
spec:
  domainRef: shared-domain  # Looks up CodeArtifactDomain/shared-domain
```

The CR reads `status.resourceName` from the domain to get the actual cloud domain name. This allows you to change domain names via the naming template without updating all package groups.

## Origin Controls (Status-Only)

Origin controls are currently read-only in kropath. To set origin restrictions, use the AWS CLI:

```bash
aws codeartifact update-package-group-origin-configuration \
  --domain shared-domain \
  --package-group npm/* \
  --restrictions restrictPublish=ALLOW,restrictDownstreamPublish=ALLOW
```

The `status.originConfiguration` field reflects the current restrictions set via AWS CLI/SDK.

**Note:** Once ACK controller support is added (Gap G-3), origin controls will become configurable via spec fields in a future kropath version.

## Pattern Rules

Package patterns use the following syntax:

- **`*`** — Wildcard matching (matches any sequence of characters within a segment)
- **`/`** — Segment separator
- **No wildcards in root** — Patterns must start with a package type or namespace

Valid examples:
- `npm/*` — All NPM packages
- `@company/*` — All packages under @company scope
- `pypi/*` — All Python packages
- `maven/com/example/*` — All Maven packages under com.example
- `gem-internal-*` — Ruby gems matching pattern

Invalid examples:
- `*/*` — Cannot start with wildcard
- `npm*` — Missing segment separator

## Naming Exemption

Unlike domains, package groups do not have user-chosen names. They are identified by domain + pattern (composite key). Therefore:

- No `effectiveName` or naming template applies
- No `status.resourceName` or `status.predictedArn` in status
- No `nameOverride` in spec

## Deleting a Package Group

By default, `spec.deletionPolicy: retain` means the Kubernetes CR can be deleted without deleting the AWS package group. The package group persists in AWS.

To delete both:

```yaml
spec:
  deletionPolicy: delete  # AWS package group will be deleted when CR is deleted
```

## Profile Inheritance

When using a `CodeArtifactConfig` profile, the package group inherits:

- **Tagging** — Org-wide and profile tags
- **Synced labels** — Labels to apply to K8s metadata and cloud tags
- **Synced annotations** — Annotations to apply to K8s metadata

Tags from the profile are merged with instance tags; profile mandatory tags take precedence on key conflicts.

## Best Practices

1. **Create a domain first** — Ensure the domain exists before creating package groups.

2. **Use governance profiles** — Select a `CodeArtifactConfig` profile so tagging is consistent and automatic.

3. **Set contact information** — Use `contactInfo` and `syncedAnnotations` to track who manages this package group.

4. **Organize by pattern hierarchy** — Create parent patterns (e.g., `npm/*`) first, then child patterns (e.g., `npm/@company/*`).

5. **Manage origin controls outside kropath** — Use AWS CLI or Management Console to set origin restrictions until kropath spec support is available.

6. **Tag for cost tracking** — Include team and package-type tags at creation.

7. **Document patterns** — Use `description` to explain what packages this group contains and who should use it.

8. **Test access policies** — After creating package groups, test that repositories can publish and pull packages as intended.

## Troubleshooting

### Domain not found

```
Error: CodeArtifactDomain shared-domain not found
```

The `domainRef` points to a domain that doesn't exist or is in a different namespace. Ensure the domain exists in the same namespace, or use `domain` + `domainOwner` for cross-account references.

### Missing required field

```
Error: one of domain or domainRef is required
```

Provide either `domain` (direct name) or `domainRef` (CR reference).

### Domain/domainRef mutual exclusivity

```
Error: domain and domainRef are mutually exclusive
```

You specified both. Provide only one.

### Pattern immutability

```
Error: pattern is immutable after creation
```

You tried to change the pattern on an existing package group. Patterns cannot be changed. Delete and recreate the package group with the new pattern.

### Invalid pattern

```
Error: invalid pattern
```

The pattern doesn't match AWS CodeArtifact pattern rules. Ensure it includes a segment separator (`/`) and doesn't start with a wildcard.

### Origin controls status-only

```
status.originConfiguration is read-only; to modify origin controls, use AWS CLI
```

Origin controls cannot yet be configured via kropath spec. Use `aws codeartifact update-package-group-origin-configuration` via the AWS CLI.

## API Reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `CodeArtifactPackageGroup`
- **Scope**: Namespaced
