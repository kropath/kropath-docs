---
type: task
---

# Onboard the platform-shared namespace

This task walks you through onboarding a Kubernetes namespace for platform-shared resources — a namespace that hosts shared AWS resources such as central logging buckets and artifact storage.

## Before you begin

- You have a working kropath cluster in AWS with the kropath-controller and ACK (AWS Controllers for Kubernetes) installed
- You have `kubectl` configured to access the cluster
- You have AWS credentials configured with permissions to create S3 buckets and IAM resources in the target account(s)
- The namespace onboarding template has been merged into kropath-core (related: [KRO-1175](https://kropath.atlassian.net/browse/KRO-1175))

## Goal

You will:

1. Create the `platform-shared` Kubernetes namespace
2. Configure it with `KropathConfig` and `S3Config` (AWS S3 resource family configuration)
3. Set up ACK cross-account annotations so ACK can manage resources in multiple AWS accounts
4. Create shared platform resources: a central logging bucket and artifact storage buckets
5. Verify that resources are ready in Kubernetes and exist in AWS

## Step 1: Create the namespace and local configurations

The namespace onboarding template from kropath-core provides the baseline for KropathConfig and ResourceFamily-specific configurations. Follow the template from [KRO-1178](https://kropath.atlassian.net/browse/KRO-1178) to:

1. **Create the Kubernetes namespace** with ACK cross-account role annotations (required by [ADR-019](https://kropath.atlassian.net/browse/ADR-019))

   ```yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: platform-shared
     annotations:
       # ACK cross-account role (allows ACK to manage resources in different AWS accounts)
       "ack.aws.com/cross-account-role-arn": "arn:aws:iam::<account-id>:role/ack-cross-account-role"
   ```

2. **Create the `KropathConfig`** — cluster-wide settings for the namespace

   ```yaml
   apiVersion: kropath.run/v1alpha1
   kind: KropathConfig
   metadata:
     name: platform-shared-config
     namespace: platform-shared
   spec:
     # Inherit tags from a central policy
     tags:
       team: platform
       environment: shared
       managed-by: kropath
   ```

3. **Create the `S3Config`** — AWS S3-specific configuration for the namespace

   ```yaml
   apiVersion: aws.kropath.run/v1alpha1
   kind: S3Config
   metadata:
     name: platform-config
     namespace: platform-shared
   spec:
     # Common S3 settings for all S3 resources in this namespace
     encryption:
       enabled: true
       algorithm: "aws:kms"
     versioning: enabled
     publicAccessBlock:
       blockPublicAcls: true
       blockPublicPolicy: true
       ignorePublicAcls: true
       restrictPublicBuckets: true
     tags:
       inherit-from: platform-shared-config
   ```

Apply these configurations:

```bash
kubectl apply -f namespace.yaml
kubectl apply -f kropathconfig.yaml
kubectl apply -f s3config.yaml
```

Verify the namespace is ready:

```bash
kubectl get namespace platform-shared
kubectl get kropathconfig -n platform-shared
kubectl get s3config -n platform-shared
```

## Step 2: Create the shared platform resources

Once the namespace and configurations are in place, create the S3 resources that platform services depend on.

### Central Logging Bucket

Create a central bucket for platform-wide log aggregation:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: central-logging
  namespace: platform-shared
spec:
  configRef: platform-config
  
  # Explicit naming template for the bucket
  # This ensures the bucket name is consistent across accounts/regions
  nameOverride: "central-logging-{account-id}-{region}"
  
  # Bucket settings
  versioningEnabled: true
  
  # Server-side encryption
  serverSideEncryption:
    enabled: true
    algorithm: "aws:kms"
  
  # Public access blocking
  publicAccessBlock:
    blockPublicAcls: true
    blockPublicPolicy: true
    ignorePublicAcls: true
    restrictPublicBuckets: true
  
  # Lifecycle policy to manage old logs
  lifecycleConfiguration:
    - id: delete-old-logs
      status: Enabled
      expirationInDays: 90
      prefix: "logs/"
  
  # Resource tags
  tags:
    purpose: central-logging
    team: platform
```

### Artifact Storage Buckets

Create buckets for build artifacts, data pipelines, and other shared data:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: artifacts
  namespace: platform-shared
spec:
  configRef: platform-config
  
  # Explicit naming template — ensures consistency across accounts/regions
  nameOverride: "artifacts-{account-id}-{region}"
  
  # Versioning for artifact history
  versioningEnabled: true
  
  # Encryption
  serverSideEncryption:
    enabled: true
    algorithm: "aws:kms"
  
  # Public access blocking
  publicAccessBlock:
    blockPublicAcls: true
    blockPublicPolicy: true
    ignorePublicAcls: true
    restrictPublicBuckets: true
  
  # Lifecycle to clean up old artifacts
  lifecycleConfiguration:
    - id: transition-old-artifacts
      status: Enabled
      noncurrentVersionTransitionInDays: 30
      noncurrentVersionExpirationInDays: 90
  
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

Wait until both buckets show `Ready` status.

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
kubectl get namespace platform-shared -o jsonpath='{.metadata.annotations.ack\.aws\.com/cross-account-role-arn}'

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

The naming template uses `{account-id}` and `{region}` tokens, which are interpolated by ACK at creation time. Verify:

```bash
# Check the actual bucket name created
kubectl get s3bucket -n platform-shared -o jsonpath='{.items[*].status.bucketName}'

# Confirm it matches the expected template
# central-logging-<account-id>-<region>
# artifacts-<account-id>-<region>
```

## Next steps

Once the namespace and platform resources are onboarded and verified:

1. **Grant access** — Set up IAM policies and bucket policies so other services can use these resources
2. **Monitor** — Set up CloudWatch alarms for bucket metrics, access patterns, and lifecycle actions
3. **Document** — Record the bucket ARNs and usage patterns for platform consumers

## Related documentation

- [S3Bucket resource documentation](../resources/aws-s3-bucket.md)
- [S3Config resource documentation](../resources/aws-s3-config.md)
- [KropathConfig reference](../resources/kropath-config.md)
- [ADR-019: Cross-account resource management](https://kropath.atlassian.net/browse/ADR-019)

## Reference

This task implements the story described in [KRO-1176: Onboard platform-shared namespace](https://kropath.atlassian.net/browse/KRO-1176). For detailed context and implementation details:

- **Namespace onboarding**: [KRO-1178](https://kropath.atlassian.net/browse/KRO-1178)
- **Resource creation**: [KRO-1183](https://kropath.atlassian.net/browse/KRO-1183)
- **Verification in AWS**: [KRO-1179](https://kropath.atlassian.net/browse/KRO-1179)
