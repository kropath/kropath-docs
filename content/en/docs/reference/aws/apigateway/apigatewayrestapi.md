---
title: APIGatewayRestAPI — REST APIs
description: "The `APIGatewayRestAPI` resource creates and manages AWS REST APIs with resources, methods, integrations, and policies."
doc_type: reference
---
# APIGatewayRestAPI — REST APIs

The `APIGatewayRestAPI` resource creates and manages AWS REST APIs with resources, methods, integrations, and policies. This is a **composite** resource that manages an API Gateway REST API together with all its resources, methods, and integration mappings.

## Overview

A complete REST API typically requires multiple AWS resources working together:

- **REST API** — The top-level API container
- **Resources** — Path segments (e.g. `/orders`, `/{id}`)
- **Methods** — HTTP verbs (GET, POST, PUT, DELETE, etc.)
- **Integrations** — Backend connections (Lambda, HTTP, AWS services, VPC links, mocks)
- **Response Mappings** — Transform requests and responses

The `APIGatewayRestAPI` resource composes all of these into one Kubernetes CR, so you define your entire API structure in one place and let kropath handle the wiring.

## Quick Start

### Simple Lambda Proxy API

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayRestAPI
metadata:
  name: hello-api
  namespace: default
spec:
  configRef: general-policy
  description: Hello world API
  resources:
    - pathPart: hello
      methods:
        - httpMethod: GET
          integration:
            type: AWS_PROXY
            uri: arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789012:function:hello/invocations
```

### Multi-Method API with Multiple Resources

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayRestAPI
metadata:
  name: orders-api
  namespace: api-prod
spec:
  configRef: prod
  description: Order management API
  resources:
    - pathPart: orders
      methods:
        - httpMethod: GET
          integration:
            type: HTTP_PROXY
            uri: https://backend.example.com/orders
        - httpMethod: POST
          integration:
            type: AWS_PROXY
            uri: arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789012:function:create-order/invocations
    - pathPart: "{id}"
      parentPath: orders
      methods:
        - httpMethod: GET
          integration:
            type: HTTP_PROXY
            uri: https://backend.example.com/orders/{id}
```

## Core Concepts

### Composite Resource Design

`APIGatewayRestAPI` is a **composite** resource that maps one Kubernetes CR to multiple AWS resources. This means you define the entire API structure in one place, and kropath automatically creates all the child AWS resources. You don't manually create Resource, Method, or Integration CRs—they're all generated from the APIGatewayRestAPI spec.

### Resource Hierarchy

Resources are organized hierarchically using path segments:

- **Root resource** — The root of the API path tree
- **Child resources** — Nested paths (e.g. `/orders/{id}`)
- **Path parameters** — Dynamic segments in curly braces (e.g. `{id}`)

```yaml
resources:
  - pathPart: orders         # /orders
    methods:
      - httpMethod: GET
  - pathPart: "{id}"         # /orders/{id}
    parentPath: orders       # Parent segment
    methods:
      - httpMethod: GET
      - httpMethod: DELETE
```

The `parentPath` field specifies the parent path segment. For the root level (e.g. `/orders`), leave `parentPath` empty.

### Integration Types

REST APIs support multiple backend integration types:

| Type | Use Case | Example |
|---|---|---|
| `HTTP` | HTTP endpoints with transformation | REST APIs, microservices |
| `HTTP_PROXY` | Pass-through to HTTP backends | Simple proxying to external services |
| `AWS_PROXY` | Lambda function proxy integration | Serverless backends |
| `AWS` | AWS service integration with transformation | AWS services like Kinesis, SQS |
| `MOCK` | Mock responses without backend | Testing, documentation, templates |
| `VPC_LINK` | Private backends via NLB | VPC-internal services |

### Naming and Identity

REST APIs use a naming template to generate their AWS name:

```yaml
spec:
  # No nameOverride set; uses configRef profile template
  # With profile template "{namespace}-{name}" and namespace api-prod:
  # Resulting name: api-prod-orders-api
  
  nameOverride: custom-orders-api  # Override the template
```

The effective name is computed at reconciliation time and exposed in `status.resourceName`.

## Configuration Reference

### API Properties

