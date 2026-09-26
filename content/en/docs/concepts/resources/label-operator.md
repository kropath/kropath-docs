---
title: Label Operator
linkTitle: Label Injection
description: The kropath controller includes a label-operator feature that automatically injects provider-specific resource-name labels onto all resources within provider API groups.
weight: 10
doc_type: concept
---

# Label Operator

The kropath controller includes a label-operator feature that automatically injects provider-specific resource-name labels onto all resources within provider API groups. This ensures that resources are reliably discoverable by Resource Group Definition (RGD) `labelSelector` lookups, a critical requirement for the governance cascade pattern.

## Why Label Injection Matters

RGDs in kropath provider repositories use `labelSelector` with the `matchLabels` field to locate external resources — both configuration resources (such as `S3Config`, `IAMConfig`) and non-configuration resources referenced via `externalRef` (such as `IAMPolicyDocument`, `S3Bucket`).

Without the label-operator, resources must be manually labeled with the correct `<provider>.kropath.run/resource-name` label. Missing or incorrect labels cause silent lookup failures where RGDs cannot locate the referenced resource, blocking reconciliation and preventing proper governance cascade application.

The label-operator solves this by automatically ensuring every resource under a `<provider>.kropath.run` API group carries the label with a value matching its `metadata.name` — guaranteeing that `labelSelector` lookups will always find the resource.

## How It Works

The kropath controller runs an operator-based reconciliation loop that continuously watches all resources under the `<provider>.kropath.run` API groups and ensures the correct label is always present and accurate.

### Automatic Labeling

On reconciliation of any resource under `<provider>.kropath.run`, the operator:

1. Reads the resource's current labels.
2. Determines the label key from the resource's API group: `<provider>.kropath.run/resource-name`.
3. If the label is absent: adds `<provider>.kropath.run/resource-name: <metadata.name>`.
4. If the label exists but its value does not match `metadata.name`: overwrites it with the correct value.
5. If the label is present and correct: skips the update to avoid unnecessary API server writes.

The mutation is applied as a server-side patch targeting only `metadata.labels`.

### Scope

The operator automatically covers:

- **All Config resources** — `S3Config`, `IAMConfig`, `KMSConfig`, `CloudStorageBucketConfig`, `StorageAccountConfig`, and any future config kinds.
- **All externally-referenced resources** — `IAMPolicyDocument`, `IAMPolicy`, `S3Bucket`, `IAMRole`, and any future resource kinds defined under `<provider>.kropath.run`.
- **Any new CRD registered under an existing provider API group** — no code changes needed. For example, if a new `S3AccessPoint` kind is added under `aws.kropath.run`, the operator automatically covers it.

**Excluded:** `KropathConfig` resources use the `kropath.run` API group (not a provider-specific group), so they are outside the operator's scope.

### Adding New Providers

When a new provider is added in the future (e.g., a new `oracle.kropath.run` API group):

- The operator **must be explicitly extended** to watch the new provider's API group.
- This requires two changes:
  1. **Controller configuration:** Add a new informer in `kropath-controller` startup to watch the new `<provider>.kropath.run` API group.
  2. **RBAC update:** Update the Helm chart ClusterRole to grant permissions on the new API group (`get`, `list`, `watch`, `patch`).
- These are configuration and deployment changes, not code changes. Once updated, the operator covers all resources in the new API group automatically.

### Provider Determination

The operator derives the provider from the resource's API group:

| API Group | Provider | Label Key |
|---|---|---|
| `aws.kropath.run` | AWS | `aws.kropath.run/resource-name` |
| `gcp.kropath.run` | GCP | `gcp.kropath.run/resource-name` |
| `azure.kropath.run` | Azure | `azure.kropath.run/resource-name` |

## Behavior When Unavailable

If the label-operator pod is unavailable or crashed:

- **Existing resources with the label** remain unaffected — labels persist in etcd regardless of operator state.
- **New resources are admitted normally** without error, but may lack the label until the operator recovers.
- **Impact:** During an operator outage, RGDs referencing newly-created resources via `labelSelector` will fail to locate them. This surfaces a condition in the RGD status but does not block the resource creation or admission. Once the operator recovers, the label is added retroactively on the next reconciliation cycle, and RGDs automatically succeed on their next reconcile.

This is a soft-failure mode — better than a webhook-based approach that would either block admission entirely or risk losing label injection during outages.

## Creating Labeled Resources

When creating or modifying resources, you typically don't interact with the label-operator directly. It runs automatically in the background. However, understanding the labeling pattern is important when writing resource manifests or debugging label-related issues.

### Example Configuration Resource

The following example shows an `S3Config` resource. The label-operator will automatically inject (or correct) the `aws.kropath.run/resource-name` label:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3Config
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory:
    encryption:
      algorithm: "aws:kms"
  defaults:
    blockPublicAccess: true
```

After the operator reconciles this resource, it will carry:

```yaml
metadata:
  labels:
    aws.kropath.run/resource-name: general-policy
```

### Example Instance Resource

Similarly, when you create an `S3Bucket` (a resource instance):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: my-app-data
  namespace: prod
spec:
  configRef: general-policy
  region: us-west-2
```

The operator automatically labels it:

```yaml
metadata:
  labels:
    aws.kropath.run/resource-name: my-app-data
```

## Interaction with RGD Composition

The label-operator does not interfere with kro RGD reconciliation:

- The operator only modifies `metadata.labels`, never `spec` or `status`.
- kro's reconciler watches for `spec` changes and ignores label-only updates.
- The operator uses a patch operation (not a full update) to avoid conflicts with concurrent kro writes.

This ensures clean separation of concerns: the operator handles discoverability via labels, while kro handles the composition and lifecycle of child resources.

## Troubleshooting

### Resources Are Missing the Label

If you notice a resource lacks the `<provider>.kropath.run/resource-name` label:

1. **Verify the operator is running.** Check that the kropath-controller pod is healthy and not in a crash loop.
2. **Check the API group.** Ensure the resource's API group matches a provider group (e.g., `aws.kropath.run`, `gcp.kropath.run`, `azure.kropath.run`). Resources in other API groups (like `kropath.run`) are not covered.
3. **Wait for reconciliation.** The operator may take a few seconds to reconcile the resource after creation. If the label is still missing after a minute, check the controller logs.

### RGD Cannot Find Referenced Resources

If an RGD's `labelSelector` lookup fails (typically signaled by a `LookupFailed` condition in the RGD status):

1. **Check the label value.** Verify that the target resource has the correct label key (`<provider>.kropath.run/resource-name`) and that the value exactly matches the resource's `metadata.name`.
2. **Verify the selector matches.** Ensure the RGD's `labelSelector.matchLabels` uses the correct provider-prefixed key and references the expected resource name.
3. **Check namespaces.** The `externalRef` must specify both `metadata.name` and `metadata.namespace`. Verify the target resource exists in the specified namespace.

## Cross-Provider Consistency

The label-operator behavior is identical across AWS, GCP, and Azure. The only difference is the label key, which is derived from the resource's API group. This ensures a consistent experience whether you're working with AWS, GCP, or Azure resources.

## Summary

The controller label-operator is a non-invasive background process that ensures all provider resources are properly labeled for discovery. It handles labeling automatically, supports retroactive labeling after outages, and integrates seamlessly with kro's RGD composition patterns. You typically don't need to interact with it directly, but understanding how it works helps when debugging `labelSelector` lookup issues or understanding resource ownership.
