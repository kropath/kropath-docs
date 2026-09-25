---
title: ECRPublicRepository — Creating and Managing Public Container Repositories
description: "The `ECRPublicRepository` resource creates and manages container image repositories in the AWS ECR Public Gallery (`public.ecr.aws`)."
doc_type: reference
---
# ECRPublicRepository — Creating and Managing Public Container Repositories

The `ECRPublicRepository` resource creates and manages container image repositories in the AWS ECR Public Gallery (`public.ecr.aws`). Use it to publish open-source container images, shared base images, or community tools that are accessible without authentication.

## Core Fields

### Governance and Profile Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `ECRPublicConfig` governance profile to apply |
| `deletionPolicy` | string | `"retain"` | Behavior when the repository resource is deleted: `"retain"` (safe default) or `"delete"` |

### Repository Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `nameOverride` | string | `""` | Bypasses the naming template; sets the repository name directly in ECR Public |

When `nameOverride` is empty, the repository name is derived from the `namingTemplate` in the selected governance profile (default: `{namespace}/{name}`).

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS cloud tags; merged additively with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels also synced to AWS cloud tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations synced to AWS cloud resource tags (prefixed `aws.kropath.run/`) |

## Status Fields

After the repository is created, you can read these output fields:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective repository name (after naming template substitution or `nameOverride`) |
| `namingStatus` | string | `valid` or `invalid-unresolved-tokens` (indicates if all naming tokens resolved successfully) |
| `predictedArn` | string | Full ARN of the repository (e.g., `arn:aws:ecr-public::123456789012:repository/default/my-app`) |
| `repositoryURI` | string | **The primary runtime output** — full push/pull URI for use in Dockerfiles and deployments (e.g., `public.ecr.aws/a1b2c3d4/default/my-app`) |
| `registryID` | string | AWS account ID of the owning public registry |
| `createdAt` | string | RFC3339 timestamp when the repository was created |
| `conditions` | array | Standard Kubernetes conditions |

**Important:** `repositoryURI` is the operationally significant output. Use it in Dockerfiles, CI/CD pipelines, and Kubernetes Pod `image` fields.

## Basic Example

Create a public repository with default naming and tags:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPublicRepository
metadata:
  name: my-app
  namespace: default
spec:
  configRef: general-policy
  deletionPolicy: retain
  tags:
    team: backend
    maintainer: backend-team@company.com
```

After reconciliation, retrieve the public gallery URI:

```bash
$ kubectl get ecrpublicrepository my-app
NAME     RESOURCENAME      NAMINGSTATUS   PREDICTEDARN
my-app   default/my-app    valid          arn:aws:ecr-public::123456789012:repository/default/my-app

$ kubectl get ecrpublicrepository my-app -o jsonpath='{.status.repositoryURI}'
public.ecr.aws/a1b2c3d4/default/my-app
```

Use this URI in your Dockerfiles and deployments:

```dockerfile
FROM public.ecr.aws/a1b2c3d4/default/my-app:v1.2.3
```

## Naming Conventions

The repository name in ECR Public is determined by one of two paths:

### 1. Default: Naming Template from Governance Profile

If `spec.nameOverride` is empty (default), the repository name comes from the `namingTemplate` in your selected `ECRPublicConfig` profile:

```yaml
spec:
  configRef: general-policy  # Uses general-policy's namingTemplate
```

The `general-policy` profile uses `{namespace}/{name}`, so a repository named `my-app` in namespace `default` becomes `default/my-app` in ECR Public.

### 2. Override: Direct Name Specification

To bypass the naming template and specify the repository name directly:

```yaml
spec:
  nameOverride: "my-org/my-public-app"
```

The repository will be created as `my-org/my-public-app` regardless of the naming template. Use this sparingly — it overrides governance controls and makes names harder to predict.

### Naming Tokens

Naming templates support variable substitution. Available tokens:

| Token | Resolves to | Example |
|---|---|---|
| `{name}` | `metadata.name` of this ECRPublicRepository | `{name}` → `my-app` |
| `{namespace}` | Kubernetes namespace | `{namespace}` → `backend` |
| `{configRef}` | The selected profile name | `{configRef}` → `general-policy` |
| `{account_id}` | AWS account ID | `{account_id}` → `123456789012` |
| `{region}` | AWS region | `{region}` → `us-east-1` |
| `{tag.KEY}` | Value of a cloud tag or synced label | `{tag.team}` → `platform` |

**Example with custom naming:**

If the profile uses `{configRef}/{namespace}/{name}`:

```yaml
metadata:
  name: app
  namespace: team-a
spec:
  configRef: open-source
```

Results in repository name: `open-source/team-a/app`

## Tag Management

Tags are merged from three sources in priority order:

```
finalTags = mandatory (from profile) + instance spec.tags + defaults (from profile)
```

On key collision, **mandatory tags always win**, ensuring the platform team can enforce critical tracking tags.

### Basic Tags

Add tags directly to your repository:

```yaml
spec:
  tags:
    team: backend
    environment: production
    maintained-by: team@company.com
```

### Mandatory Governance Tags

If your `ECRPublicConfig` profile has mandatory tags, they are automatically applied:

```yaml
# In ECRPublicConfig/open-source:
spec:
  mandatory:
    tags:
      org: my-company
      visibility: public
```

Any repository using the `open-source` profile will have these tags applied automatically. You cannot remove or override mandatory tags.

### Synced Labels

Use `syncedLabels` to automatically sync Kubernetes labels to AWS cloud tags:

```yaml
spec:
  syncedLabels:
    data-class: public
    compliance: oss-friendly
