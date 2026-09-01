# SSMParameter — Configuration and Secrets Storage

The `SSMParameter` resource represents a named configuration value or secret in AWS Systems Manager Parameter Store. It supports hierarchical naming, three parameter types (String, StringList, SecureString), and full KMS encryption integration.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SSMConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the parameter name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` (safe) or `"delete"` |

### Parameter Value (Mutually Exclusive)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `value` | string | `""` | Plain-text parameter value for String/StringList types |
| `valueFrom` | object | `nil` | Reference to Kubernetes Secret for SecureString values: `{secretKeyRef: {name, key}}` |

**Critical:** Exactly one of `value` or `valueFrom` must be set:
- **`value`:** For String and StringList parameters (direct plaintext in CR)
- **`valueFrom`:** For SecureString parameters (secret reference to prevent GitOps exposure)

### Parameter Type and Tier

| Field | Type | Default | Purpose |
|---|---|---|---|
| `type` | string | `"String"` | Parameter type: String, StringList, or SecureString; **immutable after creation** |
| `tier` | string | `""` | Tier: Standard (4 KB), Advanced (8 KB), or Intelligent-Tiering; Standard → Advanced is one-way |
| `dataType` | string | `"text"` | Data type for String only: text, aws:ec2:image, aws:ssm:integration |
| `allowedPattern` | string | `""` | Regex pattern for value validation |
| `description` | string | `""` | Human-readable description; do not include PII |

### Encryption (SecureString Only)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `keyID` | string | `""` | KMS key ID, ARN, or alias for SecureString encryption; mutually exclusive with `keyRef` |
| `keyRef` | object | `nil` | ACK reference to a `KMSKey` CR; resolves `keyID` at creation time; mutually exclusive with `keyID` |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels synchronized to AWS tags |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations synchronized to AWS tags |

### Policies (Advanced)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `policies` | string | `""` | JSON array of parameter policies: Expiration, ExpirationNotification, NoChangeNotification |

## Parameter Types

### String Parameters

Plain-text values up to 4 KB (Standard tier) or 8 KB (Advanced tier):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMParameter
metadata:
  name: app-version
  namespace: production
spec:
  type: String
  value: "v1.2.3"
  description: "Current application version"
  tags:
    Application: MyApp
```

### StringList Parameters

Comma-separated values, useful for arrays:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMParameter
metadata:
  name: allowed-regions
  namespace: platform
spec:
  type: StringList
  value: "us-east-1,us-west-2,eu-west-1"
  description: "Allowed AWS regions"
```

### SecureString Parameters

**Encrypted** using KMS; stored as a Kubernetes Secret reference, not plaintext:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMParameter
metadata:
  name: db-password
  namespace: production
spec:
  type: SecureString
  valueFrom:
    secretKeyRef:
      name: database-credentials  # Kubernetes Secret
      key: password               # Secret key
  keyID: "arn:aws:kms:us-east-1:123456789012:key/12345678-..."
  description: "Database password"
```

**Why `valueFrom` for SecureString?**

In GitOps workflows, all configuration is version-controlled. Storing sensitive data directly in CRs (`spec.value`) exposes secrets in git history. For SecureString parameters, `spec.valueFrom` references an external Kubernetes Secret—keeping secrets out of CRs and git repositories.

## Complete Examples

### Example 1: Simple String Parameter

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMParameter
metadata:
  name: log-level
  namespace: production
spec:
  configRef: general-policy
  type: String
  value: "INFO"
  description: "Application logging level"
  deletionPolicy: retain
  tags:
    Application: MyApp
    Environment: Production
```

Result:
- Parameter name: `/production-log-level` (default naming template)
- Type: String
- Value: "INFO"
- Stored unencrypted (Standard String type)

### Example 2: Hierarchical Parameter with KMS

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMParameter
metadata:
  name: db-password
  namespace: production
spec:
  configRef: secure  # Use secure profile for encryption
  type: SecureString
  valueFrom:
    secretKeyRef:
      name: db-secrets
      key: password
  keyRef:
    from:
      name: production-db-key  # Reference to KMSKey CR
  tier: Advanced
  description: "Production database password"
  tags:
    Service: Database
    Sensitivity: High
```

