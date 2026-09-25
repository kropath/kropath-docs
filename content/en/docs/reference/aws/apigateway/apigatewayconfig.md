---
title: APIGatewayConfig — REST API Governance
description: "The `APIGatewayConfig` resource defines per-environment governance policies for all REST API resources."
doc_type: reference
---
# APIGatewayConfig — REST API Governance

The `APIGatewayConfig` resource defines per-environment governance policies for all REST API resources. Platform teams deploy named profiles to enforce security, compliance, and operational standards across all APIs, authorizers, deployments, and VPC links.

## Overview

Governance profiles control:

- **Security** — Enforce minimum TLS versions, endpoint types, disable default endpoints
- **Compliance** — Mandate naming conventions, metadata tagging
- **API Key Management** — Enforce API key source (header vs authorizer)
- **Naming** — Standardize resource naming across namespaces and teams
- **Metadata** — Apply org-wide tags, labels, and annotations

Policies cascade through three tiers:

1. **Mandatory** — Enforced on all instances; cannot be overridden
2. **Defaults** — Applied if not specified; can be overridden per-instance
3. **Instance override** — Developer-specified values in the API CR

## Governance Tiers

Policies in `APIGatewayConfig` are organized into two tiers to provide flexibility and governance control.

**Mandatory Tier (`spec.mandatory`):** Policies that must always apply. Overrides instance-level settings. Use for strict compliance requirements.

**Defaults Tier (`spec.defaults`):** Suggested policies applied when not overridden. Instances can customize unless mandatory tier prevents it.

## Creating Governance Profiles

### General-Purpose Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory:
    endpointType: ""
    apiKeySource: ""
    minimumTlsVersion: ""
    disableExecuteApiEndpoint: false
    namingTemplate: ""
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    endpointType: REGIONAL
    apiKeySource: HEADER
    minimumTlsVersion: ""
    disableExecuteApiEndpoint: false
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

This profile:
- Does not enforce any mandatory policies (all zeros/empty)
- Defaults to REGIONAL endpoint type
- Uses HEADER as the API key source
- Uses the standard naming template `{namespace}-{name}`

### Production Compliance Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayConfig
metadata:
  name: prod
  namespace: kro-system
spec:
  mandatory:
    endpointType: REGIONAL
    minimumTlsVersion: TLS_1_2
    apiKeySource: HEADER
    disableExecuteApiEndpoint: false
    namingTemplate: "prod-{namespace}-{name}"
    tags:
      environment: production
      managed-by: kropath
  defaults:
    syncedLabels:
      compliance-tier: production
    syncedAnnotations:
      backup-required: "true"
```

This profile enforces:
- REGIONAL endpoints only (no edge-optimized)
- TLS 1.2 or higher for all custom domains
- Mandatory production naming prefix
- Auto-applied production tags and labels

### PCI-DSS Compliance Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayConfig
metadata:
  name: pci
  namespace: kro-system
spec:
  mandatory:
    endpointType: PRIVATE  # Private endpoints only
    minimumTlsVersion: TLS_1_2
    disableExecuteApiEndpoint: true  # Disable default AWS endpoint
    namingTemplate: "pci-{namespace}-{name}"
    tags:
      compliance: pci-dss
      audit-required: "true"
      encryption: required
  defaults:
    syncedLabels:
      security-zone: internal
      data-classification: sensitive
    syncedAnnotations:
      encryption-status: required
      audit-log-required: "true"
```

This profile enforces:
- Private endpoints only (VPC access required)
- TLS 1.2 minimum
- Disable AWS-managed endpoint (use custom domains)
- Mandatory PCI compliance tagging

## Configuration Fields

### Endpoint Type

**`endpointType`** — Endpoint type for REST APIs

- **Type:** string
- **Valid values:** `REGIONAL` | `EDGE` | `PRIVATE` | `""` (empty = not enforced)
- **Default (mandatory):** `""` (not enforced)
- **Default (defaults):** `REGIONAL`
- **Use case:** Enforce PRIVATE endpoints in internal APIs; EDGE for public CDN-backed APIs

- **REGIONAL:** Regional endpoint, API Gateway managed
- **EDGE:** Edge-optimized; CloudFront-backed for global latency
- **PRIVATE:** Private endpoint; requires VPC access via VPC endpoints

When mandatory is set:
- All APIs **must** use the specified endpoint type
- Instance `spec.endpointType` is overridden and ignored

### Minimum TLS Version

**`minimumTlsVersion`** — Enforce minimum TLS version for custom domains

- **Type:** string
- **Valid values:** `TLS_1_0` | `TLS_1_2` | `""` (empty = not enforced)
- **Default (mandatory):** `""` (not enforced)
- **Default (defaults):** `""` (use AWS default of TLS 1.0)
- **Use case:** Security profiles mandate TLS 1.2+

```yaml
spec:
  mandatory:
    minimumTlsVersion: TLS_1_2  # All APIs must use TLS 1.2
```

When set on a custom domain (via API Gateway management), only the specified TLS version and higher are allowed.

### API Key Source

**`apiKeySource`** — Where the API key is sourced from in requests

- **Type:** string
- **Valid values:** `HEADER` | `AUTHORIZER` | `""` (empty = not enforced)
- **Default (mandatory):** `""` (not enforced)
- **Default (defaults):** `HEADER`
- **Use case:** Enforce AUTHORIZER-sourced keys for OAuth flows; HEADER for traditional API keys

