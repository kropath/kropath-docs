# SSMDocument — Operational Runbooks and Automation

The `SSMDocument` resource represents a single AWS Systems Manager document—a runbook, automation script, or command definition used for operational tasks on managed instances or AWS resources.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SSMConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the document name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted: `"retain"` (safe) or `"delete"` |

### Document Properties

| Field | Type | Default | Purpose |
|---|---|---|---|
| `content` | string | (required) | Document body in JSON or YAML format; max 64 KB |
| `documentType` | string | `"Command"` | Document type: Command, Policy, Automation, Session, Package, ApplicationConfiguration, ApplicationConfigurationSchema |
| `documentFormat` | string | `"JSON"` | Format of content: JSON, YAML, or TEXT |
| `displayName` | string | `""` | Friendly name for the document version (mutable) |
| `targetType` | string | `""` | CloudFormation resource type this document targets (e.g., `/AWS::EC2::Instance`); empty = all resources |
| `versionName` | string | `""` | Artifact version label; **immutable after creation** |
| `attachments` | []object | `[]` | List of document attachments (keys, names, values) |
| `requires` | []object | `[]` | List of required documents (name, requireType, version, versionName) |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels synchronized to AWS tags |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations synchronized to AWS tags |

## Document Types

Choose a document type based on your use case:

| Type | Purpose | Example |
|---|---|---|
| **Command** | Execute commands on managed instances (default) | Run shell scripts, install software |
| **Automation** | Multi-step automation workflows | Complex operational procedures |
| **Policy** | Configuration compliance policies | Enforce system configurations |
| **Session** | Define Session Manager session configuration | Interactive instance access |
| **Package** | Bundle executable content | Application deployments |
| **ApplicationConfiguration** | Application configuration schema | Define app-specific settings |
| **ApplicationConfigurationSchema** | Schema for application config | Validation rules |

**Default:** If not specified, defaults to `Command`.

## Complete Example: Automation Runbook

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMDocument
metadata:
  name: backup-automation
  namespace: ops
spec:
  configRef: general-policy
  deletionPolicy: retain
  documentType: Automation
  displayName: "Weekly Backup Automation v1"
  versionName: "1.0"
  content: |
    {
      "schemaVersion": "0.3",
      "description": "Automated backup workflow",
      "mainSteps": [
        {
          "name": "BackupStep",
          "action": "aws:executeScript",
          "inputs": {
            "Runtime": "python3.8",
            "Handler": "backup_handler",
            "Script": "import boto3\ndef backup_handler(events, context):\n  print('Backup started')\n  return {'status': 'success'}"
          }
        }
      ]
    }
  tags:
    Purpose: Backup
    Team: Operations
    Environment: Production
  syncedLabels:
    critical: "true"
```

Result:
- Automation document with automatic versioning
- Accessible via `alias/ops-backup-automation`
- Tags synced to AWS
- Immutable `versionName` prevents accidental overwrites

## Example: Command Document

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMDocument
metadata:
  name: health-check
  namespace: monitoring
spec:
  configRef: general-policy
  documentType: Command
  documentFormat: JSON
  content: |
    {
      "schemaVersion": "2.2",
      "description": "Run health checks on managed instances",
      "mainSteps": [
        {
          "action": "aws:runShellScript",
          "name": "example",
          "inputs": {
            "runCommand": [
              "#!/bin/bash",
              "echo 'Running health checks'",
              "systemctl status docker",
              "df -h"
            ]
          }
        }
      ]
    }
  tags:
    Type: Monitoring
```

## Example: Policy Document

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMDocument
metadata:
  name: enforce-firewall
  namespace: compliance
spec:
  configRef: general-policy
  documentType: Policy
  content: |
    {
      "schemaVersion": "1.2",
      "description": "Enforce firewall configuration",
      "mainSteps": [
        {
          "action": "aws:runShellScript",
          "name": "enforceFirewall",
          "inputs": {
            "runCommand": [
              "systemctl enable firewalld",
              "systemctl start firewalld"
            ]
          }
        }
      ]
    }
```

## Document Versioning

SSM documents automatically version when you update the `content`:

- **First creation:** Creates version `1`
- **Update content:** Automatically creates version `2`, `3`, etc.
- **`versionName`:** Optional version label (e.g., "1.0-stable"); immutable after creation
- **AWS maintains `$LATEST`:** Always points to the newest version

Example:

```yaml
# Initial document
apiVersion: aws.kropath.run/v1alpha1
kind: SSMDocument
metadata:
  name: my-runbook
  namespace: ops
spec:
  content: |
    { "schemaVersion": "0.3", "mainSteps": [...] }
  versionName: "1.0"  # Immutable after creation

