---
title: Resources (RGDs)
linkTitle: Resources
description: What a kropath resource is and how application teams use them.
weight: 40
doc_type: concept
---

# Resources (RGDs)

A **kropath resource** is a Kubernetes CR that application teams create to provision a cloud resource. Beneath the surface, each resource is backed by a **ResourceGraphDefinition (RGD)** — a governance-aware wrapper that composes platform policy with the application's intent and generates the underlying provider-operator CR.

## Resource CRs

Application teams create simple CRs like:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: my-data
  namespace: prod
spec:
  configRef: general-policy
  region: us-west-2
  tags:
    application: analytics
```

The application team specifies only what they care about:

- The resource kind and basic config (e.g., S3 region)
- A reference to the platform's governance config
- Application-specific tags and labels

The platform policy (encryption, retention, naming, additional tags) is automatically applied by the governance config they reference.

## ResourceGraphDefinition (RGD)

A **ResourceGraphDefinition** is a kro primitive that defines how a kropath resource maps to cloud resources. Kropath ships one RGD per resource kind (one for `S3Bucket`, one for `IAMRole`, etc.) that:

1. Reads the application's resource CR
2. Fetches the governance config (`status.effectiveConfig`)
3. Composes both into a **merged view**
4. Generates an underlying provider-operator CR (e.g., an ACK `Bucket` CR)

**The application team never edits RGDs** — they're defined by the platform team and versioned with the kropath release. Application teams just create their resource CR and the RGD handles the rest.

### Example: How an RGD Works

Given this `S3Bucket` CR:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: my-data
  namespace: prod
spec:
  configRef: general-policy
  region: us-west-2
  tags:
    application: analytics
```

The RGD:

1. Looks up the `S3Config` named `general-policy` (via `configRef`)
2. Fetches its `status.effectiveConfig` (which contains governance mandatory and defaults)
3. Merges the user spec with the governance config (following the cascade precedence)
4. Generates an ACK `Bucket` CR with all fields resolved

Result:

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: prod-my-data  # from naming template
  namespace: prod
spec:
  bucketName: prod-my-data  # from naming template
  region: us-west-2  # from user spec
  versioning: enabled  # from governance mandatory
  tags:
    backup-retention: "30days"  # from governance defaults
    application: analytics  # from user spec
  # ... other fields from effectiveConfig
```

The ACK controller then provisions the actual S3 bucket in AWS.

## Resource Status

After the application team creates a resource, kropath populates the `status` field with important information:

```yaml
status:
  effectiveName: "prod-my-data"  # The computed cloud resource name
  predictedArn: "arn:aws:s3:::prod-my-data"  # The predicted ARN
  arn: "arn:aws:s3:::prod-my-data"  # Actual ARN after AWS confirms
  conditions:
    - type: Ready
      status: "True"
```

Application teams can use these status fields to:

- **Reference resources in other CRs** — Use `status.predictedArn` in IAM policies or network rules
- **Verify resource creation** — Check the `Ready` condition
- **Troubleshoot failures** — Look for error conditions and messages

## Label Injection

Kropath includes a **label-operator** that automatically injects provider-specific resource labels onto all resources. This ensures that resources are discoverable by governance rules and RGDs.

### How It Works

The label-operator watches all resources under `<provider>.kropath.run` API groups (e.g., `aws.kropath.run`, `gcp.kropath.run`) and automatically injects the label:

```
<provider>.kropath.run/resource-name: <metadata.name>
```

**Example:**

When you create an `S3Bucket` named `my-data`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: my-data
  namespace: prod
```

The label-operator automatically adds:

```yaml
metadata:
  labels:
    aws.kropath.run/resource-name: my-data
```

### Why Labels Matter

RGDs and governance config lookups use `labelSelector.matchLabels` to find the right configuration:

```yaml
selector:
  matchLabels:
    aws.kropath.run/resource-name: my-data
```

Without these labels, lookups would fail silently and reconciliation would stall. The label-operator ensures this works automatically — you don't need to manually label your resources.

### Automatic Coverage

The operator automatically covers:

- **All Config resources** — `S3Config`, `IAMConfig`, `RDSConfig`, etc.
- **All instance resources** — `S3Bucket`, `IAMRole`, `RDSInstance`, etc.
- **Any new CRD** under a `<provider>.kropath.run` API group — no code changes needed

