---
title: APIGatewayVPCLink — Private Integrations
description: "The `APIGatewayVPCLink` resource creates VPC links that connect API Gateway to Network Load Balancers (NLBs) inside VPCs."
doc_type: reference
---
# APIGatewayVPCLink — Private Integrations

The `APIGatewayVPCLink` resource creates VPC links that connect API Gateway to Network Load Balancers (NLBs) inside VPCs. VPC links enable private backend integrations without exposing backends to the public internet.

## Overview

A VPC link is a dedicated network tunnel from API Gateway to a private NLB. This enables REST API methods to integrate with backends that run inside VPCs without requiring public endpoints.

VPC links are standalone resources with independent lifecycle — they can be created, updated, or deleted independently of the REST APIs that reference them.

## Quick Start

### Basic VPC Link

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayVPCLink
metadata:
  name: internal-link
  namespace: default
spec:
  configRef: general-policy
  description: Link to internal NLB
  targetArns:
    - arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/net/internal-nlb/1234567890123456
```

### Using the VPC Link in an API

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayRestAPI
metadata:
  name: orders-api
  namespace: default
spec:
  configRef: general-policy
  resources:
    - pathPart: orders
      methods:
        - httpMethod: GET
          integration:
            type: HTTP_PROXY
            uri: http://internal-backend:8080/orders
            connectionType: VPC_LINK
            connectionRef: internal-link  # References APIGatewayVPCLink CR
```

## Configuration Reference

```yaml
spec:
  # Governance
  configRef: general-policy        # APIGatewayConfig profile
  nameOverride: ""                 # Override naming template
  deletionPolicy: retain           # retain | delete
  
  # Metadata
  tags: {}                         # AWS tags
  syncedLabels: {}                 # K8s labels (synced to AWS tags)
  syncedAnnotations: {}            # K8s annotations
  
  # VPC Link properties
  description: ""                  # VPC link description
  targetArns: []                   # NLB ARNs (required; immutable)
```

### Target ARNs

The `targetArns` field specifies which NLBs the VPC link connects to. All targets must be in the same AWS account.

**NLB ARN format:**
```
arn:aws:elasticloadbalancing:region:account-id:loadbalancer/net/nlb-name/1234567890123456
```

Find an NLB ARN using AWS CLI:
```bash
aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?Type=='network'].LoadBalancerArn" \
  --output text
```

### Immutability Constraint

Once a VPC link is created, the `targetArns` field **cannot be changed**. If you need to change targets, you must delete and recreate the VPC link:

1. Update APIs to use a different VPC link
2. Delete the old VPC link CR
3. Create a new VPC link CR with different targets

### Default Values

| Field | Default | Behavior |
|---|---|---|
| `configRef` | `general-policy` | Fall through to default profile |
| `nameOverride` | `""` | Use naming template from profile |
| `deletionPolicy` | `"retain"` | Keep NLB when CR is deleted |
| `description` | `""` | No description |

### Status Outputs

```yaml
status:
  resourceName: internal-link      # Effective cloud name
  namingStatus: valid              # valid | invalid-unresolved-tokens
  vpcLinkId: vpclnk-1234567890abc  # AWS-assigned VPC link ID
  status: AVAILABLE                # AVAILABLE | PENDING | DELETING | FAILED
  conditions:
    - type: Ready
      status: "True"
      reason: ReconciliationSucceeded
```

## Architecture Patterns

### Private Microservices Backend

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayVPCLink
metadata:
  name: microservices-link
  namespace: production
spec:
  configRef: prod
  description: Link to microservices NLB
  targetArns:
    - arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/net/microservices-nlb/abc123def456
---
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayRestAPI
metadata:
  name: public-api
  namespace: production
spec:
  configRef: prod
  description: Public-facing API
  resources:
    - pathPart: users
      methods:
        - httpMethod: GET
          integration:
            type: HTTP_PROXY
            uri: http://user-service.internal:8080/users
            connectionType: VPC_LINK
            connectionRef: microservices-link
    - pathPart: orders
      methods:
        - httpMethod: GET
          integration:
            type: HTTP_PROXY
            uri: http://order-service.internal:8080/orders
            connectionType: VPC_LINK
            connectionRef: microservices-link
