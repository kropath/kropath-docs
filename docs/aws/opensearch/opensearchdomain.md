# OpenSearchDomain — Managed Search Domains

The `OpenSearchDomain` resource provisions managed Amazon OpenSearch Service domains. It handles cluster provisioning, storage configuration, encryption, HTTPS/TLS, fine-grained access control, VPC networking, and logging. Governance settings cascade from a selected `OpenSearchConfig` profile.

## Purpose

`OpenSearchDomain` provides a Kubernetes-native way to manage OpenSearch Service domains:

- **Cluster topology** — Configure node types, count, dedicated masters, multi-AZ deployment
- **Storage** — Set EBS volume type, size, IOPS (gp3, io1)
- **Encryption and security** — Configure encryption at rest, node-to-node encryption, HTTPS, TLS policy, fine-grained access control
- **Networking** — Public endpoint or VPC-only private access
- **Observability** — CloudWatch logs for various log types
- **Naming and tagging** — Dynamic naming templates and resource tags

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `OpenSearchConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the domain name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` keeps AWS domain; `"delete"` removes it |

### Engine Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `engineVersion` | string | `""` | OpenSearch version (e.g., `"OpenSearch_2.9"`); empty = use governance defaults |

### Cluster Topology

| Field | Type | Default | Purpose |
|---|---|---|---|
| `instanceType` | string | `""` | Node type (e.g., `"m6g.large.search"`, `"r6g.xlarge.search"`) |
| `instanceCount` | integer | `0` | Number of data nodes; 0 = use governance defaults |
| `dedicatedMasterEnabled` | boolean | `false` | Use dedicated master nodes |
| `dedicatedMasterType` | string | `""` | Master node type (if enabled) |
| `dedicatedMasterCount` | integer | `0` | Number of master nodes |
| `zoneAwarenessEnabled` | boolean | `false` | Deploy across availability zones |
| `availabilityZoneCount` | integer | `0` | Number of AZs (2 or 3); 0 = AWS default |
| `multiAZWithStandbyEnabled` | boolean | `false` | Multi-AZ with standby nodes (3 AZs) |

### Storage

| Field | Type | Default | Constraints |
|---|---|---|---|
| `ebsEnabled` | boolean | `true` | Use EBS storage (recommended) |
| `ebsVolumeType` | string | `"gp3"` | `standard`, `gp2`, `gp3`, or `io1` |
| `ebsVolumeSize` | integer | `0` | GiB per node; 0 = use governance defaults |
| `ebsIops` | integer | `0` | IOPS (io1/gp3 only); 0 = AWS default |
| `ebsThroughput` | integer | `0` | MiB/s (gp3 only); 0 = AWS default |

**Storage tiers (not governance-controlled):**

| Field | Type | Default | Purpose |
|---|---|---|---|
| `warmEnabled` | boolean | `false` | Enable warm storage (older indices) |
| `warmType` | string | `""` | Warm node type (if enabled) |
| `warmCount` | integer | `0` | Number of warm nodes |
| `coldStorageEnabled` | boolean | `false` | Enable cold storage (archive tier) |

### Security

| Field | Type | Default | Governance |
|---|---|---|---|
| `encryptionAtRestEnabled` | boolean | `true` | Cascades from config if not set |
| `encryptionAtRestKmsKeyID` | string | `""` | KMS key ARN for customer-managed encryption; empty = AWS-managed |
| `nodeToNodeEncryptionEnabled` | boolean | `true` | Cascades from config if not set |
| `enforceHTTPS` | boolean | `true` | Cascades from config if not set |
| `tlsSecurityPolicy` | string | `""` | TLS version/ciphers; empty = cascade from config |
| `advancedSecurityEnabled` | boolean | `false` | Enable fine-grained access control |
| `internalUserDatabaseEnabled` | boolean | `false` | Use internal user database (if FGAC enabled) |
| `masterUserARN` | string | `""` | IAM role for master user (FGAC) |
| `masterUserName` | string | `""` | Internal user for master (FGAC + internal DB) |
| `masterUserPassword` | object | `nil` | Secret ref for master password (e.g., `{name: "os-secret", key: "password"}`) |

### Access Control

| Field | Type | Default | Purpose |
|---|---|---|---|
| `accessPolicies` | string | `""` | IAM policy document JSON; mutually exclusive with `domainPolicyRef` |
| `domainPolicyRef` | string | `""` | Local `PolicyDocument` CR name; mutually exclusive with `accessPolicies` |
| `ipAddressType` | string | `"ipv4"` | `"ipv4"` or `"dualstack"`; immutable after creation |

