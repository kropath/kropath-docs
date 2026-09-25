---
title: CodeArtifact on kropath
description: AWS CodeArtifact is a fully managed artifact repository service for storing and retrieving software packages.
doc_type: reference
weight: 120
---
# CodeArtifact on kropath

AWS CodeArtifact is a fully managed artifact repository service for storing and retrieving software packages. The kropath CodeArtifact family provides governance and composable resources for managing CodeArtifact domains and package groups at scale.

## Resources

- **[CodeArtifactConfig](codeartifactconfig.md)** — Governance profiles that define encryption, naming conventions, and organizational tagging policies. Platform teams create named profiles (e.g. `general-policy`, `production`); developers select a profile via `spec.configRef` on each domain and package group.

- **[CodeArtifactDomain](codeartifactdomain.md)** — The domain resource. Domains are the top-level organizational container for repositories and packages. Developers create domains by specifying encryption, naming preferences, and selecting a governance profile. All repositories in a domain share the same KMS encryption key and S3 asset storage.

- **[CodeArtifactPackageGroup](codeartifactpackagegroup.md)** — Package group resources. Package groups identify sets of packages by pattern and control how packages can be ingested from upstream sources. Each package group belongs to exactly one domain and is identified by the domain name plus pattern.

## Getting Started

### 1. Create a Governance Profile

Platform teams define governance profiles for different use cases:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    encryptionKey: ""  # AWS-managed key
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
```

### 2. Create a Domain

Developers create domains by selecting a governance profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactDomain
metadata:
  name: shared-domain
  namespace: app-team
spec:
  configRef: general-policy
  # AWS-managed key (default)
  encryptionKey: ""
  deletionPolicy: retain
```

### 3. Create a Package Group

Developers create package groups within domains:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactPackageGroup
metadata:
  name: npm-packages
  namespace: app-team
spec:
  configRef: general-policy
  domainRef: shared-domain  # References CodeArtifactDomain in same namespace
  pattern: "npm/*"  # NPM package pattern
  contactInfo: "platform-team@example.com"
```

## Key Concepts

### Two-Tier Governance

Each `CodeArtifactConfig` has two tiers:

- **Mandatory tier** — Platform enforcements that override developer choices (e.g., encryption key)
- **Defaults tier** — Sensible defaults developers can override (e.g., naming pattern, tags)

### Encryption

CodeArtifact encrypts domain assets at the domain level:

- **AWS-managed key** (default) — Encryption managed by AWS, no additional cost
- **Customer-managed KMS key** — You control the key rotation and access policies, additional KMS charges

Encryption is immutable after domain creation. Choose carefully when creating the domain.

### Domain Names

Domains are named using configurable templates. The default is `{namespace}-{name}`. Domain names must be 2–50 characters, lowercase alphanumeric and hyphens only.

### Package Groups

Package groups are identified by the combination of domain name + pattern (e.g., `npm/*`, `pypi/*`). They control how packages can be sourced:

- **Restrict PUBLISH** — Prevent direct package publication
- **Restrict UPSTREAM** — Block packages from upstream sources
- **Restrict EXTERNAL_UPSTREAM** — Block external upstream sources
- **Restrict INTERNAL_UPSTREAM** — Block internal upstream sources

**Note**: Origin controls are currently read-only status fields in kropath (awaiting ACK controller support). Manage origin controls via the AWS CLI/SDK until kropath spec support is available.

### Naming Convention

Domains are named using templates with tokens:

| Token | Value |
|---|---|
| `{namespace}` | Kubernetes namespace |
| `{name}` | CR name |
| `{account_id}` | AWS account ID |
| `{region}` | AWS region |
| `{configRef}` | Selected profile name |
| `{tag.<key>}` | Tag value |

### Deletion Protection

By default, `spec.deletionPolicy: retain` means the Kubernetes CR can be deleted without deleting the AWS domain. The domain and its repositories persist in AWS. Set `deletionPolicy: delete` to delete both.

## Governance Cascade

The effective configuration for each domain is determined by a three-tier priority:

1. **Governance mandatory tier** (highest priority) — Cannot be overridden
2. **Domain spec** (middle) — Developer choice
3. **Governance defaults tier** (lowest priority) — Fallback if not specified

This ensures platform teams can enforce critical controls (encryption, naming) while letting developers handle domain-specific settings.

## Cross-Account Domains

Package groups can reference domains in the same AWS account. Cross-account domain references require both the `domain` name and the `domainOwner` account ID:

```yaml
spec:
  domain: "shared-org-domain"
  domainOwner: "123456789012"  # 12-digit AWS account ID
  pattern: "maven/*"
```

## Best Practices

1. **Choose encryption upfront** — Encryption is immutable; plan whether you need customer-managed KMS keys before creating domains.

2. **Use governance profiles** — Encode your organization's encryption and naming policies in `CodeArtifactConfig` profiles so domains automatically inherit them.

3. **Set contact info** — Package groups should have contact information (team email, Slack channel) for developers using the packages.

4. **Tag at creation** — Cost-tracking and environment tags should be set at domain/package-group creation; retroactive tagging is error-prone.

5. **Manage origin controls outside kropath** — Until origin controls are supported in kropath spec fields, manage them via the AWS CLI or AWS Management Console.

6. **Test access policies** — After creating domains, test repository access patterns to ensure upstream sources and publishing restrictions work as intended.

## Limitations

- **Repository RGD deferred** — CodeArtifact repositories cannot yet be created via kropath (Gap G-1). Repositories must be created via AWS CLI/SDK within domains managed by kropath.

- **Origin controls status-only** — Origin control configurations (`PUBLISH`, `UPSTREAM`, etc.) are read-only status fields in kropath v1 (awaiting ACK controller support). Manage them via AWS CLI/SDK (Gap G-3).

## API Reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kinds**: `CodeArtifactConfig`, `CodeArtifactDomain`, `CodeArtifactPackageGroup`
- **Scope**: Namespaced
