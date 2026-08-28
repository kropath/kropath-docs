# DSQLCluster — Creating and Managing Aurora DSQL Clusters

The `DSQLCluster` resource represents a single Aurora DSQL cluster — a serverless, multi-Region, PostgreSQL-compatible relational database. This guide covers all configuration fields, governance cascade, and real-world usage patterns.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `DSQLConfig` governance profile to apply; falls through to `general-policy` if profile does not exist |
| `deletionPolicy` | string | `"retain"` | Behavior when the DSQL cluster resource is deleted: `"retain"` (safe) or `"delete"` |

### Cluster Properties

| Field | Type | Default | Purpose |
|---|---|---|---|
| `deletionProtectionEnabled` | pointer to bool | `nil` | `nil` = follow governance cascade; `true` = protection on; `false` = protection off (overrides governance) |
| `kmsKeyArn` | string | `""` | ARN of a KMS key for cluster encryption; mutually exclusive with `kmsKeyRef`; empty = AWS-owned key |
| `kmsKeyRef` | string | `""` | Name of a `KMSKey` CR in the same namespace; RGD resolves ARN from status; mutually exclusive with `kmsKeyArn` |
| `policy` | string | `""` | Raw resource-based IAM policy document (JSON string); mutually exclusive with `clusterPolicyRef` |
| `clusterPolicyRef` | string | `""` | Name of a `PolicyDocument` CR in the same namespace; mutually exclusive with `policy` |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | Instance-level AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

### Multi-Region Topology

| Field | Type | Default | Purpose |
|---|---|---|---|
| `multiRegionProperties` | object | `nil` | Optional; when omitted, cluster is single-Region |
| `multiRegionProperties.witnessRegion` | string | `""` | AWS region name for the witness cluster (e.g., `us-east-2`) |
| `multiRegionProperties.clusters` | string array | `[]` | List of ARNs of linked peer clusters in other regions |

## Cluster Naming — Identity and Connection

Aurora DSQL clusters have **no provider `name` field** — clusters are identified by an auto-generated `identifier` assigned by AWS at creation time.

**Important:** You do not supply a cluster name. Instead, once created, use the cluster identity from status:

```bash
kubectl get dsqlcluster my-cluster -n production -o jsonpath='{.status.identifier}'
# Output: abcdefghijklmnopqrstuvwxyz (26-char alphanumeric)
```

## Deletion Protection

Deletion protection prevents accidental cluster deletion at the AWS API level. It can be enforced at the governance level or overridden per-cluster.

### Default Behavior

When `spec.deletionProtectionEnabled` is omitted (nil), the governance cascade applies:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: prod-cluster
  namespace: production
spec:
  configRef: production
  # deletionProtectionEnabled omitted (nil)
  # → Governance cascade applies:
  #   1. Check production profile mandatory tier
  #   2. Check org-wide KropathConfig mandatory tier
  #   3. Fall through to defaults
```

For the `production` profile (with mandatory `deletionProtectionEnabled: true`), deletion protection is enforced.

### Instance Override

You can explicitly override the governance cascade at the instance level:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: temporary-cluster
  namespace: sandbox
spec:
  configRef: production
  deletionProtectionEnabled: false   # Override: disable protection (explicit override)
  # However, if production profile has mandatory: true,
  # this instance value is overridden and protection is enforced anyway
```

**Important:** If governance has `mandatory.deletionProtectionEnabled: true`, the instance-level `false` is ignored and protection is enforced.

## Cluster Encryption

Aurora DSQL supports three encryption options. They are mutually exclusive in the instance spec (only one field per cluster):

### AWS-Owned Key (Default)

When you omit all KMS key fields, AWS creates and manages the encryption key:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: default-encryption
  namespace: production
spec:
  # No kmsKeyArn, no kmsKeyRef → AWS-owned key
```

**Behavior:**
- AWS generates and manages the key
- No customer maintenance
- Cannot be rotated or replaced
- Lowest cost option
- Sufficient for non-compliance-critical workloads

### Customer-Managed Key (Direct ARN)

Provide the KMS key ARN directly:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: customer-managed-cluster
  namespace: production
spec:
  kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
```

**Behavior:**
- You control the KMS key lifecycle
- Key rotation handled by KMS key policy
- Can be revoked at any time
- Required for compliance (PCI-DSS, SOC 2, HIPAA)

### Customer-Managed Key (KMSKey Reference)

Reference a managed `KMSKey` CR for portability and reuse:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: dsql-cluster
  namespace: production
spec:
  kmsKeyRef: my-cluster-encryption-key
  # KMSKey/my-cluster-encryption-key must exist in the same namespace
```

**Behavior:**
- RGD resolves the referenced `KMSKey` and extracts its ARN
- Portable: if the `KMSKey` is updated, the cluster uses the new key
- Enforces explicit key governance (keys defined as first-class resources)
- Best for large-scale, multi-cluster deployments

**Mutual Exclusivity:**
```yaml
spec:
  kmsKeyArn: "arn:aws:kms:..."
  kmsKeyRef: "my-key"  # ERROR: both specified
