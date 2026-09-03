# KeyspacesKeyspace

`KeyspacesKeyspace` is a Kubernetes resource that represents an Amazon Keyspaces keyspace — a top-level namespace that groups CQL tables. Every Keyspaces table must belong to a keyspace, so you create keyspaces first before creating any tables within them.

## Scope

This resource is AWS-only. It wraps the ACK `Keyspace` resource and is specific to Amazon Keyspaces. GCP Cloud Bigtable and Azure Cosmos DB have different container concepts and are out of scope for this resource.

## What it solves

When working with AWS Keyspaces, you need to:

- **Create keyspaces before tables** — AWS requires the keyspace to exist first
- **Set replication strategy** — choose between single-region and multi-region, and this is immutable after creation
- **Apply naming conventions** — cloud resource names should follow your organization's naming scheme
- **Apply governance tags** — every keyspace should inherit tags from platform policies
- **Track resource status** — know when a keyspace is ready and what its ARN is

`KeyspacesKeyspace` streamlines this by providing:

- **Simple YAML spec** — define a keyspace with just its replication strategy and container keyspace name
- **Governance integration** — inherit encryption, PITR, and tagging requirements from a `KeyspacesConfig` profile
- **Naming automation** — cloud names are generated automatically using configurable templates
- **ARN tracking** — the resource exposes its predicted ARN so other resources can reference it
- **Immutability enforcement** — the replication strategy is locked after creation (just like AWS enforces)

## Core concepts

### Replication strategy

A keyspace has two replication strategies:

**SINGLE_REGION** (default):
- Keyspace is replicated within a single AWS region
- Lowest latency for single-region workloads
- Lower cost than multi-region
- Cannot be changed after creation

**MULTI_REGION**:
- Keyspace is replicated across multiple AWS regions
- Requires explicit list of regions (max 6)
- Higher resilience and disaster recovery
- Cannot be changed after creation
- Example: `us-east-1`, `eu-west-1`, `ap-southeast-1`

### Configuration via profile

A `KeyspacesConfig` profile governs settings that apply to the keyspace:

- **Encryption**: AWS-managed or customer-managed KMS keys
- **Replication strategy**: Can be enforced by a profile (e.g., `high-availability` profile mandates multi-region)
- **Tagging**: Org-wide and profile tags are applied automatically
- **Naming template**: How the cloud keyspace name is generated

You select a profile via `spec.configRef`. If you omit it, `general-policy` is used by default.

### Naming convention

Cloud keyspace names are generated from a template using:

| Token | Value | Example |
|---|---|---|
| `{namespace}` | Kubernetes namespace | `payments-prod` → `payments_prod` in name |
| `{name}` | CR name | CR `my-keyspace` → `my_keyspace` in name |
| `{account_id}` | AWS account ID | From cluster metadata |
| `{region}` | AWS region | From cluster metadata |
| `{configRef}` | Selected profile name | `compliance` → included in name if template uses it |
| `{tag.<key>}` | Tag value | `{tag.env}` → replaced with the tag's value |

**Default template**: `{namespace}_{name}`

Keyspaces identifiers allow only alphanumeric characters and underscores; the max length is 48 characters. The platform enforces these constraints via `status.namingStatus`.

**Example**: CR in namespace `payments-prod` named `orders` with template `{namespace}_{name}` becomes cloud keyspace name `payments_prod_orders`.

You can also override the entire name with `spec.nameOverride`.

### Immutability

The replication strategy and region list are immutable after the keyspace is created. This mirrors AWS Keyspaces behavior. Attempting to change them after creation is rejected:

```yaml
# This keyspace was created with SINGLE_REGION
# Updating to MULTI_REGION will be rejected
spec:
  replicationStrategy: MULTI_REGION  # ← Rejected: immutable
```

## Complete example

Here's a keyspace for a payments service with multi-region failover:

```yaml
---
# First, ensure the high-availability profile exists
apiVersion: aws.kropath.run/v1alpha1
kind: KeyspacesConfig
metadata:
  name: high-availability
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: high-availability
spec:
  mandatory:
    replicationStrategy: "MULTI_REGION"
    pointInTimeRecovery: true
  defaults:
    throughputMode: "PAY_PER_REQUEST"
    encryptionType: "AWS_OWNED_KMS_KEY"
    namingTemplate: "{namespace}_{name}"

---
# Create the keyspace in the payments namespace
apiVersion: aws.kropath.run/v1alpha1
kind: KeyspacesKeyspace
metadata:
  name: orders
  namespace: payments-prod
spec:
  # Use the HA profile, which mandates multi-region and PITR
  configRef: high-availability
  
  # Multi-region replication across 3 regions
  replicationStrategy: MULTI_REGION
  regionList:
    - us-east-1      # Primary region
    - eu-west-1      # European replica
    - ap-southeast-1 # Asia-Pacific replica
  
  # Deletion policy: retain (don't delete the AWS keyspace when this CR is deleted)
  deletionPolicy: retain
  
  # Tags for cost tracking and billing
  tags:
    cost-center: "payments-team"
    project: "orders-service"
  
  # Labels that should appear on both K8s resources and cloud tags
  syncedLabels:
    environment: production
    team: payments-platform
```

After applying this, inspect the status:

