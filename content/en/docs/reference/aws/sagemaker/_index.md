---
title: AWS SageMaker
description: The AWS SageMaker family within kropath provides abstractions for managing Amazon SageMaker machine learning resources.
doc_type: reference
weight: 470
---
# AWS SageMaker

The AWS SageMaker family within kropath provides abstractions for managing Amazon SageMaker machine learning resources. It enables platform engineers to enforce organization-wide controls such as encryption, network isolation, instance type allowlists, and VPC requirements, while allowing application teams to provision and configure SageMaker infrastructure for their ML workloads — from Studio domains and notebook instances for interactive development to production endpoints, training jobs, and feature stores.

## Prerequisites and Setup

SageMaker resources integrate with several other kropath families for core functionality:

*   **IAM Family:** For specifying execution roles (`roleArn`) that give SageMaker resources access to AWS services.
*   **EC2 Family:** For VPC configuration (subnets, security groups) to ensure SageMaker resources can communicate within your network.
*   **KMS Family:** For referencing AWS KMS keys to encrypt storage volumes, training checkpoints, and model artifacts.
*   **S3 Family:** For referencing S3 buckets for training data, output paths, model artifacts, and feature stores.

Studio domains can be created independently of compute infrastructure, but production endpoints and training jobs require VPC networking and IAM roles. Feature stores require S3 buckets for offline storage.

## Configuration

Kropath's SageMaker configuration is managed through two resources: instances of the `SageMakerConfig` CRD for establishing governance policies, and instances of individual resource kinds (e.g. `SageMakerDomain`, `SageMakerEndpoint`) that inherit governance settings. These resources leverage a ten-tier governance cascade (ADR-010, ADR-015 §5.3) to ensure compliance while providing flexibility.

### SageMakerConfig Governance Model

`SageMakerConfig` CRs define per-profile governance settings for SageMaker resources. Each `SageMakerConfig` includes `mandatory` and `defaults` sections for governance fields:

*   **`mandatory`:** Fields set in this section enforce strict policies that cannot be overridden by resource instances. If a `mandatory` field is set, the instance's corresponding field is ignored or validated against the mandatory setting.
*   **`defaults`:** Fields set here provide baseline configurations that resource instances can override. They apply only when the instance's corresponding field is not explicitly set.

**Example Profiles:**

*   `general-policy`: A conservative baseline profile with sensible defaults (e.g., `defaults.volumeSizeInGB: 5`, `defaults.rootAccess: "Enabled"`).
*   `ml-production`: A hardened compliance profile (e.g., `mandatory.enableNetworkIsolation: true`, `mandatory.enableInterContainerTrafficEncryption: true`, `mandatory.directInternetAccess: "Disabled"`).
*   `ml-training`: A training-focused profile with reasonable instance type and volume defaults for ML workloads.

### Governance Fields

SageMaker resources are governed by `SageMakerConfig` for the following fields:

*   **Common to all resources:** `tags`, `syncedLabels`, `syncedAnnotations` (merged governance), `namingTemplate` (for resources with naming support).
*   **Compute-related resources:** `instanceType` (enforced on notebook instances, training jobs, processing jobs, transform jobs), `volumeSizeInGB` (storage volume size for training/processing/transform jobs).
*   **Security-related resources:** `kmsKeyId` (encryption key for storage volumes), `enableNetworkIsolation` (network isolation enforcement), `enableInterContainerTrafficEncryption` (inter-container traffic encryption for distributed training).
*   **Access control:** `rootAccess` (for notebook instances), `directInternetAccess` (for notebook instances).

### Ten-tier Governance Cascade

The kropath-controller pre-merges all governance sources (from `KropathConfig` and `SageMakerConfig`) into `status.effectiveConfig` on the namespaced `SageMakerConfig` CR. Resource instances read this `status.effectiveConfig` to determine the final, resolved settings.

**When to use `KropathConfig.sagemaker` vs. `SageMakerConfig`:**

*   **`KropathConfig.sagemaker`:** Used for blanket, organization-wide governance that applies across all SageMaker profiles. For example, setting `KropathConfig.mandatory.sagemaker.enableNetworkIsolation: true` would force all SageMaker resources to enable network isolation, regardless of the `SageMakerConfig` profile they use.
*   **`SageMakerConfig`:** Used for per-profile governance. For instance, an `ml-production` `SageMakerConfig` profile might mandate network isolation and inter-container encryption only for resources using that profile, allowing other profiles more flexibility.

**Boolean Governance Semantics:** For boolean fields like `enableNetworkIsolation`, `false` in a `mandatory` or `defaults` tier means "follow the next tier in the cascade" rather than explicitly disabling the control. To explicitly disable a control, a dedicated `SageMakerConfig` profile must be created with `mandatory.<field>: false`, and the resource instance must reference this profile.

