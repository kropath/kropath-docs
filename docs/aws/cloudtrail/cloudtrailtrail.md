# CloudTrailTrail — API Activity Logging

CloudTrailTrail is a kropath resource for creating and managing AWS CloudTrail trails. A trail records API calls and events in your AWS environment and delivers log files to an S3 bucket, with optional integration to CloudWatch Logs for real-time streaming and SNS for notifications.

## Prerequisites and Setup

CloudTrailTrail resources require:

*   A **CloudTrailConfig** governance profile (defaults to `"general-policy"` if not specified).
*   An **S3 bucket** to receive trail logs. You can reference an existing bucket by name via `spec.s3BucketName`, or reference a kropath-managed S3Bucket CR via `spec.s3BucketRef`.
*   *(Optional)* A **KMS key** for log encryption. Provide via `spec.kmsKeyID` (direct key ARN/alias) or `spec.kmsKeyRef` (reference to a kropath-managed KMSKey CR).
*   *(Optional)* A **CloudWatch Logs log group** and **IAM role** for log delivery streaming.
*   *(Optional)* An **SNS topic** for delivery notifications.

## Configuration

### Core Fields

A CloudTrailTrail instance specifies:

*   **`configRef`** (string, default: `"general-policy"`): The CloudTrailConfig profile to use for governance. If the named profile does not exist, it falls back to `"general-policy"`.
*   **`nameOverride`** (string): Overrides the trail name derived from the naming template. Useful for migrating existing trails or bypassing naming conventions.
*   **`deletionPolicy`** (string, default: `"retain"`): Determines behavior when the trail CR is deleted:
    *   `"retain"`: The AWS CloudTrail trail persists after CR deletion.
    *   `"delete"`: The AWS CloudTrail trail is deleted when the CR is deleted.

### S3 Log Delivery

Exactly one of `s3BucketName` or `s3BucketRef` must be provided (or enforced via governance):

*   **`s3BucketName`** (string): The name of the S3 bucket where logs are delivered. Takes precedence if both fields are set.
*   **`s3BucketRef`** (string): The name of a kropath-managed `S3Bucket` CR in the same namespace. The RGD resolves the actual bucket name via `status.resourceName`.
*   **`s3KeyPrefix`** (string): An optional S3 key prefix prepended to all log file names (max 200 characters).

### Trail Scope

Control which events are logged and from which regions/accounts:

*   **`isMultiRegionTrail`** (boolean, tri-state): When `true`, the trail logs events from all AWS regions. When `false`, logs only the current region. When unset, governance decides.
*   **`isOrganizationTrail`** (boolean, tri-state): When `true`, logs events from all AWS accounts in your organization. When `false`, logs only your account. When unset, governance decides.
*   **`includeGlobalServiceEvents`** (boolean, tri-state): When `true`, includes global service events (IAM, STS). When `false`, excludes them. When unset, governance decides (defaults to `true`).

### Log Integrity and Encryption

*   **`enableLogFileValidation`** (boolean, tri-state): When `true`, CloudTrail generates digest files to validate log integrity. When unset, governance decides (defaults to `true`).
*   **`kmsKeyID`** (string): A KMS key ID, alias, or ARN for encrypting logs with Server-Side Encryption with KMS (SSE-KMS). Takes precedence if both key fields are set.
*   **`kmsKeyRef`** (string): The name of a kropath-managed `KMSKey` CR in the same namespace. The RGD resolves the actual key ID via `status.keyID`.

### CloudWatch Logs Delivery

Stream logs to CloudWatch Logs in real-time:

*   **`cloudWatchLogsLogGroupARN`** (string): The ARN of the CloudWatch Logs log group (e.g., `"arn:aws:logs:us-east-1:123456789012:log-group:/aws/cloudtrail:*"`).
*   **`cloudWatchLogsRoleARN`** (string): The ARN of an IAM role that CloudTrail assumes to deliver logs to CloudWatch Logs. Takes precedence if both role fields are set.
*   **`cloudWatchLogsRoleRef`** (string): The name of a kropath-managed `IAMRole` CR in the same namespace. The RGD resolves the actual role ARN via `status.roleArn`.

**Both `cloudWatchLogsLogGroupARN` and one of the role fields must be provided together, or both must be empty.** If only one is set, the AWS API will reject the trail.

### SNS Notifications

*   **`snsTopicName`** (string): The name of an SNS topic (not ARN) for delivery notifications. CloudTrail publishes a message to this topic each time a log file is delivered to S3.

### Metadata and Tags

*   **`tags`** (map<string,string>): Custom AWS tags applied to the trail. Merged with mandatory and default tags from governance.
*   **`syncedLabels`** (map<string,string>): Kubernetes labels mirrored as AWS resource tags (prefixed `aws.kropath.run/`).
*   **`syncedAnnotations`** (map<string,string>): Kubernetes annotations mirrored as AWS resource tags (prefixed `aws.kropath.run/`).

## Naming Conventions

Trail names are governed by the naming template specified in `CloudTrailConfig`:

