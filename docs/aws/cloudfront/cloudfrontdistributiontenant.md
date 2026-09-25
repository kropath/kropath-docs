# CloudFrontDistributionTenant — Multi-Tenant Subscriber

`CloudFrontDistributionTenant` attaches a single customer (tenant) to a multi-tenant CloudFront distribution. Each tenant has independent domain names, certificates, geo-restrictions, and WAF policies.

## Core Use Case

Use `CloudFrontDistributionTenant` when you operate a multi-tenant SaaS platform and want to give each customer their own CloudFront configuration without creating separate distributions. Each tenant shares the same distribution infrastructure but maintains independent domains, security policies, and certificates.

## Prerequisites

- A multi-tenant `CloudFrontDistribution` (with `connectionMode: dedicated-tenant-distribution`)
- A `CloudFrontConnectionGroup` (defines the shared routing endpoint)
- At least one domain name for the tenant (FQDN)
- A certificate for those domains (either bring-your-own ACM or request CloudFront-managed)
- A `CloudFrontConfig` profile (defaults to `general-policy`)

## Configuration Fields

### Required Fields

| Field | Type | Purpose |
|---|---|---|
| `domains[]` | array | At least one fully qualified domain name (FQDN) for this tenant (e.g., `["acme.example.com", "www.acme.example.com"]`) |
| `distributionID` or `distributionRef` | string | The multi-tenant distribution this tenant attaches to |
| `connectionGroupID` or `connectionGroupRef` | string | The connection group routing this tenant |

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `CloudFrontConfig` governance profile to apply |

### Certificate Configuration (Choose One)

| Field | Type | Purpose |
|---|---|---|
| `customizations.certificate.arn` | string | ARN of an existing ACM certificate for this tenant's domains (bring-your-own) |
| `managedCertificateRequest.primaryDomainName` | string | Primary domain for which CloudFront should request and manage an ACM certificate |
| `managedCertificateRequest.validationTokenHost` | string | (Optional) DNS validation token host for the managed certificate |
| `managedCertificateRequest.certificateTransparencyLoggingPreference` | string | (Optional) CT logging preference: `"enabled"` or `"disabled"` |

Use **either** `customizations.certificate.arn` (bring your own certificate) **or** `managedCertificateRequest` (let CloudFront manage it). Using both is an error.

### Geo-Restriction and WAF

| Field | Type | Default | Purpose |
|---|---|---|---|
| `customizations.geoRestrictions.restrictionType` | string | `""` | Geographic restriction: `"none"`, `"whitelist"` (allow only listed countries), or `"blacklist"` (block listed countries) |
| `customizations.geoRestrictions.locations[]` | array | `[]` | ISO 3166-1 alpha-2 country codes (e.g., `["US", "CA", "GB"]`); used with whitelist/blacklist |
| `customizations.webACL.arn` | string | `""` | ARN of a WAF WebACL to protect this tenant (required if governance sets `webACLRequired: true`) |
| `customizations.webACL.action` | string | `""` | WAF action override: `"block"` or `"count"` (optional; defaults to CloudFront behavior) |

### Tenant Parameters

| Field | Type | Purpose |
|---|---|---|
| `parameters[]` | array | Custom name/value pairs for parameters defined in the parent distribution's `tenantConfig.parameterDefinitions` |

### Other Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `enabled` | boolean | `true` | Whether this tenant actively serves traffic |
| `nameOverride` | string | `""` | Bypasses the naming template when set (advanced) |
| `deletionPolicy` | string | `"retain"` | When the resource is deleted: `"retain"` (keep the tenant) or `"delete"` (remove it) |
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The resolved cloud resource name (after naming template substitution) |
| `namingStatus` | string | Naming validation status: `"valid"` or `"invalid-unresolved-tokens"` |
| `id` | string | CloudFront-assigned tenant ID (for reference and debugging) |
| `conditions[]` | array | Reconciliation status (Ready, errors) |

## Example: Attach a Tenant to a Multi-Tenant Distribution

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontDistributionTenant
metadata:
  name: acme-tenant
  namespace: saas-platform
