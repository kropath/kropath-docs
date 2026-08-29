# AWS Glue Jobs

The AWS Glue family within kropath provides abstractions for managing AWS Glue ETL jobs. It enables platform engineers to enforce organization-wide controls over job runtime versions, worker configurations, execution settings, security policies, and job naming conventions, while allowing application teams to provision and configure Glue jobs for their specific ETL, Python Shell, Ray, and Streaming workloads.

## Prerequisites and Setup

`GlueJob` resources integrate with other kropath families for complete functionality:

* **IAM Family:** For specifying IAM role ARNs (via `IAMConfig` CRD) that grant the job permissions to access AWS resources.
* **KMS Family:** For referencing AWS KMS keys used by security configurations for job script encryption.
* **KropathConfig:** For organization-wide Glue governance settings applied across all Glue resources.

## Configuration

Kropath's Glue configuration is managed through two resources: instances of the `GlueJob` resource kind (which comes from a kro RGD and auto-generates its CRD) for defining individual ETL jobs, and `GlueConfig` custom resource instances for establishing organization-wide or profile-specific governance policies.

### GlueJob Core Fields

A `GlueJob` instance represents the desired state of an AWS Glue job. Here are its core configuration fields:

* `configRef` (string, default: `"general-policy"`): Specifies which `GlueConfig` profile to use for governance. If the named profile does not exist, it falls back to `"general-policy"`.
* `nameOverride` (string, default: `""`): Bypasses the naming template to set a custom job name.
* `deletionPolicy` (string, default: `"retain"`): Determines the behavior upon deletion of the `GlueJob` CR. Options are `"retain"` (AWS Glue job is preserved) or `"delete"` (AWS Glue job is deleted).

#### Metadata and Tags

* `tags` (map<string,string>, default: `{}`): Custom AWS tags applied to the Glue job. These are merged with mandatory and default tags from `KropathConfig` and `GlueConfig`.
* `syncedLabels` (map<string,string>, default: `{}`): Kubernetes labels that are mirrored to both K8s labels and AWS tags (prefixed with `aws.kropath.run/`), per ADR-015 §6.1.
* `syncedAnnotations` (map<string,string>, default: `{}`): Kubernetes annotations that are mirrored to the job resource metadata and prefixed with `aws.kropath.run/`.

#### Command Definition (Required)

The command section defines the ETL script and runtime configuration. A `command.name` is required to create the job.

* `command.name` (string): The type of Glue job command. Options are:
  * `"glueetl"` - Spark-based ETL jobs (standard choice for most workloads)
  * `"pythonshell"` - Python Shell jobs for lightweight Python scripts
  * `"glueray"` - Ray-based distributed computing jobs
  * `"gluestreaming"` - Streaming ETL jobs for real-time data pipelines
* `command.scriptLocation` (string, required): The S3 URI of the ETL script (e.g., `s3://bucket/script.py`).
* `command.pythonVersion` (string, default: `""`): Python version for Python Shell jobs (e.g., `"3"`). Ignored for non-Python job types.
* `command.runtime` (string, default: `""`): Runtime override for Ray jobs (e.g., `"Ray2.4"`). Used only for `glueray` command type.

#### Runtime Governance

* `glueVersion` (string, default: `""`): Glue runtime version (e.g., `"4.0"`, `"3.0"`). Falls through to the `GlueConfig` cascade when empty.
* `role` (string, required): IAM role ARN for job execution permissions (e.g., `"arn:aws:iam::123456789012:role/glue-job-role"`).

#### Worker Configuration

Worker configuration defines the computational resources for the job. Choose either `maxCapacity` (legacy) or `workerType`+`numberOfWorkers` (recommended).

* `workerType` (string, default: `""`): The type of worker. Options are `G.1X`, `G.2X`, `G.4X`, `G.8X`, `G.025X`, `Z.2X`. Falls through to the `GlueConfig` cascade when empty. Mutually exclusive with `maxCapacity`.
* `numberOfWorkers` (integer, default: `0`): Number of workers to allocate. Falls through to the `GlueConfig` cascade when `0`. Mutually exclusive with `maxCapacity`.
* `maxCapacity` (float, default: `0`): DPU allocation for legacy Glue v1.0 jobs. Mutually exclusive with `workerType`+`numberOfWorkers`. Use `workerType`+`numberOfWorkers` for Glue 3.0+ jobs.

#### Execution Settings

