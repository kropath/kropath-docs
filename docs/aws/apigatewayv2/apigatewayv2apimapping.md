# ApiGatewayV2ApiMapping — Domain Path Routing

The `ApiGatewayV2ApiMapping` resource connects custom domain names to API stages, optionally under a base path prefix. Multiple API mappings can share one domain, each routing a different path to a different API or stage.

## Overview

Use `ApiGatewayV2ApiMapping` to:

- **Route paths to APIs** — Direct domain paths to different APIs via `apiMappingKey`
- **Multi-API domains** — Host multiple APIs under one custom domain
- **Stage selection** — Route to specific stages (dev, staging, prod)
- **API versioning** — Use path prefixes for API versioning (`/v1`, `/v2`)

Mappings enable cost-efficient sharing of custom domains across multiple APIs and teams.

## Creating an API Mapping

### Simple Root Mapping

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2ApiMapping
metadata:
  name: orders-root-mapping
  namespace: api-prod
spec:
  apiRef: orders-api
  domainRef: api-domain
  stage: prod
  apiMappingKey: ""  # Empty = root path
```

This mapping:
- Routes `https://api.example.com/*` to `orders-api` prod stage
- Empty `apiMappingKey` means the API is at the root

### Path-Based Mapping

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2ApiMapping
metadata:
  name: orders-v1-mapping
  namespace: api-prod
spec:
  apiRef: orders-api
  domainRef: api-domain
  stage: prod
  apiMappingKey: "v1"  # Routes /v1/* to orders-api
```

This mapping routes `https://api.example.com/v1/*` to the orders API.

### Multi-API Domain

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2ApiMapping
metadata:
  name: orders-mapping
  namespace: api-prod
spec:
  apiRef: orders-api
  domainRef: api-domain
  stage: prod
  apiMappingKey: "orders"
---
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2ApiMapping
metadata:
  name: users-mapping
  namespace: api-prod
spec:
  apiRef: users-api
  domainRef: api-domain
  stage: prod
  apiMappingKey: "users"
---
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2ApiMapping
metadata:
  name: products-mapping
  namespace: api-prod
spec:
  apiRef: products-api
  domainRef: api-domain
  stage: prod
  apiMappingKey: "products"
```

Now a single domain serves multiple APIs:
- `https://api.example.com/orders/` → orders-api
- `https://api.example.com/users/` → users-api
- `https://api.example.com/products/` → products-api

### Version-Based Routing

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2ApiMapping
metadata:
  name: orders-v1-mapping
  namespace: api-prod
spec:
  apiRef: orders-api-v1
  domainRef: api-domain
  stage: prod
  apiMappingKey: "v1"
---
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2ApiMapping
metadata:
  name: orders-v2-mapping
  namespace: api-prod
spec:
  apiRef: orders-api-v2
  domainRef: api-domain
  stage: prod
  apiMappingKey: "v2"
```

Routes requests by API version:
- `https://api.example.com/v1/orders/` → orders-api-v1
- `https://api.example.com/v2/orders/` → orders-api-v2

### Stage-Based Routing

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2ApiMapping
metadata:
  name: orders-dev-mapping
  namespace: api-prod
spec:
  apiRef: orders-api
  domainRef: api-domain
  stage: dev
---
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2ApiMapping
metadata:
  name: orders-prod-mapping
  namespace: api-prod
spec:
  apiRef: orders-api
  domainRef: api-domain
  stage: prod
  apiMappingKey: ""  # Root = prod
```

Routes `/dev` to dev stage, `/` to prod stage.

## Configuration

### API Reference

**`apiRef`** — Local API CR name (HTTP or WebSocket)

- Type: string
- Required
- Must reference an existing `ApiGatewayV2HttpApi` or `ApiGatewayV2WebSocketApi` CR

```yaml
spec:
  apiRef: orders-api  # Must exist in same namespace
```

### Domain Reference

**`domainRef`** — Local custom domain CR name

- Type: string
- Required
- Must reference an existing `ApiGatewayV2DomainName` CR

```yaml
spec:
  domainRef: api-domain  # Must exist in same namespace
```

### Stage

**`stage`** — Stage name within the API

- Type: string
- Required
- Immutable (cannot be changed)
- Common values: `"dev"`, `"staging"`, `"prod"`, `"$default"`

```yaml
spec:
  stage: prod
```

### API Mapping Key

**`apiMappingKey`** — Base path prefix (optional)

- Type: string
- Default: `""` (empty = root path)
- Immutable (cannot be changed)
- Alphanumeric, hyphens, and underscores only
- Max 128 characters

```yaml
spec:
  apiMappingKey: "v1"  # Routes /v1/* to the API
