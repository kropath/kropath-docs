# SSMResourceDataSync — Inventory Data Synchronization

The `SSMResourceDataSync` resource configures AWS Systems Manager Inventory data aggregation. It enables centralized inventory reporting across your fleet—either syncing to S3 buckets for long-term storage or synchronizing across AWS Organizations for multi-account visibility.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SSMConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the sync name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` (safe) or `"delete"` |

### Sync Type

| Field | Type | Default | Purpose |
|---|---|---|---|
| `syncType` | string | `"SyncToDestination"` | Type: SyncToDestination (S3) or SyncFromSource (Organizations) |

### S3 Destination (Required for SyncToDestination)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `s3Destination` | object | `nil` | S3 bucket configuration: bucketName, prefix, region, syncFormat, awsKMSKeyARN, destinationDataSharing |
| `s3Destination.bucketName` | string | (required) | S3 bucket name for inventory data |
| `s3Destination.prefix` | string | `""` | Prefix for objects in bucket |
| `s3Destination.region` | string | (required) | AWS region of the S3 bucket |
| `s3Destination.syncFormat` | string | `"JsonCompressed"` | Format: JsonCompressed or Other |
| `s3Destination.awsKMSKeyARN` | string | `""` | KMS key for encrypting sync data in S3 |
| `s3Destination.destinationDataSharing` | object | `{}` | Data sharing configuration |

### Sync Source (Required for SyncFromSource)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `syncSource` | object | `nil` | Source configuration for cross-account/region sync |
| `syncSource.sourceType` | string | (required) | Source: SingleAccountMultiRegions or AwsOrganizations |
| `syncSource.sourceRegions` | []string | (required) | List of AWS regions to sync from |
| `syncSource.includeFutureRegions` | boolean | `false` | Auto-include new regions |
| `syncSource.enableAllOpsDataSources` | boolean | `false` | Sync all operational data source types |
| `syncSource.awsOrganizationsSource` | object | `{}` | AWS Organizations settings (organizationSourceType, organizationalUnits) |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels synchronized to AWS tags |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations synchronized to AWS tags |

## Sync Types

### SyncToDestination: S3 Aggregation

Sync inventory data to S3 for long-term storage and analysis:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMResourceDataSync
metadata:
  name: inventory-to-s3
  namespace: ops
spec:
  syncType: SyncToDestination
  s3Destination:
    bucketName: "my-inventory-bucket"
    prefix: "ssm-inventory/"
    region: "us-east-1"
    syncFormat: "JsonCompressed"
    awsKMSKeyARN: "arn:aws:kms:us-east-1:123456789012:key/12345678-..."
  tags:
    Purpose: InventorySync
    Team: Operations
```

Result:
- Inventory data synced to S3 in compressed JSON format
- Data encrypted with specified KMS key
- Stored in `s3://my-inventory-bucket/ssm-inventory/`

**Use case:** Centralized reporting, long-term data retention, compliance audits

### SyncFromSource: Cross-Account Sync

Sync inventory across multiple accounts/regions using AWS Organizations:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMResourceDataSync
metadata:
  name: org-inventory-sync
  namespace: ops
spec:
  syncType: SyncFromSource
  syncSource:
    sourceType: AwsOrganizations
    sourceRegions:
      - us-east-1
      - us-west-2
      - eu-west-1
    includeFutureRegions: true
    enableAllOpsDataSources: true
    awsOrganizationsSource:
      organizationSourceType: "EntireOrganization"
      # OR: organizationalUnits: ["ou-abcd-12345678", "ou-efgh-87654321"]
  tags:
    Purpose: OrgInventory
    Scope: Cross-Account
```

Result:
- Syncs inventory from all accounts in organization
- Covers us-east-1, us-west-2, eu-west-1
- Auto-includes new regions as they're added to organization
- All operational data sources enabled

**Use case:** Multi-account visibility, organization-wide compliance, security monitoring

## Complete Examples

### Example 1: S3-Based Inventory (Single Account)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMResourceDataSync
metadata:
  name: fleet-inventory-sync
  namespace: ops
spec:
  configRef: general-policy
  deletionPolicy: retain
  syncType: SyncToDestination
  s3Destination:
    bucketName: "fleet-inventory-prod"
    prefix: "ssm-inventory/"
    region: "us-east-1"
    syncFormat: "JsonCompressed"
    awsKMSKeyARN: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
    destinationDataSharing:
      destinationDataSharingType: "CrossAccountDataSharing"
  tags:
    Environment: Production
    Purpose: FleetInventory
    Team: Operations
```

