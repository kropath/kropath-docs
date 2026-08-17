# APIGatewayAuthorizer — Authorization

The `APIGatewayAuthorizer` resource creates and manages REST API authorizers. Authorizers control access to REST APIs using Lambda functions, Cognito User Pools, or other authentication mechanisms.

## Overview

Authorizers validate incoming API requests before they reach backend integrations. Three authorizer types are supported:

- **Lambda TOKEN** — Lambda function evaluates a token (typically from the Authorization header)
- **Lambda REQUEST** — Lambda function evaluates the full request (headers, query params, etc.)
- **Cognito User Pools** — Validate ID tokens against a Cognito User Pool

Authorizers are standalone resources with independent lifecycle — they can be created, updated, or deleted independently of the REST APIs that reference them.

## Quick Start

### Lambda Token Authorizer

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayAuthorizer
metadata:
  name: token-authorizer
  namespace: default
spec:
  configRef: general-policy
  restApiRef: orders-api
  type: TOKEN
  authorizerUri: arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789012:function:authorize/invocations
  identitySource: method.request.header.Authorization
  authorizerResultTtlInSeconds: 300
```

### Cognito User Pools Authorizer

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayAuthorizer
metadata:
  name: cognito-authorizer
  namespace: default
spec:
  configRef: general-policy
  restApiRef: orders-api
  type: COGNITO_USER_POOLS
  providerArns:
    - arn:aws:cognito-idp:us-east-1:123456789012:userpool/us-east-1_abcdef123
```

## Configuration Reference

### Core Properties

```yaml
spec:
  # Governance
  configRef: general-policy           # APIGatewayConfig profile
  deletionPolicy: retain              # retain | delete
  
  # Metadata
  tags: {}                            # AWS tags (K8s labels only; no cloud tags)
  syncedLabels: {}                    # K8s labels
  syncedAnnotations: {}               # K8s annotations
  
  # Required
  restApiRef: orders-api              # Local APIGatewayRestAPI CR name
  type: TOKEN                         # TOKEN | REQUEST | COGNITO_USER_POOLS
  
  # Lambda authorizers only
  authorizerUri: arn:aws:...          # Lambda function invoke URI (TOKEN, REQUEST)
  authorizerCredentials: ""           # IAM role ARN (optional)
  identitySource: method.request.header.Authorization  # Identity extraction (TOKEN, REQUEST)
  identityValidationExpression: ""    # Regex to validate token (TOKEN, REQUEST)
  authorizerResultTtlInSeconds: 300   # Cache TTL in seconds (0-3600; 0=disabled)
  
  # Cognito authorizers only
  providerArns:                       # Cognito User Pool ARNs
    - arn:aws:cognito-idp:...
```

### Authorizer Types

**Lambda TOKEN Authorizer:**
- Validates a token extracted from the request (typically the Authorization header)
- Lambda receives the token as input
- Good for traditional bearer token or API key patterns
- Required fields: `authorizerUri`, `identitySource`
- Optional: `identityValidationExpression` (regex to pre-validate token format)

**Lambda REQUEST Authorizer:**
- Validates the full HTTP request (headers, query parameters, body, context)
- Lambda receives the entire request context
- Good for complex authorization logic
- Required fields: `authorizerUri`, `identitySource`

**Cognito User Pools:**
- Validates ID tokens against AWS Cognito User Pools
- Users authenticate with Cognito and receive an ID token
- Methods require a valid Cognito ID token in the Authorization header
- Required fields: `providerArns` (list of User Pool ARNs)

### Default Values

| Field | Default | Behavior |
|---|---|---|
| `configRef` | `general-policy` | Fall through to default profile |
| `authorizerResultTtlInSeconds` | `300` | Results cached for 5 minutes (0 to disable) |
| `authorizerCredentials` | `""` | Use resource-based permissions on Lambda (recommended) |
| `identityValidationExpression` | `""` | No pre-validation of token format |

### Status Outputs

```yaml
status:
  authorizerId: a1b2c3d4e5          # AWS-assigned authorizer ID
  conditions:
    - type: Ready
      status: "True"
      reason: ReconciliationSucceeded
```

## Common Patterns

### JWT Token Authorization (Lambda TOKEN)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayAuthorizer
metadata:
  name: jwt-authorizer
  namespace: default
spec:
  configRef: general-policy
  restApiRef: orders-api
  type: TOKEN
  authorizerUri: arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789012:function:verify-jwt/invocations
  identitySource: method.request.header.Authorization
  identityValidationExpression: "^[Bb][Ee][Aa][Rr][Ee][Rr] [-0-9a-zA-z\\._]*$"
  authorizerResultTtlInSeconds: 3600  # Cache for 1 hour
```

### Request-Based Authorization (Lambda REQUEST)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayAuthorizer
metadata:
  name: request-authorizer
  namespace: default
spec:
  configRef: general-policy
  restApiRef: orders-api
  type: REQUEST
  authorizerUri: arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789012:function:authorize-request/invocations
  identitySource: method.request.header.X-Custom-Auth
  authorizerResultTtlInSeconds: 300
```