## Resource Overview

The SageMaker family includes 21 resources (20 RGDs + 1 governance CRD) organized into two priority tiers:

### Priority 0 (P0) — Core Resources

**Studio Environment:**
*   **SageMakerDomain:** A SageMaker Studio domain — the top-level organizational container for user profiles, shared spaces, and apps. Controls authentication mode (IAM or SSO), VPC networking, default user settings, and EFS/EBS encryption.
*   **SageMakerUserProfile:** A user profile within a SageMaker Studio domain — represents an individual user's identity, permissions, and workspace configuration.
*   **SageMakerSpace:** A collaborative shared space within a SageMaker Studio domain — provides shared compute, storage, and configuration for multiple users.

**Compute & Development:**
*   **SageMakerNotebookInstance:** An EC2-backed managed Jupyter environment for interactive ML development. Optionally includes lifecycle configuration scripts for automated setup.

**Model Hosting:**
*   **SageMakerModel:** Defines the container image(s) and model artifact location(s) that serve inference requests.
*   **SageMakerEndpointConfig:** Specifies which models to host on an endpoint, with production variant weights, instance types, and optional data capture/async inference settings.
*   **SageMakerEndpoint:** A managed compute resource that hosts one or more models for real-time predictions.

**Training:**
*   **SageMakerTrainingJob:** Runs model training on managed ML compute with full configuration for algorithms, hyperparameters, input/output data, debugging, and profiling.

### Priority 1 (P1) — Extended Resources

**Data Processing:**
*   **SageMakerProcessingJob:** Runs data processing, feature engineering, or model evaluation on managed ML compute.
*   **SageMakerTransformJob:** Runs offline batch inference against an existing model on a dataset.

**Advanced Training:**
*   **SageMakerHyperParameterTuningJob:** Runs automated hyperparameter optimization over one or more training job definitions.

**ML Workflows:**
*   **SageMakerPipeline:** Defines an ML workflow as a JSON pipeline definition with steps for training, processing, evaluation, and model registration.

**Model Registry:**
*   **SageMakerModelPackageGroup:** A logical container for organizing versioned model packages in the model registry.
*   **SageMakerModelPackage:** A versioned model artifact with inference specifications, metrics, and approval status within a model package group.

**Feature Management:**
*   **SageMakerFeatureGroup:** A collection of features for ML models, with online and/or offline storage backing.

**Monitoring:**
*   **SageMakerMonitoringSchedule:** Runs recurring monitoring jobs against an endpoint to detect drift and anomalies.
*   **SageMakerDataQualityJobDefinition:** Specifies the analysis algorithm and configuration for detecting data drift in endpoint inputs.
*   **SageMakerModelQualityJobDefinition:** Specifies configuration for detecting model quality degradation.
*   **SageMakerModelBiasJobDefinition:** Specifies configuration for detecting bias in model predictions.
*   **SageMakerModelExplainabilityJobDefinition:** Specifies configuration for model explainability analysis.

## Core Fields (All Resources)

Every SageMaker resource instance has the following common fields:

*   `configRef` (string, default: `"general-policy"`): Specifies which `SageMakerConfig` profile to use for governance. If the named profile does not exist, it falls back to `"general-policy"`.
*   `nameOverride` (string): Allows overriding the resource name derived from the naming template.
*   `deletionPolicy` (string, default: `"retain"`): Determines behavior upon deletion of the resource CR. Options are `"retain"` (AWS resource is preserved) or `"delete"` (AWS resource is deleted).
*   `tags` (map<string,string>): Custom AWS tags applied to the resource. These are merged with mandatory and default tags from `KropathConfig` and `SageMakerConfig`.
*   `syncedLabels` (map<string,string>): Kubernetes labels that are mirrored as AWS tags and prefixed with `aws.kropath.run/`.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations that are mirrored to AWS resource tags and prefixed with `aws.kropath.run/`.

## Naming Conventions

SageMaker resources use Kubernetes naming conventions that are transformed into cloud resource names via a naming template. The default naming template is `{namespace}-{name}`, which generates cloud resource names from your Kubernetes CR's namespace and name.

The `effectiveName` (the final cloud resource name) is derived from this template, with `spec.nameOverride` providing an escape hatch to bypass the template.

### Resource-Specific Naming Constraints

