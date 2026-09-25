---
title: APIGatewayAPIKey — API Keys
description: "The `APIGatewayAPIKey` resource creates and manages API keys for REST APIs."
doc_type: reference
---
# APIGatewayAPIKey — API Keys

The `APIGatewayAPIKey` resource creates and manages API keys for REST APIs. API keys are used for access control and can be associated with usage plans to meter and throttle API consumers.

## Overview

API keys are unique identifiers used to authenticate API consumers. They're typically passed in the `x-api-key` HTTP header (when `apiKeySource: HEADER` is set on the REST API).

API keys are standalone resources with independent lifecycle — they can be created, updated, or deleted independently of REST APIs.

## Quick Start

### Basic API Key

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayAPIKey
metadata:
  name: mobile-app-key
  namespace: default
spec:
  configRef: general-policy
  description: API key for mobile app
  enabled: true
```

### Disabled API Key

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayAPIKey
metadata:
  name: legacy-key
  namespace: default
spec:
  configRef: general-policy
  description: Legacy key (deprecated)
  enabled: false
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
  
  # API Key properties
  description: ""                  # API key description
  enabled: true                    # Enable/disable the key (pointer; nil = true)
```

### Enabled Flag

The `enabled` field controls whether the API key is active:

```yaml
spec:
  enabled: true   # Key is active; clients can use it
```

- **true** — Key is active and valid for API requests
- **false** — Key is disabled; requests using this key are rejected with 403 Forbidden

Disabling a key is safer than deleting it (non-destructive deactivation).

### Default Values

| Field | Default | Behavior |
|---|---|---|
| `configRef` | `general-policy` | Fall through to default profile |
| `nameOverride` | `""` | Use naming template from profile |
| `deletionPolicy` | `"retain"` | Keep key in AWS when CR is deleted |
| `description` | `""` | No description |
| `enabled` | `true` | Key is enabled |

### Status Outputs

```yaml
status:
  resourceName: api-key-name       # Effective cloud name
  namingStatus: valid              # valid | invalid-unresolved-tokens
  keyValue: a1b2c3d4e5f6g7h8       # Auto-generated API key value
  conditions:
    - type: Ready
      status: "True"
      reason: ReconciliationSucceeded
```

## Common Patterns

### Multiple Keys for Different Consumers

```yaml
# Web client key
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayAPIKey
metadata:
  name: web-client-key
  namespace: default
spec:
  configRef: general-policy
  description: API key for web dashboard
  tags:
    client-type: web
    team: platform

---
# Mobile client key
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayAPIKey
metadata:
  name: mobile-client-key
  namespace: default
spec:
  configRef: general-policy
  description: API key for mobile app
  tags:
    client-type: mobile
    team: mobile

---
# Third-party partner key
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayAPIKey
metadata:
  name: partner-key
  namespace: default
spec:
  configRef: general-policy
  description: API key for partner integration
  tags:
    client-type: partner
    partner-name: acme-corp
```

### Rotating API Keys

To rotate an API key safely:

1. Create a new key (this generates a new auto-generated value)
2. Update clients to use the new key value
3. Monitor the old key's usage to ensure no clients still use it
4. Disable the old key (set `enabled: false`)
5. After verification period, delete the old key (set `deletionPolicy: delete` then delete the CR)

### Environment-Specific Keys

```yaml
# Development environment
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayAPIKey
metadata:
  name: dev-key
  namespace: dev
spec:
  configRef: dev
  description: Development API key
  tags:
    environment: development

---
# Production environment
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayAPIKey
metadata:
  name: prod-key
  namespace: prod
spec:
  configRef: prod
  description: Production API key
  tags:
    environment: production
    pci-compliant: "true"
```

## Using API Keys in APIs

REST APIs require the API key to be passed by clients when `apiKeyRequired: true` is set on a method:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayRestAPI
metadata:
  name: protected-api
  namespace: default
spec:
  configRef: general-policy
  apiKeySource: HEADER  # Keys passed in headers
  resources:
    - pathPart: protected
      methods:
        - httpMethod: GET
          apiKeyRequired: true  # Require API key for this method
          integration:
            type: AWS_PROXY
            uri: arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/...
```

Clients make requests with the API key header:
```bash
curl -H "x-api-key: a1b2c3d4e5f6g7h8" https://api.example.com/protected
```

## Key Management Best Practices

### Never Hardcode Keys

❌ **Wrong:**
```yaml
spec:
  keyValue: hardcoded-key-123  # Never do this
```

✓ **Right:** Let AWS auto-generate the key; retrieve from `status.keyValue` and store in a secret manager.

### Store Keys Securely

After a key is created, retrieve its value and store it in a secrets manager:

```bash
kubectl get apikey mobile-key -o jsonpath='{.status.keyValue}'
```

Store this value in:
- AWS Secrets Manager
- HashiCorp Vault
- Kubernetes Secrets (with encryption at rest)

### Monitor Key Usage

Use CloudTrail and CloudWatch to monitor API key usage:

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceType,AttributeValue=APIGatewayAPIKey \
  --max-results 10
```

### Rotate Keys Regularly

Establish a key rotation schedule (e.g., quarterly) to minimize exposure of long-lived credentials.

## Deletion Policy

- **retain** (default) — Keep the API key in AWS when the Kubernetes CR is deleted
- **delete** — Delete both the Kubernetes CR and the AWS API key

```yaml
spec:
  deletionPolicy: delete  # Delete key when CR is deleted
```

## Naming and Identification

API keys use naming templates to generate cloud names:

```yaml
spec:
  # With profile template "{namespace}-{name}" and namespace default:
  # Resulting name: default-mobile-app-key
  
  nameOverride: production-api-key  # Override naming template
```

The effective name is exposed in `status.resourceName`.

## Monitoring

### Check API Key Status

```bash
kubectl describe apikey mobile-key -n default
```

Look for:
- `status.keyValue` — The auto-generated API key
- `status.resourceName` — The effective cloud name
- `status.namingStatus` — Naming validation result

### List All API Keys

```bash
kubectl get apikey -A
```

### Verify API Key Is Enabled

```bash
kubectl get apikey mobile-key -o jsonpath='{.spec.enabled}'
```

## Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| Request rejected with 403 | API key missing or invalid | Verify key is passed in correct header; check key is enabled |
| API key value is empty | Key not yet generated | Wait for reconciliation to complete; check status.keyValue |
| Cannot find key value | Key was deleted | Retrieve from AWS console or use new key |
| Key rotation issues | Old key still used | Monitor usage and verify all clients migrated before deleting old key |

## Limitations

- API keys are strings (not typed like OAuth tokens)
- No built-in expiration; rely on rotation for security
- Key values are auto-generated; manual values are not supported in Phase 1
- No built-in rate limiting per key (use usage plans for throttling)

## Cross-Provider Notes

- `APIGatewayAPIKey` is AWS-specific
- GCP uses API keys differently (resource-based, not usage-plan–based)
- Azure uses subscription keys with API Management

## See Also

- [API Gateway — Family Overview](index.md)
- [REST APIs](apigatewayrestapi.md) — Create and manage APIs
- [Governance Configuration](apigatewayconfig.md) — Profile settings
- [AWS API Gateway API Keys — Developer Guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-setup-api-key-with-console.html)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
