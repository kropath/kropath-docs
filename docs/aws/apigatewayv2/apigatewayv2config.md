# ApiGatewayV2Config — API Gateway V2 Governance

The `ApiGatewayV2Config` resource defines per-environment governance policies for all API Gateway V2 resources. Platform teams deploy named profiles to enforce security, compliance, and operational standards across all HTTP APIs, WebSocket APIs, stages, and custom domains.

## Overview

Governance profiles control:

- **Security** — Enforce TLS version minimums, disable default endpoints, enable access logging
- **Compliance** — Mandate CORS configuration, set naming conventions
- **Throttling** — Define default and maximum rate limits for API traffic
- **Naming** — Standardize resource naming across namespaces and teams
- **Metadata** — Apply org-wide tags, labels, and annotations
- **Logging** — Route all API access logs to centralized destinations

Policies cascade through three tiers:

1. **Mandatory** — Enforced on all instances; cannot be overridden
2. **Defaults** — Applied if not specified; can be overridden per-instance
3. **Instance override** — Developer-specified values in the API CR

## Governance Tiers

Policies in `ApiGatewayV2Config` are organized into two tiers to provide flexibility:

**Mandatory Tier (`spec.mandatory`):** Policies that must always apply. Overrides instance-level settings. Use for strict compliance requirements.

**Defaults Tier (`spec.defaults`):** Suggested policies applied when not overridden. Instances can customize unless mandatory tier prevents it.

## Creating Governance Profiles

### General-Purpose Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2Config
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory:
    disableExecuteApiEndpoint: false
    corsEnabled: false
    defaultThrottlingBurstLimit: 0
    defaultThrottlingRateLimit: 0.0
    minimumTlsVersion: ""
    accessLogDestinationArn: ""
    accessLogFormat: ""
    namingTemplate: ""
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    disableExecuteApiEndpoint: false
    corsEnabled: false
    defaultThrottlingBurstLimit: 0
    defaultThrottlingRateLimit: 0.0
    minimumTlsVersion: "TLS_1_2"
    accessLogDestinationArn: ""
    accessLogFormat: ""
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

This profile:
- Does not enforce any mandatory policies (all zeros/empty)
- Defaults to TLS 1.2 minimum
- Uses the standard naming template `{namespace}-{name}`

### PCI-DSS Compliance Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2Config
metadata:
  name: pci
  namespace: kro-system
spec:
  mandatory:
    disableExecuteApiEndpoint: true  # Enforce custom domains only
    minimumTlsVersion: "TLS_1_2"      # Enforce TLS 1.2
    accessLogDestinationArn: "arn:aws:logs:us-east-1:123456789012:log-group:/pci-api-logs"
    accessLogFormat: "$context.requestId $context.identity.sourceIp $context.identity.userAgent $context.requestTime $context.status"
    defaultThrottlingRateLimit: 1000   # Enforce rate limiting
    defaultThrottlingBurstLimit: 2000  # Enforce burst control
  defaults:
    corsEnabled: false
    tags:
      compliance: pci-dss
      audit-required: "true"
    syncedLabels:
      security-zone: internal
    syncedAnnotations:
      encryption-status: "required"
```

This profile enforces:
- Custom domains only (no default `execute-api` endpoint)
- TLS 1.2 or higher
- Access logging to a centralized CloudWatch group
- Rate limiting (1000 req/sec, 2000 burst)
- Auto-applied PCI compliance tags and labels

### Multi-Environment Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2Config
metadata:
  name: prod-policy
  namespace: kro-system
spec:
  mandatory:
    disableExecuteApiEndpoint: true  # Production: require custom domains
  defaults:
    minimumTlsVersion: "TLS_1_2"
    accessLogDestinationArn: "arn:aws:logs:us-east-1:123456789012:log-group:/prod-api-logs"
    accessLogFormat: "$json"  # JSON structured logging
    defaultThrottlingRateLimit: 1000
    defaultThrottlingBurstLimit: 2000
    namingTemplate: "prod-{namespace}-{name}"
    tags:
      environment: production
      cost-center: "operations"
```

## Configuration Fields

### Security

