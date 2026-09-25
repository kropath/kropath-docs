---
title: AWS Organizations Resources
description: The Organizations resource family provides Kubernetes-native management of AWS Organizations accounts and organizational units (OUs).
doc_type: reference
weight: 390
---
# AWS Organizations Resources

The Organizations resource family provides Kubernetes-native management of AWS Organizations accounts and organizational units (OUs).

## Resources

- **[OrganizationsConfig](./organizationsconfig.md)** — Governance profiles for Organizations resources; defines policies for billing access, cross-account roles, and naming conventions
- **[OrganizationsAccount](./organizationsaccount.md)** — Creates and manages AWS member accounts within an organization
- **[OrganizationsOU](./organizationsou.md)** — Creates and manages organizational units for grouping accounts and applying policies

## Key Concepts

### Governance Tiers

All Organizations resources are governed through named profiles called `OrganizationsConfig`. Each profile defines policies in three tiers:

1. **Mandatory** — Enforced on all instances; overrides any instance-level setting
2. **Defaults** — Applied if the instance doesn't specify a value
3. **Instance override** — Developer-specified values in the resource CR

### Immutable Fields

- **OrganizationsAccount**: `iamUserAccessToBilling` and `roleName` are immutable after account creation
- **OrganizationsOU**: `parentID` is immutable after OU creation

Governance changes to these fields after resource creation surface as drift in the resource status but cannot be automatically remediated due to AWS API limitations.

### Asynchronous Account Creation

Account creation in AWS is asynchronous:

- Accounts start in `IN_PROGRESS` state
- Transition to `SUCCEEDED` when creation completes
- Transition to `FAILED` with a failure reason if creation fails
- The process can take minutes to complete

The resource status tracks this lifecycle via `accountState`, `createAccountRequestID`, and `failureReason`.

## Setup and Prerequisites

1. **Deploy OrganizationsConfig** in the `kro-system` namespace with named profiles (e.g., `general-policy`, `security-baseline`)
2. **Deploy KropathConfig** in `kro-system` with org-wide organizations governance (optional; any unset fields fall back to resource-level or built-in defaults)
3. **Deploy the controller** to write `status.effectiveConfig` on OrganizationsConfig CRs (part of the standard kropath installation)

## Quick Start

Create a basic governance profile:

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
    parentID: "r-ab12"
    namingTemplate: "{namespace}-{name}"
    tags: {}
```

Then create an account:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsAccount
metadata:
  name: dev-account
  namespace: workloads-dev
spec:
  email: "dev-team@example.com"
  configRef: "general-policy"
```

And an OU:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsOU
metadata:
  name: dev-ou
  namespace: workloads-dev
spec:
  configRef: "general-policy"
```
