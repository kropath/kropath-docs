# SecretsManagerSecret — Creating and Managing Secrets

The `SecretsManagerSecret` resource represents a single secret in AWS Secrets Manager. This guide covers all configuration fields, governance cascade, and real-world usage patterns.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SecretsManagerConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the secret name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the secret resource is deleted: `"retain"` (safe) or `"delete"` |

### Secret Properties

| Field | Type | Default | Purpose |
|---|---|---|---|
| `description` | string | `""` | Human-readable description of the secret's purpose |
| `secretRef` | object | optional | Reference to a Kubernetes Secret containing the initial secret value |
| `secretRef.name` | string | required | Name of the Kubernetes Secret (in the same namespace) |
| `secretRef.key` | string | required | Key within the K8s Secret's data map |

### Encryption

| Field | Type | Default | Purpose |
|---|---|---|---|
| `kmsKeyRef` | string | `""` | Reference to a local `KMSKey` CR for encryption. Mutually exclusive with `kmsKeyArn`. |
| `kmsKeyArn` | string | `""` | Direct AWS KMS key ARN, key ID, or alias. Mutually exclusive with `kmsKeyRef`. When both empty, uses governance default or AWS managed key. |

### Cross-Region Replication

| Field | Type | Default | Purpose |
|---|---|---|---|
| `replicaRegions` | array | `[]` | Regions to replicate this secret to for disaster recovery. Overridable by governance mandatory tier. |
| `replicaRegions[].region` | string | required | AWS region code (e.g. `us-west-2`) |
| `replicaRegions[].kmsKeyID` | string | `""` | KMS key for the replica (defaults to AWS managed key in that region if empty) |
| `forceOverwriteReplicaSecret` | boolean | `false` | If true, overwrite an existing secret with the same name in the destination region |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation, the secret's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective secret name in AWS (derived from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if the resource name is ready, `"invalid-unresolved-tokens"` if naming template has unresolved tokens |
| `predictedArn` | string | ARN prefix of the secret in AWS format: `arn:aws:secretsmanager:region:account:secret:resourceName` (AWS appends a random 6-character suffix) |
| `secretArn` | string | Full canonical ARN after creation (populated by AWS Secrets Manager) |

## Naming Convention

Secrets are named using a configurable template. The default template is `{namespace}-{name}`, which produces resource names like `app-team-db-password` (where `app-team` is the Kubernetes namespace and `db-password` is the resource name).

**Available naming tokens:**
- `{name}` — The resource's Kubernetes name
- `{namespace}` — The resource's Kubernetes namespace
- `{configRef}` — The selected governance profile name
- `{account_id}` — AWS account ID (from governance)
- `{region}` — AWS region (from governance)
- `{tag.KEY}` — Any tag key from the merged tags (e.g. `{tag.environment}`)

Example: A profile with `namingTemplate: "{namespace}-{configRef}-{tag.environment}-{name}"` would produce names like `payments-pci-production-api-key`.

**Important:** The secret name is immutable after creation in AWS. Changing `spec.nameOverride` or the governance naming template on an existing secret does not rename the AWS secret — it remains registered under its original name.

## Complete Examples

### Basic Secret Creation

Create a simple secret without initial value or special encryption:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SecretsManagerSecret
metadata:
  name: api-token
  namespace: app-team
spec:
  configRef: general-policy
  description: "API token for third-party integration"
  deletionPolicy: retain
```

Result:
- Secret created in AWS Secrets Manager with name `app-team-api-token`
- Uses AWS managed encryption key (`aws/secretsmanager`)
- No replication
- Deletion of the Kubernetes resource keeps the AWS secret intact

### Secret with Initial Value

Create a secret with an initial value stored in a Kubernetes Secret:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-creds
  namespace: app-team
type: Opaque
data:
  password: cGFzc3dvcmQxMjM=  # base64-encoded password
---
apiVersion: aws.kropath.run/v1alpha1
kind: SecretsManagerSecret
metadata:
  name: db-password
  namespace: app-team
spec:
  configRef: general-policy
  description: "Database password"
  secretRef:
    name: db-creds
    key: password
  deletionPolicy: retain
```

Result:
- Secret created in AWS Secrets Manager
- Initial value populated from the Kubernetes Secret's `data.password` field
- Value can be rotated outside Kubernetes without re-creating the resource

