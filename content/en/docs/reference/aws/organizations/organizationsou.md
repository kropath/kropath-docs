---
title: OrganizationsOU
description: "`OrganizationsOU` is a Kubernetes resource that represents an AWS organizational unit (OU) within an organization."
doc_type: reference
---
# OrganizationsOU

`OrganizationsOU` is a Kubernetes resource that represents an AWS organizational unit (OU) within an organization. It wraps the ACK `organizations.services.k8s.aws/OrganizationalUnit` CR and provides a higher-level interface for creating OUs with governance policies, parent placement, naming conventions, and standard metadata handling.

## Scope

This resource is AWS-only. It is specific to AWS Organizations. GCP Cloud Resource Manager Folders and Azure Management Groups have different hierarchy models and APIs.

## What it Solves

Creating organizational units (OUs) in AWS requires careful planning:

- **Hierarchy management** — OUs must be placed under a root or parent OU; wrong placement breaks policy application
- **Nesting limits** — AWS allows up to 5 levels of nesting; over-nesting causes creation failures
- **Naming** — OU names should follow a consistent scheme across the organization
- **Governance** — Every OU should follow org-wide policies for metadata and naming
- **Deletion policy** — What happens when the CR is deleted (retain or delete the cloud OU)
- **Restructuring constraints** — Parent placement is immutable; moving an OU requires deletion and recreation

Manually managing these creates complexity and operational overhead. `OrganizationsOU` solves this by providing:

- **Parent placement governance** — Inherit parent OU ID from an `OrganizationsConfig` profile
- **Automatic naming** — OU names are generated from a template
- **Immutability awareness** — Understand that parent placement cannot change post-creation
- **Tag and label enforcement** — Org-wide and instance-level tags synced to both Kubernetes and AWS
- **Deletion policy** — Choose whether to delete the cloud OU when the CR is deleted

## Core Concepts

### Organizational Hierarchy

OUs form a tree under the organization root:

```
Organization Root (r-xxxx)
├── Security OU (ou-xxxx-xxxxxxxx)
│   ├── Audit OU
│   └── Compliance OU
└── Workloads OU (ou-yyyy-yyyyyyyy)
    ├── Dev OU
    ├── Staging OU
    └── Prod OU
```

Each OU (except the root) has a parent ID (`r-xxxx` for root, or `ou-xxxx-xxxxxxxx` for another OU).

### Immutable Parent Placement

The parent OU ID is set at creation time and cannot be updated. AWS does not allow moving OUs between parents via the API. If you need to restructure the hierarchy, delete the OU and recreate it under the new parent.

### Parent ID Requirement

The `parentID` must resolve to a non-empty value. If all tiers (mandatory, instance, defaults) resolve to empty string, OU creation fails with an error.

### Governance Profile Selection

OUs reference a governance profile via `spec.configRef`:

```yaml
spec:
  configRef: "general-policy"  # Use the general-policy profile
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
    # Explicit OU display name; bypasses the naming template.
    # Default: "" (use template)

  deletionPolicy: string
    # What happens when the CR is deleted: "retain" or "delete".
    # Default: "retain"

  parentID: string
    # Parent root or OU ID.
    # Format: "r-xxxx" (root) or "ou-xxxx-xxxxxxxx" (OU).
    # Empty ("") falls through to the governance profile.
    # Immutable after creation.
    # Required to be non-empty after cascade resolution.
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
    # Effective OU display name (after template expansion).

  namingStatus: string
    # "valid" | "invalid-unresolved-tokens"
    # Indicates whether the naming template resolved successfully.

  ouID: string
    # System-assigned OU ID (populated after creation succeeds).
    # Format: "ou-xxxx-xxxxxxxx"

  ouArn: string
    # OU ARN (e.g., arn:aws:organizations::123456789012:ou/o-abc/ou-xxxx-xxxxxxxx).

  conditions: array
    # Standard Kubernetes conditions for lifecycle events and errors.
```

## Complete Example

### Step 1: Create a Governance Profile with Parent OU

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  defaults:
    parentID: "r-ab12cd"  # Root ID
    namingTemplate: "{namespace}-{name}"
    tags:
      cost-centre: platform
    syncedLabels:
      organization: core
```

### Step 2: Create an OU

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsOU
metadata:
  name: workloads-ou
  namespace: platform
spec:
  configRef: "general-policy"
  tags:
    tier: operational
  syncedLabels:
    team: infrastructure
```

### Step 3: Create a Child OU

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsOU
metadata:
  name: prod-ou
  namespace: platform
spec:
  configRef: "general-policy"
  parentID: "<ouID from workloads-ou status>"  # Reference the parent OU ID
  tags:
    tier: production
```

### Step 4: Verify OU Creation

```bash
kubectl get organizationsou prod-ou -n platform -o yaml

