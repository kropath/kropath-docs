# AWS DocumentDB

The AWS DocumentDB family within kropath provides abstractions for managing Amazon DocumentDB (MongoDB-compatible) database clusters, instances, and network infrastructure. It enables platform engineers to enforce organization-wide controls such as encryption, deletion protection, backup retention, and logging, while allowing application teams to provision and configure DocumentDB clusters with flexible sizing, serverless v2 scaling, and high-availability configurations.

## Prerequisites and Setup

DocumentDB clusters can be deployed standalone or integrated with other kropath families for advanced functionality:

*   **VPC and Networking:** DocumentDB clusters require VPC subnet placement via `DocumentDBSubnetGroup` resources. Subnets must span at least two Availability Zones for high availability.
*   **KMS Family:** For encrypting DocumentDB data at rest and Performance Insights data, specify KMS key ARNs via the governance cascade.
*   **Secrets Manager:** Master user passwords can be managed either as explicit Kubernetes Secrets or via AWS Secrets Manager (mutually exclusive).

## Configuration

Kropath's DocumentDB configuration is managed through three primary resource kinds plus one governance resource: instances of `DocumentDBCluster`, `DocumentDBInstance`, and `DocumentDBSubnetGroup` resource kinds (which come from kro RGDs) for defining individual DocumentDB infrastructure, and `DocumentDBConfig` custom resource instances for establishing organization-wide or profile-specific governance policies. These resources leverage a robust ten-tier governance cascade to ensure compliance while providing flexibility.

### DocumentDBConfig Governance Model

`DocumentDBConfig` CRs define per-profile governance settings for DocumentDB resources. These profiles are referenced by resource instances via `spec.configRef`. Each `DocumentDBConfig` includes `mandatory` and `defaults` sections for governance fields:

*   **`mandatory`:** Fields set in this section enforce strict policies that cannot be overridden by instance specs. If a `mandatory` field is set, the instance's corresponding field (if present) is validated against or replaced by the mandatory setting.
*   **`defaults`:** Fields set here provide baseline configurations that instances can override. They apply only when the instance's corresponding field is not explicitly set.

**Example Profiles:**

*   `general-policy`: A conservative baseline profile with sensible defaults (e.g., `defaults.storageEncrypted: true`, `defaults.backupRetentionPeriod: 7`, `defaults.enableCloudwatchLogsExports: ["audit"]`).
*   `production`: A hardened compliance profile enforcing strong encryption, high backup retention, and audit logging (e.g., `mandatory.storageEncrypted: true`, `mandatory.backupRetentionPeriod: 14`, `mandatory.enableCloudwatchLogsExports: ["audit", "profiler"]`).
*   `development`: A more permissive profile with lower backup retention and optional encryption (e.g., `defaults.backupRetentionPeriod: 1`, `defaults.storageEncrypted: false`).

### Ten-tier Governance Cascade

Kropath employs a ten-tier governance cascade (ADR-010, ADR-015 §5.3) to resolve effective configuration for DocumentDB resources. This cascade ensures that organizational-level policies take precedence, followed by profile-specific settings, and finally instance-level overrides.

The `kropath-controller` pre-merges all governance sources (from `KropathConfig` and `DocumentDBConfig`) into `status.effectiveConfig` on the namespaced `DocumentDBConfig` CR. DocumentDB RGDs read this `status.effectiveConfig` to determine the final, resolved settings.

**When to use `KropathConfig.documentdb` vs. `DocumentDBConfig`:**

*   **`KropathConfig.documentdb`:** Used for blanket, organization-wide governance that applies across all DocumentDB profiles. For example, setting `KropathConfig.mandatory.documentdb.storageEncrypted: true` would force all DocumentDB clusters in the organization to use encryption at rest, regardless of the `DocumentDBConfig` profile they use.
*   **`DocumentDBConfig`:** Used for per-profile governance. For instance, a `pci` `DocumentDBConfig` profile might mandate encryption with a specific KMS key and deletion protection for clusters using that profile, allowing other profiles more flexibility.

## DocumentDBCluster

### What is a DocumentDBCluster?

A `DocumentDBCluster` represents a MongoDB-compatible document database cluster. It is the primary resource in the DocumentDB family and handles cluster-level configuration such as engine version, encryption, networking, backup policy, and master user credentials. Each cluster can contain multiple `DocumentDBInstance` resources that provide compute capacity.

### Core Fields

An `DocumentDBCluster` instance represents the desired state of a DocumentDB cluster. Here are its core configuration fields:

