---
title: DynamoDB on kropath
description: "DynamoDB is AWS's fully managed NoSQL database service."
doc_type: reference
weight: 160
---
# DynamoDB on kropath

DynamoDB is AWS's fully managed NoSQL database service. The kropath DynamoDB family provides governance and composable resources for managing DynamoDB tables at scale.

## Resources

- **[DynamoDBConfig](dynamodbconfig.md)** — Governance profiles that define encryption, billing mode, deletion protection, PITR, and naming conventions. Platform teams create named profiles (e.g. `general-policy`, `production`, `pci`); developers select a profile via `spec.configRef` on each table.

- **[DynamoDBTable](dynamodbtable.md)** — The table resource. Developers create tables by specifying key schema, throughput, encryption, indexes, and other settings. Governance cascades from the selected `DynamoDBConfig` profile, with support for both provisioned and on-demand billing modes.

## Getting Started

### 1. Create a Governance Profile

Platform teams define governance profiles for different use cases:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DynamoDBConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    billingMode: ""
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
```

### 2. Create a Table

Developers create tables by selecting a governance profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DynamoDBTable
metadata:
  name: user-data
  namespace: app-team
spec:
  configRef: general-policy
  keySchema:
    - attributeName: userId
      keyType: HASH
  attributeDefinitions:
    - attributeName: userId
      attributeType: S
  billingMode: PAY_PER_REQUEST
```

## Key Concepts

### Two-Tier Governance

Each `DynamoDBConfig` has two tiers:

- **Mandatory tier** — Platform enforcements that override developer choices (e.g., encryption key, deletion protection, PITR)
- **Defaults tier** — Sensible defaults developers can override (e.g., billing mode, table class, naming pattern)

### Naming Templates

Tables are named using configurable templates. The default is `{namespace}-{name}`, but custom templates can include `{account_id}`, `{region}`, and `{tag.KEY}` tokens.

### Encryption Modes

- **DynamoDB-owned** — AWS managed, no extra cost, limited control
- **Customer-managed KMS** — You control the key, additional KMS charges, full control over key rotation and access

### Billing Modes

- **Provisioned** — Fixed read/write capacity; good for predictable workloads
- **On-demand** — Pay per request; good for variable workloads

### Deletion Protection

Once enabled, a table cannot be deleted via the AWS API. Useful for protecting production data from accidental deletion.

### Point-in-Time Recovery

Enables restore to any point in the last 35 days without rebuilding your table.

## Governance Cascade

The effective configuration for each table is determined by a three-tier priority:

1. **Governance mandatory tier** (highest priority) — Cannot be overridden
2. **Table spec** (middle) — Developer choice
3. **Governance defaults tier** (lowest priority) — Fallback if not specified

This ensures platform teams can enforce critical controls (compliance, encryption, deletion protection) while letting developers handle workload-specific settings.
