# KeyspacesTable

`KeyspacesTable` is a Kubernetes resource that represents an Amazon Keyspaces CQL table. It wraps the ACK `Table` resource and provides a higher-level interface for managing table schema, capacity, encryption, backups, and TTL in a way that's consistent with your organization's governance policies.

## Scope

This resource is AWS-only. It is specific to Amazon Keyspaces. GCP Cloud Bigtable and Azure Cosmos DB have different schema and capacity models.

## What it solves

Creating and managing CQL tables in Keyspaces involves many decisions:

- **Schema definition** — columns, partition keys, clustering keys, static columns
- **Throughput mode** — on-demand (pay-per-request) or provisioned capacity
- **Encryption** — AWS-managed or customer-managed KMS keys
- **Data protection** — PITR (backup), row-level TTL, client-side timestamps
- **Governance** — every table should follow org-wide policies (encryption, backup retention, throughput defaults)
- **Naming** — cloud table names should follow a consistent scheme
- **Deletion policy** — what happens when the CR is deleted

Manually setting each of these on every table creates inconsistency and drift. `KeyspacesTable` solves this by providing:

- **Structured schema definition** — define columns and keys as YAML objects, validated at apply time
- **Governance integration** — inherit encryption, PITR, and throughput defaults from a `KeyspacesConfig` profile
- **Flexible capacity** — choose pay-per-request or provisioned, with validation for required fields
- **Flexible encryption** — AWS-managed (default), customer-managed via direct ARN, or via a `KMSKey` resource reference
- **Automatic naming** — table names are generated from a template
- **ARN tracking** — know the predicted ARN for reference by other resources
- **Status visibility** — see when the table is ready, its capacity mode, and its lifecycle status

## Core concepts

### Schema definition

A table requires three things:

**Columns** — all columns in the table, each with a name and CQL type:

```yaml
columns:
  - name: user_id
    type: uuid
  - name: event_time
    type: timestamp
  - name: event_type
    type: text
  - name: metadata
    type: text
```

**Partition keys** — the first level of sharding (hash keys):

```yaml
partitionKeys:
  - name: user_id  # Every query must provide this
```

**Clustering keys** (optional) — the second level of sorting within a partition:

```yaml
clusteringKeys:
  - name: event_time
    orderBy: DESC  # or ASC for ascending
```

**Static columns** (optional) — columns that are shared across all rows in a partition:

```yaml
staticColumns:
  - name: profile_picture  # Shared across all events for a user
```

The example creates a table like:

```
CREATE TABLE IF NOT EXISTS events (
  user_id UUID,
  event_time TIMESTAMP,
  event_type TEXT,
  metadata TEXT,
  profile_picture TEXT STATIC,
  PRIMARY KEY ((user_id), event_time)
) WITH CLUSTERING ORDER BY (event_time DESC);
```

### Throughput modes

**PAY_PER_REQUEST** (on-demand, default):
- You pay for every read and write operation
- No pre-provisioning required
- Variable cost model
- Good for unpredictable or bursty workloads

**PROVISIONED**:
- You reserve read and write capacity upfront
- Lower cost for predictable, sustained workloads
- Requires `spec.readCapacityUnits` and `spec.writeCapacityUnits`
- `readCapacityUnits` and `writeCapacityUnits` must be > 0; AWS recommends provisioning in increments of 100 for most workloads

### Encryption options

**AWS-managed** (default):
- Encryption key managed by AWS
- No additional cost
- Simplest operational model
- Sufficient for most workloads

**Customer-managed KMS key**:
- You manage the encryption key via AWS KMS
- Required for compliance audits (you control key rotation and access)
- Additional AWS KMS costs
- Two ways to specify:

  1. **Direct ARN** — reference a KMS key you've already created:
     ```yaml
     kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
     ```

  2. **Reference a `KMSKey` resource** — let kropath manage the key:
     ```yaml
     kmsKeyRef: my-kms-key
     ```
     The controller resolves the reference to the key's ARN at composition time.

### Data protection

**Point-in-Time Recovery (PITR)**:
- AWS keeps a 35-day backup of your table
- Allows recovery to any point in time within the window
- Enabling PITR increases storage costs
- Can be mandatory via profile for compliance workloads

