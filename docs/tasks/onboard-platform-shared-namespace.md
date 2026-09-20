---
type: task
---

# Onboard the platform-shared namespace

## Why this matters

As a platform team, you need a shared namespace to serve as the foundation for all other teams in your organization. The data team, payments team, analytics team, and every other tenant needs a consistent place to onboard from — and a working central-logging bucket plus artifacts bucket pair to build on.

Without a shared namespace and its dedicated resources:
- Teams lack a standard location for platform-wide logging and artifact storage
- Each team reinvents observability and artifact management independently (duplication, inconsistency)
- Platform operations become fragmented, making troubleshooting and compliance harder

This task walks you through onboarding a Kubernetes namespace for platform-shared resources — a namespace that hosts shared AWS resources such as central logging buckets and artifact storage. Once this foundation is in place, individual teams can onboard to kropath and access these shared resources as part of their standard setup.

## Before you begin

- You have a working kropath cluster in AWS with the kropath-controller and ACK (AWS Controllers for Kubernetes) installed
- You have `kubectl` configured to access the cluster
- You have AWS credentials configured with permissions to create S3 buckets and IAM resources in the target account(s)
- Platform teams have created one or more `AWSS3Config` governance profiles in the `kro-system` namespace (e.g., `general-policy`, `strict`)
- The namespace onboarding template has been prepared and is ready to apply to your cluster

## Goal

You will:

1. Create the `platform-shared` Kubernetes namespace
2. Apply the namespace onboarding template (KropathConfig and local resource-family configuration)
3. Create shared platform resources: a central logging bucket and artifact storage buckets
4. Verify that resources are ready in Kubernetes and exist in AWS

## Step 1: Create the namespace with the onboarding template

The namespace onboarding template provides baseline configurations for cross-account resource management. Apply the template manifest to create the `platform-shared` namespace with all required local configurations:

```bash
kubectl apply -f platform-shared-namespace-template.yaml
```

The template includes:

1. **Kubernetes Namespace** with annotations that enable ACK to manage cross-account resources (per ADR-019)
2. **KropathConfig** (a cluster-wide singleton in `kro-system` that governs organization-wide settings)
3. **Local resource-family configuration** (e.g., labels or namespace-scoped defaults as needed)

Verify the namespace was created:

```bash
kubectl get namespace platform-shared
kubectl describe namespace platform-shared
```

Expected: The namespace exists with ACK cross-account annotations visible in the output.

## Step 2: Create the shared platform resources

Once the namespace is ready, create the S3 resources that platform services depend on. Reference an existing `AWSS3Config` governance profile (e.g., `general-policy` or `strict`) via `configRef`.

### Central Logging Bucket

Create a central bucket for platform-wide log aggregation:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: central-logging
  namespace: platform-shared
spec:
  # Reference a governance profile created by platform teams
  configRef: general-policy
  
  # Override bucket naming to ensure global uniqueness
  nameOverride: "central-logging-{account_id}"
  
  # Configure versioning
  versioning: "Enabled"
  
  # Configure encryption (subject to governance cascade with AWSS3Config)
  encryption:
    algorithm: "aws:kms"
    kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/your-kms-key-id"
    bucketKeyEnabled: true
  
  # Control public access (subject to governance cascade)
  blockPublicAccess: true
  
  # Retention and management
  deletionPolicy: retain
  
  # Resource tags
  tags:
    purpose: central-logging
    team: platform
```

### Artifact Storage Buckets

Create buckets for build artifacts and shared data:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: artifacts
  namespace: platform-shared
spec:
  # Reference the governance profile
  configRef: general-policy
  
  # Override bucket naming for consistency across accounts
  nameOverride: "artifacts-{account_id}"
  
  # Enable versioning for artifact history
  versioning: "Enabled"
  
  # Configure encryption
  encryption:
    algorithm: "aws:kms"
    kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/your-kms-key-id"
    bucketKeyEnabled: true
  
  # Block public access
  blockPublicAccess: true
  
  # Retention and management
  deletionPolicy: retain
  
  # Tags
  tags:
    purpose: artifacts
    team: platform
```

Apply the resources:

```bash
kubectl apply -f central-logging-bucket.yaml
kubectl apply -f artifacts-bucket.yaml
```

Monitor the resource creation:

```bash
kubectl get s3bucket -n platform-shared -w
```

Wait until both buckets show `Ready` or `Synced` status.

## Step 3: Verify resources in Kubernetes

Check that the S3 buckets have been created and are ready:

```bash
kubectl describe s3bucket central-logging -n platform-shared
kubectl describe s3bucket artifacts -n platform-shared
```

Look for:

- `Status: Ready` or `Status: Synced`
- `Status.Conditions[].Reason: Success`
- `Status.BucketARN` — the ARN of the created bucket

Example output:

