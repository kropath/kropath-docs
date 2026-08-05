# AWS Elastic Load Balancing (ELB) Resources

The ELB resource family lets you create and manage Application Load Balancers (ALB), Network Load Balancers (NLB), and Gateway Load Balancers (GWLB) with centralized governance.

## Resources in This Family

| Resource | Purpose | Use Case |
|---|---|---|
| **[ELBConfig](elbconfig.md)** | Governance configuration | Platform teams define policies for load balancing |
| **[ELBLoadBalancer](elbloadbalancer.md)** | Application, network, or gateway load balancer | Create ALBs, NLBs, or GWLBs with configuration profiles |
| **[ELBTargetGroup](elbtargetgroup.md)** | Group of targets receiving traffic | Register EC2 instances, IPs, Lambda functions, or ALBs |
| **[ELBListener](elblistener.md)** | Connection listener on a load balancer | Define protocols, ports, and default routing actions |
| **[ELBRule](elbrule.md)** | ALB listener routing rule | Match conditions (path, host, headers) and route to targets |

## How the Resources Connect

```
ELBConfig
  ↓ (governance profile)
ELBLoadBalancer → ELBListener → ELBRule
     ↓                             ↓
ELBTargetGroup ← ← ← ← ← ← ← ← ← ↓
```

1. **Platform team** creates an `ELBConfig` profile in `kro-system`
2. **Developer** creates an `ELBLoadBalancer` (ALB, NLB, or GWLB)
3. **Developer** creates one or more `ELBTargetGroup` resources to group targets
4. **Developer** creates an `ELBListener` on the load balancer with default actions
5. **Developer** creates `ELBRule` resources on ALB listeners for path-based or host-based routing

## Key Governance Features

- **Mandatory tier:** Platform teams enforce policies (e.g., all load balancers must have deletion protection, must use a specific TLS policy)
- **Defaults tier:** Baseline values developers can override (e.g., default cross-zone load balancing for NLBs, default naming pattern)
- **Naming templates:** Automatic resource naming using tokens like `{namespace}`, `{name}`, `{configRef}`, and custom tags
- **Tag propagation:** Kubernetes labels automatically synced to AWS tags for cost tracking and resource organization

## Quick Start

Create an ALB with a target group and listener:

```yaml
---
# 1. Platform team: governance profile (in kro-system)
apiVersion: aws.kropath.run/v1alpha1
kind: ELBConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    deletionProtection: false
    crossZoneEnabled: true
    namingTemplate: "{namespace}-{name}"

---
# 2. Developer: load balancer
apiVersion: aws.kropath.run/v1alpha1
kind: ELBLoadBalancer
metadata:
  name: api-lb
  namespace: api-team
spec:
  configRef: general-policy
  type: application
  scheme: internet-facing
  subnets:
    - subnet-abc123
    - subnet-def456

---
# 3. Developer: target group
apiVersion: aws.kropath.run/v1alpha1
kind: ELBTargetGroup
metadata:
  name: api-targets
  namespace: api-team
spec:
  configRef: general-policy
  targetType: instance
  protocol: HTTP
  port: 80
  vpcId: vpc-12345678

---
# 4. Developer: listener
apiVersion: aws.kropath.run/v1alpha1
kind: ELBListener
metadata:
  name: api-listener
  namespace: api-team
spec:
  configRef: general-policy
  loadBalancerRef: api-lb
  protocol: HTTP
  port: 80
  defaultActions:
    - type: forward
      targetGroupRef: api-targets
```

Apply these resources to your cluster:

```bash
kubectl apply -f elb.yaml
```

## Documentation

- **[ELBConfig](elbconfig.md)** — Governance profiles and enforcement
- **[ELBLoadBalancer](elbloadbalancer.md)** — Creating ALBs, NLBs, and GWLBs
- **[ELBTargetGroup](elbtargetgroup.md)** — Target groups and health checks
- **[ELBListener](elblistener.md)** — Listeners and default actions
- **[ELBRule](elbrule.md)** — ALB routing rules and path-based routing

## Next Steps

1. Read [ELBConfig](elbconfig.md) to understand governance and create profiles
2. Follow [ELBLoadBalancer](elbloadbalancer.md) to provision load balancers
3. Set up [ELBTargetGroup](elbtargetgroup.md) resources for your workloads
4. Configure [ELBListener](elblistener.md) with protocol and port
5. Add [ELBRule](elbrule.md) for advanced routing (ALB only)
