# OrganizationsAccount

`OrganizationsAccount` is a Kubernetes resource that represents an AWS member account within an organization. It wraps the ACK `organizations.services.k8s.aws/Account` CR and provides a higher-level interface for creating accounts with governance policies, cross-account access roles, billing control, and standard naming and metadata conventions.

## Scope

This resource is AWS-only. It is specific to AWS Organizations. GCP Cloud Resource Manager Projects and Azure Subscriptions have different creation models and APIs.

## What it Solves

Creating member accounts in AWS Organizations involves many decisions:

- **Email uniqueness** — Each account needs a globally unique email address
- **Cross-account access** — A role must be auto-provisioned in the new account for management access
- **Billing control** — Whether users can access billing information for the account
- **Naming** — Account display names should follow a consistent scheme
- **Governance** — Every account should follow org-wide policies for access control, metadata, and naming
- **Asynchronous creation** — Accounts take minutes to create; you need visibility into progress
- **Deletion policy** — What happens when the CR is deleted (retain or delete the cloud account)

Manually managing these creates inconsistency and operational overhead. `OrganizationsAccount` solves this by providing:

- **Structured governance** — Inherit billing access and role names from an `OrganizationsConfig` profile
- **Automatic naming** — Account names are generated from a template
- **Async visibility** — See creation progress, failures, and account IDs in the resource status
- **Role auto-provisioning** — Specify the cross-account role name once; it's auto-created in every new account
- **Tag and label enforcement** — Org-wide and instance-level tags synced to both Kubernetes and AWS
- **Deletion policy** — Choose whether to delete the cloud account when the CR is deleted

## Core Concepts

### Account Creation Lifecycle

AWS account creation is asynchronous:

1. **`IN_PROGRESS`** — The CreateAccount request is being processed
2. **`SUCCEEDED`** — Account was created successfully; `accountID` is now available
3. **`FAILED`** — Account creation failed; `failureReason` explains why

The resource status tracks this lifecycle via the `accountState` field. Account creation typically completes within 10–15 minutes but can take longer depending on AWS load.

### Immutable Fields

Two fields are set at account creation time and cannot be updated:

- **`iamUserAccessToBilling`** — Billing access permission; immutable
- **`roleName`** — Cross-account IAM role name; immutable

If a governance policy for these fields changes after account creation, the change surfaces as drift in the resource status but cannot be automatically remediated. You must delete and recreate the account to apply the new policy.

### Governance Profile Selection

Accounts reference a governance profile via `spec.configRef`:

```yaml
spec:
  configRef: "security-baseline"  # Use the security-baseline profile
```

If the named profile doesn't exist, the resource automatically falls through to the `general-policy` profile.

## Resource Configuration

### Spec Fields

```yaml
spec:
  configRef: string
    # Profile name to inherit governance policies from.
    # Falls through to "general-policy" if not found.
    # Default: "general-policy"

  nameOverride: string
    # Explicit account display name; bypasses the naming template.
    # Default: "" (use template)

  deletionPolicy: string
    # What happens when the CR is deleted: "retain" or "delete".
    # Default: "retain"

  email: string
    # REQUIRED — Globally unique email for the account owner.
    # Format: standard email address (RFC 5322 simplified).

  iamUserAccessToBilling: string
    # Billing access: "allow" | "deny" | ""
    # Empty ("") falls through to the governance profile.
    # Immutable after creation.
    # Default: ""

  roleName: string
    # Cross-account IAM role name (e.g., "OrganizationAccountAccessRole").
    # Must match AWS IAM role name pattern: ^[\w+=,.@-]{1,64}$
    # Empty ("") falls through to the governance profile.
    # Immutable after creation.
    # Default: ""

  tags: map<string,string>
    # Instance-level cloud tags.
    # Merged with governance policy tags; instance tags override defaults.
    # Default: {}

  syncedLabels: map<string,string>
    # Labels to sync to both Kubernetes metadata and AWS cloud tags.
    # Each label is prefixed with "aws.kropath.run/" in K8s and synced to cloud tags.
    # Default: {}

  syncedAnnotations: map<string,string>
    # Annotations to sync to Kubernetes metadata.
    # Each annotation is prefixed with "aws.kropath.run/" in K8s.
    # Default: {}
```

### Status Fields

```yaml
status:
  resourceName: string
    # Effective account display name (after template expansion).

  namingStatus: string
    # "valid" | "invalid-unresolved-tokens"
    # Indicates whether the naming template resolved successfully.

  accountID: string
    # 12-digit AWS account ID (populated after creation succeeds).

  accountArn: string
    # Account ARN (e.g., arn:aws:organizations::123456789012:account/o-abc/123456789012).

  accountState: string
    # "IN_PROGRESS" | "SUCCEEDED" | "FAILED"

  createAccountRequestID: string
    # Async request tracking ID; use this in AWS console to check progress.

  failureReason: string
    # Reason for creation failure if state is "FAILED"
    # (e.g., "EMAIL_ALREADY_EXISTS").

  completedTimestamp: string
    # When account creation completed (timestamp).

  conditions: array
    # Standard Kubernetes conditions for lifecycle events and errors.
```

## Complete Example

### Step 1: Create a Governance Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  defaults:
    iamUserAccessToBilling: "allow"
    roleName: "OrganizationAccountAccessRole"
    namingTemplate: "{namespace}-{name}"
    tags:
      cost-centre: platform
    syncedLabels:
      team: infrastructure
