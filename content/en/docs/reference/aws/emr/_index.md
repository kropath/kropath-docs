---
title: AWS EMR (Elastic MapReduce)
description: AWS EMR in kropath provides abstractions for Apache Spark and Hive workloads on AWS.
doc_type: reference
weight: 250
---
# AWS EMR (Elastic MapReduce)

AWS EMR in kropath provides abstractions for Apache Spark and Hive workloads on AWS. The family spans two distinct deployment models — EMR on EKS for running Spark jobs on existing EKS clusters via virtual cluster registrations, and EMR Serverless for fully managed serverless runtimes without cluster management. Platform engineers enforce organization-wide controls such as approved EMR release versions, CPU architecture standards, auto-stop idle timeouts for cost control, maximum capacity limits, mandatory encryption for disk and log destinations, and monitoring/logging configuration. Application teams register EKS namespaces as virtual clusters, provision EMR Serverless applications with auto-start/stop and pre-initialized capacity, and submit Spark job runs with driver configuration and execution roles.

**Critical:** Kropath supports **EMR on EKS and EMR Serverless only** — not classic EMR on EC2. Traditional EC2-based EMR clusters should be managed via the AWS Console, CLI, or Terraform. This distinction is important for teams evaluating which EMR deployment model to use with kropath.

## Prerequisites and Setup

EMR resources in kropath require the following baseline setup:

*   **EKS Integration:** EMR on EKS virtual clusters map to Kubernetes namespaces on existing EKS clusters. The EKS cluster must be created and accessible beforehand.
*   **IAM Integration:** EMR job runs require an IAM execution role with permissions to access S3, CloudWatch, and other AWS services. Execution role ARNs must be provided when submitting jobs.
*   **KMS (optional):** For encryption of EMR Serverless application disk storage, CloudWatch logs, S3 logs, and managed persistence, a KMS key must be available. Encryption key ARNs are specified in governance or instance configuration.
*   **EC2 Networking (optional):** EMR Serverless applications optionally connect to VPC subnets and security groups for network isolation. Subnet IDs and security group IDs can be configured at the application or governance level.
*   **S3 (optional):** Spark entry point files (application JARs and Python scripts) must be stored in S3 for job submissions. CloudWatch and EMR Serverless can export logs to S3 buckets.
*   **CloudWatch (optional):** Control plane logs and job execution logs can be exported to CloudWatch Logs log groups. Log group names or pre-created log groups are specified in governance or instance configuration.

The EMR family consists of four resource kinds:

*   **`EMRConfig`** — Governance configuration for EMR-wide settings (release version, architecture, idle timeouts, capacity limits, encryption keys, monitoring destinations, naming).
*   **`EMRVirtualCluster`** — Registers an EKS namespace as an EMR on EKS virtual cluster for submitting Spark job runs.
*   **`EMRServerlessApplication`** — Provisions a fully managed EMR Serverless application with pre-initialized capacity, auto-start/stop, custom images, VPC networking, encryption, and monitoring.
*   **`EMRJobRun`** — Submits a Spark job run against an EMR on EKS virtual cluster. All fields are immutable after creation.

## Configuration

Kropath's EMR configuration is managed through governance layers and resource instances:

### EMRConfig: Governance Model

`EMRConfig` CRs define per-profile governance settings for all EMR resources. These profiles are referenced by EMR instances via `spec.configRef`. Each `EMRConfig` includes `mandatory` and `defaults` sections for governance fields:

*   **`mandatory`:** Fields set in this section enforce strict policies that cannot be overridden by resource instances. If a `mandatory` field is set, the instance's corresponding field is ignored or validated against the mandatory setting.
*   **`defaults`:** Fields set here provide baseline configurations that resource instances can override. They apply only when the instance's corresponding field is not explicitly set.

#### EMRConfig Core Fields

*   `releaseLabel` (string, default: `""` = not enforced): Enforces the EMR release version for all EMR resources. Valid values are EMR-supported versions (e.g., `"emr-7.1.0"`, `"emr-6.15.0-latest"`). Mandatory tier overrides instance selection; defaults tier provides a baseline version. For `EMRJobRun`, this can be empty to inherit from governance; for `EMRServerlessApplication`, this is required and subject to governance override.

