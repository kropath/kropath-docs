---
title: CloudFrontVPCOrigin — Private VPC Origin
description: "`CloudFrontVPCOrigin` registers a private AWS resource (ALB, NLB, or EC2 instance) as a CloudFront origin, allowing CloudFront to serve content from your VPC without exposing the resource to the public internet."
doc_type: reference
---
# CloudFrontVPCOrigin — Private VPC Origin

`CloudFrontVPCOrigin` registers a private AWS resource (ALB, NLB, or EC2 instance) as a CloudFront origin, allowing CloudFront to serve content from your VPC without exposing the resource to the public internet.

## Core Use Case

Use `CloudFrontVPCOrigin` when you want CloudFront to fetch content from a private application inside your VPC. CloudFront accesses the resource through a managed VPC attachment, keeping your origin off the public internet.

## Prerequisites

- A private endpoint in your VPC: an Application Load Balancer (ALB), Network Load Balancer (NLB), or EC2 instance
- The endpoint's ARN (e.g., `arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb/abc123`)
- The endpoint must be reachable from CloudFront's managed VPC connection (this approval is handled out-of-band by AWS)
- A `CloudFrontConfig` profile (defaults to `general-policy`)

## Configuration Fields

### Required Fields

| Field | Type | Purpose |
|---|---|---|
| `arn` | string | ARN of the VPC endpoint (ALB, NLB, or EC2 instance) |

### Common Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `CloudFrontConfig` governance profile to apply |
| `httpPort` | integer | `80` | HTTP port on the VPC endpoint (1–65535) |
| `httpsPort` | integer | `443` | HTTPS port on the VPC endpoint (1–65535) |
| `originProtocolPolicy` | string | `""` | How CloudFront connects to the origin: `"http-only"`, `"https-only"`, or `"match-viewer"` (uses governance default if unset) |
| `originSSLProtocols` | array | `[]` | Allowed TLS versions for the origin connection, e.g., `["TLSv1.2"]` |
| `nameOverride` | string | `""` | Bypasses the naming template when set (advanced) |
| `deletionPolicy` | string | `"retain"` | When the resource is deleted: `"retain"` (keep the CloudFront origin) or `"delete"` (remove it) |
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The resolved cloud resource name (after naming template substitution) |
| `namingStatus` | string | Naming validation status: `"valid"` or `"invalid-unresolved-tokens"` |
| `id` | string | CloudFront-assigned VPC origin ID (consumed by `CloudFrontDistribution` origins) |
| `conditions[]` | array | Reconciliation status (Ready, errors) |

## Origin Protocol Policy — Governance

The `originProtocolPolicy` field is governable via `CloudFrontConfig`. If the governance profile sets a **mandatory** origin protocol policy, it overrides your resource spec:

- **Mandatory wins** — If `CloudFrontConfig.spec.mandatory.vpcOriginProtocolPolicy: "https-only"`, all VPC origins must use HTTPS-only, regardless of what you set in `spec.originProtocolPolicy`.
- **Defaults apply** — If nothing is mandatory and you don't specify a value, the governance default applies (typically `"https-only"`).
- **Resource spec wins** — If only a default is set, you can override it in your spec.

## Example: Register an ALB Origin

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontVPCOrigin
metadata:
  name: web-app-origin
  namespace: cdn-prod
spec:
  configRef: general-policy
  arn: arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/web-alb/abc123def456
  httpPort: 80
  httpsPort: 443
  originProtocolPolicy: "https-only"
  originSSLProtocols:
    - TLSv1.2
    - TLSv1.3
  tags:
    application: web-app
    tier: backend
```

After reconciliation:

```yaml
status:
  resourceName: cdn-prod-web-app-origin
  namingStatus: valid
  id: vo-abc123  # CloudFront-assigned VPC origin ID
  conditions:
    - type: Ready
      status: "True"
```

The VPC origin ID (`vo-abc123`) can now be referenced in a `CloudFrontDistribution` resource to serve content from this private ALB.

## Custom Ports and Protocols

You can customize the ports CloudFront uses to connect to your origin:

```yaml
spec:
  arn: arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/network/my-nlb/abc123
  httpPort: 8080    # Custom HTTP port on the NLB
  httpsPort: 8443   # Custom HTTPS port on the NLB
  originProtocolPolicy: "https-only"
  originSSLProtocols:
    - TLSv1.2
```

## TLS Configuration

Use `originSSLProtocols` to specify which TLS versions your private origin supports. If you don't specify a value, CloudFront's default is applied:

```yaml
spec:
  originSSLProtocols:
    - TLSv1.2
    - TLSv1.3
```

Supported values: `"TLSv1.0"`, `"TLSv1.1"`, `"TLSv1.2"`, `"TLSv1.3"` (exact format as shown).

## Resource Naming

VPC origins use a naming template to generate their cloud resource name. The default template is `{namespace}-{name}` (where `{name}` resolves from `metadata.name`):

```
namespace: cdn-prod
metadata.name: web-alb-origin
expected resourceName: cdn-prod-web-alb-origin  (from namespace + metadata.name)
```

To override the name entirely, use `nameOverride`:

```yaml
spec:
  nameOverride: prod-web-origin  # Skips naming template
```

If the naming template includes tokens that don't resolve (e.g., `{tag.environment}` but no `environment` tag), the resource reports `status.namingStatus: invalid-unresolved-tokens`.


## Deletion Behavior

- **`deletionPolicy: "retain"`** (default) — The CloudFront VPC origin persists in AWS when the Kubernetes resource is deleted
- **`deletionPolicy: "delete"`** — The CloudFront VPC origin is removed from AWS when the Kubernetes resource is deleted

For most cases, retain is safer (you keep the origin configuration if you temporarily remove the Kubernetes resource).

## Tags and Labels

VPC origins support AWS tags and Kubernetes labels. Use `syncedLabels` to automatically apply both:

```yaml
spec:
  tags:
    application: web-app
    owner: platform-team
  syncedLabels:
    environment: production
    tier: backend
```

After reconciliation, the VPC origin in AWS receives both the `tags` entries AND the `syncedLabels` entries (prefixed with `aws.kropath.run/`).

Governance tags (from `CloudFrontConfig`) are automatically merged with your tags; governance mandatory tags cannot be overridden.

## Troubleshooting

### VPC Origin Cannot Connect

If the VPC origin is created but CloudFront cannot connect to your private endpoint:

1. Verify the endpoint ARN is correct: `arn:aws:elasticloadbalancing:region:account-id:loadbalancer/type/name/id`
2. Ensure the endpoint is in a supported region and reachable from CloudFront's managed VPC attachment
3. Check that CloudFront has approved access to your VPC out-of-band (contact AWS support if needed)
4. Verify the port configuration matches the port your application listens on

### Naming Template Cannot Resolve

If `status.namingStatus: invalid-unresolved-tokens`, the naming template references a token that doesn't exist:

- Check that any `{tag.KEY}` references in the template match tags you've applied
- Check that `{namespace}` and `{name}` are present (they always exist)
- Add missing tags and reconcile again

## Related Resources

- [CloudFrontConfig](./cloudfrontconfig.md) — Set governance policies and defaults for VPC origins
- [CloudFrontDistribution](./cloudfrontdistribution.md) — Create a CDN distribution using your VPC origins
- [CloudFront resources](./index.md) — Overview of all CloudFront resource types
