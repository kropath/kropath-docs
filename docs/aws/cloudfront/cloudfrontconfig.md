# CloudFrontConfig — Governance Configuration

`CloudFrontConfig` is the governance configuration for all CloudFront resources in your organization. Platform teams deploy profiles (e.g., `general-policy`, `strict-security`) to codify compliance requirements, security baselines, and operational defaults. Individual CloudFront resources reference a profile via `configRef`.

## Core Governance Model

Every CloudFront resource has a three-tier governance cascade:

1. **Mandatory tier** (highest priority) — Platform enforcement that overrides everything; used for compliance and security gates
2. **Resource spec** (middle) — Developer choices
3. **Defaults tier** (lowest priority) — Sensible fallbacks when the resource doesn't specify a value

**Example:** If `CloudFrontConfig` has `mandatory.viewerProtocolPolicy: "https-only"`, all distributions must use HTTPS-only, regardless of what developers set in their `spec`.

## Configuration Fields

### Mandatory Tier

Fields in the `spec.mandatory` section override developer choices. Use these for compliance requirements.

| Field | Type | Purpose |
|---|---|---|
| `viewerProtocolPolicy` | string | Force all distributions to use a specific viewer protocol: `"https-only"`, `"redirect-to-https"`, or `""` (not enforced) |
| `minimumProtocolVersion` | string | Enforce minimum TLS version (e.g., `"TLSv1.2_2021"`); empty string means not enforced |
| `httpVersion` | string | Enforce HTTP version: `"http2"`, `"http2and3"`, `"http3"`, or `""` (not enforced) |
| `sslSupportMethod` | string | Enforce SSL method: `"sni-only"`, `"vip"`, or `""` (not enforced) |
| `loggingEnabled` | boolean | Force all distributions to enable access logging to S3 |
| `loggingBucket` | string | Mandatory S3 bucket for access logs (only used when `loggingEnabled: true`) |
| `priceClass` | string | Enforce edge tier: `"PriceClass_100"`, `"PriceClass_200"`, `"PriceClass_All"`, or `""` (not enforced) |
| `webACLRequired` | boolean | Require all distributions to have a WAF WebACL attached (blocks creation if missing) |
| `geoRestrictionType` | string | Enforce geographic restriction: `"whitelist"`, `"blacklist"`, `"none"`, or `""` (not enforced) |
| `oacSigningBehavior` | string | Enforce OAC signing behavior: `"always"`, `"never"`, `"no-override"`, or `""` (not enforced) |
| `namingTemplate` | string | Enforce naming convention for policy resources (e.g., `"{namespace}-{name}"`) |
| `tags` | map | Mandatory AWS tags applied to all distributions |
| `syncedLabels` | map | Mandatory Kubernetes labels and AWS tags |
| `syncedAnnotations` | map | Mandatory Kubernetes annotations |

### Defaults Tier

Fields in the `spec.defaults` section apply when a resource doesn't specify a value. Use these for sensible, overrideable baselines.

| Field | Type | Default Value | Purpose |
|---|---|---|---|
| `viewerProtocolPolicy` | string | `"redirect-to-https"` | Default viewer protocol if not specified in distribution |
| `minimumProtocolVersion` | string | `"TLSv1.2_2021"` | Default minimum TLS version |
| `httpVersion` | string | `"http2"` | Default HTTP version |
| `sslSupportMethod` | string | `"sni-only"` | Default SSL method |
| `loggingEnabled` | boolean | `false` | Access logging disabled by default |
| `loggingBucket` | string | `""` | No default bucket (only relevant if loggingEnabled is true) |
| `priceClass` | string | `"PriceClass_All"` | Use all edge locations by default |
| `webACLRequired` | boolean | `false` | WAF not required by default |
| `geoRestrictionType` | string | `"none"` | No geographic restriction by default |
| `oacSigningBehavior` | string | `"always"` | OAC always signs requests by default |
| `namingTemplate` | string | `"{namespace}-{name}"` | Default naming template |
| `tags` | map | `{}` | No default tags |
| `syncedLabels` | map | `{}` | No default labels |
| `syncedAnnotations` | map | `{}` | No default annotations |

## Typical Profiles

### general-policy (Default)

