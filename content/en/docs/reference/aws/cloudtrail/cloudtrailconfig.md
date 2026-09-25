---
title: CloudTrailConfig Governance
description: CloudTrailConfig is the governance resource for the CloudTrail family.
doc_type: reference
---
# CloudTrailConfig Governance

CloudTrailConfig is the governance resource for the CloudTrail family. It defines per-profile mandatory and default settings that are consumed by both CloudTrailTrail and CloudTrailEventDataStore resources. Platform engineers use CloudTrailConfig to enforce organization-wide audit logging controls—such as mandatory multi-region trails, KMS encryption, and retention policies—while allowing teams to customize their audit logging within those constraints.

## Prerequisites and Setup

CloudTrailConfig is typically deployed once per namespace by platform administrators. Most clusters will have a single default profile (`general-policy`) suitable for general-purpose workloads, along with specialized profiles for compliance-heavy or highly restricted environments.

CloudTrailConfig integrates with:

*   **KropathConfig:** For org-wide governance that applies across all CloudTrail profiles. The `cloudtrail` section of `KropathConfig` provides blanket policies (e.g., mandatory multi-region trails) that override profile defaults.
*   **S3 Family:** When using `s3BucketRef` in CloudTrailTrail instances to reference S3 buckets managed via kropath S3Bucket CRs.
*   **KMS Family:** When using `kmsKeyRef` in CloudTrailTrail instances to reference KMS keys managed via kropath KMSKey CRs.
*   **IAM Family:** When using `cloudWatchLogsRoleRef` in CloudTrailTrail instances to reference IAM roles for CloudWatch Logs delivery.

## Configuration

CloudTrailConfig uses a governance model with two configuration tiers:

*   **`mandatory`:** Fields set here enforce strict policies that cannot be overridden by resource instances. If a mandatory field is set, the resource's corresponding field is ignored.
*   **`defaults`:** Fields set here provide baseline configurations that resource instances can override. They apply only when the resource's corresponding field is not explicitly set.

### Governance Fields

A CloudTrailConfig profile contains fields that apply to both CloudTrailTrail and CloudTrailEventDataStore resources:

#### Trail-Specific Fields

These fields govern CloudTrailTrail resources only; they are ignored by CloudTrailEventDataStore:

*   `isMultiRegionTrail` (boolean): When true (either mandatory or default), trails deliver logs from all AWS regions.
*   `enableLogFileValidation` (boolean): When true, CloudTrail generates digest files for log integrity validation.
*   `includeGlobalServiceEvents` (boolean): When true, global service events (IAM, STS) are included in logs.
*   `isOrganizationTrail` (boolean): When true, the trail logs events from all AWS accounts in your organization.
*   `s3BucketName` (string): S3 bucket name where trail logs are delivered. Empty string = no enforcement.
*   `s3KeyPrefix` (string): S3 key prefix prepended to all trail log file names.
*   `kmsKeyID` (string): KMS key ID, alias, or ARN for trail log encryption. Empty string = no encryption enforcement.
*   `namingTemplate` (string): Template for auto-generating trail names (e.g., `"{namespace}-{name}"`). Empty string = no mandatory template.

#### EventDataStore-Specific Fields

These fields govern CloudTrailEventDataStore resources only; they are ignored by CloudTrailTrail:

*   `multiRegionEnabled` (boolean): When true, the event data store collects events from all AWS regions.
*   `organizationEnabled` (boolean): When true, the event data store collects events from all AWS accounts in your organization.
*   `retentionPeriod` (integer): Number of days to retain events in the data store (7 to 2557 days, or up to 3653 with extended retention pricing).
*   `terminationProtectionEnabled` (boolean): When true, the event data store cannot be deleted.

#### Common Governance Fields

These fields apply to both CloudTrailTrail and CloudTrailEventDataStore:

*   `tags` (map<string,string>): AWS tags applied to all resources using this profile. Merged with instance-level tags and mandatory tags from KropathConfig.
*   `syncedLabels` (map<string,string>): Kubernetes labels mirrored as AWS resource tags (prefixed `aws.kropath.run/`).
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations mirrored as AWS resource tags (prefixed `aws.kropath.run/`).

### Ten-Tier Governance Cascade

