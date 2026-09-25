---
title: MQConfig — Governance for Message Brokers
description: "The `MQConfig` resource defines governance policies for Amazon MQ brokers."
doc_type: reference
---
# MQConfig — Governance for Message Brokers

The `MQConfig` resource defines governance policies for Amazon MQ brokers. It establishes organization-wide or environment-specific constraints on broker configuration: engine type (ActiveMQ or RabbitMQ), deployment topology, encryption, logging, user authentication, and naming conventions. Platform teams deploy named profiles (`general-policy`, `production`, `pci`) to enforce compliance across all brokers in a namespace.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `metadata.name` | string | required | Profile name; selected by broker via `spec.configRef` |
| `metadata.namespace` | string | `"kro-system"` | Global profiles are deployed to `kro-system`; local profiles per namespace |

### Mandatory Tier (Policy Enforcement)

Mandatory fields **override** instance specifications — platform requirements that instances cannot bypass.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `spec.mandatory.engineType` | string | `""` | Force all brokers to ActiveMQ or RabbitMQ; `""` = not enforced |
| `spec.mandatory.authenticationStrategy` | string | `""` | Force SIMPLE or LDAP (ActiveMQ only); `""` = not enforced |
| `spec.mandatory.deploymentMode` | string | `""` | Force single-instance or multi-AZ topology; `""` = not enforced |
| `spec.mandatory.hostInstanceType` | string | `""` | Force EC2 instance type (e.g., `mq.m5.xlarge`); `""` = not enforced |
| `spec.mandatory.publiclyAccessible` | boolean | nil | Force public/private network access; nil = not enforced |
| `spec.mandatory.autoMinorVersionUpgrade` | boolean | nil | Force automatic minor version upgrades; nil = not enforced |
| `spec.mandatory.logsGeneral` | boolean | nil | Force CloudWatch general logging; nil = not enforced |
| `spec.mandatory.logsAudit` | boolean | nil | Force CloudWatch audit logging (ActiveMQ only); nil = not enforced |
| `spec.mandatory.encryptionUseAWSOwnedKey` | boolean | nil | Force AWS-owned or customer-managed KMS key; nil = not enforced |
| `spec.mandatory.storageType` | string | `""` | Force storage type (efs or io1, ActiveMQ only); `""` = not enforced |
| `spec.mandatory.namingTemplate` | string | `""` | Force naming pattern (e.g., `corp-{namespace}-{name}`); `""` = not enforced |
| `spec.mandatory.tags` | map | `{}` | Mandatory cloud tags — instances cannot remove these |
| `spec.mandatory.syncedLabels` | map | `{}` | Labels that sync to both Kubernetes labels AND cloud tags (prefixed `aws.kropath.run/`) |
| `spec.mandatory.syncedAnnotations` | map | `{}` | Annotations for Kubernetes metadata |

### Defaults Tier (Sensible Defaults)

Defaults apply only when an instance specification is empty — providing baseline values without blocking overrides.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `spec.defaults.engineType` | string | `""` | Default engine type; overridable by instance |
| `spec.defaults.authenticationStrategy` | string | `""` | Default auth strategy |
| `spec.defaults.deploymentMode` | string | `""` | Default topology; instances can override |
| `spec.defaults.hostInstanceType` | string | `""` | Default EC2 instance type |
| `spec.defaults.publiclyAccessible` | boolean | nil | Default public/private access |
| `spec.defaults.autoMinorVersionUpgrade` | boolean | nil | Default auto-upgrade policy |
| `spec.defaults.logsGeneral` | boolean | nil | Default general logging |
| `spec.defaults.logsAudit` | boolean | nil | Default audit logging (ActiveMQ only) |
| `spec.defaults.encryptionUseAWSOwnedKey` | boolean | nil | Default encryption key type |
| `spec.defaults.storageType` | string | `""` | Default storage type |
| `spec.defaults.namingTemplate` | string | `"{namespace}-{name}"` | Default naming pattern — cluster-scoped broker names |
| `spec.defaults.tags` | map | `{}` | Baseline cloud tags; instances can add tags but cannot remove baseline |
| `spec.defaults.syncedLabels` | map | `{}` | Baseline synced labels |
| `spec.defaults.syncedAnnotations` | map | `{}` | Baseline synced annotations |

## Governance Cascade

Broker resources use a ten-level cascade to resolve fields:

```
KropathConfig.mandatory → MQConfig.mandatory → Instance spec → MQConfig.defaults → KropathConfig.defaults → RGD built-in default
```

**Example:**

A broker in namespace `messaging-prod` with no `spec.engineType` set:
1. Check `KropathConfig.mandatory.mq.engineType` — if set, use it (organization requirement)
2. Check `MQConfig/production.spec.mandatory.engineType` — if set, use it (profile requirement)
3. Check `spec.engineType` on the broker — if set, use it (instance override)
4. Check `MQConfig/production.spec.defaults.engineType` — if set, use it (profile default)
5. Check `KropathConfig.defaults.mq.engineType` — if set, use it (organization default)
6. Use RGD built-in: either a hard error (required field) or a provider default

