---
title: MQBroker — Amazon MQ Message Brokers
description: "The `MQBroker` resource creates and manages Amazon MQ brokers (ActiveMQ or RabbitMQ)."
doc_type: reference
---
# MQBroker — Amazon MQ Message Brokers

The `MQBroker` resource creates and manages Amazon MQ brokers (ActiveMQ or RabbitMQ). It provides a simplified interface to Amazon MQ with built-in governance, secure secret management for broker users, multi-AZ deployment options, encryption, CloudWatch logging, and automatic naming based on governance profiles.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects the `MQConfig` governance profile (e.g., `production`, `pci`) |
| `nameOverride` | string | `""` | Bypasses naming template; sets a custom broker name directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` keeps the broker in AWS when the CR is deleted; `"delete"` removes the broker |

### Engine Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `engineType` | string | `""` | `"ACTIVEMQ"` or `"RABBITMQ"`; empty falls through to governance |
| `engineVersion` | string | `""` | Broker engine version (e.g., `"5.17.6"`, `"3.12.0"`); empty uses AWS default |
| `authenticationStrategy` | string | `""` | `"SIMPLE"` or `"LDAP"` (ActiveMQ only); empty falls through to governance |

### Deployment Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `deploymentMode` | string | `""` | `"SINGLE_INSTANCE"`, `"ACTIVE_STANDBY_MULTI_AZ"`, or `"CLUSTER_MULTI_AZ"` (RabbitMQ only); empty falls through to governance |
| `hostInstanceType` | string | `""` | EC2 instance type (e.g., `"mq.m5.large"`); empty falls through to governance |

### Network Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `publiclyAccessible` | boolean | nil | Expose broker to the internet; nil falls through to governance |
| `securityGroupIDs` | array | `[]` | AWS security group IDs (1–125); mutually exclusive with `securityGroupRefs` |
| `securityGroupRefs` | array | `[]` | Kubernetes references to security groups; each has `from.name` and `from.namespace` |
| `subnetIDs` | array | `[]` | AWS subnet IDs for broker placement (constraints depend on `deploymentMode`) |
| `subnetRefs` | array | `[]` | Kubernetes references to subnets |

**Subnet constraints:**
- `SINGLE_INSTANCE`: exactly 1 subnet
- `ACTIVE_STANDBY_MULTI_AZ` (ActiveMQ): exactly 2 subnets in different AZs
- `CLUSTER_MULTI_AZ` (RabbitMQ): no subnets required when publicly accessible; at least 1 subnet required when NOT publicly accessible

### Encryption and Keys

| Field | Type | Default | Purpose |
|---|---|---|---|
| `encryptionUseAWSOwnedKey` | boolean | nil | Use AWS-managed KMS key (true) or customer-managed key (false); nil falls through to governance |
| `encryptionKMSKeyID` | string | `""` | Customer-managed KMS key ID or ARN; required when `encryptionUseAWSOwnedKey: false` |

### Logging

| Field | Type | Default | Purpose |
|---|---|---|---|
| `logsGeneral` | boolean | nil | Enable CloudWatch general broker logs; nil falls through to governance |
| `logsAudit` | boolean | nil | Enable CloudWatch audit logs (ActiveMQ only); nil falls through to governance |

### Storage (ActiveMQ Only)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `storageType` | string | `""` | `"efs"` or `"io1"` (ActiveMQ only); empty falls through to governance |

### Maintenance

| Field | Type | Default | Purpose |
|---|---|---|---|
| `autoMinorVersionUpgrade` | boolean | nil | Allow AWS to automatically upgrade minor versions; nil falls through to governance; required true for ActiveMQ ≥ 5.18 and RabbitMQ ≥ 3.13 |
| `maintenanceWindowDay` | string | `""` | Day of week (MONDAY–SUNDAY); empty uses AWS default |
| `maintenanceWindowTime` | string | `""` | Time in HH:MM format; empty uses AWS default |
| `maintenanceWindowTZ` | string | `""` | Timezone (e.g., `"UTC"`, `"US/Eastern"`); empty uses AWS default |

### Broker Users

| Field | Type | Default | Purpose |
|---|---|---|---|
| `users` | array | required | List of broker users with passwords stored in Kubernetes Secrets |
| `users[].username` | string | required | Username |
| `users[].passwordSecretRef` | object | required | Reference to Kubernetes Secret containing broker password |
| `users[].passwordSecretRef.key` | string | required | Key within the Secret (e.g., `"password"`) |
| `users[].passwordSecretRef.name` | string | required | Secret name |
| `users[].passwordSecretRef.namespace` | string | required | Secret namespace |
| `users[].consoleAccess` | boolean | `false` | Allow ActiveMQ Web Console access (ActiveMQ only) |
| `users[].groups` | array | `[]` | ActiveMQ user groups (up to 20; ActiveMQ only) |

### ActiveMQ Configuration (ActiveMQ Only)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configurationID` | string | `""` | Pre-existing ActiveMQ configuration ID; empty uses AWS default |
| `configurationRevision` | integer | 0 | Configuration revision number; 0 = latest available |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

