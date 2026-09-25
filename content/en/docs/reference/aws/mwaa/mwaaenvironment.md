---
title: MWAAEnvironment — MWAA Instance Configuration
description: "The `MWAAEnvironment` resource creates and manages a fully configured MWAA (Managed Workflows for Apache Airflow) environment in AWS."
doc_type: reference
---
# MWAAEnvironment — MWAA Instance Configuration

The `MWAAEnvironment` resource creates and manages a fully configured MWAA (Managed Workflows for Apache Airflow) environment in AWS. Each environment is a complete Airflow runtime backed by S3 storage for DAGs, CloudWatch for logging, and VPC networking. Environments support independent autoscaling of workers and web servers, granular logging per Airflow component, and configuration management via `MWAAConfig` governance profiles.

## What It Does

An `MWAAEnvironment` CR orchestrates the creation of an AWS MWAA environment with:

- **DAG storage** — An S3 bucket location where your Airflow DAGs, plugins, and dependencies live
- **Execution role** — An IAM role with permissions to access the DAG bucket and other AWS resources
- **Networking** — VPC subnets and security groups for the Airflow runtime
- **Airflow configuration** — Version selection, environment sizing, logging, autoscaling, and Airflow `airflow.cfg` overrides
- **Governance** — Mandatory and default settings from a selected `MWAAConfig` profile
- **Lifecycle** — Automatic cleanup on deletion (configurable via `deletionPolicy`)

The environment is fully managed by Airflow and your configuration; you do not provision EC2 instances, databases, or other infrastructure yourself.

## Prerequisites

1. An S3 bucket containing your DAGs (required)
2. An IAM execution role with S3 and CloudWatch permissions (required)
3. VPC subnets in at least two Availability Zones (required)
4. A `MWAAConfig` governance profile (defaults to `general-policy` if not specified)
5. (Optional) VPC security groups for fine-grained network control
6. (Optional) KMS key for encryption at rest
7. (Optional) Custom plugins and requirements files in S3

## Cluster Setup

Ensure your cluster has:
- `MWAAConfig` profiles deployed in `kro-system` namespace (or use `general-policy` default)
- (Optional) VPC endpoint readiness ConfigMaps if using `CUSTOMER` endpoint management mode
- (Optional) Custom KMS keys for encryption

## Core Fields

### Governance Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | "general-policy" | Name of the `MWAAConfig` profile that provides governance policies |
| `nameOverride` | string | "" | If set, bypasses the naming template and uses this literal name for the MWAA environment |

### DAG and Code Storage

| Field | Type | Required | Purpose |
|---|---|---|---|
| `dagS3Path` | string | Yes | Relative path to DAGs folder on the S3 bucket (e.g., `dags`) |
| `sourceBucketARN` | string | Yes | ARN of the S3 bucket storing DAGs and supporting files (e.g., `arn:aws:s3:::my-dag-bucket`) |
| `pluginsS3Path` | string | No | Relative path to `plugins.zip` on S3 bucket |
| `pluginsS3ObjectVersion` | string | No | S3 object version of `plugins.zip`; required when `pluginsS3Path` is set |
| `requirementsS3Path` | string | No | Relative path to `requirements.txt` on S3 |
| `requirementsS3ObjectVersion` | string | No | S3 object version of `requirements.txt`; required when `requirementsS3Path` is set |
| `startupScriptS3Path` | string | No | Relative path to startup shell script on S3 |
| `startupScriptS3ObjectVersion` | string | No | S3 object version of startup script; required when `startupScriptS3Path` is set |

### Execution and Networking

| Field | Type | Required | Purpose |
|---|---|---|---|
| `executionRoleARN` | string | Yes | IAM role ARN for Airflow to access S3, CloudWatch, and other AWS services |
| `networkConfiguration.subnetIDs` | list of strings | Yes | EC2 subnet IDs (minimum 2, in different Availability Zones); immutable after creation |
| `networkConfiguration.securityGroupIDs` | list of strings | No | EC2 security group IDs for network access control; if omitted, a default is created |

### Environment Configuration

