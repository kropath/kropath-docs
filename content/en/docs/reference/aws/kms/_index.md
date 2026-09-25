---
title: AWS KMS — Encryption Key Management
description: The AWS KMS family within kropath provides abstractions for managing Amazon KMS encryption keys.
doc_type: reference
weight: 300
---
# AWS KMS — Encryption Key Management

The AWS KMS family within kropath provides abstractions for managing Amazon KMS encryption keys. It enables platform engineers to enforce organization-wide controls such as mandatory key rotation, allowed key types, and key policy governance, while allowing application teams to provision and configure encryption keys for securing data at rest in S3, EBS, RDS, Lambda, and other AWS services.

## Prerequisites and Setup

`KMSKey` resources can be created independently, but the KMS family integrates with other kropath families for end-to-end data protection:

*   **S3 Family:** For encrypting S3 bucket objects via the `S3Bucket.spec.encryption.kmsKeyArn` field.
*   **EBS Family:** For encrypting EBS volumes (deferred to P2+).
*   **RDS Family:** For encrypting RDS databases (deferred to P2+).
*   **EKS Family:** For encrypting EKS secrets (deferred to P2+).
*   **Lambda Family:** For encrypting Lambda environment variables (deferred to P2+).
*   **IAM Family:** For creating service-linked roles that grant keys permissions to other services.
*   **Policy Family:** For defining granular key access policies using the `PolicyDocument` CRD.

## Quick Start

To create a simple encryption key:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: my-data-key
  namespace: payments-prod
spec:
  configRef: general-policy
  description: "Encryption key for production payment data"
  keySpec: SYMMETRIC_DEFAULT
  keyUsage: ENCRYPT_DECRYPT
  enableKeyRotation: true
  createAlias: true
```

This creates:
1. An AWS KMS encryption key with automatic annual rotation
2. A human-readable alias (`alias/payments-prod-my-data-key`)
3. Automatic tags and labels from the `general-policy` governance profile

## Key Concepts

### KMSKey — Encryption Key Instances

An `KMSKey` resource represents a single encryption key in AWS KMS. It defines:
- **Key type** (symmetric or asymmetric)
- **Key usage** (encrypt/decrypt, sign/verify, MAC generation)
- **Rotation policy** (automatic annual for symmetric keys)
- **Access policy** (who can use the key)
- **Friendly alias** (optional human-readable name)
- **Deletion behavior** (retain or delete when removed)

### KMSConfig — Governance Profiles

`KMSConfig` CRs define per-profile governance settings for KMS keys. These profiles are referenced by `KMSKey` instances via `spec.configRef`. Each profile includes `mandatory` and `defaults` sections that control encryption requirements across your organization.

**Example profiles:**
- `general-policy`: Conservative defaults (rotation enabled, symmetric keys)
- `pci`: Hardened for PCI compliance (restricted key types, mandatory rotation)
- `dev`: Permissive for development (any key type, rotation optional)

### KMSGrant — Temporary Access Permissions

A `KMSGrant` resource represents a temporary, scoped permission to use a KMS key. Grants allow you to delegate key access to named principals without modifying the key's resource policy — making them ideal for:
- Short-lived or service-delegated access (e.g., allowing EBS to re-encrypt snapshots)
- Cross-account access for a specific operation set
- Encryption-context-scoped access (e.g., tenant isolation in multi-tenant systems)

Grants differ from key policies in that they:
- Are temporary (can be revoked immediately)
- Support encryption-context constraints
- Allow fine-grained operation filtering via governance profiles

### Governance Cascade

Kropath employs a nine-tier governance cascade (ADR-010, ADR-015 §5.3) to resolve effective configuration for KMS keys. This ensures organizational-level policies take precedence while providing flexibility for specific use cases.

The `kropath-controller` pre-merges all governance sources into `status.effectiveConfig` on the namespaced `KMSConfig` CR. `KMSKey` and `KMSGrant` RGDs read this configuration to determine the final, resolved settings.

**When to use `KropathConfig.kms` vs. `KMSConfig`:**
- **`KropathConfig.kms`:** Org-wide governance (e.g., force all keys to have rotation enabled)
- **`KMSConfig`:** Per-profile governance (e.g., restrict a `pci` profile to specific key types)

## Key Concepts: Symmetric vs. Asymmetric

### Symmetric Keys (`SYMMETRIC_DEFAULT`)

Use symmetric keys for encrypting data at rest in AWS services (S3, EBS, RDS, etc.). AWS handles key rotation automatically (annual). These are the default and most commonly used key type.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: s3-bucket-encryption
  namespace: data-prod
spec:
  keySpec: SYMMETRIC_DEFAULT
  keyUsage: ENCRYPT_DECRYPT
  enableKeyRotation: true  # Enabled by default; ignored by AWS for asymmetric keys
```