```yaml
spec:
  # Governance
  configRef: general-policy     # Reference to APIGatewayConfig profile
  nameOverride: ""              # Override naming template (optional)
  deletionPolicy: retain        # retain | delete
  
  # API metadata
  description: "My API"         # API description
  tags: {}                       # AWS tags
  syncedLabels: {}              # K8s labels that sync to AWS
  syncedAnnotations: {}         # K8s annotations
  
  # API Gateway configuration
  apiKeySource: HEADER          # HEADER | AUTHORIZER
  endpointType: REGIONAL        # REGIONAL | EDGE | PRIVATE
  vpcEndpointIds: []            # VPC endpoints (PRIVATE only)
  minimumCompressionSize: 0     # 0=disabled; 0-10485760 bytes
  disableExecuteApiEndpoint: false
  
  # Access policies
  policy: ""                    # Inline JSON resource policy (mutually exclusive with resourcePolicyRef)
  resourcePolicyRef: ""         # PolicyDocument CR name (mutually exclusive with policy)
  
  # Binary media types
  binaryMediaTypes:
    - application/octet-stream
    - image/png
    - image/jpeg
  
  # Resources, methods, and integrations
  resources: [...]              # See below
```

### Resource Schema

```yaml
resources:
  - pathPart: orders            # Path segment (required)
    parentPath: ""              # Parent segment (empty = root level)
    methods:
      - httpMethod: GET         # HTTP method (required)
        authorizationType: NONE  # NONE | AWS_IAM | CUSTOM | COGNITO_USER_POOLS
        authorizerRef: ""        # Local APIGatewayAuthorizer CR name
        apiKeyRequired: false
        operationName: ""        # Operation name for documentation
        requestParameters:       # method.request.{location}.{name}
          method.request.header.Authorization: true
          method.request.querystring.page: false
        requestModels:           # Content-type → Model name
          application/json: OrderRequest
        
        integration:
          type: AWS_PROXY        # HTTP | HTTP_PROXY | AWS | AWS_PROXY | MOCK
          uri: arn:aws:apigateway:us-east-1:lambda:path/...  # Backend URI
          integrationHttpMethod: POST   # HTTP method for backend
          credentials: ""        # IAM role ARN (optional)
          connectionType: INTERNET   # INTERNET | VPC_LINK
          connectionRef: ""      # APIGatewayVPCLink CR name (VPC_LINK only)
          passthroughBehavior: WHEN_NO_MATCH  # WHEN_NO_MATCH | WHEN_NO_TEMPLATES | NEVER
          
          requestParameters: {}  # integration.request.{location}.{name}
          requestTemplates:      # Content-type → Velocity template
            application/json: |
              { "id": "$input.params('id')" }
          
          contentHandling: ""    # CONVERT_TO_BINARY | CONVERT_TO_TEXT | ""
          timeoutInMillis: 29000 # 50-29000 ms
          tlsInsecureSkipVerify: false
          
          cacheKeyParameters: [] # Request parameters to cache
          cacheNamespace: ""     # Cache grouping
          
          responses:
            - statusCode: 200
              selectionPattern: ""      # Regex match (empty = default response)
              contentHandling: ""
              responseParameters:       # method.response.header.{name}
                method.response.header.Content-Type: integration.response.header.Content-Type
              responseTemplates:
                application/json: $input.json('$')
        
        methodResponses:
          - statusCode: 200
            responseModels:
              application/json: OrderResponse
            responseParameters:
              method.response.header.Content-Type: true
          - statusCode: 400
            responseModels:
              application/json: ErrorResponse
```

### Default Values and Zero-Value Behavior

| Field | Default | Zero-Value Behavior |
|---|---|---|
| `configRef` | `general-policy` | Falls through to default profile |
| `nameOverride` | `""` | Use naming template from profile |
| `deletionPolicy` | `"retain"` | Keep AWS resources when CR is deleted |
| `apiKeySource` | `"HEADER"` | API key in HTTP header |
| `endpointType` | `""` | Use profile default |
| `minimumCompressionSize` | `0` | Compression disabled |
| `disableExecuteApiEndpoint` | `false` | Default endpoint enabled |
| `authorizationType` | `"NONE"` | No authorization required |
| `integration.type` | (required) | Must specify |
| `integration.credentials` | `""` | Use resource-based permissions |
| `integration.connectionType` | `"INTERNET"` | Public internet connection |
| `integration.timeoutInMillis` | `29000` | 29-second timeout (max allowed) |

### Status Outputs

The REST API status exposes:

```yaml
status:
  resourceName: api-prod-orders-api    # Effective cloud name
  namingStatus: valid                  # valid | invalid-unresolved-tokens
  predictedArn: arn:aws:apigateway:us-east-1::...  # Note: restApiId is system-assigned
  restApiId: a1b2c3d4e5               # System-assigned REST API ID
  rootResourceId: r1s2t3u4v5           # Root resource ID (for top-level methods)
  conditions:                          # Standard kro reconciliation conditions
    - type: Ready
      status: "True"
      reason: ReconciliationSucceeded
```

## Common Patterns