**Row-level TTL**:
- Rows automatically expire after a specified time
- TTL is set per-row or via a default across the table
- One-way toggle: once enabled, cannot be disabled
- Useful for time-series data, logs, sessions

**Client-side timestamps**:
- Cassandra automatically assigns server-side timestamps to every write
- Client-side timestamps let your application provide the timestamp
- Cannot be disabled once enabled
- Rarely needed unless your application has specific timestamp requirements

### Configuration via profile

A `KeyspacesConfig` profile governs:

- **Throughput mode** — can enforce provisioned or on-demand
- **Encryption** — can mandate customer-managed keys for compliance
- **PITR** — can mandate point-in-time recovery for audit tables
- **TTL** — can mandate TTL for time-series or log data
- **Naming template** — how table names are generated
- **Tagging** — org-wide and profile tags

You select a profile via `spec.configRef`. If you omit it, `general-policy` is used.

## Complete example

Here's a comprehensive example: an events table for an e-commerce platform with compliance encryption and backups:

```yaml
---
# First, create a customer-managed KMS key for encryption
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: commerce-table-key
  namespace: commerce
  labels:
    aws.kropath.run/resource-name: commerce-table-key
spec:
  # ... KMS key configuration ...

---
# Create the compliance profile (requires customer-managed encryption and PITR)
apiVersion: aws.kropath.run/v1alpha1
kind: KeyspacesConfig
metadata:
  name: compliance
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: compliance
spec:
  mandatory:
    encryptionType: "CUSTOMER_MANAGED_KMS_KEY"
    pointInTimeRecovery: true
  defaults:
    throughputMode: "PAY_PER_REQUEST"
    ttlEnabled: false
    namingTemplate: "{namespace}_{name}"

---
# Create the events table
apiVersion: aws.kropath.run/v1alpha1
kind: KeyspacesTable
metadata:
  name: events
  namespace: commerce
spec:
  # Use compliance profile (mandates CMK encryption and PITR)
  configRef: compliance
  
  # Keyspace must exist first
  keyspaceName: commerce_prod_orders
  
  # Schema: track user events in the orders domain
  columns:
    - name: user_id
      type: uuid
    - name: event_time
      type: timestamp
    - name: event_type
      type: text
    - name: order_id
      type: uuid
    - name: amount
      type: decimal
    - name: metadata
      type: text
    - name: profile_picture
      type: text
  
  partitionKeys:
    - name: user_id
  
  clusteringKeys:
    - name: event_time
      orderBy: DESC
  
  staticColumns:
    - name: profile_picture
  
  # On-demand throughput (from profile defaults)
  throughputMode: ""  # Empty: inherit from profile
  
  # Encryption: profile mandates CUSTOMER_MANAGED_KMS_KEY
  encryptionType: ""  # Empty: inherit from profile
  kmsKeyRef: commerce-table-key  # Reference the KMS key by name
  
  # Data protection: profile mandates PITR
  pointInTimeRecovery: null  # Null: inherit from profile (will be true)
  
  # TTL disabled by default, but can be set per-row
  ttlEnabled: false
  defaultTimeToLive: 0  # No default TTL
  
  # Deletion policy
  deletionPolicy: retain
  
  # Human-readable description
  comment: "Events for order processing and audit trail (PCI compliance)"
  
  # Tagging for billing and compliance
  tags:
    cost-center: "commerce-platform"
    data-classification: "pci-dss"
  
  syncedLabels:
    environment: production
    team: commerce-platform
```

After applying this:

```bash
kubectl describe keyspacestable events -n commerce
```

You'll see:

- `status.resourceName: commerce_events` — the cloud table name
- `status.predictedArn: arn:aws:cassandra:us-east-1:123456789012:/keyspace/commerce_prod_orders/table/commerce_events` — the full ARN
- `status.tableStatus: ACTIVE` — the table is ready for use
- Standard reconciliation conditions

## Reference specification

### Spec fields

