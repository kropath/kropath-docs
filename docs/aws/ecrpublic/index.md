# ECR Public — Container Image Publishing to the Public Gallery

ECR Public is a fully managed container image registry service that hosts publicly accessible container images in the [AWS ECR Public Gallery](https://gallery.ecr.aws). Use it to publish open-source container images, shared base images, or community tools without requiring authentication from end users.

## Key Differences from Private ECR

ECR Public is a separate AWS service from private ECR, with a distinct feature set optimized for public distribution:

| Feature | Private ECR (`ecr`) | ECR Public |
|---|---|---|
| **Access** | Requires AWS credentials (IAM) | Public, unauthenticated pull access |
| **Discoverability** | Private within an AWS account | Listed in the ECR Public Gallery (https://gallery.ecr.aws) |
| **Encryption** | Per-repository encryption (AES256 or KMS) | No per-repository encryption |
| **Image scanning** | Per-repository or registry-level scanning | Not supported |
| **Tag mutability** | Enforced per repository | Not supported |
| **Lifecycle policies** | Auto-expire images by count, age, or tag pattern | Not supported |
| **Credentials** | IAM roles, cross-account access policies | Registry alias only; no credentials needed for pull |

ECR Public repositories are hosted at `public.ecr.aws/<alias>/<repository-name>`. Because the service is simpler than private ECR, governance focuses on **naming conventions**, **mandatory tagging**, and **deletion safety** rather than encryption or lifecycle management.

## Governance Profiles

Platform teams deploy `ECRPublicConfig` CRs as named governance profiles — for example, `general-policy` (permissive) and `open-source` (enforce org ownership tags). Each application team's `ECRPublicRepository` selects a profile via `spec.configRef` and inherits mandatory naming patterns and tags.

**Common profiles:**

- `general-policy` — Default profile with permissive naming (`{namespace}/{name}`) and no mandatory tags
- `open-source` — Enforce ownership tags (`org: my-company`) and a naming pattern that includes the profile name for clear identification

## Resource Reference

- **[ECRPublicConfig](ecrpublicconfig.md)** — Governance CRD that defines naming conventions, mandatory tags, and synced labels/annotations for all public repositories
- **[ECRPublicRepository](ecrpublicrepository.md)** — The main resource used by application teams to create and manage public container repositories

## Quick Start

Create a public repository in the default `general-policy` profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPublicRepository
metadata:
  name: my-app
  namespace: default
spec:
  tags:
    team: platform
    maintainer: team@company.com
```

After reconciliation, retrieve the public gallery URI:

```bash
$ kubectl get ecrpublicrepository my-app -o jsonpath='{.status.repositoryURI}'
public.ecr.aws/a1b2c3d4/default/my-app
```

Use this URI in Dockerfiles or CI/CD pipelines:

```dockerfile
FROM public.ecr.aws/a1b2c3d4/default/my-app:latest
```

## Further Reading

- [AWS ECR Public Documentation](https://docs.aws.amazon.com/AmazonECR/latest/public/)
- [ECR Public Gallery](https://gallery.ecr.aws)