*   `configRef` (string, default: `"general-policy"`): Specifies which `DocumentDBConfig` profile to use for governance. If the named profile does not exist, it falls back to `"general-policy"`.
*   `nameOverride` (string): Allows overriding the cluster name derived from the naming template.
*   `deletionPolicy` (string, default: `"retain"`): Determines the behavior upon deletion of the `DocumentDBCluster` CR. Options are `"retain"` (AWS DocumentDB cluster is preserved) or `"delete"` (AWS DocumentDB cluster is deleted).

#### Security and Encryption

*   `storageEncrypted` (boolean, nullable): Encrypt data at rest. When `nil` (not set), the governance cascade applies. When `true`, encryption is enabled (immutable after creation). This field follows the `DocumentDBConfig` cascade; mandatory settings cannot be overridden.
*   `kmsKeyArn` (string): The ARN of the AWS KMS key to use for at-rest encryption. When empty, AWS-owned keys are used. This field is immutable after cluster creation and follows the cascade.
*   `deletionProtection` (boolean, nullable): When `true`, the cluster cannot be accidentally deleted. Follows the cascade for mandatory/default enforcement.

#### Engine and Compute

*   `engineVersion` (string): DocumentDB engine version (e.g., `"5.0.0"`). When empty, DocumentDB uses its latest major version. Follows the cascade for governance.
*   `dbClusterParameterGroupName` (string): Optional cluster parameter group name. When empty, DocumentDB uses the default parameter group.

#### Master User Credentials

*   `masterUsername` (string, required on create): The master user name for cluster access.
*   `masterUserPassword` (object, SecretKeyReference): Reference to a Kubernetes Secret containing the master password. Requires both `key` (the secret key) and `name`/`namespace` (the Secret location). Mutually exclusive with `manageMasterUserPassword`.
*   `manageMasterUserPassword` (boolean, nullable): When `true`, AWS Secrets Manager manages the master password automatically. Mutually exclusive with `masterUserPassword`.
*   `masterUserSecretKmsKeyArn` (string): Optional KMS key ARN to encrypt the Secrets Manager secret created by `manageMasterUserPassword`.

#### Networking

*   `subnetGroupName` (string): The name of the `DocumentDBSubnetGroup` for VPC subnet placement. When empty, DocumentDB uses the default subnet group.
*   `securityGroupIDs` (array of strings): VPC security group IDs for cluster access control.
*   `networkType` (string): Network type, either `"IPV4"` or `"DUAL"`. When empty, defaults to `"IPV4"`.
*   `port` (integer, nullable): Port for cluster connections. When `nil`, DocumentDB defaults to `27017`.

#### Storage and Backups

*   `storageType` (string): Storage type, either `"standard"` or `"iopt1"` (optimized I/O). When empty, uses `"standard"`. Note: changing from `"iopt1"` to `"standard"` is not supported; this choice is effectively immutable.
*   `backupRetentionPeriod` (integer, nullable): Number of days to retain automated backups (1–35). When `nil`, DocumentDB defaults to 1 day. Follows the cascade; mandatory settings enforce a minimum retention.
*   `preferredBackupWindow` (string): Daily UTC time range for automated backups (e.g., `"04:00-05:00"`).
*   `preferredMaintenanceWindow` (string): Weekly maintenance window (e.g., `"sun:05:00-sun:06:00"`).

#### Logging and Monitoring

*   `enableCloudwatchLogsExports` (array of strings): Log types to export to CloudWatch Logs. Valid values: `"audit"` (cluster activity) and `"profiler"` (slow query and profiling data). Follows the cascade.

#### Serverless v2 Scaling

*   `serverlessV2ScalingConfiguration` (optional object): Enables serverless v2 auto-scaling. Contains:
    *   `minCapacity` (float): Minimum ACU capacity (e.g., `0.5`).
    *   `maxCapacity` (float): Maximum ACU capacity (e.g., `16.0`).

When not set, the cluster uses provisioned instance types only.

#### Metadata and Tags

*   `tags` (map<string,string>): Custom AWS tags applied to the cluster. These are merged with mandatory and default tags from `KropathConfig` and `DocumentDBConfig`.
*   `syncedLabels` (map<string,string>): Kubernetes labels that are mirrored as AWS tags and prefixed with `aws.kropath.run/`.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations that are mirrored to AWS resource tags and prefixed with `aws.kropath.run/`.

### Status Outputs