| Resource | Max chars | Pattern |
|---|---|---|
| SageMakerDomain | 63 | alphanumeric + hyphens |
| SageMakerUserProfile | 63 | alphanumeric + hyphens |
| SageMakerSpace | 63 | alphanumeric + hyphens |
| SageMakerNotebookInstance | 63 | alphanumeric + hyphens |
| SageMakerModel | 63 | alphanumeric + hyphens |
| SageMakerEndpointConfig | 63 | alphanumeric + hyphens |
| SageMakerEndpoint | 63 | alphanumeric + hyphens |
| SageMakerTrainingJob | 63 | alphanumeric + hyphens |
| SageMakerProcessingJob | 63 | alphanumeric + hyphens |
| SageMakerTransformJob | 63 | alphanumeric + hyphens |
| SageMakerHyperParameterTuningJob | 32 | alphanumeric + hyphens |
| SageMakerPipeline | 256 | alphanumeric + hyphens |
| SageMakerModelPackageGroup | 63 | alphanumeric + hyphens |
| SageMakerFeatureGroup | 64 | alphanumeric + hyphens + underscores |
| SageMakerMonitoringSchedule | 63 | alphanumeric + hyphens |
| Job Definition resources | 63 | alphanumeric + hyphens |

**Naming Exemptions:** `SageMakerModelPackage` (versioned packages) does not support user-settable names — they are identified by their model package group name and an auto-assigned version number.

## Quickstart: Studio Domain, User Profile, and Notebook Instance

This example demonstrates creating a complete SageMaker Studio environment end-to-end:

```yaml
---
# 1. SageMakerConfig profile for general use
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerConfig
metadata:
  name: general-policy
  namespace: ml-platform
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    volumeSizeInGB: 5
    rootAccess: "Enabled"
    directInternetAccess: "Enabled"
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}

---
# 2. SageMaker Studio Domain
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerDomain
metadata:
  name: my-studio-domain
  namespace: ml-platform
spec:
  configRef: general-policy
  authMode: IAM
  vpcId: vpc-12345678
  subnetIds:
    - subnet-11111111
    - subnet-22222222
  appNetworkAccessType: VpcOnly
  defaultUserSettings:
    executionRole: arn:aws:iam::123456789012:role/SageMakerExecutionRole
    securityGroups:
      - sg-12345678

---
# 3. User Profile within the Domain
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerUserProfile
metadata:
  name: data-scientist-alice
  namespace: ml-platform
spec:
  configRef: general-policy
  domainId: d-1234567890  # Reference the domain's ID from its status
  userSettings:
    executionRole: arn:aws:iam::123456789012:role/DataScientistRole

---
# 4. Notebook Instance for Interactive Development
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerNotebookInstance
metadata:
  name: alice-dev-notebook
  namespace: ml-platform
spec:
  configRef: general-policy
  instanceType: ml.t3.medium
  roleArn: arn:aws:iam::123456789012:role/DataScientistRole
  subnetId: subnet-11111111
  securityGroupIds:
    - sg-12345678
  kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012
  tags:
    environment: development
    owner: alice
```

**Expected Results:**

After applying these resources:

1. The `SageMakerDomain` CR reconciles to a SageMaker Studio domain (cloud resource name: `ml-platform-my-studio-domain`).
2. The `SageMakerUserProfile` CR reconciles to a user profile within that domain (cloud resource name: `ml-platform-data-scientist-alice`).
3. The `SageMakerNotebookInstance` CR reconciles to a managed Jupyter notebook instance (cloud resource name: `ml-platform-alice-dev-notebook`).

All resources inherit governance settings from the `general-policy` config profile, ensuring that tags, encryption, and naming conventions are consistently applied organization-wide.

## Example: Training Job with Governance Enforcement

This example demonstrates a training job that respects governance policies:

```yaml
---
# Production training policy
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerConfig
metadata:
  name: ml-production
  namespace: ml-platform
  labels:
    aws.kropath.run/resource-name: ml-production
spec:
  mandatory:
    enableNetworkIsolation: true
    enableInterContainerTrafficEncryption: true
    tags:
      environment: production
      cost-center: ml-ops
  defaults:
    instanceType: ml.p3.2xlarge
    volumeSizeInGB: 30
    kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/prod-key

---
# Training job using the production policy
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerTrainingJob
metadata:
  name: xgboost-training-v1
  namespace: ml-platform
spec:
  configRef: ml-production
  algorithmSpecification:
    trainingImage: 246618743249.dkr.ecr.us-east-1.amazonaws.com/xgboost:latest
    trainingInputMode: File
    metricDefinitions:
      - name: validation:auc
        regex: "validation:auc=([0-9\\.]+)"
  resourceConfig:
    instanceType: ml.p3.2xlarge        # Falls through to governance defaults
    instanceCount: 2
    volumeSizeInGB: 50                 # Override default
    keepAliveInSeconds: 0
  roleArn: arn:aws:iam::123456789012:role/SageMakerTrainingRole
  inputDataConfig:
    - channelName: training
      dataSource:
        s3DataSource:
          s3Uri: s3://my-bucket/training-data
          s3DataType: S3Prefix
          s3DataDistributionType: FullyReplicated
      contentType: text/csv
      compressionType: None
  outputDataConfig:
    s3OutputPath: s3://my-bucket/training-output
    kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/prod-key
  stoppingCondition:
    maxRuntimeInSeconds: 3600
  tags:
    model: xgboost
    dataset: v1
```

