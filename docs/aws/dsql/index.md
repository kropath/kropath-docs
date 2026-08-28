# AWS Aurora DSQL — Distributed SQL Database

The AWS Aurora DSQL family within kropath provides abstractions for provisioning and managing Amazon Aurora DSQL clusters — a serverless, multi-Region, PostgreSQL-compatible relational database with active-active replication. It enables platform engineers to enforce organization-wide controls such as mandatory deletion protection, customer-managed KMS encryption, and resource-based IAM policies, while allowing application teams to provision clusters with custom access policies and multi-Region topology.

## Prerequisites and Setup

Aurora DSQL clusters are created independently, but the DSQL family integrates with other kropath families:

- **KMS Family:** For encrypting cluster data using customer-managed KMS keys via `DSQLCluster.spec.kmsKeyArn` or `spec.kmsKeyRef` references.
- **IAM Family:** For defining resource-based cluster access policies using the `PolicyDocument` CRD and `spec.clusterPolicyRef`.
- **KropathConfig:** For organization-wide deletion protection and KMS encryption governance via the `dsql` family section.

## Quick Start

To create a simple Aurora DSQL cluster:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: my-dsql-cluster
  namespace: production
spec:
  configRef: general-policy
  deletionProtectionEnabled: true
  tags:
    application: payments
    environment: production
  syncedLabels:
    team: platform
```

This creates:
1. A serverless Aurora DSQL cluster with automatic multi-AZ replication
2. Deletion protection enforced (preventing accidental cluster deletion)
3. Automatic tagging and labels from the `general-policy` governance profile
4. Cluster identity available via `status.identifier`

## Key Concepts

### DSQLCluster — Database Cluster Instances

A `DSQLCluster` resource represents a single Aurora DSQL cluster. Unlike traditional databases with explicit creation fields, Aurora DSQL clusters are identified by an auto-generated cluster identifier (26-char lowercase alphanumeric). Clusters define:

- **Deletion protection** (mandatory or defaults tier via governance)
- **KMS encryption** (AWS-owned, customer-managed ARN, or referenced `KMSKey` CR)
- **Resource-based IAM policies** (raw JSON or referenced `PolicyDocument` CR)
- **Cloud tags and Kubernetes labels** (merged with governance tags)
- **Multi-Region topology** (optional linked clusters in other regions)
- **Deletion behavior** (retain to keep AWS cluster when K8s resource is deleted)

### DSQLConfig — Governance Profiles

`DSQLConfig` CRs define per-profile governance settings for DSQL clusters. These profiles are referenced by `DSQLCluster` instances via `spec.configRef`. Each profile includes `mandatory` and `defaults` sections that control cluster security requirements across your organization.

**Example profiles:**
- `general-policy`: Conservative defaults (deletion protection on, AWS-owned key)
- `production`: Hardened for production (deletion protection mandatory, customer-managed KMS key required)
- `dev`: Permissive for development (deletion protection optional)

### Naming Exemption

Aurora DSQL has **no provider `name` field** — clusters are identified by an auto-generated `identifier` (26-char lowercase alphanumeric). The naming convention does not apply to this resource.

When you inspect cluster status, you will find:
- `status.identifier` — AWS-assigned cluster ID (e.g., `abcdefghijklmnopqrstuvwxyz`)
- `status.endpoint` — Connection endpoint hostname (e.g., `abc123.dsql.us-east-1.on.aws`)
- `status.arn` — Cluster ARN for cross-region or external references

### Governance Cascade

Kropath employs a ten-tier governance cascade (ADR-015 §5.3, ADR-010) to resolve effective configuration for DSQL clusters. This ensures organizational-level policies take precedence while providing flexibility for specific use cases.

The `kropath-controller` pre-merges all governance sources into `status.effectiveConfig` on the namespaced `DSQLConfig` CR. `DSQLCluster` RGDs read this configuration to determine the final, resolved settings.

**When to use `KropathConfig.dsql` vs. `DSQLConfig`:**
- **`KropathConfig.dsql`:** Org-wide governance (e.g., force all DSQL clusters to have deletion protection)
- **`DSQLConfig`:** Per-profile governance (e.g., restrict a `production` profile to use customer-managed KMS keys)

## Deletion Protection

Deletion protection prevents accidental cluster deletion. It can be enforced at three levels:

1. **Organizational level** (`KropathConfig.mandatory.dsql.deletionProtectionEnabled: true`): All profiles and clusters must have deletion protection
2. **Profile level** (`DSQLConfig/production.mandatory.deletionProtectionEnabled: true`): All clusters using this profile must have deletion protection
3. **Instance level** (`DSQLCluster.spec.deletionProtectionEnabled: true`): This cluster has deletion protection

When deletion protection is enabled, the AWS API prevents the cluster from being deleted until protection is explicitly disabled.

## Cluster Encryption

Aurora DSQL encryption options:

### AWS-Owned Key (Default)

When you do not specify a KMS key, AWS creates and manages the encryption key:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: aws-managed-encryption
  namespace: production
spec:
  # No kmsKeyArn, no kmsKeyRef → AWS-owned key
```

