---
title: APIGatewayDeployment — Deployments and Stages
description: "The `APIGatewayDeployment` resource deploys REST APIs to stages."
doc_type: reference
---
# APIGatewayDeployment — Deployments and Stages

The `APIGatewayDeployment` resource deploys REST APIs to stages. A deployment captures the current API configuration at a point in time; a stage exposes that configuration to callers via an invoke URL with optional caching, canary deployments, and tracing.

## Overview

Deployments and stages are closely related:

- **Deployment** — A snapshot of the REST API configuration (resource structure, methods, integrations)
- **Stage** — A named environment endpoint (e.g. `dev`, `prod`) that exposes the deployment to clients

The `APIGatewayDeployment` resource composes both into one logical concept: "make this API version available at a named endpoint."

## Quick Start

### Basic Deployment to Production

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayDeployment
metadata:
  name: orders-prod
  namespace: production
spec:
  configRef: prod
  restApiRef: orders-api
  stageName: prod
  description: Production deployment
```

### Deployment with Caching

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayDeployment
metadata:
  name: orders-prod
  namespace: production
spec:
  configRef: prod
  restApiRef: orders-api
  stageName: prod
  cacheClusterEnabled: true
  cacheClusterSize: "1.6"  # 1.6 GB cache
  description: Production deployment with caching
```

### Deployment with Canary

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayDeployment
metadata:
  name: orders-prod-canary
  namespace: production
spec:
  configRef: prod
  restApiRef: orders-api
  stageName: prod
  canarySettings:
    percentTraffic: 10.0  # Send 10% of traffic to canary
    useStageCache: false  # Canary doesn't use main stage cache
```

## Configuration Reference

```yaml
spec:
  # Governance
  configRef: general-policy         # APIGatewayConfig profile
  deletionPolicy: retain            # retain | delete
  
  # Metadata (applied to Stage only)
  tags: {}                          # AWS tags (Stage only)
  syncedLabels: {}                  # K8s labels
  syncedAnnotations: {}             # K8s annotations
  
  # Required
  restApiRef: orders-api            # Local APIGatewayRestAPI CR name
  stageName: prod                   # Stage name (required; max 128 chars)
  
  # Stage properties
  description: ""                   # Deployment description
  stageDescription: ""              # Stage description
  variables: {}                     # Stage variables (map of strings)
  
  # Caching
  cacheClusterEnabled: false        # Enable stage cache
  cacheClusterSize: ""              # Cache size: 0.5, 1.6, 6.1, 13.5, 28.4, 58.2, 118, 237 GB
  
  # Observability
  tracingEnabled: false             # Enable X-Ray active tracing
  
  # Canary deployment
  canarySettings:
    percentTraffic: 0.0             # Canary traffic percentage (0.0-100.0)
    stageVariableOverrides: {}      # Stage variable overrides for canary
    useStageCache: false            # Canary uses stage cache
```

### Stage Name

The `stageName` is a user-chosen identifier for the deployment endpoint:

- **Format:** Alphanumeric, hyphens, underscores; max 128 characters
- **Examples:** `prod`, `staging`, `v1`, `canary`, `blue-green-prod`
- **Invoke URL:** `https://{restApiId}.execute-api.{region}.amazonaws.com/{stageName}`

Each REST API can have multiple stages (deployments) deployed independently.

### Stage Variables

Stage variables are key-value pairs available to backend integrations and can be used in request/response mappings:

```yaml
spec:
  variables:
    backend_url: "https://prod-backend.example.com"
    log_level: "INFO"
    max_retries: "3"
```

Access in integrations via `$stageVariables.{variable-name}`:
```
integration.requestParameters:
  integration.request.header.X-Backend-Url: stageVariables.backend_url
```

### Caching

Enable response caching to reduce backend load and improve latency:

```yaml
spec:
  cacheClusterEnabled: true   # Enable cache
  cacheClusterSize: "1.6"     # 1.6 GB cache cluster
```

