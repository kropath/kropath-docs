---
title: "AWS Systems Manager (SSM) — Operations & Configuration"
description: The AWS SSM family within kropath provides abstractions for managing AWS Systems Manager resources.
doc_type: reference
weight: 520
---
# AWS Systems Manager (SSM) — Operations & Configuration

The AWS SSM family within kropath provides abstractions for managing AWS Systems Manager resources. It enables platform engineers to enforce organization-wide controls—such as mandatory encryption for parameters, approved document types, and default patch baselines—while allowing application teams to manage operational documents, configuration parameters, patch compliance, and inventory synchronization.

## Prerequisites and Setup

SSM resources can be created independently, but several integrate with other kropath families for end-to-end workflows:

*   **KMS Family:** For encrypting SecureString parameters (required for SSMParameter encryption)
*   **S3 Family:** For storing inventory data from SSMResourceDataSync

## Quick Start

To create your first SSM resources:

```yaml
---
# Configuration: Define organization-wide SSM governance
apiVersion: aws.kropath.run/v1alpha1
kind: SSMConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory:
    allowedDocumentTypes:
      - Command
      - Automation
  defaults:
    documentType: Command
    parameterType: String
---
# Example: Store a configuration parameter
apiVersion: aws.kropath.run/v1alpha1
kind: SSMParameter
metadata:
  name: db-connection-string
  namespace: production
spec:
  type: String
  value: "host=db.example.com;port=5432"
  description: "Database connection string for application"
---
# Example: Define an operational runbook
apiVersion: aws.kropath.run/v1alpha1
kind: SSMDocument
metadata:
  name: backup-runner
  namespace: ops
spec:
  documentType: Automation
  content: |
    {
      "schemaVersion": "0.3",
      "description": "Backup automation document",
      "mainSteps": [...]
    }
```

## Key Concepts

### SSMDocument — Operational Runbooks and Automation

An `SSMDocument` resource represents a single Systems Manager document—a runbook, automation script, or command definition used for operational tasks on managed instances or AWS resources.

- **Document types:** Command, Policy, Automation, Session, Package
- **Versioning:** Automatic via ACK controller (updating content creates new version)
- **Naming:** Custom names with reserved prefix enforcement
- **Governance:** Restrict document types, require specific naming patterns

### SSMParameter — Configuration and Secrets Storage

An `SSMParameter` resource represents a configuration value or secret in Parameter Store. Supports hierarchical naming and three parameter types:

- **String:** Plain text values (up to 4 KB standard, 8 KB advanced tier)
- **StringList:** Comma-separated values
- **SecureString:** Encrypted using KMS (requires KMS key reference)

### SSMPatchBaseline — Fleet Patch Compliance

An `SSMPatchBaseline` resource defines patch approval rules for operating systems. Configure which patches auto-approve, compliance severity levels, and rejected patches to block fleet-wide patching via Systems Manager Patch Manager.

### SSMResourceDataSync — Inventory Aggregation

An `SSMResourceDataSync` resource synchronizes SSM Inventory data to S3 buckets or across AWS accounts. Use it to centralize inventory reporting across your fleet.

### SSMConfig — Governance Profiles

`SSMConfig` CRs define per-profile governance settings for the SSM family. These profiles are referenced by SSM instances via `spec.configRef`. Each profile includes `mandatory` and `defaults` sections that control requirements across your organization.

**Example profiles:**
- `general-policy`: Balanced defaults (Command/Automation documents, String parameters)
- `secure`: Hardened (SecureString mandatory, specific KMS key, Advanced tier)
- `patching`: Patch compliance (AMAZON_LINUX_2, HIGH compliance level)

### Governance Cascade

Kropath employs a governance cascade (ADR-010, ADR-015) to resolve effective configuration. The `kropath-controller` pre-merges all governance sources into `status.effectiveConfig` on the namespaced `SSMConfig` CR. Instances read this configuration to determine final settings.