| Field | Type | Required? | Default | Notes |
|---|---|---|---|---|
| `configRef` | string | No | `general-policy` | Profile name for governance (encryption, PITR, throughput, tags, naming). |
| `keyspaceName` | string | **Yes** | (required) | Name of the containing keyspace. Must exist first. |
| `columns` | `[]Column` | **Yes** | (required) | All columns in the table. Each: `{name: string, type: string}`. |
| `partitionKeys` | `[]PartitionKey` | **Yes** | (required) | Partition keys (shard keys). Each: `{name: string}`. |
| `clusteringKeys` | `[]ClusteringKey` | No | `[]` | Clustering keys (sort within partition). Each: `{name: string, orderBy: ASC/DESC}`. |
| `staticColumns` | `[]StaticColumn` | No | `[]` | Static columns (shared per partition). Each: `{name: string}`. |
| `throughputMode` | `PAY_PER_REQUEST` \| `PROVISIONED` | No | From profile | Capacity mode. Empty = inherit from profile. |
| `readCapacityUnits` | integer | No | 0 | Required if `throughputMode` is `PROVISIONED`. Must be > 0. |
| `writeCapacityUnits` | integer | No | 0 | Required if `throughputMode` is `PROVISIONED`. Must be > 0. |
| `encryptionType` | `AWS_OWNED_KMS_KEY` \| `CUSTOMER_MANAGED_KMS_KEY` | No | From profile | Encryption type. Empty = inherit from profile. |
| `kmsKeyArn` | string | No | (empty) | Direct ARN of customer-managed KMS key. Mutually exclusive with `kmsKeyRef`. |
| `kmsKeyRef` | string | No | (empty) | Name of `KMSKey` CR in same namespace. Mutually exclusive with `kmsKeyArn`. |
| `pointInTimeRecovery` | boolean | No | (null) | Enable PITR. Null = inherit from profile. |
| `ttlEnabled` | boolean | No | (null) | Enable row-level TTL. Null = inherit from profile. One-way toggle: cannot disable. |
| `defaultTimeToLive` | integer | No | 0 | Default TTL in seconds. 0 = no default. |
| `clientSideTimestamps` | boolean | No | (null) | Enable client-side timestamps. One-way toggle. |
| `comment` | string | No | (empty) | Human-readable table description. |
| `nameOverride` | string | No | (empty) | Override cloud table name entirely. Bypasses naming template. |
| `deletionPolicy` | `retain` \| `delete` | No | `retain` | Delete AWS table when CR is deleted? |
| `tags` | map[string]string | No | `{}` | Cloud tags. Merged with profile (profile wins on conflict). |
| `syncedLabels` | map[string]string | No | `{}` | Labels to sync to K8s and cloud tags. |
| `syncedAnnotations` | map[string]string | No | `{}` | Annotations to sync to K8s and cloud tags. |

### Status fields

| Field | Type | Meaning |
|---|---|---|
| `resourceName` | string | Generated cloud table name (after naming template substitution). |
| `namingStatus` | `valid` \| `invalid-unresolved-tokens` | Whether naming template resolved. `invalid` means a tag is missing. |
| `predictedArn` | string | Full ARN: `arn:aws:cassandra:{region}:{account_id}:/keyspace/{keyspaceName}/table/{resourceName}` |
| `tableStatus` | string | AWS table lifecycle: `ACTIVE`, `CREATING`, `DELETING`, etc. |
| `conditions[]` | list | Standard reconciliation conditions (Ready, etc.). |

## Provisioned capacity example

For predictable workloads, reserve capacity:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KeyspacesTable
metadata:
  name: sessions
  namespace: auth
spec:
  configRef: general-policy
  keyspaceName: auth_sessions
  
  # Schema...
  columns:
    - name: session_id
      type: uuid
    - name: user_id
      type: uuid
    - name: created_at
      type: timestamp
  partitionKeys:
    - name: session_id
  
  # Provisioned capacity
  throughputMode: PROVISIONED
  readCapacityUnits: 100
  writeCapacityUnits: 100
  
  # TTL: session expires after 1 day (86400 seconds)
  ttlEnabled: true
  defaultTimeToLive: 86400
