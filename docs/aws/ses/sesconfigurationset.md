# SESConfigurationSet — User Guide

`SESConfigurationSet` is a Kubernetes resource that provisions AWS SES v1 configuration sets for email sending workflows.

## Overview

A configuration set is a named container in AWS SES that groups email sending rules and event destinations. When your application sends email via SES APIs (SendEmail, SendRawEmail), you reference the configuration set name to apply associated rules — event tracking, delivery options, reputation monitoring, and other sending behaviors.

Configuration sets themselves store only their names. Event destinations (CloudWatch, SNS, Kinesis Firehose) and other sending rules are configured separately outside of Kubernetes.

## Prerequisites

- A Kubernetes cluster running kropath-aws
- A `SESConfig` resource in your namespace (or in `kro-system` for fallback to `general-policy`)
- AWS SES verified identities (email addresses or domains) — configuration sets do not affect identity verification

## Basic Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SESConfigurationSet
metadata:
  name: transactional-emails
  namespace: email-prod
spec:
  # Governance profile selection (defaults to "general-policy" if not specified)
  configRef: general-policy

  # Optional: custom tags for cost tracking and metadata governance
  tags:
    application: order-service
    cost-centre: engineering

  # Optional: Kubernetes labels synced to cloud metadata
  syncedLabels:
    team: email-platform

  # Optional: Kubernetes annotations
  syncedAnnotations:
    runbook: "https://wiki.example.com/email-config-sets"

  # Optional: deletion policy (retain | delete; defaults to retain)
  deletionPolicy: retain

  # Optional: override the computed resource name
  nameOverride: "custom-transactional"
```

After applying this resource, inspect the status:

```bash
kubectl get sesconfigurationset -n email-prod
kubectl describe sesconfigurationset transactional-emails -n email-prod
```

You'll see:
- `status.resourceName` — The computed cloud configuration set name
- `status.predictedArn` — The expected AWS ARN
- `status.namingStatus` — Whether the naming template was valid

## Resource Fields

### `spec.configRef` (optional, default: "general-policy")

Reference to a `SESConfig` governance profile.

The profile defines:
- Naming conventions
- Mandatory tags and labels
- Default metadata governance policies

**Example:**
```yaml
configRef: "transactional"  # Use the transactional governance profile
```

If the named profile doesn't exist, the system falls back to `general-policy`.

### `spec.nameOverride` (optional)

Bypass the computed naming template and use this exact name for the AWS resource.

If omitted, the resource name is computed from `spec.configRef` and the naming template defined in `SESConfig`.

**Example:**
```yaml
nameOverride: "my-config-set"
```

Without this field, the default naming template `{namespace}-{name}` would produce `email-prod-transactional-emails`.

### `spec.deletionPolicy` (optional, default: "retain")

Deletion policy when the Kubernetes resource is deleted.

- `retain` — Keep the AWS configuration set (default, safer)
- `delete` — Delete the AWS configuration set

**Example:**
```yaml
deletionPolicy: delete  # Clean up when resource is deleted
```

Be careful with `delete` — existing emails rules (event destinations, delivery options, reputation options) configured outside of Kubernetes will be lost.

### `spec.tags` (optional)

Custom tags applied to the AWS configuration set resource.

Merged with governance profile tags. Mandatory tags from the profile cannot be overridden.

**Example:**
```yaml
tags:
  application: order-service
  cost-centre: engineering
  environment: production
```

### `spec.syncedLabels` (optional)

Kubernetes labels synced to the Kubernetes resource metadata (prefixed with `aws.kropath.run/`).

These labels do not get forwarded to AWS cloud tags — they are Kubernetes-only metadata.

**Example:**
```yaml
syncedLabels:
  team: email-platform
  data-class: internal
```

Result:
- Kubernetes: `aws.kropath.run/team: email-platform`, `aws.kropath.run/data-class: internal`

### `spec.syncedAnnotations` (optional)

Kubernetes annotations synced to the Kubernetes resource metadata (prefixed with `aws.kropath.run/`).

**Example:**
```yaml
syncedAnnotations:
  runbook: "https://wiki.example.com/email-config-sets"
  alerts: "pd-oncall-email-team"