**When to use `KropathConfig.ssm` vs. `SSMConfig`:**
- **`KropathConfig.ssm`:** Org-wide governance (e.g., force all parameters to SecureString)
- **`SSMConfig`:** Per-profile governance (e.g., restrict a `secure` profile to Advanced tier parameters)

## Core Features

### Encryption and Security

SecureString parameters automatically encrypt values using AWS KMS:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMParameter
metadata:
  name: db-password
  namespace: production
spec:
  type: SecureString
  valueFrom:
    secretKeyRef:
      name: db-credentials  # Kubernetes Secret
      key: password
  keyID: "arn:aws:kms:us-east-1:123456789012:key/12345678-..."
  description: "Database password for production"
```

**Note:** SecureString parameters require `spec.valueFrom` referencing a Kubernetes Secret, not `spec.value`. This prevents sensitive data from leaking into git repositories in GitOps workflows.

### Hierarchical Parameter Naming

Parameters support hierarchical paths to organize configurations:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMParameter
metadata:
  name: db-password
  namespace: production
spec:
  value: "secretpassword"
  # With naming template "/{tag.env}/db/{name}"
  # Resolves to: "/prod/db/db-password"
```

### Parameter Tier Management

Standard tier supports up to 4 KB of data; Advanced tier supports up to 8 KB. Upgrade from Standard to Advanced is **one-way and irreversible** without deleting and recreating the parameter:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMParameter
metadata:
  name: large-config
  namespace: production
spec:
  type: String
  value: "..."  # Large value > 4 KB
  tier: Advanced  # Upgrade from Standard (cannot revert)
```

## Document Governance

Restrict which document types can be created across your organization:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMConfig
metadata:
  name: secure
  namespace: kro-system
spec:
  mandatory:
    allowedDocumentTypes:
      - Command
      - Automation
    # Setting documentType forces ALL documents to this type
    # documentType: Automation  # Uncomment to enforce Automation only
```

## Patch Baseline Management

Define compliance rules for fleet-wide patching:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMPatchBaseline
metadata:
  name: amazon-linux-2
  namespace: ops
spec:
  operatingSystem: AMAZON_LINUX_2
  approvedPatchesComplianceLevel: HIGH
  approvedPatchesEnableNonSecurity: false
  rejectedPatchesAction: BLOCK
  approvalRules:
    patchRules:
      - approveAfterDays: 7
        complianceLevel: CRITICAL
```

**Important:** The `globalFilters` field is only configurable via CLI/SDK—not available in the AWS Patch Manager console.

## Cross-Family References

SSM resources integrate with:
- **KMS:** `SSMParameter` can reference a `KMSKey` for SecureString encryption via `spec.keyRef` or direct ARN
- **S3:** `SSMResourceDataSync` writes inventory data to S3 buckets
- **Kubernetes Secrets:** `SSMParameter` with SecureString reads sensitive values from Kubernetes Secrets via `spec.valueFrom.secretKeyRef`

## Next Steps

For detailed guidance, see:
- [SSMConfig Governance](./ssmconfig.md) — Understanding mandatory vs. defaults tiers and profile management
- [SSMDocument Guide](./ssmdocument.md) — Creating and managing operational runbooks
- [SSMParameter Guide](./ssmparameter.md) — Storing configuration and secrets
- [SSMPatchBaseline Guide](./ssmpatchbaseline.md) — Setting up fleet patch compliance
- [SSMResourceDataSync Guide](./ssmresourcedatasync.md) — Synchronizing inventory data

## Out-of-Scope (Phase 2+)

The following SSM features are not yet supported:
- SSM Maintenance Windows (complex scheduling and task orchestration)
- SSM Associations (linking documents to managed instances)
- SSM State Manager (state tracking for documents)
- SSM Run Command (ad hoc execution)
- SSM Session Manager (interactive sessions)
