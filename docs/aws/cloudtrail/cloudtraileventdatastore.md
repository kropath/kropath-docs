# CloudTrailEventDataStore — Event Querying with CloudTrail Lake

CloudTrailEventDataStore is a kropath resource for creating and managing AWS CloudTrail Lake event data stores. An event data store collects and stores CloudTrail audit events in a queryable format, enabling SQL-based analysis of API activity across your AWS environment.

## Prerequisites and Setup

CloudTrailEventDataStore resources require:

*   A **CloudTrailConfig** governance profile (defaults to `"general-policy"` if not specified).
*   *(Optional)* A **KMS key** for encryption (customer-managed KMS encryption is deferred; currently AWS-managed encryption is used).

Unlike CloudTrailTrail, event data stores do not require S3 buckets or CloudWatch Logs configuration—CloudTrail Lake manages storage and query infrastructure.

## Configuration

### Core Fields

A CloudTrailEventDataStore instance specifies:

*   **`configRef`** (string, default: `"general-policy"`): The CloudTrailConfig profile to use for governance. If the named profile does not exist, it falls back to `"general-policy"`.
*   **`deletionPolicy`** (string, default: `"retain"`): Determines behavior when the event data store CR is deleted:
    *   `"retain"`: The AWS event data store persists after CR deletion.
    *   `"delete"`: The AWS event data store is deleted when the CR is deleted.

### Event Collection Scope

Control which events are collected and from which regions/accounts:

*   **`multiRegionEnabled`** (boolean, tri-state): When `true`, the data store collects events from all AWS regions. When `false`, collects from the current region only. When unset, governance decides (defaults to `false`).
*   **`organizationEnabled`** (boolean, tri-state): When `true`, the data store collects events from all AWS accounts in your organization. When `false`, collects from your account only. When unset, governance decides (defaults to `false`).

### Retention and Protection

*   **`retentionPeriod`** (integer, tri-state): The number of days to retain events in the data store. Minimum 7 days; maximum 2557 days (7 years, FIXED_RETENTION pricing) or 3653 days (10 years, EXTENDABLE_RETENTION pricing). When unset, governance decides (defaults to 2557 days).
*   **`terminationProtectionEnabled`** (boolean, tri-state): When `true`, the event data store cannot be deleted until termination protection is disabled. When unset, governance decides (defaults to `true`).

### Event Filtering

*   **`advancedEventSelectors`** (array): Up to 5 advanced event selectors to filter which events are ingested. Each selector has:
    *   `name` (string, optional): A display name for the selector.
    *   `fieldSelectors` (array, required): One or more field selectors specifying which events to include.
        *   `field` (string): The event field name (e.g., `"eventCategory"`, `"resources.type"`).
        *   `equals`, `notEquals`, `startsWith`, `notStartsWith`, `endsWith`, `notEndsWith` (array of strings): Matching conditions.

If `advancedEventSelectors` is empty (default), all events are collected.

### Metadata and Tags

*   **`tags`** (map<string,string>): Custom AWS tags applied to the event data store. Merged with mandatory and default tags from governance.
*   **`syncedLabels`** (map<string,string>): Kubernetes labels mirrored as AWS resource tags (prefixed `aws.kropath.run/`).
*   **`syncedAnnotations`** (map<string,string>): Kubernetes annotations mirrored as AWS resource tags (prefixed `aws.kropath.run/`).

## Naming

**Naming exemption:** Event data store ARNs are opaque and UUID-based (e.g., `arn:aws:cloudtrail:us-east-1:123456789012:eventdatastore/12345678-1234-1234-1234-123456789012`). The `{namespace}-{name}` pattern does not apply. The ACK CRD requires a display label (`spec.name`), which the RGD derives automatically as `"{namespace}-{name}"`, but this label does not appear in the ARN.

There is no `status.resourceName`, `status.namingStatus`, or `status.predictedArn` for event data stores.

## Governance Cascade

All fields follow the ten-tier governance cascade:

1. **CloudTrailConfig `mandatory` tier** (highest priority)
2. **CloudTrailEventDataStore `spec` instance override**
3. **CloudTrailConfig `defaults` tier** (lowest priority)

The RGD resolves each field by checking this cascade in order and applying the first non-nil/non-zero value found.

## Example CloudTrailEventDataStore Resources

