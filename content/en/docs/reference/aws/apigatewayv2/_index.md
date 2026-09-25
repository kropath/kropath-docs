---
title: API Gateway V2
description: AWS API Gateway V2 provides a modern, cost-effective way to build serverless HTTP APIs and real-time WebSocket applications.
doc_type: reference
weight: 20
---
# API Gateway V2

AWS API Gateway V2 provides a modern, cost-effective way to build serverless HTTP APIs and real-time WebSocket applications. The API Gateway V2 family in kropath includes resources for creating, managing, and exposing APIs with custom domains, access control, and VPC integrations.

## What is API Gateway V2?

API Gateway V2 is the second generation of AWS API Gateway, offering two distinct protocol support:

- **HTTP APIs** — Optimized for HTTP and REST workloads. Lower latency, lower cost, and simpler configuration than REST APIs (v1). Best for Lambda proxy and HTTP proxy backends.
- **WebSocket APIs** — Enable bidirectional, stateful communication for real-time applications like chat, notifications, and live dashboards.

Both API types can use:
- Custom domain names with ACM certificates
- Stage-based deployments (dev, staging, prod)
- Throttling and access logging governance
- Route-key-based message routing and authorizers

## Resources

| Resource | Purpose | Phase |
|----------|---------|-------|
| [ApiGatewayV2Config](apigatewayv2config.md) | Governance configuration for API Gateway V2 policies | Phase 1 |
| [ApiGatewayV2HttpApi](apigatewayv2httpapi.md) | HTTP APIs with Lambda/HTTP proxy integrations | Phase 1 |
| [ApiGatewayV2WebSocketApi](apigatewayv2websocketapi.md) | WebSocket APIs for bidirectional communication | Phase 1 |
| [ApiGatewayV2Stage](apigatewayv2stage.md) | Deployment stages for APIs (dev, staging, prod) | Phase 1 |
| [ApiGatewayV2DomainName](apigatewayv2domainname.md) | Custom domain names with TLS certificates | Phase 2 |
| [ApiGatewayV2ApiMapping](apigatewayv2apimapping.md) | Route custom domain paths to APIs and stages | Phase 2 |
| [ApiGatewayV2VpcLink](apigatewayv2vpclink.md) | VPC connectivity for private integrations | Phase 2 |

## Getting Started

### 1. Set Up Governance (Phase 1)

Create a governance profile to define mandatory and default policies for all APIs:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2Config
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory:
    disableExecuteApiEndpoint: false
  defaults:
    minimumTlsVersion: "TLS_1_2"
    namingTemplate: "{namespace}-{name}"
```

### 2. Create an HTTP API (Phase 1)

Deploy an HTTP API with Lambda integration:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2HttpApi
metadata:
  name: orders-api
  namespace: api-prod
spec:
  configRef: general-policy
  routes:
    - routeKey: "GET /orders"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:list-orders"
    - routeKey: "POST /orders"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:create-order"
```

### 3. Create a Deployment Stage (Phase 1)

Deploy the API to a stage:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2Stage
metadata:
  name: orders-api-prod
  namespace: api-prod
spec:
  apiRef: orders-api
  stageName: prod
  autoDeploy: true
  defaultRouteSettings:
    throttlingRateLimit: 1000
    throttlingBurstLimit: 2000
```

### 4. Add a Custom Domain (Phase 2)

Route API traffic through a branded domain:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2DomainName
metadata:
  name: api-domain
  namespace: api-prod
spec:
  configRef: general-policy
  domainName: "api.example.com"
  domainNameConfigurations:
    - certificateArn: "arn:aws:acm:us-east-1:123456789012:certificate/12345"
```

### 5. Map Domain to API (Phase 2)

Connect the custom domain to your API stage:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2ApiMapping
metadata:
  name: orders-api-domain-mapping
  namespace: api-prod
spec:
  apiRef: orders-api
  domainRef: api-domain
  stage: prod
  apiMappingKey: ""  # Empty = root path
```

Now your API is accessible at `https://api.example.com/`

## Key Concepts

### HTTP API vs WebSocket API

| Feature | HTTP API | WebSocket API |
|---------|----------|---------------|
| Protocol | HTTP/REST | WebSocket (bidirectional) |
| Routes | `GET /path`, `POST /path` | `$connect`, `$disconnect`, `$default`, custom keys |
| Use case | Synchronous request/response | Bidirectional real-time communication |
| Authorizers | JWT and Lambda REQUEST | Lambda REQUEST only |
| Payload format | Flexible | JSON or binary |

### Naming

Resource names are auto-generated from a naming template. The default is `{namespace}-{name}`:

- Namespace: `api-prod`
- CR name: `orders-api`
- **Resulting API name:** `api-prod-orders-api`

Override with `spec.nameOverride`:

```yaml
spec:
  nameOverride: "my-orders-api"  # Use exactly this name
```

### Access Logging

Enable logging to CloudWatch or Kinesis Firehose through governance profiles:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2Config
metadata:
  name: logging-policy
  namespace: kro-system
spec:
  defaults:
    accessLogDestinationArn: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/apigateway/orders"
    accessLogFormat: "$context.requestId $context.error.message $context.error.messageString"
