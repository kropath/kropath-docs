---
title: DynamoDBTable — Creating and Managing Tables
description: "The `DynamoDBTable` resource represents a single table in AWS DynamoDB."
doc_type: reference
---
# DynamoDBTable — Creating and Managing Tables

The `DynamoDBTable` resource represents a single table in AWS DynamoDB. This guide covers all configuration fields, governance cascade, and real-world usage patterns for creating and managing tables with encryption, billing modes, indexes, and backup policies.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `DynamoDBConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the table name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the table resource is deleted: `"retain"` (safe) or `"delete"` |

### Key Schema

| Field | Type | Required | Purpose |
|---|---|---|---|
| `keySchema` | array | yes | Partition key (HASH) and optional sort key (RANGE) for the table |
| `attributeDefinitions` | array | yes | Attribute definitions (only for key attributes: table + index keys) |

### Billing and Throughput

| Field | Type | Default | Purpose |
|---|---|---|---|
| `billingMode` | string | `""` | Billing mode: `PROVISIONED`, `PAY_PER_REQUEST`, or empty to use governance default |
| `provisionedThroughput` | object | required for PROVISIONED | Read and write capacity units for provisioned mode |
| `onDemandThroughput` | object | optional | Maximum request limits for on-demand mode |

### Encryption (Governed by DynamoDBConfig)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `encryption.enabled` | boolean | `false` | When `true`, uses customer-managed KMS encryption |
| `encryption.kmsMasterKeyId` | string | `""` | KMS key ARN, ID, or alias for encryption |

### Data Protection and Recovery (Governed by DynamoDBConfig)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `deletionProtectionEnabled` | boolean | `false` | When `true`, table cannot be deleted via AWS API |
| `pointInTimeRecoveryEnabled` | boolean | `false` | When `true`, enables restore to any point in the last 35 days |

### Table Class and Insights (Governed by DynamoDBConfig)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tableClass` | string | `""` | Table class: `STANDARD` or `STANDARD_INFREQUENT_ACCESS` (empty uses governance default) |
| `contributorInsights` | string | `""` | `ENABLE` or `DISABLE` Contributor Insights for monitoring (empty uses governance default) |

### Streams and TTL (Not Governed)

| Field | Type | Purpose |
|---|---|---|
| `streamSpecification.streamEnabled` | boolean | Enable DynamoDB Streams for change capture |
| `streamSpecification.streamViewType` | string | Stream view type: `KEYS_ONLY`, `NEW_IMAGE`, `OLD_IMAGE`, or `NEW_AND_OLD_IMAGES` |
| `timeToLive.enabled` | boolean | Enable automatic item expiration via TTL |
| `timeToLive.attributeName` | string | Attribute name containing Unix epoch timestamp for TTL |

### Indexes

| Field | Type | Purpose |
|---|---|---|
| `globalSecondaryIndexes` | array | Global secondary indexes (up to 20; mutable) |
| `localSecondaryIndexes` | array | Local secondary indexes (up to 5; immutable, created with table only) |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

### Resource Policy

| Field | Type | Default | Purpose |
|---|---|---|---|
| `resourcePolicyRef` | string | `""` | Name of a `PolicyDocument` CR for table-level access policy |

## Status Outputs

After reconciliation, the table's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective table name in AWS (derived from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if the table name is ready, `"invalid-unresolved-tokens"` if naming template has unresolved tokens |
| `predictedArn` | string | ARN of the table: `arn:aws:dynamodb:region:account:table/resourceName` |

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

## Complete Examples

### Basic On-Demand Table

Create a simple table without special encryption or protection:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DynamoDBTable
metadata:
  name: user-sessions
  namespace: app-team
spec:
  configRef: general-policy
  keySchema:
    - attributeName: sessionId
      keyType: HASH
  attributeDefinitions:
    - attributeName: sessionId
      attributeType: S
  billingMode: PAY_PER_REQUEST
  deletionPolicy: retain
