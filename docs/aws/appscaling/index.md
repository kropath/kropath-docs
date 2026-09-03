# Application Auto Scaling

The Application Auto Scaling family provides unified resource scaling across AWS services. Manage capacity bounds, scaling policies, and governance rules for ECS services, DynamoDB tables, Lambda provisioned concurrency, and 15+ other AWS resources through a single, consistent interface.

## Resources

This family includes three core resources:

- **[AppScalingConfig](./appscalingconfig.md)** — Per-profile governance: capacity bounds, scale-in protection, cooldown periods, tags
- **[AppScalingTarget](./appscalingtarget.md)** — Register a scalable resource with Application Auto Scaling
- **[AppScalingPolicy](./appscalingpolicy.md)** — Attach target tracking or step scaling policies to registered targets

## Quick Start

A typical workflow:

1. Define a governance profile using `AppScalingConfig` (or use the default `general-policy`)
2. Register a scalable resource (ECS service, DynamoDB table, etc.) with `AppScalingTarget`
3. Attach a scaling policy with `AppScalingPolicy`

## Supported Services

Application Auto Scaling works with:

- **Compute:** ECS services, EC2 Spot fleets, AppStream 2.0
- **Database:** DynamoDB (tables and global secondary indexes), Aurora read replicas
- **Functions:** AWS Lambda provisioned concurrency
- **Other:** ElastiCache, Keyspaces, Neptune, Comprehend, RDS proxy

## Governance Model

Platform teams deploy named profiles (`general-policy`, `production`, `cost-optimized`, etc.) to enforce organizational scaling policies. The cascade ensures consistency:

1. Organization-wide settings (KropathConfig)
2. Profile-specific mandatory rules
3. Resource-level overrides
4. Profile-specific defaults

Resources respect mandatory governance rules — they cannot be overridden by instance-level specs.

## Key Concepts

### Scalable Target

A scalable target is an AWS resource or resource dimension registered with Application Auto Scaling. It identifies:

- The target service (e.g., `ecs`, `dynamodb`)
- The scaling dimension (e.g., `ecs:service:DesiredCount`)
- The resource identifier (e.g., `service/my-cluster/my-service`)

Multiple scaling policies can attach to the same target, but only one of each policy type (target tracking or step scaling per target).

### Scaling Policies

Two policy types attach to scalable targets:

- **Target Tracking:** Maintains a target metric value by auto-scaling capacity (e.g., keep CPU at 75%)
- **Step Scaling:** Discrete capacity adjustments in response to CloudWatch alarms

### Scale-In Protection

The `disableScaleIn` setting prevents automatic capacity reduction. Useful for cost-sensitive or stateful workloads that should never scale down involuntarily. Governed by `AppScalingConfig` profiles.

### Cooldown Periods

- **Scale-In Cooldown:** Minimum seconds between scale-in events (default: 300s / 5 minutes)
- **Scale-Out Cooldown:** Minimum seconds between scale-out events (default: 60s)

Prevents thrashing and allows time for metrics to stabilize between scaling actions.

## Next Steps

- [AppScalingConfig](./appscalingconfig.md) — Set up governance profiles
- [AppScalingTarget](./appscalingtarget.md) — Register your first scalable resource
- [AppScalingPolicy](./appscalingpolicy.md) — Attach scaling policies