- **HEADER:** API key passed in HTTP request headers (e.g. `x-api-key`)
- **AUTHORIZER:** API key sourced from authorizer response

```yaml
spec:
  mandatory:
    apiKeySource: HEADER  # All APIs require HEADER-sourced keys
```

### Disable Execute API Endpoint

**`disableExecuteApiEndpoint`** — Disable the default AWS-managed `execute-api` endpoint

- **Type:** boolean
- **Default (mandatory):** `false` (not enforced)
- **Default (defaults):** `false` (default endpoint enabled)
- **Use case:** Enforce custom domains in production; prevent direct AWS endpoint access

When mandatory is `true`:
- All APIs **must** disable the `execute-api` endpoint
- APIs must use custom domains
- Improves security by preventing AWS-managed endpoint bypass

```yaml
spec:
  mandatory:
    disableExecuteApiEndpoint: true  # Disable default AWS endpoint
```

### Naming

**`namingTemplate`** — Template for generating cloud resource names

- **Type:** string
- **Default (mandatory):** `""` (not enforced)
- **Default (defaults):** `"{namespace}-{name}"`
- **Tokens:** `{namespace}`, `{name}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.<key>}`
- **Use case:** Enforce naming conventions across teams and environments

```yaml
spec:
  defaults:
    namingTemplate: "prod-{namespace}-{name}"
```

With this template:
- Namespace: `api-prod`
- CR name: `orders-api`
- **Resulting name:** `prod-api-prod-orders-api`

Naming template applies to APIs, authorizers, VPC links, and API keys (resources with provider `name` fields). Deployments don't use naming templates.

### Metadata

**`tags`** — AWS tags applied to API resources

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
      app: orders-service
      version: v1
    syncedAnnotations:
      slack-channel: "#api-alerts"
      on-call: api-team
```

Metadata at the governance level applies to all resources of this type. Instances can add custom metadata which merges with governance defaults and mandatory tags.

## Selecting a Profile

APIs reference a governance profile via `configRef`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayRestAPI
metadata:
  name: orders-api
  namespace: api-prod
spec:
  configRef: prod  # Use the prod profile
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
kind: APIGatewayConfig
metadata:
  name: pci
spec:
  mandatory:
    minimumTlsVersion: TLS_1_2      # REQUIRED
    endpointType: PRIVATE           # REQUIRED
  defaults:
    namingTemplate: "pci-{namespace}-{name}"  # Used if instance doesn't specify

---
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayRestAPI
metadata:
  name: payments-api
  namespace: api-prod
spec:
  configRef: pci
  # TLS version: MUST be TLS_1_2 (from mandatory)
  # Endpoint type: MUST be PRIVATE (from mandatory)
  # Naming template: Uses pci-api-prod-payments-api (from defaults)
```

## Tier-Exclusive Validation

Scalar fields (`endpointType`, `apiKeySource`, etc.) cannot be set in both mandatory and defaults simultaneously. If you attempt this, the APIGatewayConfig will be rejected with a validation error:

```yaml
spec:
  mandatory:
    endpointType: REGIONAL
  defaults:
    endpointType: EDGE  # ERROR: Cannot set in both tiers
```

Map fields (`tags`, `syncedLabels`, `syncedAnnotations`) are NOT mutually exclusive — they use additive merge instead. The final effective config will contain all keys from both mandatory and defaults tiers.

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

These labels help operators organize and discover profiles. The labels are distinct from `spec.tags`, which apply to REST API resources.

## Deletion Policy

Governance profiles are not managed by deletion policies. Deleting a profile does **not** delete APIs that reference it; APIs continue to operate but may fail to reconcile if they can't locate the profile.

To safely remove a profile:

1. Update all APIs to use a different `configRef`
2. Verify no APIs reference the old profile: `kubectl get restapi -A -o jsonpath='{range .items[*]}{.spec.configRef}{"\n"}{end}'`
3. Delete the old profile

## Monitoring and Verification

### Check a Profile

```bash
kubectl describe apigwconfig prod -n kro-system
```

Look for:
- `spec.mandatory` — Policies that are enforced
- `spec.defaults` — Fallback policies
- `status.effectiveConfig` — Merged configuration after cascade resolution

### View Effective Configuration

The controller computes and exposes `status.effectiveConfig` after merging KropathConfig org-level settings with the APIGatewayConfig profile:

```bash
kubectl get apigwconfig prod -n kro-system -o jsonpath='{.status.effectiveConfig}' | jq
```

This shows what an API will actually use after merging all tiers (org-wide, profile, instance).

### Audit API Compliance

List all APIs using a profile:

```bash
kubectl get restapi -A -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.configRef}{"\n"}{end}'
```

Verify they're using the intended profile.

## Cross-Provider Notes

- `APIGatewayConfig` is AWS REST API–specific
- GCP and Azure have their own API management governance models
- Field names differ by provider: AWS uses `endpointType`; others use different terminology
- Minimum TLS version names differ: AWS uses `TLS_1_0`, `TLS_1_2`

## See Also

- [API Gateway — Family Overview](index.md)
- [REST APIs](apigatewayrestapi.md) — Create REST APIs
- [Authorizers](apigatewayauthorizer.md) — Authorization strategies
- [ADR-015 — Consolidated Platform Decisions](https://github.com/kropath/kropath-core/blob/main/docs/adrs/015-consolidated-platform-decisions.md) — Governance cascade design