| Field | Type | Default | Governed | Purpose |
|---|---|---|---|---|
| `airflowVersion` | string | "" | Yes | Airflow version (e.g., `2.10.3`); "" = falls through to MWAAConfig defaults |
| `environmentClass` | string | "" | Yes | Environment sizing: mw1.micro \| mw1.small \| mw1.medium \| mw1.large \| mw1.xlarge \| mw1.2xlarge; "" = falls through |
| `airflowConfigurationOptions` | map | {} | Yes | Key-value overrides for `airflow.cfg` settings; merged with governance policies |
| `webserverAccessMode` | string | "" | Yes | Web server access: PUBLIC_ONLY \| PRIVATE_ONLY; "" = falls through to MWAAConfig |
| `endpointManagement` | string | "" | Yes | VPC endpoint model: SERVICE \| CUSTOMER; "" = falls through to MWAAConfig; immutable |
| `kmsKeyARN` | string | "" | Yes | KMS key ARN for encryption at rest; "" = AWS-managed; immutable |

### Scaling

| Field | Type | Default | Governed | Immutable | Purpose |
|---|---|---|---|---|---|
| `maxWorkers` | integer | 0 | Yes | No | Max Celery workers (1–10); 0 = falls through to governance |
| `minWorkers` | integer | 0 | Yes | No | Min Celery workers (1–10); 0 = falls through to governance |
| `maxWebservers` | integer | 0 | Yes | No | Max web servers (1–5); 0 = falls through to governance |
| `minWebservers` | integer | 0 | Yes | No | Min web servers (1–5); 0 = falls through to governance |
| `schedulers` | integer | 0 | Yes | No | Scheduler processes (1–5); mw1.micro always 1; 0 = falls through to governance |

### Maintenance and Logging

| Field | Type | Default | Governed | Purpose |
|---|---|---|---|---|
| `weeklyMaintenanceWindowStart` | string | "" | Yes | Maintenance window in DAY:HH:MM UTC format (e.g., `SUN:03:00`); "" = MWAA chooses |
| `loggingConfiguration.dagProcessingLogs.enabled` | boolean | nil | Yes | Enable DAG processing logs; nil = falls through to governance |
| `loggingConfiguration.dagProcessingLogs.logLevel` | string | "" | Yes | Log level: CRITICAL \| ERROR \| WARNING \| INFO \| DEBUG; "" = falls through |
| `loggingConfiguration.schedulerLogs.enabled` | boolean | nil | Yes | Enable scheduler logs; nil = falls through |
| `loggingConfiguration.schedulerLogs.logLevel` | string | "" | Yes | Scheduler log level; "" = falls through |
| `loggingConfiguration.taskLogs.enabled` | boolean | nil | Yes | Enable task logs; nil = falls through |
| `loggingConfiguration.taskLogs.logLevel` | string | "" | Yes | Task log level; "" = falls through |
| `loggingConfiguration.webserverLogs.enabled` | boolean | nil | Yes | Enable web server logs; nil = falls through |
| `loggingConfiguration.webserverLogs.logLevel` | string | "" | Yes | Web server log level; "" = falls through |
| `loggingConfiguration.workerLogs.enabled` | boolean | nil | Yes | Enable worker logs; nil = falls through |
| `loggingConfiguration.workerLogs.logLevel` | string | "" | Yes | Worker log level; "" = falls through |

### Metadata and Lifecycle

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | {} | AWS tags for the environment resource |
| `syncedLabels` | map | {} | Kubernetes labels that are also synced to AWS tags (ADR-015 §6.1) |
| `syncedAnnotations` | map | {} | Kubernetes annotations synced to the environment |
| `deletionPolicy` | string | "retain" | Behavior on CR deletion: "retain" = keep MWAA environment, "delete" = terminate environment |

## Naming Convention

The environment's cloud name is determined by the naming template from your selected `MWAAConfig` profile, with these tokens available:

- `{name}` — Your Kubernetes resource name
- `{namespace}` — Your resource's namespace
- `{configRef}` — The selected governance profile name
- `{account_id}` — AWS account ID from `KropathConfig`
- `{region}` — AWS region from `KropathConfig`
- `{tag.KEY}` — Any tag from your environment's merged tags

**AWS Constraints:** Environment names must:
- Start with a letter (a–z, A–Z)
- Contain only alphanumeric characters, hyphens, and underscores
- Be 1–80 characters long