*   `architecture` (string, default: `""` = not enforced): Enforces the CPU architecture for `EMRServerlessApplication`. Valid values: `"X86_64"` (Intel), `"ARM64"` (Graviton). Mandatory tier overrides instance selection; defaults tier provides a baseline architecture. AWS defaults to `X86_64` when not specified.

*   `autoStopIdleTimeoutMinutes` (integer, default: `0` = not enforced): Enforces the idle timeout for `EMRServerlessApplication` before auto-stopping. When set in `mandatory`, all applications must stop after this idle period for cost control. Defaults tier provides a baseline timeout. Zero (`0`) means "not set" and allows fallthrough to the next tier.

*   `maximumCapacityCPU` (string, default: `""` = not enforced): Enforces the maximum total vCPU for `EMRServerlessApplication` (e.g., `"400"`, `"1000"`). Mandatory tier enforces a hard cap on compute resources.

*   `maximumCapacityMemory` (string, default: `""` = not enforced): Enforces the maximum total memory for `EMRServerlessApplication` (e.g., `"3000g"`, `"6000g"`). Mandatory tier enforces a hard cap on memory resources.

*   `diskEncryptionKeyARN` (string, default: `""` = not enforced): KMS key ARN for encryption of local worker disk storage in `EMRServerlessApplication`. When set in `mandatory`, all applications must encrypt disk with this key.

*   `namingTemplate` (string, default: `"{namespace}-{name}"` in defaults): The pattern for generating EMR resource names. Token vocabulary: `{name}`, `{namespace}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.<key>}`.

*   `tags` (map<string,string>): Custom AWS tags applied to all EMR resources, merged with instance tags.

*   `syncedLabels` (map<string,string>): Kubernetes labels mirrored as AWS tags and prefixed with `aws.kropath.run/`.

*   `syncedAnnotations` (map<string,string>): Kubernetes annotations mirrored to AWS resource tags and prefixed with `aws.kropath.run/`.

**Example EMRConfig Profiles:**

*   `general-policy`: A baseline profile with no enforced policies, defaulting to reasonable EMR versions and X86_64 architecture.
*   `spark-production`: A hardened profile with mandatory `ARM64` architecture, mandatory 15-minute idle timeout, maximum 200 vCPU and 1500G memory per application, and mandatory production tags.

**General-Policy EMRConfig Example:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EMRConfig
metadata:
  name: general-policy
  namespace: kropath-config
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  defaults:
    releaseLabel: "emr-7.1.0"
    architecture: "X86_64"
    autoStopIdleTimeoutMinutes: 30
    namingTemplate: "{namespace}-{name}"
    tags:
      Environment: general
    syncedLabels:
      governance-profile: general-policy
  mandatory: {}
```

**Spark-Production EMRConfig Example:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EMRConfig
metadata:
  name: spark-production
  namespace: kropath-config
  labels:
    aws.kropath.run/resource-name: spark-production
spec:
  defaults:
    releaseLabel: "emr-7.1.0"
    architecture: "X86_64"
    autoStopIdleTimeoutMinutes: 30
    namingTemplate: "{namespace}-{name}"
  mandatory:
    architecture: "ARM64"
    autoStopIdleTimeoutMinutes: 15
    maximumCapacityCPU: "200"
    maximumCapacityMemory: "1500g"
    tags:
      Environment: production
      CostCenter: data-team
    syncedLabels:
      governance-profile: spark-production
```

#### Ten-Tier Governance Cascade

Kropath employs a ten-tier governance cascade (ADR-010, ADR-015 §5.3) to resolve effective EMR configuration. The `kropath-controller` pre-merges all governance sources (from `KropathConfig` and `EMRConfig`) into `status.effectiveConfig` on the namespaced `EMRConfig` CR. EMR RGDs read this `status.effectiveConfig` to determine final settings.

**Governance cascade precedence (highest to lowest):**

