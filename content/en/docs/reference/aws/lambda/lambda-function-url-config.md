---
title: LambdaFunctionURLConfig — HTTPS Endpoints for Lambda Functions
description: "The `LambdaFunctionURLConfig` resource creates dedicated HTTPS endpoints for Lambda functions."
doc_type: reference
---
# LambdaFunctionURLConfig — HTTPS Endpoints for Lambda Functions

The `LambdaFunctionURLConfig` resource creates dedicated HTTPS endpoints for Lambda functions. This is simpler than ALB/API Gateway for serverless functions that need direct HTTP/HTTPS invocation without complex routing.

## Overview

Function URLs provide:
- **Dedicated HTTPS endpoint** — Stable URL that invokes the function
- **Built-in authentication** — AWS_IAM or no auth
- **CORS support** — Cross-origin requests with configurable headers
- **Qualifier support** — URLs can point to specific aliases or versions
- **No API Gateway overhead** — Direct Lambda invocation via HTTP

A function URL looks like: `https://abcdefghijklmnopqrstuvwxyz123456.lambda-url.us-east-1.on.aws/`

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `LambdaConfig` governance profile to apply (for tags/labels only) |
| `deletionPolicy` | string | `"retain"` | Behavior on resource deletion: `"retain"` (keep AWS URL) or `"delete"` (remove URL) |

### Target Function

| Field | Type | Default | Purpose |
|---|---|---|---|
| `functionRef` | string | required | Local `LambdaFunction` CR name; resolved to function ARN |
| `qualifier` | string | `""` | Optional alias or version number; empty = `$LATEST` |

The URL invokes the specified function or alias:
- No qualifier → invokes `$LATEST`
- Qualifier = `"prod"` → invokes the `prod` alias
- Qualifier = `"5"` → invokes version 5

### Authentication

| Field | Type | Default | Purpose |
|---|---|---|---|
| `authType` | string | `"AWS_IAM"` | `AWS_IAM` (identity-based access control) or `NONE` (public, unauthenticated) |

**Security note:**
- `AWS_IAM` — Callers must have `lambda:InvokeFunctionUrl` permission
- `NONE` — Anyone with the URL can invoke; suitable for public webhooks

### CORS Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `cors.allowCredentials` | boolean | `false` | Allow credentials (Authorization header) from cross-origin requests |
| `cors.allowHeaders` | array | `[]` | Allowed HTTP headers in preflight requests |
| `cors.allowMethods` | array | `[]` | Allowed HTTP methods (GET, POST, PUT, DELETE, PATCH, etc.) |
| `cors.allowOrigins` | array | `[]` | Allowed origins (e.g., `https://example.com`, `https://*.example.com`) |
| `cors.exposeHeaders` | array | `[]` | Headers exposed to the browser in responses |
| `cors.maxAge` | integer | `0` | Preflight cache lifetime in seconds |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels (prefixed `aws.kropath.run/`; **function URLs do NOT sync to cloud tags**) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