```

Result:
- Table created in AWS DynamoDB with name `app-team-user-sessions`
- On-demand billing (pay per request)
- DynamoDB-owned encryption
- No deletion protection
- No PITR

### Production Table with Protection and Encryption

Create a table with mandatory protection settings and customer-managed encryption:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DynamoDBTable
metadata:
  name: orders
  namespace: production
spec:
  configRef: production  # Uses production governance profile
  keySchema:
    - attributeName: orderId
      keyType: HASH
    - attributeName: createdAt
      keyType: RANGE
  attributeDefinitions:
    - attributeName: orderId
      attributeType: S
    - attributeName: createdAt
      attributeType: N
  billingMode: PROVISIONED
  provisionedThroughput:
    readCapacityUnits: 100
    writeCapacityUnits: 100
  encryption:
    enabled: true
    kmsMasterKeyId: "arn:aws:kms:us-east-1:123456789012:key/prod-table-key"
  deletionProtectionEnabled: true
  pointInTimeRecoveryEnabled: true
  tags:
    business-critical: "true"
  syncedLabels:
    environment: production
  deletionPolicy: retain
```

Result:
- Table with composite key (orderId + createdAt)
- Provisioned billing with 100 read and 100 write capacity units
- Customer-managed KMS encryption (enforced by production profile)
- Deletion protection enabled (enforced by production profile)
- PITR enabled for 35-day recovery window (enforced by production profile)
- Custom tags and labels applied

### Table with Streams and TTL

Create a table that captures changes and automatically expires items:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DynamoDBTable
metadata:
  name: events
  namespace: analytics
spec:
  configRef: general-policy
  keySchema:
    - attributeName: eventId
      keyType: HASH
  attributeDefinitions:
    - attributeName: eventId
      attributeType: S
  billingMode: PAY_PER_REQUEST
  streamSpecification:
    streamEnabled: true
    streamViewType: NEW_AND_OLD_IMAGES
  timeToLive:
    enabled: true
    attributeName: expiresAt
  tags:
    data-type: event-log
  deletionPolicy: retain
```

Result:
- DynamoDB Streams enabled with NEW_AND_OLD_IMAGES view (captures before/after values)
- TTL enabled on `expiresAt` attribute (items expire automatically)
- Lambda or other services can consume stream records in real time

### Table with Global and Local Secondary Indexes

Create a table with multiple query patterns via indexes:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DynamoDBTable
metadata:
  name: products
  namespace: catalog
spec:
  configRef: general-policy
  keySchema:
    - attributeName: productId
      keyType: HASH
  attributeDefinitions:
    - attributeName: productId
      attributeType: S
    - attributeName: category
      attributeType: S
    - attributeName: priceRange
      attributeType: N
  billingMode: PROVISIONED
  provisionedThroughput:
    readCapacityUnits: 50
    writeCapacityUnits: 50
  globalSecondaryIndexes:
    - indexName: category-price-index
      keySchema:
        - attributeName: category
          keyType: HASH
        - attributeName: priceRange
          keyType: RANGE
      projection:
        projectionType: ALL
      provisionedThroughput:
        readCapacityUnits: 25
        writeCapacityUnits: 25
  localSecondaryIndexes:
    - indexName: product-lsi
      keySchema:
        - attributeName: productId
          keyType: HASH
        - attributeName: category
          keyType: RANGE
      projection:
        projectionType: KEYS_ONLY
  deletionPolicy: retain
```

Result:
- Base table with primary key on productId
- Global secondary index for querying by category and price range
- Local secondary index for range queries within a product
- Each index has its own provisioned throughput (GSI only; LSI shares table throughput)

### Table with Resource Policy

Create a table with a resource-based access policy:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DynamoDBTable
metadata:
  name: shared-data
  namespace: default
