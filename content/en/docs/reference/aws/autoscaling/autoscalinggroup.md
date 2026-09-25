---
title: AutoScalingGroup — Managed Instance Fleets
description: "The `AutoScalingGroup` resource creates AWS Auto Scaling groups for managing EC2 instance fleets."
doc_type: reference
---
# AutoScalingGroup — Managed Instance Fleets

The `AutoScalingGroup` resource creates AWS Auto Scaling groups for managing EC2 instance fleets. Auto Scaling groups automatically scale instance count based on demand, health, and lifecycle policies.

## Overview

Use `AutoScalingGroup` to create:

- **Standard fleets** — Launched from a single EC2 launch template, scaling between min and max size
- **Mixed-capacity fleets** — On-Demand and Spot instances for cost optimization
- **Load-balanced groups** — Integrated with ELBv2 target groups for traffic distribution
- **Lifecycle-managed groups** — With lifecycle hooks for graceful shutdown and custom actions
- **Warm pool groups** — Pre-warmed instances for rapid scaling response
- **Automatically-rotating fleets** — With instance rotation policies for freshness

Each group has:
- **Scaling behavior** — Min/max size, desired capacity, cooldown periods
- **Health management** — EC2/ELB health checks, grace periods, automatic instance replacement
- **Capacity management** — Termination policies, instance maintenance windows
- **Governance** — Profile-based enforcement of compliance and operational policies
- **Cost optimization** — On-Demand and Spot mixing with rebalancing

## Fleet Types

Choose the fleet type that matches your use case:

| Type | Best For | Example |
|---|---|---|
| **Single launch template** (no mixedInstancesPolicy) | Stable workloads with consistent instance type | Web servers, API backends |
| **Mixed instances** (mixedInstancesPolicy enabled) | Cost optimization with On-Demand + Spot | Batch jobs, non-critical compute |
| **Warm pool** (warmPool configured) | Low-latency scaling response needed | Real-time bidding, event-driven apps |
| **Lifecycle hooks** (lifecycleHooks specified) | Custom actions on launch/termination | Graceful drains, log uploads |

## Creating an Auto Scaling Group

### Simple Standard Fleet

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AutoScalingGroup
metadata:
  name: web-backend
  namespace: app-prod
spec:
  configRef: general-policy
  minSize: 2
  maxSize: 8
  desiredCapacity: 3
  launchTemplate:
    name: backend-v2
    version: "$Latest"
  vpcZoneIdentifier: "subnet-12345,subnet-67890"
```

This group:
- Uses the `general-policy` governance profile
- Maintains 3 instances normally, scales between 2–8 based on demand
- Launches instances using the latest backend-v2 launch template
- Deploys instances across two subnets
- Is named `app-prod-web-backend` (from the naming template)

### High-Availability Web Fleet

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AutoScalingGroup
metadata:
  name: api-servers
  namespace: web-prod
spec:
  configRef: production
  minSize: 3
  maxSize: 20
  desiredCapacity: 5
  launchTemplate:
    name: api-server-v3
  vpcZoneIdentifier: "subnet-az1,subnet-az2,subnet-az3"
  healthCheckType: "ELB"
  healthCheckGracePeriod: 60
  targetGroupARNs:
    - "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/api-prod/abc123"
  tags:
    team: platform
    service: api
```

This group:
- Maintains high availability across 3 availability zones
- Scales up to 20 instances for traffic spikes
- Relies on ELB health checks (faster than EC2 health checks alone)
- 60-second grace period before health checks begin
- Registers instances with the API load balancer target group

### Cost-Optimized Mixed Capacity Fleet

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AutoScalingGroup
metadata:
  name: batch-workers
  namespace: compute-prod
spec:
  configRef: general-policy
  minSize: 1
  maxSize: 50
  launchTemplate:
    name: batch-worker
  mixedInstancesPolicy:
    onDemandBaseCapacity: 2
    onDemandPercentageAboveBaseCapacity: 20
    spotAllocationStrategy: "capacity-optimized"
    overrides:
      - instanceType: "t3.large"
      - instanceType: "t3a.large"
      - instanceType: "m5.large"
      - instanceType: "m5a.large"
  vpcZoneIdentifier: "subnet-12345,subnet-67890"
```

This group:
- Uses 2 On-Demand instances as a baseline
- 20% of additional capacity is On-Demand; 80% is Spot
- Allocates Spot instances by capacity-optimized strategy (minimizes interruptions)
- Provides 4 instance type options (flexibility = better Spot availability)
- Total potential capacity: 50 instances at <20% On-Demand cost

**Alternative: Attribute-Based Selection**

Instead of specifying `overrides` with explicit instance types, use `instanceRequirements` for attribute-based selection:

```yaml
mixedInstancesPolicy:
  onDemandBaseCapacity: 2
  onDemandPercentageAboveBaseCapacity: 20
  spotAllocationStrategy: "capacity-optimized"
  instanceRequirements:
    vCpuCount:
      min: 2
      max: 4
    memoryMiB:
      min: 4096
      max: 8192
    cpuManufacturers:
      - "intel"
      - "amd"