### Lambda Proxy with Error Handling

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayRestAPI
metadata:
  name: backend-api
  namespace: default
spec:
  configRef: general-policy
  resources:
    - pathPart: api
      methods:
        - httpMethod: POST
          integration:
            type: AWS_PROXY
            uri: arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789012:function:handler/invocations
            responses:
              - statusCode: 200
              - statusCode: 400
              - statusCode: 500
```

### HTTP Proxy with Request Transformation

```yaml
resources:
  - pathPart: external
    methods:
      - httpMethod: GET
        integration:
          type: HTTP_PROXY
          uri: https://api.example.com/v1
          requestParameters:
            integration.request.header.X-API-Key: method.request.header.Authorization
          requestTemplates:
            application/json: |
              { 
                "userId": "$input.params('user_id')",
                "action": "$context.httpMethod"
              }
```

### VPC Link Integration

```yaml
resources:
  - pathPart: internal
    methods:
      - httpMethod: POST
        integration:
          type: HTTP_PROXY
          uri: http://internal-nlb-123.us-east-1.elb.amazonaws.com:8080/api
          connectionType: VPC_LINK
          connectionRef: internal-link  # References APIGatewayVPCLink CR
```

### Mock Integration (Testing)

```yaml
resources:
  - pathPart: mock
    methods:
      - httpMethod: GET
        integration:
          type: MOCK
          responses:
            - statusCode: 200
              responseTemplates:
                application/json: |
                  {
                    "message": "Hello from mock API"
                  }
```

## Authorizers

Methods can use authorizers to control access. Authorizers are created separately as `APIGatewayAuthorizer` resources and referenced by name:

```yaml
resources:
  - pathPart: admin
    methods:
      - httpMethod: GET
        authorizationType: CUSTOM
        authorizerRef: my-authorizer  # References APIGatewayAuthorizer CR
        integration:
          type: AWS_PROXY
          uri: arn:aws:apigateway:...
```

See [Authorizers](apigatewayauthorizer.md) for complete authorizer documentation.

## Resource Policies

APIs can enforce access policies at the API level:

**Inline policy:**
```yaml
spec:
  policy: |
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": "*",
          "Action": "execute-api:Invoke",
          "Resource": "arn:aws:execute-api:*:*:*"
        }
      ]
    }
```

**Reference a PolicyDocument CR** (recommended for reusability):
```yaml
spec:
  resourcePolicyRef: api-policy  # References a PolicyDocument CR
```

Policy and resourcePolicyRef are mutually exclusive—set one or neither, not both.

## Deletion Policy

Control what happens when the API is deleted:

- **retain** (default) — Keep the REST API in AWS; delete only the Kubernetes CR
- **delete** — Delete both the Kubernetes CR and all AWS resources (REST API, resources, methods, integrations)

```yaml
spec:
  deletionPolicy: delete  # Delete AWS resources when CR is deleted
```

Use `retain` for production APIs to prevent accidental deletion. Use `delete` for temporary test APIs.

## Monitoring

### Check API Status

```bash
kubectl describe restapi orders-api -n api-prod
```

Look for:
- `status.restApiId` — The AWS REST API ID
- `status.resourceName` — The effective cloud name
- `status.namingStatus` — Whether naming is valid
- `status.conditions` — Reconciliation status

### View the Effective Configuration

After deployment, the controller computes the effective configuration including governance cascade:

```bash
kubectl get restapi orders-api -n api-prod -o jsonpath='{.status}' | jq
```

### List All APIs

```bash
kubectl get restapi -A
```

## Limitations and Known Behaviors

- **Resource limit:** A single APIGatewayRestAPI can compose up to 1000 resources (configurable per deployment)
- **Response mapping:** All method responses and integration responses must be explicitly defined
- **Naming:** The REST API ID is system-assigned by AWS and not fully predictable; `status.predictedArn` shows the most accurate prediction but actual ARN may differ until creation
- **Tags:** Tags on RestAPI resources are applied via the APIGatewayConfig profile; instances can add custom tags which merge with profile defaults

## Cross-Provider Notes

- `APIGatewayRestAPI` is AWS-specific (REST API v1)
- GCP and Azure have different API management models
- HTTP APIs (API Gateway v2) are documented separately in the [APIGatewayV2](../apigatewayv2/index.md) family

## See Also

- [API Gateway — Family Overview](index.md)
- [Governance Configuration](apigatewayconfig.md) — Profile configuration
- [Authorizers](apigatewayauthorizer.md) — Authorization strategies
- [Deployments](apigatewaydeployment.md) — Deploy to stages
- [VPC Links](apigatewayvpclink.md) — Private integrations
- [AWS API Gateway — Developer Guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/)
