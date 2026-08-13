# ApiGatewayV2DomainName — Custom Domain Names

The `ApiGatewayV2DomainName` resource creates custom domain names for APIs, enabling access via branded URLs instead of AWS-managed `execute-api` endpoints. Custom domains support TLS certificates and optional mutual TLS authentication.

## Overview

Use `ApiGatewayV2DomainName` to:

- **Brand APIs** — Use company domains instead of `execute-api` endpoints
- **Enable HTTPS** — TLS certificates managed by AWS Certificate Manager (ACM)
- **Require mTLS** — Optional client certificate authentication
- **Support routing** — Route domain paths to different APIs and stages via `ApiGatewayV2ApiMapping`

Domains must be HTTPS-only; HTTP is not supported.

## Creating a Domain Name

### Basic Custom Domain

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
    - certificateArn: "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012"
```

This domain:
- Is accessible at `https://api.example.com`
- Uses the specified ACM certificate
- Inherits TLS version from governance profile (default: TLS 1.2)
- Can be mapped to APIs via `ApiGatewayV2ApiMapping`

### Domain with Explicit TLS Version

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2DomainName
metadata:
  name: secure-api-domain
  namespace: api-prod
spec:
  configRef: general-policy
  domainName: "secure-api.example.com"
  domainNameConfigurations:
    - certificateArn: "arn:aws:acm:us-east-1:123456789012:certificate/abcd1234"
      securityPolicy: "TLS_1_2"  # Enforce TLS 1.2
```

### Domain with Mutual TLS

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2DomainName
metadata:
  name: mtls-domain
  namespace: api-prod
spec:
  configRef: general-policy
  domainName: "internal-api.example.com"
  domainNameConfigurations:
    - certificateArn: "arn:aws:acm:us-east-1:123456789012:certificate/server-cert"
      securityPolicy: "TLS_1_2"
  
  mutualTlsAuthentication:
    truststoreUri: "s3://mybucket/truststore.pem"
    truststoreVersion: "v1"  # Optional S3 version ID
```

Mutual TLS requires clients to present a valid certificate from the truststore (stored in S3).

### Domain with Multiple Configurations

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2DomainName
metadata:
  name: multi-config-domain
  namespace: api-prod
spec:
  configRef: general-policy
  domainName: "api.example.com"
  domainNameConfigurations:
    - certificateArn: "arn:aws:acm:us-east-1:123456789012:certificate/current"
    - certificateArn: "arn:aws:acm:us-east-1:123456789012:certificate/next"  # During rotation
```

Multiple configurations enable certificate rotation without downtime.

## Configuration

### Domain Name

**`domainName`** — The fully qualified domain name

- Type: string
- Required
- Immutable (cannot be changed)
- Must be registered and point to API Gateway endpoint via CNAME or ALIAS record

```yaml
spec:
  domainName: "api.example.com"
```

### Domain Name Configurations

**`domainNameConfigurations[]`** — TLS certificate and security policy

**`certificateArn`** — ACM certificate ARN

- Type: string (ARN)
- Required
- Must be in the same region as the API

```yaml
domainNameConfigurations:
  - certificateArn: "arn:aws:acm:us-east-1:123456789012:certificate/12345"
```

**`securityPolicy`** — TLS version requirement

- Type: string
- Default: `"TLS_1_2"` (from governance profile)
- Valid: `"TLS_1_0"`, `"TLS_1_2"`
- Governable: Governance profile can enforce a minimum

```yaml
domainNameConfigurations:
  - certificateArn: "arn:aws:acm:us-east-1:123456789012:certificate/12345"
    securityPolicy: "TLS_1_2"
```

**`ownershipCertificateArn`** — Ownership verification (optional)

- Type: string (ARN)
- Used for domain ownership verification during setup
- Usually not required after initial setup

### Mutual TLS Authentication

**`mutualTlsAuthentication`** — Require client certificates

```yaml
spec:
  mutualTlsAuthentication:
    truststoreUri: "s3://my-bucket/truststore.pem"
    truststoreVersion: "v123"  # Optional: specific S3 version
```

**`truststoreUri`** — S3 location of PEM-encoded certificate authority bundle

- Type: string (S3 URI)
- Format: `s3://bucket-name/key-name`
- Contains PEM-encoded CA certificates trusted for client authentication

**`truststoreVersion`** — S3 object version ID (optional)

- Type: string
- Used to pin to a specific version of the truststore
- Useful for gradual certificate rotation

Example truststore (PEM format):

```
-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAJC1/iNAZwqDMA0GCSqGSIb3DQEBBQUAMEUxCzAJBgNV
...
-----END CERTIFICATE-----
```

## Tags and Labels

Add organization metadata:

```yaml
spec:
  tags:
    team: api-platform
    environment: production
  syncedLabels:
    app: api-gateway
  syncedAnnotations:
    managed-by: "kropath"
```