| Tier | Source | Scope | Example |
|------|--------|-------|---------|
| 1 | KropathConfig.spec.mandatory.emr.releaseLabel (global) | Organization-wide | KropathConfig enforces `releaseLabel: "emr-7.1.0"` for all profiles |
| 2 | KropathConfig.spec.mandatory.emr.architecture (global) | Organization-wide | KropathConfig enforces `architecture: "ARM64"` for all profiles |
| 3 | EMRConfig.spec.mandatory.releaseLabel | Profile-scoped | `spark-production` profile enforces a specific EMR version |
| 4 | EMRConfig.spec.mandatory.architecture | Profile-scoped | `spark-production` profile enforces CPU architecture |
| 5 | Instance spec (resource YAML) | Single resource | `EMRServerlessApplication.spec.releaseLabel: "emr-6.15.0"`  |
| 6 | EMRConfig.spec.defaults.releaseLabel | Profile-scoped | `general-policy` defaults `releaseLabel: "emr-7.1.0"` |
| 7 | EMRConfig.spec.defaults.architecture | Profile-scoped | `general-policy` defaults `architecture: "X86_64"` |
| 8 | KropathConfig.spec.defaults.emr.releaseLabel (global) | Organization-wide | KropathConfig defaults `releaseLabel: "emr-6.15.0"` for all clusters |
| 9 | KropathConfig.spec.defaults.emr.architecture (global) | Organization-wide | KropathConfig defaults `architecture: "X86_64"` for all clusters |
| 10 | Hard-coded final default | — | AWS defaults (e.g., X86_64 architecture) |

**Example cascade resolution for `releaseLabel` in `EMRServerlessApplication`:**
- If `KropathConfig.spec.mandatory.emr.releaseLabel` is set, enforce that (Tier 1).
- Else if the application's `EMRConfig` profile has `mandatory.releaseLabel`, enforce that (Tier 3).
- Else if `EMRServerlessApplication.spec.releaseLabel` is set, use that (Tier 5).
- Else if the application's `EMRConfig` profile has `defaults.releaseLabel`, use that (Tier 6).
- Else if `KropathConfig.spec.defaults.emr.releaseLabel` is set, use that (Tier 8).
- Else use the AWS provider default (Tier 10).

**When to use `KropathConfig.emr` vs. `EMRConfig`:**

*   **`KropathConfig.emr`:** Used for blanket, organization-wide governance that applies across *all* EMR profiles. For example, setting `KropathConfig.mandatory.emr.architecture: "ARM64"` forces all EMR Serverless applications to use Graviton architecture regardless of profile.
*   **`EMRConfig`:** Used for per-profile governance. For instance, a `spark-production` profile might mandate `ARM64` architecture and 15-minute idle timeouts only for that profile, allowing other profiles to use mixed configurations.

### EMRVirtualCluster: EKS Namespace Registration

An `EMRVirtualCluster` resource registers a Kubernetes namespace on an EKS cluster as an EMR on EKS virtual cluster, enabling Spark job submissions against that namespace.

#### Core Fields

*   `configRef` (string, default: `"general-policy"`): Specifies which `EMRConfig` profile to use for governance.
*   `nameOverride` (string): Allows overriding the virtual cluster name derived from the naming template.
*   `deletionPolicy` (string, default: `"retain"`): Determines behavior upon deletion. Options: `"retain"` (preserve AWS virtual cluster) or `"delete"` (terminate AWS virtual cluster).
*   `tags` (map<string,string>): Custom AWS tags applied to the virtual cluster, merged with governance tags.
*   `syncedLabels` (map<string,string>): Kubernetes labels mirrored as AWS tags.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations mirrored to AWS tags.

#### Container Provider

*   `containerProviderID` (string, required): The EKS cluster name or ID where this virtual cluster runs.
*   `containerProviderNamespace` (string, required): The Kubernetes namespace on the EKS cluster that this virtual cluster maps to. All job submissions against this virtual cluster run in this namespace.

#### Naming

Resource names follow the naming convention. `effectiveName` is the resolved cloud resource name derived from the naming template or `spec.nameOverride`. Token vocabulary: `{name}`, `{namespace}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.<key>}`.