### VPC Networking

Leave empty for public endpoint; populate for VPC-only private access.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `vpcSubnetIDs` | array | `[]` | VPC subnet IDs for domain nodes; empty = public endpoint |
| `vpcSecurityGroupIDs` | array | `[]` | Security group IDs; empty = default VPC SG |

### Cognito Authentication

| Field | Type | Default | Purpose |
|---|---|---|---|
| `cognitoEnabled` | boolean | `false` | Enable Cognito user pool authentication |
| `cognitoUserPoolID` | string | `""` | Cognito user pool ID |
| `cognitoIdentityPoolID` | string | `""` | Cognito identity pool ID |
| `cognitoRoleARN` | string | `""` | IAM role for Cognito |

### Logging

| Field | Type | Default | Purpose |
|---|---|---|---|
| `logPublishingOptions` | map | `{}` | Log type → CloudWatch configuration map |

Log types: `INDEX_SLOW_LOGS`, `SEARCH_SLOW_LOGS`, `ES_APPLICATION_LOGS`, `AUDIT_LOGS`

Example:

```yaml
logPublishingOptions:
  INDEX_SLOW_LOGS:
    cloudWatchLogsLogGroupARN: "arn:aws:logs:us-east-1:123:log-group:/aws/opensearch/index-slow"
    enabled: true
  SEARCH_SLOW_LOGS:
    cloudWatchLogsLogGroupARN: "arn:aws:logs:us-east-1:123:log-group:/aws/opensearch/search-slow"
    enabled: true
```

### Auto-Tune and Maintenance

| Field | Type | Default | Governance |
|---|---|---|---|
| `autoTuneDesiredState` | string | `""` | `ENABLED` or `DISABLED`; empty = cascade from config |
| `autoTuneUseOffPeakWindow` | boolean | `false` | Use off-peak window for auto-tune |
| `offPeakWindowEnabled` | boolean | `false` | Define an off-peak maintenance window |
| `offPeakWindowStartHours` | integer | `0` | Window start hour (0–23) |
| `offPeakWindowStartMinutes` | integer | `0` | Window start minute |
| `autoSoftwareUpdateEnabled` | boolean | `false` | Auto-apply patch updates during off-peak window |

### Tags and Governance

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS resource tags; merged with config tags |
| `syncedLabels` | map | `{}` | Labels synced to K8s and cloud resource tags |
| `syncedAnnotations` | map | `{}` | Annotations synced to K8s metadata |

## Status Fields

After creation, the domain reports:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | Effective domain name after naming template substitution |
| `namingStatus` | string | `"valid"` or `"invalid-unresolved-tokens"` (if template has unresolved tokens) |
| `predictedArn` | string | Domain ARN (e.g., `arn:aws:es:us-east-1:123:domain/observability-logs`) |
| `conditions` | array | Standard Kubernetes conditions (Ready, Reconciling, etc.) |

## Examples

### Single-Node Development Domain

For testing, with minimal resources:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchDomain
metadata:
  name: dev-logs
  namespace: observability
spec:
  configRef: development
  instanceType: "t3.small.search"
  instanceCount: 1
  ebsVolumeType: "gp3"
  ebsVolumeSize: 20
  encryptionAtRestEnabled: false  # Dev override
  nodeToNodeEncryptionEnabled: false
  enforceHTTPS: false
```

### Production HA Domain with Encryption

Multi-AZ deployment with customer-managed encryption:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchDomain
metadata:
  name: prod-logs
  namespace: observability
spec:
  configRef: production
  instanceType: "m6g.large.search"
  instanceCount: 3
  dedicatedMasterEnabled: true
  dedicatedMasterType: "m6g.large.search"
  dedicatedMasterCount: 3
  zoneAwarenessEnabled: true
  availabilityZoneCount: 3
  multiAZWithStandbyEnabled: true
  ebsVolumeType: "gp3"
  ebsVolumeSize: 200
  ebsIops: 3000
  ebsThroughput: 125
  encryptionAtRestEnabled: true
  encryptionAtRestKmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/abc-def"
  nodeToNodeEncryptionEnabled: true
  enforceHTTPS: true
  tlsSecurityPolicy: "Policy-Min-TLS-1-2-2019-07"
  advancedSecurityEnabled: true
  masterUserARN: "arn:aws:iam::123456789012:role/opensearch-admin"
  tags:
    team: observability
    backup: daily
```

