# DynamoDBConfig — Governance Configuration

The `DynamoDBConfig` resource defines governance profiles that control how DynamoDB tables are created and managed across your organization and namespaces. Platform teams create named profiles; developers select the profile they need via `spec.configRef` on each table.

## Overview

`DynamoDBConfig` establishes two tiers of governance:

- **Mandatory tier** — Controls that cannot be overridden by developers (e.g., encryption keys that all tables must use, required deletion protection for production)
- **Defaults tier** — Baseline values developers can override (e.g., default encryption, default naming pattern, default billing mode)

This two-tier approach lets platform teams enforce critical compliance and security controls while preserving developer flexibility for non-critical fields.

## Configuration Fields

### Mandatory Tier

Mandatory values **always apply** and override developer choices:

| Field | Type | Purpose |
|---|---|---|
| `encryptionEnabled` | boolean | When `true`, forces customer-managed KMS encryption on all tables. `false` = not enforced. |
| `kmsMasterKeyId` | string | Mandatory KMS key ARN or alias for customer-managed encryption. Empty string = not enforced. |
| `deletionProtectionEnabled` | boolean | When `true`, forces deletion protection on all tables. `false` = not enforced. |
| `pointInTimeRecoveryEnabled` | boolean | When `true`, forces point-in-time recovery on all tables. `false` = not enforced. |
| `billingMode` | string | Mandatory billing mode (`PROVISIONED` or `PAY_PER_REQUEST`). Empty string = not enforced. |
| `tableClass` | string | Mandatory table class (`STANDARD` or `STANDARD_INFREQUENT_ACCESS`). Empty string = not enforced. |
| `contributorInsights` | string | Mandatory Contributor Insights setting (`ENABLE` or `DISABLE`). Empty string = not enforced. |
| `namingTemplate` | string | Naming pattern for table names (e.g. `{namespace}-{name}`). Empty string = no mandatory template. |
| `tags` | map | Cloud tags applied to all tables. Cannot be removed by developers. |
| `syncedLabels` | map | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`). Merged with developer labels. |
| `syncedAnnotations` | map | Kubernetes annotations (prefixed `aws.kropath.run/`). Merged with developer annotations. |

### Defaults Tier

Default values apply only when **not specified** at the table level:

| Field | Type | Purpose |
|---|---|---|
| `encryptionEnabled` | boolean | Default encryption setting when table doesn't specify one. `false` = use DynamoDB-owned encryption by default. |
| `kmsMasterKeyId` | string | Default KMS key when table doesn't specify one. Empty string = use DynamoDB-owned or AWS-managed key. |
| `deletionProtectionEnabled` | boolean | Default deletion protection. `false` = no protection by default. |
| `pointInTimeRecoveryEnabled` | boolean | Default PITR setting. `false` = no PITR by default. |
| `billingMode` | string | Default billing mode when table doesn't specify one. Empty string defaults to on-demand billing. |
| `tableClass` | string | Default table class when table doesn't specify one. Empty string defaults to STANDARD. |
| `contributorInsights` | string | Default Contributor Insights setting. Empty string defaults to DISABLE. |
| `namingTemplate` | string | Default naming pattern (e.g. `{namespace}-{name}`). Applied when table doesn't use `spec.nameOverride`. |
| `tags` | map | Default cloud tags for tables. Can be overridden per-table. |
| `syncedLabels` | map | Default labels to sync to Kubernetes and cloud tags. |
| `syncedAnnotations` | map | Default annotations to sync to Kubernetes. |

**Key rule:** A field cannot be set in both mandatory and defaults tiers simultaneously. (Empty values like `{}`, `[]`, or `""` can appear in both — they indicate "not set".)

## Example Profiles

### Baseline (general-policy)

Permissive defaults; no mandatory enforcement. Suitable for development and general use:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DynamoDBConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    encryptionEnabled: false
    kmsMasterKeyId: ""
    deletionProtectionEnabled: false
    pointInTimeRecoveryEnabled: false
    billingMode: ""
    tableClass: ""
    contributorInsights: ""
    namingTemplate: ""
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    encryptionEnabled: false
    kmsMasterKeyId: ""
    deletionProtectionEnabled: false
    pointInTimeRecoveryEnabled: false
    billingMode: ""  # Defaults to on-demand
    tableClass: ""   # Defaults to STANDARD
    contributorInsights: ""  # Defaults to DISABLE
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

### Production (production)

Enforces deletion protection and point-in-time recovery for production tables:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DynamoDBConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  mandatory:
    encryptionEnabled: false
    kmsMasterKeyId: ""
    deletionProtectionEnabled: true
    pointInTimeRecoveryEnabled: true
    billingMode: ""
    tableClass: ""
    contributorInsights: ""
    namingTemplate: ""
    tags:
      environment: production
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    encryptionEnabled: false
    kmsMasterKeyId: ""
    deletionProtectionEnabled: false
    pointInTimeRecoveryEnabled: false
    billingMode: ""
    tableClass: ""
    contributorInsights: ""
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

Developers using the `production` profile cannot override:
- Deletion protection (mandatory for all production tables)
- Point-in-time recovery (mandatory for all production tables)
- Environment tag (production tables always tagged as such)

### PCI Compliance (pci)

Enforces encryption with a customer-managed key and mandatory PITR for compliance:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DynamoDBConfig
metadata:
  name: pci
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: pci
spec:
  mandatory:
    encryptionEnabled: true
    kmsMasterKeyId: "arn:aws:kms:us-east-1:123456789012:key/pci-table-key"
    deletionProtectionEnabled: true
    pointInTimeRecoveryEnabled: true
    billingMode: ""
    tableClass: ""
    contributorInsights: ""
    namingTemplate: ""
    tags:
      compliance: pci
      data-classification: restricted
    syncedLabels:
      compliance: pci
    syncedAnnotations: {}
  defaults:
    encryptionEnabled: false
    kmsMasterKeyId: ""
    deletionProtectionEnabled: false
    pointInTimeRecoveryEnabled: false
    billingMode: ""
    tableClass: ""
    contributorInsights: ""
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

## How to Deploy

1. Create the profile CRs in `kro-system` namespace (reserved for system-wide configuration):

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: DynamoDBConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    encryptionEnabled: false
    kmsMasterKeyId: ""
    deletionProtectionEnabled: false
    pointInTimeRecoveryEnabled: false
    billingMode: ""
    tableClass: ""
    contributorInsights: ""
    namingTemplate: ""
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    encryptionEnabled: false
    kmsMasterKeyId: ""
    deletionProtectionEnabled: false
    pointInTimeRecoveryEnabled: false
    billingMode: ""
    tableClass: ""
    contributorInsights: ""
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
EOF
```

