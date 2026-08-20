# AWS Elastic Container Registry (ECR)

AWS Elastic Container Registry (ECR) resources in kropath enable you to create, manage, and govern container image repositories with encryption, image tag mutability enforcement, lifecycle policies, and platform-wide governance controls.

## Resources

- **[ECRConfig](./ecrconfig.md)** — Governance profiles that control encryption, tag immutability, naming, and lifecycle policies across your organization
- **[ECRRepository](./ecrrepository.md)** — The primary resource for creating and managing private container image repositories
- **[ECRPullThroughCacheRule](./ecrpullthroughcacherule.md)** — Rules that transparently cache images from upstream public registries (Docker Hub, ECR Public, GitHub Container Registry, Quay)
- **[ECRRepositoryCreationTemplate](./ecrrepositorycreationtemplate.md)** — Templates that govern the configuration of repositories auto-created by pull-through cache rules or cross-region replication

## Quick Start

### 1. Define Governance Profiles

Create an `ECRConfig` profile to define your organization's encryption, tag mutability, and naming conventions:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory: {}
  defaults:
    imageTagMutability: "MUTABLE"
    encryptionType: "AES256"
    namingTemplate: "{namespace}/{name}"
```

### 2. Create Repositories

Create repositories by selecting a governance profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: my-app
  namespace: app-team
spec:
  configRef: general-policy
  deletionPolicy: retain
```

Result: Repository created as `app-team/my-app` with AWS-managed encryption and mutable image tags.

### 3. (Optional) Add Pull-Through Cache

Cache images from upstream registries automatically:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: docker-hub
  namespace: kro-system
spec:
  ecrRepositoryPrefix: docker-hub
  upstreamRegistryURL: registry-1.docker.io
```

Users can now pull images like `123456789012.dkr.ecr.us-east-1.amazonaws.com/docker-hub/library/ubuntu`, and ECR automatically caches them.

## Key Concepts

### Governance Cascade

ECR resources follow a three-tier governance cascade:

1. **Platform mandatory tier** — Organization-wide enforcement (encryption type, tag immutability, naming patterns)
2. **Repository spec** — Developer overrides (when not overridden by mandatory tier)
3. **Platform defaults tier** — Fallback values (applied when developer doesn't specify)

Example: If your platform mandates `imageTagMutability: IMMUTABLE` for all repositories, a developer cannot create a repository with mutable tags.

### Repository Naming

Repositories are named using a configurable template with placeholders like `{namespace}`, `{name}`, and `{tag.KEY}`. The default template is `{namespace}/{name}`, producing names like `app-team/my-app`. This hierarchical naming makes it easy to organize repositories by team or application.

### Image Tag Mutability

- **IMMUTABLE** — Once an image is tagged, the tag cannot be reassigned to a different image (supply chain security)
- **MUTABLE** — Tags can be reassigned to different images (faster iteration during development)

You can exclude specific tags from immutability enforcement using `imageTagMutabilityExclusionFilters` (e.g., exclude the `latest` tag while keeping other tags immutable).

### Encryption Options

- **AES256** — AWS-managed encryption (free, no additional setup required)
- **KMS** — Customer-managed encryption with AWS Key Management Service (for compliance requirements)

### Lifecycle Policies

Define retention rules for images based on age or tag status. Example: "Expire untagged images after 7 days" or "Keep only the most recent 10 images per repository."

## Learn More

- See [ECRConfig](./ecrconfig.md) for setting up governance profiles with mandatory and default policies
- See [ECRRepository](./ecrrepository.md) for creating and managing repositories with encryption, tag mutability, and lifecycle policies
- See [ECRPullThroughCacheRule](./ecrpullthroughcacherule.md) for transparently caching images from upstream registries
- See [ECRRepositoryCreationTemplate](./ecrrepositorycreationtemplate.md) for auto-configuring repositories created by cache rules or replication
- For ADR context, see `kropath-core/docs/families/aws/ecr.md`