### Private VPC Domain with FGAC

VPC-only domain with fine-grained access control:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchDomain
metadata:
  name: internal-logs
  namespace: platform
spec:
  configRef: production
  nameOverride: "internal-opensearch"  # Custom name
  instanceType: "m6g.large.search"
  instanceCount: 3
  ebsVolumeSize: 100
  vpcSubnetIDs:
    - "subnet-12345678"
    - "subnet-87654321"
  vpcSecurityGroupIDs:
    - "sg-opensearch-nodes"
  advancedSecurityEnabled: true
  masterUserName: "admin"
  masterUserPassword:
    name: "opensearch-credentials"
    key: "admin-password"
  internalUserDatabaseEnabled: true
  logPublishingOptions:
    AUDIT_LOGS:
      cloudWatchLogsLogGroupARN: "arn:aws:logs:us-east-1:123:log-group:/aws/opensearch/audit"
      enabled: true
  tags:
    team: platform
    access: internal-only
```

### Domain with VPC Endpoint

For applications in other VPCs to access the domain:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchDomain
metadata:
  name: shared-logs
  namespace: observability
spec:
  configRef: production
  instanceType: "m6g.large.search"
  instanceCount: 3
  ebsVolumeSize: 100
  vpcSubnetIDs:
    - "subnet-vpc1-1"
    - "subnet-vpc1-2"
  vpcSecurityGroupIDs:
    - "sg-opensearch-provider"
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchVPCEndpoint
metadata:
  name: shared-logs-from-vpc2
  namespace: app-team
spec:
  domainRef: shared-logs  # Reference the domain
  vpcSubnetIDs:
    - "subnet-vpc2-app-1"
    - "subnet-vpc2-app-2"
  vpcSecurityGroupIDs:
    - "sg-opensearch-consumer"
```

## Governance Cascade

When resolving configuration, fields cascade through this priority:

1. **OpenSearchConfig mandatory tier** (highest priority)
2. **Domain spec** (developer choice)
3. **OpenSearchConfig defaults tier** (lowest priority)

### Boolean Field Semantics

Boolean governance fields use `false` as the "not set" sentinel. If both mandatory and defaults set a boolean to `true`, the RGD rejects the domain with a validation error (mutual exclusion). To explicitly disable a governance control, create a profile with `false` in the mandatory tier.

### Example

Config:

```yaml
spec:
  mandatory:
    encryptionAtRestEnabled: false  # Not enforced
    nodeToNodeEncryptionEnabled: true
  defaults:
    enforceHTTPS: true
```

Domain:

```yaml
spec:
  encryptionAtRestEnabled: false  # Developer choice wins; not enforced
  nodeToNodeEncryptionEnabled: false  # Mandatory true overrides
  enforceHTTPS: false  # Defaults true overrides
```

Result:

- `encryptionAtRestEnabled`: `false` (developer choice; not enforced)
- `nodeToNodeEncryptionEnabled`: `true` (mandatory wins)
- `enforceHTTPS`: `true` (defaults apply)

## Naming

The effective domain name is computed from:

1. **nameOverride** (if set) — Use this name directly
2. **namingTemplate** (if set) — Apply the template with token substitution
3. **Fallback** — Use metadata.name

### Naming Constraints

- Lowercase `a-z`, digits `0-9`, hyphens `-`
- Must start with a lowercase letter
- 3–28 characters
- Pattern: `^[a-z][a-z0-9\-]{2,27}$`

### Template Tokens

- `{name}` — CR metadata.name
- `{namespace}` — CR metadata.namespace
- `{account_id}` — AWS account ID
- `{region}` — AWS region
- `{tag.KEY}` — Value of tag KEY
- `{configRef}` — Profile name

## Deletion Behavior

| Policy | Behavior |
|---|---|
| `retain` (default) | AWS domain persists; K8s CR deleted |
| `delete` | AWS domain deleted when K8s CR deleted |

## Related Concepts

- **Governance profiles** — See [OpenSearchConfig](opensearchconfig.md)
- **VPC endpoints** — See [OpenSearchVPCEndpoint](opensearchvpcendpoint.md)
- **Access policies** — See [PolicyDocument](../resources/aws-policy-document.md)
- **Fine-grained access control** — See [OpenSearchConfig advanced security](opensearchconfig.md#security-fields)
- **Serverless alternative** — See [OpenSearchCollection](opensearchcollection.md)