# Later: Update content
# $ kubectl patch ssmdocument my-runbook --type merge -p '{"spec":{"content":"..."}}'
# Result: New version 2 is created; versionName stays "1.0"
```

## Document Naming

Document names must:
- Be 3-128 characters
- Contain only `a-zA-Z0-9_\-.` (alphanumeric, underscore, hyphen, period)
- NOT start with reserved prefixes: `aws`, `amazon`, `amzn`, `AWSEC2`, `AWSConfigRemediation`, `AWSSupport`

**Naming template resolution (ADR-015 §9):**

Default naming template: `{namespace}-{name}`

Supported tokens: `{name}`, `{namespace}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.<key>}`

Example:

```yaml
spec:
  tags:
    team: platform
    environment: prod
  # With naming template: "{namespace}-{team}-{environment}-{name}"
  # Resolves to: "ops-platform-prod-backup-automation"
```

If tokens are unresolved, `status.namingStatus: invalid-unresolved-tokens`.

## Status Fields

After creation, retrieve document details from status:

```yaml
status:
  resourceName: "ops-backup-automation"        # effectiveName
  namingStatus: "valid"                        # "valid" | "invalid-unresolved-tokens"
  documentVersion: "1"                         # Latest version number
  documentFormat: "JSON"                       # Format used
  predictedArn: "arn:aws:ssm:us-east-1:123456789012:document/ops-backup-automation"
  ackResourceMetadata:
    arn: "arn:aws:ssm:us-east-1:123456789012:document/ops-backup-automation"
```

## Immutability

After creation, these fields cannot be changed:

- **`versionName`** — Once set, cannot be updated
- **`documentType`** — Document type is locked at creation

Example of immutable field:

```bash
$ kubectl patch ssmdocument my-doc --patch '{"spec":{"versionName":"2.0"}}'
# Error: versionName is immutable after creation
```

To change document type, delete and recreate the resource.

## Attachments and Requirements

Documents can include attachments (media files, scripts) and declare dependencies on other documents:

### Attachments

```yaml
spec:
  content: |
    { "schemaVersion": "0.3", ... }
  attachments:
    - key: "s3object"
      name: "backup-script.sh"
      values:
        - "s3://my-bucket/scripts/backup-script.sh"
```

### Requirements

```yaml
spec:
  content: |
    { "schemaVersion": "0.3", ... }
  requires:
    - name: "AWS-ConfigureAWSPackage"
      requireType: "DocumentVersion"
      version: "1"
    - name: "my-custom-document"
      requireType: "Resource"
      version: "1"
```

## Governance Cascade

When you don't specify a field, kropath resolves it using governance:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMDocument
metadata:
  name: minimal-doc
  namespace: ops
spec:
  configRef: secure
  content: |
    { "schemaVersion": "0.3", "mainSteps": [...] }
  # documentType not specified — resolved by cascade
```

The cascade for `documentType`:
1. Check `secure` SSMConfig mandatory tier → `Automation`
2. Result: document gets `documentType=Automation`

Platform teams can enforce document types via governance:

```yaml
# In SSMConfig (secure profile)
spec:
  mandatory:
    documentType: Automation  # Force Automation
    allowedDocumentTypes: [Automation, Policy]
```

## Multiple Documents in One Manifest

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: SSMDocument
metadata:
  name: backup-automation
  namespace: ops
spec:
  documentType: Automation
  content: |
    { "schemaVersion": "0.3", "mainSteps": [...] }
---
apiVersion: aws.kropath.run/v1alpha1
kind: SSMDocument
metadata:
  name: health-check
  namespace: monitoring
spec:
  documentType: Command
  content: |
    { "schemaVersion": "2.2", "mainSteps": [...] }
```

## Best Practices

1. **Use descriptive names** — Include purpose and team in the document name
2. **Set `versionName`** — Make version labels immutable for release tracking
3. **Use governance profiles** — Let `SSMConfig` enforce document types and naming
4. **Reference required documents** — Declare dependencies via `requires`
5. **Test documents before production** — Use a dev profile for testing
6. **Store large content in S3** — If content exceeds 64 KB, split into attachments
7. **Use `retain` deletion policy** — Default; prevents accidental deletion
8. **Tag appropriately** — Include team, purpose, and compliance metadata

## Troubleshooting

**Document creation fails with "Invalid documentType"**
- Check `SSMConfig.mandatory.allowedDocumentTypes` for the profile you selected
- Verify your `documentType` is in the allowed list

**Naming validation fails**
- Check `status.namingStatus` for unresolved tokens
- Verify all `{tag.*}` references exist in `spec.tags`

**VersionName not updating**
- `versionName` is immutable after creation
- Create a new document or leave `versionName` empty for auto-versioning

## Next Steps

- [SSMConfig Governance](./ssmconfig.md) — Understanding document governance
- [AWS SSM User Guide](https://docs.aws.amazon.com/systems-manager/latest/userguide/documents.html) — AWS Systems Manager documents reference
