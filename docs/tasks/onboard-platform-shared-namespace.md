---
type: task
---

# Onboard the platform-shared namespace

This task walks you through onboarding a Kubernetes namespace for platform-shared resources — a namespace that hosts shared AWS resources such as central logging buckets and artifact storage.

## Before you begin

- You have a working kropath cluster in AWS with the kropath-controller and ACK (AWS Controllers for Kubernetes) installed
- You have `kubectl` configured to access the cluster
- You have AWS credentials configured with permissions to create S3 buckets and IAM resources in the target account(s)
- Platform teams have created one or more `AWSS3Config` governance profiles in the `kro-system` namespace (e.g., `general-policy`, `strict`)
- The namespace onboarding template has been merged into kropath-core (see [KRO-1178](https://github.com/kropath/kropath-core/issues) for details)

## Goal

You will:

1. Create the `platform-shared` Kubernetes namespace
2. Apply the namespace onboarding template (KropathConfig and local resource-family configuration)
3. Create shared platform resources: a central logging bucket and artifact storage buckets
4. Verify that resources are ready in Kubernetes and exist in AWS

## Step 1: Create the namespace with the onboarding template

The namespace onboarding template from kropath-core (task [KRO-1178](https://github.com/kropath/kropath-core/issues)) provides baseline configurations. Apply the template manifest to create the `platform-shared` namespace with all required local configurations:

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
  
  # Override bucket naming to ensure global uniqueness across accounts/regions
  nameOverride: "central-logging-{account_id}-{region}"
  
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
  
  # Override bucket naming for consistency across accounts/regions
  nameOverride: "artifacts-{account_id}-{region}"
  
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

## Step 5: Verify cross-account access (if applicable)

If the cluster manages resources across multiple AWS accounts, verify that ACK's cross-account role is configured correctly:

```bash
# List the cross-account role ARN from the namespace annotation
kubectl get namespace platform-shared -o jsonpath='{.metadata.annotations.aws\.kropath\.run/cross-account-role-arn}'

# Verify the role exists in the target account
aws iam get-role \
  --role-name ack-cross-account-role \
  --profile <target-account-profile>
```

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
- Confirm the role ARN in the namespace annotation matches the cross-account role in the target account

### Bucket names do not match the naming template

The naming template uses `{account_id}` and `{region}` tokens, which are interpolated at creation time. Verify:

```bash
# Check the actual bucket name created
kubectl get s3bucket -n platform-shared -o jsonpath='{.items[*].status.bucketName}'

# Confirm it matches the expected template
# central-logging-<account_id>-<region>
# artifacts-<account_id>-<region>
```

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

This task implements the story described in [KRO-1176: Onboard platform-shared namespace](https://github.com/kropath/kropath-core/issues). For detailed context and implementation details, see the related Multica tickets:

- **KRO-1178**: Namespace onboarding template creation
- **KRO-1183**: S3 resource creation (central-logging and artifacts buckets)
- **KRO-1179**: Verification in AWS
