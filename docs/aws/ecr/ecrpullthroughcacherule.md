# ECRPullThroughCacheRule — Caching Public Container Images

The `ECRPullThroughCacheRule` resource sets up pull-through caching in AWS ECR. Pull-through caching transparently proxies container images from public registries (Docker Hub, GitHub Container Registry, Quay, etc.) into your private ECR, caching them for faster and more reliable access.

## When to Use Pull-Through Cache

- **Reduce dependency on public registries** — Air-gapped or intermittently connected environments
- **Improve image availability** — Cache frequently-used base images locally
- **Control security scanning** — Apply compliance scanning to cached images
- **Bandwidth optimization** — Multiple pulls from the same image pull from cache

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `ECRConfig` governance profile to apply (for tags/labels) |
| `deletionPolicy` | string | `"retain"` | Behavior when the rule is deleted: `"retain"` (safe) or `"delete"` |

### Cache Rule Identity (Immutable)

| Field | Type | Required | Purpose |
|---|---|---|---|
| `ecrRepositoryPrefix` | string | Yes | Local ECR prefix for cached images (e.g., `"docker-hub"`, `"ghcr"`, `"ROOT"` for catch-all) |
| `upstreamRegistryURL` | string | Yes | URL of the upstream registry (e.g., `"registry-1.docker.io"`, `"ghcr.io"`) |
| `upstreamRegistry` | string | No | Enum name (e.g., `"docker-hub"`, `"ecr-public"`, `"github-container-registry"`) |
| `upstreamRepositoryPrefix` | string | No | Filter images by upstream namespace (e.g., `"library"` for `library/*` images) |

### Authentication

| Field | Type | Default | Purpose |
|---|---|---|---|
| `credentialArn` | string | `""` | ARN of Secrets Manager secret with upstream registry credentials (for private registries) |
| `customRoleArn` | string | `""` | IAM role ARN for upstream authentication |

### Metadata

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | Kubernetes tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |
| `registryID` | string | `""` | AWS account ID; defaults to the cluster's account |

## Basic Examples

### Docker Hub Caching

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

**How it works:**

1. User pulls: `123456789012.dkr.ecr.us-east-1.amazonaws.com/docker-hub/nginx:latest`
2. ECR checks: Does `docker-hub/nginx:latest` exist locally?
3. If not: Fetches `nginx:latest` from Docker Hub (`registry-1.docker.io/library/nginx:latest`)
4. If yes: Returns from cache

### ECR Public Registry

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
  deletionPolicy: retain
```

**Result:** Cached images available as `123456789012.dkr.ecr.us-east-1.amazonaws.com/ecr-public/...`

### GitHub Container Registry

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
  deletionPolicy: retain
```

**Result:** Cached images available as `123456789012.dkr.ecr.us-east-1.amazonaws.com/ghcr/...`

### Quay.io

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
  deletionPolicy: retain
```

## Advanced Configuration

### Filtering by Upstream Namespace

Cache only images from a specific upstream namespace:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: docker-library
  namespace: kro-system
spec:
  ecrRepositoryPrefix: docker-library
  upstreamRegistryURL: registry-1.docker.io
  upstreamRegistry: docker-hub
  upstreamRepositoryPrefix: "library"  # Only cache official Docker images
  deletionPolicy: retain
```

**Caches:** `docker-library/nginx:latest` (from `library/nginx:latest`)

**Does NOT cache:** Images from other namespaces like `myrepo/custom-app:latest`

### ROOT Prefix (Catch-All)

Cache images from any upstream namespace under a single prefix:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: all-docker-hub
  namespace: kro-system
spec:
  ecrRepositoryPrefix: ROOT
  upstreamRegistryURL: registry-1.docker.io
  upstreamRegistry: docker-hub
  deletionPolicy: retain
```

**Caches all images:**
- `123456789012.dkr.ecr.us-east-1.amazonaws.com/library/nginx:latest`
- `123456789012.dkr.ecr.us-east-1.amazonaws.com/myrepo/custom-app:latest`
- `123456789012.dkr.ecr.us-east-1.amazonaws.com/...`

### Private Registry with Credentials

Cache images from a private container registry that requires authentication:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: private-registry
  namespace: kro-system
spec:
  ecrRepositoryPrefix: private
  upstreamRegistryURL: registry.company.com
  credentialArn: "arn:aws:secretsmanager:us-east-1:123456789012:secret:ecr-upstream-creds"
  deletionPolicy: retain
```

**Prerequisites:**