* `executionClass` (string, default: `""`): Execution class for the job. Options are `"STANDARD"` (default, always-on workers) or `"FLEX"` (flexible provisioning). Falls through to the `GlueConfig` cascade when empty.
* `timeout` (integer, default: `0`): Job timeout in minutes. When `0` (not set), falls through to the `GlueConfig` cascade; the AWS Glue service default is 2880 minutes (48 hours).
* `maxRetries` (integer, default: `0`): Maximum number of automatic retries on job failure. When `0` (not set), falls through to the `GlueConfig` cascade; otherwise specifies the retry count.
* `maxConcurrentRuns` (integer, default: `0`): Maximum number of simultaneous job runs. When `0` (not set), falls through to the `GlueConfig` cascade; otherwise limits concurrent executions.
* `jobRunQueuingEnabled` (boolean, default: `false`): When `true`, excess job runs are queued instead of rejected when `maxConcurrentRuns` is reached.

#### Job Arguments

* `defaultArguments` (map<string,string>, default: `{}`): Default job arguments passed to the script at runtime (e.g., `{"--TempDir": "s3://bucket/temp", "--job-language": "python"}`). Supports Glue system arguments.
* `nonOverridableArguments` (map<string,string>, default: `{}`): Arguments that cannot be overridden at job run time, enforcing fixed values for security or compliance.

#### Notification and Monitoring

* `notifyDelayAfter` (integer, default: `0`): Minutes before CloudWatch notification if the job run has not completed. When `0` (not set), falls through to the `GlueConfig` cascade.

#### Optional Configuration

* `description` (string, default: `""`): Human-readable job description.
* `connections` (array<string>, default: `[]`): List of Glue connection names the job uses (e.g., JDBC connections for database access).
* `securityConfiguration` (string, default: `""`): Name of a Glue SecurityConfiguration to apply for encryption and audit logging. Falls through to the `GlueConfig` cascade when empty.
* `jobMode` (string, default: `""`): Job mode for Glue Studio visual jobs. Options are `"SCRIPT"`, `"VISUAL"`, or `"NOTEBOOK"`. Defaults to `"SCRIPT"` when empty.
* `maintenanceWindow` (string, default: `""`): Maintenance window for streaming jobs (e.g., `"Sun:02"`). Specifies when Glue can perform automatic updates.

#### Source Control Integration

* `sourceControlDetails.provider` (string, default: `""`): Source control provider. Options are `"GITHUB"`, `"GITLAB"`, `"BITBUCKET"`, or `"AWS_CODE_COMMIT"`.
* `sourceControlDetails.repository` (string, default: `""`): Repository name.
* `sourceControlDetails.owner` (string, default: `""`): Repository owner or organization.
* `sourceControlDetails.branch` (string, default: `""`): Branch name (e.g., `"main"`, `"develop"`).
* `sourceControlDetails.folder` (string, default: `""`): Folder path within the repository containing the job script.
* `sourceControlDetails.authStrategy` (string, default: `""`): Authentication method. Options are `"PERSONAL_ACCESS_TOKEN"` or `"AWS_SECRETS_MANAGER"`.
* `sourceControlDetails.authToken` (string, default: `""`): Authentication token for the source control provider.

### GlueConfig Governance Model

`GlueConfig` CRs define per-profile governance settings for Glue jobs. These profiles are referenced by `GlueJob` instances via `spec.configRef`. Each `GlueConfig` includes `mandatory` and `defaults` sections for governance fields:

* **`mandatory`:** Fields set in this section enforce strict policies that cannot be overridden by `GlueJob` instances. If a `mandatory` field is set, the instance's corresponding field (if present) is ignored.
* **`defaults`:** Fields set here provide baseline configurations that `GlueJob` instances can override. They apply only when the instance's corresponding field is not explicitly set (or is set to the zero-value for integer fields).

#### Governance Fields in GlueConfig

Both `mandatory` and `defaults` tiers support the following fields:

* `glueVersion` (string): Glue runtime version (e.g., `"4.0"`, `"3.0"`).
* `workerType` (string): Worker type (`G.1X`, `G.2X`, `G.4X`, `G.8X`, `G.025X`, `Z.2X`).
* `numberOfWorkers` (integer): Worker count.
* `executionClass` (string): Execution class (`STANDARD` or `FLEX`).
* `timeout` (integer): Job timeout in minutes.
* `maxRetries` (integer): Maximum retry count.
* `maxConcurrentRuns` (integer): Maximum concurrent job runs.
* `securityConfiguration` (string): Security configuration name.
* `notifyDelayAfter` (integer): Notification delay in minutes.
* `namingTemplate` (string): Naming template for job names (e.g., `"{namespace}-{name}"`).
* `tags` (map<string,string>): Mandatory or default cloud tags.
* `syncedLabels` (map<string,string>): Labels to sync to both Kubernetes and cloud tags.
* `syncedAnnotations` (map<string,string>): Annotations to sync to Kubernetes metadata.