```

This automatically selects instance types matching the criteria instead of maintaining a manual list. Useful when flexibility across instance families is desired.

### Graceful Termination with Lifecycle Hooks

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AutoScalingGroup
metadata:
  name: drain-sensitive
  namespace: workers
spec:
  configRef: general-policy
  minSize: 1
  maxSize: 10
  launchTemplate:
    name: worker
  lifecycleHooks:
    - name: drain-hook
      transition: "autoscaling:EC2_INSTANCE_TERMINATING"
      defaultResult: "CONTINUE"
      heartbeatTimeout: 120
      notificationTargetArn: "arn:aws:sqs:us-east-1:123456789012:worker-drain"
      notificationMetadata: "environment=prod,service=worker"
      roleArn: "arn:aws:iam::123456789012:role/autoscaling-lifecycle"
  tags:
    graceful-drain: "true"
```

This group:
- Publishes termination events to an SQS queue before killing instances
- Gives consumers 120 seconds to drain connections and clean up
- Uses `CONTINUE` as default (proceed with termination if timeout elapses)
- Terminating instances wait for the hook completion before dying

### Warm Pool for Rapid Scaling

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AutoScalingGroup
metadata:
  name: surge-capacity
  namespace: events
spec:
  configRef: general-policy
  minSize: 2
  maxSize: 100
  launchTemplate:
    name: event-processor
  warmPool:
    poolState: "Stopped"
    minSize: 5
    maxGroupPreparedCapacity: 20
    reuseOnScaleIn: true
  vpcZoneIdentifier: "subnet-12345,subnet-67890"
```

This group:
- Maintains 5 pre-initialized stopped instances in the warm pool
- Scales up to 20 warm instances if needed
- Starts instances from warm pool on scale-up (faster than launch from AMI)
- Returns instances to warm pool on scale-down (vs. terminating)
- Saves on EC2 startup latency during traffic spikes

## Scaling Configuration

### Desired Capacity

Set the target number of running instances:

```yaml
spec:
  minSize: 2
  maxSize: 10
  desiredCapacity: 4  # Run 4 instances normally
```

Desired capacity must be between `minSize` and `maxSize`. If omitted, defaults to `minSize`.

### Cooldown Period

Prevent rapid oscillation between scale-up and scale-down:

```yaml
spec:
  defaultCooldown: 300  # Wait 300 seconds between scaling activities
```

Cooldown reduces costs by preventing thrashing when demand fluctuates near the scaling threshold.

### Instance Warmup

Time to wait before an instance is considered ready for traffic:

```yaml
spec:
  defaultInstanceWarmup: 120  # Wait 120 seconds for instance to stabilize
```

Allows the instance time to initialize, download dependencies, and warm up caches before load is applied.

## Health Management

### Health Check Type

Choose what determines instance health:

**EC2-only (default):**
```yaml
spec:
  healthCheckType: "EC2"  # Only EC2 status checks
```

Instances are marked unhealthy only if EC2 itself reports them unhealthy. Fastest to detect EC2 hardware failures.

**ELB Health Checks:**
```yaml
spec:
  healthCheckType: "ELB"  # Only ELB health checks
```

Instances are marked unhealthy based on application-level health checks from the load balancer. Better for application-level failures.

**EBS Health Checks:**
```yaml
spec:
  healthCheckType: "EBS"  # EBS-level health checks
```

Instances are marked unhealthy based on EBS volume status. Useful for storage-intensive workloads.

**VPC Lattice Health Checks:**
```yaml
spec:
  healthCheckType: "VPC_LATTICE"  # VPC Lattice health checks
```

Instances are marked unhealthy based on VPC Lattice service-level health checks. Enables service mesh integration.

**Multiple Checks:**
```yaml
spec:
  healthCheckType: "EC2,ELB"  # Both EC2 and ELB health checks
```

Instances must pass both checks; failure in either marks them unhealthy. Most rigorous but may be overly aggressive.

### Grace Period

Delay before health checks apply to newly-launched instances:

```yaml
spec:
  healthCheckGracePeriod: 300  # Wait 300 seconds before checking health
```

Gives instances time to initialize and become healthy before checks begin. Use longer periods (600s) for applications with slow startup.

**Note:** Setting `healthCheckGracePeriod: 0` is treated as "not set" — it falls through to profile defaults. To achieve a 0-second grace period, set it in `AutoScalingConfig.defaults.healthCheckGracePeriod`.

## Instance Lifecycle

### Scale-In Protection

Protect new instances from being terminated during scale-down:

```yaml
spec:
  newInstancesProtectedFromScaleIn: true  # Don't kill new instances during scale-down
```

Useful for long-running jobs; prevents work loss due to unexpected scale-down.

### Capacity Rebalancing

For Spot fleets, proactively replace at-risk instances:

```yaml
spec:
  capacityRebalance: true
```

AWS notifies of Spot interruptions before they happen. The group launches replacement instances while old ones are still running, minimizing disruption.

### Maximum Instance Lifetime

Automatically rotate instances for freshness:

```yaml
spec:
  maxInstanceLifetime: 86400  # Rotate instances every 24 hours