The `KropathConfig` resource (in the `kropath.run` API group, not a provider-specific group) is excluded from labeling.

### Behavior During Outages

If the label-operator pod is temporarily unavailable:

- **Existing resources** retain their labels — they're stored in etcd and persist regardless of operator state
- **New resources** are admitted normally without error, but may lack the label initially
- **Impact during outage** — RGD lookups for newly-created resources may fail until the operator recovers and labels them retroactively
- **After recovery** — The operator automatically labels the resource on the next reconciliation cycle, and RGD lookups succeed

This is a graceful degradation mode — better than a webhook-based approach that would either block admission or risk losing label injection entirely during outages.

## Resource Kinds

Kropath currently ships resource CRs for AWS. Each resource kind maps to a cloud service and has a corresponding RGD:

**AWS resource families:**

- **S3**: `S3Bucket`
- **IAM**: `IAMRole`, `IAMPolicy`, `IAMUser`, `IAMGroup`
- **Lambda**: `LambdaFunction`, `LambdaAlias`, `LambdaEventSourceMapping`
- **RDS**: `RDSInstance`, `RDSCluster`
- **SQS**: `SQSQueue`
- **SNS**: `SNSTopic`
- **ECS**: `ECSCluster`, `ECSService`, `ECSTaskDefinition`
- **EKS**: `EKSCluster`, `EKSNodeGroup`
- **DynamoDB**: `DynamoDBTable`
- **KMS**: `KMSKey`
- **Secrets Manager**: `SecretsManagerSecret`
- **EventBridge**: `EventBridgeEventBus`, `EventBridgeRule`
- **ELB**: `ELBLoadBalancer`, `ELBTargetGroup`, `ELBListener`
- **CloudFront**: `CloudFrontDistribution`
- **EC2**: `EC2Instance`, `EC2SecurityGroup`, `EC2VPC`

**GCP and Azure** resources are in development — support is not yet available.

## Creating and Managing Resources

### Create

Application teams create a resource CR with just the fields they care about:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMRole
metadata:
  name: app-role
  namespace: prod
spec:
  configRef: iam-policy
  type: ec2
  tags:
    application: myapp
```

### Reference in Other Resources

Use the resource's `status.predictedArn` to reference it in other resources:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMPolicy
metadata:
  name: app-policy
spec:
  statement:
    - effect: Allow
      actions:
        - "s3:GetObject"
      resources:
        - "arn:aws:s3:::my-bucket/*"
```

Or use policy document composition:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: assume-role-policy
spec:
  statements:
    - sid: AllowEC2Assume
      effect: Allow
      principals:
        - type: Service
          arn: "ec2.amazonaws.com"
      actions:
        - "sts:AssumeRole"
```

### Update

Modify the resource CR to update settings:

```yaml
spec:
  configRef: iam-policy-v2  # Switch to a different governance config
  tags:
    application: myapp
    version: "2"
```

The RGD and kropath-controller automatically recompute `status.effectiveConfig` and update the underlying cloud resource.

### Delete

Deletion policy is controlled by the platform team via the `services.k8s.aws/deletion-policy` annotation on the resource CR:

```yaml
metadata:
  annotations:
    services.k8s.aws/deletion-policy: delete  # or: retain
```

If `delete`, the cloud resource is deleted when the CR is deleted. If `retain` (or missing), the cloud resource persists.

## Troubleshooting

**Resource is not Ready:**

Check the resource's `status.conditions`:

```bash
kubectl describe <resource-kind> <resource-name> -n <namespace>
```

Common issues:

- **No config found** — Verify `spec.configRef` points to an existing `<ResourceFamily>Config`
- **Invalid name** — The computed name exceeds provider length limits or contains invalid characters
- **Missing label** — The label-operator is down or hasn't reconciled yet

**Cannot reference resource in policy:**

Verify the resource has the correct label:

```bash
kubectl get <resource-kind> <name> -o yaml | grep "aws.kropath.run/resource-name"
```

If missing, wait for the label-operator to reconcile (usually a few seconds).

**Governance config not applied:**

Check that `spec.configRef` matches an existing `<ResourceFamily>Config` in the same namespace or the kro-system namespace.