Result:
- Inventory synced to S3 in compressed JSON
- KMS encryption for at-rest security
- Data available for cross-account sharing
- Retention: AWS default (S3 bucket lifecycle policies apply)

### Example 2: Multi-Account Sync via Organizations

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMResourceDataSync
metadata:
  name: organization-wide-sync
  namespace: ops
spec:
  configRef: general-policy
  syncType: SyncFromSource
  syncSource:
    sourceType: AwsOrganizations
    sourceRegions:
      - us-east-1
      - us-west-2
      - eu-west-1
      - ap-southeast-1
    includeFutureRegions: true
    enableAllOpsDataSources: true
    awsOrganizationsSource:
      organizationSourceType: "EntireOrganization"
  tags:
    Scope: OrganizationWide
    Compliance: Required
    Purpose: CentralInventory
```

Result:
- Syncs inventory from **all accounts** in the organization
- Covers 4 specified regions + any future regions
- All data sources included (applications, packages, network config, etc.)
- Centralized Explorer view available
- Members can query across accounts

### Example 3: Specific OUs Only

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMResourceDataSync
metadata:
  name: production-ou-sync
  namespace: ops
spec:
  syncType: SyncFromSource
  syncSource:
    sourceType: AwsOrganizations
    sourceRegions:
      - us-east-1
      - us-west-2
    includeFutureRegions: false  # Fixed regions only
    enableAllOpsDataSources: true
    awsOrganizationsSource:
      organizationSourceType: "OrganizationalUnits"
      organizationalUnits:
        - "ou-prod-12345678"     # Production OU
        - "ou-staging-87654321"  # Staging OU
  tags:
    Scope: ProductionOnly
    Environment: Production
```

Result:
- Syncs only from Production and Staging OUs
- Excludes Development accounts
- 2 fixed regions (no auto-expansion)
- Centralized visibility for production fleet

## S3 Destination Details

### Bucket Requirements

The S3 bucket must:
- Exist before the sync is created
- Allow SSM to write objects (IAM/bucket policy)
- Be in the specified region

### Prefix

Organize data using S3 prefixes:

```yaml
s3Destination:
  bucketName: "my-inventory"
  prefix: "ssm-inventory/production/2026/"
  # Objects stored at: s3://my-inventory/ssm-inventory/production/2026/...
```

### Encryption

Optionally encrypt synced data using KMS:

```yaml
s3Destination:
  awsKMSKeyARN: "arn:aws:kms:us-east-1:123456789012:key/12345678-..."
  # Sync data encrypted at rest in S3
```

Without encryption, objects are stored unencrypted (or use S3 default encryption if configured on bucket).

### Data Sharing

Enable cross-account data sharing:

```yaml
s3Destination:
  destinationDataSharing:
    destinationDataSharingType: "CrossAccountDataSharing"
```

Allows other AWS accounts (specified via bucket policy) to read inventory data.

## Sync Source Details

### Source Type: SingleAccountMultiRegions

Sync across multiple regions in a single account:

```yaml
syncSource:
  sourceType: SingleAccountMultiRegions
  sourceRegions: [us-east-1, us-west-2, eu-west-1]
  includeFutureRegions: false
  enableAllOpsDataSources: false
```

### Source Type: AwsOrganizations

#### Entire Organization

Sync all accounts:

```yaml
syncSource:
  sourceType: AwsOrganizations
  awsOrganizationsSource:
    organizationSourceType: "EntireOrganization"
  sourceRegions: [us-east-1, us-west-2]
  includeFutureRegions: true
```

#### Specific Organizational Units

Sync only specified OUs:

```yaml
syncSource:
  sourceType: AwsOrganizations
  awsOrganizationsSource:
    organizationSourceType: "OrganizationalUnits"
    organizationalUnits:
      - "ou-prod-12345678"
      - "ou-staging-87654321"
  sourceRegions: [us-east-1]
```

### Future Regions

Auto-include new AWS regions:

```yaml
syncSource:
  includeFutureRegions: true  # New regions auto-included
```

When AWS launches a new region, it's automatically included in the sync (if in `sourceRegions`).

### All OpsDataSources

Enable all operational data sources:

```yaml
syncSource:
  enableAllOpsDataSources: true
```

Includes:
- Applications
- AWS Config compliance
- Instance information
- Instance patches
- Network config
- Custom inventory
- Windows registry (Windows only)
- File contents (optional custom)

## Naming and ARN

Sync names follow standard naming conventions:

- Max 128 characters
- `a-zA-Z0-9_\-.` only
- Default template: `{namespace}-{name}`
- Custom via `spec.nameOverride`

**Important:** ResourceDataSync does **not have an ARN** in status. Unlike other SSM resources, `status.predictedArn` is omitted. Only `status.resourceName` is available.

```yaml
status:
  resourceName: "ops-fleet-inventory-sync"
  namingStatus: "valid"
  # NO predictedArn or ackResourceMetadata.arn for ResourceDataSync
```

## Status Fields

After creation:

```yaml
status:
  resourceName: "ops-fleet-inventory-sync"
  namingStatus: "valid"
  # Note: No predictedArn or ackResourceMetadata for ResourceDataSync (no ARN available)
```

## Governance Cascade

When fields aren't specified, they resolve via governance:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMResourceDataSync
metadata:
  name: my-sync
  namespace: ops
spec:
  configRef: general-policy
  syncType: SyncToDestination
  s3Destination:
    bucketName: "inventory-bucket"
    region: "us-east-1"
  # syncFormat, prefix not specified — resolved by cascade
```

Governance can enforce naming templates and tags:

```yaml
# In SSMConfig
spec:
  mandatory:
    namingTemplate: "{namespace}-inventory-{syncType}"
    tags:
      ManagedBy: kropath
      Purpose: Inventory
```

## Cross-Family Dependencies

SSMResourceDataSync requires:
- **S3 bucket** — Target for `SyncToDestination` (must exist beforehand)
- **KMS key** (optional) — For encrypting data in S3 (via `s3Destination.awsKMSKeyARN`)

Kropath does not enforce dependency ordering—the ACK controller handles eventual consistency via retries. Ensure the S3 bucket and KMS key exist before creating the sync.

## CloudFormation Tags Limitation

**Important:** The ACK `ResourceDataSync` CRD v1.5.1 does **not** support cloud tags via `spec.tags`. Tags are applied as Kubernetes metadata labels/annotations only (prefixed `aws.kropath.run/`), not as AWS tags on the ResourceDataSync resource itself.

This is an ACK limitation that may be addressed in future versions.

## Multiple Syncs in One Manifest

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: SSMResourceDataSync
metadata:
  name: s3-inventory
  namespace: ops
spec:
  syncType: SyncToDestination
  s3Destination:
    bucketName: "inventory-bucket"
    region: "us-east-1"
---
apiVersion: aws.kropath.run/v1alpha1
kind: SSMResourceDataSync
metadata:
  name: org-sync
  namespace: ops
spec:
  syncType: SyncFromSource
  syncSource:
    sourceType: AwsOrganizations
    sourceRegions: [us-east-1, us-west-2]
```

Result:
- One sync aggregating to S3
- One sync pulling from organization

## Best Practices

1. **Choose sync type based on use case**
   - **SyncToDestination:** Long-term retention, reporting, compliance
   - **SyncFromSource:** Multi-account visibility, centralized management

2. **Encrypt S3 data** — Use KMS when syncing to S3
3. **Use S3 prefixes** — Organize by environment, team, or time
4. **Set retention policies** — Add S3 lifecycle rules for cost optimization
5. **Include future regions** — Auto-expand to new AWS regions (if desired)
6. **Use governance profiles** — Let `SSMConfig` enforce naming and tags
7. **Verify bucket permissions** — Ensure SSM service role can write to bucket
8. **Monitor sync status** — Check Systems Manager console for sync health
9. **Tag for operations** — Environment, purpose, team metadata
10. **Use `retain` deletion policy** — Default; prevents accidental deletion

## Troubleshooting

**Sync creation fails with bucket access error**
- Verify bucket exists in specified region
- Check IAM permissions for SSM service role
- Verify bucket policy allows SSM to write

**Organization sync not syncing all accounts**
- Verify OU paths are correct (ou-xxxx-12345678 format)
- Confirm organization is set up correctly
- Check SSM API trust relationship with Organizations

**S3 data not appearing**
- Confirm sync completed (check CloudTrail/Systems Manager console)
- Verify bucket has read access
- Check S3 CloudTrail logs for write errors

**No ARN in status**
- ResourceDataSync intentionally has no ARN (AWS API limitation)
- Use `status.resourceName` instead for reference

## Next Steps

- [SSMConfig Governance](./ssmconfig.md) — Understanding sync governance
- [AWS Systems Manager Inventory](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-inventory.html) — AWS documentation
- [Resource Data Sync](https://docs.aws.amazon.com/systems-manager/latest/userguide/Explorer-resource-data-sync.html) — Data sync guide