*   `status.resourceName` (string): The effective cluster name after naming template resolution and `.lowerAscii()` post-processing.
*   `status.namingStatus` (string): `"valid"` or `"invalid-unresolved-tokens"` — indicates naming template validity.
*   `status.predictedArn` (string): The predicted ARN of the cluster: `"arn:aws:rds:<region>:<accountId>:cluster:<resourceName>"`.
*   `status.clusterEndpoint` (string): Primary endpoint address for the cluster.
*   `status.readerEndpoint` (string): Load-balanced reader endpoint for read-only connections.
*   `status.clusterStatus` (string): Lifecycle state (e.g., `creating`, `available`, `updating`, `deleting`).

### Example DocumentDBCluster CR

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DocumentDBCluster
metadata:
  name: orders-db
  namespace: data-prod
spec:
  configRef: production
  nameOverride: ""  # Use default naming template
  deletionPolicy: retain

  # Engine and encryption
  engineVersion: "5.0.0"
  storageEncrypted: true
  kmsKeyArn: "arn:aws:kms:ap-southeast-2:123456789012:key/12345678-1234-1234-1234-123456789012"
  deletionProtection: true

  # Compute
  dbClusterParameterGroupName: "default.docdb5.0"

  # Master user credentials
  masterUsername: "docdbadmin"
  masterUserPassword:
    name: docdb-credentials
    key: password
    namespace: data-prod

  # Networking
  subnetGroupName: docdb-prod-subnets
  securityGroupIDs:
    - sg-12345678
    - sg-87654321
  networkType: "DUAL"
  port: 27017

  # Storage and backups
  storageType: standard
  backupRetentionPeriod: 14
  preferredBackupWindow: "04:00-05:00"
  preferredMaintenanceWindow: "sun:05:00-sun:06:00"

  # Logging
  enableCloudwatchLogsExports:
    - audit
    - profiler

  # Serverless v2 scaling (optional)
  serverlessV2ScalingConfiguration:
    minCapacity: 1.0
    maxCapacity: 16.0

  # Tags and labels
  tags:
    application: orders
    cost-center: engineering
  syncedLabels:
    environment: production
    data-classification: internal
```

## DocumentDBInstance

### What is a DocumentDBInstance?

A `DocumentDBInstance` represents an individual database instance within a DocumentDB cluster. Instances provide the compute capacity for the cluster. Multiple instances within a cluster provide high availability via automatic failover, with the instance having the lowest promotion tier becoming the new primary if the current primary fails.

### Core Fields

A `DocumentDBInstance` instance represents the desired state of a database instance. Here are its core configuration fields:

*   `configRef` (string, default: `"general-policy"`): Specifies which `DocumentDBConfig` profile to use for governance.
*   `nameOverride` (string): Allows overriding the instance name derived from the naming template.
*   `deletionPolicy` (string, default: `"retain"`): Determines the behavior upon deletion of the `DocumentDBInstance` CR.

#### Cluster Membership and Sizing

*   `dbClusterIdentifier` (string, required): The identifier of the cluster this instance belongs to. Must match a `DocumentDBCluster` resource's `status.resourceName`.
*   `dbInstanceClass` (string, required): The instance class (e.g., `"db.r6g.large"`, `"db.t3.medium"`). Provides compute and memory capacity. Follows the governance cascade.

#### Failover and Monitoring

*   `promotionTier` (integer, nullable): Failover priority (0–15). Lower values are promoted first when the primary fails. When `nil`, DocumentDB defaults to `1`.
*   `performanceInsightsEnabled` (boolean, nullable): When `true`, enables Performance Insights for database monitoring. Follows the cascade.
*   `performanceInsightsKmsKeyArn` (string): Optional KMS key ARN to encrypt Performance Insights data. When empty, uses AWS-owned keys.

#### Engine and Certificates

*   `caCertificateIdentifier` (string): Optional CA certificate identifier for the server certificate (e.g., `"rds-ca-rsa2048-g1"`).

#### Maintenance and Snapshots

*   `preferredMaintenanceWindow` (string): Weekly maintenance window (e.g., `"sun:05:00-sun:06:00"`).
*   `copyTagsToSnapshot` (boolean, nullable): When `true`, tags from the instance are copied to automated snapshots.

#### Metadata and Tags

*   `tags` (map<string,string>): Custom AWS tags applied to the instance.
*   `syncedLabels` (map<string,string>): Kubernetes labels mirrored as AWS tags.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations mirrored to AWS tags.

### Status Outputs

*   `status.resourceName` (string): The effective instance name after naming template resolution.
*   `status.namingStatus` (string): `"valid"` or `"invalid-unresolved-tokens"`.
*   `status.predictedArn` (string): The predicted ARN: `"arn:aws:rds:<region>:<accountId>:db:<resourceName>"`.
*   `status.instanceEndpoint` (string): Instance endpoint address.
*   `status.instancePort` (integer): Instance endpoint port.
*   `status.instanceStatus` (string): Lifecycle state (e.g., `creating`, `available`, `modifying`, `deleting`).

### Example DocumentDBInstance CR

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DocumentDBInstance
metadata:
  name: orders-reader-1
  namespace: data-prod
spec:
  configRef: production
  nameOverride: ""
  deletionPolicy: retain

  # Cluster membership and sizing
  dbClusterIdentifier: orders-db  # Matches DocumentDBCluster.status.resourceName
  dbInstanceClass: db.r6g.large

  # Failover and monitoring
  promotionTier: 1
  performanceInsightsEnabled: true
  performanceInsightsKmsKeyArn: "arn:aws:kms:ap-southeast-2:123456789012:key/87654321-4321-4321-4321-210987654321"

  # Engine
  caCertificateIdentifier: "rds-ca-rsa2048-g1"

  # Maintenance
  preferredMaintenanceWindow: "sun:05:00-sun:06:00"
  copyTagsToSnapshot: true

  # Tags
  tags:
    application: orders
    role: reader
  syncedLabels:
    instance-type: read-replica
```

