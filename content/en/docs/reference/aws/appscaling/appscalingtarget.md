---
title: AppScalingTarget — Register Scalable Resources
description: "The `AppScalingTarget` resource registers an AWS resource or resource dimension with Application Auto Scaling."
doc_type: reference
---
# AppScalingTarget — Register Scalable Resources

The `AppScalingTarget` resource registers an AWS resource or resource dimension with Application Auto Scaling. Once registered, scaling policies can attach to the target to automate capacity management.

## Core Fields

### Resource Configuration

| Field | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `configRef` | string | No | `"general-policy"` | Selects which `AppScalingConfig` governance profile to apply |
| `deletionPolicy` | string | No | `"retain"` | Behavior when the resource is deleted: `"retain"` (safe) or `"delete"` (remove AWS resource) |
| `tags` | map | No | `{}` | AWS cloud tags to apply (additive, merged with profile governance) |
| `syncedLabels` | map | No | `{}` | Kubernetes labels synced to AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | No | `{}` | Kubernetes annotations synced to resource metadata (prefixed `aws.kropath.run/`) |

### Target Identity

| Field | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `serviceNamespace` | string | Yes | — | AWS service namespace: `"ecs"`, `"dynamodb"`, `"lambda"`, `"elasticmapreduce"`, etc. |
| `scalableDimension` | string | Yes | — | Scaling dimension: `"ecs:service:DesiredCount"`, `"dynamodb:table:ReadCapacityUnits"`, etc. |
| `resourceID` | string | Yes | — | AWS resource identifier: `"service/cluster-name/service-name"`, `"table/table-name"`, etc. |

### Capacity Bounds

| Field | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `minCapacity` | integer | Yes | — | Minimum capacity; zero is valid for services that support scale-to-zero |
| `maxCapacity` | integer | Yes | — | Maximum capacity to scale out to |

These values are governed by the `AppScalingConfig` cascade — mandatory tier overrides instance values.

### Optional — Identity and Access

| Field | Type | Mutually Exclusive | Default | Purpose |
|---|---|---|---|---|
| `roleARN` | string | with `roleRef` | `""` | IAM role ARN for Application Auto Scaling (required only for services without service-linked role support, e.g. EMR) |
| `roleRef` | string | with `roleARN` | `""` | Reference to a local IAM `Role` CR managed by ACK (when using this, omit `roleARN`) |

### Optional — Suspended State

| Field | Type | Default | Purpose |
|---|---|---|---|
| `suspendedState.dynamicScalingInSuspended` | boolean | `false` | Suspend policy-triggered scale-in |
| `suspendedState.dynamicScalingOutSuspended` | boolean | `false` | Suspend policy-triggered scale-out |
| `suspendedState.scheduledScalingSuspended` | boolean | `false` | Suspend scheduled-action scaling |

## Governance Cascade

The capacity bounds follow the governance cascade:

```
AppScalingConfig.mandatory.minCapacity  →  spec.minCapacity  →  AppScalingConfig.defaults.minCapacity
AppScalingConfig.mandatory.maxCapacity  →  spec.maxCapacity  →  AppScalingConfig.defaults.maxCapacity
```

Mandatory tier values always win. If the mandatory tier specifies `minCapacity: 2`, your instance-level `spec.minCapacity: 1` is overridden to `2`.

## Example: ECS Service Target

Register an ECS service for scaling:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingTarget
metadata:
  name: api-service-target
  namespace: services
spec:
  configRef: general-policy              # Use general-policy profile
  serviceNamespace: ecs
  scalableDimension: ecs:service:DesiredCount
  resourceID: service/prod-cluster/api-service
  minCapacity: 2                          # At least 2 instances
  maxCapacity: 20                         # Scale up to 20
  tags:
    service: api
    team: platform
  syncedLabels:
    app: api-service
  syncedAnnotations:
    scaling-enabled: "true"
```

**After deployment:**
- The ECS service is registered as a scalable target
- Capacity will remain between 2 and 20 instances
- Scaling policies can now attach to this target
- Tags and labels sync to the registered AWS resource

## Example: DynamoDB Table Target

Register a DynamoDB table for scaling:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingTarget
metadata:
  name: dynamodb-table-target
  namespace: data
spec:
  configRef: production                   # Use production profile
  serviceNamespace: dynamodb
  scalableDimension: dynamodb:table:ReadCapacityUnits
  resourceID: table/user-events
  minCapacity: 5                          # Minimum 5 RCUs (production enforces min 2)
  maxCapacity: 1000                       # Maximum 1000 RCUs
  tags:
    database: events
    retention: permanent
```

**After deployment:**
- Production governance applied (no mandatory overrides for this profile)
- Read capacity provisioned between 5 and 1000 RCUs
- Target tracking or step scaling policies can attach to manage RCU levels

## Example: Lambda Provisioned Concurrency Target

Register Lambda provisioned concurrency for scaling:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingTarget
metadata:
  name: payment-processor-target
  namespace: functions
spec:
  configRef: production
  serviceNamespace: lambda
  scalableDimension: lambda:function:ProvisionedConcurrentExecutions
  resourceID: function:payment-processor:provisioned
  minCapacity: 10                         # Minimum 10 concurrent executions
  maxCapacity: 100                        # Maximum 100 concurrent
  tags:
    function: payment-processor
    cost-center: payments
