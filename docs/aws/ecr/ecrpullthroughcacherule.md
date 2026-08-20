# ECRPullThroughCacheRule — Transparent Image Caching from Upstream Registries

The `ECRPullThroughCacheRule` resource enables transparent caching of container images from upstream public registries (Docker Hub, ECR Public, GitHub Container Registry, Quay, etc.) into your private ECR. When you pull an image that matches a cache rule, ECR automatically fetches it from the upstream registry and caches it locally for future pulls.

## Use Cases

- **Compliance:** Cache images in your private registry for regulatory or security auditing
- **Performance:** Eliminate repeated pulls from upstream registries; reduce bandwidth costs
- **Availability:** Reduce dependency on upstream registry availability
- **Image scanning:** Run vulnerability scanning on cached images before they're deployed
- **Cost optimization:** Upstream registries may charge per pull; caching reduces those costs

## Core Fields

### Rule Identity

| Field | Type | Required | Immutable | Purpose |
|---|---|---|---|---|
| `ecrRepositoryPrefix` | string | Yes | Yes | Local ECR prefix for cached images (e.g. `"docker-hub"`, `"ecr-public"`). Use `"ROOT"` for a catch-all rule. |
| `upstreamRegistryURL` | string | Yes | Yes | URL of the upstream registry (e.g. `"registry-1.docker.io"`, `"public.ecr.aws"`, `"ghcr.io"`, `"quay.io"`). |
| `upstreamRegistry` | string | No | Yes | Enum name of the upstream registry (e.g. `"docker-hub"`, `"ecr-public"`, `"github-container-registry"`, `"quay"`). Optional; AWS infers from URL if not set. |
| `upstreamRepositoryPrefix` | string | No | Yes | Upstream namespace prefix to match (e.g. `"library"` for Docker Hub's public library). Defaults to `"ROOT"` (match all upstream repos). |

**Important:** `ecrRepositoryPrefix`, `upstreamRegistryURL`, `upstreamRegistry`, and `upstreamRepositoryPrefix` are immutable after creation. To change these, you must delete and recreate the rule.

### Authentication

| Field | Type | Default | Purpose |
|---|---|---|---|---|
| `credentialArn` | string | `""` | ARN of a Secrets Manager secret containing upstream registry credentials |
| `credentialRef` | string | `""` | Reference to resolve credential ARN (Phase 2 feature; currently not supported) |
| `customRoleArn` | string | `""` | IAM role ARN that ECR assumes for authentication (for AWS services or federated identity) |
| `customRoleRef` | string | `""` | Reference to resolve role ARN (Phase 2 feature; currently not supported) |

### Governance and Deletion

| Field | Type | Default | Purpose |
|---|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `ECRConfig` profile to apply (for tagging only) |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted: `"retain"` or `"delete"` |
| `tags` | map | `{}` | Kubernetes labels and AWS tags (K8s metadata only — pull-through rules don't support cloud tags) |
| `syncedLabels` | map | `{}` | Kubernetes labels synced to the rule (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

### Operational Fields

| Field | Type | Default | Purpose |
|---|---|---|---|---|
| `registryID` | string | `""` | AWS account ID. Empty uses the account where the controller runs. |

## Common Upstream Registries

### Docker Hub

Cache public images from Docker Hub:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: docker-hub
  namespace: kro-system
spec:
  ecrRepositoryPrefix: docker-hub
  upstreamRegistryURL: registry-1.docker.io
  upstreamRegistry: docker-hub
```

Usage: Pull `123456789012.dkr.ecr.us-east-1.amazonaws.com/docker-hub/library/ubuntu:latest` to cache Docker Hub's `library/ubuntu:latest`.

### ECR Public

Cache images from AWS's public registry:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: ecr-public
  namespace: kro-system
spec:
  ecrRepositoryPrefix: ecr-public
  upstreamRegistryURL: public.ecr.aws
  upstreamRegistry: ecr-public
```

Usage: Pull `123456789012.dkr.ecr.us-east-1.amazonaws.com/ecr-public/amazonlinux/amazonlinux:latest` to cache `public.ecr.aws/amazonlinux/amazonlinux:latest`.

### GitHub Container Registry

Cache images from GitHub Packages:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: ghcr
  namespace: kro-system
spec:
  ecrRepositoryPrefix: ghcr
  upstreamRegistryURL: ghcr.io
  upstreamRegistry: github-container-registry
```

Usage: Pull `123456789012.dkr.ecr.us-east-1.amazonaws.com/ghcr/myorg/myimage:latest` to cache `ghcr.io/myorg/myimage:latest`.

### Quay.io

Cache images from Quay:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: quay
  namespace: kro-system
spec:
  ecrRepositoryPrefix: quay
  upstreamRegistryURL: quay.io
  upstreamRegistry: quay
```

Usage: Pull `123456789012.dkr.ecr.us-east-1.amazonaws.com/quay/coreos/etcd:latest` to cache `quay.io/coreos/etcd:latest`.

## Complete Examples

### Basic Cache Rule (Public Registry)

Cache public images from Docker Hub without authentication:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: docker-hub
  namespace: kro-system
spec:
  ecrRepositoryPrefix: docker-hub
  upstreamRegistryURL: registry-1.docker.io
  upstreamRegistry: docker-hub
  deletionPolicy: retain
```

Result:
- Any pull of `<ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/docker-hub/*` is transparently proxied to Docker Hub
- Image is cached locally for future pulls

### Cache Specific Namespace

Cache only the `library` namespace from Docker Hub:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: docker-hub-library
  namespace: kro-system
spec:
  ecrRepositoryPrefix: docker-hub-library
  upstreamRegistryURL: registry-1.docker.io
  upstreamRegistry: docker-hub
  upstreamRepositoryPrefix: library
  deletionPolicy: retain
```

Result:
- Pulls of `<ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/docker-hub-library/*` proxy to `registry-1.docker.io/library/*`
- Attempts to cache from other namespaces (e.g., `myorg/myimage`) will fail

### Private Registry with Credentials

Cache images from a private registry that requires authentication:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: private-registry
  namespace: kro-system
spec:
  ecrRepositoryPrefix: private-registry
  upstreamRegistryURL: registry.example.com
  credentialArn: "arn:aws:secretsmanager:us-east-1:123456789012:secret:ecr-pullthroughcache/private-registry"
  deletionPolicy: retain
```

**Setup:** Store your upstream registry credentials in AWS Secrets Manager (not Kubernetes Secrets). The secret must contain `username` and `password` fields. ECR assumes an IAM role with permission to read from Secrets Manager, then uses those credentials to authenticate to the private registry. Update the `credentialArn` to point to your Secrets Manager secret ARN.

### ROOT Prefix (Catch-All Rule)

Cache all images from a registry under a single prefix:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: all-registries
  namespace: kro-system
spec:
  ecrRepositoryPrefix: ROOT
  upstreamRegistryURL: registry-1.docker.io
  upstreamRegistry: docker-hub
  deletionPolicy: retain
```

Result:
- Any pull of `<ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/library/ubuntu` proxies to `registry-1.docker.io/library/ubuntu`
- Any pull of `<ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/myorg/myimage` proxies to `registry-1.docker.io/myorg/myimage`
- Single rule handles all Docker Hub namespaces

## Key Behaviors

### Immutable Configuration

Once created, these fields cannot be changed:
- `ecrRepositoryPrefix`
- `upstreamRegistryURL`
- `upstreamRegistry`
- `upstreamRepositoryPrefix`
- `registryID`

To change any of these, delete the rule and create a new one.

### Automatic Repository Creation

When a pull matches a cache rule, ECR automatically creates the destination repository if it doesn't exist. If you have an `ECRRepositoryCreationTemplate` with a matching prefix, that template's encryption, tag mutability, and lifecycle policy settings are applied to the auto-created repository.

### Image Metadata Refresh

Image layers are cached locally for performance. Image metadata (e.g., the image manifest) is re-fetched from the upstream registry on each pull to ensure consistency between the cached layers and the upstream manifest. This prevents stale or mismatched image data after cached layers are pulled.

### Permissions Required

Your AWS account needs:
- `ecr:CreateRepository` (to create the destination repository on first cache hit)
- `ecr:PutImage` (to cache image layers)
- Upstream registry access credentials (if the registry requires authentication)

## Troubleshooting

### Pull Fails with "Repository Not Found"

Check:
1. The cache rule exists and is configured correctly
2. The image name matches the `ecrRepositoryPrefix` (e.g., pull from `docker-hub/library/ubuntu`, not just `library/ubuntu`)
3. You've authenticated to ECR (run `aws ecr get-login-password | docker login ...`)

### Pull Fails with "Unauthorized"

- **Public registry:** This error is unexpected. Check the upstream registry URL and authentication settings.
- **Private registry:** Verify the `credentialArn` points to a valid Secrets Manager secret with correct credentials.

### Can't Modify Rule After Creation

Immutable fields cannot be changed. If you need to change `ecrRepositoryPrefix` or `upstreamRegistryURL`, delete the rule and create a new one.

### Images Not Being Cached

Ensure:
1. The pull command uses the ECR URI (e.g., `123456789012.dkr.ecr.us-east-1.amazonaws.com/docker-hub/...`)
2. The image name matches a configured cache rule's `ecrRepositoryPrefix`
3. Your cluster has internet access to reach the upstream registry (if it's public)
