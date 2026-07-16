# KMSKey — Creating and Managing Encryption Keys

The `KMSKey` resource represents a single encryption key in AWS KMS. This guide covers all configuration fields, governance, and real-world usage patterns.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `KMSConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the key alias directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the KMS key resource is deleted: `"retain"` (safe) or `"delete"` |

### Key Properties

| Field | Type | Default | Purpose |
|---|---|---|---|
| `description` | string | `""` | Human-readable description of the key's purpose |
| `keySpec` | string | `""` | Key type/size; falls through to governance cascade |
| `keyUsage` | string | `""` | Key usage (ENCRYPT_DECRYPT, SIGN_VERIFY, etc.); falls through cascade |
| `enableKeyRotation` | boolean | `true` | Automatic annual rotation for symmetric keys only |

### Key Alias

| Field | Type | Default | Purpose |
|---|---|---|---|
| `createAlias` | boolean | `true` | Whether to create a human-readable alias for the key |
| `aliasName` | string | `""` | Custom alias suffix; if empty, derived from resource name |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

### Key Policy

| Field | Type | Default | Purpose |
|---|---|---|---|
| `policy` | string | `""` | Raw KMS key policy (JSON); mutually exclusive with `keyPolicyRef` |
| `keyPolicyRef` | string | `""` | Reference to `PolicyDocument` CR; mutually exclusive with `policy` |

## Key Specs (Types)

| Key Spec | Key Type | Compatible Usage | Example Use |
|---|---|---|---|
| `SYMMETRIC_DEFAULT` | Symmetric | ENCRYPT_DECRYPT | S3, EBS, RDS encryption |
| `RSA_2048` | Asymmetric | ENCRYPT_DECRYPT, SIGN_VERIFY | External encryption, signing |
| `RSA_3072` | Asymmetric | ENCRYPT_DECRYPT, SIGN_VERIFY | High-security signing |
| `RSA_4096` | Asymmetric | ENCRYPT_DECRYPT, SIGN_VERIFY | FIPS-level security |
| `ECC_NIST_P256` | Asymmetric | SIGN_VERIFY, KEY_AGREEMENT | Signing, key agreement |
| `ECC_NIST_P384` | Asymmetric | SIGN_VERIFY, KEY_AGREEMENT | High-security signing |
| `ECC_NIST_P521` | Asymmetric | SIGN_VERIFY, KEY_AGREEMENT | Maximum security |
| `ECC_SECG_P256K1` | Asymmetric | SIGN_VERIFY | Blockchain/crypto signing |
| `HMAC_224` | MAC | GENERATE_VERIFY_MAC | Message authentication (28 bytes) |
| `HMAC_256` | MAC | GENERATE_VERIFY_MAC | Message authentication (32 bytes) |
| `HMAC_384` | MAC | GENERATE_VERIFY_MAC | Message authentication (48 bytes) |
| `HMAC_512` | MAC | GENERATE_VERIFY_MAC | Message authentication (64 bytes) |

## Complete Example: S3 Encryption Key

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: s3-encryption-key
  namespace: data-prod
spec:
  configRef: general-policy
  deletionPolicy: retain
  description: "Encryption key for production S3 buckets"
  keySpec: SYMMETRIC_DEFAULT
  keyUsage: ENCRYPT_DECRYPT
  enableKeyRotation: true
  createAlias: true
  aliasName: s3-prod-encryption
  tags:
    service: s3
    environment: production
  syncedLabels:
    team: data-platform
    sensitivity: high
```

Result:
- Symmetric key with automatic annual rotation
- Alias: `alias/s3-prod-encryption`
- Will sync labels to AWS tags
- Deletion deletes only Kubernetes resource; AWS key retained

## Example: API Signing Key

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: api-signer
  namespace: services
spec:
  configRef: general-policy
  description: "Key for signing API tokens"
  keySpec: RSA_4096
  keyUsage: SIGN_VERIFY
  createAlias: true
  tags:
    purpose: api-signing
