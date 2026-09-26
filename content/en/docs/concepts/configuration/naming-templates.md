---
title: Dynamic Tag Fields in Naming Templates
linkTitle: Naming Templates
description: "Kropath allows you to embed tag values directly into resource naming templates using the `{tag.fieldName}` placeholder syntax."
weight: 10
doc_type: concept
---

# Dynamic Tag Fields in Naming Templates

Kropath allows you to embed tag values directly into resource naming templates using the `{tag.fieldName}` placeholder syntax. This enables you to derive cloud resource names from tags defined in your resource configuration without needing to use a separate `spec.nameOverride` field.

## Overview

By default, kropath assigns names to cloud resources using a naming template like `{namespace}-{name}-{account_id}`. The dynamic tag field feature extends this by allowing you to reference any tag available in the resource's `spec.tags` field or injected by governance mandatory/default configuration.

For example, if your resource has a tag `environment: production`, you can use the template `{tag.environment}-my-app-{name}` to generate a resource name like `production-my-app-my-resource`.

## Syntax

The syntax for dynamic tag fields is:

```
{tag.fieldName}
```

Where `fieldName` is the exact key of a tag in your resource's merged tags. The placeholder is replaced with the corresponding tag value during resource reconciliation.

### Valid Template Examples

- `{tag.environment}-{name}` — Uses the `environment` tag and the resource name
- `{tag.team}-{tag.env}-bucket` — Uses two tags plus a static suffix
- `{namespace}-{tag.project}-{account_id}` — Combines namespace, a tag, and account ID
- `{tag.owner}` — Uses only the tag value as the entire name

### Multiple Placeholders

A single template can use multiple `{tag.fieldName}` placeholders, multiple standard placeholders (like `{namespace}`, `{name}`, `{account_id}`), and static text all in one template:

```
{tag.cost-center}-{tag.environment}-{namespace}-{name}
```

## Tag Resolution Order

When a naming template is evaluated, the system resolves tags from the `mergedTags` collection in a cascading order:

1. **Mandatory tags** from the governance config (`<ResourceFamily>Config` or `KropathConfig`)
2. **Instance-level tags** from `spec.tags` only
3. **Default tags** from the governance config