*   **Default template:** `"{namespace}-{name}"` — combines your CR's namespace and name.
*   **Tokens supported:** `{name}`, `{namespace}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.<key>}` (missing tag → empty string).
*   **Constraints:** 3–128 characters, alphanumeric plus periods (`.`), underscores (`_`), and hyphens (`-`); must not be an IP address format.
*   **Immutability:** Trail names are immutable after creation. If you change `nameOverride` or the governing naming template, the RGD will reject the change.

Use `spec.nameOverride` to bypass the naming template for legacy or externally-managed trails.

## Governance Cascade

All boolean and string fields follow the ten-tier governance cascade:

1. **CloudTrailConfig `mandatory` tier** (highest priority)
2. **CloudTrailTrail `spec` instance override**
3. **CloudTrailConfig `defaults` tier** (lowest priority)

The RGD resolves each field by checking this cascade in order and applying the first non-nil/non-empty value found.

## Example CloudTrailTrail Resources

### Basic Trail with Direct S3 Bucket

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailTrail
metadata:
  name: api-audit-trail
  namespace: security-prod
spec:
  configRef: general-policy
  s3BucketName: "my-org-audit-logs"
  s3KeyPrefix: "trails/prod/"
  deletionPolicy: retain
  tags:
    team: security
    environment: production
```

### Trail with Cross-RGD S3Bucket and KMSKey References

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailTrail
metadata:
  name: compliance-trail
  namespace: security-prod
spec:
  configRef: security  # Uses the 'security' CloudTrailConfig profile
  s3BucketRef: "central-audit-bucket"  # References an S3Bucket CR
  s3KeyPrefix: "compliance/"
  kmsKeyRef: "audit-key"  # References a KMSKey CR
  isMultiRegionTrail: true
  enableLogFileValidation: true
  includeGlobalServiceEvents: true
  tags:
    compliance: pci
    retention: 7-years
```

### Trail with CloudWatch Logs Delivery

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailTrail
metadata:
  name: streaming-audit-trail
  namespace: analytics-prod
spec:
  configRef: general-policy
  s3BucketName: "audit-logs-bucket"
  kmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
  cloudWatchLogsLogGroupARN: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/cloudtrail:*"
  cloudWatchLogsRoleRef: "cloudtrail-cwl-role"  # References an IAMRole CR
  isMultiRegionTrail: true
  tags:
    monitoring: realtime
```

### Multi-Region Organization Trail with SNS

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudTrailTrail
metadata:
  name: org-central-trail
  namespace: security-prod
spec:
  configRef: pci  # Uses PCI compliance profile
  s3BucketName: "organization-audit-logs"
  s3KeyPrefix: "central/"
  kmsKeyID: "alias/organization-audit-key"
  isMultiRegionTrail: true
  isOrganizationTrail: true
  includeGlobalServiceEvents: true
  enableLogFileValidation: true
  snsTopicName: "cloudtrail-notifications"
  deletionPolicy: retain
  tags:
    compliance: pci-dss
    scope: organization
```

## Status Fields

Once a CloudTrailTrail is reconciled, the following status fields are populated:

*   **`status.resourceName`**: The effective trail name after template substitution.
*   **`status.namingStatus`**: Either `"valid"` or `"invalid-unresolved-tokens"` (if template tokens could not be resolved).
*   **`status.predictedArn`**: The predicted ARN of the trail: `"arn:aws:cloudtrail:<region>:<account-id>:trail/<name>"`.
*   **`status.conditions`**: Standard Kubernetes conditions indicating reconciliation status.

## Cross-RGD References

CloudTrailTrail supports referencing other kropath-managed resources:

*   **S3Bucket via `s3BucketRef`:** The RGD resolves the bucket name by reading `status.resourceName` from the referenced S3Bucket CR.
*   **KMSKey via `kmsKeyRef`:** The RGD resolves the key ID by reading `status.keyID` from the referenced KMSKey CR.
*   **IAMRole via `cloudWatchLogsRoleRef`:** The RGD resolves the role ARN by reading `status.roleArn` from the referenced IAMRole CR.

All references use label-based lookup (`aws.kropath.run/resource-name: <ref-name>`) within the same namespace.

## Cross-Provider Notes

*   **Trail names:** Are case-sensitive (unlike S3 bucket names which are lowercased).
*   **GCP and Azure:** Do not have a direct "trail" concept. GCP audit logs are automatic and routed via Cloud Logging; Azure activity logs are automatic. Equivalent functionality is implemented via export sinks (GCP) or diagnostic settings (Azure).
*   **CloudWatch Logs delivery:** Is AWS-specific. GCP routes logs via Cloud Logging sinks; Azure uses diagnostic settings.
*   **SNS notifications:** Are AWS-specific for CloudTrail delivery notifications.

## Related Resources

*   [CloudTrailConfig](cloudtrailconfig.md)
*   [CloudTrailEventDataStore](cloudtraileventdatastore.md)
*   [S3Bucket](../s3/s3.md)
*   [KMSKey](../kms/kmskey.md)
*   [IAMRole](../iam/iamrole.md)