```

### Multi-Environment VPC Links

```yaml
# Development environment
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayVPCLink
metadata:
  name: dev-backend-link
  namespace: dev
spec:
  configRef: dev
  targetArns:
    - arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/net/dev-nlb/abc123
---
# Production environment
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayVPCLink
metadata:
  name: prod-backend-link
  namespace: prod
spec:
  configRef: prod
  targetArns:
    - arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/net/prod-nlb/xyz789
```

## Deletion Policy

- **retain** (default) — Keep the NLB when the VPC link Kubernetes CR is deleted
- **delete** — Delete both the Kubernetes CR and the VPC link (NLB is preserved)

```yaml
spec:
  deletionPolicy: retain  # Keep VPC link when CR is deleted
```

Note: The deletion policy does NOT control whether the NLB is deleted. The NLB lifecycle is independent. Delete the VPC link only when you're sure no APIs reference it.

## Naming and Identification

VPC links use naming templates to generate cloud names:

```yaml
spec:
  # With profile template "{namespace}-{name}" and namespace production:
  # Resulting name: production-internal-link
  
  nameOverride: my-custom-link  # Override naming template
```

The effective name is exposed in `status.resourceName`.

## Monitoring

### Check VPC Link Status

```bash
kubectl describe vpclink internal-link -n default
```

Look for:
- `status.vpcLinkId` — AWS-assigned VPC link ID
- `status.status` — VPC link status (AVAILABLE, PENDING, etc.)
- `status.namingStatus` — Naming validation result

### Verify VPC Link Availability

```bash
kubectl get vpclink -n default -o wide
```

Only AVAILABLE status VPC links can be used for integrations.

### List APIs Using a VPC Link

Find all APIs that reference a VPC link:

```bash
kubectl get restapi -A -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.resources[*].methods[*].integration.connectionRef}{"\n"}{end}'
```

## Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| VPC link stuck in PENDING | NLB not ready or subnet/security group issues | Verify NLB status; check security groups allow API Gateway traffic |
| VPC link FAILED status | NLB deleted or not reachable | Recreate NLB or VPC link with valid NLB ARN |
| Backend unreachable | DNS resolution or routing issue | Verify NLB accepts traffic on specified port; check security group rules |
| Cannot change targetArns | Field is immutable | Delete and recreate VPC link with new target ARNs |

## Deletion Workflow

To safely remove a VPC link:

1. Identify all APIs using the VPC link:
   ```bash
   kubectl get restapi -A --field-selector spec.resources[*].methods[*].integration.connectionRef=internal-link
   ```

2. Update those APIs to use a different VPC link or remove the VPC_LINK integration type

3. Verify no APIs reference the old VPC link

4. Delete the VPC link CR:
   ```bash
   kubectl delete vpclink internal-link -n default
   ```

## Limits

- **Target NLBs:** Up to 10 targets per VPC link (immutable)
- **Subnets:** VPC link automatically spans all subnets in the NLB target VPC
- **NLB configuration:** NLB must allow traffic on the port specified in the integration URI
- **Cross-account:** VPC links cannot reference NLBs in different AWS accounts

## Performance Considerations

- VPC link initialization takes 1-5 minutes (status shows PENDING until ready)
- Once AVAILABLE, integrations using the VPC link have latency similar to direct NLB access
- NLB throughput limits apply to APIs using the VPC link
- Consider NLB capacity planning when sizing for API traffic

## Cross-Provider Notes

- `APIGatewayVPCLink` is AWS-specific
- GCP uses VPC connectors (Cloud Run integration)
- Azure uses VNet integration and private endpoints
- This resource only works with REST APIs, not HTTP APIs (APIGatewayV2)

## See Also

- [API Gateway — Family Overview](index.md)
- [REST APIs](apigatewayrestapi.md) — Create and manage APIs
- [Governance Configuration](apigatewayconfig.md) — Profile settings
- [AWS API Gateway VPC Links — Developer Guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-private-integration.html)
- [Network Load Balancers](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/)