```

Empty string routes to the domain root:

```yaml
spec:
  apiMappingKey: ""  # Routes /* to the API (must be only one mapping with empty key per domain)
```

## Tags and Labels

Add organization metadata:

```yaml
spec:
  tags:
    team: api-platform
  syncedLabels:
    app: microservices
  syncedAnnotations:
    managed-by: "kropath"
```

Note: `ApiGatewayV2ApiMapping` does not support cloud tags on the AWS side (G-7), but Kubernetes labels and annotations are still applied.

## Deletion Policy

### Retain (default)

```yaml
spec:
  deletionPolicy: "retain"
```

The mapping remains in API Gateway.

### Delete

```yaml
spec:
  deletionPolicy: "delete"
```

The mapping is deleted when the CR is deleted.

## Monitoring and Verification

### Check Mapping Status

```bash
kubectl describe apimapping orders-v1-mapping -n api-prod
```

Look for:
- `status.conditions` — Ready, error, or warning states
- `spec.apiRef` — Connected API
- `spec.domainRef` — Connected domain
- `spec.stage` — Target stage

### Test the Mapping

```bash
# Test root mapping
curl https://api.example.com/orders

# Test path-based mapping
curl https://api.example.com/v1/orders

# Test specific path
curl https://api.example.com/v1/orders/123
```

### List All Mappings for a Domain

```bash
kubectl get apimapping -n api-prod \
  -o custom-columns=NAME:.metadata.name,API:.spec.apiRef,STAGE:.spec.stage,KEY:.spec.apiMappingKey
```

## Updating a Mapping

### Change Target Stage

**Note:** Stage cannot be changed directly. Instead:

1. Create a new mapping with the new stage
2. Test the new mapping
3. Delete the old mapping

```yaml
# Old mapping (delete this)
spec:
  apiRef: orders-api
  domainRef: api-domain
  stage: dev
  apiMappingKey: "orders"

# New mapping (apply this)
spec:
  apiRef: orders-api
  domainRef: api-domain
  stage: prod  # Changed
  apiMappingKey: "orders"
```

### Change Target API

**Note:** API reference cannot be changed. Create a new mapping and delete the old one.

## Best Practices

1. **Plan mapping structure** — Decide between path-based, API-based, or version-based routing before creating mappings.
2. **Use consistent naming** — Use clear `apiMappingKey` values that reflect the content (`v1`, `orders`, `users`).
3. **One root mapping per domain** — Only one mapping can use an empty `apiMappingKey` per domain.
4. **Stage separation** — Keep dev and prod mappings separate for safety.
5. **Document routing** — Maintain a README documenting which paths route to which APIs.
6. **Version compatibility** — If supporting multiple API versions, ensure backward compatibility before deprecating old versions.
7. **Monitor traffic** — Use CloudWatch logs to see which mappings receive traffic.

## Routing Examples

### Single API at Root

```yaml
spec:
  apiRef: api
  domainRef: domain
  stage: prod
  apiMappingKey: ""
```

- `https://domain.com/` → api
- `https://domain.com/orders` → api
- `https://domain.com/users/123` → api

### Multiple APIs with Path Prefixes

```yaml
# Mapping 1
spec:
  apiRef: orders-api
  stage: prod
  apiMappingKey: "orders"

# Mapping 2
spec:
  apiRef: users-api
  stage: prod
  apiMappingKey: "users"
```

- `https://domain.com/orders/list` → orders-api
- `https://domain.com/users/profile` → users-api
- `https://domain.com/invalid` → **404 Not Found**

### API Versioning

```yaml
# v1 at /v1
spec:
  apiRef: api-v1
  stage: prod
  apiMappingKey: "v1"

# v2 at root (newer default)
spec:
  apiRef: api-v2
  stage: prod
  apiMappingKey: ""
```

- `https://domain.com/v1/orders` → api-v1 (legacy)
- `https://domain.com/orders` → api-v2 (current)

## Limitations

- Max one mapping with empty `apiMappingKey` per domain
- Stage and API reference are immutable after creation
- Max 128-character mapping key
- All paths under a mapping key route to the same API stage

## Cross-Provider Notes

- API Gateway V2 path mapping is AWS-specific
- GCP Cloud API Gateway uses OpenAPI spec for routing
- Azure API Management uses custom domain backend pools for multi-API routing
- Path-based routing mechanism differs significantly across cloud providers

## See Also

- [API Gateway V2](index.md) — Family overview
- [Custom Domains](apigatewayv2domainname.md) — Create custom domain names
- [HTTP APIs](apigatewayv2httpapi.md) — Create HTTP APIs
- [WebSocket APIs](apigatewayv2websocketapi.md) — Create WebSocket APIs
- [Stages](apigatewayv2stage.md) — Configure deployment stages