spec:
  configRef: general-policy
  keySchema:
    - attributeName: dataId
      keyType: HASH
  attributeDefinitions:
    - attributeName: dataId
      attributeType: S
  billingMode: PAY_PER_REQUEST
  resourcePolicyRef: shared-data-policy
  deletionPolicy: retain
---
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: shared-data-policy
  namespace: default
  labels:
    aws.kropath.run/resource-name: shared-data-policy
spec:
  documentJSON: |
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "AWS": "arn:aws:iam::123456789012:role/cross-account-app"
          },
          "Action": "dynamodb:GetItem",
          "Resource": "*"
        }
      ]
    }
```

Result:
- Table with resource-based policy attached
- Cross-account role can read items from the table
- Policy can be updated independently via the PolicyDocument CR

## Governance Cascade

The effective configuration for each table is determined by a three-tier cascade:

1. **Governance mandatory tier** (highest priority) — Platform enforcement that overrides everything
2. **Table spec** (middle) — Developer choices
3. **Governance defaults tier** (lowest priority) — Fallback values

For example, if the production profile has `mandatory.deletionProtectionEnabled: true`, that protection is always applied, even if the table specifies `deletionProtectionEnabled: false`. If mandatory is unset but the table doesn't specify encryption, the defaults apply.

Platform teams use the mandatory tier for critical controls (compliance, encryption, deletion protection); they also use the defaults tier to provide reasonable baselines that developers can override when needed.

## Key Behaviors

### Immutable Table Name After Creation

Once created in AWS DynamoDB, a table's name cannot be changed. The naming template or `nameOverride` field determines the name at creation time only.

### Immutable Key Schema and LSIs

Once a table is created, the key schema and local secondary indexes cannot be modified. These structures are defined at table creation time and are permanent. Global secondary indexes, on the other hand, can be added or removed after table creation.

### Predictable ARNs

The ARN shown in `status.predictedArn` follows the format `arn:aws:dynamodb:region:account:table/tableName`, which is computed from the effective table name. Use this ARN in resource policies or cross-service references.

### Billing Mode Impact

- **PROVISIONED** — Pay for specific read/write capacity; good for predictable workloads
- **PAY_PER_REQUEST** — Pay per request; good for bursty or unpredictable workloads

Switching billing modes after table creation is possible but involves downtime. Plan your billing mode at creation time.

### Encryption Behavior

- When `encryption.enabled: false` — Table uses DynamoDB-owned encryption (AWS managed)
- When `encryption.enabled: true` and `kmsMasterKeyId` set — Table uses customer-managed KMS encryption
- When `encryption.enabled: true` and `kmsMasterKeyId` empty — Table uses AWS-managed service key (`aws/dynamodb`)

Encryption cannot be changed after table creation.

### Deletion Policy

- `retain` (default) — Deleting the Kubernetes resource keeps the table safe in DynamoDB
- `delete` — Deleting the Kubernetes resource also deletes the table in AWS (use with caution)

### Tag Format

Tags in kropath are specified as a map (e.g. `key: value`). DynamoDB stores tags internally as a list. The conversion is handled automatically during reconciliation.

## Troubleshooting

### Table Not Creating

Check `status.namingStatus`:
- If `invalid-unresolved-tokens`, the naming template has a token that cannot be resolved (e.g. a tag key that doesn't exist). Fix the template or ensure required tags are present.
- If `valid` but table not created, check `status.conditions` for errors from AWS (e.g., permission issues, duplicate name).

### Can't Override Encryption or Deletion Protection

If governance has a mandatory tier set for `encryptionEnabled` or `deletionProtectionEnabled`, those values cannot be overridden at the table level. Only the defaults tier can be overridden by the developer. Contact your platform team if you need different settings.

### Table Won't Delete When `deletionPolicy: delete`

Ensure the Kubernetes service account running kropath has AWS IAM permissions for `dynamodb:DeleteTable`. If the table has resource-based policies restricting deletion, those must be updated in AWS before the Kubernetes resource can be deleted.