```

## KMS key reference vs. direct ARN

**Use `kmsKeyRef` when**:
- You want kropath to manage the KMS key resource
- The key is created and deployed via CR
- You want the full lifecycle to be declarative

**Use `kmsKeyArn` when**:
- The KMS key exists outside of kropath (manually managed)
- The key is shared across multiple systems
- You just need to reference an existing key

Both approaches work; choose based on your key management strategy.

## TTL and timestamps: one-way toggles

Once you enable either TTL or client-side timestamps, you **cannot disable them** — this is an AWS Keyspaces constraint, not a kropath limitation.

```yaml
# First version: TTL disabled
ttlEnabled: false

# Later version: enable TTL for time-series data
ttlEnabled: true
defaultTimeToLive: 86400
```

Later, if you try to disable TTL:

```yaml
# This will be rejected by AWS
ttlEnabled: false  # Error: once enabled, cannot disable
```

Plan your data protection strategy upfront.

## Profile inheritance

When using a `KeyspacesConfig` profile, the table inherits:

- **Throughput mode** — on-demand vs. provisioned (can be mandatory)
- **Encryption** — AWS-managed vs. customer-managed (can be mandatory)
- **PITR** — point-in-time recovery enabled/disabled (can be mandatory)
- **TTL** — row-level TTL enabled/disabled (can be mandatory)
- **Tagging** — org-wide and profile tags
- **Naming template** — how cloud table names are generated

If a profile mandates customer-managed encryption, you must provide either `kmsKeyArn` or `kmsKeyRef`; otherwise the table creation fails.

## Naming convention

Cloud table names are generated from a template (default: `{namespace}_{name}`) using tokens:

| Token | Value |
|---|---|
| `{namespace}` | Kubernetes namespace |
| `{name}` | CR name |
| `{account_id}` | AWS account ID |
| `{region}` | AWS region |
| `{configRef}` | Selected profile name |
| `{tag.<key>}` | Tag value |

**Example**: CR in namespace `commerce-prod` named `events` with template `{namespace}_{name}` becomes cloud table name `commerce_prod_events`.

Table names allow only alphanumeric characters and underscores; max 48 characters.

You can override the entire name with `spec.nameOverride`.

## Deleting a table

By default, `spec.deletionPolicy: retain` means the Kubernetes CR can be deleted without deleting the AWS table. The data persists in AWS.

To delete both:

```yaml
spec:
  deletionPolicy: delete  # AWS table will be deleted when CR is deleted
```

## Best practices

1. **Define schema carefully.** Schema is immutable in Keyspaces (no alter table). Test extensively before deployment.

2. **Use profiles for compliance.** If encryption or PITR are mandatory for your org, encode them in a profile so tables automatically inherit them.

3. **Plan TTL upfront.** TTL is a one-way toggle. Decide at creation time whether rows need expiration.

4. **Use provisioned capacity for stable workloads.** If your query patterns are predictable, reserve capacity to save costs vs. on-demand.

5. **Tag at table creation.** Cost-tracking and environment tags should be set upfront; retroactive tagging is error-prone.

6. **Monitor table status.** Tables take time to provision. Check `status.tableStatus` to know when the table is ready for writes.

7. **Document schema intent.** The `comment` field is visible in AWS and useful for team members. Use it to explain the table's purpose and schema design.

## Troubleshooting

### Encryption error
```
Error: kmsKeyArn and kmsKeyRef are mutually exclusive
```
You specified both. Provide only one.

```
Error: kmsKeyArn or kmsKeyRef is required when encryptionType is CUSTOMER_MANAGED_KMS_KEY
```
You set encryption to customer-managed but didn't provide a key. Add either `kmsKeyArn` or `kmsKeyRef`.

### Capacity validation error
```
Error: readCapacityUnits is required and must be > 0 when throughputMode is PROVISIONED
```
You selected provisioned mode but didn't specify read capacity. Provide a value greater than 0.

### TTL toggle error
```
Error: ttlEnabled cannot be changed from true to false
```
TTL is one-way. Once enabled, it cannot be disabled. Create a new table if you need to disable TTL.

### Naming invalid
```
status.namingStatus: invalid-unresolved-tokens
```
A tag reference in your naming template is missing. Example: template `{tag.env}_{name}` fails if the `env` tag is absent. Add the missing tag to `spec.tags`.

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `KeyspacesTable`
- **Scope**: Namespaced