### Basic Event Data Store

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailEventDataStore
metadata:
  name: api-events
  namespace: analytics-prod
spec:
  configRef: general-policy
  retentionPeriod: 365  # 1 year
  multiRegionEnabled: false
  organizationEnabled: false
  terminationProtectionEnabled: true
  tags:
    team: analytics
    environment: production
```

### Multi-Region Organization Event Data Store

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailEventDataStore
metadata:
  name: org-events
  namespace: security-prod
spec:
  configRef: pci  # Uses PCI compliance profile
  multiRegionEnabled: true
  organizationEnabled: true
  retentionPeriod: 2557  # 7 years (FIXED_RETENTION maximum)
  terminationProtectionEnabled: true
  deletionPolicy: retain
  tags:
    compliance: pci-dss
    scope: organization
```

### Event Data Store with Advanced Event Selectors

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailEventDataStore
metadata:
  name: management-events-only
  namespace: security-prod
spec:
  configRef: general-policy
  multiRegionEnabled: true
  retentionPeriod: 90
  terminationProtectionEnabled: false
  advancedEventSelectors:
    - name: "management-events"
      fieldSelectors:
        - field: "eventCategory"
          equals: ["Management"]
    - name: "iam-and-sts-events"
      fieldSelectors:
        - field: "eventName"
          startsWith: ["CreateRole", "DeleteRole", "AssumeRole"]
  tags:
    event-type: management-only
```

### Event Data Store with S3 Data Events

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailEventDataStore
metadata:
  name: s3-data-events
  namespace: data-prod
spec:
  configRef: general-policy
  multiRegionEnabled: true
  retentionPeriod: 30
  terminationProtectionEnabled: true
  advancedEventSelectors:
    - name: "s3-data-events"
      fieldSelectors:
        - field: "resources.type"
          equals: ["AWS::S3::Object"]
  tags:
    event-type: s3-data
```

## Status Fields

Once a CloudTrailEventDataStore is reconciled, the following status fields are populated:

*   **`status.conditions`**: Standard Kubernetes conditions indicating reconciliation status.

Note: Unlike CloudTrailTrail, there are no `status.resourceName`, `status.namingStatus`, or `status.predictedArn` fields due to the naming exemption. The actual event data store ARN is available from the child ACK EventDataStore CR's `status.ackResourceMetadata.arn`.

## Advanced Event Selectors

Advanced event selectors enable fine-grained filtering of which events are ingested into the data store, reducing storage costs and query complexity.

**Common field values:**

*   `eventCategory`: `"Management"`, `"Data"`, `"Insight"`
*   `eventName`: Specific AWS API names (e.g., `"CreateRole"`, `"PutObject"`)
*   `resources.type`: AWS resource types (e.g., `"AWS::S3::Object"`, `"AWS::EC2::Instance"`)

**Example selectors:**

*   Management events only: `fieldSelectors: [{field: "eventCategory", equals: ["Management"]}]`
*   S3 data events: `fieldSelectors: [{field: "resources.type", equals: ["AWS::S3::Object"]}]`
*   Specific event names: `fieldSelectors: [{field: "eventName", startsWith: ["Assume", "Create"]}]`

## Deferred Features

The following features are currently out of scope and deferred to future phases:

*   **CloudTrail Lake Channels:** Multi-source event aggregation and advanced routing.
*   **Customer-managed KMS encryption:** Event data stores currently use AWS-managed encryption. Customer-managed KMS support awaits ACK CRD support.
*   **`billingMode` parameter:** The `billingMode` field (`FIXED_RETENTION_PRICING` vs. `EXTENDABLE_RETENTION_PRICING`) affects maximum retention but is not exposed in ACK v1.6.0. The RGD defaults to 2557-day maximum (FIXED_RETENTION).

## Cross-Provider Notes

*   **Event data stores:** Are unique to AWS CloudTrail Lake. GCP audit logs are analyzed via BigQuery export; Azure audit logs use Log Analytics workspaces.
*   **Advanced event selectors:** Are AWS-specific. GCP and Azure use fixed audit log categories with diagnostic settings filters.
*   **Naming:** Event data store ARNs are UUID-based and assigned by AWS. GCP and Azure resources typically use user-provided names.

## Related Resources

*   [CloudTrailConfig](cloudtrailconfig.md)
*   [CloudTrailTrail](cloudtrailtrail.md)