**Valid cache sizes:** 0.5, 1.6, 6.1, 13.5, 28.4, 58.2, 118, 237 GB

Caching is only meaningful when `cacheClusterEnabled: true`. Without it, `cacheClusterSize` is ignored.

**Cache key:** Derived from request parameters and headers specified in method/integration configuration.

**Cache validity:** Use method/integration `cacheKeyParameters` to define what goes into the cache key.

### Tracing

Enable X-Ray active tracing to record and analyze API traffic:

```yaml
spec:
  tracingEnabled: true  # Enable X-Ray tracing
```

When enabled, API Gateway sends detailed request/response traces to AWS X-Ray for analysis and debugging.

### Canary Deployment

Gradually roll out API changes using canary deployment (traffic splitting):

```yaml
spec:
  canarySettings:
    percentTraffic: 10.0           # Route 10% of traffic to canary
    useStageCache: false           # Canary ignores main stage cache
    stageVariableOverrides:        # Different config for canary
      backend_url: "https://canary-backend.example.com"
      log_level: "DEBUG"
```

- **percentTraffic** — Percentage of traffic routed to canary (0.0-100.0)
- **useStageCache** — Whether canary uses the main stage's cache (false = independent testing)
- **stageVariableOverrides** — Override stage variables for canary traffic

Canary is ideal for testing API changes with real production traffic before full rollout.

### Default Values

| Field | Default | Behavior |
|---|---|---|
| `configRef` | `general-policy` | Fall through to default profile |
| `description` | `""` | No deployment description |
| `stageDescription` | `""` | No stage description |
| `variables` | `{}` | No stage variables |
| `cacheClusterEnabled` | `false` | Caching disabled |
| `cacheClusterSize` | `""` | Not set (only meaningful with caching enabled) |
| `tracingEnabled` | `false` | X-Ray tracing disabled |
| `canarySettings.percentTraffic` | `0.0` | No canary traffic |

### Status Outputs

```yaml
status:
  deploymentId: abc123def456       # AWS-assigned deployment ID
  stageInvokeUrl: https://a1b2c3d4e5.execute-api.us-east-1.amazonaws.com/prod
  conditions:
    - type: Ready
      status: "True"
      reason: ReconciliationSucceeded
```

## Common Patterns

### Progressive Rollout Strategy

```yaml
# 1. Deploy to staging first
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayDeployment
metadata:
  name: orders-staging
  namespace: production
spec:
  configRef: prod
  restApiRef: orders-api
  stageName: staging
  description: Staging deployment for testing

---
# 2. Deploy to production with canary (10% traffic)
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayDeployment
metadata:
  name: orders-prod-canary
  namespace: production
spec:
  configRef: prod
  restApiRef: orders-api
  stageName: prod
  canarySettings:
    percentTraffic: 10.0
    useStageCache: false

# After monitoring canary (5-30 minutes)...
# 3. Promote canary to 100% (delete canary, redeploy without it)
```

### Blue-Green Deployment

```yaml
# Blue deployment (current production)
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayDeployment
metadata:
  name: orders-blue
  namespace: production
spec:
  configRef: prod
  restApiRef: orders-api
  stageName: prod-blue

---
# Green deployment (new version) to separate stage
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayDeployment
metadata:
  name: orders-green
  namespace: production
spec:
  configRef: prod
  restApiRef: orders-api
  stageName: prod-green

# Test prod-green, then update clients to use prod-green
# Delete orders-blue after full cutover
```

### Multi-Environment Deployments

```yaml
# Development
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayDeployment
metadata:
  name: orders-dev
  namespace: development
spec:
  configRef: dev
  restApiRef: orders-api-dev
  stageName: dev

---
# Staging
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayDeployment
metadata:
  name: orders-staging
  namespace: staging
spec:
  configRef: staging
  restApiRef: orders-api
  stageName: staging

---
# Production with caching and tracing
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayDeployment
metadata:
  name: orders-prod
  namespace: production
spec:
  configRef: prod
  restApiRef: orders-api
  stageName: prod
  cacheClusterEnabled: true
  cacheClusterSize: "6.1"
  tracingEnabled: true
```

