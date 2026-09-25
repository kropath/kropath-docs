# CloudFrontConnectionGroup — Multi-Tenant Routing Endpoint

`CloudFrontConnectionGroup` defines a shared routing endpoint and static IP configuration for multi-tenant CloudFront distributions. A connection group is one half of the multi-tenant model; the other half is `CloudFrontDistributionTenant` (which attaches individual tenants to the group).

## Core Use Case

Use `CloudFrontConnectionGroup` to set up shared infrastructure for a multi-tenant SaaS platform. Each connection group has static Anycast IPs and a DNS name; multiple `CloudFrontDistributionTenant` resources attach their individual customers to a single connection group.

## Prerequisites

- A multi-tenant `CloudFrontDistribution` (with `connectionMode: dedicated-tenant-distribution`)
- A `CloudFrontConfig` profile (defaults to `general-policy`)
- (Optional) An Anycast static IP list ID if you need fixed IPs for your tenants

## Configuration Fields

### Common Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `CloudFrontConfig` governance profile to apply |
| `name` | string | `""` | Friendly name for this connection group (immutable after creation) |
| `enabled` | boolean | `true` | Whether the connection group actively serves traffic |
| `ipv6Enabled` | boolean | `true` | Enable IPv6 for tenants (immutable after creation) |
| `anycastIPListID` | string | `""` | (Optional) CloudFront Anycast static IP list ID for fixed IPs |
| `nameOverride` | string | `""` | Bypasses the naming template when set (advanced) |
| `deletionPolicy` | string | `"retain"` | When the resource is deleted: `"retain"` (keep the group) or `"delete"` (remove it) |
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The resolved cloud resource name (after naming template substitution) |
| `namingStatus` | string | Naming validation status: `"valid"` or `"invalid-unresolved-tokens"` |
| `id` | string | CloudFront-assigned connection group ID (referenced by distribution tenants) |
| `routingEndpoint` | string | DNS name for the routing endpoint (e.g., `d123abc.cloudfront.net`) — point your tenants' DNS here |
| `isDefault` | boolean | Whether this is the account-level default connection group (read-only; set by CloudFront) |
| `conditions[]` | array | Reconciliation status (Ready, errors) |

## Example: Create a Connection Group

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontConnectionGroup
metadata:
  name: tenant-routing
  namespace: saas-platform
spec:
  configRef: general-policy
  name: saas-prod-routing
  enabled: true
  ipv6Enabled: true
  tags:
    platform: saas
    environment: production
  syncedLabels:
    tier: edge
```

After reconciliation:

```yaml
status:
  resourceName: saas-platform-tenant-routing
  namingStatus: valid
  id: cg-abc123          # CloudFront-assigned connection group ID
  routingEndpoint: d123abc456.cloudfront.net  # DNS name
  isDefault: false
  conditions:
    - type: Ready
      status: "True"
```

Tenants reference this group by name (`tenant-routing`) or by ID (`cg-abc123`) in their own resource definitions.

## Enabled and IPv6

- **`enabled: true`** (default) — The connection group actively routes traffic to attached tenants
- **`enabled: false`** — The connection group is inactive (existing tenants stop serving traffic)
- **`ipv6Enabled: true`** (default) — Tenants can be reached over IPv6
- **`ipv6Enabled: false`** — Only IPv4 (no IPv6 support for tenants)

Both fields are mutable — you can enable/disable IPv6 or the group itself after creation.

## Static Anycast IPs (Advanced)

If you need fixed IP addresses for your connection group (e.g., for IP allowlists), use `anycastIPListID`:

```yaml
spec:
  anycastIPListID: aipl-abc123  # CloudFront Anycast static IP list ID
```

CloudFront assigns a static Anycast IP list to the connection group, and all traffic from this group uses those fixed IPs.

## Resource Naming

Connection groups use a naming template (default `{namespace}-{name}`) to generate the cloud resource name:

```
namespace: saas-platform
metadata.name: tenant-routing
spec.name: saas-prod-routing
expected resourceName: saas-platform-tenant-routing  (from naming template)
```

To override the name entirely, use `nameOverride`:

```yaml
spec:
  nameOverride: prod-shared-routing  # Skips naming template