### Asymmetric Keys (RSA, ECC)

Use asymmetric keys for encryption outside AWS services (e.g., encrypting data before sending to third parties) or for signing documents. Choose based on your use case:

- **RSA** (2048, 3072, 4096 bits): For encryption or signing; widely supported
- **ECC NIST** (P-256, P-384, P-521): For signing only; faster and smaller than RSA
- **ECC SECG** (P-256K1): Secp256k1 curve, used in cryptocurrency/blockchain

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: api-signing-key
  namespace: services
spec:
  keySpec: RSA_4096
  keyUsage: SIGN_VERIFY
  description: "Key for signing API tokens and certificates"
```

**Note:** `enableKeyRotation` only applies to symmetric keys. For asymmetric keys, AWS KMS silently ignores this field; rotation is not supported.

## Key Aliases

Every `KMSKey` can have a human-readable alias (enabled by default) to make the key easier to reference. The alias is automatically derived from your resource name and namespace, or you can provide a custom name.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: payment-processor-key
  namespace: payments-prod
spec:
  createAlias: true                    # Enabled by default
  aliasName: "payment-encryption-key"  # Optional custom alias (else: {namespace}-{name})
```

Aliases are useful when referencing keys in other services or third-party applications.

## Key Policies

Control who can use your encryption key through key access policies. Kropath supports two approaches:

### Raw JSON Policy

Provide a complete KMS key policy document:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: sensitive-data-key
  namespace: security
spec:
  policy: |
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "Enable IAM User Permissions",
          "Effect": "Allow",
          "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
          "Action": "kms:*",
          "Resource": "*"
        }
      ]
    }
```

### PolicyDocument Reference

Reference a managed policy document for reuse across multiple keys:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: s3-encryption-key
  namespace: data
spec:
  keyPolicyRef: s3-encryption-policy  # References an PolicyDocument CR
```

**Mutual exclusivity:** You cannot specify both `policy` and `keyPolicyRef` — choose one approach per key.

## Key Deletion Behavior

When you delete an `KMSKey` resource, the behavior of the AWS KMS key depends on the deletion policy:

- **`retain` (default):** The AWS KMS key is preserved; only the Kubernetes resource is deleted. This is the safe default to prevent accidental key deletion.
- **`delete`:** The AWS KMS key is deleted (scheduled for deletion with a 7-day waiting period per AWS KMS policy).

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: temporary-key
  namespace: test
spec:
  deletionPolicy: "delete"  # Unsafe; use only for test keys
```

**Recommendation:** Use the default `retain` policy. Delete KMS keys manually through the AWS console if needed, and verify that no services are still using the key.

## ARN Reference Patterns

Use the `status` fields on your `KMSKey` resource to reference the key in other services or external systems:

- **`status.keyArn`:** The full KMS key ARN (available post-creation)
  ```
  arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012
  ```

- **`status.aliasArn`:** The alias ARN (predictable even pre-creation if using default alias)
  ```
  arn:aws:kms:us-east-1:123456789012:alias/my-namespace-my-key
  ```

- **`status.resourceName`:** The effective resource name (e.g., `my-namespace-my-key`)

- **`status.predictedArn`:** Equivalent to `keyArn` (populated post-creation)

## Next Steps

For detailed guidance, see:
- [KMSConfig Governance Model](./governance.md) — Understanding mandatory vs. defaults tiers and profile management
- [KMSKey Usage Guide](./kmskey.md) — Field reference and configuration options
- [KMSGrant Access Delegation](./kmsgrant.md) — Creating temporary, scoped key access permissions
- [Cross-Family Integration](./cross-family-integration.md) — How to reference KMS keys in S3, EBS, RDS, Lambda, and EKS

## Out-of-Scope (Phase 2+)

The following KMS features are not yet supported and are deferred to later phases:
- Multi-region keys
- Imported key material
- Custom key stores
