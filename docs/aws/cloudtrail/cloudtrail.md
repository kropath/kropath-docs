# AWS CloudTrail

The AWS CloudTrail family within kropath provides abstractions for managing Amazon CloudTrail resources for comprehensive API activity logging. It enables platform engineers to enforce organization-wide audit logging controls—such as multi-region trail configuration, log integrity validation, and encryption mandates—while allowing application teams to provision and configure CloudTrail trails and event data stores for their specific compliance and auditing needs. The family supports both traditional CloudTrail trails (for AWS API activity logging with S3 delivery) and CloudTrail Lake event data stores (for queryable event storage and advanced filtering).

## Prerequisites and Setup

CloudTrail resources benefit from integration with other kropath families for complete audit logging infrastructure:

*   **S3 Family:** For specifying S3 buckets to receive trail logs via the `S3Bucket` CRD or direct bucket references (`s3BucketRef` / `s3BucketName`).
*   **KMS Family:** For referencing AWS KMS keys to enable log encryption via the `KMSKey` CRD or direct key references (`kmsKeyRef` / `kmsKeyID`).
*   **IAM Family:** For specifying IAM roles to grant CloudWatch Logs permissions via the `IAMRole` CRD or direct role ARN references.

No compute or networking resources are required to provision CloudTrail resources—they operate independently and can be created in any cluster namespace.

## CloudTrailConfig Governance Model

Kropath's CloudTrail configuration is governed through two resource layers:

### CloudTrailConfig: The Governance CRD

`CloudTrailConfig` is a custom resource definition that defines per-profile governance settings for the entire CloudTrail family. Each `CloudTrailConfig` CR contains mandatory and defaults tiers that control behavior across both `CloudTrailTrail` and `CloudTrailEventDataStore` resources.

Every organization should define at least one `CloudTrailConfig` profile (typically named `general-policy`). Multiple profiles allow different teams or compliance zones to enforce different baseline settings.

#### CloudTrailConfig Core Fields

`CloudTrailConfig` organizes fields into `spec.mandatory` and `spec.defaults` sections. A field set in `mandatory` cannot be overridden by individual resource instances. A field set in `defaults` applies to instances that do not specify a value.

**Common governance fields** (apply to both trails and event data stores):

*   `tags` (map<string,string>): AWS tags applied to all resources using this profile. Merged with instance-level tags via the governance cascade.
*   `syncedLabels` (map<string,string>): Kubernetes labels mirrored as AWS tags and prefixed with `aws.kropath.run/`.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations mirrored as AWS tags and prefixed with `aws.kropath.run/`.
*   `namingTemplate` (string): Template for generating CloudTrailTrail names. Default: `{namespace}-{name}`. Supports dynamic tokens: `{name}`, `{namespace}`, `{account_id}`, `{region}`, `{configRef}`, and tag references like `{tag.environment}`.

**Trail-specific governance fields** (apply only to `CloudTrailTrail`):

*   `isMultiRegionTrail` (boolean): Whether trails default to or mandate multi-region logging. Default (in defaults tier): `false` (single region).
*   `enableLogFileValidation` (boolean): Whether to enforce or default to digest file validation for log integrity. Default (in defaults tier): `true`.
*   `includeGlobalServiceEvents` (boolean): Whether to include IAM and other global service events. Default (in defaults tier): `true`.
*   `isOrganizationTrail` (boolean): Whether trails span an organization or single account. Default (in defaults tier): `false`.
*   `s3BucketName` (string): Default S3 bucket for log delivery. Empty string (`""`) means "not enforced."
*   `s3KeyPrefix` (string): Default key prefix for S3 logs.
*   `kmsKeyID` (string): Default KMS key ID or ARN for log encryption.

**Event Data Store-specific governance fields** (apply only to `CloudTrailEventDataStore`):