spec:
  configRef: general-policy
  domains:
    - domain: acme.example.com
    - domain: www.acme.example.com
  distributionRef: shared-cdn          # Name of CloudFrontDistribution CR
  connectionGroupRef: tenant-routing   # Name of CloudFrontConnectionGroup CR
  customizations:
    certificate:
      arn: arn:aws:acm:us-east-1:123456789012:certificate/abc123
    geoRestrictions:
      restrictionType: whitelist
      locations:
        - US
        - CA
    webACL:
      arn: arn:aws:wafv2:us-east-1:123456789012:global/webacl/tenant-acl/abc123
  tags:
    customer: acme-inc
    tier: premium
```

After reconciliation:

```yaml
status:
  resourceName: saas-platform-acme-tenant
  namingStatus: valid
  id: dt-abc123
  conditions:
    - type: Ready
      status: "True"
```

## Certificate Management

### Bring Your Own Certificate

If you already have an ACM certificate for the tenant's domains, provide its ARN:

```yaml
spec:
  customizations:
    certificate:
      arn: arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012
```

The certificate must cover all domains in `spec.domains[]`.

### CloudFront-Managed Certificate

Let CloudFront request and manage an ACM certificate for you:

```yaml
spec:
  managedCertificateRequest:
    primaryDomainName: acme.example.com
    validationTokenHost: cloudfront
```

CloudFront will request an ACM certificate for the primary domain and any other domains you've specified in `spec.domains[]`. DNS validation is handled through the token host you specify.

**Note:** You cannot use both methods. Specifying both `customizations.certificate.arn` and `managedCertificateRequest` causes the resource to be rejected.

## Geo-Restriction

Apply geographic restrictions to this tenant independently of the distribution-level geo-restriction:

```yaml
spec:
  customizations:
    geoRestrictions:
      restrictionType: whitelist  # Allow only these countries
      locations:
        - US
        - CA
        - GB
```

Options:

- **`"whitelist"`** — Serve content only to viewers in listed countries
- **`"blacklist"`** — Block viewers in listed countries
- **`"none"`** — No geographic restriction (default)

If your `CloudFrontConfig` sets `mandatory.geoRestrictionType`, it overrides the tenant's setting.

Use ISO 3166-1 alpha-2 country codes (e.g., `US`, `FR`, `JP`).

## WAF (Web Application Firewall)

Protect this tenant's traffic with a WAF WebACL:

```yaml
spec:
  customizations:
    webACL:
      arn: arn:aws:wafv2:us-east-1:123456789012:global/webacl/tenant-protection/abc123
```

If your `CloudFrontConfig` sets `mandatory.webACLRequired: true`, you **must** provide a WebACL ARN, or creation is blocked.

## Tenant Parameters

If the parent distribution defines custom parameters (via `tenantConfig.parameterDefinitions`), pass values for those parameters:

```yaml
spec:
  parameters:
    - name: siteTitle
      value: "ACME Inc"
    - name: supportEmail
      value: "support@acme.example.com"
```

## Resource Naming

Tenants use a naming template (default `{namespace}-{name}`) to generate the cloud resource name:

```
namespace: saas-platform
metadata.name: acme-tenant
expected resourceName: saas-platform-acme-tenant  (from namespace + metadata.name)
```

To override the name entirely, use `nameOverride`:

```yaml
spec:
  nameOverride: acme-inc-tenant  # Skips naming template
```

**Important:** Once created, the tenant's name is immutable. Changing the naming template or `nameOverride` after creation will cause reconciliation to fail. If you need to rename a tenant, delete and recreate it.

## Using Sibling References

Instead of providing raw IDs, you can reference the distribution and connection group by name:

```yaml
spec:
  distributionRef: shared-cdn          # Name of CloudFrontDistribution CR
  connectionGroupRef: tenant-routing   # Name of CloudFrontConnectionGroup CR
