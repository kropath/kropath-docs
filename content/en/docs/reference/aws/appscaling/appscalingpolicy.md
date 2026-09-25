---
title: AppScalingPolicy — Define Scaling Policies
description: "The `AppScalingPolicy` resource attaches target tracking or step scaling policies to registered scalable targets."
doc_type: reference
---
# AppScalingPolicy — Define Scaling Policies

The `AppScalingPolicy` resource attaches target tracking or step scaling policies to registered scalable targets. Policies define when and how capacity changes based on CloudWatch metrics or alarms.

## Core Fields

### Policy Configuration

| Field | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `configRef` | string | No | `"general-policy"` | Selects which `AppScalingConfig` governance profile to apply |
| `deletionPolicy` | string | No | `"retain"` | Behavior when the resource is deleted: `"retain"` (safe) or `"delete"` |
| `tags` | map | No | `{}` | AWS cloud tags to apply (additive, merged with profile governance) |
| `syncedLabels` | map | No | `{}` | Kubernetes labels synced to AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | No | `{}` | Kubernetes annotations synced to resource metadata (prefixed `aws.kropath.run/`) |

### Policy Identity

| Field | Type | Required | Default | Purpose |
|---|---|---|---|---|
| `policyName` | string | Yes | — | Policy name; immutable after creation (delete and recreate to rename) |
| `policyType` | string | No | `"TargetTrackingScaling"` | Scaling type: `"TargetTrackingScaling"` or `"StepScaling"` |

### Target Binding

| Field | Type | Mutually Exclusive | Default | Purpose |
|---|---|---|---|---|
| `serviceNamespace` | string | with `resourceRef` | `""` | AWS service namespace (required when `resourceRef` not set) |
| `scalableDimension` | string | with `resourceRef` | `""` | Scaling dimension (required when `resourceRef` not set) |
| `resourceID` | string | with `resourceRef` | `""` | AWS resource identifier (required when `resourceRef` not set) |
| `resourceRef` | string | with `resourceID` | `""` | Reference to a local `AppScalingTarget` CR to resolve target identifiers |

One of these two forms must be used:
- **Direct specification:** set `serviceNamespace`, `scalableDimension`, `resourceID`
- **Cross-CR resolution:** set `resourceRef` and omit the three target fields

## Governance Cascade

Scale-in and scale-out cooldown periods are governed by `AppScalingConfig`:

```
AppScalingConfig.mandatory.scaleInCooldown  →  spec.targetTracking.scaleInCooldown  →  AppScalingConfig.defaults.scaleInCooldown
AppScalingConfig.mandatory.scaleOutCooldown  →  spec.targetTracking.scaleOutCooldown  →  AppScalingConfig.defaults.scaleOutCooldown
AppScalingConfig.mandatory.disableScaleIn  →  spec.targetTracking.disableScaleIn  →  AppScalingConfig.defaults.disableScaleIn
```

Mandatory tier values override instance-level specs.

## Target Tracking Policies

Target tracking maintains a target metric value by automatically adjusting capacity. The system scales to keep the metric at your target value.

### Target Tracking — Predefined Metric

Use a predefined AWS metric like CPU utilization or request count:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingPolicy
metadata:
  name: ecs-cpu-tracking
  namespace: services
spec:
  configRef: general-policy
  policyName: ecs-cpu-tracking          # AWS policy name (immutable)
  policyType: TargetTrackingScaling     # Target tracking type
  serviceNamespace: ecs
  scalableDimension: ecs:service:DesiredCount
  resourceID: service/prod-cluster/api-service
  targetTracking:
    targetValue: 75.0                   # Maintain 75% CPU
    predefinedMetricSpecification:
      predefinedMetricType: ECSServiceAverageCPUUtilization
    scaleInCooldown: 300                # 5 minutes between scale-in
    scaleOutCooldown: 60                # 1 minute between scale-out
    disableScaleIn: false               # Allow scale-in
  tags:
    metric: cpu
    policy-type: target-tracking
```

**Behavior:**
- Scales capacity to keep average CPU at 75%
- Waits 5 minutes between scale-in events
- Waits 1 minute between scale-out events
- Policy can scale down (scale-in enabled)

### Target Tracking — Custom Metric

Use a custom CloudWatch metric for scaling:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingPolicy
metadata:
  name: custom-metric-policy
  namespace: services
spec:
  configRef: general-policy
  policyName: custom-metric-policy
  policyType: TargetTrackingScaling
  serviceNamespace: ecs
  scalableDimension: ecs:service:DesiredCount
  resourceID: service/prod-cluster/worker-service
  targetTracking:
    targetValue: 1000.0                 # Maintain 1000 requests/second
    customizedMetricSpecification:
      metricName: RequestCount
      namespace: MyApplication
      statistic: Sum
      unit: Count
      dimensions:
        - name: ServiceName
          value: worker-service
    scaleInCooldown: 300
    scaleOutCooldown: 60
    disableScaleIn: false
  tags:
    metric: custom
    source: application
```