```

Results in both:
- Kubernetes `metadata.labels`: `aws.kropath.run/data-class: public`, `aws.kropath.run/compliance: oss-friendly`
- AWS tags: `aws.kropath.run/data-class: public`, `aws.kropath.run/compliance: oss-friendly`

This pattern enables Kubernetes-native label queries to match cloud-side compliance requirements.

## Deletion Policies

Control what happens when the `ECRPublicRepository` resource is deleted:

### Retain (Safe Default)

```yaml
spec:
  deletionPolicy: retain
```

- The Kubernetes resource is deleted
- **The actual ECR Public repository and all images are retained in AWS**
- Safe for production use — prevents accidental image loss

### Delete

```yaml
spec:
  deletionPolicy: delete
```

- The Kubernetes resource is deleted
- **The actual ECR Public repository and all images are deleted from AWS**
- Use with caution — this is destructive and cannot be undone

Always use `retain` for production and shared image repositories. Use `delete` only for temporary or test repositories that you want to clean up automatically.

## Profile Examples

### Default Profile (Permissive)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPublicRepository
metadata:
  name: nginx-fork
  namespace: community
spec:
  # configRef: general-policy is the implicit default
  tags:
    license: MIT
    upstream: nginx
```

Result:
- Repository name: `community/nginx-fork` (uses default `{namespace}/{name}` template)
- No mandatory tags
- Deletion policy: `retain` (default, safe)

### Strict Governance Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPublicRepository
metadata:
  name: base-image
  namespace: platform
spec:
  configRef: open-source
  tags:
    description: Minimal Debian-based runtime
```

If `open-source` profile has:
```yaml
spec:
  mandatory:
    namingTemplate: "{configRef}/{namespace}/{name}"
    tags:
      org: my-company
      visibility: public
```

Result:
- Repository name: `open-source/platform/base-image` (enforced by profile)
- Automatic tags: `org: my-company`, `visibility: public`
- Additional tags from instance: `description: Minimal Debian-based runtime`
- Final tag set: `{org, visibility, description}`
- Deletion policy: `retain`

## Using Repositories in Practice

### Docker Push and Pull

```bash
# Build and tag locally
docker build -t public.ecr.aws/a1b2c3d4/platform/base-image:v1.0.0 .

# Push to public registry (no credentials needed for this example, but push requires AWS auth)
docker push public.ecr.aws/a1b2c3d4/platform/base-image:v1.0.0

# Pull from public registry (any user can pull without AWS credentials)
docker pull public.ecr.aws/a1b2c3d4/platform/base-image:v1.0.0
```

### In Dockerfiles

```dockerfile
# FROM a public ECR repository (no credentials required)
FROM public.ecr.aws/a1b2c3d4/platform/base-image:v1.0.0

RUN apt-get update && apt-get install -y curl

COPY . /app
WORKDIR /app
CMD ["./app"]
```

### In Kubernetes Deployments

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-service
  template:
    metadata:
      labels:
        app: my-service
    spec:
      containers:
      - name: app
        # Reference the public registry URI
        image: public.ecr.aws/a1b2c3d4/platform/base-image:v1.0.0
        # No imagePullSecrets needed — registry is public
```

### In GitHub Actions

```yaml
name: Build and Push to ECR Public

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v3
      - uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions-role
          aws-region: us-east-1
      
      - uses: docker/setup-buildx-action@v2
      - uses: docker/build-push-action@v4
        with:
          push: true
          tags: public.ecr.aws/a1b2c3d4/platform/my-app:${{ github.sha }}
```

## Troubleshooting

### Repository not created / `namingStatus: invalid-unresolved-tokens`

The naming template contains a token that could not be resolved. Common causes:

- **`{tag.KEY}` token missing:** The tag key doesn't exist in any tier (mandatory, spec, or defaults)
- **`{configRef}` mismatch:** The selected profile does not exist

**Fix:**
1. Check your `ECRPublicConfig` profile for all required tags
2. Verify the `configRef` name matches an existing profile
3. Add the missing tag or use a simpler naming template

### `repositoryURI` is empty

The repository was not successfully created in AWS. Common causes:

- **Invalid repository name:** Contains uppercase letters, unsupported characters, or violates regex rules
- **Configuration profile missing:** The referenced `ECRPublicConfig` doesn't exist or has issues
- **Controller reconciliation pending:** Wait a few moments and check status again

**Fix:**
1. Verify `status.namingStatus` is `valid`
2. Run `kubectl describe ecrpublicrepository <name>` for detailed error messages
3. Check controller logs: `kubectl logs deployment/kropath-controller -n kro-system`

### Cannot override mandatory tags

If your repository instance includes a tag that conflicts with a mandatory tag from the profile, the mandatory tag always wins. This is by design — platform teams use mandatory tags to enforce compliance.

**Solution:** Coordinate with your platform team if you need to change a mandatory tag value.

## Best Practices

1. **Use descriptive repository names** — include the project, team, or purpose: `platform/base-image`, `team-a/nginx-fork`
2. **Tag all images with semantic versions** — e.g., `v1.0.0`, `v1.0.0-rc1`, not just `latest`
3. **Use meaningful tags** — include `team`, `maintainer`, `license`, `description` for discoverability in the ECR Public Gallery
4. **Keep deletion policy as `retain` for production** — only use `delete` for temporary test repositories
5. **Let governance profiles enforce naming** — avoid using `nameOverride` unless absolutely necessary
6. **Keep governance profiles simple** — avoid complex token substitutions that are hard to predict