*   `multiRegionEnabled` (boolean): Whether event data stores default to or mandate multi-region collection. Default (in defaults tier): `false`.
*   `organizationEnabled` (boolean): Whether event data stores span an organization or single account. Default (in defaults tier): `false`.
*   `retentionPeriod` (integer, days): How long to retain events. Minimum 7 days, maximum 3653 (or 2557 for fixed-retention mode). Default (in defaults tier): `2557` (~7 years).
*   `terminationProtectionEnabled` (boolean): Whether to prevent deletion of event data stores. Default (in defaults tier): `true`.

#### Boolean Governance Semantics

For boolean fields, `false` in the `mandatory` tier means "not enforced" (the next cascade tier decides), not "explicitly disabled." To enforce single-region trails when a defaults tier sets `isMultiRegionTrail: true`, create a profile with `mandatory.isMultiRegionTrail: false`, and instances must reference this profile to override.

#### Profile Examples

*   **`general-policy`** (recommended starting point): Sensible defaults for most organizations. Enables log validation, includes global service events, defaults to single-region trails, defaults to 7-year retention for event data stores.
    
    ```yaml
    apiVersion: aws.kropath.run/v1alpha1
    kind: CloudTrailConfig
    metadata:
      name: general-policy
      namespace: kro-system
      labels:
        aws.kropath.run/resource-name: general-policy
    spec:
      defaults:
        enableLogFileValidation: true
        includeGlobalServiceEvents: true
        retentionPeriod: 2557
        terminationProtectionEnabled: true
        namingTemplate: "{namespace}-{name}"
    ```

*   **`security`** (security team enforcement): Mandatory multi-region trails, digest validation, and KMS encryption. Ensures all trails meet baseline security controls.
    
    ```yaml
    apiVersion: aws.kropath.run/v1alpha1
    kind: CloudTrailConfig
    metadata:
      name: security
      namespace: kro-system
      labels:
        aws.kropath.run/resource-name: security
    spec:
      mandatory:
        isMultiRegionTrail: true
        enableLogFileValidation: true
        kmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        s3BucketName: "org-audit-logs"
    ```

*   **`pci`** (PCI-DSS compliance): Strict controls for regulated workloads. Mandates multi-region organization trails, digest validation, specific KMS encryption, and extended retention.

### KropathConfig CloudTrail Section

Organization-wide governance can be specified in `KropathConfig.spec.mandatory.cloudtrail` and `KropathConfig.spec.defaults.cloudtrail` to apply blanket settings across all CloudTrailConfig profiles:

*   `isMultiRegionTrail` (boolean): Org-wide setting for multi-region trail coverage.
*   `enableLogFileValidation` (boolean): Org-wide enforcement of digest validation.
*   `retentionPeriod` (integer): Org-wide minimum retention for event data stores.

KropathConfig settings are merged into the ten-tier cascade at levels 1–2 (mandatory) and 8–9 (defaults), while per-profile `CloudTrailConfig` settings govern levels 3–4 (mandatory) and 6–7 (defaults).

## CloudTrailTrail Usage Guide

`CloudTrailTrail` is a Kubernetes resource that provisions an AWS CloudTrail trail. Trails record API calls across your AWS account and (optionally) organization, deliver logs to S3, validate log integrity, and optionally stream logs to CloudWatch.

### Creating a Basic Trail

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailTrail
metadata:
  name: api-audit
  namespace: platform
spec:
  configRef: general-policy
  s3BucketName: org-audit-logs
