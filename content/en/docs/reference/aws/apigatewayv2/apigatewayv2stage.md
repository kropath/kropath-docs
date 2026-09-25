---
title: ApiGatewayV2Stage — Deployment Stages
description: "The `ApiGatewayV2Stage` resource creates named deployment stages for APIs (HTTP or WebSocket), enabling dev, staging, and production environments."
doc_type: reference
---
# ApiGatewayV2Stage — Deployment Stages

The `ApiGatewayV2Stage` resource creates named deployment stages for APIs (HTTP or WebSocket), enabling dev, staging, and production environments. Stages expose APIs at invoke URLs and control access logging, throttling, and route-specific settings.

## Overview

Use `ApiGatewayV2Stage` to:

- **Deploy to environments** — Separate dev, staging, and prod stages from one API
- **Enable auto-deployment** — Automatically deploy API changes to HTTP API stages
- **Control throttling** — Set rate limits and burst thresholds per-stage
- **Configure logging** — Route access logs to CloudWatch or Kinesis Firehose
- **Customize routes** — Override settings for specific routes (throttling, logging level)
- **Stage variables** — Pass configuration to backend Lambda via stage variables

Each stage exposes the API at a distinct URL: `https://<api-id>.execute-api.<region>.amazonaws.com/<stage-name>/`

## Creating a Stage

### Simple Dev Stage

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2Stage
metadata:
  name: orders-api-dev
  namespace: api-prod
spec:
  configRef: general-policy
  apiRef: orders-api  # Reference the HTTP or WebSocket API
  stageName: dev
  description: "Development stage for testing"
```

This stage:
- Exposes the API at `https://<api-id>.execute-api.region.amazonaws.com/dev/`
- Inherits throttling and logging from the governance profile
- Uses standard metadata and labels

### Production Stage with Logging

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2Stage
metadata:
  name: orders-api-prod
  namespace: api-prod
spec:
  configRef: general-policy
  apiRef: orders-api
  stageName: prod
  description: "Production stage"
  
  accessLogSettings:
    destinationArn: "arn:aws:logs:us-east-1:123456789012:log-group:/api-gateway/orders"
    format: "$json"
  
  defaultRouteSettings:
    throttlingRateLimit: 1000   # 1000 requests per second
    throttlingBurstLimit: 2000  # 2000 concurrent requests
    detailedMetricsEnabled: true
```

This stage:
- Routes all access logs to CloudWatch
- Enforces rate limiting (1000 req/sec, 2000 burst)
- Enables detailed CloudWatch metrics
- Suitable for production traffic

### Stage with Auto-Deploy (HTTP APIs only)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2Stage
metadata:
  name: orders-api-staging
  namespace: api-prod
spec:
  configRef: general-policy
  apiRef: orders-api
  stageName: staging
  autoDeploy: true  # Automatically deploy API changes
```

Auto-deploy applies route and integration updates to this stage without manual deployment. Only available for HTTP APIs.

### Stage with Route-Specific Settings

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2Stage
metadata:
  name: orders-api-prod
  namespace: api-prod
spec:
  configRef: general-policy
  apiRef: orders-api
  stageName: prod
  
  defaultRouteSettings:
    throttlingRateLimit: 1000
    throttlingBurstLimit: 2000
  
  routeSettings:
    "GET /orders":
      throttlingRateLimit: 2000      # Higher limit for read-heavy endpoint
    "POST /orders":
      throttlingRateLimit: 100       # Lower limit for write operations
      detailedMetricsEnabled: true   # Enable metrics for create operations
    "$default":
      loggingLevel: "ERROR"          # Only log errors for unmatched routes
```

Override throttling and logging per-route.

### Stage with Variables

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2Stage
metadata:
  name: orders-api-dev
  namespace: api-prod
spec:
  configRef: general-policy
  apiRef: orders-api
  stageName: dev
  
  stageVariables:
    env: "development"
    logLevel: "DEBUG"
    database: "dev-db"
```

Lambda functions access stage variables via `event.stageVariables`:

```python
def lambda_handler(event, context):
    env = event['stageVariables']['env']
    log_level = event['stageVariables']['logLevel']
    db = event['stageVariables']['database']
    # Use configuration from stage
```

## Configuration

### Access Logging

Enable access logs to CloudWatch or Kinesis Firehose:

```yaml
spec:
  accessLogSettings:
    destinationArn: "arn:aws:logs:us-east-1:123456789012:log-group:/api-logs"
    format: "$json"  # JSON format
```

**Log format options:**

- `"$json"` — Structured JSON logging (recommended)
- `"$clf"` — Common Log Format
- Custom: `"$context.requestId $context.status $context.error.message"`

Logs include request ID, HTTP status, latency, error messages, and custom context variables.

### Throttling

Control throughput at the stage or route level:

```yaml
spec:
  defaultRouteSettings:
    throttlingRateLimit: 1000   # requests per second
    throttlingBurstLimit: 2000  # concurrent requests
```

**Rate limit:** Enforced over a 1-second window. `0.0` uses AWS account default.