### Customer-Managed Key (Direct ARN)

Provide the KMS key ARN directly:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: customer-managed-key
  namespace: production
spec:
  kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
```

### Customer-Managed Key (KMSKey Reference)

Reference a managed `KMSKey` CR for portability:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: dsql-cluster
  namespace: production
spec:
  kmsKeyRef: my-cluster-key  # Must be a KMSKey CR in the same namespace
```

The RGD resolves the referenced `KMSKey` and extracts its ARN.

## Cluster Access Policies

Control who can connect to your cluster using resource-based IAM policies:

### Raw JSON Policy

Provide a complete policy document:

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
          "Effect": "Allow",
          "Principal": {"AWS": "arn:aws:iam::123456789012:role/application"},
          "Action": "dsql:DbConnectAdmin",
          "Resource": "*"
        }
      ]
    }
```

### PolicyDocument Reference

Reference a managed policy document for reuse:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: dsql-cluster
  namespace: production
spec:
  clusterPolicyRef: dsql-access-policy  # Must be a PolicyDocument CR in the same namespace
```

**Mutual exclusivity:** You cannot specify both `policy` and `clusterPolicyRef` — choose one approach per cluster.

## Multi-Region Topology

Aurora DSQL supports active-active replication across regions. To create a multi-Region cluster, specify linked peer clusters and a witness region:

```yaml
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
```

**Important:** Each region's cluster is represented as a separate `DSQLCluster` CR in your namespace. Multi-Region topology is specified via `spec.multiRegionProperties` on each CR; there is no composite multi-Region RGD.

## Cluster Deletion Behavior

When you delete a `DSQLCluster` resource, the behavior of the AWS DSQL cluster depends on the deletion policy:

- **`retain` (default):** The AWS DSQL cluster is preserved; only the Kubernetes resource is deleted. This is the safe default to prevent accidental cluster deletion.
- **`delete`:** The AWS DSQL cluster is deleted immediately.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: temporary-cluster
  namespace: test
spec:
  deletionPolicy: "delete"  # Unsafe; use only for test clusters
```

**Recommendation:** Use the default `retain` policy. Delete DSQL clusters manually through the AWS console if needed, and verify that no applications are still using the cluster.

## Cluster Identity and Connection

After creation, retrieve the cluster identifier and connection endpoint from status:

```bash
kubectl describe dsqlcluster my-dsql-cluster -n production
```

Look for:
- `status.identifier` — The AWS-assigned cluster ID (26 chars)
- `status.endpoint` — The connection hostname (use this to connect from applications)
- `status.arn` — The cluster ARN for cross-region or external references
- `status.clusterStatus` — Lifecycle state (ACTIVE, CREATING, DELETING, etc.)

Example connection string:
```
postgresql://user@my-cluster-id.dsql.us-east-1.on.aws/dbname?sslmode=require
```

## Tagging and Labeling

Control resource metadata through tags and labels:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: dsql-cluster
  namespace: production
spec:
  tags:
    application: payments
    cost-center: platform
  syncedLabels:
    team: platform
    sensitivity: high
  syncedAnnotations:
    runbook: "https://wiki/dsql-runbook"
```

- **`tags`:** AWS cloud tags; merged with governance mandatory and default tags
- **`syncedLabels`:** Kubernetes labels AND AWS tags (prefixed `aws.kropath.run/`)
- **`syncedAnnotations`:** Kubernetes annotations (prefixed `aws.kropath.run/`)

## Encryption Status Observability

After cluster creation, check encryption details in status for compliance auditing:

```bash
kubectl get dsqlcluster my-dsql-cluster -n production -o jsonpath='{.status.encryptionDetails}'
```

Output includes:
- `encryptionStatus` — ENABLED, ENABLING, KMS_KEY_INACCESSIBLE, or UPDATING
- `encryptionType` — AWS_OWNED_KMS_KEY or CUSTOMER_MANAGED_KMS_KEY
- `kmsKeyARN` — The KMS key ARN used for encryption (if customer-managed)

## Next Steps

For detailed guidance, see:
- [DSQLConfig Governance Model](./dsqlconfig.md) — Understanding mandatory vs. defaults tiers and profile management
- [DSQLCluster Usage Guide](./dsqlcluster.md) — Field reference and configuration options
- [Cross-Family Integration](../kms/cross-family-integration.md) — How to reference KMS keys and Policy Documents in DSQL clusters

## Out-of-Scope (Phase 2+)

The following DSQL features are not yet supported and are deferred to later phases:
- Composite multi-Region topology RGD (each region's cluster is a separate `DSQLCluster` CR in P0)
- Policy field JSON admission validation