```
Name:         central-logging
Namespace:    platform-shared
Status:
  Conditions:
  - LastTransitionTime: 2026-09-20T15:30:42Z
    Reason:              ACKResourceSynced
    Status:              "True"
    Type:                ACK.Synced
  BucketARN: arn:aws:s3:::central-logging-123456789012-us-east-1
  BucketName: central-logging-123456789012-us-east-1
```

## Step 4: Verify resources in AWS

Use the AWS CLI to confirm that the buckets exist and are configured correctly in AWS.

### Check that buckets exist

```bash
aws s3api head-bucket --bucket central-logging-123456789012-us-east-1
aws s3api head-bucket --bucket artifacts-123456789012-us-east-1
```

Expected: No error output (exit code 0).

### Verify bucket settings

Check encryption:

```bash
aws s3api get-bucket-encryption \
  --bucket central-logging-123456789012-us-east-1

# Expected output shows:
# ServerSideEncryptionConfiguration:
#   Rules:
#   - ApplyServerSideEncryptionByDefault:
#       SSEAlgorithm: aws:kms
```

Check public access blocking:

```bash
aws s3api get-public-access-block \
  --bucket central-logging-123456789012-us-east-1

# Expected output shows:
# PublicAccessBlockConfiguration:
#   BlockPublicAcls: true
#   BlockPublicPolicy: true
#   IgnorePublicAcls: true
#   RestrictPublicBuckets: true
```

Check versioning:

```bash
aws s3api get-bucket-versioning \
  --bucket artifacts-123456789012-us-east-1

# Expected output shows:
# Status: Enabled
```

Check tags:

```bash
aws s3api get-bucket-tagging \
  --bucket central-logging-123456789012-us-east-1

# Expected output shows tags matching the CR spec
```

## Step 5: Verify namespace annotations (if applicable)

If the cluster manages resources across multiple AWS accounts, verify that the namespace has the correct cross-account annotations applied by the onboarding template:

```bash
# List the namespace annotations
kubectl get namespace platform-shared -o jsonpath='{.metadata.annotations}' | jq .

# Expected annotations:
# - aws.kropath.run/global-config-namespace: shared
# - services.k8s.aws/owner-account-id: <account-id>
# - services.k8s.aws/default-region: <region>
```

These annotations enable ACK to manage resources across accounts and regions. For details on how these annotations work, see ADR-019: Cross-account resource management in kropath-core.

## Troubleshooting

### Buckets are stuck in a pending state

Check the resource status and events:

```bash
kubectl describe s3bucket central-logging -n platform-shared
kubectl logs -n ack-system -l app.kubernetes.io/name=ack-system
```

Common causes:
- **Naming conflict**: The bucket name already exists globally in AWS. Verify the `nameOverride` template is unique.
- **IAM permissions**: The cross-account role may lack S3 permissions. Check IAM policies.
- **ACK not running**: Verify ACK is running in the cluster: `kubectl get pods -n ack-system`.

### Buckets are ready in Kubernetes but not visible in AWS

- Verify the account and region using the bucket ARN in the status
- Check IAM permissions for the user viewing the bucket
- Confirm the namespace annotations (especially `services.k8s.aws/owner-account-id`) match the target account

### Bucket names do not match the naming template

The naming override template uses `{account_id}` tokens, which are interpolated at creation time. Verify:

```bash
# Check the actual bucket name created
kubectl get s3bucket -n platform-shared -o jsonpath='{.items[*].status.bucketName}'

# Confirm it matches the expected template
# central-logging-<account_id>
# artifacts-<account_id>
```

If you need region information in the bucket name, set `spec.region` in your S3Bucket CR and include the region value in the `nameOverride` as a literal string (e.g., `central-logging-us-east-1-{account_id}`).

## Next steps

Once the namespace and platform resources are onboarded and verified:

1. **Grant access** — Set up IAM policies and bucket policies so other services can use these resources
2. **Monitor** — Set up CloudWatch alarms for bucket metrics, access patterns, and lifecycle actions
3. **Document** — Record the bucket ARNs and usage patterns for platform consumers

## Related documentation

- [AWS S3 Buckets resource documentation](../aws/s3/s3.md)
- [AWSS3Config governance configuration](../aws/s3/s3.md#awss3config-governance-model)

For architectural and governance details, see the design documents in kropath-core:

- ADR-019: Cross-account resource management
- ADR-015: Consolidated platform decisions (§5.3 governance cascade)
- ADR-010: kropath-controller effective-config cascade

## Reference

This task sets up the foundation for platform teams to onboard shared resources. Once the `platform-shared` namespace is ready, individual teams can reference the central-logging and artifacts buckets in their own onboarding process.

For design and governance details, see these references in kropath-core:

- **ADR-019**: Cross-account resource management (annotations, role configuration)
- **ADR-015** (§5.3): Governance cascade for S3 configuration
- **ADR-010**: kropath-controller effective-config cascade