Used by most workloads. All mandatory fields empty (no enforcement), sensible defaults.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory:
    viewerProtocolPolicy: ""        # No enforcement
    minimumProtocolVersion: ""      # No enforcement
    httpVersion: ""                 # No enforcement
    sslSupportMethod: ""            # No enforcement
    loggingEnabled: false           # Not enforced
    loggingBucket: ""               # Not enforced
    priceClass: ""                  # Not enforced
    webACLRequired: false           # Not enforced
    geoRestrictionType: ""          # Not enforced
    oacSigningBehavior: ""          # Not enforced
    namingTemplate: ""              # Not enforced
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    viewerProtocolPolicy: "redirect-to-https"
    minimumProtocolVersion: "TLSv1.2_2021"
    httpVersion: "http2"
    sslSupportMethod: "sni-only"
    loggingEnabled: false
    loggingBucket: ""
    priceClass: "PriceClass_All"
    webACLRequired: false
    geoRestrictionType: "none"
    oacSigningBehavior: "always"
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

### strict-security

For production workloads with high security requirements. Enforces HTTPS, minimum TLS version, WAF requirement, and logging.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontConfig
metadata:
  name: strict-security
  namespace: kro-system
spec:
  mandatory:
    viewerProtocolPolicy: "https-only"        # Enforce HTTPS-only
    minimumProtocolVersion: "TLSv1.2_2021"    # Enforce TLS 1.2 minimum
    httpVersion: "http2and3"                  # Enforce modern HTTP versions
    sslSupportMethod: "sni-only"              # Enforce SNI
    loggingEnabled: true                      # Force logging
    loggingBucket: "org-cf-logs.s3.amazonaws.com"  # Enforce logging bucket
    priceClass: ""                            # No enforcement
    webACLRequired: true                      # Require WAF
    geoRestrictionType: ""                    # No enforcement
    oacSigningBehavior: "always"              # Enforce OAC always signing
    namingTemplate: ""                        # No enforcement
    tags:
      security-profile: strict
    syncedLabels:
      compliance: pci
    syncedAnnotations: {}
  defaults:
    viewerProtocolPolicy: "https-only"
    minimumProtocolVersion: "TLSv1.2_2021"
    httpVersion: "http2and3"
    sslSupportMethod: "sni-only"
    loggingEnabled: true
    loggingBucket: "org-cf-logs.s3.amazonaws.com"
    priceClass: "PriceClass_200"  # Use fewer edge locations
    webACLRequired: true
    geoRestrictionType: "none"
    oacSigningBehavior: "always"
    namingTemplate: "{namespace}-{configRef}-{name}"
    tags:
      security-profile: strict
    syncedLabels:
      compliance: pci
    syncedAnnotations: {}
```

### cost-optimized

For non-critical workloads where cost matters more than performance.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontConfig
metadata:
  name: cost-optimized
  namespace: kro-system
spec:
  mandatory:
    viewerProtocolPolicy: ""
    minimumProtocolVersion: ""
    httpVersion: ""
    sslSupportMethod: ""
    loggingEnabled: false  # Don't log to save costs
    loggingBucket: ""
    priceClass: "PriceClass_100"  # Mandatory: Use fewer, cheaper edge locations
    webACLRequired: false
    geoRestrictionType: ""
    oacSigningBehavior: ""
    namingTemplate: ""
    tags:
      cost-profile: optimized
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    viewerProtocolPolicy: "redirect-to-https"
    minimumProtocolVersion: "TLSv1.2_2019"  # Allow older TLS
    httpVersion: "http2"
    sslSupportMethod: "sni-only"
    loggingEnabled: false
    loggingBucket: ""
    priceClass: "PriceClass_100"  # Use fewer edge locations
    webACLRequired: false
    geoRestrictionType: "none"
    oacSigningBehavior: "always"
    namingTemplate: "{namespace}-{name}"
    tags:
      cost-profile: optimized
    syncedLabels: {}
    syncedAnnotations: {}
```

## How to Use CloudFrontConfig

### As a Distribution Developer

Reference your profile in every distribution:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontDistribution
metadata:
  name: my-app
  namespace: app-team
spec:
  configRef: general-policy  # or strict-security, cost-optimized, etc.
  # ... rest of distribution spec