```

These references are resolved to their CloudFront-assigned IDs at reconciliation time. If both `distributionRef` and `distributionID` are set, the `ref` takes precedence.

## Enabled and Disabled Tenants

- **`enabled: true`** (default) — The tenant actively serves traffic
- **`enabled: false`** — The tenant is disabled (existing traffic stops)

You can toggle this at any time after creation.

## Deletion Behavior

- **`deletionPolicy: "retain"`** (default) — The CloudFront tenant persists when the Kubernetes resource is deleted
- **`deletionPolicy: "delete"`** — The CloudFront tenant is removed when the Kubernetes resource is deleted

For most cases, retain is safer (you keep the tenant configuration if you temporarily remove the Kubernetes resource).

## Governance Cascade

The tenant inherits some governance from your `CloudFrontConfig`:

- **`geoRestrictionType`** — If set as mandatory, overrides the tenant's `customizations.geoRestrictions.restrictionType`
- **`webACLRequired`** — If set as mandatory, blocks creation unless `customizations.webACL.arn` is provided
- **Naming, tags, labels, annotations** — Follow the standard three-tier cascade (mandatory > spec > defaults)

## Tags and Labels

Tenants support AWS tags and Kubernetes labels. Use `syncedLabels` to automatically apply both:

```yaml
spec:
  tags:
    customer: acme-inc
    tier: premium
    support-level: enterprise
  syncedLabels:
    environment: production
    tenant-id: acme
```

After reconciliation, the tenant in AWS receives both the `tags` entries AND the `syncedLabels` entries (prefixed with `aws.kropath.run/`).

Governance tags (from `CloudFrontConfig`) are automatically merged with your tags; governance mandatory tags cannot be overridden.

## Multi-Tenant Distribution Setup

A typical multi-tenant SaaS setup:

```
CloudFrontDistribution (multi-tenant mode, connectionMode: dedicated-tenant-distribution)
└── CloudFrontConnectionGroup (shared routing & Anycast IPs)
    ├── CloudFrontDistributionTenant (customer-a)
    ├── CloudFrontDistributionTenant (customer-b)
    └── CloudFrontDistributionTenant (customer-c)
```

Each tenant has:
- Independent domains (customer-a.example.com, customer-b.example.com, etc.)
- Independent certificates (each manages their own or requests CloudFront-managed)
- Independent geo-restrictions and WAF policies
- Independent enabled/disabled state

All tenants share the same underlying distribution and connection group infrastructure.

## Troubleshooting

### Certificate Source Must Be Mutual Exclusive

If you specify both `customizations.certificate.arn` and `managedCertificateRequest`, the resource is rejected:

```
Error: certificate sources are mutually exclusive: choose either
  customizations.certificate.arn (bring your own) or
  managedCertificateRequest (managed by CloudFront), not both
```

**Solution:** Use only one certificate source per tenant.

### WAF Required but Not Provided

If `CloudFrontConfig` has `mandatory.webACLRequired: true` and you don't provide a WebACL ARN:

```
Error: WAF WebACL is required for this tenant
```

**Solution:** Provide a WAF WebACL ARN in `customizations.webACL.arn`, or change the governance policy.

### Geo-Restriction Override

If both the distribution and this tenant have geo-restrictions, the tenant's setting is applied to this tenant's traffic specifically.

If `CloudFrontConfig.mandatory.geoRestrictionType` is set, it takes precedence and cannot be overridden at the tenant level.

### Distribution or Connection Group Not Found

If `distributionRef` or `connectionGroupRef` points to a resource that doesn't exist:

```
Error: referenced distribution 'does-not-exist' not found
```

**Solution:** Verify the reference name matches an existing `CloudFrontDistribution` or `CloudFrontConnectionGroup` in the same namespace.

## Related Resources

- [CloudFrontConfig](./cloudfrontconfig.md) — Set governance policies and defaults for tenants
- [CloudFrontConnectionGroup](./cloudfrontconnectiongroup.md) — The routing endpoint this tenant connects through
- [CloudFrontDistribution](./cloudfrontdistribution.md) — The multi-tenant distribution (requires `connectionMode: dedicated-tenant-distribution`)
- [CloudFront resources](./index.md) — Overview of all CloudFront resource types