### Idempotency

| Field | Type | Default | Purpose |
|---|---|---|---|
| `creatorRequestID` | string | `""` | Unique UUID for idempotent creation (AWS will reject duplicate requests with same ID) |

## Status Outputs

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | Effective broker name (resolved from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if ready, `"invalid-unresolved-tokens"` if template has unresolved placeholders |
| `brokerARN` | string | AWS broker ARN (e.g., `arn:aws:mq:us-east-1:123456789:broker:prod-orders:broker-uuid`); populated only after broker reaches RUNNING state |
| `brokerID` | string | AWS-assigned broker ID (UUID) |
| `brokerState` | string | Broker lifecycle state: `CREATION_IN_PROGRESS`, `CREATION_FAILED`, `RUNNING`, `REBOOT_IN_PROGRESS`, `DELETION_IN_PROGRESS` |
| `brokerInstances` | array | Allocated broker instance details (endpoint URLs, IP addresses, console URLs) |
| `conditions[]` | array | Standard kro conditions; may include governance enforcement notes |

**Note:** `status.predictedArn` is intentionally **not** provided. MQ broker ARNs include an AWS-assigned UUID that cannot be predicted before creation. Use `status.brokerARN` (available after the broker reaches RUNNING state) for cross-resource references.

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

**Immutability:** Broker names are immutable after creation — Amazon MQ does not support renaming. Changing `nameOverride` or the naming template will not rename an existing broker.

## Complete Examples

### Single-Node Development Broker

A simple ActiveMQ broker for development and testing:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MQBroker
metadata:
  name: dev-broker
  namespace: development
spec:
  configRef: general-policy
  engineType: ACTIVEMQ
  engineVersion: "5.17.6"
  deploymentMode: SINGLE_INSTANCE
  hostInstanceType: mq.t2.micro
  publiclyAccessible: false
  authenticationStrategy: SIMPLE
  logsGeneral: true
  logsAudit: false
  encryptionUseAWSOwnedKey: true
  subnetIDs:
    - subnet-12345678
  users:
    - username: admin
      passwordSecretRef:
        name: dev-broker-creds
        key: password
      consoleAccess: true
  tags:
    environment: development
    team: platform
  deletionPolicy: delete
```

**Result:**
- Single-node ActiveMQ broker for development
- Minimal cost (micro instance)
- Web console access for troubleshooting
- Auto-deleted when resource is removed

### High-Availability Production Broker

A multi-AZ ActiveMQ broker with strict governance:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MQBroker
metadata:
  name: orders-broker
  namespace: messaging-prod
spec:
  configRef: production
  engineType: ACTIVEMQ
  engineVersion: "5.18.3"
  deploymentMode: ACTIVE_STANDBY_MULTI_AZ
  hostInstanceType: mq.m5.xlarge
  authenticationStrategy: SIMPLE
  publiclyAccessible: false
  autoMinorVersionUpgrade: false
  logsGeneral: true
  logsAudit: true
  encryptionUseAWSOwnedKey: false
  encryptionKMSKeyID: arn:aws:kms:us-east-1:123456789:key/12345678-1234-1234-1234-123456789abc
  subnetIDs:
    - subnet-12345678  # AZ 1
    - subnet-87654321  # AZ 2
  maintenanceWindowDay: SUNDAY
  maintenanceWindowTime: "02:00"
  maintenanceWindowTZ: UTC
  storageType: io1
  users:
    - username: admin
      passwordSecretRef:
        name: orders-broker-admin
        key: password
      consoleAccess: true
      groups:
        - admins
    - username: orders-app
      passwordSecretRef:
        name: orders-app-creds
        key: password
      groups:
        - producers
  tags:
    environment: production
    compliance: sox
    cost-center: platform-engineering
  syncedLabels:
    critical: "true"
    backup-policy: daily
  deletionPolicy: retain
  creatorRequestID: "550e8400-e29b-41d4-a716-446655440000"
```

**Result:**
- Multi-AZ broker for high availability and automatic failover
- Customer-managed KMS encryption
- Audit logging for compliance
- Two users: admin with console access and app user with producer role
- Protected from accidental deletion
- Maintenance window on Sunday morning

### RabbitMQ Cluster for High Throughput

A clustered RabbitMQ broker for distributed message processing:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MQBroker
metadata:
  name: events-broker
  namespace: messaging-prod
spec:
  configRef: production
  engineType: RABBITMQ
  engineVersion: "3.12.0"
  deploymentMode: CLUSTER_MULTI_AZ
  hostInstanceType: mq.m6g.2xlarge
  autoMinorVersionUpgrade: false
  logsGeneral: true
  logsAudit: false
  encryptionUseAWSOwnedKey: true
  subnetIDs:
    - subnet-aaaaaaaa
    - subnet-bbbbbbbb
    - subnet-cccccccc
  securityGroupIDs:
    - sg-12345678
  users:
    - username: admin
      passwordSecretRef:
        name: events-broker-admin
        key: password
      consoleAccess: true
    - username: event-producer
      passwordSecretRef:
        name: event-producer-creds
        key: password
    - username: event-consumer
      passwordSecretRef:
        name: event-consumer-creds
        key: password
  nameOverride: "prod-events-primary"
  tags:
    environment: production
    workload: high-throughput
    cost-center: data-platform
  deletionPolicy: retain
```

**Result:**
- RabbitMQ cluster across 3 AZs for maximum availability and throughput
- High-memory instance (2xlarge) for large message volumes
- Three users with different roles
- AWS-managed encryption (default)

## Governance Cascade

Broker configurations follow a governance cascade that merges organization-wide (`KropathConfig`) and profile-specific (`MQConfig`) settings with instance specifications.

**Resolution order:**
1. Mandatory tier (MQConfig or KropathConfig) — enforced, instance cannot override
2. Instance specification (`spec`) — instance-specific override
3. Defaults tier (MQConfig or KropathConfig) — fallback when instance is empty
4. RGD built-in default — final fallback (e.g., `SIMPLE` for auth strategy, `false` for public access)

**Example:** If `MQConfig/production` has `mandatory.encryptionUseAWSOwnedKey: false` (mandate customer-managed KMS), the broker cannot set `encryptionUseAWSOwnedKey: true` — the mandatory policy always wins.

## Key Behaviors

- **Boolean governance semantics:** Boolean fields like `publiclyAccessible` use `nil` (absent) to mean "not enforced." Only set to `true` or `false` to enforce a value. This distinguishes three states: explicit true, explicit false, and unset.
- **Tag merging:** `spec.tags` merge with governance tags. Mandatory tags from `MQConfig` take precedence on key conflicts; defaults are additive.
- **Label sync:** `syncedLabels` appear as both Kubernetes labels (prefixed `aws.kropath.run/`) and AWS cloud tags, enabling consistent metadata across platforms.
- **Password security:** Broker user passwords are stored in Kubernetes Secrets and referenced via `passwordSecretRef`, never embedded as plaintext in the CR.
- **User limits:** RabbitMQ requires exactly one admin user at creation. ActiveMQ supports multiple admin users.
- **LDAP limitation:** ActiveMQ LDAP authentication is available via `authenticationStrategy: LDAP`. LDAP server metadata (server URL, directory structure, service account credentials) must be configured directly on the underlying AWS broker — it is not part of the MQBroker spec.
- **Immutable fields after creation:** `engineType`, `deploymentMode`, and `publiclyAccessible` cannot be changed after the broker is created. Amazon MQ rejects updates to these fields.

## Related Resources

- [MQConfig](mqconfig.md) — Governance profiles for broker configuration
- [KropathConfig](../../../concepts/resources/label-operator.md) — Organization-wide configuration