**`disableExecuteApiEndpoint`** — Disable the default AWS-managed `execute-api` endpoint

- **Type:** boolean
- **Default (mandatory):** `false` (not enforced)
- **Default (defaults):** `false` (custom domains optional)
- **Use case:** Enforce custom domains in production; allows instances to choose

When mandatory is `true`:
- All APIs **must** disable the `execute-api` endpoint
- APIs must use custom domains (`ApiGatewayV2DomainName`)
- Improves security by preventing direct AWS endpoint access

**`minimumTlsVersion`** — Enforce a minimum TLS version for custom domains

- **Type:** string
- **Valid values:** `"TLS_1_0"`, `"TLS_1_2"`
- **Default (mandatory):** `""` (not enforced)
- **Default (defaults):** `"TLS_1_2"` (recommended)
- **Use case:** Security profiles mandate TLS 1.2+

```yaml
spec:
  mandatory:
    minimumTlsVersion: "TLS_1_2"  # All domains must use TLS 1.2
```

### CORS

**`corsEnabled`** — Require CORS configuration on HTTP APIs

- **Type:** boolean
- **Default (mandatory):** `false` (not enforced)
- **Default (defaults):** `false` (optional)
- **Use case:** Public APIs accessible from browsers; mandatory for cross-origin requests

When mandatory is `true`:
- All HTTP APIs **must** include a `corsConfiguration` block
- WebSocket APIs are unaffected

```yaml
spec:
  mandatory:
    corsEnabled: true  # Force all HTTP APIs to define CORS

# Instance must now include corsConfiguration
spec:
  corsConfiguration:
    allowOrigins: ["https://example.com"]
```

### Throttling

**`defaultThrottlingRateLimit`** — Default rate limit (requests per second)

- **Type:** number (float)
- **Default (mandatory):** `0.0` (not enforced)
- **Default (defaults):** `0.0` (use AWS account defaults)
- **Range:** 0 or any positive number
- **Use case:** Prevent runaway costs; enforce consistent API performance

**`defaultThrottlingBurstLimit`** — Default burst limit (peak concurrent requests)

- **Type:** integer
- **Default (mandatory):** `0` (not enforced)
- **Default (defaults):** `0` (use AWS account defaults)
- **Range:** 0 or any positive integer
- **Use case:** Control traffic spikes; prevent sudden load

```yaml
spec:
  mandatory:
    defaultThrottlingRateLimit: 1000   # Hard limit: 1000 req/sec
    defaultThrottlingBurstLimit: 2000  # Peak: 2000 concurrent requests
```

Throttling applies to all routes in a stage unless overridden at the route level.

### Access Logging

**`accessLogDestinationArn`** — CloudWatch Logs group or Kinesis Firehose for access logs

- **Type:** string (ARN)
- **Default (mandatory):** `""` (not enforced)
- **Default (defaults):** `""` (optional)
- **Format:** CloudWatch: `arn:aws:logs:region:account:log-group:name`; Kinesis: `arn:aws:kinesis:region:account:stream/name`

**`accessLogFormat`** — Log format string

- **Type:** string
- **Default (mandatory):** `""` (not enforced)
- **Default (defaults):** `""` (AWS-recommended JSON)
- **Formats:**
  - `"$json"` → JSON structured logging
  - `"$clf"` → Common Log Format
  - Custom format with tokens: `$context.requestId $context.status $context.error.message`

```yaml
spec:
  mandatory:
    accessLogDestinationArn: "arn:aws:logs:us-east-1:123456789012:log-group:/api-logs"
    accessLogFormat: "$json"  # JSON logging mandatory
```

When set:
- Stages inherit logging configuration
- Instances can override unless mandatory tier prevents it
- Logs are delivered continuously to the specified destination

### Naming

**`namingTemplate`** — Template for generating resource names

- **Type:** string
- **Default (mandatory):** `""` (not enforced)
- **Default (defaults):** `"{namespace}-{name}"` (recommended)
- **Tokens:** `{namespace}`, `{name}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.<key>}`
- **Use case:** Enforce naming conventions across teams

```yaml
spec:
  defaults:
    namingTemplate: "prod-{namespace}-{name}"
```