**Note:** The fields `hostInstanceType` and `namingTemplate` are governed exclusively by `MQConfig` — they do not appear in `KropathConfig` and cannot be overridden in individual broker instances. Use `MQConfig` profiles to define instance types and naming conventions across your brokers.

## Naming Convention

Broker names are AWS account-scoped — they must be unique within your account but not globally.

**Default template:** `{namespace}-{name}` → e.g., `messaging-prod-orders-broker`

**Available tokens:**
- `{namespace}` — Kubernetes namespace
- `{name}` — Kubernetes resource name
- `{account_id}` — AWS account ID
- `{region}` — AWS region
- `{configRef}` — MQConfig profile name
- `{tag.<key>}` — Replace with tag value (e.g., `{tag.env}` → `prod` if tags include `env: prod`)

**AWS constraints:** 1–50 characters, `a-zA-Z0-9_-` only. Template must resolve to a valid name.

## Complete Examples

### General Policy — Development and Testing

A permissive profile for development environments:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MQConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  defaults:
    engineType: ACTIVEMQ
    deploymentMode: SINGLE_INSTANCE
    hostInstanceType: mq.t2.micro
    authenticationStrategy: SIMPLE
    publiclyAccessible: false
    autoMinorVersionUpgrade: true
    logsGeneral: false
    logsAudit: false
    encryptionUseAWSOwnedKey: true
    storageType: efs
    namingTemplate: "{namespace}-{name}"
    tags:
      team: platform
      cost-center: engineering
```

**Result:**
- Brokers default to single-node ActiveMQ
- Developers can override any field
- Baseline tags applied to all brokers

### Production — Strict Governance

A production profile with mandatory compliance requirements:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MQConfig
metadata:
  name: production
  namespace: kro-system
spec:
  mandatory:
    # Compliance requirements — cannot override
    deploymentMode: ACTIVE_STANDBY_MULTI_AZ
    publiclyAccessible: false
    autoMinorVersionUpgrade: false
    logsGeneral: true
    logsAudit: true
    encryptionUseAWSOwnedKey: false  # Mandate customer-managed KMS
    tags:
      environment: production
      compliance: sox
      backup-policy: daily
    syncedLabels:
      critical: "true"
  defaults:
    # Sensible defaults for production brokers
    engineType: RABBITMQ
    hostInstanceType: mq.m5.large
    authenticationStrategy: SIMPLE
    storageType: efs
    namingTemplate: "prod-{namespace}-{name}"
```

**Result:**
- All production brokers must be multi-AZ (high availability)
- Private network access enforced
- Customer-managed encryption mandatory
- Audit logging required for compliance
- Brokers inherit compliance tags

### PCI-Compliance Profile

A locked-down profile for payment processing:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MQConfig
metadata:
  name: pci
  namespace: kro-system
spec:
  mandatory:
    engineType: ACTIVEMQ
    deploymentMode: ACTIVE_STANDBY_MULTI_AZ
    hostInstanceType: mq.m5.xlarge
    authenticationStrategy: LDAP
    publiclyAccessible: false
    autoMinorVersionUpgrade: false
    logsGeneral: true
    logsAudit: true
    encryptionUseAWSOwnedKey: false
    storageType: io1
    namingTemplate: "pci-{namespace}-{name}"
    tags:
      environment: production
      compliance: pci-dss
      data-classification: restricted
    syncedLabels:
      pci: "true"
      audit-required: "true"
```

**Result:**
- All fields locked — no instance override possible
- LDAP authentication for user management
- High-performance storage (io1) for transaction volume
- Multi-AZ for availability
- Audit logging and encryption required

**Note:** LDAP server metadata (server URL, directory structure, service account credentials) must be configured directly on the AWS broker after creation, as it is not exposed in the Kubernetes resource specification.

## Key Behaviors

- **Mutual exclusivity:** Each scalar field (string or boolean) must appear in **either** the `mandatory` tier **or** the `defaults` tier, not both. Maps (`tags`, `syncedLabels`, `syncedAnnotations`) can appear in both tiers and merge additively.
- **Boolean semantics:** Boolean fields use `nil` (absent) to mean "not enforced." Only set a boolean to `true` or `false` to enforce a value.
- **Tag merging:** `mandatory.tags` and `defaults.tags` merge automatically. Mandatory tags take precedence on key conflicts. Instances can add their own tags but cannot remove mandatory tags.
- **Label sync:** `syncedLabels` appear as both Kubernetes labels (with `aws.kropath.run/` prefix) and as AWS cloud tags, enabling consistent metadata across platforms.
- **Profile fallback:** If a broker references a profile that does not exist, it falls back to `general-policy`. Ensure `general-policy` always exists in `kro-system`.

## Related Resources

- [MQBroker](mqbroker.md) — Create and manage individual message brokers
- [KropathConfig](../../../concepts/controller/label-operator.md) — Organization-wide configuration defaults for all resource types