### Custom Encryption Key

Encrypt a secret with a customer-managed KMS key:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SecretsManagerSecret
metadata:
  name: sensitive-token
  namespace: security
spec:
  configRef: general-policy
  description: "Sensitive authentication token"
  kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/mrk-sensitive"
  deletionPolicy: retain
```

Result:
- Secret encrypted with the specified customer-managed key
- AWS Secrets Manager enforces access through the KMS key's permissions
- Only users/roles with KMS key permissions can decrypt the secret

### Cross-Region Replication for Disaster Recovery

Replicate a secret to a DR region with its own encryption key:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SecretsManagerSecret
metadata:
  name: critical-db-creds
  namespace: production
spec:
  configRef: general-policy
  description: "Critical database credentials"
  replicaRegions:
    - region: us-west-2
      kmsKeyID: "arn:aws:kms:us-west-2:123456789012:key/mrk-dr"
  forceOverwriteReplicaSecret: true
  deletionPolicy: retain
```

Result:
- Secret replicated to `us-west-2` region
- DR replica encrypted with its own regional KMS key
- If a secret with the same name exists in the DR region, it is overwritten

### PCI Compliance Profile

Use a PCI-hardened governance profile with mandatory encryption and replication:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SecretsManagerSecret
metadata:
  name: payment-key
  namespace: payments
spec:
  configRef: pci  # Uses PCI compliance profile
  description: "Payment processing key (PCI-DSS)"
  secretRef:
    name: payment-secret
    key: key
  tags:
    business-critical: "true"
  syncedLabels:
    payment-processing: "true"
  deletionPolicy: retain
```

Result:
- Profile's mandatory KMS key enforced (cannot be overridden)
- Profile's mandatory replication to DR region enforced
- PCI compliance tags applied automatically
- Labels synced to both Kubernetes and AWS tags

## Governance Cascade

The effective configuration for each secret is determined by a three-tier cascade:

1. **Governance mandatory tier** (highest priority) — Platform enforcement that overrides everything
2. **Secret spec** (middle) — Developer choices
3. **Governance defaults tier** (lowest priority) — Fallback values

For example, if the PCI profile has `mandatory.kmsKeyID` set, that key is always used, even if the secret specifies `spec.kmsKeyArn`. If mandatory is empty but the secret doesn't specify encryption, the defaults apply.

Platform teams use the mandatory tier for critical controls (compliance, encryption, replication); developers use the defaults tier for reasonable baselines that developers can override when needed.

## Key Behaviors

### Immutable Secret Name After Creation

Once created in AWS Secrets Manager, a secret's name cannot be changed. The naming template or `nameOverride` field determines the name at creation time only.

### Predictable ARNs

The ARN shown in `status.predictedArn` is a prefix that matches how AWS Secrets Manager names the resource. AWS Secrets Manager appends a random 6-character suffix to the name when creating the secret, so the full ARN in AWS will be longer. Use `status.secretArn` (populated after creation) to get the complete ARN if needed.

### Tag Format

Tags in kropath are specified as a map (e.g. `key: value`). AWS Secrets Manager stores tags internally as a list of key-value pairs. The conversion is handled automatically during reconciliation.

### Deletion Policy

- `retain` (default) — Deleting the Kubernetes resource keeps the secret safe in AWS Secrets Manager
- `delete` — Deleting the Kubernetes resource also deletes the secret in AWS (use with caution)

## Troubleshooting

### Secret Not Creating

Check `status.namingStatus`:
- If `invalid-unresolved-tokens`, the naming template has a token that cannot be resolved (e.g. a tag key that doesn't exist). Fix the template or ensure required tags are present.
- If `valid` but secret not created, check `status.conditions` for errors from AWS (e.g., permission issues, duplicate name).

### Can't Override Encryption or Replication

If governance has a mandatory tier set for `kmsKeyID` or `replicaRegions`, those values cannot be overridden at the secret level. Only the defaults tier can be overridden by the developer. Contact your platform team if you need different encryption or replication settings.

### Secret Won't Delete When `deletionPolicy: delete`

Ensure the Kubernetes service account running kropath has AWS IAM permissions for `secretsmanager:DeleteSecret`. If the secret has resource-based policies restricting deletion, those must be updated in AWS before the Kubernetes resource can be deleted.