**Governance Applied:**

1. **Network isolation:** `enableNetworkIsolation: true` (mandatory)
2. **Encryption:** Inter-container traffic encryption enabled (mandatory)
3. **Tags:** Both mandatory tags (`environment: production`, `cost-center: ml-ops`) and instance tags (`model: xgboost`, `dataset: v1`) are merged and applied
4. **Instance type:** Defaults to `ml.p3.2xlarge` from the profile, but overridden to `ml.p3.2xlarge` in the instance (same value)
5. **Storage:** Defaults to `30` GB, but overridden to `50` GB in the instance

## Example: Feature Store with Online and Offline Storage

```yaml
---
# Feature store governance
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerConfig
metadata:
  name: ml-features
  namespace: ml-platform
  labels:
    aws.kropath.run/resource-name: ml-features
spec:
  mandatory: {}
  defaults:
    kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/feature-store-key
    namingTemplate: "{namespace}-{name}"

---
# Feature Group for customer features
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerFeatureGroup
metadata:
  name: customer-features
  namespace: ml-platform
spec:
  configRef: ml-features
  recordIdentifierFeatureName: customer_id
  eventTimeFeatureName: event_time
  featureDefinitions:
    - featureName: customer_id
      featureType: String
    - featureName: total_purchases
      featureType: Integral
    - featureName: avg_purchase_value
      featureType: Fractional
    - featureName: event_time
      featureType: String
  onlineStoreConfig:
    enableOnlineStore: true
  offlineStoreConfig:
    s3StorageConfig:
      s3Uri: s3://my-bucket/feature-store/offline
  roleArn: arn:aws:iam::123456789012:role/SageMakerFeatureStoreRole
```

## Cross-Provider Notes

While kropath aims for a consistent experience across cloud providers, SageMaker has several AWS-specific characteristics:

*   **Studio Domains:** AWS SageMaker's Studio domain concept (with domain-scoped user profiles and collaborative spaces) is unique to SageMaker. GCP Vertex AI uses workspace-level access control; Azure ML uses a workspace-centric model.
*   **Endpoint Configuration:** SageMaker separates endpoint configuration from endpoint deployment (two separate resources). GCP Vertex AI and Azure ML have inline endpoint deployment configuration.
*   **Feature Store:** SageMaker's online/offline store architecture is specific to AWS. GCP and Azure have different feature store designs.
*   **Monitoring Definitions:** SageMaker's separate job definition resources for data quality, model quality, bias, and explainability monitoring are AWS-specific patterns.
*   **Hyperparameter Tuning:** AWS's AutoML and hyperparameter tuning job definitions have no direct equivalent in GCP or Azure.

## Resource-Specific Documentation

For detailed field reference for each individual resource, see:

**Governance:**
*   [SageMakerConfig](sagemakerconfig.md) — Governance profiles and control policies

**P0 Resources:**
*   [SageMakerDomain](sagemakerdomain.md)
*   [SageMakerUserProfile](sagemakeruserprofile.md)
*   [SageMakerSpace](sagemakerspace.md)
*   [SageMakerNotebookInstance](sagemakernotebookinstance.md)
*   [SageMakerModel](sagemakermodel.md)
*   [SageMakerEndpointConfig](sagemakerendpointconfig.md)
*   [SageMakerEndpoint](sagemakerendpoint.md)
*   [SageMakerTrainingJob](sagemakertrainingjob.md)

**P1 Resources:**
*   [SageMakerProcessingJob](sagemakerprocessingjob.md)
*   [SageMakerTransformJob](sagemakertransformjob.md)
*   [SageMakerHyperParameterTuningJob](sagemakerhyperparametertuningjob.md)
*   [SageMakerPipeline](sagemakerpipeline.md)
*   [SageMakerModelPackageGroup](sagemakermodelpackagegroup.md)
*   [SageMakerModelPackage](sagemakermodelpackage.md)
*   [SageMakerFeatureGroup](sagemakerfeaturegroup.md)
*   [SageMakerMonitoringSchedule](sagemakermonitoringschedule.md)
*   [SageMakerDataQualityJobDefinition](sagemakerdataqualityjobdefinition.md)
*   [SageMakerModelQualityJobDefinition](sagemakermodelqualityjobdefinition.md)
*   [SageMakerModelBiasJobDefinition](sagemakermodelbiasjobdefinition.md)
*   [SageMakerModelExplainabilityJobDefinition](sagemakermodelexplainabilityjobdefinition.md)