```bash
kubectl describe keyspaceskeyspace orders -n payments-prod
```

You'll see:

- `status.resourceName: payments_prod_orders` — the cloud keyspace name
- `status.predictedArn: arn:aws:cassandra:us-east-1:123456789012:/keyspace/payments_prod_orders/` — the ARN for reference by other resources
- `status.namingStatus: valid` — the name template resolved successfully
- Standard Kubernetes conditions showing reconciliation status

## Reference specification

### Spec fields

| Field | Type | Required? | Default | Notes |
|---|---|---|---|---|
| `configRef` | string | No | `general-policy` | Profile name for governance (encryption, PITR, tags, naming template). |
| `replicationStrategy` | `SINGLE_REGION` \| `MULTI_REGION` | No | From profile defaults | Keyspace replication. Immutable after creation. |
| `regionList` | `[]string` | No | `[]` | Regions for multi-region replication. Immutable after creation. Max 6 regions. Required if replicationStrategy is `MULTI_REGION`. |
| `nameOverride` | string | No | (empty) | Override the cloud keyspace name entirely. Bypasses the naming template. |
| `deletionPolicy` | `retain` \| `delete` | No | `retain` | Whether to delete the AWS keyspace when this CR is deleted. |
| `tags` | map[string]string | No | `{}` | Cloud resource tags. Merged with profile tags (profile tags win on conflict). |
| `syncedLabels` | map[string]string | No | `{}` | Labels to sync to both K8s resource and cloud tags. |
| `syncedAnnotations` | map[string]string | No | `{}` | Annotations to sync to K8s resource and cloud tags. |

### Status fields

| Field | Type | Meaning |
|---|---|---|
| `resourceName` | string | The generated cloud keyspace name (after naming template substitution). |
| `namingStatus` | `valid` \| `invalid-unresolved-tokens` | Whether the naming template resolved successfully. `invalid-unresolved-tokens` means a tag reference in the template is missing. |
| `predictedArn` | string | The full ARN of the keyspace: `arn:aws:cassandra:{region}:{account_id}:/keyspace/{resourceName}/` |
| `conditions[]` | list | Standard Kubernetes reconciliation conditions (Ready, etc.). |

## Deleting a keyspace

By default, `spec.deletionPolicy: retain` means the Kubernetes CR can be deleted without deleting the actual AWS keyspace. This is safe — the keyspace persists in AWS.

To delete both the CR and the AWS keyspace, set `spec.deletionPolicy: delete`:

```yaml
spec:
  deletionPolicy: delete  # AWS keyspace will be deleted when CR is deleted
```

## Profile inheritance

When you reference a profile, the keyspace inherits:

- **Encryption** — AWS-managed or customer-managed (with KMS key)
- **PITR** — Point-in-time recovery enabled/disabled
- **Tagging** — Platform tags, environment tags, cost-center tags
- **Naming template** — How cloud names are generated

Example: if the `compliance` profile mandates PITR, all keyspaces using that profile will have PITR enabled, regardless of what the instance spec says.

If the profile mandates replication strategy (e.g., `high-availability` mandates `MULTI_REGION`), any instance using that profile will use multi-region replication.

## ARN reference pattern

Other resources can reference a keyspace by its ARN. The `status.predictedArn` field exposes this:

```bash
kubectl get keyspaceskeyspace orders -n payments-prod -o jsonpath='{.status.predictedArn}'
# Output: arn:aws:cassandra:us-east-1:123456789012:/keyspace/payments_prod_orders/
```

Tables within this keyspace can reference it via the `spec.keyspaceName` field (plain string, not an ARN):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KeyspacesTable
metadata:
  name: user-events
spec:
  keyspaceName: payments_prod_orders  # Cloud keyspace name (from status.resourceName)
  # ... rest of table spec ...
```

## Multi-region best practices

1. **Always include the primary region.** If creating a multi-region keyspace, the current AWS region must be in the region list.

2. **Start with single-region.** Multi-region is immutable, so choose carefully. Test with single-region first, then migrate to multi-region when you're confident.

3. **Use 3 regions for HA.** Primary + 2 secondaries provides good geographic spread without over-provisioning. Maximum is 6.

4. **Profile-enforce for compliance.** If your policy requires multi-region for DR, use a profile to mandate `MULTI_REGION` so teams can't accidentally create single-region keyspaces.

5. **Monitor replication lag.** Multi-region replication has eventual consistency semantics. Monitor your application's tolerance for cross-region lag.

## Troubleshooting

### Immutability error
```
Error: replicationStrategy is immutable after creation
```
Once created, the replication strategy cannot change. Delete the keyspace and recreate it with the new strategy.

### Naming invalid
```
status.namingStatus: invalid-unresolved-tokens
```
A tag reference in your naming template is missing. Example: template `{tag.env}_{name}` fails if the `env` tag is not set. Add the missing tag to `spec.tags`.

### Region list validation failed
```
Error: regionList must contain at most 6 regions
```
You specified more than 6 regions. AWS Keyspaces supports maximum 6 regions per keyspace.

```
Error: regionList is required when replicationStrategy is MULTI_REGION
```
You set `replicationStrategy: MULTI_REGION` but left `regionList` empty. Provide at least one region.

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `KeyspacesKeyspace`
- **Scope**: Namespaced