```

This trail uses the `general-policy` profile and delivers logs to the `org-audit-logs` S3 bucket.

### CloudTrailTrail Core Fields

*   `configRef` (string, default: `"general-policy"`): Selects the `CloudTrailConfig` profile to use for governance. Falls back to `general-policy` if the named profile does not exist.
*   `nameOverride` (string): Bypasses the naming template. If set, the trail name is `nameOverride` directly (subject to AWS CloudTrail naming constraints).
*   `deletionPolicy` (string, default: `"retain"`): Behavior when the CR is deleted. Options:
    *   `"retain"`: The AWS trail continues to exist and deliver logs.
    *   `"delete"`: The AWS trail is deleted. Logs already in S3 remain.

#### S3 Log Delivery

CloudTrail requires an S3 bucket to receive API activity logs. Specify either a direct bucket name or a reference to a kropath `S3Bucket` CR:

*   `s3BucketName` (string): Direct S3 bucket name. Mutually exclusive with `s3BucketRef`. Example: `"org-audit-logs"`.
*   `s3BucketRef` (string): Name of a local `S3Bucket` CR in the same namespace. Mutually exclusive with `s3BucketName`. The RGD resolves the bucket name from the `S3Bucket` status. Example: `"audit-logs-bucket"` (references `S3Bucket` named `audit-logs-bucket`).
*   `s3KeyPrefix` (string): Optional prefix for S3 log objects. Max 200 characters. Example: `"cloudtrail/2024/"`. Empty string (default) means logs are stored at the bucket root.

#### Trail Scope and Coverage

*   `isMultiRegionTrail` (boolean or nil): Whether the trail covers all AWS regions or just the specified region.
    *   `true`: Trail operates in all regions; receives API activity from globally distributed resources.
    *   `false`: Trail covers only the specified region.
    *   `nil` (default): Governance cascade decides. Defaults to `false` (single region) if no governance is set.

*   `isOrganizationTrail` (boolean or nil): Whether the trail applies to an entire AWS Organization or a single account.
    *   `true`: Trail is organization-wide (requires `arn:aws:organizations::<root-account-id>::o-<org-id>` membership and proper IAM permissions).
    *   `false`: Trail is account-scoped.
    *   `nil`: Governance cascade decides. Defaults to `false` if not set.

*   `includeGlobalServiceEvents` (boolean or nil): Whether to include AWS global service events (IAM, STS, etc.) or only region-specific events.
    *   `true`: Include global service events.
    *   `false`: Region-specific events only.
    *   `nil`: Governance cascade decides. Defaults to `true` if not set.

#### Log Integrity Validation

*   `enableLogFileValidation` (boolean or nil): Whether CloudTrail generates digest files to validate log file integrity.
    *   `true`: Digest files enabled (recommended for compliance).
    *   `false`: No digest files.
    *   `nil`: Governance cascade decides. Defaults to `true` if not set.

#### Encryption

CloudTrail log files can be encrypted with AWS KMS. Specify either a direct key ID/ARN or reference a kropath `KMSKey` CR:

*   `kmsKeyID` (string): Direct KMS key ID, alias, or ARN. Example: `"arn:aws:kms:us-east-1:123456789012:key/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"`. Mutually exclusive with `kmsKeyRef`.
*   `kmsKeyRef` (string): Name of a local `KMSKey` CR. The RGD resolves the key ID from the `KMSKey` status. Mutually exclusive with `kmsKeyID`.

#### CloudWatch Logs Delivery (Optional)

Stream CloudTrail logs to CloudWatch for near-real-time monitoring:

*   `cloudWatchLogsLogGroupARN` (string): ARN of the CloudWatch Logs log group. Example: `"arn:aws:logs:us-east-1:123456789012:log-group:/aws/cloudtrail/org-audit:*"`. Both this field and one of the role fields are required together.
*   `cloudWatchLogsRoleARN` (string): ARN of the IAM role granting CloudWatch Logs write permissions. Mutually exclusive with `cloudWatchLogsRoleRef`.
*   `cloudWatchLogsRoleRef` (string): Name of a local `IAMRole` CR. The RGD resolves the role ARN from the `IAMRole` status. Mutually exclusive with `cloudWatchLogsRoleARN`.

#### SNS Notifications (Optional)

Receive SNS notifications whenever CloudTrail delivers a log file to S3:

*   `snsTopicName` (string): Name of an SNS topic to notify. Max 256 characters. Topic must exist and have permissions granting CloudTrail `SNS:Publish`.

#### Metadata and Tags

*   `tags` (map<string,string>): Custom AWS tags. Merged with governance tags via the cascade.
*   `syncedLabels` (map<string,string>): Kubernetes labels mirrored as AWS tags (prefixed with `aws.kropath.run/`).
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations mirrored as AWS tags (prefixed with `aws.kropath.run/`).

### CloudTrailTrail Naming

Trail names are governed by the naming convention (default: `{namespace}-{name}`, allowing 3–128 characters, alphanumeric plus `.`, `_`, `-`). The `status.predictedArn` field shows the expected ARN: `arn:aws:cloudtrail:<region>:<account-id>:trail/<effective-name>`.

Trail names are immutable after creation—changing the naming template or `nameOverride` after the trail is created will not update the existing AWS trail.

### Example CloudTrailTrail Resources

**Single-region trail with S3 and digest validation:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailTrail
metadata:
  name: standard-audit
  namespace: platform
spec:
  configRef: general-policy
  s3BucketName: org-audit-logs
  s3KeyPrefix: "trails/"
  isMultiRegionTrail: false
  enableLogFileValidation: true
  includeGlobalServiceEvents: true
  tags:
    team: platform
    compliance: sox
```