The default template `mwaa-{namespace}-{name}` ensures names start with a letter via the `mwaa-` prefix.

### Using `nameOverride`

If you need a specific literal name instead of a generated one:

```yaml
spec:
  nameOverride: my-airflow-environment
```

This bypasses the naming template entirely. You are responsible for ensuring the name meets AWS constraints.

## Status Outputs

After the controller reconciles an `MWAAEnvironment`, these read-only fields are populated:

| Field | Type | Purpose |
|---|---|---|
| `status.resourceName` | string | The effective cloud name (from naming template or `nameOverride`) |
| `status.namingStatus` | string | "valid" = name is valid; "invalid-unresolved-tokens" = template has unresolved tokens |
| `status.predictedArn` | string | AWS ARN: `arn:aws:airflow:<region>:<accountId>:environment/<resourceName>` |
| `status.environmentStatus` | string | MWAA environment state: CREATING \| CREATE_FAILED \| AVAILABLE \| UPDATING \| ROLLING_BACK \| DELETING \| DELETED \| UNAVAILABLE \| UPDATE_FAILED \| CREATING_SNAPSHOT \| PENDING \| MAINTENANCE |
| `status.webserverURL` | string | Airflow web UI URL (read-only, populated by MWAA) |
| `status.createdAt` | date-time | Environment creation timestamp (read-only) |
| `status.conditions` | array | Standard Kubernetes conditions for tracking reconciliation state |

## Immutable Fields

These fields cannot be changed after the environment is created:

| Field | Reason |
|---|---|
| `networkConfiguration.subnetIDs` | VPC networking is determined at environment creation and cannot be changed |
| `endpointManagement` | VPC endpoint model is immutable (SERVICE → CUSTOMER or vice versa requires recreation) |
| `kmsKeyARN` | Encryption key is set at creation and cannot be rotated through this field |

To change immutable fields, you must delete the environment and create a new one.

## Governance Cascade

All fields marked "Governed: Yes" follow this cascade:

```
MWAAConfig.mandatory.<field>  →  instance spec.<field>  →  MWAAConfig.defaults.<field>
```

- If `MWAAConfig.mandatory.<field>` is set, that value is used (instance override is ignored)
- Otherwise, if instance `spec.<field>` is set to a non-default value, that value is used
- Otherwise, `MWAAConfig.defaults.<field>` is used
- Otherwise, the RGD built-in default is used

**Map fields** (`tags`, `syncedLabels`, `syncedAnnotations`, `airflowConfigurationOptions`) merge additively:
- Mandatory values from governance cannot be removed
- Instance values supplement defaults and can override per-key
- Merge order: mandatory (top) + instance + defaults (bottom)

## Per-Component Logging

MWAA supports independent logging for five Airflow components. You can enable/disable each and set granular log levels:

| Component | Logs | Purpose |
|---|---|---|
| **DAG processing** | DAG scheduling and parsing | Understand which DAGs loaded and when |
| **Scheduler** | Scheduler process | Track task scheduling decisions |
| **Task** | Task execution | See which tasks ran, passed, or failed |
| **Web server** | Web UI and REST API | Track API calls and web server health |
| **Worker** | Celery task execution | Deep dive into task worker behavior |

### Logging Example

```yaml
spec:
  loggingConfiguration:
    dagProcessingLogs:
      enabled: true
      logLevel: INFO
    schedulerLogs:
      enabled: true
      logLevel: INFO
    taskLogs:
      enabled: true
      logLevel: DEBUG        # Debug task execution
    webserverLogs:
      enabled: true
      logLevel: WARNING      # Less verbose UI logging
    workerLogs:
      enabled: true
      logLevel: INFO
```

Logs are sent to CloudWatch under `/aws/airflow/<environment-name>/<component>`.

## VPC Endpoint Management

MWAA provides two VPC endpoint models:

### SERVICE Mode (Default, Recommended)

AWS manages VPC endpoints automatically. Your environment is created immediately without additional setup:

```yaml
spec:
  endpointManagement: SERVICE
```

Best for standard workloads. Choose this unless you have specific VPC endpoint requirements.

### CUSTOMER Mode (Advanced)

You create and manage custom VPC interface endpoints. The environment waits for endpoint readiness:

```yaml
spec:
  endpointManagement: CUSTOMER
```

When using `CUSTOMER` mode:

1. Create the required VPC interface endpoints before or simultaneously with the environment
2. The RGD enforces a readiness gate: a ConfigMap `mwaa-vpc-endpoint-gate-<environment-name>` must exist in the same namespace
3. Create the ConfigMap with `data.ready: "false"` initially
4. After endpoints are created and verified, update the ConfigMap: `data.ready: "true"`
5. Environment creation proceeds once the gate is ready

Example readiness gate ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mwaa-vpc-endpoint-gate-my-environment
  namespace: default
data:
  ready: "true"  # Set after VPC endpoints are verified and operational
```

**Use `CUSTOMER` mode only if you need custom endpoint configuration, isolation policies, or enhanced security controls.**

## Complete Examples

### Basic Development Environment

A simple development environment with minimal configuration:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MWAAEnvironment
metadata:
  name: dev-airflow
  namespace: default
spec:
  configRef: dev                              # Use permissive dev profile
  dagS3Path: dags
  sourceBucketARN: arn:aws:s3:::my-dag-bucket
  executionRoleARN: arn:aws:iam::123456789012:role/mwaa-exec-dev
  networkConfiguration:
    subnetIDs:
      - subnet-dev-az1
      - subnet-dev-az2
  tags:
    environment: development
    team: data
```

All other settings fall through to the `dev` governance profile, which optimizes for cost and flexibility.

### Production Environment with Full Configuration

A production environment with explicit sizing, security settings, and logging:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MWAAEnvironment
metadata:
  name: prod-airflow
  namespace: default
spec:
  configRef: production                       # Use hardened production profile
  dagS3Path: dags
  sourceBucketARN: arn:aws:s3:::prod-dag-bucket
  executionRoleARN: arn:aws:iam::123456789012:role/mwaa-exec-prod
  networkConfiguration:
    subnetIDs:
      - subnet-prod-az1
      - subnet-prod-az2
    securityGroupIDs:
      - sg-prod-airflow
  airflowVersion: "2.10.3"                    # Explicit version (may be overridden by mandatory policy)
  environmentClass: mw1.large                 # Larger for high-volume DAGs
  webserverAccessMode: PRIVATE_ONLY           # Internet-isolated
  endpointManagement: SERVICE                 # AWS-managed endpoints
  maxWorkers: 50
  minWorkers: 10
  maxWebservers: 3
  minWebservers: 2
  schedulers: 3
  weeklyMaintenanceWindowStart: "SUN:04:00"   # Off-hours
  loggingConfiguration:
    dagProcessingLogs:
      enabled: true
      logLevel: INFO
    schedulerLogs:
      enabled: true
      logLevel: INFO
    taskLogs:
      enabled: true
      logLevel: WARNING                        # Task logs can be verbose
    webserverLogs:
      enabled: true
      logLevel: WARNING                        # UI logs less verbose
    workerLogs:
      enabled: true
      logLevel: INFO
  airflowConfigurationOptions:
    core.parallelism: "32"
    core.dag_concurrency: "16"
    core.max_active_runs_per_dag: "3"
  tags:
    environment: production
    cost-centre: data-eng
    compliance-required: "true"
  syncedLabels:
    audit-required: "true"
  deletionPolicy: retain                      # Keep on CR deletion (must be manually terminated)