*   Default `namingTemplate`: `{namespace}-{name}`
*   Provider character/length constraints: Pattern `^[\.\-_/#A-Za-z0-9]+$` (no length limit specified in ACK CRD; AWS API enforces practical limits).
*   Post-processing: None required.

#### Status Outputs

*   `status.resourceName`: The effective name after naming template substitution.
*   `status.namingStatus`: `"valid"` or `"invalid-unresolved-tokens"`.
*   `status.predictedArn`: `arn:aws:emr-containers:{region}:{accountId}:/virtualclusters/{virtualClusterId}` (fully resolved after creation when AWS assigns the cluster ID).
*   `status.id`: The AWS-assigned virtual cluster ID.

**Example EMRVirtualCluster:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EMRVirtualCluster
metadata:
  name: spark-jobs
  namespace: data-team
spec:
  configRef: general-policy
  containerProviderID: my-eks-cluster
  containerProviderNamespace: spark-workloads
  deletionPolicy: retain
  tags:
    Application: spark-analytics
  syncedLabels:
    workload: data-processing
```

### EMRServerlessApplication: Fully Managed Serverless Runtimes

An `EMRServerlessApplication` resource provisions a fully managed EMR Serverless application providing a serverless runtime environment for Apache Spark or Hive jobs. Applications pre-warm compute capacity, scale automatically, and manage auto-start/stop lifecycle without cluster management.

#### Core Fields

*   `configRef` (string, default: `"general-policy"`): Specifies which `EMRConfig` profile to use for governance.
*   `nameOverride` (string): Allows overriding the application name derived from the naming template.
*   `deletionPolicy` (string, default: `"retain"`): Determines behavior upon deletion. Options: `"retain"` or `"delete"`.
*   `tags` (map<string,string>): Custom AWS tags applied to the application, merged with governance tags.
*   `syncedLabels` (map<string,string>): Kubernetes labels mirrored as AWS tags.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations mirrored to AWS tags.

#### Engine Configuration (Required)

*   `releaseLabel` (string, required): EMR release version (e.g., `"emr-7.1.0"`, `"emr-6.15.0-latest"`). Subject to governance cascade: mandatory tier > instance > defaults tier.
*   `type` (string, required): Application engine type. Valid values: `"Spark"` or `"Hive"`.
*   `architecture` (string, default: `""`): CPU architecture. Valid values: `"X86_64"` (Intel) or `"ARM64"` (Graviton). Empty defaults to `"X86_64"` via governance cascade.

#### Lifecycle Configuration

*   `autoStartEnabled` (boolean, default: `true`): When `true`, the application automatically starts when the first job is submitted. Set to `false` to start manually.
*   `autoStopEnabled` (boolean, default: `true`): When `true`, the application automatically stops after idle timeout. Set to `false` to keep running.
*   `autoStopIdleTimeoutMinutes` (integer, default: `0`): Minutes before auto-stopping after idle. Zero (`0`) means "not set"; governance cascade determines the effective timeout.

#### Capacity Configuration

*   `initialCapacity` (map<string,object>, default: `{}`): Pre-initialized capacity per worker type. Each entry maps a worker type (e.g., `"Driver"`, `"Executor"`) to capacity configuration including `workerCount`, `cpu`, `memory`, `disk`, `diskType`. Pre-initialized capacity reduces cold-start latency; omit to use on-demand capacity only.
*   `maximumCapacityCPU` (string, default: `""`): Maximum total vCPU across all workers (e.g., `"400"`, `"1000"`). Empty means "not set"; governance cascade determines the limit. Subject to governance cascade.
*   `maximumCapacityMemory` (string, default: `""`): Maximum total memory across all workers (e.g., `"3000g"`, `"6000g"`). Empty means "not set". Subject to governance cascade.
*   `maximumCapacityDisk` (string, default: `""`): Maximum total disk space (e.g., `"20000g"`). Empty means "no limit".

#### Container Images

*   `imageURI` (string, default: `""`): Custom container image URI for the application. Empty uses AWS-managed images for the `releaseLabel`. This image applies to all worker types unless overridden.
*   `workerTypeSpecifications` (map<string,object>, default: `{}`): Per-worker-type image overrides. Each entry maps a worker type (e.g., `"Driver"`, `"Executor"`) to an `imageURI` for that type only.

#### Networking (Optional)

*   `networkSubnetIDs` ([]string, default: `[]`): EC2 subnet IDs for VPC connectivity. Omit for AWS-managed networking. Applications with subnet IDs are isolated to that VPC.
*   `networkSecurityGroupIDs` ([]string, default: `[]`): EC2 security group IDs to associate with application workers. Requires `networkSubnetIDs` to be set.

#### Encryption

*   `diskEncryptionKeyARN` (string, default: `""`): KMS key ARN for encryption of local worker disk storage. Empty means no disk encryption. Subject to governance cascade.
*   `diskEncryptionContext` (map<string,string>, default: `{}`): Additional KMS encryption context key-value pairs for disk encryption (only used when `diskEncryptionKeyARN` is set).

#### Monitoring and Logging

*   `monitoringS3LogURI` (string, default: `""`): S3 URI prefix for log output (e.g., `"s3://my-bucket/emr-logs/"`). Empty means no S3 logging.
*   `monitoringS3EncryptionKeyARN` (string, default: `""`): KMS key ARN for encrypting S3 logs.
*   `monitoringCloudWatchEnabled` (boolean, default: `false`): Enable CloudWatch Logs export.
*   `monitoringCloudWatchLogGroup` (string, default: `""`): CloudWatch Logs group name. Required if `monitoringCloudWatchEnabled: true`.
*   `monitoringCloudWatchLogPrefix` (string, default: `""`): Log prefix for CloudWatch logs.
*   `monitoringCloudWatchEncryptionKeyARN` (string, default: `""`): KMS key ARN for encrypting CloudWatch logs.
*   `monitoringCloudWatchLogTypes` (map<string,[]string>, default: `{}`): Log types per driver component (e.g., `{"SPARK_DRIVER": ["STDOUT", "STDERR"]}`).
*   `monitoringManagedPersistenceEnabled` (boolean, default: `false`): Enable EMR Managed Persistence logs.
*   `monitoringManagedPersistenceEncryptionKeyARN` (string, default: `""`): KMS key ARN for encrypting managed persistence logs.
*   `monitoringPrometheusRemoteWriteURL` (string, default: `""`): Amazon Managed Prometheus remote write endpoint URL for metrics export.

#### Scheduler Configuration (EMR 7.0.0+)

*   `schedulerMaxConcurrentRuns` (integer, default: `0`): Maximum concurrent jobs running simultaneously. Zero (`0`) means "not set" (no limit).
*   `schedulerQueueTimeoutMinutes` (integer, default: `0`): Queue timeout in minutes. Zero (`0`) means "not set".

#### Runtime Configuration

*   `runtimeConfiguration` ([]object, default: `[]`): Application-level Spark/Hive configuration classifications. Each entry includes `classification` and `properties` (map of key-value strings).

#### Naming

Resource names follow the naming convention. `effectiveName` is the resolved cloud resource name derived from the naming template or `spec.nameOverride`.

*   Default `namingTemplate`: `{namespace}-{name}`
*   Provider character/length constraints: Pattern `^[A-Za-z0-9._/#-]+$`, 1–64 characters.

**Example EMRServerlessApplication:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EMRServerlessApplication
metadata:
  name: analytics-app
  namespace: data-team
spec:
  configRef: spark-production
  type: Spark
  releaseLabel: "emr-7.1.0"
  architecture: "ARM64"
  autoStartEnabled: true
  autoStopEnabled: true
  autoStopIdleTimeoutMinutes: 15
  initialCapacity:
    Driver:
      workerCount: 1
      cpu: "4"
      memory: "16g"
      disk: "100g"
      diskType: "gp3"
    Executor:
      workerCount: 2
      cpu: "8"
      memory: "32g"
      disk: "200g"
      diskType: "gp3"
  maximumCapacityCPU: "200"
  maximumCapacityMemory: "1500g"
  monitoringS3LogURI: "s3://my-bucket/emr-logs/"
  monitoringCloudWatchEnabled: true
  monitoringCloudWatchLogGroup: "/aws/emr/serverless"
  tags:
    Application: analytics
    CostCenter: data-team
  syncedLabels:
    workload: analytics
```

### EMRJobRun: Spark Job Submission

An `EMRJobRun` resource submits a Spark job against an EMR on EKS virtual cluster. **All fields are immutable after creation** — the ACK controller calls `StartJobRun` on create and `CancelJobRun` on delete. Any spec change triggers job cancellation and re-creation, which disrupts running jobs.

#### Core Fields

*   `configRef` (string, default: `"general-policy"`): Specifies which `EMRConfig` profile to use for governance.
*   `nameOverride` (string): Allows overriding the job run name derived from the naming template.
*   `deletionPolicy` (string, default: `"delete"`): Determines behavior upon deletion. Options: `"retain"` (preserve AWS job run record) or `"delete"` (cancel and remove). **Note:** Defaults to `"delete"` (not `"retain"`) because job runs are ephemeral workloads; retaining a completed job run serves no purpose — the metadata is already stored in the EMR service.
*   `tags` (map<string,string>, immutable): Custom AWS tags applied to the job run at submission time. Immutable after creation.
*   `syncedLabels` (map<string,string>): Kubernetes labels mirrored as AWS tags.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations mirrored to AWS tags.

#### Job Target (Required, Immutable)

*   `virtualClusterID` (string, default: `""`): The ID of the EMR on EKS virtual cluster to submit the job to. Mutually exclusive with `virtualClusterRef`.
*   `virtualClusterRef` (object, default: `nil`): ACK reference to an `EMRVirtualCluster` resource (resolves via `status.id`). Mutually exclusive with `virtualClusterID`. Useful for cross-namespace references.

#### Execution Configuration (Required, Immutable)

*   `executionRoleARN` (string, required): IAM role ARN for job execution. This role must have permissions to access S3, CloudWatch, and other AWS services used by the job. **Note:** No governance path for this field — it is a per-job operational parameter, not an organization-wide policy. If execution role governance is needed, use IAM family policy controls.
*   `releaseLabel` (string, default: `""`): EMR release version override for this job (e.g., `"emr-6.15.0-latest"`). Empty (`""`) means "not set"; governance cascade determines the effective version. Subject to governance cascade: mandatory tier > instance > defaults tier.

#### Spark Submit Driver Configuration (Required, Immutable)

*   `sparkEntryPoint` (string, required): Entry point URI — S3 path to the application JAR or Python script (e.g., `"s3://my-bucket/my-app.jar"`, `"s3://my-bucket/script.py"`).
*   `sparkEntryPointArguments` ([]string, default: `[]`): Arguments passed to the entry point application.
*   `sparkSubmitParameters` (string, default: `""`): Additional Spark submit parameters (e.g., `"--conf spark.executor.instances=2 --conf spark.executor.memory=4g"`).

#### Configuration Overrides (Immutable)

*   `configurationOverrides` (string, default: `""`): JSON-serialized configuration overrides. Due to recursive schema limitations in the ACK CRD, this is stored as a raw JSON string. Consumers must manually marshal/unmarshal the JSON. Example: `'{"Classification": "spark", "Properties": {"maximizeResourceAllocation": "true"}}'`.

#### Naming

Resource names follow the naming convention. `effectiveName` is the resolved cloud resource name derived from the naming template or `spec.nameOverride`.

*   Default `namingTemplate`: `{namespace}-{name}`
*   Provider character/length constraints: Pattern `^[\.\-_/#A-Za-z0-9]+$` (no length limit specified in ACK CRD).

#### Status Outputs

*   `status.resourceName`: The effective name after naming template substitution.
*   `status.namingStatus`: `"valid"` or `"invalid-unresolved-tokens"`.
*   `status.predictedArn`: `arn:aws:emr-containers:{region}:{accountId}:/virtualclusters/{virtualClusterId}/jobruns/{jobRunId}` (fully resolved after creation).
*   `status.id`: The AWS-assigned job run ID.
*   `status.state`: The job run state (e.g., `PENDING`, `SUBMITTED`, `RUNNING`, `FAILED`, `CANCELLED`, `CANCEL_PENDING`, `COMPLETED`), polled every 15 seconds.

**Example EMRJobRun:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EMRJobRun
metadata:
  name: daily-etl-job
  namespace: data-team
spec:
  configRef: general-policy
  virtualClusterRef:
    name: spark-jobs
    namespace: data-team
  executionRoleARN: "arn:aws:iam::123456789012:role/emr-job-execution-role"
  releaseLabel: "emr-7.1.0"
  sparkEntryPoint: "s3://my-bucket/jobs/etl-pipeline.jar"
  sparkEntryPointArguments:
    - "--input-path"
    - "s3://my-bucket/data/input/"
    - "--output-path"
    - "s3://my-bucket/data/output/"
  sparkSubmitParameters: "--conf spark.executor.instances=4 --conf spark.executor.memory=8g"
  deletionPolicy: delete
  tags:
    JobType: etl
    Schedule: daily
  syncedLabels:
    job-type: etl
```

## Key Governance Considerations

### EMR Release Version Governance

Release version governance is critical for ensuring compatibility and security. Use the cascade tiers strategically:

*   **Organization-wide enforcement:** Set `KropathConfig.mandatory.emr.releaseLabel` to enforce a single EMR version across all applications and jobs.
*   **Per-profile enforcement:** Set `EMRConfig.mandatory.releaseLabel` to enforce a version within a specific profile (e.g., `spark-production` always uses `"emr-7.1.0"`).
*   **Per-application override:** Set `EMRServerlessApplication.spec.releaseLabel` or `EMRJobRun.spec.releaseLabel` to use a different version for a specific workload (subject to mandatory tiers).

### Architecture Selection and Cost Optimization

CPU architecture selection significantly impacts costs:

*   **ARM64 (Graviton) instances** are approximately 20% cheaper than X86_64 and offer comparable performance for most Spark workloads.
*   Enforce `architecture: "ARM64"` in a `spark-production` `EMRConfig` profile to standardize on Graviton for cost-sensitive workloads.
*   Override to `"X86_64"` in `EMRServerlessApplication` or `EMRJobRun` only when specific libraries or dependencies require x86 architecture.

### Capacity Limits and Cost Control

`EMRServerlessApplication` auto-scales compute resources dynamically. Enforce capacity limits to prevent runaway costs:

*   Set `maximumCapacityCPU` and `maximumCapacityMemory` in `EMRConfig.mandatory` to hard-cap compute resource usage.
*   Set `autoStopIdleTimeoutMinutes` in `EMRConfig.mandatory` to automatically stop idle applications after a specified period (e.g., 15 minutes for production workloads).

### Immutability of EMRJobRun

All `EMRJobRun` fields are immutable after creation. **Any spec change (e.g., different S3 path, different entry point arguments) cancels the running job and submits a new one.** This design supports declarative, GitOps-style job management but requires careful consideration of operational impact:

*   Use `EMRJobRun` for scheduled, repeatable jobs (e.g., daily ETL pipelines managed via GitOps).
*   For ad-hoc job submission with dynamic parameters (e.g., user-provided input paths), use the AWS CLI or Step Functions instead of `EMRJobRun` resources.

## Next Steps

For detailed implementation guidance, refer to the kropath architecture specifications in the `kropath-core` repository:

*   [EMR Family Design](https://github.com/kropath/kropath-core/blob/main/docs/families/aws/emr.md)
*   [EMRVirtualCluster Spec](https://github.com/kropath/kropath-core/blob/main/docs/specs/aws/aws-emr-01-emrvirtualcluster.md)
*   [EMRServerlessApplication Spec](https://github.com/kropath/kropath-core/blob/main/docs/specs/aws/aws-emr-02-emrserverlessapplication.md)
*   [EMRJobRun Spec](https://github.com/kropath/kropath-core/blob/main/docs/specs/aws/aws-emr-03-emrjobrun.md)
