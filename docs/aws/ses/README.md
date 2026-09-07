# SES Resource Family

The SES resource family provides Kubernetes-native abstractions for managing AWS Simple Email Service (SES) v1 configuration sets.

## Overview

Amazon SES configuration sets are named containers for email sending rules. When you send email via SES APIs, you reference a configuration set to apply associated event destinations, delivery options, reputation tracking, and other sending behaviors.

The SES family makes it easy to:

- **Provision configuration sets** via Kubernetes manifests (`SESConfigurationSet`)
- **Enforce naming conventions** across all configuration sets
- **Govern metadata** (labels, annotations, tags) with platform policies (`SESConfig`)
- **Manage deletion policies** (retain or clean up cloud resources when Kubernetes resources are deleted)

## Resources in This Family

| Resource | Purpose |
|---|---|
| [`SESConfigurationSet`](./sesconfigurationset.md) | Create named configuration sets for email sending workflows |
| [`SESConfig`](./sesconfig.md) | Define governance profiles and naming policies for all configuration sets |

## Quick Start

Create a configuration set for your application:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SESConfigurationSet
metadata:
  name: marketing-emails
  namespace: email-prod
spec:
  # Optional: reference a governance profile (defaults to "general-policy")
  configRef: general-policy

  # Optional: custom tags for cost tracking
  tags:
    application: marketing
    cost-centre: growth
```

Apply it to your cluster:

```bash
kubectl apply -f config-set.yaml
```

The configuration set is created in AWS with a name derived from your namespace and resource name (by default: `email-prod-marketing-emails`). Applications can then reference this configuration set in their SES SendEmail/SendRawEmail API calls using the `X-SES-CONFIGURATION-SET` header or the `ConfigurationSetName` parameter.

## Prerequisites

- A Kubernetes cluster running kropath-aws
- A `SESConfig` governance profile in your namespace or `kro-system` (or use the default `general-policy`)
- AWS SES verified identities (email addresses or domains) — configuration sets are containers for sending rules but do not affect identity verification

## Use Cases

**Transactional emails** — Create a configuration set for customer transactional emails (order confirmations, password resets) and configure CloudWatch/SNS event destinations outside of Kubernetes to track bounces and complaints.

**Marketing campaigns** — Use a separate configuration set for marketing emails with different event tracking and reputation settings.

**Notification workflows** — Configuration sets for internal notifications, alerts, and system messages with organization-specific delivery rules.

## Key Concepts

### Configuration Set Naming

By default, configuration set names follow the pattern `{namespace}-{name}` derived from your Kubernetes resource. You can override this:

- Use `spec.nameOverride` for a custom name
- Use `spec.configRef` to select a governance profile with a different naming template

AWS requires configuration set names to:
- Use characters `[a-zA-Z0-9_-]`
- Be 1–64 characters long
- Not contain spaces

### Governance Profiles

Platform teams create `SESConfig` profiles to enforce:

- **Naming templates** — required naming conventions across all configuration sets
- **Mandatory tags** — cost-center, compliance, ownership tags that cannot be overridden
- **Default tags** — baseline tags for all configuration sets
- **Label and annotation policies** — Kubernetes metadata governance

Application teams select a profile via `spec.configRef` when creating configuration sets. If the profile doesn't exist, the system falls back to `general-policy`.

### Associated Sending Rules

Configuration sets themselves are bare containers — they store only the name. Associated event destinations (CloudWatch, Kinesis Firehose, SNS) and delivery/reputation/tracking options are managed via separate SES API calls (not exposed as Kubernetes CRDs). Applications configure these outside of Kubernetes using Terraform, CloudFormation, or the AWS CLI.

## See Also

- [SESConfigurationSet User Guide](./sesconfigurationset.md)
- [SESConfig Governance Reference](./sesconfig.md)
- [AWS SES Documentation](https://docs.aws.amazon.com/ses/)