Result:
- Parameter name: `/production/db/db-password` (if naming template is `/{namespace}/db/{name}`)
- Type: SecureString (encrypted with KMS key)
- Value: Fetched from `db-secrets` Kubernetes Secret at creation time
- Tier: Advanced (8 KB limit)
- Deletion: Retain AWS parameter when CR is deleted

### Example 3: Parameter with Validation Pattern

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMParameter
metadata:
  name: api-port
  namespace: services
spec:
  type: String
  value: "8080"
  allowedPattern: "^[0-9]{1,5}$"  # Regex: 1-5 digits
  description: "API service port number"
  tags:
    Service: API
```

## Tier Management

Parameter tiers control storage limits and cost:

| Tier | Max Size | Cost | Use Case | Upgrade |
|---|---|---|---|---|
| **Standard** | 4 KB | Free | Most parameters | → Advanced (one-way) |
| **Advanced** | 8 KB | Charged | Large configs | ← Cannot downgrade |
| **Intelligent-Tiering** | 8 KB | Auto-determined | Varies with usage | Auto |

### Tier One-Way Upgrade

Standard → Advanced is **irreversible**:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMParameter
metadata:
  name: large-config
  namespace: production
spec:
  type: String
  value: "..."  # > 4 KB value
  tier: Advanced  # Upgrade from Standard
  # WARNING: Cannot downgrade to Standard without delete + recreate
```

To revert, delete and recreate the parameter (causes data loss). Platform teams should set `tier` defaults to avoid accidental upgrades:

```yaml
# In SSMConfig (general-policy profile)
spec:
  mandatory:
    tier: Standard  # Enforce Standard unless explicitly overridden
```

## Parameter Naming

Parameters support hierarchical paths for organization:

```yaml
# Without naming template
apiVersion: aws.kropath.run/v1alpha1
kind: SSMParameter
metadata:
  name: db-password
  namespace: production
spec:
  value: "secret"
  # Default naming template: "{namespace}-{name}"
  # Resolves to: "production-db-password"
---
# With custom naming template
apiVersion: aws.kropath.run/v1alpha1
kind: SSMParameter
metadata:
  name: db-password
  namespace: production
spec:
  value: "secret"
  tags:
    env: prod
    service: database
  # With template: "/{tag.env}/{tag.service}/{name}"
  # Resolves to: "/prod/database/db-password"
```

### Reserved Prefixes

Parameter names cannot start with:
- `aws`
- `ssm`

Maximum length: 1011 characters (excluding ARN prefix).

## KMS Integration

### Direct KMS Key Reference

Use the key ARN directly:

```yaml
spec:
  type: SecureString
  keyID: "arn:aws:kms:us-east-1:123456789012:key/12345678-..."
  valueFrom:
    secretKeyRef:
      name: api-key-secret
      key: key
```

### Cross-Resource KMS Reference

Reference a `KMSKey` CR using ACK's reference mechanism:

```yaml
spec:
  type: SecureString
  keyRef:
    from:
      name: encryption-key  # KMSKey CR in same namespace
  valueFrom:
    secretKeyRef:
      name: api-key-secret
      key: key
```

The controller resolves `keyRef.from.name` to the KMS key ARN at creation time.

### KMS Governance Cascade

When both KropathConfig and SSMConfig set KMS requirements, the cascade determines the final key:

1. **Global KropathConfig mandatory.ssm.keyID** → Enforced org-wide
2. **Local KropathConfig mandatory.ssm.keyID** → Enforced in namespace
3. **SSMConfig (profile) mandatory.keyID** → Profile-specific requirement
4. **Instance spec.keyID** → Parameter's choice
5. **SSMConfig (profile) defaults.keyID** → Profile suggestion
6. **AWS default key** → AWS's default KMS key for SecureString

