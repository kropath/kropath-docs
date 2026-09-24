# StepFunctionsStateMachineAlias — User Guide

`StepFunctionsStateMachineAlias` is a Kubernetes resource that provisions AWS Step Functions aliases for routing traffic between state machine versions.

## Overview

An alias is a named, stable endpoint that routes execution traffic to one or two versions of a state machine with configurable weights. Because the alias ARN never changes while the versions behind it do, you can reference the alias in your applications and update the underlying workflow without changing your caller's code. This makes blue/green and canary deployments of workflows simple and safe.

**Key uses:**
- **Canary deployments** — Route 10% traffic to a new version while 90% continues on the stable version
- **Blue/green rollouts** — Instantly switch all traffic from one version to another by adjusting weights to 0/100
- **Traffic splitting** — Distribute load between versions during a gradual migration

## Prerequisites

- A Kubernetes cluster running kropath-aws
- A `StepFunctionsConfig` resource in your namespace (or in `kro-system` for fallback to `general-policy`)
- An existing `StepFunctionsStateMachine` with at least one published version (versions are created by publishing a state machine revision via the AWS API)
- State machine version ARNs — obtained from AWS when you publish a version

## Basic Example — Canary Deployment

This example creates an alias that routes 90% of traffic to a stable version and 10% to a canary:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsStateMachineAlias
metadata:
  name: order-processor-alias
  namespace: workflows-prod
spec:
  # Reference to a StepFunctionsConfig governance profile
  configRef: "general-policy"

  # Required: routing configuration — 1 or 2 versions with weights summing to 100
  routingConfiguration:
    # Stable version: 90% of traffic
    - stateMachineVersionArn: "arn:aws:states:us-east-1:123456789012:stateMachine:order-processor:1"
      weight: 90
    # Canary version: 10% of traffic
    - stateMachineVersionArn: "arn:aws:states:us-east-1:123456789012:stateMachine:order-processor:2"
      weight: 10

  # Optional: description
  description: "Canary deployment: testing v2 with 10% traffic"

  # Optional: Kubernetes labels synced to K8s metadata.labels only (no cloud tags on alias)
  syncedLabels:
    team: workflows
    environment: production

  # Optional: Kubernetes annotations
  syncedAnnotations:
    on-call: "workflows-team"
    runbook: "https://wiki.example.com/order-processor-deployment"

  # Optional: deletion policy (retain | delete; defaults to retain)
  deletionPolicy: retain

  # Optional: override the computed resource name
  nameOverride: "order-processor-v2-canary"
```

After applying this resource, inspect the status:

```bash
kubectl get stepfunctionsstatemachinealias -n workflows-prod
kubectl describe stepfunctionsstatemachinealias order-processor-alias -n workflows-prod
```

You'll see:
- `status.resourceName` — The computed cloud resource name
- `status.aliasArn` — The actual AWS alias ARN (populated after provisioning)
- `status.namingStatus` — Whether the naming template was valid
- `status.conditions` — Reconciliation status

**Important difference:** Unlike state machines and activities, aliases do **not** have a `status.predictedArn` field. The alias ARN embeds the parent state machine name, which isn't part of the alias spec, so it cannot be predicted beforehand. Use the actual `status.aliasArn` after provisioning.

## Resource Fields

### `spec.routingConfiguration` (required)

Specifies how to route traffic between state machine versions.

**Constraints:**
- Exactly 1 or 2 entries
- Weights must sum to 100
- Each entry has:
  - `stateMachineVersionArn` (string) — Full version ARN (e.g. `arn:aws:states:region:account:stateMachine:name:1`)
  - `weight` (integer) — Traffic weight, 0–100

**Example — 50/50 blue/green split:**
```yaml
routingConfiguration:
  - stateMachineVersionArn: "arn:aws:states:us-east-1:123456789012:stateMachine:order-processor:5"
    weight: 50
  - stateMachineVersionArn: "arn:aws:states:us-east-1:123456789012:stateMachine:order-processor:6"
    weight: 50
