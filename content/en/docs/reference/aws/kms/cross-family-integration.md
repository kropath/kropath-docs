---
title: Cross-Family KMS Integration
description: This guide explains how other AWS families (S3, EBS, RDS, Lambda, EKS) reference and use KMS encryption keys, including ARN patterns, dependency ordering, and real-world examples.
doc_type: reference
---
# Cross-Family KMS Integration

This guide explains how other AWS families (S3, EBS, RDS, Lambda, EKS) reference and use KMS encryption keys, including ARN patterns, dependency ordering, and real-world examples.

## Overview

KMS is a foundational security service. Other AWS services integrate with KMS by referencing key ARNs in their configuration:

- **S3** — Encrypts bucket objects with SSE-KMS
- **EBS** — Encrypts volumes and snapshots (deferred to P2+)
- **RDS** — Encrypts database instances and backups (deferred to P2+)
- **Lambda** — Encrypts environment variables (deferred to P2+)
- **EKS** — Encrypts Kubernetes secrets (deferred to P2+)

All families follow the same pattern: reference the KMS key ARN from the `KMSKey.status` fields.

## ARN Reference Patterns

After an `KMSKey` is created, three ARNs are available in the `status`:

### Key ARN

Used by most services (S3, EBS, RDS, Lambda, EKS) to encrypt data:

```
arn:aws:kms:<region>:<account-id>:key/<key-id>
```

**Example:**
```
arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012
```

**Available in:** `status.keyArn` or `status.predictedArn`  
**When available:** Post-creation only

### Alias ARN

Alternative reference using human-readable alias:

```
arn:aws:kms:<region>:<account-id>:alias/<alias-name>
```

**Example:**
```
arn:aws:kms:us-east-1:123456789012:alias/s3-prod-encryption
```

**Available in:** `status.aliasArn`  
**When available:** Post-creation  
**Pre-creation predictable:** Yes, if you know namespace, name, and naming template

### Alias Name

For services accepting alias names directly:

```
alias/<alias-name>
```

## S3 Integration

Encrypt S3 bucket objects with server-side encryption (SSE-KMS).

### Step 1: Create the KMS Key

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: s3-encryption-key
  namespace: data-prod
spec:
  configRef: general-policy
  description: "Encryption key for S3 buckets"
  keySpec: SYMMETRIC_DEFAULT
  keyUsage: ENCRYPT_DECRYPT
  enableKeyRotation: true
  createAlias: true
```

### Step 2: Reference in S3 Bucket

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: product-data
  namespace: data-prod
spec:
  configRef: general-policy
  encryption:
    algorithm: "aws:kms"
    kmsKeyArn: arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012
    bucketKeyEnabled: true
  blockPublicAccess: true
```

**Key points:**
- Use `status.keyArn` from the `KMSKey` resource
- Set `algorithm: "aws:kms"` to enable KMS encryption
- Set `bucketKeyEnabled: true` to reduce KMS API costs
- S3 service needs `kms:Decrypt` and `kms:GenerateDataKey` permissions

### Dependencies

Deploy KMS key before S3 bucket to ensure `status.keyArn` is available.

## RDS Integration

Use a KMS key to encrypt RDS databases and backups.

### Create the KMS Key

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: rds-encryption-key
  namespace: databases
spec:
  configRef: general-policy
  description: "Encryption key for RDS databases"
  keySpec: SYMMETRIC_DEFAULT
  keyUsage: ENCRYPT_DECRYPT
  enableKeyRotation: true
  tags:
    service: rds
    sensitivity: high
```

### Reference in RDS Database

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSInstance  # Note: RDS family is Phase 2+
metadata:
  name: production-db
  namespace: databases
spec:
  engine: postgres
  storageEncrypted: true
  kmsKeyArn: arn:aws:kms:us-east-1:123456789012:key/12345678-...
```

**Note:** RDS family is deferred to Phase 2+; this example shows expected integration.

## EBS Integration

Encrypt EBS volumes.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EBSVolume  # Note: EBS family is Phase 2+
metadata:
  name: encrypted-data-volume
  namespace: compute