```

## Example: EMR Target with IAM Role

For services without service-linked role support (e.g., EMR), provide an IAM role ARN:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingTarget
metadata:
  name: emr-cluster-target
  namespace: analytics
spec:
  configRef: general-policy
  serviceNamespace: elasticmapreduce
  scalableDimension: elasticmapreduce:instancegroup:InstanceCount
  resourceID: ig-CLUSTER_ID_REPLACES_THIS
  minCapacity: 1
  maxCapacity: 100
  roleARN: "arn:aws:iam::123456789012:role/EMRAutoScalingRole"
  tags:
    cluster: analytics
```

## Example: Cross-CR Resolution with roleRef

When the IAM role is managed by ACK, use `roleRef` to resolve the role ARN automatically:

```yaml
# First, define the IAM role (managed by ACK in kro)
---
apiVersion: iam.services.k8s.aws/v1alpha1
kind: Role
metadata:
  name: autoscaling-role
spec:
  assumeRolePolicyDocument: |
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": "application-autoscaling.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }
status:
  ackResourceMetadata:
    arn: arn:aws:iam::123456789012:role/autoscaling-role

---
# Then, reference the role in your scaling target
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingTarget
metadata:
  name: emr-cluster-target
  namespace: analytics
spec:
  configRef: general-policy
  serviceNamespace: elasticmapreduce
  scalableDimension: elasticmapreduce:instancegroup:InstanceCount
  resourceID: ig-CLUSTER_ID
  minCapacity: 1
  maxCapacity: 100
  roleRef: autoscaling-role            # Reference to the IAM role CR
  tags:
    cluster: analytics
```

The role ARN is resolved from `autoscaling-role.status.ackResourceMetadata.arn`.

## Example: Scale-to-Zero Target

Services like ECS and Lambda support scale-to-zero. Use `minCapacity: 0`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingTarget
metadata:
  name: staging-worker-target
  namespace: batch
spec:
  configRef: cost-optimized              # Use cost-optimized profile
  serviceNamespace: ecs
  scalableDimension: ecs:service:DesiredCount
  resourceID: service/staging-cluster/batch-worker
  minCapacity: 0                          # Allow scaling to zero
  maxCapacity: 10
  tags:
    environment: staging
    cost-sensitive: "true"
```

**With this target:**
- Minimum capacity is 0 (no instances when not needed)
- Cost optimization profiles can apply aggressive scale-in cooldowns
- Cost-sensitive workloads scale to zero automatically

## Example: Suspended Scaling

Temporarily suspend scaling activities without deleting the target:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingTarget
metadata:
  name: maintenance-target
  namespace: services
spec:
  configRef: general-policy
  serviceNamespace: ecs
  scalableDimension: ecs:service:DesiredCount
  resourceID: service/prod-cluster/maintenance
  minCapacity: 3
  maxCapacity: 30
  suspendedState:
    dynamicScalingInSuspended: true       # No automatic scale-in
    dynamicScalingOutSuspended: false     # Scale-out still allowed
    scheduledScalingSuspended: true       # No scheduled actions
```

**Use cases:**
- During maintenance windows (keep current capacity)
- Testing without autoscaling interference
- Cost controls (freeze capacity while investigating)

Resume scaling by setting suspended flags to `false`.

## Status Fields

After deployment, status fields expose the registered target's metadata:

```yaml
status:
  scalableTargetARN: arn:aws:application-autoscaling:us-east-1:123456789012:scalable-target/1234567890
  creationTime: "2024-01-15T10:30:00Z"
  conditions:
    - type: Ready
      status: "True"
      reason: Registered
      message: Scalable target registered with AWS
```

## Supported Service Namespaces

Application Auto Scaling works with:

| Service | Namespace | Scalable Dimension | Resource ID Format |
|---------|-----------|-------------------|-------------------|
| ECS | `ecs` | `ecs:service:DesiredCount` | `service/cluster/name` |
| DynamoDB | `dynamodb` | `dynamodb:table:ReadCapacityUnits` | `table/name` |
| DynamoDB | `dynamodb` | `dynamodb:table:WriteCapacityUnits` | `table/name` |
| DynamoDB GSI | `dynamodb` | `dynamodb:index:ReadCapacityUnits` | `table/name/index/name` |
| DynamoDB GSI | `dynamodb` | `dynamodb:index:WriteCapacityUnits` | `table/name/index/name` |
| Lambda | `lambda` | `lambda:function:ProvisionedConcurrentExecutions` | `function:name:provisioned` |
| Aurora | `rds` | `rds:cluster:ReadReplicaCount` | `cluster:name` |
| EC2 Spot | `ec2spot` | `ec2spot:fleet:DesiredCapacity` | `spot-fleet-request/id` |
| ElastiCache | `elasticache` | `elasticache:replication-group:DesiredMemberCount` | `replication-group:name` |
| AppStream | `appstream` | `appstream:fleet:DesiredCapacity` | `fleet/name` |
| EMR | `elasticmapreduce` | `elasticmapreduce:instancegroup:InstanceCount` | `instancegroup/id` |
| Keyspaces | `cassandra` | `cassandra:table:ReadCapacityUnits` | `keyspace/name/table/name` |
| Comprehend | `comprehend` | `comprehend:document-classifier-endpoint:DesiredInferenceUnits` | `arn:...` |

Consult AWS documentation for the exact resource ID format for your service.

## Next Steps

- [AppScalingPolicy](./appscalingpolicy.md) — Attach scaling policies to targets
- [AppScalingConfig](./appscalingconfig.md) — Set up governance profiles
- [Application Auto Scaling Overview](./index.md) — Family concepts and quick start