## Deletion Policy

### Retain (default)

```yaml
spec:
  deletionPolicy: "retain"
```

The domain name remains in API Gateway.

### Delete

```yaml
spec:
  deletionPolicy: "delete"
```

The domain name is deleted when the CR is deleted.

## Setting Up DNS

After creating the domain, configure DNS to point to the API Gateway endpoint:

### Get the Target Endpoint

```bash
kubectl get domainname api-domain -n api-prod -o jsonpath='{.status.ackResourceMetadata}' | jq
```

Look for the regional endpoint (e.g., `d123456789.execute-api.us-east-1.amazonaws.com`).

### Update DNS

**CNAME record** (most common):

```
api.example.com    CNAME    d123456789.execute-api.us-east-1.amazonaws.com
```

**ALIAS record** (Route53):

```
Name: api.example.com
Type: A
Alias: d123456789.execute-api.us-east-1.amazonaws.com
Alias Target: Yes
Routing Policy: Simple
```

After DNS propagates, verify:

```bash
nslookup api.example.com
# Should resolve to the API Gateway endpoint
```

## Mapping Domain to APIs

After creating the domain, use `ApiGatewayV2ApiMapping` to route traffic to APIs:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2ApiMapping
metadata:
  name: orders-mapping
  namespace: api-prod
spec:
  domainRef: api-domain
  apiRef: orders-api
  stage: prod
  apiMappingKey: ""  # Empty = root path
```

Now `https://api.example.com/` routes to the orders API.

With multiple mappings:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2ApiMapping
metadata:
  name: orders-v1-mapping
  namespace: api-prod
spec:
  domainRef: api-domain
  apiRef: orders-api
  stage: prod
  apiMappingKey: "v1"  # https://api.example.com/v1
---
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2ApiMapping
metadata:
  name: users-v1-mapping
  namespace: api-prod
spec:
  domainRef: api-domain
  apiRef: users-api
  stage: prod
  apiMappingKey: "v2"  # https://api.example.com/v2
```

## Certificate Management

### Renewing Certificates

ACM handles certificate renewal automatically. No action needed.

### Rotating Certificates

1. Request a new certificate in ACM
2. Add the new certificate to `domainNameConfigurations`
3. Wait for DNS to stabilize
4. Remove the old certificate

### Adding a Backup Certificate

Add multiple certificates for failover:

```yaml
spec:
  domainNameConfigurations:
    - certificateArn: "arn:aws:acm:us-east-1:123456789012:certificate/primary"
    - certificateArn: "arn:aws:acm:us-east-1:123456789012:certificate/backup"
```

## Monitoring and Verification

### Check Domain Status

```bash
kubectl describe domainname api-domain -n api-prod
```

Look for:
- `status.conditions` — Ready, error, or warning states
- `spec.domainName` — The configured domain

### Test the Domain

```bash
curl https://api.example.com/
```

Should return a response from the mapped API.

### Verify TLS

```bash
openssl s_client -connect api.example.com:443
```

Check certificate validity and TLS version.

### Monitor CloudWatch Logs

Access logs are available in CloudWatch if configured on the stages:

```bash
aws logs tail /api-gateway/logs --follow
```

## Best Practices

1. **Use HTTPS only** — Custom domains require TLS; HTTP is not supported.
2. **Plan domain structure** — Use subdomains for different API purposes (`api.example.com`, `internal-api.example.com`).
3. **Automate certificate renewal** — Use ACM for automatic renewal.
4. **Enable mTLS for internal APIs** — Require client certificates for internal-only APIs.
5. **Monitor DNS** — Verify CNAME/ALIAS records are correctly configured.
6. **Use path-based routing** — Map multiple APIs to one domain via `ApiMappingKey` for cost efficiency.

## Limitations

- Only HTTPS supported (HTTP not available)
- Domain name is immutable after creation
- Endpoint type is REGIONAL (global not supported for V2)
- Maximum 128-character domain name

## Cross-Provider Notes

- Custom domain configuration is AWS-specific
- GCP Cloud API Gateway uses custom domains via Google Cloud DNS
- Azure API Management handles custom domains differently via custom hostnames
- mTLS implementation differs: AWS uses S3 truststore; Azure uses certificate pinning
- Certificate management via ACM is AWS-specific; GCP uses Google Cloud Certificate Manager; Azure uses Azure Key Vault

## See Also

- [API Gateway V2](index.md) — Family overview
- [API Mapping](apigatewayv2apimapping.md) — Route domain paths to APIs
- [HTTP APIs](apigatewayv2httpapi.md) — Create HTTP APIs
- [WebSocket APIs](apigatewayv2websocketapi.md) — Create WebSocket APIs
- [Stages](apigatewayv2stage.md) — Configure deployment stages