## Status Fields

After creation, retrieve parameter details:

```yaml
status:
  resourceName: "prod-db-password"  # effectiveName
  namingStatus: "valid"             # "valid" | "invalid-unresolved-tokens"
  parameterVersion: "1"             # Parameter version number
  predictedArn: "arn:aws:ssm:us-east-1:123456789012:parameter/prod-db-password"
  ackResourceMetadata:
    arn: "arn:aws:ssm:us-east-1:123456789012:parameter/prod-db-password"
```

**Note:** `SecureString` parameter values are never exposed in status—ACK does not return encrypted values, even in status.

## Immutability

After creation, these fields cannot be changed:

- **`type`** — Parameter type is locked; String → StringList conversion requires deletion + recreation

Example:

```bash
$ kubectl patch ssmparameter my-param --patch '{"spec":{"type":"StringList"}}'
# Error: type is immutable after creation
```

## Validation Rules

Kropath enforces these rules via `x-kubernetes-validations`:

1. **Exactly one of `value` or `valueFrom` must be set**
   - Cannot leave both empty
   - Cannot set both

2. **`type: SecureString` requires `valueFrom`**
   - `spec.value` is rejected for SecureString
   - Must use `spec.valueFrom.secretKeyRef`

3. **`type: String/StringList` requires `value`**
   - `spec.valueFrom` is rejected
   - Must use plaintext `spec.value`

4. **`keyID` and `keyRef` are mutually exclusive**
   - Choose one approach: direct ARN or CR reference
   - Cannot set both

## Multiple Parameters in One Manifest

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: SSMParameter
metadata:
  name: app-config
  namespace: production
spec:
  type: String
  value: |
    {
      "database": "prod-db",
      "cache": "redis-prod"
    }
---
apiVersion: aws.kropath.run/v1alpha1
kind: SSMParameter
metadata:
  name: api-key
  namespace: production
spec:
  type: SecureString
  valueFrom:
    secretKeyRef:
      name: api-credentials
      key: key
  keyID: "arn:aws:kms:us-east-1:123456789012:key/..."
```

## Best Practices

1. **Use SecureString for sensitive data** — Encrypt passwords, API keys, tokens
2. **Store SecureString values in Kubernetes Secrets** — Use `valueFrom`, never `value`
3. **Use hierarchical naming** — Organize parameters by environment or service
4. **Validate with `allowedPattern`** — Enforce format constraints for values
5. **Apply governance profiles** — Let `SSMConfig` enforce encryption and tier requirements
6. **Be cautious with tier upgrades** — Standard → Advanced is irreversible
7. **Use `retain` deletion policy** — Default; prevents accidental parameter deletion
8. **Tag for operations** — Include service, environment, sensitivity metadata
9. **Avoid large parameters** — Use Advanced tier (8 KB max); for larger data, use S3
10. **Reference from applications** — Applications fetch parameters via AWS SDK at runtime

## Troubleshooting

**Parameter creation fails with "SecureString requires valueFrom"**
- You specified `type: SecureString` with `spec.value`
- Change to use `spec.valueFrom.secretKeyRef` instead

**KMS key not found**
- Verify `keyID` is correct (ARN, key ID, or alias)
- Check IAM permissions on the key
- If using `keyRef`, verify the `KMSKey` CR exists in the same namespace

**Tier upgrade fails**
- Ensure value size fits Advanced tier (8 KB max)
- Verify IAM permissions allow `ssm:PutParameter` with tier modification

**Naming validation fails**
- Check `status.namingStatus` for unresolved tokens
- Verify all `{tag.*}` references exist in `spec.tags`

## Next Steps

- [SSMConfig Governance](./ssmconfig.md) — Understanding parameter governance
- [KMS Integration](../kms/cross-family-integration.md) — Using KMS keys with parameters
- [AWS Parameter Store User Guide](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html) — AWS documentation
