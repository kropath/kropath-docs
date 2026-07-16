# AWS Identity and Access Management (IAM)

The AWS IAM family provides abstractions for managing cloud identities, permissions, and access controls in Amazon Web Services.

## Overview

The IAM resource family lets you provision and govern:

- **Workload identities** — IAM roles for EC2 instances, ECS tasks, Lambda functions, EKS workloads, and AWS services
- **Permissions** — IAM managed policies (reusable) and inline policies
- **Federation** — OIDC and SAML identity providers for external workload authentication
- **Operator access** — IAM groups and users for human access to AWS resources
- **Governance** — Org-wide mandatory controls and defaults (permissions boundaries, access key restrictions, session duration limits)

## Core Concepts

### Governance Hierarchy

IAM governance operates in three layers:

1. **Organization level** — Org-wide defaults and mandatory controls apply to all namespaces
2. **Namespace level** — Namespace-specific profiles override org defaults for workloads in that namespace
3. **Resource level** — Individual resources can override namespace and org defaults

This three-layer hierarchy ensures safe, auditable control without removing developer flexibility.

### Profile-Based Configuration

Each resource instance selects an `IAMConfig` profile (e.g., `"general-policy"` or `"pci"`) via `spec.configRef`. Platform teams create profiles that encode org policies:

- **general-policy** — Conservative baseline suitable for most workloads
- **pci** — Hardened configuration for payment card industry compliance
- **dev** — Permissive settings for development environments

If a named profile does not exist, resources fall back to `general-policy`.

## Resources

- **[IAMConfig](./iamconfig.md)** — Governance configuration for the IAM family
- **[IAMRole](./iamrole.md)** — Workload identity principals for EC2, Lambda, ECS, EKS, and services
- **[IAMPolicy](./iampolicy.md)** — Reusable managed policies
- **[IAMIdentityProvider](./iamidentityprovider.md)** — OIDC and SAML providers for external federation
- **[IAMGroup](./iamgroup.md)** — Groups for human operator access
- **[IAMUser](./iamuser.md)** — Users for human operator access

## Common Patterns

### Attaching Policies to Roles, Groups, and Users

You can attach policies in three ways:

1. **AWS managed policy** — Pre-built policies provided by AWS
2. **Reusable managed policy** — Your own `IAMPolicy` resource, referenced by CR name
3. **Inline policy** — Policy defined directly on the resource (not recommended for reuse)

Prefer reusable managed policies when the policy is used by multiple principals.

### Working with OIDC Providers

To use OIDC federation for EKS workloads:

1. Create an `IAMIdentityProvider` with `type: oidc`, providing your OIDC issuer URL
2. Create an `IAMRole` with `type: eks-irsa`, referencing the provider's `providerArn` and your Kubernetes service account
3. The role's trust policy automatically permits your service account to assume the role

### Cross-Workload Resource Sharing

When multiple `IAMRole` instances need the same permissions, create a single `IAMPolicy` and reference it from each role:

```yaml
policies:
  - ref: my-shared-policy  # References IAMPolicy/my-shared-policy
```

## Deletion and Retention

By default, IAM resources use `deletionPolicy: retain` to prevent accidental deletion of shared infrastructure. When you delete a resource, the underlying AWS resource remains in your account.

To delete the underlying AWS resource when the Kubernetes resource is deleted, set `deletionPolicy: delete`.

## Monitoring and Troubleshooting

Check the resource's `status` field to verify creation:

```bash
kubectl describe iamrole my-role -n my-namespace
```

Look for:
- `status.resourceName` — The effective name used in AWS
- `status.predictedArn` — The ARN the resource will have (or has) in AWS
- `status.conditions` — Any errors or warnings

## Related Documentation

See the [governance hierarchy guide](./governance.md) for deeper explanations of mandatory vs. defaults tiers and cascade semantics.