**Behavior:**
- Scales based on custom `RequestCount` metric
- Maintains 1000 requests/second average
- Works with application-emitted CloudWatch metrics

### Target Tracking — ALB Request Count

Special case for ALB-backed services:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingPolicy
metadata:
  name: alb-request-count-policy
  namespace: services
spec:
  configRef: general-policy
  policyName: alb-request-count-policy
  policyType: TargetTrackingScaling
  serviceNamespace: ecs
  scalableDimension: ecs:service:DesiredCount
  resourceID: service/prod-cluster/web-service
  targetTracking:
    targetValue: 1000.0                 # 1000 requests per target
    predefinedMetricSpecification:
      predefinedMetricType: ALBRequestCountPerTarget
      resourceLabel: app/my-alb/1234567890abcdef    # ALB ARN suffix
    scaleInCooldown: 300
    scaleOutCooldown: 60
```

**Behavior:**
- Scales based on ALB request rate
- Maintains 1000 requests per instance
- Ideal for web services behind load balancers

### Target Tracking — Governance Override

When profile governance forces cooldown values:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingPolicy
metadata:
  name: production-policy
  namespace: services
spec:
  configRef: production              # Production profile enforces scaleInCooldown: 600
  policyName: production-policy
  policyType: TargetTrackingScaling
  serviceNamespace: ecs
  scalableDimension: ecs:service:DesiredCount
  resourceID: service/prod-cluster/critical-service
  targetTracking:
    targetValue: 50.0                 # 50% CPU
    predefinedMetricSpecification:
      predefinedMetricType: ECSServiceAverageCPUUtilization
    scaleInCooldown: 300              # This will be overridden to 600 (production minimum)
    scaleOutCooldown: 60              # This will be overridden by mandatory tier if set
    disableScaleIn: false             # This may be overridden to true by mandatory tier
  tags:
    environment: production
```

**After deployment:**
- If production profile has `mandatory.scaleInCooldown: 600`, instance value `300` is overridden
- If production profile has `mandatory.disableScaleIn: true`, scale-in is blocked regardless

## Step Scaling Policies

Step scaling adjusts capacity by discrete steps based on CloudWatch alarm thresholds. Useful for workloads with unpredictable scaling patterns.

### Step Scaling — Scale Out on Demand

Scale capacity up by fixed increments when load increases:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingPolicy
metadata:
  name: ecs-step-scale-out
  namespace: services
spec:
  configRef: general-policy
  policyName: ecs-step-scale-out
  policyType: StepScaling
  serviceNamespace: ecs
  scalableDimension: ecs:service:DesiredCount
  resourceID: service/prod-cluster/batch-service
  stepScaling:
    adjustmentType: ChangeInCapacity     # Add/remove specific number of instances
    metricAggregationType: Average        # Use average metric value
    stepAdjustments:
      - metricIntervalLowerBound: 0       # Alarm threshold >= 0
        metricIntervalUpperBound: 10
        scalingAdjustment: 1              # Add 1 instance
      - metricIntervalLowerBound: 10      # Alarm threshold >= 10
        metricIntervalUpperBound: 20
        scalingAdjustment: 2              # Add 2 instances
      - metricIntervalLowerBound: 20      # Alarm threshold >= 20
        scalingAdjustment: 3              # Add 3 instances
    cooldown: 120                         # 2 minutes between scaling events
  tags:
    scaling-type: step
    direction: scale-out
```

**Behavior:**
- Threshold 0–10: add 1 instance
- Threshold 10–20: add 2 instances
- Threshold 20+: add 3 instances
- Wait 2 minutes between scaling events

### Step Scaling — Percent Change

Scale by percentage rather than fixed counts:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingPolicy
metadata:
  name: dynamodb-step-scale-out
  namespace: data
spec:
  configRef: general-policy
  policyName: dynamodb-step-scale-out
  policyType: StepScaling
  serviceNamespace: dynamodb
  scalableDimension: dynamodb:table:ReadCapacityUnits
  resourceID: table/user-events
  stepScaling:
    adjustmentType: PercentChangeInCapacity    # Scale by percentage
    metricAggregationType: Average
    minAdjustmentMagnitude: 1                   # At least 1 RCU adjustment
    stepAdjustments:
      - metricIntervalLowerBound: 0
        metricIntervalUpperBound: 25
        scalingAdjustment: 10                   # Add 10%
      - metricIntervalLowerBound: 25
        metricIntervalUpperBound: 50
        scalingAdjustment: 30                   # Add 30%
      - metricIntervalLowerBound: 50
        scalingAdjustment: 50                   # Add 50%
  tags:
    scaling-type: step
    metric: provisioned-capacity
```

**Behavior:**
- 0–25% over threshold: add 10% capacity
- 25–50% over threshold: add 30% capacity
- 50%+ over threshold: add 50% capacity
- Always adjust by at least 1 RCU

## Cross-CR Resolution with resourceRef

Reference a scalable target instead of specifying identifiers directly:

```yaml
---
# First, define the scalable target
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingTarget
metadata:
  name: api-service-target
  namespace: services
spec:
  configRef: general-policy
  serviceNamespace: ecs
  scalableDimension: ecs:service:DesiredCount
  resourceID: service/prod-cluster/api-service
  minCapacity: 2
  maxCapacity: 20

---
# Then, attach a policy referencing the target
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingPolicy
metadata:
  name: api-policy
  namespace: services
spec:
  configRef: general-policy
  policyName: api-cpu-tracking
  policyType: TargetTrackingScaling
  resourceRef: api-service-target          # Reference the target by name
  targetTracking:
    targetValue: 75.0
    predefinedMetricSpecification:
      predefinedMetricType: ECSServiceAverageCPUUtilization
  tags:
    target: api-service
```

**Benefits:**
- Single source of truth for target identifiers (prevents drift)
- Update target location without editing policies
- Simpler policy definitions

## Immutability and Updates

Policy names are immutable after creation. To rename a policy:

```yaml
# Original policy (will be deleted)
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingPolicy
metadata:
  name: old-policy
spec:
  policyName: old-name                  # Immutable — cannot be changed

---
# New policy (creates with new name)
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingPolicy
metadata:
  name: new-policy
spec:
  policyName: new-name                  # Create a new policy with this name
  # ... same configuration
```

## Status Fields

After deployment, status fields expose the policy's AWS metadata:

```yaml
status:
  policyARN: arn:aws:autoscaling:us-east-1:123456789012:scalingPolicy:1234567890:resource/...
  alarms:                               # CloudWatch alarms (target tracking only)
    - alarmName: TargetTracking-service/cluster/name-AlarmHigh-1234567890
      alarmARN: arn:aws:cloudwatch:us-east-1:123456789012:alarm:...
    - alarmName: TargetTracking-service/cluster/name-AlarmLow-1234567890
      alarmARN: arn:aws:cloudwatch:us-east-1:123456789012:alarm:...
  creationTime: "2024-01-15T10:30:00Z"
  conditions:
    - type: Ready
      status: "True"
      reason: Registered
      message: Scaling policy registered with AWS
```

**Note:** Step scaling policies have empty `alarms` — they use CloudWatch alarms defined separately.

## Common Patterns

### Pattern: Multi-Stage Target Tracking

Scale aggressively on high CPU, conservatively on low CPU:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingPolicy
metadata:
  name: cpu-balanced
spec:
  policyName: cpu-balanced
  policyType: TargetTrackingScaling
  resourceRef: my-service-target
  targetTracking:
    targetValue: 50.0                   # Conservative target (lower = more capacity)
    predefinedMetricSpecification:
      predefinedMetricType: ECSServiceAverageCPUUtilization
    scaleInCooldown: 600                # Slow scale-in (wait 10 min)
    scaleOutCooldown: 60                # Fast scale-out (1 min)
```

This maintains high resource availability while controlling costs.

### Pattern: Cost-Optimized Step Scaling

Aggressive scaling up, conservative scaling down:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingPolicy
metadata:
  name: cost-optimized
spec:
  policyName: cost-optimized
  policyType: StepScaling
  resourceRef: batch-worker-target
  stepScaling:
    adjustmentType: PercentChangeInCapacity
    stepAdjustments:
      - metricIntervalLowerBound: 0
        scalingAdjustment: 50             # Scale up 50% on any alarm
    cooldown: 60
```

### Pattern: Fixed-Size Scaling

Step scaling that adds/removes exact capacity:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingPolicy
metadata:
  name: fixed-scaling
spec:
  policyName: fixed-scaling
  policyType: StepScaling
  resourceRef: database-target
  stepScaling:
    adjustmentType: ExactCapacity        # Set to exact value
    stepAdjustments:
      - metricIntervalLowerBound: 0
        metricIntervalUpperBound: 50
        scalingAdjustment: 10            # Set to exactly 10
      - metricIntervalLowerBound: 50
        scalingAdjustment: 50            # Set to exactly 50
```

## Supported Predefined Metrics

Common predefined metrics by service:

| Service | Metric Type |
|---------|-------------|
| ECS | `ECSServiceAverageCPUUtilization`, `ECSServiceAverageMemoryUtilization`, `ALBRequestCountPerTarget` |
| DynamoDB | `DynamoDBReadCapacityUtilization`, `DynamoDBWriteCapacityUtilization` |
| Lambda | `LambdaProvisionedConcurrencyUtilization` |
| Aurora | `RDSReaderAverageCPUUtilization`, `RDSReaderAverageDatabaseConnections` |
| AppStream | `AppStreamAverageCapacityUtilization` |

Consult AWS documentation for the full list of metrics per service.

## Next Steps

- [AppScalingTarget](./appscalingtarget.md) — Register scalable resources
- [AppScalingConfig](./appscalingconfig.md) — Set up governance profiles
- [Application Auto Scaling Overview](./index.md) — Family concepts and quick start