```
This is rejected by `x-kubernetes-validations`.

## Cluster Access Policies

Control who can connect to your DSQL cluster using resource-based IAM policies. Two approaches:

### Raw JSON Policy

Provide the complete policy document inline:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: restricted-cluster
  namespace: production
spec:
  policy: |
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "AllowApplicationRole",
          "Effect": "Allow",
          "Principal": {"AWS": "arn:aws:iam::123456789012:role/payments-app"},
          "Action": ["dsql:DbConnectAdmin", "dsql:DbConnect"],
          "Resource": "*"
        },
        {
          "Sid": "AllowReadOnlyRole",
          "Effect": "Allow",
          "Principal": {"AWS": "arn:aws:iam::123456789012:role/analytics"},
          "Action": "dsql:DbConnect",
          "Resource": "*"
        }
      ]
    }
```

**Pros:**
- Complete control over policy structure
- No external dependencies
- Good for one-off or highly customized policies

**Cons:**
- Inline JSON is verbose
- Policy duplication across multiple clusters
- Harder to audit consistency

### PolicyDocument Reference

Reference a managed `PolicyDocument` CR for reuse:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: dsql-cluster
  namespace: production
spec:
  clusterPolicyRef: dsql-standard-access
  # PolicyDocument/dsql-standard-access must exist in the same namespace
```

**Pros:**
- Reuse policy across multiple clusters
- Single source of truth for policy
- Easier to audit and update

**Cons:**
- Requires external `PolicyDocument` CR
- One more resource to manage

**Mutual Exclusivity:**
```yaml
spec:
  policy: "{...}"
  clusterPolicyRef: "my-policy"  # ERROR: both specified
```
This is rejected by `x-kubernetes-validations`.

## Multi-Region Topology

Aurora DSQL supports active-active replication across AWS regions via multi-Region clusters. Each region's cluster is a separate `DSQLCluster` CR.

### Single-Region Cluster (Default)

When `multiRegionProperties` is omitted, the cluster is created in a single region:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: us-east-1-cluster
  namespace: production
spec:
  # No multiRegionProperties → single-Region cluster
```

### Multi-Region Topology

To create a multi-Region cluster, specify the witness region and peer cluster ARNs:

```yaml
---
# Primary cluster (us-east-1)
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: primary-cluster
  namespace: production
spec:
  multiRegionProperties:
    witnessRegion: us-east-2
    clusters:
      - arn:aws:dsql:us-west-2:123456789012:cluster/secondary-cluster-id
---
# Secondary cluster (us-west-2)
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: secondary-cluster
  namespace: production
spec:
  multiRegionProperties:
    witnessRegion: us-east-2
    clusters:
      - arn:aws:dsql:us-east-1:123456789012:cluster/primary-cluster-id
```

**Important Notes:**
- Each region's cluster is a separate `DSQLCluster` CR in your namespace (no composite RGD in P0)
- The witness region is where Aurora DSQL writes quorum metadata for failover
- All clusters in a multi-Region topology must reference each other's ARNs
- AWS validates topology consistency; invalid configurations are rejected with clear error messages

## Complete Example: Production Cluster

A production DSQL cluster with all best practices:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: payments-prod-db
  namespace: payments-prod
spec:
  configRef: production
  deletionPolicy: retain
  deletionProtectionEnabled: true     # Enforced by production profile
  kmsKeyRef: payments-cluster-key     # References KMSKey/payments-cluster-key
  clusterPolicyRef: payments-app-access  # References PolicyDocument
  tags:
    application: payments
    cost-center: platform
    owner: database-team
  syncedLabels:
    team: data-platform
    sensitivity: pci-dss
    criticality: p0
  syncedAnnotations:
    slack-channel: "#database-alerts"
    runbook: "https://wiki/payments-db-runbook"
```

**This creates a cluster with:**
- Governance enforced by `production` profile
- Deletion protection required
- Customer-managed KMS encryption
- Standardized access policy
- Comprehensive tagging and labeling
- All metadata synced to Kubernetes

## Example: Development Cluster

A development cluster with permissive settings:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: dev-test-db
  namespace: dev-sandbox
spec:
  configRef: dev
  deletionPolicy: delete              # Safer to delete test clusters
  # deletionProtectionEnabled omitted → dev profile defaults to false
  # kmsKeyArn omitted → AWS-owned key (no cost)
  tags:
    environment: dev
    team: engineering
```

## Status Fields

After creation, retrieve cluster identity and status:

```bash
kubectl describe dsqlcluster payments-prod-db -n payments-prod
```

Status fields available:

| Field | Type | Purpose |
|---|---|---|
| `status.identifier` | string | AWS-assigned cluster ID (26-char alphanumeric) — use this to connect |
| `status.endpoint` | string | Connection endpoint hostname (e.g., `abc123.dsql.us-east-1.on.aws`) |
| `status.arn` | string | Cluster ARN for cross-region references |
| `status.clusterStatus` | string | Lifecycle state (ACTIVE, CREATING, DELETING, UPDATING) |
| `status.creationTime` | string | Timestamp of cluster creation |
| `status.encryptionDetails.encryptionStatus` | string | ENABLED, ENABLING, KMS_KEY_INACCESSIBLE, UPDATING |
| `status.encryptionDetails.encryptionType` | string | AWS_OWNED_KMS_KEY or CUSTOMER_MANAGED_KMS_KEY |
| `status.encryptionDetails.kmsKeyARN` | string | ARN of the KMS key (if customer-managed) |
| `status.conditions` | array | Standard ACK conditions (synced, terminal) |

### Example: Getting the Connection Endpoint

```bash
# Get the cluster identifier
IDENTIFIER=$(kubectl get dsqlcluster payments-prod-db -n payments-prod -o jsonpath='{.status.identifier}')

# Get the endpoint
ENDPOINT=$(kubectl get dsqlcluster payments-prod-db -n payments-prod -o jsonpath='{.status.endpoint}')

# Connect from psql
psql -h "$ENDPOINT" -U postgres -d mydb
```

## Governance Cascade

When you don't specify a field, kropath resolves it using the governance cascade. Example:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: my-cluster
  namespace: production
spec:
  configRef: production
  # deletionProtectionEnabled omitted → cascade applies
  # kmsKeyArn omitted → cascade applies
```

**Cascade for `deletionProtectionEnabled`:**
1. Is it set in `KropathConfig.mandatory.dsql`? → Use that value (mandatory wins)
2. Is it set in the instance spec? → Use that value
3. Is it set in `production` DSQLConfig mandatory tier? → Use that value
4. Is it set in `KropathConfig.defaults.dsql`? → Use that value
5. Is it set in `production` DSQLConfig defaults tier? → Use that value
6. Otherwise → RGD built-in default: `true` (protection on)

**Cascade for `kmsEncryptionKey`:**
1. Is it set in `KropathConfig.mandatory.dsql`? → Use that value
2. Is it set via instance `kmsKeyRef` or `kmsKeyArn`? → Resolve and use that value
3. Is it set in `production` DSQLConfig mandatory tier? → Use that value
4. Is it set via instance `kmsKeyRef` or `kmsKeyArn`? → (already checked, skipped here)
5. Is it set in `KropathConfig.defaults.dsql`? → Use that value
6. Is it set in `production` DSQLConfig defaults tier? → Use that value
7. Otherwise → Omit the field; AWS creates cluster with AWS-owned KMS key

## Multiple Clusters in One Manifest

```yaml
---
# Production cluster
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: prod-db
  namespace: payments-prod
spec:
  configRef: production
  deletionProtectionEnabled: true
  kmsKeyRef: prod-encryption-key

---
# Staging cluster
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: staging-db
  namespace: payments-staging
spec:
  configRef: general-policy
  # deletionProtectionEnabled omitted → uses general-policy defaults (true)

---
# Development cluster
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: dev-db
  namespace: payments-dev
spec:
  configRef: dev
  deletionPolicy: delete
```

## Troubleshooting

**Cluster creation fails with "Invalid kmsKeyArn"**
- Verify the ARN syntax: `arn:aws:kms:region:account-id:key/key-id`
- Ensure the KMS key exists in the same AWS region as the cluster
- Check that the cluster's IAM role has permission to use the key

**"clusterPolicyRef not found"**
- Verify the `PolicyDocument` CR exists in the same namespace
- Check the CR name matches exactly in `spec.clusterPolicyRef`
- Ensure the `PolicyDocument` has a `metadata.labels.aws.kropath.run/resource-name` label

**Cluster stuck in CREATING state**
- Check cluster conditions: `kubectl describe dsqlcluster <name>`
- View ACK controller logs: `kubectl logs -n kro-system deployment/kro-aws-dsql-controller`
- AWS API issues are logged in the condition stack trace

**Encryption status shows KMS_KEY_INACCESSIBLE**
- The cluster has a KMS key ARN, but it cannot be accessed
- Check that the key exists and has not been disabled or scheduled for deletion
- Verify cluster IAM role has `kms:DescribeKey` and `kms:Decrypt` permissions

## Best Practices

1. **Use `retain` deletion policy** — Default; prevents accidental cluster deletion
2. **Reference governance profiles** — Let `DSQLConfig` enforce compliance
3. **Use customer-managed KMS keys for production** — Required for compliance (PCI-DSS, SOC 2)
4. **Use `KMSKey` references** — Better than direct ARNs; enables key portability
5. **Use `PolicyDocument` references** — Better than raw JSON; enables policy reuse
6. **Enable deletion protection for production** — Prevents accidental cluster deletion
7. **Tag appropriately** — Include team, cost-center, criticality metadata
8. **Set sync labels for production** — Kubernetes labels + AWS tags for observability
9. **Test multi-Region failover** — Validate that witness region and peer cluster ARNs are correct before production cutover

## Next Steps

- [DSQLConfig Governance Model](./dsqlconfig.md) — Understanding cascade and profiles
- [Aurora DSQL Family Overview](./index.md) — High-level concepts and quick start