```

**Example — Single version (100% traffic):**
```yaml
routingConfiguration:
  - stateMachineVersionArn: "arn:aws:states:us-east-1:123456789012:stateMachine:order-processor:10"
    weight: 100
```

**How versions are identified:** Version ARNs come from publishing a state machine revision. Use the AWS CLI or your deployment pipeline to publish versions:

```bash
# Publish a new version
aws stepfunctions publish-state-machine-version \
  --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:order-processor

# Output includes version ARN:
# "stateMachineVersionArn": "arn:aws:states:us-east-1:123456789012:stateMachine:order-processor:11"
```

You supply the complete version ARN to the alias — kropath does not manage versions directly.

### `spec.description` (optional)

A human-readable description of the alias and its purpose.

**Example:**
```yaml
description: "Production alias routing to latest stable and canary versions"
```

**Important:** If omitted, the field is **absent** from the cloud resource (not set to an empty string). This is a special case: when you omit a field, kropath omits it from the AWS resource, allowing AWS defaults to apply.

### `spec.configRef` (optional, default: "general-policy")

Reference to a `StepFunctionsConfig` governance profile.

Governance profiles control:
- Naming template for computing the resource name
- Mandatory or default labels and annotations

**Example — using a custom governance profile:**
```yaml
configRef: "pci-compliance"
```

If you omit this field or reference a profile that doesn't exist, kropath falls back to `general-policy`.

**Config lookup mechanism:** Profiles are selected by label. Ensure your `StepFunctionsConfig` carries the matching label:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsConfig
metadata:
  name: pci-compliance
  labels:
    aws.kropath.run/resource-name: pci-compliance
spec:
  # ... profile configuration ...
```

### `spec.nameOverride` (optional, default: "")

Override the computed resource name.

By default, kropath uses the naming template from your governance profile to compute the resource name. The default template is `{namespace}-{name}`, so a resource named `order-processor-alias` in namespace `workflows-prod` becomes `workflows-prod-order-processor-alias`.

To use a custom name instead, set `nameOverride`:

```yaml
nameOverride: "order-processor-canary-v2"
```

**Naming constraints:**
- Max 80 characters
- Must contain at least one letter, underscore, hyphen, or period (no all-digits names; AWS forbids this to avoid ambiguity with version numbers)
- Allowed characters: `a-z`, `A-Z`, `0-9`, `_`, `-`, `.`

### `spec.syncedLabels` (optional)

Kubernetes labels that are synced to the Kubernetes resource metadata.

**Important — key difference from state machines:** Aliases do **not** support cloud tags (`spec.tags`). Labels here are synced to Kubernetes `metadata.labels` **only**, not to AWS cloud tags. To tag the workflow, tag the underlying `StepFunctionsStateMachine` instead.

**Example:**
```yaml
syncedLabels:
  team: workflows
  environment: production
  application: order-processing
```

These appear in the Kubernetes object as:
```yaml
metadata:
  labels:
    aws.kropath.run/team: workflows
    aws.kropath.run/environment: production
    aws.kropath.run/application: order-processing
```

### `spec.syncedAnnotations` (optional)

Kubernetes annotations that are synced to the Kubernetes resource metadata.

**Example:**
```yaml
syncedAnnotations:
  runbook: "https://wiki.example.com/order-processor-alias"
  escalation-policy: "workflows-oncall"
```

These appear in the Kubernetes object as:
```yaml
metadata:
  annotations:
    aws.kropath.run/runbook: "https://wiki.example.com/order-processor-alias"
    aws.kropath.run/escalation-policy: "workflows-oncall"
```

### `spec.deletionPolicy` (optional, default: "retain")

What happens to the cloud resource when the Kubernetes resource is deleted.

- `retain` — Keep the AWS alias when the Kubernetes object is deleted (default; recommended for production)
- `delete` — Delete the AWS alias when the Kubernetes object is deleted

**Example:**
```yaml
deletionPolicy: delete  # Clean up cloud resources when this CR is removed
```