## DocumentDBSubnetGroup

### What is a DocumentDBSubnetGroup?

A `DocumentDBSubnetGroup` represents a named collection of VPC subnets that designate the network placement for DocumentDB cluster instances. Subnet groups are independently useful and commonly shared across multiple DocumentDB clusters, so they are managed as standalone resources referenced by cluster specifications. DocumentDB requires at least two subnets in different Availability Zones within a subnet group.

### Core Fields

A `DocumentDBSubnetGroup` instance represents the desired state of a subnet group. Here are its core configuration fields:

*   `configRef` (string, default: `"general-policy"`): Specifies which `DocumentDBConfig` profile to use for governance.
*   `nameOverride` (string): Allows overriding the subnet group name derived from the naming template.
*   `deletionPolicy` (string, default: `"retain"`): Determines the behavior upon deletion of the `DocumentDBSubnetGroup` CR.
*   `description` (string, required): Human-readable description of the subnet group's purpose.
*   `subnetIDs` (array of strings): VPC subnet IDs to include in the group. DocumentDB requires at least two subnets in different Availability Zones.

#### Metadata and Tags

*   `tags` (map<string,string>): Custom AWS tags applied to the subnet group.
*   `syncedLabels` (map<string,string>): Kubernetes labels mirrored as AWS tags.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations mirrored to AWS tags.

### Status Outputs

*   `status.resourceName` (string): The effective subnet group name after naming template resolution.
*   `status.namingStatus` (string): `"valid"` or `"invalid-unresolved-tokens"`.
*   `status.predictedArn` (string): The predicted ARN: `"arn:aws:rds:<region>:<accountId>:subgrp:<resourceName>"`.
*   `status.subnetGroupStatus` (string): Subnet group status (e.g., `"Complete"`).

### Example DocumentDBSubnetGroup CR

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DocumentDBSubnetGroup
metadata:
  name: docdb-prod-subnets
  namespace: data-prod
spec:
  configRef: general-policy
  nameOverride: ""
  deletionPolicy: retain

  description: "DocumentDB subnets for production cluster"
  subnetIDs:
    - subnet-12345678  # AZ: ap-southeast-2a
    - subnet-87654321  # AZ: ap-southeast-2b
    - subnet-aabbccdd  # AZ: ap-southeast-2c (optional, for extra HA)

  # Tags
  tags:
    network-purpose: database
  syncedLabels:
    environment: production