**Important:** Function URLs do NOT support cloud tags (AWS doesn't tag URLs). `syncedLabels` and `syncedAnnotations` only apply to Kubernetes.

## Status Outputs

After reconciliation:

| Field | Type | Purpose |
|---|---|---|
| `functionUrl` | string | The HTTPS endpoint URL (e.g., `https://abcdef123456.lambda-url.us-east-1.on.aws/`) |
| `conditions[]` | array | Standard Kubernetes conditions tracking reconciliation progress |

## Naming Convention

**Function URLs do not have user-defined names.** AWS auto-generates a unique URL. The Kubernetes resource name is purely for organization within Kubernetes. The actual URL is determined by AWS and returned in `status.functionUrl`.

## Complete Examples

### Simple Public Webhook

Create a public webhook endpoint with no authentication:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunctionURLConfig
metadata:
  name: webhook-endpoint
  namespace: integrations
spec:
  configRef: general-policy
  functionRef: webhook-handler
  authType: NONE  # Public access
  deletionPolicy: retain
```

Result:
- Function URL created and available immediately
- Anyone with the URL can invoke the function
- Typical use case: webhook receivers, public APIs

### Authenticated API Endpoint with CORS

Create a private API endpoint with IAM authentication and CORS headers:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunctionURLConfig
metadata:
  name: api-endpoint
  namespace: services
spec:
  configRef: general-policy
  functionRef: api-handler
  authType: AWS_IAM  # Identity-based access control
  cors:
    allowOrigins:
      - "https://app.example.com"
      - "https://admin.example.com"
    allowMethods:
      - GET
      - POST
      - PUT
      - DELETE
    allowHeaders:
      - "Content-Type"
      - "Authorization"
      - "X-Custom-Header"
    exposeHeaders:
      - "X-Total-Count"
      - "X-Page-Number"
    maxAge: 3600
    allowCredentials: true
  deletionPolicy: retain
```

Result:
- Function URL secured with AWS IAM
- CORS headers allow cross-origin requests from specified domains
- Credentials (Authorization header) allowed
- Preflight requests cached for 1 hour

### Alias-Specific Endpoint

Create a URL pointing to a production alias for stable routing:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunctionURLConfig
metadata:
  name: prod-api
  namespace: services
spec:
  configRef: general-policy
  functionRef: api-service
  qualifier: "prod"  # Points to prod alias, not $LATEST
  authType: AWS_IAM
  cors:
    allowOrigins:
      - "https://api.example.com"
    allowMethods:
      - GET
      - POST
    maxAge: 300
  deletionPolicy: retain
```

Result:
- URL invokes the `prod` alias
- If the alias is updated to point to a new version, this URL immediately uses the new version
- Stable endpoint for production traffic

### Version-Specific Endpoint for Testing

Create a URL pointing to a specific version for canary testing:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunctionURLConfig
metadata:
  name: canary-test
  namespace: services
spec:
  configRef: general-policy
  functionRef: api-service
  qualifier: "42"  # Points to version 42
  authType: NONE  # Open to testing
  deletionPolicy: delete  # Clean up when resource deleted
```

Result:
- URL invokes exactly version 42
- Allows testing a specific version without affecting production
- Endpoint deleted when resource is deleted

### Internal Service Endpoint

Create an endpoint for internal service-to-service communication:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunctionURLConfig
metadata:
  name: internal-processor
  namespace: services
spec:
  configRef: general-policy
  functionRef: internal-handler
  authType: AWS_IAM
  cors:
    allowOrigins:
      - "https://*.internal.example.com"
    allowMethods:
      - POST
  deletionPolicy: retain
```

Result:
- Only services with IAM credentials can invoke
- Allows any subdomain under `*.internal.example.com`
- Typical for microservice communication

## CORS Behavior

CORS is handled automatically by Lambda:

1. **Preflight requests** (OPTIONS) return CORS headers if the origin is in `allowOrigins`
2. **Actual requests** (GET, POST, etc.) are checked against `allowMethods`
3. **Credentials** (Authorization header) included only if `allowCredentials: true`
4. **Response headers** listed in `exposeHeaders` are sent to the browser

If CORS is not configured, cross-origin requests will be blocked by the browser.

## Governance

Function URL configs inherit tags, syncedLabels, and syncedAnnotations from the `LambdaConfig` governance profile via `configRef`.

**Important:** AWS Lambda function URLs do NOT support cloud tags. Only Kubernetes labels and annotations are applied.

## Key Behaviors

### URL is Stable

Once created, the function URL never changes. If you update the qualifier or delete the config and recreate it, you get a new URL.

### Qualifier Immutable

The `qualifier` field cannot be changed after creation. To switch to a different alias or version, delete and recreate the URL config.

### Function Must Exist

The referenced `LambdaFunction` CR must exist. If a qualifier is specified, it must be a valid alias or published version.

### IAM Permissions

For `authType: AWS_IAM`, callers need:
- `lambda:InvokeFunctionUrl` permission
- Policy to invoke the specific function ARN

For `authType: NONE`, anyone with the URL can invoke.

## Troubleshooting

### URL Not Generated

Verify the `functionRef` resolves to a valid function and the function exists.

### CORS Preflight Failing

Check that:
- The origin is in `allowOrigins` (exact match or wildcard)
- The method is in `allowMethods`
- Headers are in `allowHeaders`

### "User: arn:aws:iam::... is not authorized"

For `authType: AWS_IAM`, ensure the caller's IAM role has `lambda:InvokeFunctionUrl` permission.

### Stale URL After Qualifier Update

Function URLs are immutable. To use a new alias, delete the old URL config and create a new one.

## Reference

- **Design:** See `kropath-core/docs/families/aws/lambda.md` for function URL design
- **AWS Lambda documentation:** https://docs.aws.amazon.com/lambda/latest/dg/lambda-urls.html