With this template:
- Namespace: `api-prod`
- CR name: `orders-api`
- **Resulting name:** `prod-api-prod-orders-api`

Naming applies to HTTP APIs, WebSocket APIs, and VPC Links (which have provider `name` fields). Stages and domain names use different identifiers and don't use the naming template.

### Metadata

**`tags`** — AWS tags applied to all API resources

- **Type:** map (key-value pairs)
- **Default:** `{}` (empty)
- **Use case:** Cost tracking, environment identification, automation

**`syncedLabels`** — Kubernetes labels synced to AWS tags

- **Type:** map
- **Default:** `{}` (empty)
- **Prefixed:** `aws.kropath.run/` on AWS resources; plain keys on Kubernetes

**`syncedAnnotations`** — Kubernetes annotations synced to AWS tags

- **Type:** map
- **Default:** `{}` (empty)
- **Prefixed:** `aws.kropath.run/` on both Kubernetes and AWS

```yaml
spec:
  defaults:
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

## Selecting a Profile

APIs reference a governance profile via `configRef`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2HttpApi
metadata:
  name: orders-api
  namespace: api-prod
spec:
  configRef: general-policy  # Use the general-policy profile
```

If the referenced profile doesn't exist, APIs default to `general-policy`. If `general-policy` doesn't exist, the API deployment fails with an error.

## Profile Resolution Order

When creating an API, kropath resolves configuration in this order:

1. **Mandatory tier** from the profile (cannot be overridden)
2. **Instance spec** (developer-specified values)
3. **Defaults tier** from the profile (fallback values)

Example with the `pci` profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2Config
metadata:
  name: pci
spec:
  mandatory:
    minimumTlsVersion: "TLS_1_2"      # REQUIRED
  defaults:
    defaultThrottlingRateLimit: 1000  # Used if instance doesn't specify

---
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2HttpApi
metadata:
  name: orders-api
  namespace: api-prod
spec:
  configRef: pci
  # TLS version: MUST be TLS_1_2 (from mandatory)
  # Rate limit: Uses 1000 (from defaults, instance didn't specify)
```

## Tags and Labels

Apply metadata to the governance profile itself:

```yaml
metadata:
  name: pci
  namespace: kro-system
  labels:
    compliance: pci-dss
    tier: governance
  annotations:
    description: "PCI-DSS compliance profile for payment APIs"
```

## Deletion Policy

Governance profiles are not managed by deletion policies. Deleting a profile does **not** delete APIs that reference it; APIs continue to operate but may fail to reconcile if they can't locate the profile.

To safely remove a profile:

1. Update all APIs to use a different `configRef`
2. Verify no APIs reference the old profile
3. Delete the old profile

## Monitoring and Verification

### Check a Profile

```bash
kubectl describe apigwv2config general-policy -n kro-system
```

Look for:
- `spec.mandatory` — Policies that are enforced
- `spec.defaults` — Fallback policies
- `status.effectiveConfig` — Merged configuration after cascade resolution

### View Effective Configuration

The controller computes and exposes `status.effectiveConfig`:

```bash
kubectl get apigwv2config general-policy -n kro-system -o jsonpath='{.status.effectiveConfig}' | jq
```

This shows what an API will actually use after merging all tiers.

### Audit API Compliance

List all APIs using a profile:

```bash
kubectl get httpapi,websocketapi -A -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.configRef}{"\n"}{end}'
```

Verify they're using the intended profile.

## Cross-Provider Notes

- `ApiGatewayV2Config` is AWS-specific
- GCP and Azure have their own API management governance models
- TLS version names differ by provider: AWS uses `TLS_1_0`, `TLS_1_2`; others use `1.0`, `1.2`
- Access logging destinations are provider-specific: AWS uses CloudWatch Logs or Kinesis Firehose; GCP uses Cloud Logging; Azure uses Diagnostic Settings

## See Also

- [API Gateway V2](index.md) — Family overview
- [HTTP APIs](apigatewayv2httpapi.md) — Create HTTP APIs
- [Stages](apigatewayv2stage.md) — Deploy to stages
- [Custom Domains](apigatewayv2domainname.md) — Use custom domains
