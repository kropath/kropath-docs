---
title: SageMakerUserProfile — User Identity in Studio
description: "The `SageMakerUserProfile` resource represents a user profile within a SageMaker Studio domain — an individual user's identity, permissions, and workspace configuration."
doc_type: reference
---
# SageMakerUserProfile — User Identity in Studio

The `SageMakerUserProfile` resource represents a user profile within a SageMaker Studio domain — an individual user's identity, permissions, and workspace configuration. Each user profile is scoped to a domain and can have custom execution roles, sharing policies, and user settings.

## Core Fields

### User Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted: `"retain"` (keeps AWS profile) or `"delete"` (deletes AWS profile) |
| `domainId` | string | required | ID of the parent SageMaker domain |
| `userName` | string | required | The user's name within the domain |

### User Settings

| Field | Type | Default | Purpose |
|---|---|---|---|
| `userSettings` | object | optional | Execution role, sharing settings, and user-specific defaults |
| `singleSignOnUserIdentifier` | string | optional | SSO user identifier (required if domain uses SSO auth) |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation, the user profile's status contains:

| Field | Type | Purpose |
|---|---|---|
| `userProfileArn` | string | The ARN of the user profile in AWS |
| `conditions` | array | Status conditions (ready, error, etc.) |

## Naming Convention

User profiles are identified by their username within the domain. The `userName` field directly maps to the AWS user profile name (no template).

**AWS constraints:**
- Max 63 characters
- Alphanumeric, hyphens, and underscores
- Unique within the domain

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerUserProfile
metadata:
  name: data-scientist-1
  namespace: ml-team
spec:
  configRef: ml-production
  domainId: d-12345678abcd
  userName: john-doe
  userSettings:
    executionRole: arn:aws:iam::123456789012:role/SageMakerUserExecutionRole
    sharingSettings:
      notebookOutputOption: AllowSharedNotebookAccess
  tags:
    Team: ml-platform
    Role: data-scientist
```

## Dependencies

- **Requires:** Parent `SageMakerDomain` (specified by `domainId`)
- **Governance:** `SageMakerConfig` for execution role enforcement and sharing policies