**Multi-region organization trail with KMS encryption and CloudWatch Logs:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailTrail
metadata:
  name: org-secure-trail
  namespace: platform
spec:
  configRef: security
  s3BucketRef: audit-bucket
  kmsKeyRef: org-audit-key
  isMultiRegionTrail: true
  isOrganizationTrail: true
  enableLogFileValidation: true
  cloudWatchLogsLogGroupARN: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/cloudtrail/org:*"
  cloudWatchLogsRoleRef: cloudtrail-cwl-role
  deletionPolicy: retain
  tags:
    compliance: pci-dss
```

## CloudTrailEventDataStore Usage Guide

`CloudTrailEventDataStore` is a Kubernetes resource that provisions an AWS CloudTrail Lake event data store. Event data stores store CloudTrail events in queryable format (AWS CloudTrail Lake) with advanced filtering, configurable retention, and termination protection.

Unlike trails (which deliver logs to S3), event data stores store events in AWS-managed CloudTrail Lake infrastructure, allowing SQL-based queries via the AWS API or console.

### Creating a Basic Event Data Store

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailEventDataStore
metadata:
  name: api-analytics
  namespace: platform
spec:
  configRef: general-policy
  multiRegionEnabled: false
  retentionPeriod: 365
```

This event data store uses the `general-policy` profile, collects events from a single region, and retains events for 365 days.

### CloudTrailEventDataStore Core Fields

*   `configRef` (string, default: `"general-policy"`): Selects the `CloudTrailConfig` profile. Falls back to `general-policy` if not found.
*   `deletionPolicy` (string, default: `"retain"`): Behavior on CR deletion:
    *   `"retain"`: The event data store continues to exist and retain events.
    *   `"delete"`: The event data store is deleted; events are lost.

#### Scope and Coverage

*   `multiRegionEnabled` (boolean or nil): Whether the event data store collects events from all AWS regions.
    *   `true`: Multi-region (global) event collection.
    *   `false`: Single region only.
    *   `nil`: Governance cascade decides. Defaults to `false` if not set.

*   `organizationEnabled` (boolean or nil): Whether the event data store spans an AWS Organization.
    *   `true`: Organization-wide event collection.
    *   `false`: Single account only.
    *   `nil`: Governance cascade decides. Defaults to `false` if not set.

#### Retention and Protection

*   `retentionPeriod` (integer or nil, days): How long to retain events. Minimum 7 days, maximum 3653 (or 2557 for fixed-retention mode).
    *   If set to a value: Events older than that many days are deleted.
    *   `nil`: Governance cascade decides. Defaults to 2557 days (~7 years) if not set.