2. Developers create tables that reference the profile:

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: DynamoDBTable
metadata:
  name: user-orders
  namespace: app-team
spec:
  configRef: general-policy  # Selects the profile
  keySchema:
    - attributeName: userId
      keyType: HASH
  attributeDefinitions:
    - attributeName: userId
      attributeType: S
EOF
```

## Effective Configuration

When a table is created, kropath-controller reads the selected `DynamoDBConfig` and merges mandatory and defaults tiers along with org-wide settings from `KropathConfig`. The final merged configuration is written to `status.effectiveConfig` on the config CR.

Developers and platform teams can inspect the effective configuration:

```bash
kubectl get dynamodbconfig general-policy -n kro-system -o yaml
```

The `status.effectiveConfig` shows:
- All mandatory fields (platform enforcement)
- All default fields (developer overrides possible)
- AWS account and region information

This single config CR ensures consistent, auditable governance across all tables that reference it.

## Naming Convention

Tables are named using a configurable template. The default template is `{namespace}-{name}`, which produces resource names like `app-team-user-orders` (where `app-team` is the Kubernetes namespace and `user-orders` is the resource name).

**Available naming tokens:**
- `{name}` — The resource's Kubernetes name
- `{namespace}` — The resource's Kubernetes namespace
- `{account_id}` — AWS account ID (from governance)
- `{region}` — AWS region (from governance)
- `{tag.KEY}` — Any tag key from the merged tags (e.g. `{tag.environment}`)

Example: A profile with `namingTemplate: "{namespace}-{tag.environment}-{name}"` would produce names like `app-team-prod-user-orders`.

**Important:** The table name is immutable after creation in AWS. Changing `spec.nameOverride` or the governance naming template on an existing table does not rename the AWS table — it remains registered under its original name.
