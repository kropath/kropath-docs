# CloudFrontOriginAccessControl — Restrict Origin Access

`CloudFrontOriginAccessControl` (OAC) restricts access to your origin so only CloudFront can reach it. Supported origin types: S3, MediaStore, Lambda, and MediaPackageV2. Kropath handles SigV4 request signing automatically.

## Core Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `CloudFrontConfig` governance profile to apply |
| `name` | string | `""` | Human-readable OAC name (shown in CloudFront console) |
| `description` | string | `""` | Free-text description of this OAC's purpose |
| `originAccessControlOriginType` | string | required | Origin type: `s3`, `mediastore`, `lambda`, or `mediapackagev2` |
| `signingBehavior` | string | `""` | Request signing: `"always"`, `"never"`, `"no-override"`, or `""` (use governance default) |
| `signingProtocol` | string | `"sigv4"` | Only SigV4 is supported |
| `nameOverride` | string | `""` | Bypass the naming template and set the OAC name directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` (keep OAC in AWS) or `"delete"` (remove it) |
| `syncedLabels` | map | `{}` | Kubernetes labels (no AWS tags for OAC) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations |

## Status Outputs

| Field | Type | Purpose |
|---|---|---|
| `id` | string | CloudFront-assigned OAC ID (referenced by distributions) |
| `resourceName` | string | Effective OAC name after naming template substitution |
| `namingStatus` | string | `"valid"` if name is ready, `"invalid-unresolved-tokens"` if template has unresolved tokens |
| `conditions[]` | array | Reconciliation status |

## Governance Cascade

Only `signingBehavior` is governable:
- `mandatory.oacSigningBehavior: "always"` → All OACs always sign requests
- `defaults.oacSigningBehavior: "always"` → Use `always` if not specified
- `""` → Developer choice

## Examples

### Basic S3 Access Control

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontOriginAccessControl
metadata:
  name: s3-access
  namespace: app-team
spec:
  configRef: general-policy
  name: s3-private-access
  description: "Restrict S3 bucket to CloudFront only"
  originAccessControlOriginType: s3
  signingBehavior: always
  signingProtocol: sigv4
```

### MediaStore OAC

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontOriginAccessControl
metadata:
  name: mediastore-access
  namespace: media-team
spec:
  configRef: general-policy
  name: mediastore-restricted
  originAccessControlOriginType: mediastore
  signingBehavior: always
```

### Lambda Origin Protection

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontOriginAccessControl
metadata:
  name: lambda-access
  namespace: serverless
spec:
  configRef: general-policy
  name: lambda-function-access
  originAccessControlOriginType: lambda
  signingBehavior: always
```

## Usage in Distributions

Reference the OAC in a distribution by name:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontDistribution
metadata:
  name: secure-app
  namespace: app-team
spec:
  configRef: general-policy
  origins:
    - id: s3-origin
      domainName: my-bucket.s3.us-east-1.amazonaws.com
      originAccessControlRef: s3-access  # Name of the OAC resource
  defaultCacheBehavior:
    targetOriginID: s3-origin
    viewerProtocolPolicy: https-only
    cachePolicyID: 658327ea-f89d-4fab-a63d-7e88639e58f6
```

Kropath resolves the OAC name to its CloudFront-assigned ID and wires it into the distribution.

## Naming

OAC has a `name` field and uses the naming convention. Default template: `{namespace}-{name}`.

Example: Resource named `s3-access` in namespace `app-team` produces name `app-team-s3-access` (unless overridden).

**Available tokens:** `{name}`, `{namespace}`, `{configRef}`, `{account_id}`, `{region}`, `{tag.KEY}`

## S3 Bucket Policy Setup

After creating the OAC, configure your S3 bucket policy to allow only CloudFront:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudfront.amazonaws.com"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-bucket/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::<account_id>:distribution/<distribution_id>"
        }
      }
    }
  ]
}
```

Replace `<account_id>` with your AWS account ID and `<distribution_id>` with the distribution's ID from `status.id`.

## Signing Behavior

| Value | Behavior |
|---|---|
| `always` | CloudFront always signs requests to the origin with SigV4 |
| `never` | CloudFront never signs requests (origin does not require it) |
| `no-override` | Individual OAC instances can choose, but this OAC defaults to `always` |

Most use cases require `always` to enforce that only signed (CloudFront) requests reach the origin.

## Troubleshooting

### S3 Access Denied

- Ensure the S3 bucket policy allows the CloudFront service principal
- Verify the OAC ID in the bucket policy matches `status.id`
- Check that the distribution's origin references the OAC via `originAccessControlRef` or ID

### Naming Template Unresolved

If `status.namingStatus: invalid-unresolved-tokens`, the template references a tag or token that doesn't exist. Fix the template or ensure required tags are present.

---

See [CloudFrontDistribution](./cloudfrontdistribution.md) for usage examples.
