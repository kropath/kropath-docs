# ManagedPrometheusLoggingConfiguration

A `ManagedPrometheusLoggingConfiguration` routes workspace vended logs from an AWS Managed Service for Prometheus workspace to a CloudWatch Logs log group. Exactly one logging configuration is allowed per workspace.

## Overview

`ManagedPrometheusLoggingConfiguration` is a singleton per workspace. It enables and configures the routing of AMP workspace logs to CloudWatch Logs for centralized observability. Platform teams can enforce standardized log destinations via the `ManagedPrometheusConfig` `logGroupARN` governance field.

## Configuration Fields

```yaml
spec:
  configRef              string   default="general-policy"
                                  # Selects ManagedPrometheusConfig profile
  deletionPolicy         string   default="retain"
                                  # retain | delete
  syncedLabels           map      default={}
                                  # K8s labels AND AWS tags (prefixed aws.kropath.run/)
  syncedAnnotations      map      default={}
                                  # K8s annotations (prefixed aws.kropath.run/)
  
  # LoggingConfiguration-specific
  logGroupARN            string   required OR governed
                                  # ARN of target CloudWatch log group;
                                  # governance cascade applies (mandatory → instance → defaults);
                                  # must be valid CloudWatch Logs ARN;
                                  # regex: ^arn:aws[a-z0-9-]*:logs:[a-z0-9-]+:\d{12}:log-group:[...]{1,512}:\*$
  workspaceRef           string   required
                                  # Reference to ManagedPrometheusWorkspace CR
                                  # (metadata.name in the same namespace)
```

### Governance Fields

| Field | Governance | Notes |
|---|---|---|
| `logGroupARN` | Mandatory → instance → defaults | Platform teams can enforce a standard log destination. If all tiers are empty, `logGroupARN` is required. |
| `syncedLabels` | Merged: mandatory + instance + defaults | K8s labels on the logging configuration resource |
| `syncedAnnotations` | Merged: mandatory + instance + defaults | K8s annotations on the logging configuration resource |

### Status Fields

```yaml
status:
  statusCode             string   # CREATING | ACTIVE | UPDATE_FAILED
  statusReason           string   # Failure reason (empty when healthy)
  conditions             array    # Standard Kubernetes conditions
```

## Naming & Tags

**Naming exemption (KRO-236).** This resource has no provider `name` field and is a singleton per workspace. Omitted: `spec.nameOverride`, `status.resourceName`, `status.predictedArn`, `status.namingStatus`.

**Tag exemption:** This resource has no `spec.tags` field in the upstream AWS API. Cloud tags do not apply. Only `syncedLabels` and `syncedAnnotations` are available for governance.

## Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusLoggingConfiguration
metadata:
  name: logs
  namespace: monitoring
spec:
  configRef: general-policy
  workspaceRef: prod-metrics
  logGroupARN: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/amp/prod-metrics:*"
  syncedLabels:
    logging: enabled
  syncedAnnotations:
    log-destination: cloudwatch
  deletionPolicy: retain
```

## Common Patterns

### Governance-Enforced Logging

Platform team enforces all workspaces to log to a central location:

```yaml
# ManagedPrometheusConfig in kro-system
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusConfig
metadata:
  name: logging-required
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: logging-required
spec:
  mandatory:
    logGroupARN: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/amp/central:*"
  defaults: {}

---
# Developer creates LoggingConfiguration
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusLoggingConfiguration
metadata:
  name: logs
  namespace: monitoring
spec:
  configRef: logging-required
  workspaceRef: prod-metrics
  # logGroupARN is enforced by the config profile
```

### Optional Logging with Default

Platform provides a default log group but allows developers to override:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    logGroupARN: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/amp/default:*"

---
# Developer can override with custom log group
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusLoggingConfiguration
metadata:
  name: logs
  namespace: myapp
spec:
  configRef: general-policy
  workspaceRef: myapp-metrics
  logGroupARN: "arn:aws:logs:us-east-1:123456789012:log-group:/myapp/amp-logs:*"
```

### Development Logging

Minimal logging for development environments:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusLoggingConfiguration
metadata:
  name: logs
  namespace: observability-dev
spec:
  configRef: dev  # Uses development profile
  workspaceRef: dev-metrics
  logGroupARN: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/amp/dev:*"
  deletionPolicy: delete  # Safe to delete in dev
```

## How to Deploy

1. Ensure the target CloudWatch Logs log group exists. If managed by the CloudWatch Logs family, create it first:

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsLogGroup
metadata:
  name: amp-logs
  namespace: observability
spec:
  logGroupName: /aws/amp/prod-metrics
  retentionInDays: 7
EOF
```

2. Create the logging configuration:

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusLoggingConfiguration
metadata:
  name: logs
  namespace: monitoring
spec:
  configRef: general-policy
  workspaceRef: prod-metrics
  logGroupARN: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/amp/prod-metrics:*"
  deletionPolicy: retain
EOF
```

3. Verify creation:

```bash
kubectl get managedprometheusloggingconfiguration -n monitoring
kubectl describe managedprometheusloggingconfiguration logs -n monitoring
```

## Prerequisites

- **Workspace exists** — A `ManagedPrometheusWorkspace` CR matching `spec.workspaceRef` must exist
- **Log group exists** — The CloudWatch Logs log group specified in `logGroupARN` must be pre-created
- **Valid ARN** — The `logGroupARN` must be a valid CloudWatch Logs log group ARN
- **Governance profile** — A `ManagedPrometheusConfig` CR matching `spec.configRef` must exist
- **Singleton constraint** — Only one logging configuration per workspace
- **IAM permissions** — The cluster must have permission to create `LoggingConfiguration` resources in AMP

## Limitations

- **Singleton per workspace** — A second creation attempt on the same workspace will fail
- **ARN validation** — AWS validates the ARN format; invalid ARNs are rejected
- **Log group must exist** — The target CloudWatch Logs log group must be pre-created
- **No automatic log group creation** — Kropath does not create log groups; use CloudWatch Logs family resources instead

## CloudWatch Logs Integration

AMP logs can be viewed in CloudWatch Logs:

```bash
# View logs in CloudWatch Logs
aws logs tail /aws/amp/prod-metrics --follow
```

For more details on log group management, see [CloudWatch Logs](../cloudwatchlogs/index.md).

## Related Resources

- [ManagedPrometheusWorkspace](./managedprometheusworkspace.md) — Workspace these logs originate from
- [ManagedPrometheusConfig](./managedprometheusconfig.md) — Governance configuration (logging destination)
- [CloudWatch Logs](../cloudwatchlogs/index.md) — Log group management
