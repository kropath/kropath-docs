# CodeArtifactDomain

`CodeArtifactDomain` is a Kubernetes resource that represents an AWS CodeArtifact domain. It wraps the ACK `Domain` resource and provides a higher-level interface for managing domain encryption, naming, tagging, and governance in a way that's consistent with your organization's policies.

## Scope

This resource is AWS-only. GCP Artifact Registry and Azure Artifacts have different organizational models and do not have domain concepts.

## What it solves

Creating and managing CodeArtifact domains involves many decisions:

- **Encryption** — AWS-managed or customer-managed KMS keys?
- **Naming** — How should domain names follow your organization's conventions?
- **Governance** — Every domain should follow org-wide policies (encryption, naming, tagging)
- **Deletion policy** — What happens when the CR is deleted?
- **Tagging** — Track ownership, cost center, environment

Manually setting each policy on every domain creates inconsistency and drift. `CodeArtifactDomain` solves this by providing:

- **Governance integration** — Inherit encryption, naming, and tagging policies from a `CodeArtifactConfig` profile
- **Flexible encryption** — AWS-managed (default), customer-managed via direct ARN, or via a `KMSKey` resource reference
- **Automatic naming** — Domain names are generated from a template
- **ARN tracking** — Know the predicted ARN for reference by other resources
- **Status visibility** — See when the domain is ready, its encryption key, and its lifecycle status

## Core Concepts

### Domain Hierarchy

A CodeArtifact domain is the top-level container for repositories and packages. All repositories in a domain share:

- The same KMS encryption key (immutable after creation)
- The same S3 asset storage bucket
- The same access control policies

### Encryption Options

**AWS-Managed Key** (default):
- Encryption key managed by AWS
- No additional cost
- Simplest operational model
- Sufficient for most workloads

**Customer-Managed KMS Key**:
- You manage the encryption key via AWS KMS
- Required for compliance audits (you control key rotation and access)
- Additional AWS KMS costs
- Two ways to specify:

  1. **Direct ARN** — reference a KMS key you've already created:
     ```yaml
     encryptionKey: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
     ```

  2. **Reference a `KMSKey` resource** — let kropath manage the key:
     ```yaml
     encryptionKeyRef: my-domain-key
     ```
     The controller resolves the reference to the key's ARN at composition time.

**Important:** Encryption is immutable after domain creation. Choose carefully when creating the domain.

### Naming Templates

Domain names are generated from templates using tokens:

| Token | Value |
|---|---|
| `{namespace}` | Kubernetes namespace |
| `{name}` | CR name |
| `{account_id}` | AWS account ID |
| `{region}` | AWS region |
| `{configRef}` | Selected profile name |
| `{tag.<key>}` | Tag value |

**Example template**: `{namespace}-{name}` generates `dev-team-shared-domain` for a CR named `shared-domain` in namespace `dev-team`.

**AWS constraints**: Domain names must be 2–50 characters, lowercase alphanumeric and hyphens only, starting and ending with alphanumeric characters.

### Governance Cascade

The effective configuration for each domain follows this priority:

1. **Mandatory tier** (highest priority) — Cannot be overridden by developer
2. **Domain spec** (middle) — Developer choice
3. **Defaults tier** (lowest priority) — Fallback when developer spec is empty

This ensures platform teams can enforce critical controls (encryption, naming) while letting developers handle domain-specific settings.

## Complete Example

```yaml
---
# First, create a customer-managed KMS key for encryption
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: commerce-domain-key
  namespace: commerce
  labels:
    aws.kropath.run/resource-name: commerce-domain-key
spec:
  # ... KMS key configuration ...

---
# Create a production governance profile
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  mandatory:
    encryptionKey: "arn:aws:kms:us-east-1:123456789012:key/prod-cmk"
    namingTemplate: "prod-{namespace}-{name}"
  defaults:
    tags:
      environment: production
      managed-by: kropath

---
# Create a production domain
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactDomain
metadata:
  name: shared-domain
  namespace: commerce
spec:
  # Use production governance profile
  configRef: production
  
  # Deletion policy: retain the AWS domain when CR is deleted
  deletionPolicy: retain
  
  # Tagging for cost tracking and environment
  tags:
    cost-center: commerce-platform
    team: platform-engineering
  
  # Labels to sync to Kubernetes and cloud tags
  syncedLabels:
    environment: production
    owned-by: commerce-team
  
  syncedAnnotations:
    contact-email: commerce-platform@example.com
```

After applying this:

```bash
kubectl describe codeartifactdomain shared-domain -n commerce
```

You'll see:

- `status.resourceName: prod-commerce-shared-domain` — the cloud domain name
- `status.predictedArn: arn:aws:codeartifact:us-east-1:123456789012:domain/prod-commerce-shared-domain` — the full ARN
- `status.domainStatus: Active` — the domain is ready for use
- Standard reconciliation conditions

## Alternative: Direct Encryption Key Reference

If your KMS key already exists and is managed outside kropath, reference it directly:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactDomain
metadata:
  name: shared-domain
  namespace: commerce
spec:
  configRef: general-policy
  # Direct KMS key ARN (no KMSKey CR needed)
  encryptionKey: "arn:aws:kms:us-east-1:123456789012:key/existing-key"
  deletionPolicy: retain
```

## Alternative: AWS-Managed Encryption

For development or non-compliance workloads, use AWS-managed encryption:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactDomain
metadata:
  name: dev-domain
  namespace: dev-team
spec:
  configRef: general-policy
  # Empty: use AWS-managed key
  encryptionKey: ""
  deletionPolicy: retain
```

## Reference Specification

### Spec Fields

