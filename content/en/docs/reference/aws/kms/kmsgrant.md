---
title: KMSGrant — Temporary Key Access Permissions
description: "The `KMSGrant` resource represents a temporary, scoped permission to use a KMS key."
doc_type: reference
---
# KMSGrant — Temporary Key Access Permissions

The `KMSGrant` resource represents a temporary, scoped permission to use a KMS key. Grants allow you to delegate key access to named principals without modifying the key's resource policy — making them ideal for short-lived or service-delegated access scenarios like allowing EBS snapshot copies to re-encrypt data with a different key, or cross-account principals to call `Decrypt` for bounded encryption contexts.

## When to Use Grants vs. Key Policy

| Use Case | Use This |
|----------|----------|
| Permanent, role-based access | Key policy (`KMSKey.spec.policy` or `KMSKey.spec.keyPolicyRef`) |
| Temporary or service-delegated access | **KMSGrant** |
| Cross-account access for a specific operation set | **KMSGrant** |
| Encryption-context-scoped access | **KMSGrant** (policies don't support context constraints) |
| Automatic grant retirement on schedule | Key policy (grants don't auto-retire) |

## Core Fields

### Key Reference (Exactly One)

Specify which KMS key the grant applies to:

| Field | Type | Default | Purpose |
|---|---|---|---|
| `keyRef` | string | `""` | Name of a `KMSKey` CR in the same namespace; grants access to the key ID stored in that CR's `status.keyID`. Mutually exclusive with `keyArn`. |
| `keyArn` | string | `""` | ARN or key ID of a KMS key not managed by kropath. Mutually exclusive with `keyRef`. |

**At least one must be set.** Choose `keyRef` for keys created by `KMSKey` CRs, and `keyArn` for keys created outside kropath.

### Grant Principal and Operations

| Field | Type | Default | Purpose |
|---|---|---|---|
| `granteePrincipal` | string | Required | ARN of the IAM principal (role, user, or federated identity) receiving the permissions |
| `operations` | `[]string` | Required, `minItems: 1` | List of permitted KMS operations (see table below) |
| `retiringPrincipal` | string | `""` | ARN of a principal permitted to retire (revoke) the grant; omit to prevent automatic grant retirement by the grantee |

### Grant Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `grantName` | string | `""` | Idempotency token forwarded to the AWS API; prevents duplicate grants on retry. When empty, defaults to `<namespace>-<name>`. **Not a cloud resource name.** |

### Encryption Context Constraints

Restrict when the grant can be used based on encryption-context parameters:

| Field | Type | Default | Purpose |
|---|---|---|---|
| `constraints.encryptionContextEquals` | map | `{}` | Grant valid only when the request encryption context matches exactly (all pairs must match) |
| `constraints.encryptionContextSubset` | map | `{}` | Grant valid only when the request encryption context includes these key-value pairs (can include additional pairs) |

**Note:** Both `encryptionContextEquals` and `encryptionContextSubset` are optional. When empty or omitted, the grant is unconstrained by encryption context. While you can set both fields in the CR (and the RGD will render both), AWS KMS enforces a constraint that at most one of these two may be used per request — if you set both, AWS will reject grant operations that don't match both constraints exactly.

### Governance and Metadata

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects the `KMSConfig` governance profile; if the profile doesn't exist, the governance tier becomes empty (no allowlist enforced) |
| `deletionPolicy` | string | `"retain"` | Behavior when the grant is deleted: `"retain"` (orphans the AWS grant) or `"delete"` (calls `RevokeGrant` to terminate the grant) |
| `tags` | map | `{}` | Kubernetes metadata only — **AWS grants don't support cloud tags** |
| `syncedLabels` | map | `{}` | Kubernetes labels (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Permitted Operations

Use any combination of these operations:

| Operation | Description | Use Case |
|-----------|-------------|----------|
| `Encrypt` | Encrypt data with the key | Encrypting data before storage |
| `Decrypt` | Decrypt data with the key | Decrypting stored data |
| `GenerateDataKey` | Generate and return plaintext data key | Applications encrypting their own data |
| `GenerateDataKeyWithoutPlaintext` | Generate encrypted data key only | S3 Server-Side Encryption (SSE-KMS) |
| `GenerateDataKeyPair` | Generate asymmetric key pair | Signing and verification operations |
| `GenerateDataKeyPairWithoutPlaintext` | Generate encrypted key pair | When plaintext must not leave AWS |
| `ReEncryptFrom` | Re-encrypt data encrypted with this key | Changing encryption keys |
| `ReEncryptTo` | Re-encrypt data with this key as target | Changing encryption keys to this key |
| `CreateGrant` | Create additional grants on the key | Delegating grant creation to a principal |
| `RetireGrant` | Retire (revoke) grants created by the grantee | Allowing a principal to clean up its own grants |
| `DescribeKey` | Query key metadata | Getting key information |
| `GenerateMac` | Generate a message authentication code | HMAC-based data verification |
| `VerifyMac` | Verify a message authentication code | HMAC verification |
| `DeriveSharedSecret` | Derive a shared secret for key agreement | Secure key negotiation |

## Status Fields

After creation, the grant's identity and resolved configuration appear in status:

```yaml
status:
  grantID: "0c237476b39f8bc44e45e41eae2d7d26ef78dc7ef5b7d67eb95e79c3fc0df58f"  # AWS-assigned grant ID
  grantToken: "opaque-token-value"  # Grant token for immediate-use call chaining (single-use)
  resolvedKeyID: "1234abcd-12ab-34cd-56ef-1234567890ab"  # The key ID actually forwarded to AWS
  validationError: ""  # Non-empty if the grant CR is invalid (advisory validation)
  droppedOperations: []  # Operations filtered by allowedGrantOperations allowlist (empty when nothing was dropped)
```

**Note:** There is no `status.resourceName`, `status.predictedArn`, or `status.namingStatus` — AWS grants have no cloud resource name. They are identified solely by the grant ID and grant token.

### Validation and Filtering Signals

The `status.validationError` and `status.droppedOperations` fields provide feedback on grant validity and operation filtering:

- **`validationError` is non-empty when:** The grant CR is invalid (e.g., both `keyRef` and `keyArn` are set, `operations` is empty, or allowlist filtering resulted in zero allowed operations). This is an **advisory validation signal** — the CR itself is accepted (`apply` succeeds) but the ACK Grant child will not be created until the error is resolved. Check this field to understand why a grant isn't being created.

- **`droppedOperations` is non-empty when:** `KMSConfig.mandatory.allowedGrantOperations` or `.defaults.allowedGrantOperations` filtered your requested operations. For example, if you request `["Decrypt", "Encrypt"]` but the profile allows only `["Decrypt"]`, then `droppedOperations` will contain `["Encrypt"]` and the grant is created with only the allowed operations.

**Important:** The "Required" and "Mutually exclusive" constraints on `keyRef`/`keyArn`/`operations` are enforced at the RGD advisory level (via `status.validationError`), not at the CRD or API server level. This means `kubectl apply` will **always succeed** — the validation occurs after acceptance, and the validation status appears in `status.validationError` rather than a creation failure.

## Complete Example: Cross-Account Snapshot Copy

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSGrant
metadata:
  name: snapshot-copy-grant
  namespace: backup
spec:
  configRef: general-policy
  deletionPolicy: retain

  # Allow the snapshot service to use the encryption key
  granteePrincipal: "arn:aws:iam::123456789012:role/aws:elasticsnapshotcopy"
  
  # Allow re-encryption operations only
  operations:
    - ReEncryptFrom
    - ReEncryptTo
    - DescribeKey

  # Reference a locally-managed KMS key
  keyRef: backup-encryption-key

  # Tag for tracking
  tags:
    purpose: snapshot-copy
    rotation: managed
```

Result:
- Grant created in AWS KMS
- The snapshot copy service can re-encrypt backups with `backup-encryption-key`
- No access to `Decrypt` or `Encrypt` operations (principle of least privilege)
- Grant retained when deleted (not revoked automatically)

## Example: Encryption-Context-Scoped Access

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSGrant
metadata:
  name: tenant-isolation-grant
  namespace: multi-tenant-app
spec:
  deletionPolicy: delete

  # Allow a per-tenant role to decrypt
  granteePrincipal: "arn:aws:iam::123456789012:role/app-tenant-acme"
  operations:
    - Decrypt
    - DescribeKey

  # Use an external KMS key
  keyArn: "arn:aws:kms:us-east-1:123456789012:key/9876fedc-98fe-76dc-54ba-9876543210ba"

  # Restrict to tenant-specific encryption context
  constraints:
    encryptionContextEquals:
      tenant: "acme-corp"
      environment: production
```

Result:
- The `app-tenant-acme` role can decrypt data **only** when the encryption context contains `tenant: acme-corp` and `environment: production`
- Any decrypt request with a different or missing encryption context is rejected by AWS KMS
- Deleting the grant revokes it immediately (instead of orphaning it)

## Example: Service-Delegated EBS Encryption

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSGrant
metadata:
  name: ebs-reencryption-grant
  namespace: infrastructure
spec:
  # Allow EBS service to re-encrypt volume data
  granteePrincipal: "arn:aws:service-principal:ebs.amazonaws.com"
  
  # Minimal operation set for re-encryption
  operations:
    - ReEncryptFrom
    - ReEncryptTo
    - DescribeKey

  # Reference a key managed by KMSKey
  keyRef: default-ebs-key

  # Allow EBS (via key admin role) to retire the grant if needed
  retiringPrincipal: "arn:aws:iam::123456789012:role/key-administrators"

  # Governance: enforce allowedGrantOperations from general-policy profile
  configRef: general-policy

  # Sync labels to Kubernetes for observability
  syncedLabels:
    service: ebs
    critical: true
```

Result:
- EBS service can re-encrypt volumes with the managed key
- Key administrators can revoke the grant via `RetireGrant`
- Only re-encryption and describe operations are permitted
- Kubernetes labels track grant ownership and criticality

## Governance: allowedGrantOperations Allowlist

When a `KMSConfig` profile defines `allowedGrantOperations`, the RGD filters your grant's operation list:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSConfig
metadata:
  name: pci-compliance
  namespace: security
spec:
  mandatory:
    # No grant can request operations outside this allowlist
    allowedGrantOperations:
      - Decrypt
      - GenerateDataKey
      - DescribeKey
```

When this profile is active and your grant requests `["Decrypt", "Encrypt"]`:
- `Decrypt` is allowed → included
- `Encrypt` is not on the allowlist → dropped
- The grant is created with only `["Decrypt"]`
- `status.droppedOperations` reports that `Encrypt` was filtered out

**Behavior:**
- An empty allowlist (`[]`) means no restriction — all operations are permitted
- If both `mandatory.allowedGrantOperations` and `defaults.allowedGrantOperations` are set, an error is raised (use one or the other)
- If filtering results in **zero** remaining operations, the grant is not created and `status.validationError` reports the empty-set condition
- **Why filtering, not rejection?** A narrower grant is still valid — blocking all key access because of one forbidden operation is a worse failure mode

## Idempotency Token

The `spec.grantName` field is an **idempotency token**, not a resource name. AWS uses it to deduplicate `CreateGrant` retries: if a retry is received with the same key, grantee, operations, constraints, and name, AWS returns the existing grant instead of creating a duplicate.

When `spec.grantName` is empty (the default), the RGD derives a value from the CR coordinates:
```
<namespace>-<cr-name>
```

Example: A grant in namespace `payments-prod` named `snapshot-grant` gets token `payments-prod-snapshot-grant`.

You can override this by setting `spec.grantName` to any value (e.g., `ebs-copy-token`), but the naming template in your governance profile is **not** applied to this field — grants have no resource name, so naming templates don't apply.

## Deletion Semantics

When you delete a `KMSGrant` CR:

| `deletionPolicy` | Behavior |
|---|---|
| `retain` (default) | The AWS grant is orphaned; it continues to exist in KMS and must be manually revoked via `RevokeGrant` or the AWS console. The Kubernetes resource is deleted. |
| `delete` | The RGD calls AWS `RevokeGrant` to terminate the grant immediately, then deletes the Kubernetes resource. |

**Recommendation:** Use the default `retain` policy for production grants. Deleting a grant allows you to verify that no workloads are still using it before revocation. Manual revocation via the AWS console provides an additional safety gate.

## Key Resolution

### Using a Local KMSKey

```yaml
keyRef: backup-encryption-key  # Name of a KMSKey CR in the same namespace
```

The RGD:
1. Attempts to read `status.keyID` from the referenced `KMSKey` CR
2. Creates the ACK Grant child CR immediately, even if `status.keyID` is still empty (setting `keyID: ""`)
3. Patches the Grant CR with the resolved key ID once the `KMSKey` CR's `status.keyID` becomes available

### Using an External KMS Key

```yaml
keyArn: "arn:aws:kms:us-east-1:123456789012:key/1234abcd-1234-1234-1234-1234567890ab"
# or:
keyArn: "1234abcd-1234-1234-1234-1234567890ab"  # Just the key ID
```

The RGD forwards the ARN or key ID verbatim to AWS. No `KMSKey` CR lookup is required.

## Naming Exemption (Technical Note)

This resource is **naming-exempt**. AWS KMS grants have no user-visible cloud resource name — they are identified solely by an AWS-assigned grant ID and grant token. The naming convention does not apply:

- No `spec.nameOverride` field
- No `status.resourceName` field
- No `status.predictedArn` field
- No `status.namingStatus` field
- The `namingTemplate` in your governance profile is **not** read by this RGD

The `spec.grantName` field is an idempotency token for retry deduplication, not a resource name.

## Governance Cascade

The grant's configuration is resolved via the nine-tier governance cascade (see [Governance Guide](./governance.md)):

**Fields subject to cascade:**
- `tags` (mandatory ∪ instance ∪ defaults)
- `syncedLabels` (same merge)
- `syncedAnnotations` (same merge)
- `allowedGrantOperations` (mandatory allowlist wins; else defaults allowlist; else no restriction)

**Fields NOT subject to cascade** (workload-specific bindings with no meaningful org-wide default):
- `granteePrincipal`
- `retiringPrincipal`
- `keyRef` / `keyArn`
- `operations`
- `constraints`
- `grantName`
- `deletionPolicy`

### Example: Cascade in Action

```yaml
# kropath-docs doesn't define a cross-family governing set; 
# this is illustrative from standard patterns
```

1. `KropathConfig.kms.tags` → mandatory organization-wide tags
2. `KMSConfig/general-policy.mandatory.tags` → profile mandatory tags
3. `spec.tags` (instance) → override specific tags
4. `KMSConfig/general-policy.defaults.tags` → profile defaults
5. Result → merged tags applied to Kubernetes metadata (prefixed `aws.kropath.run/`)

## Best Practices

1. **Use `retain` deletion policy** — Default; provides a safety gate before grant revocation
2. **Prefer `keyRef` when possible** — Keeps key and grant lifecycle linked
3. **Encrypt context constraints** — Use `encryptionContextEquals` or `encryptionContextSubset` to enforce tenant isolation in multi-tenant systems
4. **Principle of least privilege** — Request only the operations the principal needs
5. **Set `retiringPrincipal`** — Allow the grantee to clean up its own grants via `RetireGrant`
6. **Use governance allowlists** — Define `allowedGrantOperations` in profiles to enforce organizational security policies
7. **Monitor grant status** — Watch for condition changes indicating filtering or key resolution delays

## Troubleshooting

**Grant was not created**

- Check `status.validationError` for advisory validation issues (e.g., `keyRef` and `keyArn` both set, or empty `operations`)
- When `status.validationError` is non-empty, the ACK Grant child CR is never created until the error is resolved
- Fix the validation error (correct the CR spec), and the grant will be created in the next reconciliation

**Grant is created but waiting for key to be ready**

- If `status.resolvedKeyID` is empty and `status.validationError` is empty, the grant was created with `keyID: ""` and is waiting for the referenced `KMSKey` to be ready
- Verify the referenced `KMSKey` CR exists and check its `status.keyID`
- This is normal during key creation; once the `KMSKey` is ready, the grant will be patched with the resolved key ID

**Grant operations are silently filtered**

- Inspect `status.droppedOperations` to see which operations were filtered
- This happens when `KMSConfig.mandatory.allowedGrantOperations` or `.defaults.allowedGrantOperations` is set
- Verify the profile's allowlist includes your requested operations; if the allowlist is more restrictive, some operations will be dropped

**Empty intersection — no operations allowed**

- The allowlist in your profile doesn't overlap with your requested operations
- Either expand the allowlist in the profile or request different operations
- This is treated as an error: the grant is not created, and `status.validationError` reports the mismatch

**Encryption context constraint isn't working**

- Verify the constraint is spelled correctly (`encryptionContextEquals` vs. `encryptionContextSubset`)
- Ensure the encryption context keys match exactly (case-sensitive, whitespace-sensitive)
- Use `encryptionContextEquals` for exact matching; use `encryptionContextSubset` to allow additional pairs

**Grant revocation fails**

- Ensure the principal calling `RevokeGrant` is either the key owner or the `retiringPrincipal`
- If using `deletionPolicy: delete`, the RGD will call `RevokeGrant` automatically on deletion
- To force revocation, delete the CR and verify the AWS grant is no longer listed

## Next Steps

- [KMSKey Usage Guide](./kmskey.md) — Creating and managing encryption keys
- [KMSConfig Governance Model](./governance.md) — Understanding governance profiles and the cascade
- [Cross-Family Integration](./cross-family-integration.md) — Using KMS keys with S3, EBS, RDS, and Lambda