#### Example Profiles

* `general-policy`: Conservative baseline profile (e.g., `defaults.glueVersion: "4.0"`, `defaults.workerType: "G.1X"`, `defaults.numberOfWorkers: 2`).
* `etl-standard`: Hardened profile for standard ETL workloads (e.g., `mandatory.glueVersion: "4.0"`, `mandatory.workerType: "G.2X"`, `mandatory.executionClass: "STANDARD"`).
* `streaming`: Profile for streaming jobs (e.g., `defaults.executionClass: "FLEX"`, `defaults.maxConcurrentRuns: 2`).

### Zero-Value Sentinel Semantics

For integer fields (`timeout`, `maxRetries`, `maxConcurrentRuns`, `notifyDelayAfter`), the value `0` has special meaning:

* **In mandatory tier:** `0` means "not enforced" — the field does not override the instance value.
* **In defaults tier:** `0` means "fall through to the next tier in the cascade" or use the AWS Glue service default.
* **In instance spec:** `0` means "not set" — the field is not specified and falls through to the governance cascade.

To enforce an explicit zero value at the mandatory tier (e.g., disable retries), use the defaults tier instead with a clear intention.

### Cross-Tier Validation

`GlueConfig` CRs prevent conflicting governance by validating that scalar fields cannot be set in both `mandatory` and `defaults` tiers simultaneously. For example, you cannot set both `mandatory.timeout: 120` and `defaults.timeout: 60` — one tier must be used for each field.

### Glue Governance Cascade

Kropath employs a ten-tier governance cascade (ADR-010, ADR-015 §5.3) to resolve effective configuration for Glue jobs. The following six tiers are applicable to Glue resources. The `kropath-controller` pre-merges all governance sources (from `KropathConfig` and `GlueConfig`) into `status.effectiveConfig` on the namespaced `GlueConfig` CR. `GlueJob` RGDs read this `status.effectiveConfig` to determine the final, resolved settings.

**Cascade order (highest to lowest priority):**
1. `KropathConfig.spec.mandatory.glue.*` (organization-wide enforcement)
2. `GlueConfig.spec.mandatory.*` (profile-specific enforcement)
3. `GlueJob.spec.*` (instance-level specification)
4. `GlueConfig.spec.defaults.*` (profile-specific defaults)
5. `KropathConfig.spec.defaults.glue.*` (organization-wide defaults)
6. AWS Glue service defaults

**When to use `KropathConfig.glue` vs. `GlueConfig`:**

* **`KropathConfig.glue`:** Used for organization-wide governance that applies across *all* Glue profiles. For example, setting `KropathConfig.mandatory.glue.glueVersion: "4.0"` forces all Glue jobs in the organization to use Glue 4.0, regardless of the `GlueConfig` profile they reference.
* **`GlueConfig`:** Used for per-profile governance. For instance, an `etl-standard` `GlueConfig` profile might mandate a specific worker type only for jobs using that profile, allowing other profiles more flexibility.

## Naming Conventions

Glue job names are case-sensitive, are 255 characters or fewer, and must be unique per AWS account. They can contain most printable characters.

Kropath's default naming template for Glue jobs is `{namespace}-{name}`. The `effectiveName` (the final job name) is derived from this template, with `spec.nameOverride` providing an escape hatch to bypass the template.

### Dynamic Tag Fields in Naming Templates

Glue naming templates support `{tag.fieldName}` placeholders that allow you to embed tag values directly into job names. For example, a template like `{tag.environment}-{tag.application}-job` would derive the job name from tags defined in `spec.tags`, `spec.syncedLabels`, or `spec.syncedAnnotations`, combined with the CR name.

Tag values are resolved in a cascading order: mandatory tags from governance config, then instance-level tags, then default tags. If a referenced tag does not exist, the naming template validation reports `status.namingStatus: invalid-unresolved-tokens`.

**Example:**

```yaml
spec:
  tags:
    environment: production
    application: data-etl
  # With a naming template: "{tag.environment}-{tag.application}-{name}"
  # effectiveName = "production-data-etl-my-job"
```

For detailed information on dynamic tag field syntax, tag resolution order, provider constraints, and best practices, see [Dynamic Tag Fields in Naming Templates](../../resources/naming-template-dynamic-tags.md).

### Status Fields

The `GlueJob` status section provides resolved configuration and read-back values:

* `status.resourceName` (string): The effective job name (computed from naming template or override).
* `status.predictedArn` (string): The expected ARN of the Glue job (`arn:aws:glue:<region>:<accountId>:job/<resourceName>`).
* `status.namingStatus` (string): Naming validation status (`"valid"` or `"invalid-unresolved-tokens"`).
* `status.lastCommitID` (string): The latest commit ID from source control integration (read back from the Glue job status).
* `status.conditions[]` (array): Standard kro condition entries for reconciliation status.

## Example GlueJob Resource Instance

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: GlueJob
metadata:
  name: daily-transform
  namespace: etl-prod
spec:
  configRef: etl-standard      # Uses the 'etl-standard' GlueConfig profile
  deletionPolicy: retain
  
  # Command definition (required)
  command:
    name: glueetl
    scriptLocation: s3://etl-scripts-prod/transform.py
    pythonVersion: "3"
  
  # Runtime configuration
  glueVersion: "4.0"
  role: arn:aws:iam::123456789012:role/glue-etl-role
  
  # Worker configuration
  workerType: G.2X
  numberOfWorkers: 5
  
  # Execution settings
  executionClass: STANDARD
  timeout: 480
  maxRetries: 2
  maxConcurrentRuns: 3
  jobRunQueuingEnabled: true
  
  # Job arguments
  defaultArguments:
    "--TempDir": s3://etl-temp/
    "--job-language": python
    "--enable-metrics": "true"
  nonOverridableArguments:
    "--enable-spark-ui": "true"
  
  # Notification
  notifyDelayAfter: 120
  
  # Optional configuration
  description: "Daily data transformation for production pipeline"
  connections:
    - jdbc-prod-db
  securityConfiguration: prod-encryption
  
  # Metadata
  tags:
    environment: production
    cost-center: platform
    team: data-eng
  syncedLabels:
    data-sensitivity: high
```

## Example GlueConfig Profile Instance

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: GlueConfig
metadata:
  name: etl-standard
  namespace: kro-system
spec:
  mandatory:
    glueVersion: "4.0"
    workerType: "G.2X"
    executionClass: "STANDARD"
    timeout: 480
    maxRetries: 2
    tags:
      cost-center: platform
      managed-by: kropath
  defaults:
    numberOfWorkers: 5
    maxConcurrentRuns: 1
    securityConfiguration: prod-encryption
    namingTemplate: "etl-{namespace}-{name}"
    syncedLabels:
      platform: glue
```

## Cross-Provider Notes

Glue-specific features with no direct equivalents in other cloud providers:

* **Job Command Types:** Glue's `glueetl`, `pythonshell`, `glueray`, and `gluestreaming` command types are specific to AWS. GCP Dataproc and Azure Data Factory use different abstraction models for batch and streaming workloads.
* **Execution Classes:** AWS Glue's `STANDARD` vs. `FLEX` execution classes are Glue-specific. GCP and Azure handle compute provisioning differently at the cluster or pipeline level.
* **Worker Types and Capacity:** Glue's `G.1X` through `G.8X` worker types and `maxCapacity` are AWS-specific. GCP Dataproc uses executor configuration and provisioning nodes; Azure uses compute resource types.
* **Security Configurations:** Glue SecurityConfigurations for encryption and audit logging are AWS-specific. Other providers handle security through separate services (KMS for encryption, CloudTrail-equivalent for logging).
* **Source Control Integration:** AWS Glue's built-in source control integration is a Glue-specific feature. GCP and Azure rely on external CI/CD pipelines for script management.
* **Maintenance Windows:** AWS Glue streaming jobs support maintenance windows for automatic updates. GCP and Azure do not have direct equivalents.

## Troubleshooting

### Worker Configuration Conflicts

If you encounter an error about conflicting worker configurations, ensure you're using either `maxCapacity` (for legacy Glue v1.0) or `workerType`+`numberOfWorkers` (for Glue 3.0+), but not both. The AWS Glue API rejects requests that specify both configurations.

### Naming Template Issues

If `status.namingStatus` shows `"invalid-unresolved-tokens"`, check that all `{tag.fieldName}` placeholders in your naming template have corresponding tags defined in the mandatory, instance, or default tag sources. Tags must be present in one of these three sources for the template to resolve correctly.

### Governance Conflicts

If you receive validation errors about fields being set in both `mandatory` and `defaults` tiers, you must choose one tier for each field. The ten-tier cascade will automatically prioritize mandatory settings over defaults.

### Role ARN Validation

Ensure the IAM role ARN specified in `spec.role` exists and has the necessary permissions for your Glue job's intended operations (e.g., S3 bucket access, database connections, KMS key usage for encryption).