kropath employs a ten-tier governance cascade (see ADR-010) to resolve effective configuration for CloudTrail resources. This cascade ensures that organizational-level policies take precedence, followed by profile-specific settings, and finally instance-level overrides.

The `kropath-controller` pre-merges all governance sources (from `KropathConfig` and `CloudTrailConfig`) into `status.effectiveConfig` on the namespaced `CloudTrailConfig` CR. Both `CloudTrailTrail` and `CloudTrailEventDataStore` RGDs read this `status.effectiveConfig` to determine the final, resolved settings.

**When to use `KropathConfig.cloudtrail` vs. `CloudTrailConfig`:**

*   **`KropathConfig.cloudtrail`:** Used for blanket, organization-wide governance that applies across *all* CloudTrail profiles. For example, setting `KropathConfig.mandatory.cloudtrail.isMultiRegionTrail: true` would force all trails in the organization to be multi-region, regardless of the `CloudTrailConfig` profile they use.
*   **`CloudTrailConfig`:** Used for per-profile governance. For instance, a `pci` `CloudTrailConfig` profile might mandate a specific KMS key only for resources using that profile, allowing other profiles more flexibility.

**Boolean Governance Semantics:** For boolean fields, `false` in a `mandatory` or `defaults` tier means "follow the next tier in the cascade" rather than explicitly disabling the control. To explicitly disable a control (e.g., allow single-region trails when the default mandates multi-region), a dedicated `CloudTrailConfig` profile must be created with `mandatory.<field>: false`, and resources must reference this profile via `spec.configRef`.

### Predefined Profile Examples

Standard profiles for common scenarios:

*   **`general-policy`** (default): Sensible defaults for most workloads.
    *   Defaults: `enableLogFileValidation: true`, `includeGlobalServiceEvents: true`, `namingTemplate: "{namespace}-{name}"`
    *   Event Data Store retention: 2557 days (approximately 7 years)

*   **`security`**: Mandatory security controls for highly sensitive workloads.
    *   Mandatory: `isMultiRegionTrail: true`, `enableLogFileValidation: true`, KMS encryption required
    *   Defaults: Org-wide S3 bucket, high-assurance KMS key

*   **`pci`**: PCI-DSS compliance profile.
    *   Mandatory: `isMultiRegionTrail: true`, `enableLogFileValidation: true`, organization trail, termination protection on event data stores
    *   Mandatory retention: 2557 days (7-year minimum)

## Example CloudTrailConfig Profiles

### General Policy Profile

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
    # Trail defaults
    enableLogFileValidation: true
    includeGlobalServiceEvents: true
    isMultiRegionTrail: false
    isOrganizationTrail: false
    namingTemplate: "{namespace}-{name}"
    # EventDataStore defaults
    multiRegionEnabled: false
    organizationEnabled: false
    retentionPeriod: 2557
    terminationProtectionEnabled: true
    tags:
      managed-by: kropath
```

### Security Profile with Mandatory Controls

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
    # Enforce multi-region trails and log validation
    isMultiRegionTrail: true
    enableLogFileValidation: true
    # Central audit S3 bucket
    s3BucketName: "org-cloudtrail-logs"
    s3KeyPrefix: "security/"
    # Organization-managed KMS key
    kmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
    # Enforce termination protection on event data stores
    terminationProtectionEnabled: true
    tags:
      compliance: security
      environment: production
  defaults:
    # Default retention period
    retentionPeriod: 2557
    namingTemplate: "security-{namespace}-{name}"
```

## Label Requirement

Every `CloudTrailConfig` CR **must** carry a label to enable resource lookup via labelSelector:

```yaml
metadata:
  labels:
    aws.kropath.run/resource-name: <profile-name>
```

CloudTrailTrail and CloudTrailEventDataStore resources locate their governance config via this label, not by metadata name.

## Cross-Provider Notes

*   **GCP and Azure:** Each cloud provider would define its own audit logging governance CRD (e.g., `AuditLogConfig` for GCP). The governance model is consistent across providers, but field names reflect provider-specific audit APIs.
*   **Mandatory vs. Defaults Semantics:** The boolean semantics (false = "not enforced") allow platform teams to override defaults without explicitly disabling controls. This pattern is shared across all kropath governance CRDs.

## Related Resources

*   [CloudTrailTrail](cloudtrailtrail.md)
*   [CloudTrailEventDataStore](cloudtraileventdatastore.md)