### Cognito with Multiple User Pools

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayAuthorizer
metadata:
  name: cognito-multi
  namespace: default
spec:
  configRef: general-policy
  restApiRef: orders-api
  type: COGNITO_USER_POOLS
  providerArns:
    - arn:aws:cognito-idp:us-east-1:123456789012:userpool/us-east-1_abc123def
    - arn:aws:cognito-idp:us-east-1:123456789012:userpool/us-east-1_xyz789uvw
```

## Using Authorizers in APIs

Reference an authorizer in your REST API methods:

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
          authorizationType: CUSTOM
          authorizerRef: jwt-authorizer  # References the APIGatewayAuthorizer
          integration:
            type: AWS_PROXY
            uri: arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/...
```

When a method uses an authorizer, the authorizer's logic is invoked before the backend integration is called.

## Lambda Authorizer Function Requirements

Lambda authorizer functions must accept a structured input and return an authorization policy response.

### TOKEN Authorizer Input

```json
{
  "type": "TOKEN",
  "authorizationToken": "incoming-client-token",
  "methodArn": "arn:aws:execute-api:us-east-1:123456789012:a1b2c3d4e5/prod/GET/orders"
}
```

### REQUEST Authorizer Input

```json
{
  "type": "REQUEST",
  "methodArn": "arn:aws:execute-api:us-east-1:123456789012:a1b2c3d4e5/prod/GET/orders",
  "resource": "/orders",
  "path": "/orders",
  "httpMethod": "GET",
  "headers": {
    "Authorization": "Bearer token123",
    "Content-Type": "application/json"
  },
  "queryStringParameters": {
    "page": "1"
  },
  "requestContext": {
    "accountId": "123456789012",
    "apiId": "a1b2c3d4e5",
    "protocol": "HTTP/1.1",
    "httpMethod": "GET",
    "path": "/orders",
    "stage": "prod",
    "sourceIp": "192.0.2.1"
  }
}
```

### Authorization Response

Both authorizer types must return:

```json
{
  "principalId": "user-id",
  "policyDocument": {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": "execute-api:Invoke",
        "Effect": "Allow",
        "Resource": "arn:aws:execute-api:us-east-1:123456789012:a1b2c3d4e5/*"
      }
    ]
  },
  "context": {
    "userId": "user-123",
    "email": "user@example.com"
  }
}
```

The context values are passed to the backend integration via `$context.authorizer.xxx`.

## Caching

Lambda authorizer results can be cached to reduce invocations and improve performance:

- **TTL:** Set `authorizerResultTtlInSeconds` (0 = disable, max 3600)
- **Cache key:** Derived from the authorizer type and identity source
- **Invalidation:** Cache is invalidated when the authorizer code changes or credentials rotate

```yaml
spec:
  authorizerResultTtlInSeconds: 3600  # Cache for 1 hour
```

Higher TTL reduces Lambda invocations but may delay authorization updates. For sensitive use cases, use lower TTL or disable caching (0).

## Deletion Policy

- **retain** (default) — Keep the authorizer in AWS when the Kubernetes CR is deleted
- **delete** — Delete both the Kubernetes CR and the AWS authorizer

```yaml
spec:
  deletionPolicy: delete  # Delete authorizer when CR is deleted
```

## Monitoring

### Check Authorizer Status

```bash
kubectl describe authorizer jwt-authorizer -n default
```

Look for:
- `status.authorizerId` — The AWS authorizer ID
- `status.conditions` — Reconciliation status

### Test Authorizer Behavior

Use AWS CLI to test the authorizer:

```bash
aws apigateway test-invoke-authorizer \
  --rest-api-id a1b2c3d4e5 \
  --authorizer-id abc123def456 \
  --authorization-token "Bearer token123"
```

## Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| Authorizer invocation fails | Lambda not found or wrong URI | Verify Lambda ARN is correct; check Lambda permissions |
| 403 Forbidden from API | Authorizer denies request | Check Lambda authorizer policy response; verify tokens are valid |
| Slow API responses | Authorizer caching disabled | Increase `authorizerResultTtlInSeconds` if appropriate |
| Authorizer cache hits wrong token | Cache key too broad | Adjust `identitySource` to be more specific |

## Cross-Provider Notes

- `APIGatewayAuthorizer` is AWS-specific
- GCP and Azure use different authorization models (IAM bindings, OAuth policies)
- Lambda authorizer pattern is unique to AWS API Gateway

## See Also

- [API Gateway — Family Overview](index.md)
- [REST APIs](apigatewayrestapi.md) — Create and manage APIs
- [Governance Configuration](apigatewayconfig.md) — Profile settings
- [AWS API Gateway Authorizers — Developer Guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-use-lambda-authorizer.html)
- [AWS Cognito User Pools](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pools.html)