```

Ensures instances never run longer than the specified age (in seconds). Must be at least 86400 (1 day) when enabled. Useful for security patching and preventing configuration drift.

### Termination Policies

Control which instances are terminated during scale-down:

```yaml
spec:
  terminationPolicies:
    - "OldestLaunchTemplate"  # Kill instances from oldest launch template version
    - "Default"               # Fall back to default policies if tied
```

Common policies:
- `Default` — AWS-default behavior (AZ rebalancing, then oldest launch configuration)
- `OldestInstance` — Terminate oldest instance by launch time
- `OldestLaunchTemplate` — Terminate instances from oldest launch template version
- `NewestInstance` — Terminate newest instance (useful for testing)
- `AllocationStrategy` — Follow the instance weighting strategy

### Instance Maintenance

Control the pace of updates during operations:

```yaml
spec:
  instanceMaintenancePolicy:
    minHealthyPercentage: 80   # Keep 80% running during updates
    maxHealthyPercentage: 120  # Allow up to 120% temporarily for rolling updates
```

Replaces unhealthy or outdated instances while maintaining available capacity.

## Launch Configuration

### Launch Template

Specify the EC2 configuration:

```yaml
spec:
  launchTemplate:
    name: "web-app-v2"
    version: "$Latest"  # or "$Default", or specific version number
```

Launch templates contain AMI ID, instance type, security groups, IAM role, and user data. Use `$Latest` to always use the latest template version; use specific version numbers for stability.

## Network Configuration

### Subnet Placement (VPC)

Deploy instances to specific subnets:

```yaml
spec:
  vpcZoneIdentifier: "subnet-12345,subnet-67890,subnet-abcde"
```

Comma-separated list of subnets. Instances are launched across these subnets for availability. Required for VPC deployments.

### Availability Zones

Alternative to subnets for EC2-Classic or AZ-specific launching:

```yaml
spec:
  availabilityZones:
    - "us-east-1a"
    - "us-east-1b"
```

Use `vpcZoneIdentifier` for VPC deployments; use `availabilityZones` for EC2-Classic or when subnets are not specified.

## Load Balancing

### Target Group Registration

Register instances with load balancer target groups:

```yaml
spec:
  targetGroupARNs:
    - "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/api/abc123"
    - "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/metrics/def456"
```

Instances are automatically registered with these target groups at launch and deregistered at termination. Enables seamless integration with ELBv2 load balancers.

## Naming

Group names are auto-generated from a template. The default template is `{namespace}-{name}`:

- Namespace: `app-prod`
- CR name: `web-backend`
- **Group name:** `app-prod-web-backend`

Override the template in `AutoScalingConfig`, or override per-group:

```yaml
spec:
  nameOverride: "my-custom-asg"
```

With `nameOverride`, the group is named exactly `my-custom-asg` (no template applied).

**AWS constraints:** Group names must:
- Be unique per account per region
- Not contain colons (`:`)
- Be max 255 characters

## Tags and Labels

Add organization and application metadata:

```yaml
spec:
  tags:
    team: backend
    cost-center: "1234"
    environment: production
  syncedLabels:
    application: web-api
    data-class: internal
  syncedAnnotations:
    slack-channel: "#api-alerts"
    runbook: "https://wiki.example.com/web-api"
```

Tags appear on both the AWS Auto Scaling group and launched EC2 instances. Synced labels and annotations are propagated to Kubernetes.

## Deletion Policy

Control what happens to the AWS group when the CR is deleted:

### Retain (default)

```yaml
spec:
  deletionPolicy: "retain"  # default
```

The AWS group remains when the CR is deleted. Instances continue running. Useful for production groups to prevent accidental deletion.

### Delete

```yaml
spec:
  deletionPolicy: "delete"
```

The AWS group is terminated when the CR is deleted. All instances are shut down. Use only for temporary or test groups.

## Monitoring

Check group status:

```bash
kubectl describe autoscalinggroup web-backend -n app-prod
```

Look for:
- `status.resourceName` — The actual group name in AWS
- `status.predictedArn` — The full ARN (in wildcard form for pre-creation ARN prediction)
- `status.namingStatus` — `valid` or `invalid-unresolved-tokens` (indicates naming errors)
- `status.conditions` — Ready, error, or warning states

Query AWS for live capacity:

```bash
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names app-prod-web-backend
```

Check for unhealthy instances:

```bash
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names app-prod-web-backend \
  --query 'AutoScalingGroups[0].Instances[?HealthStatus==`Unhealthy`]'
```

## Cross-Provider Notes

- Auto Scaling group names are case-sensitive (unlike some other AWS resources)
- `predictedArn` uses a wildcard form (`*` for UUID) before the group is created in AWS
- On-Demand/Spot mixing via `mixedInstancesPolicy` is AWS-specific
- Lifecycle hooks and warm pools are AWS-specific features
- Termination policy options differ across AWS, GCP, and Azure
- Capacity rebalancing for Spot is AWS-specific; other providers use different mechanisms