```

Result:
- RSA-4096 key for signing (asymmetric)
- `enableKeyRotation` is ignored by AWS (not applicable to asymmetric)
- Alias: `alias/services-api-signer`

## Example: Referenced Policy Document

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: bucket-key
  namespace: data
spec:
  description: "Encryption key for S3 buckets"
  keySpec: SYMMETRIC_DEFAULT
  keyUsage: ENCRYPT_DECRYPT
  keyPolicyRef: s3-encryption-policy
  # Note: s3-encryption-policy must be an existing PolicyDocument CR
```

## Status Fields

After creation, retrieve ARNs and names from status:

```yaml
status:
  resourceName: "data-s3-bucket-key"           # effectiveName
  namingStatus: "valid"                        # "valid" | "invalid-unresolved-tokens"
  keyID: "12345678-1234-1234-1234-123456789012"  # AWS key ID
  keyArn: "arn:aws:kms:us-east-1:123456789012:key/12345678-..."  # Use for S3/RDS/etc
  aliasArn: "arn:aws:kms:us-east-1:123456789012:alias/..."       # Alias reference
  predictedArn: "arn:aws:kms:us-east-1:123456789012:key/12345..."  # Equivalent to keyArn
```

## Immutability

After creation, these fields cannot be changed:

- **`keySpec`** — Key type is locked at creation
- **`keyUsage`** — Key usage is locked at creation

Attempting updates will fail:
```bash
$ kubectl patch kmskey my-key --patch '{"spec":{"keySpec":"RSA_4096"}}'
# Error: keySpec is immutable after creation
```

## Governance Cascade

When you don't specify a field, kropath resolves it using the governance cascade:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: minimal-key
  namespace: test
spec:
  configRef: pci
  # keySpec, keyUsage, enableKeyRotation are empty — resolved by cascade
```

The cascade for this key:
1. Check `pci` KMSConfig mandatory tier
2. Check instance spec (empty in this case)
3. Check `pci` KMSConfig defaults tier → uses defaults
4. Result: key gets `keySpec=SYMMETRIC_DEFAULT`, `enableKeyRotation=true` from `pci` profile

See [Governance Guide](./governance.md) for full cascade details.

## Multiple Keys in One Manifest

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: backup-encryption
  namespace: backup
spec:
  configRef: general-policy
  description: "Key for encrypting backups"
  keySpec: SYMMETRIC_DEFAULT
---
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: database-encryption
  namespace: backup
spec:
  configRef: general-policy
  description: "Key for encrypting databases"
  enableKeyRotation: false  # Override governance default
```

## Best Practices

1. **Use `retain` deletion policy** — Default; prevents accidental key deletion
2. **One key per use case** — Don't reuse keys across services
3. **Use governance profiles** — Let `KMSConfig` enforce compliance
4. **Reference policy documents** — Use `keyPolicyRef` for standardized policies
5. **Tag appropriately** — Include team, cost-center, sensitivity metadata
6. **Enable rotation for symmetric keys** — Required for data-at-rest encryption
7. **Verify cross-family references** — Check that S3, RDS, etc. can use your key ARN

## Troubleshooting

**Key creation fails with "Invalid keySpec"**
- Check `KMSConfig.mandatory.allowedKeySpecs` for the profile you selected
- Verify your requested `keySpec` is in the allowed list

**Alias creation fails**
- Verify alias name doesn't already exist in the region
- AWS alias names: 1-256 characters, alphanumeric + `/`, `_`, `-`
- No `alias/aws/` prefix allowed

**Key rotation not enabled**
- Rotation only applies to `SYMMETRIC_DEFAULT` keys
- Asymmetric (RSA, ECC) and HMAC keys don't support rotation

## Next Steps

- [Governance Guide](./governance.md) — Understanding cascade and profiles
- [Cross-Family Integration](./cross-family-integration.md) — Using KMS keys in other AWS services
