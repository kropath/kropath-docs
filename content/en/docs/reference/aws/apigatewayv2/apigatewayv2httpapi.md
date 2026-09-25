---
title: ApiGatewayV2HttpApi — HTTP REST APIs
description: "The `ApiGatewayV2HttpApi` resource creates modern, serverless HTTP APIs optimized for Lambda proxy and HTTP proxy workloads."
doc_type: reference
---
# ApiGatewayV2HttpApi — HTTP REST APIs

The `ApiGatewayV2HttpApi` resource creates modern, serverless HTTP APIs optimized for Lambda proxy and HTTP proxy workloads. HTTP APIs are simpler, faster, and cheaper than REST APIs (API Gateway v1), with built-in support for CORS, authorizers, and throttling.

## Overview

Use `ApiGatewayV2HttpApi` to create:

- **Lambda proxy APIs** — Invoke Lambda functions directly with API Gateway handling request/response transformation
- **HTTP proxy APIs** — Route requests to HTTP endpoints (ALB, NLB, private HTTP services)
- **Multi-route APIs** — Define multiple routes (`GET /users`, `POST /users/{id}`) in one API
- **Secured APIs** — Use JWT or Lambda authorizers to protect routes
- **Cross-origin APIs** — Enable CORS for browser-based clients
- **Throttled APIs** — Control throughput and burst traffic

HTTP APIs automatically expose a default `execute-api` endpoint (e.g. `https://api-id.execute-api.region.amazonaws.com`). Use custom domains to provide branded URLs.

## Creating an HTTP API

### Simple Single-Route API

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2HttpApi
metadata:
  name: hello-api
  namespace: api-prod
spec:
  configRef: general-policy
  routes:
    - routeKey: "GET /"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:hello"
```

This API:
- Creates a single route `GET /`
- Invokes the `hello` Lambda function
- Is named `api-prod-hello-api` (from naming template)
- Accessible at `https://<api-id>.execute-api.us-east-1.amazonaws.com/`

### Multi-Route RESTful API

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2HttpApi
metadata:
  name: orders-api
  namespace: api-prod
spec:
  configRef: general-policy
  description: "Orders microservice API"
  version: "1.0"
  routes:
    - routeKey: "GET /orders"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:list-orders"
    
    - routeKey: "GET /orders/{id}"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:get-order"
    
    - routeKey: "POST /orders"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:create-order"
    
    - routeKey: "PUT /orders/{id}"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:update-order"
    
    - routeKey: "DELETE /orders/{id}"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:delete-order"
```

### API with JWT Authorization

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2HttpApi
metadata:
  name: secure-api
  namespace: api-prod
spec:
  configRef: general-policy
  authorizers:
    - name: auth0
      type: JWT
      jwtIssuer: "https://example.auth0.com/"
      jwtAudience:
        - "api.example.com"
      identitySource:
        - "$request.header.Authorization"
  
  routes:
    - routeKey: "GET /public"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:public"
    
    - routeKey: "GET /protected"
      authorizationType: JWT
      authorizerRef: auth0
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:protected"
```

Routes without `authorizerRef` are public. Routes with `authorizerRef` require a valid JWT from the specified issuer.

### API with CORS

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2HttpApi
metadata:
  name: web-api
  namespace: api-prod
spec:
  configRef: general-policy
  corsConfiguration:
    allowOrigins:
      - "https://example.com"
      - "https://app.example.com"
      - "http://localhost:3000"
    allowMethods:
      - "GET"
      - "POST"
      - "PUT"
      - "DELETE"
      - "OPTIONS"
    allowHeaders:
      - "Content-Type"
      - "Authorization"
      - "X-API-Key"
    exposeHeaders:
      - "X-RateLimit-Limit"
      - "X-RateLimit-Remaining"
    maxAge: 3600
    allowCredentials: true
  
  routes:
    - routeKey: "GET /data"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:fetch-data"
```

CORS applies to all routes. Browsers will automatically include CORS headers in requests.

### API with HTTP Proxy Integration

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2HttpApi
metadata:
  name: proxy-api
  namespace: api-prod
spec:
  configRef: general-policy
  routes:
    - routeKey: "GET /api"
      integration:
        type: HTTP_PROXY
        integrationUri: "https://backend-service.example.com/api"
        integrationMethod: "GET"
```

HTTP proxy APIs pass requests directly to HTTP backends (ALBs, NLBs, private HTTP services).

### API with VPC Link Integration

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2HttpApi
metadata:
  name: internal-api
  namespace: api-prod
spec:
  configRef: general-policy
  routes:
    - routeKey: "GET /internal"
      integration:
        type: HTTP_PROXY
        integrationUri: "http://internal-alb.example.com"
        connectionType: VPC_LINK
        connectionRef: internal-vpc-link
```

VPC Link enables API Gateway to reach private resources inside your VPC.

## Configuration

### Routes

Each route defines a path, HTTP method, and integration backend.

**Route Key Syntax:**

- `"GET /path"` — Single HTTP method
- `"POST /path/{id}"` — Path parameters in curly braces
- `"$default"` — Catch-all for unmatched routes

```yaml
routes:
  - routeKey: "GET /users"
    name: "list-users"  # Optional: used in child CR names
    operationName: "ListUsers"  # OpenAPI operation name