1. Create a Secrets Manager secret with upstream registry credentials:

   ```bash
   aws secretsmanager create-secret \
     --name ecr-upstream-creds \
     --secret-string '{"username":"user","password":"pass"}'
   ```

2. Grant ECR permission to access the secret (via IAM policy or resource policy)

## Immutable Fields

Once created, these fields **cannot be changed**:

- `ecrRepositoryPrefix`
- `upstreamRegistryURL`
- `upstreamRegistry`
- `upstreamRepositoryPrefix`
- `registryID`

**To change any of these:** Delete the rule and create a new one.

```bash
kubectl delete ecrpullthroughcacherule docker-hub
kubectl apply -f docker-hub-updated.yaml
```

## Complete Example: Multi-Registry Setup

```yaml
---
# Docker Hub official images
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: docker-official
  namespace: kro-system
spec:
  ecrRepositoryPrefix: docker
  upstreamRegistryURL: registry-1.docker.io
  upstreamRegistry: docker-hub
  upstreamRepositoryPrefix: "library"
  deletionPolicy: retain
  tags:
    source: docker-hub

---
# GitHub Container Registry
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: ghcr
  namespace: kro-system
spec:
  ecrRepositoryPrefix: ghcr
  upstreamRegistryURL: ghcr.io
  upstreamRegistry: github-container-registry
  deletionPolicy: retain
  tags:
    source: github

---
# ECR Public Registry
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: ecr-public
  namespace: kro-system
spec:
  ecrRepositoryPrefix: ecr-public
  upstreamRegistryURL: public.ecr.aws
  upstreamRegistry: ecr-public
  deletionPolicy: retain
  tags:
    source: aws

---
# Quay.io
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: quay
  namespace: kro-system
spec:
  ecrRepositoryPrefix: quay
  upstreamRegistryURL: quay.io
  upstreamRegistry: quay
  deletionPolicy: retain
  tags:
    source: quay
```

Users can now pull from any of these upstream registries via local ECR:

```bash
docker pull 123456789012.dkr.ecr.us-east-1.amazonaws.com/docker/nginx:latest
docker pull 123456789012.dkr.ecr.us-east-1.amazonaws.com/ghcr/my-org/my-app:v1.0
docker pull 123456789012.dkr.ecr.us-east-1.amazonaws.com/ecr-public/amazon/aws-cli:latest
docker pull 123456789012.dkr.ecr.us-east-1.amazonaws.com/quay/coreos/etcd:v3.5.0
```

## Combining with ECRRepositoryCreationTemplate

Pull-through cache rules work with `ECRRepositoryCreationTemplate` to apply encryption and policies to auto-created repositories.

When a pull-through cache rule creates a new repository (on first pull), ECR looks for a matching `ECRRepositoryCreationTemplate` by prefix and applies its settings:

```yaml
---
# Cache rule
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: docker-hub
  namespace: kro-system
spec:
  ecrRepositoryPrefix: docker-hub
  upstreamRegistryURL: registry-1.docker.io

---
# Template defining how cached repositories should be configured
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepositoryCreationTemplate
metadata:
  name: docker-hub-template
  namespace: kro-system
spec:
  prefix: docker-hub
  appliedFor:
  - PULL_THROUGH_CACHE
  encryptionType: KMS
  kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/..."
  imageTagMutability: IMMUTABLE
```

When the first image is pulled via the cache rule, ECR auto-creates the repository and applies the template settings (KMS encryption, immutable tags, etc.).

## Troubleshooting

### Image Pull Fails

1. **Verify the rule is created:**
   ```bash
   kubectl get ecrpullthroughcacherule
   ```

2. **Check ECR status:**
   ```bash
   aws ecr describe-pull-through-cache-rules --region us-east-1
   ```

3. **Verify upstream registry is accessible:**
   ```bash
   docker pull registry-1.docker.io/library/nginx:latest
   ```

4. **Check credentials (if using private registry):**
   ```bash
   aws secretsmanager get-secret-value --secret-id ecr-upstream-creds
   ```

### Cannot Change Immutable Fields

If you try to update an immutable field:

1. Delete the rule: `kubectl delete ecrpullthroughcacherule <name>`
2. Cached images remain in ECR
3. Create a new rule with updated settings
4. Old cached images can be manually deleted if needed

## See Also

- [ECRRepositoryCreationTemplate](ecrrepositorycreationtemplate.md) — Configure auto-created repositories
- [ECRRepository](ecrrepository.md) — Create manual repositories
- [ECRConfig](ecrconfig.md) — Set governance policies