```

Several fields may be overridden by mandatory policies from the `production` governance profile.

### Data Platform Environment with Custom Plugins

An environment for complex data pipelines with custom plugins and requirements:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MWAAEnvironment
metadata:
  name: data-platform-airflow
  namespace: default
spec:
  configRef: data-platform
  nameOverride: data-platform-prod            # Use custom literal name
  dagS3Path: dags
  sourceBucketARN: arn:aws:s3:::data-platform-dags
  executionRoleARN: arn:aws:iam::123456789012:role/mwaa-exec-data
  networkConfiguration:
    subnetIDs:
      - subnet-data-az1
      - subnet-data-az2
    securityGroupIDs:
      - sg-data-platform
  pluginsS3Path: plugins.zip
  pluginsS3ObjectVersion: "v1.2.3"            # Track S3 object version
  requirementsS3Path: requirements.txt
  requirementsS3ObjectVersion: "main"         # Could be git commit hash or version tag
  startupScriptS3Path: bootstrap.sh
  startupScriptS3ObjectVersion: "v2.1"
  environmentClass: mw1.2xlarge               # Max compute for high-volume processing
  maxWorkers: 100
  minWorkers: 20
  loggingConfiguration:
    dagProcessingLogs:
      enabled: true
      logLevel: INFO
    taskLogs:
      enabled: true
      logLevel: DEBUG                          # Debug complex task execution
    schedulerLogs:
      enabled: true
      logLevel: INFO
    workerLogs:
      enabled: true
      logLevel: DEBUG
    webserverLogs:
      enabled: false                           # Reduce noise
  airflowConfigurationOptions:
    core.parallelism: "128"
    core.dag_concurrency: "64"
    core.max_active_runs_per_dag: "5"
    scheduler.catchup_by_default: "false"
  tags:
    platform: data
    sla-required: "true"
    monitoring: datadog                       # Custom tag for monitoring
  deletionPolicy: delete                      # Clean up on CR deletion
```

### CUSTOMER VPC Endpoint Mode

An environment using CUSTOMER-managed VPC endpoints with readiness gate:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MWAAEnvironment
metadata:
  name: isolated-airflow
  namespace: default
spec:
  configRef: production
  dagS3Path: dags
  sourceBucketARN: arn:aws:s3:::isolated-dags
  executionRoleARN: arn:aws:iam::123456789012:role/mwaa-exec-isolated
  networkConfiguration:
    subnetIDs:
      - subnet-isolated-az1
      - subnet-isolated-az2
    securityGroupIDs:
      - sg-isolated-airflow
  endpointManagement: CUSTOMER                # Requires manual VPC endpoint setup
  # ... other fields ...
  tags:
    network-mode: customer-endpoints
```

Before or simultaneously, create the readiness gate:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mwaa-vpc-endpoint-gate-isolated-airflow
  namespace: default
data:
  ready: "false"                              # Initially blocked
```

Once your VPC endpoints are created and verified:

```bash
kubectl patch cm mwaa-vpc-endpoint-gate-isolated-airflow -n default -p '{"data":{"ready":"true"}}'
```

The environment will proceed to creation.

## Deletion Behavior

The `deletionPolicy` field controls what happens when you delete the `MWAAEnvironment` CR:

| Policy | Behavior |
|---|---|
| `retain` (default) | The MWAA environment continues running; only the Kubernetes CR is deleted |
| `delete` | The MWAA environment is terminated when the CR is deleted |

Use `retain` for production to prevent accidental data loss. Use `delete` for temporary/test environments.

## Troubleshooting

### Environment Stuck in PENDING State

Check the environment's `status.environmentStatus`. If it's `PENDING`:

1. Verify `endpointManagement` setting (if `CUSTOMER`, check readiness gate ConfigMap)
2. Check `status.conditions` for error messages
3. Verify subnets and security groups exist and are accessible
4. Check IAM execution role permissions

### "pluginsS3ObjectVersion is required when pluginsS3Path is set"

You specified `pluginsS3Path` but omitted `pluginsS3ObjectVersion`. Either:
- Add the S3 object version, or
- Remove both `pluginsS3Path` and `pluginsS3ObjectVersion` if you don't have custom plugins

Same applies for `requirementsS3ObjectVersion` and `startupScriptS3ObjectVersion`.

### "MWAA environment name must start with a letter"

Your naming template produced a name that starts with a digit. Either:
- Use `spec.nameOverride` with a valid name, or
- Adjust your `MWAAConfig` naming template to ensure it produces valid names

For example, use `mwaa-{namespace}-{name}` which starts with `mwaa-`.

### Configuration Overridden by Governance

Your environment's settings were changed because mandatory policies in your `MWAAConfig` profile override them. Check your profile's `mandatory` tier in the `MWAAConfig` resource. Contact your platform team to discuss adjusting policies if needed.

## Next Steps

- Deploy a `MWAAConfig` governance profile or use the default `general-policy`
- Create your first `MWAAEnvironment` with required fields
- Monitor environment creation via `kubectl describe mwaaenvironment <name>`
- See [MWAAConfig](mwaaconfig.md) for governance and profile examples