## Naming

APIGatewayDeployment **does not use naming templates**. The stage name and deployment ID are determined by:

- **Deployment ID** — AWS-assigned (system-generated)
- **Stage Name** — User-specified in `spec.stageName`
- **Invoke URL** — Constructed from REST API ID and stage name

This is different from other API Gateway resources (RestAPI, Authorizer, etc.) which use naming templates.

## Deletion Policy

- **retain** (default) — Keep the stage and deployment in AWS when the Kubernetes CR is deleted
- **delete** — Delete both the Kubernetes CR and the AWS deployment/stage

```yaml
spec:
  deletionPolicy: delete  # Delete AWS resources when CR is deleted
```

## Monitoring

### Check Deployment Status

```bash
kubectl describe deployment orders-prod -n production
```

Look for:
- `status.deploymentId` — AWS deployment ID
- `status.stageInvokeUrl` — The public endpoint URL
- `status.conditions` — Reconciliation status

### Invoke the Deployed API

```bash
curl https://a1b2c3d4e5.execute-api.us-east-1.amazonaws.com/prod/orders
```

### Monitor Canary Metrics

After enabling canary, monitor metrics in CloudWatch:

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Invocations \
  --dimensions Name=ApiName,Value=orders-api Name=Stage,Value=prod \
  --start-time 2026-08-18T00:00:00Z \
  --end-time 2026-08-18T01:00:00Z \
  --period 300 \
  --statistics Sum
```

## Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| Deployment stuck in PENDING | REST API changes not finalized | Wait for RestAPI reconciliation to complete; check RestAPI status |
| 403 Forbidden from stage | API key required but not provided | Pass API key header if `apiKeyRequired: true` on methods |
| Cache not working | Cache not properly configured | Verify `cacheClusterEnabled: true` and `cacheClusterSize` is set |
| Canary shows wrong backend | Stage variables not overridden | Verify `stageVariableOverrides` are set correctly |
| X-Ray traces missing | Tracing not enabled | Set `tracingEnabled: true` in deployment |

## Best Practices

### Use Stages for Environment Isolation

```yaml
# ✓ Good: One deployment per environment
stageName: dev
stageName: staging
stageName: prod
```

```yaml
# ✗ Avoid: Using REST API names for env isolation
stageName: orders-api-dev
stageName: orders-api-prod
```

### Enable Caching in Production

For high-traffic APIs, enable caching to reduce backend load:

```yaml
cacheClusterEnabled: true
cacheClusterSize: "6.1"  # 6.1 GB for medium load
```

### Use Canary for Major Changes

Roll out risky changes gradually using canary:

```yaml
canarySettings:
  percentTraffic: 5.0   # Start with 5%
  # Monitor for 30 min, increase to 10%, then 50%, then 100%
```

### Enable Tracing in Production

For debugging and performance analysis:

```yaml
tracingEnabled: true
```

### Document Deployments

Always include meaningful descriptions:

```yaml
description: "Orders API v2.1 - improved error handling"
stageDescription: "Production stage with canary deployment"
```

## Cross-Provider Notes

- `APIGatewayDeployment` is AWS-specific
- GCP uses API versions and revisions
- Azure uses deployment slots (app service) or revisions (container apps)
- This resource only works with REST APIs, not HTTP APIs (APIGatewayV2)

## See Also

- [API Gateway — Family Overview](index.md)
- [REST APIs](apigatewayrestapi.md) — Create and manage APIs
- [Governance Configuration](apigatewayconfig.md) — Profile settings
- [AWS API Gateway Stages — Developer Guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/stages.html)
- [AWS X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/)
- [Canary Deployments](https://docs.aws.amazon.com/apigateway/latest/developerguide/canary-deployment.html)