```

## Status Fields

After the configuration set is created, inspect the status:

```bash
kubectl get sesconfigurationset transactional-emails -n email-prod -o yaml
```

**Common status fields:**

- `status.resourceName` — The computed AWS configuration set name (derived from naming template or `nameOverride`)
- `status.namingStatus` — `valid` or `invalid-unresolved-tokens` (if naming template has unresolved placeholders)
- `status.predictedArn` — Expected AWS ARN format (e.g., `arn:aws:ses:ap-southeast-2:123456789012:configuration-set/email-prod-transactional-emails`)
- `status.conditions` — Kubernetes standard conditions (ReconcileSucceeded, ReconcileFailed, etc.)

## Naming Conventions

By default, configuration set names follow the pattern `{namespace}-{name}` derived from your resource's namespace and metadata name.

**Example:**
- Namespace: `email-prod`
- Resource name: `transactional-emails`
- Computed name: `email-prod-transactional-emails`

AWS requires configuration set names to:
- Use characters `[a-zA-Z0-9_-]`
- Be 1–64 characters long
- Not contain spaces or uppercase letters (no case restriction, but lowercase is recommended)

If you need a custom naming pattern (for example, environment-specific prefixes or tag-based tokens), update the `SESConfig` profile's `spec.defaults.namingTemplate` or `spec.mandatory.namingTemplate`.

## Using Configuration Sets in Your Application

Once the configuration set is created, your application can reference it in SES API calls:

### Via X-SES-CONFIGURATION-SET Header

In transactional email libraries (for example, when sending verification emails):

```python
# Using boto3
client = boto3.client('ses')
client.send_email(
    Source='noreply@example.com',
    Destination={'ToAddresses': ['user@example.com']},
    Message={
        'Subject': {'Data': 'Welcome'},
        'Body': {'Text': {'Data': 'Hello!'}}
    },
    # Reference the configuration set
    ConfigurationSetName='email-prod-transactional-emails'
)
```

### Via SendRawEmail Parameter

For more complex email formats:

```python
import email.mime.text

msg = email.mime.text.MIMEText('Hello!')
msg['Subject'] = 'Welcome'
msg['From'] = 'noreply@example.com'
msg['To'] = 'user@example.com'

client.send_raw_email(
    RawMessage={'Data': msg.as_string()},
    Source='noreply@example.com',
    Destinations=['user@example.com'],
    ConfigurationSetName='email-prod-transactional-emails'
)
```

The configuration set applies any event destinations, delivery options, and reputation tracking configured via the AWS CLI, Terraform, or CloudFormation.

## Examples

### Simple Configuration Set

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SESConfigurationSet
metadata:
  name: notifications
  namespace: systems
spec:
  configRef: general-policy
  tags:
    application: alerts
  deletionPolicy: retain
```

### Configuration Set with Custom Naming

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SESConfigurationSet
metadata:
  name: marketing
  namespace: campaigns-prod
spec:
  configRef: general-policy
  nameOverride: "customer-campaigns-prod"
  tags:
    application: marketing
    cost-centre: growth
  syncedLabels:
    team: marketing-automation
```

### Configuration Set with Full Governance

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SESConfigurationSet
metadata:
  name: transactional
  namespace: email-prod
spec:
  configRef: compliance-strict
  tags:
    application: order-service
    cost-centre: engineering
    compliance-level: high
  syncedLabels:
    team: email-platform
    data-class: customer-data
  syncedAnnotations:
    runbook: "https://wiki.example.com/email-transactional"
    oncall: "pagerduty-email-team"
  deletionPolicy: retain
```

## Troubleshooting

**"My configuration set isn't being created"**
- Check `kubectl get sesconfigurationset -n <namespace>` for status
- View detailed events: `kubectl describe sesconfigurationset <name> -n <namespace>`
- Ensure the `SESConfig` profile exists (or `general-policy` fallback is in place)

**"The naming template is invalid"**
- Verify `status.namingStatus` is `valid`
- Check that all tokens in the naming template are resolved (e.g., `{tag.env}` requires an `env` tag)
- If using a custom naming template in `SESConfig`, verify it contains only valid tokens: `{name}`, `{namespace}`, `{account_id}`, `{region}`, `{configRef}`, or `{tag.<key>}`

**"My configuration set isn't applying event destinations"**
- Configuration sets are containers only — event destinations, delivery options, and reputation tracking must be configured separately via AWS CLI, Terraform, or CloudFormation
- Use `aws sesv1 put-configuration-set-event-destinations` or equivalent IaC tools to add event destinations after the configuration set is created

**"My governance profile's mandatory fields aren't being enforced"**
- Verify the `SESConfig` exists and has `status.effectiveConfig` populated
- Ensure your `configRef` points to the correct profile name
- Check that the profile has `mandatory.namingTemplate` (not `defaults.namingTemplate`) if you want to enforce a naming pattern

## See Also

- [SESConfig Governance Reference](./sesconfig.md)
- [SES Resource Family Overview](./README.md)
- [AWS SES Documentation](https://docs.aws.amazon.com/ses/)
- [SES Configuration Sets Guide](https://docs.aws.amazon.com/ses/latest/dg/configuration-sets.html)