*   `terminationProtectionEnabled` (boolean or nil): Prevent accidental deletion of the event data store.
    *   `true`: Deletion is prevented.
    *   `false`: Deletion is allowed.
    *   `nil`: Governance cascade decides. Defaults to `true` if not set.

#### Event Filtering (Advanced Event Selectors)

Advanced event selectors allow fine-grained filtering of which events are stored in the event data store. Up to 5 selectors can be defined:

*   `advancedEventSelectors` (array of objects): Each selector contains:
    *   `name` (string, optional): Display name for the selector.
    *   `fieldSelectors` (array of objects, required): Conditions to match events:
        *   `field` (string): Event field (e.g., `"eventCategory"`, `"eventName"`, `"resources.type"`).
        *   `equals` (array of strings): Event field values that match.
        *   `notEquals`, `startsWith`, `notStartsWith`, `endsWith`, `notEndsWith`: Alternative matchers.

**Event Selector Examples:**

Management events only (API calls):
```yaml
- fieldSelectors:
  - field: eventCategory
    equals: ["Management"]
```

S3 data events:
```yaml
- fieldSelectors:
  - field: eventCategory
    equals: ["Data"]
  - field: resources.type
    equals: ["AWS::S3::Object"]
```

No selectors (default—capture all events):
```yaml
advancedEventSelectors: []
```

#### Metadata and Tags

*   `tags` (map<string,string>): Custom AWS tags. Merged with governance tags.
*   `syncedLabels` (map<string,string>): Kubernetes labels mirrored as AWS tags.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations mirrored as AWS tags.

### CloudTrailEventDataStore Naming

Event data stores do not follow the standard naming convention (KRO-236). AWS assigns opaque, UUID-based ARNs: `arn:aws:cloudtrail:<region>:<account-id>:eventdatastore/<uuid>`. The CR name is not part of the cloud identifier. The `status` does not include `resourceName` or `predictedArn` fields.

### Example CloudTrailEventDataStore Resources

**Single-region event data store with management events only:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailEventDataStore
metadata:
  name: management-events
  namespace: platform
spec:
  configRef: general-policy
  multiRegionEnabled: false
  retentionPeriod: 365
  advancedEventSelectors:
  - name: management
    fieldSelectors:
    - field: eventCategory
      equals: ["Management"]
  tags:
    purpose: api-auditing
```

**Multi-region organization event data store with extended retention and termination protection:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailEventDataStore
metadata:
  name: org-data-lake
  namespace: platform
spec:
  configRef: security
  multiRegionEnabled: true
  organizationEnabled: true
  retentionPeriod: 2557
  terminationProtectionEnabled: true
  advancedEventSelectors:
  - name: management-events
    fieldSelectors:
    - field: eventCategory
      equals: ["Management"]
  - name: s3-data-events
    fieldSelectors:
    - field: eventCategory
      equals: ["Data"]
    - field: resources.type
      equals: ["AWS::S3::Object"]
  deletionPolicy: retain
  tags:
    compliance: pci-dss
    team: security
```

## Cross-Family Integrations

CloudTrail integrates seamlessly with other kropath families:

### S3 Bucket References

Use `S3Bucket` CRs to manage the S3 bucket receiving CloudTrail logs:

```yaml
# Define an S3 bucket in kropath
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: audit-logs
  namespace: platform
spec:
  blockPublicAccess: true
  versioning: Enabled
  tags:
    purpose: cloudtrail-logs

---
# Reference it in a trail
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailTrail
metadata:
  name: main-trail
  namespace: platform
spec:
  s3BucketRef: audit-logs
```

### KMS Key References

Use `KMSKey` CRs for trail log encryption:

```yaml
# Define a KMS key
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: cloudtrail-key
  namespace: platform
spec:
  keyPolicy: # ... (defined via PolicyDocument)

---
# Reference it in a trail
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailTrail
metadata:
  name: encrypted-trail
  namespace: platform
spec:
  kmsKeyRef: cloudtrail-key
  s3BucketName: org-audit-logs
```