```

**Important:** Once created, the connection group's name is immutable. Changing the naming template or `nameOverride` after creation will cause reconciliation to fail (CloudFront blocks name changes). If you need to rename a connection group, delete and recreate it.

## Using Connection Groups in Distributions

Tenants attach to a multi-tenant distribution and reference a connection group:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontDistributionTenant
metadata:
  name: acme-tenant
  namespace: saas-platform
spec:
  domains:
    - acme.example.com
  connectionGroupRef: tenant-routing  # Name of CloudFrontConnectionGroup CR
  distributionRef: shared-cdn
  # ... rest of tenant config
```

When multiple tenants reference the same connection group, they share the same routing endpoint and Anycast IPs (if configured).

## Deletion and Retention

- **`deletionPolicy: "retain"`** (default) — The CloudFront connection group persists when the Kubernetes resource is deleted
- **`deletionPolicy: "delete"`** — The CloudFront connection group is removed when the Kubernetes resource is deleted

**Caution:** Deleting a connection group that still has attached tenants fails on AWS. Set all tenants to use a different group first, or delete the tenants before attempting to delete the group. The `deletionPolicy: "retain"` default prevents accidental deletion of active infrastructure.

## Tags and Labels

Connection groups support AWS tags and Kubernetes labels. Use `syncedLabels` to automatically apply both:

```yaml
spec:
  tags:
    platform: saas
    owner: infrastructure-team
  syncedLabels:
    environment: production
    tier: edge
```

After reconciliation, the connection group in AWS receives both the `tags` entries AND the `syncedLabels` entries (prefixed with `aws.kropath.run/`).

Governance tags (from `CloudFrontConfig`) are automatically merged with your tags; governance mandatory tags cannot be overridden.

## Multi-Tenant Architecture

In a multi-tenant setup, one connection group serves multiple `CloudFrontDistributionTenant` resources:

```
CloudFrontConnectionGroup (shared routing, Anycast IPs)
├── CloudFrontDistributionTenant (customer-a)
│   ├── domains: [a.example.com]
│   ├── certificate: (customer-a's ACM certificate)
│   └── geoRestrictions: (customer-a's restrictions)
│
├── CloudFrontDistributionTenant (customer-b)
│   ├── domains: [b.example.com]
│   ├── certificate: (customer-b's ACM certificate)
│   └── geoRestrictions: (customer-b's restrictions)
│
└── CloudFrontDistributionTenant (customer-c)
    ├── domains: [c.example.com]
    ├── certificate: (customer-c's managed certificate)
    └── geoRestrictions: (customer-c's restrictions)
```

All three customers route through the same connection group, but each has independent domains, certificates, and policies.

## Troubleshooting

### Name Cannot Change After Creation

If you attempt to update `spec.name`, `nameOverride`, or the naming template after creation, reconciliation fails with an immutability error:

```
Error: spec.name: Invalid value: "new-name": field is immutable
```

**Solution:** Connection group names are immutable in CloudFront. Delete the connection group and recreate it with the desired name, or redeploy all tenants to use a new group.

### Naming Template Cannot Resolve

If `status.namingStatus: invalid-unresolved-tokens`, the naming template references a token that doesn't exist:

- Check that any `{tag.KEY}` references match tags you've applied
- Verify that `{namespace}` and `{name}` are present (they always exist)
- Add missing tags and reconcile again

### Deletion Fails (Tenants Still Attached)

If you try to delete a connection group that still has active tenants, the deletion fails:

```
Error: cannot delete connection group with active tenants
```

**Solution:** Delete all tenants that reference this group first, then delete the group. Or switch all tenants to use a different connection group.

## Related Resources

- [CloudFrontConfig](./cloudfrontconfig.md) — Set governance policies and defaults for connection groups
- [CloudFrontDistributionTenant](./cloudfrontdistributiontenant.md) — Attach individual tenants to this connection group
- [CloudFrontDistribution](./cloudfrontdistribution.md) — Create a multi-tenant distribution (requires `connectionMode: dedicated-tenant-distribution`)
- [CloudFront resources](./index.md) — Overview of all CloudFront resource types