```

## Naming Conventions

DocumentDB resource names (cluster identifiers, instance identifiers, subnet group names) must conform to AWS constraints:

*   **Cluster identifiers:** 1–63 characters; must begin with a letter; alphanumeric and hyphens only; cannot end with a hyphen; no consecutive hyphens. Case-insensitive but stored lowercase.
*   **Instance identifiers:** 1–63 characters; must begin with a letter; alphanumeric and hyphens only. Case-insensitive but stored lowercase.
*   **Subnet group names:** Alphanumeric and hyphens; must begin with a letter. Case-insensitive but stored lowercase.

Kropath's default naming template for all DocumentDB resources is `{namespace}-{name}`. The `effectiveName` (the final cloud resource name) is derived from this template, with `spec.nameOverride` providing an escape hatch to bypass the template. The RGD automatically applies `.lowerAscii()` to the generated name to ensure compliance with AWS's lowercase storage requirement.

### Dynamic Tag Fields in Naming Templates

Naming templates support `{tag.fieldName}` placeholders that allow you to embed tag values directly into resource names. For example, a template like `{tag.environment}-{name}` would derive the resource name from a tag defined in `spec.tags`, `spec.syncedLabels`, or `spec.syncedAnnotations`, combined with the CR name.

Tag values are resolved in a cascading order: mandatory tags from governance config, then instance-level tags, then default tags. If a referenced tag does not exist, the naming template validation reports `status.namingStatus: invalid-unresolved-tokens`.

## ARN Format

DocumentDB resources use the `rds` ARN service namespace (not `documentdb`), following AWS's architectural decision to build DocumentDB on top of RDS infrastructure:

*   **Cluster ARN:** `arn:aws:rds:<region>:<accountId>:cluster:<resourceName>`
*   **Instance ARN:** `arn:aws:rds:<region>:<accountId>:db:<resourceName>`
*   **Subnet group ARN:** `arn:aws:rds:<region>:<accountId>:subgrp:<resourceName>`

All resource identifiers are case-insensitive and stored lowercase by AWS.

## Governance Cascade Details

The governance cascade for DocumentDB follows the standard kropath pattern (ADR-010, ADR-015 §5.3):

| Field | Mandatory Semantics | Defaults Semantics |
|---|---|---|
| `storageEncrypted` | Forces encryption on all clusters; instance cannot disable | Applies when instance field is not set |
| `deletionProtection` | Forces deletion protection on all resources; cannot be disabled | Applies when instance field is not set |
| `kmsKeyArn` | Forces specific KMS key; instance cannot use a different key | Applies when instance field is empty |
| `performanceInsightsEnabled` | Forces Performance Insights on all instances | Applies when instance field is not set |
| `dbInstanceClass` | Forces specific instance class; instance cannot override | Applies when instance field is empty |
| `engineVersion` | Forces specific engine version; cannot be overridden | Applies when instance field is empty |
| `allowedInstanceClasses` | Restricts instance classes to an allowlist | Baseline allowlist; overridable per-instance |
| `storageType` | Forces specific storage type; immutable after creation | Applies when instance field is empty |
| `backupRetentionPeriod` | Forces minimum retention; instance cannot go below this value | Applies when instance field is not set |
| `enableCloudwatchLogsExports` | Forces specific log exports; instance cannot remove | Applies when instance field is empty |
| `tags` / `syncedLabels` / `syncedAnnotations` | Merged into all resources; cannot be removed | Baseline metadata; overridable per-instance |
| `namingTemplate` | Forces naming pattern; `spec.nameOverride` is the only escape hatch | Applies when instance field is empty |

## Immutable Fields

The following fields are immutable after resource creation and cannot be changed:

*   `storageEncrypted` — encryption at rest cannot be changed after cluster creation
*   `kmsKeyArn` — KMS key cannot be changed after cluster creation
*   `storageType: "iopt1"` — optimized I/O storage cannot be reverted to standard storage

Changes to these fields on an existing resource require deleting and recreating the cluster.

## Master User Credential Management

DocumentDB clusters support two mutually exclusive credential management approaches:

1. **Explicit password:** Specify `masterUserPassword` referencing a Kubernetes Secret containing the password. The secret is stored in Kubernetes and not modified by kropath.
2. **AWS Secrets Manager:** Specify `manageMasterUserPassword: true` to have AWS Secrets Manager manage the password automatically. Optionally set `masterUserSecretKmsKeyArn` to encrypt the secret with a specific KMS key.

Choose based on your security and operational requirements:

*   **Explicit password:** Best for cases where you want full control and auditability within your Kubernetes cluster.
*   **AWS Secrets Manager:** Best for automatic password rotation and cloud-native secret management.

## High Availability and Failover

DocumentDB provides high availability through multi-instance clusters:

*   Each cluster contains one primary writer instance and zero or more secondary reader instances.
*   When the primary fails, the secondary with the lowest `promotionTier` is automatically promoted to primary.
*   Promotion tiers range from 0 (highest priority) to 15 (lowest priority).
*   All cluster data and configuration are shared across instances — each instance is a full replica.

## Related Resources

*   **DocumentDB family design:** See `docs/families/aws/documentdb.md` in kropath-core for the complete governance model, cascade tables, and architectural decisions.
*   **DocumentDB specifications:** Detailed resource specifications in kropath-core `docs/specs/aws/aws-docdb-*.md` files define all acceptance criteria and field mappings.