```

If a governance field is mandatory, you cannot override it — it is enforced. If it's in defaults, you can override it by setting the field explicitly in your spec.

**For example:** Under `strict-security`, if `mandatory.viewerProtocolPolicy: "https-only"`, you cannot set `spec.defaultCacheBehavior.viewerProtocolPolicy: "allow-all"` — the governance setting always wins.

### As a Platform Team Member

1. Create a `CloudFrontConfig` CR with your organization's compliance policies
2. Decide which fields are mandatory (compliance / security gates) and which are defaults (provide guidance but allow override)
3. Deploy the profile to the `kro-system` namespace
4. Share the profile name with platform users
5. Use `syncedLabels` and `syncedAnnotations` to automatically label resources by profile

Platform teams can have multiple profiles deployed in parallel. Developers choose the right profile for their use case via `configRef`.

## Mutual Exclusion Rule

A field cannot be set in both `mandatory` and `defaults` simultaneously. If you try:

```yaml
spec:
  mandatory:
    viewerProtocolPolicy: "https-only"
  defaults:
    viewerProtocolPolicy: "redirect-to-https"  # ERROR: Cannot set in both tiers
```

API validation will reject this configuration. Decide: Is the field a governance requirement (mandatory) or a sensible default (defaults)? Set it in one tier only.

## Field Semantics

### Viewer Protocol Policy

- `mandatory: "https-only"` → All distributions must refuse HTTP traffic
- `defaults: "redirect-to-https"` → HTTP requests are redirected to HTTPS (developer can override)
- `""` → Not enforced; developer choice

### Minimum Protocol Version

- `mandatory: "TLSv1.2_2021"` → All distributions must support at least TLS 1.2 (2021-07-02 certificates)
- `defaults: "TLSv1.2_2021"` → Use this TLS version if distribution doesn't specify
- `""` → Not enforced

### Logging

- `mandatory: { loggingEnabled: true, loggingBucket: "org-logs.s3.amazonaws.com" }` → All distributions log access
- `defaults: { loggingEnabled: false }` → No logging unless developer enables it
- If only `loggingEnabled: true` is mandatory but `loggingBucket` is not, logs go to a default bucket or require the developer to specify one

### Web ACL Requirement

- `mandatory: true` → All distributions must have a WAF WebACL; creation is blocked if `webACLID` is empty
- `defaults: false` → WAF is optional (developer can attach it if needed)

### OAC Signing Behavior

- `mandatory: "always"` → All origin access controls always sign requests; independent of the `no-override` setting on individual OAC instances
- `defaults: "always"` → Use `always` signing if OAC spec doesn't specify
- `""` → Not enforced; developer chooses per OAC

## Naming Template Tokens

When using `namingTemplate`, the following tokens are available:

| Token | Example | Notes |
|---|---|---|
| `{name}` | `my-cache-policy` | The resource's Kubernetes name |
| `{namespace}` | `app-team` | The resource's Kubernetes namespace |
| `{configRef}` | `general-policy` | The selected profile name |
| `{account_id}` | `123456789012` | AWS account ID (from governance) |
| `{region}` | `us-east-1` | AWS region (from governance) |
| `{tag.KEY}` | `prod`, `api` | Any tag key; missing keys become empty string |

Example template: `"{namespace}-{configRef}-{tag.environment}-{name}"` produces names like `app-team-general-policy-production-my-policy`.

Distribution has no provider `name` field and does not use naming — it is identified by CloudFront's assigned distribution ID.

## Troubleshooting

### Can't Override Governance Setting

If a field is in `mandatory`, it cannot be overridden at the resource level. Only fields in `defaults` (and those without governance settings) can be overridden. Contact your platform team if you need a different governance setting.

### Naming Template Has Unresolved Tokens

Check `status.namingStatus`. If `invalid-unresolved-tokens`, the template references a tag or token that doesn't exist. For example, if the template uses `{tag.environment}` but the resource has no `environment` tag, the template cannot resolve. Add the missing tag or fix the template.

### Resource Creation Blocked by WAF Gate

If `CloudFrontConfig` has `mandatory.webACLRequired: true` and you try to create a distribution without a `webACLID`, creation is blocked. Add a WAF WebACL ARN to your distribution's `spec.webACLID`.

---

For more on CloudFront governance, see [CloudFront resources](./index.md).