```

### Integrations

Choose how the API reaches its backend.

**AWS_PROXY (Lambda Proxy):**

```yaml
integration:
  type: AWS_PROXY
  integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:handler"
```

API Gateway passes the request directly to Lambda with no transformation. Lambda must return a response in the expected format.

**HTTP_PROXY (HTTP):**

```yaml
integration:
  type: HTTP_PROXY
  integrationUri: "https://backend.example.com"
  integrationMethod: "GET"  # Can differ from route method
  payloadFormatVersion: "2.0"  # 1.0 or 2.0
  timeoutInMillis: 30000  # 50-30000 ms
```

Pass requests to HTTP endpoints. Request transformation is minimal.

**Request/Response Parameters:**

```yaml
integration:
  requestParameters:
    "overwrite:path": "method.request.path.id"
    "append:querystring": "method.request.querystring.filter"
  responseParameters:
    "statuscode": "method.response.status"
```

Transform request/response headers and query parameters.

### Authorizers

Protect routes with authentication and authorization.

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
```

Validates JWT tokens from a trusted issuer.

**Lambda REQUEST Authorizer:**

```yaml
authorizers:
  - name: custom-auth
    type: REQUEST
    authorizerUri: "arn:aws:lambda:us-east-1:123456789012:function:authorizer"
    authorizerCredentials: "arn:aws:iam::123456789012:role/authorizer-role"
    payloadFormatVersion: "2.0"
    enableSimpleResponses: true
    resultTtlInSeconds: 300
```

Invoke a Lambda function to make authorization decisions. Results are cached for the specified TTL.

### CORS Configuration

Enable cross-origin requests:

```yaml
corsConfiguration:
  allowOrigins: ["*"]  # or specific origins
  allowMethods: ["GET", "POST", "DELETE"]
  allowHeaders: ["Content-Type", "Authorization"]
  exposeHeaders: ["X-Total-Count"]
  maxAge: 3600
  allowCredentials: false
```

## Naming

Resource names are generated from a naming template. Default: `{namespace}-{name}`

```yaml
metadata:
  namespace: api-prod
  name: orders-api
# Resulting name: api-prod-orders-api
```

Override the template:

```yaml
spec:
  nameOverride: "my-orders-api"  # Use exactly this name
```

Max length: 128 characters. alphanumeric and common punctuation only.

## Tags and Labels

Add organization metadata:

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

Tags appear on the AWS API resource. Labels and annotations are synced to Kubernetes.

## Deletion Policy

Control what happens when the CR is deleted:

### Retain (default)

```yaml
spec:
  deletionPolicy: "retain"  # API remains in AWS
```

The AWS API continues to exist and handle traffic.

### Delete

```yaml
spec:
  deletionPolicy: "delete"  # API is deleted from AWS
```

The AWS API is deleted. Routes and integrations are destroyed.

## Monitoring and Verification

### Check API Status

```bash
kubectl describe httpapi orders-api -n api-prod
```

Look for:
- `status.resourceName` — The actual API name in AWS
- `status.conditions` — Ready, error, or warning states

### Test a Route

```bash
# Get the default endpoint
API_ID=$(kubectl get httpapi orders-api -n api-prod -o jsonpath='{.status.ackResourceMetadata.arn}' | cut -d: -f6)

# Test the API
curl https://${API_ID}.execute-api.us-east-1.amazonaws.com/orders
```

### View Logs

Enable CloudWatch logging through `ApiGatewayV2Config`:

```bash
aws logs tail /aws/apigateway/orders-api --follow
```

### Check Route Details

```bash
kubectl get routes -n api-prod | grep orders-api
```

## Updating an API

### Add a Route

Edit the CR and add a new route:

```yaml
routes:
  - routeKey: "GET /orders"
    # ...existing route...
  
  - routeKey: "PATCH /orders/{id}"  # New route
    integration:
      type: AWS_PROXY
      integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:patch-order"
```

Apply the change:

```bash
kubectl apply -f api.yaml
```

A new Route and Integration CR are created.

### Remove a Route

Remove the route from the `routes` array and apply:

```bash
kubectl apply -f api.yaml
```

The Route and Integration CRs are deleted.

### Update an Integration

Modify the integration configuration:

```yaml
routes:
  - routeKey: "GET /orders"
    integration:
      type: AWS_PROXY
      integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:list-orders-v2"  # New Lambda
```

Apply the change. The Integration CR is updated.

## Cross-Provider Notes

- HTTP APIs are AWS-specific
- GCP provides Cloud API Gateway and Cloud Run for similar use cases
- Azure offers API Management (APIM) for enterprise API management
- JWT and Lambda authorizers are AWS-specific; other clouds use different authorization mechanisms
- VPC Link connectivity is AWS-specific; GCP and Azure use different private networking

## See Also

- [API Gateway V2](index.md) — Family overview
- [WebSocket APIs](apigatewayv2websocketapi.md) — Real-time bidirectional APIs
- [Stages](apigatewayv2stage.md) — Deploy APIs to stages
- [Custom Domains](apigatewayv2domainname.md) — Use branded URLs
- [VPC Links](apigatewayv2vpclink.md) — Private integrations
- [Governance](apigatewayv2config.md) — Organizational policies