**Burst limit:** Peak concurrent requests allowed before throttling. `0` uses AWS account default.

When exceeded, API Gateway returns HTTP 429 (Too Many Requests).

### Route Settings

Override settings for specific routes:

```yaml
spec:
  defaultRouteSettings:
    throttlingRateLimit: 1000
  
  routeSettings:
    "GET /orders":
      throttlingRateLimit: 2000  # Override rate limit for this route
    "POST /orders":
      dataTraceEnabled: true     # Log request/response bodies
    "DELETE /orders/{id}":
      detailedMetricsEnabled: true  # Enable detailed CloudWatch metrics
```

### Metrics

Enable detailed CloudWatch metrics:

```yaml
spec:
  defaultRouteSettings:
    detailedMetricsEnabled: true
```

Metrics include:
- Count (request count)
- 4XXError, 5XXError (error counts)
- Latency (request latency)
- IntegrationLatency (backend latency)

### Logging Levels (WebSocket only)

Set logging level for WebSocket routes:

```yaml
spec:
  defaultRouteSettings:
    loggingLevel: "INFO"  # ERROR | INFO | OFF
```

- `ERROR` — Log errors only
- `INFO` — Log info and errors
- `OFF` — Disable logging

## Stage Names

**Predefined stage:** Use `$default` for the default stage:

```yaml
spec:
  stageName: "$default"
```

**Custom stages:** Any alphanumeric name:

```yaml
spec:
  stageName: prod
```

**Immutable:** Stage name cannot be changed after creation. Create a new stage if you need a different name.

## Tags and Labels

Add organization metadata:

```yaml
spec:
  tags:
    team: api-platform
    environment: production
  syncedLabels:
    app: order-service
  syncedAnnotations:
    slack-channel: "#api-alerts"
```

## Deletion Policy

### Retain (default)

```yaml
spec:
  deletionPolicy: "retain"
```

The stage remains in AWS.

### Delete

```yaml
spec:
  deletionPolicy: "delete"
```

The stage is deleted when the CR is deleted.

## Monitoring and Verification

### Check Stage Status

```bash
kubectl describe stage orders-api-prod -n api-prod
```

Look for:
- `status.conditions` — Ready, error, or warning states
- `spec.apiRef` — Connected API reference

### Test the Stage URL

```bash
# Get the stage URL
API_ID=$(kubectl get httpapi orders-api -n api-prod -o jsonpath='{.status.ackResourceMetadata.arn}' | cut -d: -f6)

# Test
curl https://${API_ID}.execute-api.us-east-1.amazonaws.com/prod/orders
```

### View CloudWatch Logs

```bash
aws logs tail /api-logs --follow
```

### Monitor CloudWatch Metrics

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=orders-api Name=StageName,Value=prod \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

### Check for Throttling

Look for `4XXError` or high `Latency` metrics, which indicate throttling.

## Updating a Stage

### Change Throttling Limits

Edit the CR:

```yaml
spec:
  defaultRouteSettings:
    throttlingRateLimit: 2000  # Increased from 1000
```

Apply the change.

### Add Route-Specific Settings

Add to `routeSettings`:

```yaml
spec:
  routeSettings:
    "POST /orders":  # New route-specific setting
      throttlingRateLimit: 500
```

### Enable Access Logging

Add or modify `accessLogSettings`:

```yaml
spec:
  accessLogSettings:
    destinationArn: "arn:aws:logs:us-east-1:123456789012:log-group:/new-logs"
    format: "$json"
```

### Add Stage Variables

Update `stageVariables`:

```yaml
spec:
  stageVariables:
    newVar: "value"
```

## Best Practices

1. **Use multiple stages** — Separate dev, staging, and prod; test changes in staging before promoting to prod.
2. **Enable logging** — CloudWatch logs are essential for debugging and monitoring.
3. **Enable metrics** — CloudWatch metrics help identify performance issues and throttling.
4. **Route-specific throttling** — Adjust throttle limits per-route based on expected load.
5. **Use stage variables** — Pass configuration to Lambda without redeploy.
6. **Auto-deploy for dev** — Enable for development stages to avoid manual deployments.
7. **Disable auto-deploy for prod** — Require explicit deployment for production.

## Limits

- Max 10 routes per stage with custom settings
- Max 128 characters for stage name
- Max 1024 characters for stage description
- Max 50 stage variables per stage

## Cross-Provider Notes

- API Gateway V2 stages are AWS-specific
- GCP Cloud API Gateway uses separate deployments instead of stages
- Azure API Management uses environments/slots for similar multi-environment support
- Stage variables are AWS-specific; other clouds use environment variables or config maps

## See Also

- [API Gateway V2](index.md) — Family overview
- [HTTP APIs](apigatewayv2httpapi.md) — Create HTTP APIs
- [WebSocket APIs](apigatewayv2websocketapi.md) — Create WebSocket APIs
- [Custom Domains](apigatewayv2domainname.md) — Use custom domain names with stages
- [Governance](apigatewayv2config.md) — Default logging and throttling