# Watch the status fields:
# - ouID: populated when creation succeeds
# - ouArn: populated when creation succeeds
```

## Governance Cascade

The parent ID is resolved through a three-tier cascade:

1. **Mandatory policy** (from `OrganizationsConfig.spec.mandatory`) → overrides all
2. **Instance specification** (`spec.parentID`)
3. **Defaults policy** (from `OrganizationsConfig.spec.defaults`)
4. **Unresolved** → Creation fails with an error

Tags are merged additively:

```
result.tags = mandatory.tags + instance.tags + defaults.tags
```

Mandatory tags cannot be removed by the instance.

## Naming Convention

OU display names are generated from a template unless overridden:

- **Default template**: `{namespace}-{name}`
- **Override**: Set `spec.nameOverride` to use an explicit name (bypasses the template)
- **Tokens**: `{namespace}`, `{name}`, `{tag.X}` (value of tag `X`)

Example:

- Namespace: `platform`
- CR name: `workloads-ou`
- Template: `{namespace}-{name}`
- Result: `platform-workloads-ou`

If a token in the template is unresolved (e.g., tag `env` is referenced but not defined), the resource enters a `namingStatus: "invalid-unresolved-tokens"` state and the OU is not created.

## Parent ID Validation

The parent ID must match one of these formats:

- **Root ID**: `^r-[a-z0-9]{4,32}$` (e.g., `r-ab12cd`)
- **OU ID**: `^ou-[a-z0-9]{4,32}-[a-z0-9]{8,32}$` (e.g., `ou-ab12-cd345678`)

Invalid formats are rejected at creation time.

## Deletion Policy

### Retain (Default)

```yaml
spec:
  deletionPolicy: "retain"
```

When the CR is deleted, the AWS OU is retained. The OU and all its child OUs and accounts remain intact.

### Delete

```yaml
spec:
  deletionPolicy: "delete"
```

When the CR is deleted, the AWS OU is also deleted. This only succeeds if the OU has no child accounts or OUs. Use with caution; this is irreversible.

## Restructuring Hierarchy

Since `parentID` is immutable, moving an OU to a different parent requires:

1. Create a new OU CR with the desired parent ID
2. Move all child accounts and OUs to the new OU (via their parent ID references)
3. Delete the old OU CR

The process is manual in Kubernetes to prevent accidental restructuring.

## Creating OU Chains

To create nested OUs, first create the parent, then reference its `ouID` in the child's `parentID`:

```yaml
---
# Parent OU
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsOU
metadata:
  name: workloads
  namespace: platform
spec:
  parentID: "r-ab12cd"  # Root
---
# Child OU (references parent's ouID from status)
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsOU
metadata:
  name: dev
  namespace: platform
spec:
  parentID: "ou-xx12-yy345678"  # Replace with parent OU's status.ouID
```

In practice, use `kubectl` to patch the child OU after the parent is created:

```bash
PARENT_OU_ID=$(kubectl get organizationsou workloads -n platform -o jsonpath='{.status.ouID}')
kubectl patch organizationsou dev -n platform --type merge -p '{"spec":{"parentID":"'${PARENT_OU_ID}'"}}'
```

## Synced Labels and Annotations

### Synced Labels

Labels in `spec.syncedLabels` are:

1. Added to the ACK `OrganizationalUnit` child resource's Kubernetes metadata with the `aws.kropath.run/` prefix
2. Also synced to AWS cloud tags (without the prefix)

Example:

```yaml
spec:
  syncedLabels:
    tier: operational
    team: platform
```

Results in:

- K8s label: `aws.kropath.run/tier: operational`
- AWS tag: `tier: operational`

### Synced Annotations

Annotations in `spec.syncedAnnotations` are added to the ACK `OrganizationalUnit` child resource with the `aws.kropath.run/` prefix.

## Best Practices

### 1. Plan Your OU Hierarchy in Advance

AWS allows up to 5 levels of nesting. Design your hierarchy before creating OUs:

```
Root
├── Security (level 1)
│   ├── Audit (level 2)
│   └── Compliance (level 2)
└── Workloads (level 1)
    ├── Dev (level 2)
    ├── Staging (level 2)
    └── Prod (level 2)
```

### 2. Use Governance Profiles for OU Tiers

Create profiles for different OU types:

```yaml
---
# For workload OUs
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsConfig
metadata:
  name: workload-ou-policy
  namespace: kro-system
spec:
  defaults:
    parentID: "ou-workloads-xxxxxxxx"
    namingTemplate: "{tag.env}-{name}"
---
# For security OUs
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsConfig
metadata:
  name: security-ou-policy
  namespace: kro-system
spec:
  mandatory:
    parentID: "ou-security-xxxxxxxx"
```

### 3. Document Parent-Child Relationships

Use comments or labels to document your OU hierarchy:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsOU
metadata:
  name: prod-ou
  namespace: platform
  labels:
    parent-ou: workloads  # References the workloads-ou CR
spec:
  # This OU is a child of workloads-ou
  parentID: "ou-xxxx-xxxxxxxx"
```

### 4. Test Hierarchy Changes in Staging

Before moving large numbers of accounts, test hierarchy changes in a staging organization:

1. Create the new hierarchy structure in staging
2. Move a small number of test accounts
3. Verify all policies and integrations work
4. Apply changes to production

### 5. Use Naming Templates for Consistency

Avoid manual names; use templates to ensure consistency:

```yaml
spec:
  nameOverride: ""  # Use the template
  tags:
    environment: prod
    tier: core
  # Naming template: "{tag.environment}-{tag.tier}-{name}"
  # Result: "prod-core-payment-ou"
```

### 6. Monitor Nesting Depth

Keep track of OU nesting depth to avoid exceeding AWS's 5-level limit:

```bash
# Calculate nesting depth
kubectl get organizationsou -A -o jsonpath='{range .items[*]}{.spec.parentID}{"\n"}{end}' | sort | uniq -c
```

## Differences from AWS Console

Creating OUs via Kubernetes is functionally equivalent to using the AWS Organizations console, with these differences:

- **Immutable parent placement** — Once created, an OU's parent cannot be changed; delete and recreate if needed
- **Governance enforcement** — Mandatory policies override any instance-level override
- **Automatic naming** — Names are generated from templates; no manual name input
- **Parent ID requirement** — Parent ID must be explicitly specified (no default "root" assumption)
- **Structured hierarchy** — Reference parent OUs by their ouID; no manual ID lookup needed