spec:
  size: 100
  encrypted: true
  kmsKeyArn: arn:aws:kms:us-east-1:123456789012:key/12345678-...
```

**Note:** EBS family is deferred to Phase 2+.

## Lambda Integration

Encrypt Lambda environment variables.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunction  # Note: Lambda family is Phase 2+
metadata:
  name: secure-handler
  namespace: functions
spec:
  runtime: python3.11
  environment:
    variables:
      DATABASE_PASSWORD: "secret"
  kmsKeyArn: arn:aws:kms:us-east-1:123456789012:key/12345678-...
```

**Note:** Lambda family is deferred to Phase 2+.

## EKS Integration

Encrypt Kubernetes secrets in EKS.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EKSCluster  # Note: EKS family is Phase 2+
metadata:
  name: production-cluster
  namespace: platform
spec:
  version: "1.28"
  secretEncryption:
    kmsKeyArn: arn:aws:kms:us-east-1:123456789012:key/12345678-...
```

**Note:** EKS family is deferred to Phase 2+.

## Key Policy Requirements

For services to use your KMS key, grant permissions in the key policy.

### Example: S3 and EBS Access

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Enable IAM policies",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
      "Action": "kms:*",
      "Resource": "*"
    },
    {
      "Sid": "Allow S3 to use the key",
      "Effect": "Allow",
      "Principal": {"Service": "s3.amazonaws.com"},
      "Action": [
        "kms:Decrypt",
        "kms:GenerateDataKey",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Allow EBS to use the key",
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": [
        "kms:Decrypt",
        "kms:CreateGrant",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    }
  ]
}
```

### Using PolicyDocument

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: multi-service-key-policy
  namespace: security
spec:
  documentJSON: |
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "Enable IAM policies",
          "Effect": "Allow",
          "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
          "Action": "kms:*",
          "Resource": "*"
        },
        {
          "Sid": "Allow S3 and EBS",
          "Effect": "Allow",
          "Principal": {"Service": ["s3.amazonaws.com", "ec2.amazonaws.com"]},
          "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
          "Resource": "*"
        }
      ]
    }
---
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: data-encryption-key
  namespace: security
spec:
  configRef: general-policy
  keySpec: SYMMETRIC_DEFAULT
  keyUsage: ENCRYPT_DECRYPT
  keyPolicyRef: multi-service-key-policy
```

## Dependency Ordering

1. **Create KMS Keys** — Wait for `status.keyArn` to populate
2. **Create Service Resources** — Reference the key ARN (S3 buckets, RDS instances, etc.)
3. **Update IAM Roles** — Grant service roles explicit KMS permissions if needed

### Example Deployment

```yaml
# Step 1: Create KMS key
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: encryption-key
  namespace: data-prod
spec:
  configRef: general-policy
  keySpec: SYMMETRIC_DEFAULT
---
# Step 2: Create bucket (after key status.keyArn is available)
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: encrypted-bucket
  namespace: data-prod
spec:
  encryption:
    algorithm: "aws:kms"
    kmsKeyArn: arn:aws:kms:us-east-1:123456789012:key/...
```

## Troubleshooting

**"Access Denied" when service uses the key**
- Verify KMS key policy allows the service (e.g., `s3.amazonaws.com`, `rds.amazonaws.com`)
- Check service role has `kms:Decrypt` and needed permissions
- See [Key Policy Requirements](#key-policy-requirements)

**"Key ARN not found" errors**
- Ensure you're using `status.keyArn` (post-creation only)
- Verify key was created in same AWS region
- Check account ID in ARN is correct

**"Invalid KMS key" when creating encrypted resource**
- Verify key exists and is enabled
- Confirm key ARN format: `arn:aws:kms:<region>:<account-id>:key/<key-id>`
- Verify key spec is compatible (symmetric for S3)

**Key rotation affecting encrypted data**
- KMS key rotation is automatic and transparent
- Encrypted data remains readable after rotation
- No action needed

## Next Steps

- [KMSKey Usage Guide](./kmskey.md) — Configure individual keys
- [Governance Guide](./governance.md) — Enforce KMS policies
- [AWS KMS Documentation](https://docs.aws.amazon.com/kms/) — AWS native documentation
