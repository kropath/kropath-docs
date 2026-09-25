---
title: Auto Scaling
description: Manage EC2 Auto Scaling groups with governance, capacity control, and lifecycle policies.
doc_type: reference
weight: 50
---
# Auto Scaling

Manage EC2 Auto Scaling groups with governance, capacity control, and lifecycle policies.

## Resources

- **[AutoScalingConfig](autoscalingconfig.md)** — Governance profiles for compliance and operational policies
- **[AutoScalingGroup](autoscalinggroup.md)** — Managed instance fleets with auto-scaling and health management

## Getting Started

1. **Define governance:** Create `AutoScalingConfig` profiles in `kro-system` namespace (or use the built-in `general-policy`)
2. **Create groups:** Deploy `AutoScalingGroup` resources in your application namespaces, selecting a profile via `configRef`
3. **Monitor capacity:** Use `kubectl` to check group status; use AWS CLI for detailed capacity and instance information

## Common Scenarios

### High-Availability Web Backend

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AutoScalingGroup
metadata:
  name: api-backend
  namespace: api-prod
spec:
  configRef: production
  minSize: 3
  maxSize: 20
  launchTemplate:
    name: backend-v2
  vpcZoneIdentifier: "subnet-az1,subnet-az2,subnet-az3"
  healthCheckType: "ELB"
  targetGroupARNs:
    - "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/api/abc123"
```

### Cost-Optimized Compute Cluster

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AutoScalingGroup
metadata:
  name: batch-workers
  namespace: compute
spec:
  minSize: 1
  maxSize: 50
  launchTemplate:
    name: worker
  mixedInstancesPolicy:
    onDemandBaseCapacity: 2
    onDemandPercentageAboveBaseCapacity: 20
    spotAllocationStrategy: "capacity-optimized"
```

## Governance

Auto Scaling groups enforce governance through `AutoScalingConfig` profiles:

- **Mandatory tier:** Non-overrideable controls (e.g., instance rotation policies, mandatory health checks)
- **Defaults tier:** Baseline values developers can override

Platform teams define profiles; developers select which profile applies to their group via `spec.configRef`.