### IAM Role References

Use `IAMRole` CRs for CloudWatch Logs permissions:

```yaml
# Define an IAM role (simplified example)
apiVersion: aws.kropath.run/v1alpha1
kind: IAMRole
metadata:
  name: cloudtrail-cwl-role
  namespace: platform
spec:
  # AssumeRolePolicyDocument grants CloudTrail service permission

---
# Reference it in a trail
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailTrail
metadata:
  name: monitored-trail
  namespace: platform
spec:
  cloudWatchLogsLogGroupARN: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/cloudtrail/api:*"
  cloudWatchLogsRoleRef: cloudtrail-cwl-role
```

## Governance Cascade for Platform Engineers

The CloudTrail governance cascade merges settings from three sources (in priority order):

1. **KropathConfig mandatory** (org-wide enforcement): Highest priority.
2. **CloudTrailConfig mandatory** (profile-specific enforcement): Overrides defaults.
3. **Resource instance fields**: User-specified overrides if permitted.
4. **CloudTrailConfig defaults** (profile-specific defaults): Fallback values.
5. **KropathConfig defaults** (org-wide defaults): Lowest priority.

For example, if `KropathConfig.mandatory.cloudtrail.isMultiRegionTrail: true`, all trails are multi-region, regardless of resource or profile settings. If a `CloudTrailConfig` profile sets `mandatory.s3BucketName: "org-audit-logs"`, no trail using that profile can override the S3 bucket.

Platform engineers can enforce compliance by:

*   Setting mandatory fields in `CloudTrailConfig` profiles for strict controls (e.g., mandatory digest validation, mandatory multi-region coverage for production).
*   Creating separate profiles for different compliance zones (e.g., `general-policy` for general workloads, `pci` for payment-processing systems).
*   Using `KropathConfig.mandatory` for org-wide non-negotiable controls (e.g., all trails must be multi-region; all logs must use KMS encryption).

## Out-of-Scope (Deferred)

The following features are not available in this phase and are tracked for future work:

*   **CloudTrail Insights**: Automated anomaly detection for unusual account activity. Deferred to P1.
*   **CloudTrail Lake Channels**: Integration with analytics tools (e.g., Datadog, Sumo Logic). Deferred to P2+.
*   **Customer-Managed KMS for Event Data Stores**: Direct KMS encryption control for event data stores. Awaiting ACK support.
*   **Event Data Store `billingMode`**: Control between fixed-retention (1–2557 days) and extended-retention (up to 3653 days) modes. Not exposed in ACK CloudTrail v1.6.0.
*   **GCP and Azure equivalents**: Cloud Logging (GCP) and Azure Activity Log integrations deferred to respective provider families.

## Requirements and Cluster Setup

### Cluster Prerequisites

*   Kubernetes cluster running kropath (with `kropath-controller` deployed).
*   Appropriate AWS IAM permissions for the cluster's service account:
    *   CloudTrail trail and event data store create/read/update/delete.
    *   S3 bucket read (if using `S3Bucket` references).
    *   KMS key read (if using `KMSKey` references).
    *   IAM role read (if using `IAMRole` references).

### KropathConfig Additions

If using org-wide CloudTrail governance, define the `cloudtrail` section in your `KropathConfig`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: config
  namespace: kro-system
spec:
  mandatory:
    cloudtrail:
      isMultiRegionTrail: true
      enableLogFileValidation: true
  defaults:
    cloudtrail:
      isMultiRegionTrail: false
      retentionPeriod: 2557
```

### CloudTrailConfig Deployment

Define at least one `CloudTrailConfig` profile (recommended: `general-policy`):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  defaults:
    enableLogFileValidation: true
    includeGlobalServiceEvents: true
    retentionPeriod: 2557
    terminationProtectionEnabled: true
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
```