```

### Throttling and Rate Limiting

Control API throughput with governance policies:

```yaml
spec:
  mandatory:
    defaultThrottlingRateLimit: 1000  # Requests per second
    defaultThrottlingBurstLimit: 2000  # Peak burst
```

These limits apply to all API stages unless overridden at the stage level.

### VPC Integrations

For private backends, create a VPC Link for API Gateway to reach resources inside a VPC:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2VpcLink
metadata:
  name: internal-link
  namespace: api-prod
spec:
  subnetIds:
    - "subnet-12345678"
    - "subnet-87654321"
  securityGroupIds:
    - "sg-12345678"
```

Then reference it in your API routes:

```yaml
routes:
  - routeKey: "GET /internal"
    integration:
      type: HTTP_PROXY
      integrationUri: "http://internal-alb.example.com"
      connectionType: VPC_LINK
      connectionRef: internal-link
```

### Authorizers

Protect routes with JWT or Lambda authorizers:

**JWT Authorizer (HTTP APIs only):**

```yaml
authorizers:
  - name: auth0
    type: JWT
    jwtIssuer: "https://example.auth0.com/"
    jwtAudience:
      - "api.example.com"
    identitySource:
      - "$request.header.Authorization"

routes:
  - routeKey: "GET /protected"
    authorizationType: JWT
    authorizerRef: auth0
```

**Lambda REQUEST Authorizer (HTTP and WebSocket):**

```yaml
authorizers:
  - name: custom-auth
    type: REQUEST
    authorizerUri: "arn:aws:lambda:us-east-1:123456789012:function:authorizer"
    resultTtlInSeconds: 300

routes:
  - routeKey: "GET /protected"
    authorizationType: CUSTOM
    authorizerRef: custom-auth
```

### CORS Configuration

Enable cross-origin requests for browser-based clients:

```yaml
corsConfiguration:
  allowOrigins:
    - "https://example.com"
    - "https://app.example.com"
  allowMethods:
    - "GET"
    - "POST"
    - "DELETE"
  allowHeaders:
    - "Content-Type"
    - "Authorization"
  exposeHeaders:
    - "X-Custom-Header"
  maxAge: 3600
  allowCredentials: true
```

## Governance

Platform teams define governance through `ApiGatewayV2Config` profiles. These profiles cascade mandatory and default policies:

| Tier | Purpose | Example |
|------|---------|---------|
| **Mandatory** | Enforced on all APIs; no override | Disable `execute-api` endpoint for security |
| **Defaults** | Applied if not specified; can be overridden | Minimum TLS version, access log destination |

Use governance profiles to enforce:
- **TLS version minimum** — Require TLS 1.2 or higher
- **Access logging** — Log all API requests to CloudWatch
- **Throttling limits** — Rate limit API traffic
- **CORS enforcement** — Require CORS configuration on HTTP APIs
- **Resource naming** — Standardize API names across namespaces

## Deletion Policy

Control what happens to AWS resources when CRs are deleted:

### Retain (default)

```yaml
spec:
  deletionPolicy: "retain"
```

AWS resources remain when the CR is deleted. Recommended for production to prevent accidental data loss.

### Delete

```yaml
spec:
  deletionPolicy: "delete"
```

AWS resources are deleted when the CR is deleted. Use for temporary or test environments only.

## Tags and Labels

Add metadata for organization and cost tracking:

```yaml
spec:
  tags:
    team: api-platform
    cost-center: "1234"
    environment: production
  syncedLabels:
    app: order-service
    version: v2
  syncedAnnotations:
    slack-channel: "#api-alerts"
    on-call: "api-team"
```

Tags appear on the AWS API resource. Synced labels and annotations are mirrored to Kubernetes.

## Monitoring and Verification

### Check API Status

```bash
kubectl describe httpapi orders-api -n api-prod
```

Look for:
- `status.resourceName` — The actual API name in AWS
- `status.conditions` — Ready, error, or warning states

### Test an API

```bash
curl https://api.example.com/orders
```

### View CloudWatch Logs

Access logs are available in CloudWatch after enabling them through governance profiles:

```bash
aws logs tail /aws/apigateway/orders-api --follow
```

### Verify Custom Domain

```bash
nslookup api.example.com
```

Should resolve to the API Gateway regional endpoint.

## Cross-Provider Notes

- API Gateway V2 is AWS-specific
- GCP offers Cloud API Gateway and Cloud Endpoints for similar use cases
- Azure provides API Management (APIM) for enterprise API governance
- WebSocket APIs are an AWS-specific feature; other clouds use different mechanisms
- VPC Link connectivity is AWS-specific; GCP and Azure use different private networking approaches

## See Also

- [API Gateway V2 Config](apigatewayv2config.md) — Governance profiles
- [HTTP APIs](apigatewayv2httpapi.md) — RESTful APIs with Lambda backends
- [WebSocket APIs](apigatewayv2websocketapi.md) — Real-time bidirectional communication
- [Stages](apigatewayv2stage.md) — Deployment environments
- [Custom Domains](apigatewayv2domainname.md) — Branded URLs
- [API Mapping](apigatewayv2apimapping.md) — Domain path routing
- [VPC Links](apigatewayv2vpclink.md) — Private integrations