```

### Step 2: Create an Account

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsAccount
metadata:
  name: dev-account
  namespace: workloads-dev
spec:
  email: "dev-team@example.com"
  configRef: "general-policy"
  tags:
    project: alpha
  syncedLabels:
    environment: development
```

### Step 3: Monitor Creation Progress

```bash
kubectl get organizationsaccount dev-account -n workloads-dev -o yaml

# Watch the status fields:
# - accountState: IN_PROGRESS → SUCCEEDED
# - accountID: populated when SUCCEEDED
# - createAccountRequestID: use to track progress in AWS console
```

### Step 4: Retrieve the Account ID

```bash
ACCOUNT_ID=$(kubectl get organizationsaccount dev-account -n workloads-dev \
  -o jsonpath='{.status.accountID}')

# Use this to assume the cross-account role in the new account:
aws sts assume-role \
  --role-arn arn:aws:iam::${ACCOUNT_ID}:role/OrganizationAccountAccessRole \
  --role-session-name admin-session
```

## Governance Cascade

The billing access and role name are resolved through a three-tier cascade:

1. **Mandatory policy** (from `OrganizationsConfig.spec.mandatory`) → overrides all
2. **Instance specification** (`spec.iamUserAccessToBilling`, `spec.roleName`)
3. **Defaults policy** (from `OrganizationsConfig.spec.defaults`)
4. **RGD built-in default** → `"allow"` for billing access, `"OrganizationAccountAccessRole"` for role name

Tags are merged additively:

```
result.tags = mandatory.tags + instance.tags + defaults.tags
```

Mandatory tags cannot be removed by the instance.

## Naming Convention

Account display names are generated from a template unless overridden:

- **Default template**: `{namespace}-{name}`
- **Override**: Set `spec.nameOverride` to use an explicit name (bypasses the template)
- **Tokens**: `{namespace}`, `{name}`, `{tag.X}` (value of tag `X`)

Example:

- Namespace: `workloads-prod`
- CR name: `api-account`
- Template: `{namespace}-{name}`
- Result: `workloads-prod-api-account`

If a token in the template is unresolved (e.g., tag `env` is referenced but not defined), the resource enters a `namingStatus: "invalid-unresolved-tokens"` state and the account is not created.

## Deletion Policy

### Retain (Default)

```yaml
spec:
  deletionPolicy: "retain"
```

When the CR is deleted, the AWS account is retained. Useful for accounts you want to keep running independently.

### Delete

```yaml
spec:
  deletionPolicy: "delete"
```

When the CR is deleted, the AWS account is also deleted. Use with caution; this is irreversible.

## Account Creation Failures

Common failure reasons:

- **`EMAIL_ALREADY_EXISTS`** — The email is already used by another account. Choose a unique email.
- **`INVALID_EMAIL_ADDRESS`** — The email format is invalid.
- **`ACCOUNT_NOT_CREATED`** — Creation failed due to an AWS internal error. Try again.

Check the `failureReason` and `createAccountRequestID` in the resource status to troubleshoot:

```bash
kubectl describe organizationsaccount dev-account -n workloads-dev
```

## Synced Labels and Annotations

### Synced Labels

Labels in `spec.syncedLabels` are:

1. Added to the ACK `Account` child resource's Kubernetes metadata with the `aws.kropath.run/` prefix
2. Also synced to AWS cloud tags (without the prefix)

Example:

```yaml
spec:
  syncedLabels:
    environment: development
    team: platform
```

Results in:

- K8s label: `aws.kropath.run/environment: development`
- AWS tag: `environment: development`

### Synced Annotations

Annotations in `spec.syncedAnnotations` are added to the ACK `Account` child resource with the `aws.kropath.run/` prefix.

## Best Practices

### 1. Use Globally Unique Emails

Email addresses are globally unique within a single AWS organization. Choose a naming scheme that avoids collisions:

```yaml
spec:
  email: "team-${NAMESPACE}@${DOMAIN}.com"
```

### 2. Leverage Governance Profiles

Create multiple profiles for different risk levels or compliance tiers:

```yaml
---
# General-purpose profile
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  defaults:
    iamUserAccessToBilling: "allow"
---
# Security-sensitive profile
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsConfig
metadata:
  name: security-baseline
  namespace: kro-system
spec:
  mandatory:
    iamUserAccessToBilling: "deny"
```

### 3. Monitor Creation Progress

Account creation is async. Use the `createAccountRequestID` to track progress:

```bash
aws organizations describe-create-account-status \
  --request-id $(kubectl get organizationsaccount dev-account -n workloads-dev \
    -o jsonpath='{.status.createAccountRequestID}')
```

### 4. Plan for Immutable Field Changes

Since `iamUserAccessToBilling` and `roleName` are immutable, finalize governance policies before account creation. If a policy must change, delete and recreate the account.

### 5. Use Naming Templates for Consistency

Avoid manual names; use templates to ensure consistency:

```yaml
spec:
  nameOverride: ""  # Use the template
  # Relies on OrganizationsConfig.defaults.namingTemplate
```

## Differences from AWS Console

Creating accounts via Kubernetes is functionally equivalent to using the AWS Organizations console, with these differences:

- **Synchronous workflow** — Console requests are async; watch the status for completion
- **Immutable fields** — Role name and billing access cannot be changed after creation via the RGD
- **Governance enforcement** — Mandatory policies override any instance-level override
- **Automatic naming** — Names are generated from templates; no manual name input
- **Cross-account role** — Auto-provisioned with the specified role name; no manual IAM setup needed