| Field | Type | Required? | Default | Notes |
|---|---|---|---|---|
| `configRef` | string | No | `general-policy` | Profile name for governance (encryption, naming, tags). |
| `encryptionKey` | string | No | empty | KMS key ARN for domain encryption. Empty = AWS-managed key. Immutable after creation. Mutually exclusive with `encryptionKeyRef`. |
| `encryptionKeyRef` | string | No | empty | Name of a `KMSKey` CR in the same namespace. Resolved to ARN at composition time. Immutable after creation. Mutually exclusive with `encryptionKey`. |
| `nameOverride` | string | No | empty | Override cloud domain name entirely. Bypasses naming template. |
| `deletionPolicy` | `retain` \| `delete` | No | `retain` | Delete AWS domain when CR is deleted? |
| `tags` | map[string]string | No | `{}` | Cloud tags. Merged with profile (mandatory profile tags override). |
| `syncedLabels` | map[string]string | No | `{}` | Labels to sync to K8s and cloud tags. |
| `syncedAnnotations` | map[string]string | No | `{}` | Annotations to sync to K8s. |

### Status Fields

| Field | Type | Meaning |
|---|---|---|
| `resourceName` | string | Generated cloud domain name (after naming template substitution). |
| `namingStatus` | `valid` \| `invalid-unresolved-tokens` | Whether naming template resolved. `invalid` means a tag is missing. |
| `predictedArn` | string | Full ARN: `arn:aws:codeartifact:{region}:{account_id}:domain/{resourceName}` |
| `domainArn` | string | Actual ARN from AWS after domain creation. |
| `owner` | string | AWS account ID that owns the domain. |
| `s3BucketArn` | string | ARN of the S3 bucket used for domain asset storage. |
| `domainStatus` | string | Operational status: `Active`, `Deleting`, etc. |
| `conditions[]` | list | Standard reconciliation conditions (Ready, etc.). |

## KMS Key Reference vs. Direct ARN

**Use `encryptionKeyRef` when**:
- You want kropath to manage the KMS key resource
- The key is created and deployed via `KMSKey` CR
- You want the full lifecycle to be declarative

**Use `encryptionKey` when**:
- The KMS key exists outside of kropath (manually managed)
- The key is shared across multiple systems
- You just need to reference an existing key

Both approaches work; choose based on your key management strategy.

## Naming Convention

Domain names follow the default template `{namespace}-{name}` or a custom template from the governance profile.

**AWS domain name constraints:**
- 2–50 characters
- Lowercase alphanumeric and hyphens only
- Must start and end with alphanumeric

Example: CR `shared-domain` in namespace `dev-team` with template `{namespace}-{name}` becomes cloud domain `dev-team-shared-domain`.

You can override the entire name with `spec.nameOverride`.

## Deleting a Domain

By default, `spec.deletionPolicy: retain` means the Kubernetes CR can be deleted without deleting the AWS domain. The domain and its repositories persist in AWS.

To delete both:

```yaml
spec:
  deletionPolicy: delete  # AWS domain will be deleted when CR is deleted
```

## Profile Inheritance

When using a `CodeArtifactConfig` profile, the domain inherits:

- **Encryption** — AWS-managed vs. customer-managed (can be mandatory)
- **Naming template** — How cloud domain names are generated
- **Tagging** — Org-wide and profile tags
- **Synced labels** — Labels to apply to K8s metadata and cloud tags

If a profile mandates a specific encryption key via `mandatory.encryptionKey`, the governance cascade applies it automatically to the domain. The developer does not supply anything — the mandatory key is enforced by the controller at reconciliation time.

## Best Practices

1. **Choose encryption upfront** — Encryption is immutable; decide whether you need customer-managed KMS keys before creating the domain.

2. **Use governance profiles** — Select a `CodeArtifactConfig` profile (e.g., `general-policy`, `production`) so encryption and naming are automatic and consistent.

3. **Set contact information** — Use tags or `syncedAnnotations` to track domain ownership and support contacts.

4. **Tag at domain creation** — Cost-tracking and environment tags should be set at creation; retroactive tagging is error-prone.

5. **Use `deletionPolicy: retain` for production** — Protect production domains from accidental deletion.

6. **Plan for cross-account access** — If other AWS accounts need to pull packages from this domain, plan your KMS key policies and repository permissions accordingly.

7. **Monitor domain status** — Domains are typically ready immediately, but check `status.domainStatus` to confirm the domain is `Active`.

## Troubleshooting

### Encryption key conflict

```
Error: encryptionKey and encryptionKeyRef are mutually exclusive
```

You specified both. Provide only one.

```
Error: encryptionKey is immutable after creation
```

You tried to change the encryption key on an existing domain. Encryption is set at creation time and cannot be changed. Create a new domain with the desired key.

```
Error: encryptionKeyRef is immutable after creation
```

You tried to change the referenced `KMSKey` on an existing domain. Key references are immutable. Create a new domain with the desired key reference.

### Key reference not found

```
Error: KMSKey my-domain-key not found
```

The `encryptionKeyRef` points to a `KMSKey` CR that doesn't exist or is in a different namespace. Ensure the key exists in the same namespace as the domain CR.

### Naming invalid

```
status.namingStatus: invalid-unresolved-tokens
```

A tag reference in your naming template is missing. Example: template `{tag.env}_{name}` fails if the `env` tag is absent. Add the missing tag to `spec.tags`.

### Profile not found

```
Error: CodeArtifactConfig general-policy not found
```

The referenced profile doesn't exist in `kro-system`. Create the profile or specify a `configRef` to an existing profile.

## API Reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `CodeArtifactDomain`
- **Scope**: Namespaced