**Recommendation:** For production aliases, use `retain` to prevent accidental deletion. For temporary test aliases, use `delete` to ensure cleanup.

## Governance and Configuration

### Naming Conventions

Alias names follow the same naming rules as state machines and activities. By default, kropath applies a naming template from your governance profile to compute the cloud resource name.

- **Default template:** `{namespace}-{name}`
- **Namespace:** The Kubernetes namespace where the CR exists
- **Name:** The Kubernetes resource name (`metadata.name`)
- **Result:** For a CR named `order-processor-alias` in namespace `workflows-prod`, the computed name is `workflows-prod-order-processor-alias`

To override this:

```yaml
spec:
  nameOverride: "my-custom-alias-name"
```

The computed name appears in:
- `status.resourceName`
- AWS alias name

**Status fields related to naming:**
- `status.resourceName` — The final computed alias name
- `status.namingStatus` — Either `valid` or `invalid-unresolved-tokens` (if your template references tags that don't exist)

### Mandatory Governance

If your `StepFunctionsConfig` profile specifies mandatory values for naming or labels, those take precedence over your instance settings.

**Example:**
```yaml
# In your governance profile (StepFunctionsConfig)
spec:
  mandatory:
    namingTemplate: "prod-{namespace}-{name}"
    syncedLabels:
      department: engineering
      compliance: required
```

Any alias using this profile will have:
- Names prefixed with `prod-` (mandatory)
- Synced labels **merged** with `department: engineering` and `compliance: required` (mandatory wins conflicts)

## Status Fields

### `status.resourceName`

The computed cloud resource name after applying naming templates and any overrides.

**Example:**
```yaml
status:
  resourceName: "workflows-prod-order-processor-alias"
```

### `status.namingStatus`

Validation status of the naming template.

- `valid` — All naming tokens resolved successfully
- `invalid-unresolved-tokens` — One or more template tokens (e.g. `{tag.missing-key}`) couldn't be resolved

### `status.aliasArn` and `status.aliasArnNoDescription`

The AWS ARN of the alias, populated after provisioning.

**Format:** `arn:aws:states:region:account-id:stateMachine:state-machine-name:alias:alias-name`

**Which field to use:**
- If you set `spec.description`: read `status.aliasArn`
- If you omitted `spec.description`: read `status.aliasArnNoDescription`

**Example (with description):**
```yaml
spec:
  description: "Canary deployment"
status:
  aliasArn: "arn:aws:states:us-east-1:123456789012:stateMachine:order-processor:alias:workflows-prod-order-processor-alias"
```

**Example (without description):**
```yaml
spec:
  # description omitted
status:
  aliasArnNoDescription: "arn:aws:states:us-east-1:123456789012:stateMachine:order-processor:alias:workflows-prod-order-processor-alias"
```

**Note:** Unlike state machines, these fields are **not** predictable because they include the parent state machine name, which isn't part of the alias spec. Callers must use the actual ARN from status at runtime.

### `status.conditions` and `status.conditionsNoDescription`

Standard Kubernetes conditions reflecting reconciliation status (e.g. `Reconciling`, `Ready`, `Error`).

**Which field to use:**
- If you set `spec.description`: read `status.conditions`
- If you omitted `spec.description`: read `status.conditionsNoDescription`

Both fields work the same way; the split exists as a kro v0.9.2 workaround for optional field omission.

## Updating an Alias

You can update traffic weights and other properties on a live alias without downtime.

**Example — Gradually shift traffic:**

Initial state (90/10):
```yaml
routingConfiguration:
  - stateMachineVersionArn: "arn:aws:states:us-east-1:123456789012:stateMachine:order-processor:1"
    weight: 90
  - stateMachineVersionArn: "arn:aws:states:us-east-1:123456789012:stateMachine:order-processor:2"
    weight: 10
```

After validation (50/50):
```yaml
routingConfiguration:
  - stateMachineVersionArn: "arn:aws:states:us-east-1:123456789012:stateMachine:order-processor:1"
    weight: 50
  - stateMachineVersionArn: "arn:aws:states:us-east-1:123456789012:stateMachine:order-processor:2"
    weight: 50
```

Full migration (0/100):
```yaml
routingConfiguration:
  - stateMachineVersionArn: "arn:aws:states:us-east-1:123456789012:stateMachine:order-processor:2"
    weight: 100
```

Apply the update and monitor executions — traffic will immediately shift to the new weights.

## Important Notes

### No Cloud Tags

Unlike state machines and activities, aliases have **no cloud tag surface** in AWS. Any `spec.tags` field is silently ignored. To tag your workflow, tag the underlying `StepFunctionsStateMachine` instead. Labels you specify here appear in Kubernetes metadata only.

### No Predicted ARN

Unlike state machines and activities, aliases do **not** have a `status.predictedArn` field. The alias ARN depends on the parent state machine name, which you don't specify in the alias resource. Use the actual `status.aliasArn` after provisioning.

### Version ARNs Are External

Version ARNs are produced outside kropath — by publishing a state machine revision via the AWS API, CLI, CDK, or your deployment pipeline. kropath passes them through to the alias without validation beyond checking the ARN shape. If you reference a version ARN that doesn't exist in AWS, the alias creation will fail with an AWS error.

### Weights Must Sum to 100

If your weights don't sum to 100, the CR applies successfully, but the alias will not be provisioned in AWS. Check `status.conditions` to verify reconciliation status — if no ACK child resource was created, verify that your weights sum to exactly 100.

### At Most Two Versions

AWS aliases support at most 2 versions (and at least 1). If you specify fewer than 1 or more than 2 entries in `routingConfiguration`, the CR applies successfully, but the alias will not be provisioned in AWS. Check `status.conditions` to verify reconciliation status.

## Troubleshooting

### The alias doesn't provision (no ACK child created)

If the CR applies successfully but no AWS alias is provisioned:

```bash
kubectl describe stepfunctionsstatemachinealias order-processor-alias -n workflows-prod
```

Check for these silent validation failures (they prevent ACK child creation but don't report on `status.conditions`):

- **Weights don't sum to 100** — Verify `routingConfiguration[].weight` entries sum to exactly 100
- **Wrong number of versions** — Ensure `routingConfiguration` has 1 or 2 entries, not 0 or 3+
- **Invalid weight range** — Ensure each weight is between 0 and 100
- **Invalid version ARN** — Verify the ARN format: `arn:aws:states:region:account:stateMachine:name:version-number`
- **Invalid alias name** — The computed cloud name violates AWS rules (e.g. all digits, too long, invalid characters)

### The alias is stuck in a `Reconciling` or `Error` state

If `status.conditions` shows an error:

```bash
kubectl describe stepfunctionsstatemachinealias order-processor-alias -n workflows-prod
```

Check the conditions for details — the most common issues are:
- **Missing state machine** — The underlying `StepFunctionsStateMachine` doesn't exist
- **Invalid governance config** — The referenced `StepFunctionsConfig` is missing or misconfigured
- **Version ARN doesn't exist** — The version was deleted or the ARN is malformed

### I updated the alias but the alias doesn't reflect my changes

Ensure you've saved the updated YAML and applied it to the cluster:

```bash
kubectl apply -f alias.yaml -n workflows-prod
```

Then verify:

```bash
kubectl describe stepfunctionsstatemachinealias order-processor-alias -n workflows-prod
```

### The alias ARN changes when I redeploy

The alias ARN is stable and should never change. If it does, you've deleted and recreated the alias. To avoid this, use `deletionPolicy: retain` in production.

## See Also

- [StepFunctionsStateMachine Guide](stepfunctionsstatemachine.md)
- [StepFunctionsActivity Guide](stepfunctionsactivity.md)
- [StepFunctionsConfig Reference](stepfunctionsconfig.md)
- [AWS Step Functions Aliases Documentation](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-state-machine-alias.html)