If a tag key exists at multiple levels (e.g., both mandatory and instance level), the mandatory value takes precedence. If a tag key does not exist at any level, the placeholder resolves to an empty string and the template validity check reports an error (see [Troubleshooting](#troubleshooting) below).

**Important:** For naming template resolution, only `spec.tags` are included in `mergedTags`. Kubernetes-level metadata like `spec.syncedLabels` and `spec.syncedAnnotations` are NOT included in the tag resolution for naming templates — they are separate cloud metadata fields. A naming template that references a tag not in `spec.tags`, governance mandatory tags, or governance defaults tags will fail validation.

### Tag Sources

Tag values available for naming templates come from a single source: `spec.tags` combined with mandatory and default tags from the governance config:

- **`spec.tags`** — Custom AWS/provider tags applied directly to the resource
- **Governance mandatory tags** — Tags enforced at the organization or profile level
- **Governance default tags** — Tags applied when not explicitly overridden

Example:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: my-bucket
  namespace: data-prod
spec:
  tags:
    environment: production
    cost-center: engineering
  # If configRef points to a profile with:
  # - defaults.namingTemplate: "{tag.environment}-{tag.cost-center}-{namespace}-{name}"
  # Then effectiveName = "production-engineering-data-prod-my-bucket"
  # 
  # NOTE: spec.syncedLabels and spec.syncedAnnotations are NOT used for naming
  # template tag resolution — only spec.tags are used.
```

## Supported Resource Families

Dynamic tag fields in naming templates are supported for all AWS resource families in kropath. This includes, but is not limited to:

**Compute & Containers:** EC2, ECS, EKS, Lambda, AutoScaling, AppScaling

**Storage:** S3, S3 Advanced, EBS, EFS, Backup

**Database & Cache:** RDS, DynamoDB, ElastiCache, DocumentDB, MemoryDB, Keyspaces

**Messaging & Events:** SQS, SNS, EventBridge, MQ, Kinesis

**Security & IAM:** IAM, KMS, WAF, Secrets Manager, ACM

**Analytics & Data:** Athena, Glue, EMR, Redshift, QuickSight, OpenSearch

**Networking:** Route53, API Gateway, VPC, Network Firewall, CloudFront

**Management & Monitoring:** CloudWatch, CloudTrail, EventBridge, SSM, Pipes

**ML & AI:** SageMaker, Bedrock

...and all other AWS services with active kropath reconciler support. See the kropath-controller [README](https://github.com/kropath/kropath-controller/blob/main/README.md) for the complete list of all 57 reconcilers and their integration status.

## Provider Constraints

Each cloud provider imposes length and character constraints on resource names. When using dynamic tag fields, ensure that the combined result of all placeholders and static text fits within the provider's limits.

### AWS S3 Buckets

- **Length:** 3–63 characters
- **Character set:** Lowercase alphanumeric and hyphens only (no uppercase letters)
- **Rules:** Must start and end with an alphanumeric character; no consecutive hyphens; cannot be an IP address format
- **Important:** Kropath automatically applies `.lowerAscii()` to the final name to ensure S3 compliance

Example:

```yaml
spec:
  configRef: general-policy  # defaults.namingTemplate: "{tag.env}-{name}"
  tags:
    env: prod
  # With metadata.name: "data-pipeline"
  # effectiveName = "prod-data-pipeline" (7 chars, valid)
```

### AWS IAM Resources

- **Length:** 1–64 characters for role and user names; 1–128 characters for group names
- **Character set:** Alphanumeric plus `+`, `=`, `,`, `.`, `@`, `-`, `_`
- **No lowercase requirement**

Example:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMRole
metadata:
  name: payments-role
  namespace: payments-prod
spec:
  type: ec2
  tags:
    environment: production
    team: payments
  # With defaults.namingTemplate: "{tag.team}-{tag.environment}-{name}"
  # effectiveName = "payments-production-payments-role" (37 chars, valid)
```

### AWS KMS Keys

KMS keys are identified by `KeyId` (a UUID-like string), not a human-readable name. However, you can apply tags to the key and reference them in the naming template for the `Alias` (friendly name):

- **Alias length:** 1–256 characters
- **Alias character set:** Alphanumeric plus `-` and `_`; customer-managed aliases must start with `alias/` prefix (the `aws/` prefix is reserved for AWS-managed keys)
- **Important:** The alias is the human-friendly identifier; the key itself has an immutable ID

Example:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: app-key
  namespace: security
spec:
  tags:
    app: payment-processor
    tier: production
  # With defaults.namingTemplate: "alias/kms-{tag.app}-{tag.tier}"
  # Alias = "alias/kms-payment-processor-production" (valid)
```

### AWS SQS Queues

- **Length:** 1–80 characters
- **Character set:** Alphanumeric plus hyphens and underscores
- **Rules:** FIFO queue names must end with `.fifo`

Example:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SQSQueue
metadata:
  name: notifications
  namespace: backend
spec:
  fifo: false
  tags:
    service: notifications
    environment: prod
  # With defaults.namingTemplate: "{tag.environment}-{tag.service}-{name}"
  # Queue name = "prod-notifications-notifications" (31 chars, valid)
```

## Examples

### Example 1: S3 Bucket with Environment Tag

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: logs-archive
  namespace: logging
spec:
  configRef: general-policy
  region: us-east-1
  tags:
    environment: production
    data-type: logs
  # Given defaults.namingTemplate: "{tag.environment}-{tag.data-type}-{namespace}-{name}"
  # effectiveName = "production-logs-logging-logs-archive"
```

### Example 2: IAM Role with Multiple Tags

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMRole
metadata:
  name: lambda-processor
  namespace: data-engineering
spec:
  type: lambda
  tags:
    team: data-eng
    environment: staging
  syncedLabels:
    cost-center: analytics
  # Given defaults.namingTemplate: "{tag.team}-{tag.environment}-{name}"
  # effectiveName = "data-eng-staging-lambda-processor"
  # NOTE: syncedLabels (cost-center) cannot be used in naming templates — only spec.tags
```

### Example 3: KMS Key with Service Name

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: db-key
  namespace: databases
spec:
  tags:
    service: user-database
    tier: production
  # Given defaults.namingTemplate: "alias/kms-{tag.service}-{tag.tier}"
  # Alias = "alias/kms-user-database-production"
```

### Example 4: SQS Queue with Governance Tags

You can combine governance-level tags (from `KropathConfig` or `<ResourceFamily>Config`) with instance-level tags:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SQSQueue
metadata:
  name: order-processor
  namespace: fulfillment
spec:
  fifo: false
  tags:
    application: order-system
    environment: production
```

If `KropathConfig.spec.defaults.tags` includes `{"cost-center": "operations"}` and the `SQSConfig` has `defaults.namingTemplate: "{tag.cost-center}-{tag.application}-queue"`, then:

- **Merged tags for naming:** `{cost-center: operations, application: order-system, environment: production}`
- **effectiveName:** `operations-order-system-queue`

Note: Only `spec.tags` and governance tags are used for naming template resolution. `syncedLabels` and `syncedAnnotations` are not included in the tag resolution for naming templates.

## Troubleshooting

### "invalid-unresolved-tokens" Error

If you use a placeholder for a tag that does not exist in the merged tags, the naming template validation will fail with status `namingStatus: invalid-unresolved-tokens`.

**Example:**

```yaml
spec:
  tags:
    environment: production
  # If defaults.namingTemplate: "{tag.owner}-{name}" but "owner" tag is not set
  # Then status.namingStatus = "invalid-unresolved-tokens"
```

**Solution:**

1. Ensure the tag key exists in one of these places:
   - `spec.tags` (instance-level)
   - Governance config mandatory or default tags (via `KropathConfig` or `<ResourceFamily>Config`)

2. Check the tag name for typos. Tag keys are case-sensitive.

3. If the tag is optional, use a fallback approach:
   - Create a different `<ResourceFamily>Config` profile with a template that does not require the tag
   - Use `spec.nameOverride` to manually specify the name for that particular resource

### Exceeds Provider Length Limits

If the resolved name exceeds the provider's length limit, the reconciliation will fail.

**Example:**

```yaml
spec:
  tags:
    very-long-tag-value: "this-is-an-extremely-long-value-that-exceeds-limits"
  # With template "{tag.very-long-tag-value}-{name}-{namespace}-{account_id}"
  # May exceed S3's 63-character limit
```

**Solution:**

1. Reduce tag values to shorter values (e.g., use abbreviations)
2. Simplify the naming template to use fewer components
3. Use `spec.nameOverride` to provide a shorter explicit name
4. Contact your platform team to define a shorter default template in the governance config

### Tag Value Contains Prohibited Characters

If a tag value contains characters not allowed by the cloud provider, the name validation will fail.

**Example (S3):**

```yaml
spec:
  tags:
    environment: "PROD"  # Uppercase not allowed in S3
  # S3 requires lowercase; Kropath applies .lowerAscii() automatically
  # But if tag contains special chars like '/', the validation will still fail
```

**Solution:**

1. Ensure tag values contain only characters allowed by the target provider
2. For S3, use lowercase alphanumeric and hyphens only
3. For IAM, allowed characters are alphanumeric plus `+`, `=`, `,`, `.`, `@`, `-`, `_`
4. For SQS, use alphanumeric plus hyphens and underscores

## Best Practices

1. **Keep tag values concise** — Long tag values can quickly exceed resource name length limits. Prefer abbreviations.

2. **Use meaningful tags** — Tag names should be semantically clear (e.g., `environment` rather than `e`).

3. **Test template changes** — Before updating a governance config's naming template, test it with a small sample of resources to ensure names stay within limits.

4. **Document templates in governance profiles** — Include a comment in your `<ResourceFamily>Config` or `KropathConfig` explaining the naming template logic for your team.

5. **Avoid tag-only names** — Combine tags with stable identifiers like `{namespace}` or `{name}` to ensure uniqueness and stability.

   Bad: `{tag.team}-queue` (not unique if multiple queues per team)

   Good: `{tag.team}-{name}-queue` (includes the CR name for uniqueness)

## Related Resources

For comprehensive design documentation on naming conventions, refer to the [Configuration / Governance]({{< relref "/docs/concepts/configuration" >}}) section.
