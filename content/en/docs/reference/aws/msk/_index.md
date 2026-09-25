---
title: AWS MSK — Managed Apache Kafka Clusters
description: The AWS MSK family within kropath provides abstractions for managing Amazon MSK (Managed Streaming for Apache Kafka) infrastructure.
doc_type: reference
weight: 350
---
# AWS MSK — Managed Apache Kafka Clusters

The AWS MSK family within kropath provides abstractions for managing Amazon MSK (Managed Streaming for Apache Kafka) infrastructure. It enables platform engineers to enforce organization-wide controls such as mandatory encryption at rest and in transit, Kafka version governance, enhanced monitoring levels, and naming conventions, while allowing application teams to provision and configure Kafka clusters, broker configurations, serverless clusters, and VPC connectivity for event-driven architectures, real-time data pipelines, change data capture (CDC), and stream processing.

## Prerequisites and Setup

`MSKCluster`, `MSKConfiguration`, `MSKServerlessCluster`, and `MSKVPCConnection` resources can be created independently of compute or networking resources, but the MSK family integrates with other kropath families for end-to-end infrastructure management:

*   **KMS Family:** For referencing AWS KMS keys to enable encryption at rest via `MSKConfig.spec.mandatory.encryptionAtRestKmsKeyId` or `MSKConfig.spec.defaults.encryptionAtRestKmsKeyId`.
*   **Secrets Manager Family:** For associating SASL/SCRAM authentication secrets with MSK clusters.
*   **VPC Family (future):** For specifying subnets and security groups that determine broker placement and network isolation.
*   **KropathConfig:** For org-wide encryption, version, and monitoring governance applied across all MSK profiles.

## Configuration

Kropath's MSK configuration is managed through `MSKConfig` custom resources that define per-profile governance policies. These resources leverage an eight-tier governance cascade (ADR-010, ADR-015 §5.3) to ensure compliance while providing flexibility.

### MSKConfig Governance Resource

`MSKConfig` CRs define per-profile governance settings for all MSK resources (clusters, configurations, serverless clusters, and VPC connections). These profiles are referenced by resource instances via `spec.configRef` and selected through Kubernetes label selectors using the `aws.kropath.run/resource-name` label.

Each `MSKConfig` includes `mandatory` and `defaults` sections for governance fields:

*   **`mandatory`:** Fields set in this section enforce strict policies that cannot be overridden by individual resource instances. If a `mandatory` field is set, the instance's corresponding field (if present) is ignored.
*   **`defaults`:** Fields set here provide baseline configurations that resource instances can override. They apply only when the instance's corresponding field is not explicitly set.

**Example Profiles:**

*   `general-policy`: The default production profile with secure-by-default encryption (TLS between clients and brokers, inter-broker encryption enabled) and Kafka 3.6.0.
*   `pci`: A hardened compliance profile for PCI DSS workloads with mandatory at-rest and in-transit encryption, restricted versions, and enhanced monitoring.
*   `hipaa`: A compliance profile for HIPAA-covered entities with mandatory encryption and audit logging configuration.

### MSKConfig Core Fields

An `MSKConfig` instance defines governance for Kafka version, broker instance type, encryption (at rest and in transit), enhanced CloudWatch monitoring, naming conventions, and tags. Here are the key configuration sections:

#### Kafka Version Governance

*   **`kafkaVersion`** (string, default: `""` for mandatory, `"3.6.0"` for defaults): Specifies the Apache Kafka version enforced or defaulted across clusters using this profile. When set in the `mandatory` tier, all clusters referencing this profile must use this version. When set in the `defaults` tier, clusters that do not explicitly specify a version inherit this value.

#### Broker Instance Type Governance

*   **`instanceType`** (string, default: `""` for mandatory, `"kafka.m5.large"` for defaults): Specifies the EC2 instance type for Kafka brokers (e.g., `kafka.m5.large`, `kafka.m5.xlarge`). This field applies only to provisioned `MSKCluster` and `MSKServerlessCluster` resources. When mandatory, all clusters must use this instance type. When default, clusters without an explicit instance type inherit this value.

#### Encryption at Rest

*   **`encryptionAtRestKmsKeyId`** (string, default: `""` for both tiers): Specifies the AWS KMS key ID, ARN, or alias for encrypting EBS volumes. An empty value means AWS service-managed keys are used. When set in the `mandatory` tier, all clusters use this key. When set in the `defaults` tier, it applies to clusters without an explicit KMS key configuration.

#### Encryption in Transit — Client-Broker

*   **`encryptionInTransitClientBroker`** (string, options: `"TLS"`, `"TLS_PLAINTEXT"`, `"PLAINTEXT"`; defaults: `""` mandatory, `"TLS"` defaults): Controls the encryption mode between clients and brokers. `"TLS"` enforces encryption, `"TLS_PLAINTEXT"` allows both encrypted and plaintext, and `"PLAINTEXT"` allows only plaintext (not recommended). The `"TLS"` default ensures secure-by-default communication.

#### Encryption in Transit — Inter-Broker

*   **`encryptionInTransitInCluster`** (string, options: `"true"`, `"false"`; defaults: `""` mandatory, `"true"` defaults): Specifies whether inter-broker traffic (between Kafka brokers) is encrypted. Set to `"true"` to enforce encryption, `"false"` for no encryption. The `"true"` default ensures brokers communicate securely.

**Note on three-state semantics:** The `encryptionInTransitInCluster` field uses three-state logic (empty, "true", "false"). An empty string in the governance tier means "not enforced"; the resource instance must provide a value or another governance layer must supply it. This differs from boolean fields in other families — refer to the spec for exact cascade rules.

#### Enhanced CloudWatch Monitoring

*   **`enhancedMonitoring`** (string, options: `"DEFAULT"`, `"PER_BROKER"`, `"PER_TOPIC_PER_BROKER"`, `"PER_TOPIC_PER_PARTITION"`; defaults: `""` mandatory, `"DEFAULT"` defaults): Specifies the CloudWatch monitoring granularity. `"DEFAULT"` provides basic metrics, while higher levels provide broker-level, topic-level, and partition-level metrics respectively. Higher levels incur additional CloudWatch costs.

#### Naming Conventions

*   **`namingTemplate`** (string, default: `""` for mandatory, `"{namespace}-{name}"` for defaults): Specifies a template for generating effective cluster and configuration names. Tokens include `{namespace}` (Kubernetes namespace), `{name}` (resource name), `{account_id}`, and `{region}`. AWS MSK names are 1–64 characters and can contain only alphanumeric characters, hyphens, and underscores. This field applies to `MSKCluster`, `MSKConfiguration`, and `MSKServerlessCluster` only — `MSKVPCConnection` has no name field (see Naming Conventions section below).

#### Tags and Labels

*   **`tags`** (map<string,string>, default: `{}`): AWS cloud tags applied to all MSK resources created with this profile. When set in the `mandatory` tier, these tags are merged into all resource tags and cannot be removed. When set in the `defaults` tier, they provide a baseline that resources can augment. **Note:** `MSKConfiguration` is an exception — the underlying ACK kafka/Configuration CRD does not support tags, so tag governance does not apply to `MSKConfiguration` resources.

*   **`syncedLabels`** (map<string,string>, default: `{}`): Kubernetes labels that are automatically mirrored as AWS cloud tags (prefixed with `aws.kropath.run/`) and as Kubernetes resource labels. This enables consistent labeling across both platforms.

*   **`syncedAnnotations`** (map<string,string>, default: `{}`): Kubernetes annotations that are mirrored to both Kubernetes metadata and cloud tags (prefixed with `aws.kropath.run/`).

### KropathConfig MSK Family Section

`KropathConfig` defines org-wide governance for MSK that applies to *all* MSK profiles. Only blanket encryption, version, and monitoring fields are mirrored at the `KropathConfig` level (not instance-type or naming, which are profile-specific):

```yaml
spec:
  mandatory:
    msk:
      kafkaVersion: ""                       # Org-wide mandatory Kafka version
      enhancedMonitoring: ""                 # Org-wide mandatory monitoring level
      encryptionInTransitClientBroker: ""    # Org-wide mandatory client-broker encryption
      encryptionInTransitInCluster: ""       # Org-wide mandatory inter-broker encryption
      encryptionAtRestKmsKeyId: ""           # Org-wide mandatory KMS key
  defaults:
    msk:
      kafkaVersion: ""
      enhancedMonitoring: ""
      encryptionInTransitClientBroker: ""
      encryptionInTransitInCluster: ""
      encryptionAtRestKmsKeyId: ""
```

**When to use `KropathConfig.msk` vs. `MSKConfig`:**

*   **`KropathConfig.msk`:** Used for blanket, organization-wide governance that applies across *all* MSK profiles. For example, setting `KropathConfig.mandatory.msk.encryptionInTransitClientBroker: "TLS"` would force all MSK clusters in the organization to use TLS encryption between clients and brokers, regardless of the `MSKConfig` profile they use.
*   **`MSKConfig`:** Used for per-profile governance. For instance, a `pci` profile might mandate specific Kafka versions or monitoring levels only for PCI-regulated clusters, allowing other profiles more flexibility.

## Quick Start

### Step 1: Create a Default MSKConfig Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MSKConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}  # No mandatory overrides
  defaults:
    kafkaVersion: "3.6.0"
    instanceType: "kafka.m5.large"
    encryptionAtRestKmsKeyId: ""  # AWS service-managed key
    encryptionInTransitClientBroker: "TLS"
    encryptionInTransitInCluster: "true"
    enhancedMonitoring: "DEFAULT"
    namingTemplate: "{namespace}-{name}"
    tags:
      team: platform
      environment: production
    syncedLabels:
      data-classification: internal
    syncedAnnotations: {}
```

### Step 2: Create a PCI Compliance Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MSKConfig
metadata:
  name: pci
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: pci
spec:
  mandatory:
    kafkaVersion: "3.7.0"
    instanceType: "kafka.m5.xlarge"
    encryptionAtRestKmsKeyId: "arn:aws:kms:us-east-1:123456789012:key/abc123"
    encryptionInTransitClientBroker: "TLS"
    encryptionInTransitInCluster: "true"
    enhancedMonitoring: "PER_BROKER"
    namingTemplate: "pci-{namespace}-{name}"
    tags:
      compliance: pci
      cost-center: security
  defaults: {}
```

### Step 3: Reference a Profile in an MSKCluster

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MSKCluster
metadata:
  name: my-cluster
  namespace: analytics
spec:
  configRef: general-policy  # Reference the profile by name
  numberOfBrokerNodes: 3
  clientSubnets:
    - subnet-12345678
    - subnet-87654321
    - subnet-aabbccdd
  securityGroups:
    - sg-12345678
  tags:
    application: streaming-pipeline
```

The cluster will inherit:
- Kafka version 3.6.0 (from `defaults`)
- Instance type `kafka.m5.large` (from `defaults`)
- TLS encryption between clients and brokers (from `defaults`)
- Inter-broker encryption enabled (from `defaults`)
- DEFAULT enhanced monitoring (from `defaults`)
- Name derived from `{namespace}-{name}` template: `analytics-my-cluster`
- Tags merged from profile defaults and instance-level tags

## Naming Conventions

MSK resource names are governed by AWS naming constraints and the `namingTemplate` field in `MSKConfig`:

*   **Name length:** 1–64 characters
*   **Allowed characters:** Alphanumeric characters, hyphens (`-`), and underscores (`_`)
*   **Default template:** `{namespace}-{name}` — derived from the Kubernetes namespace and resource name

The effective name (called `effectiveName` in the RGD) is resolved from the naming template, with `spec.nameOverride` providing an escape hatch to bypass the template entirely.

**Applies to:** The naming template governs `MSKCluster`, `MSKConfiguration`, and `MSKServerlessCluster` names only. `MSKVPCConnection` has no provider `name` field — AWS identifies VPC connections by their ARN (UUID), not by name.

**Note on ARN prediction:** Unlike some services, MSK cluster and configuration ARNs include an AWS-assigned UUID component that cannot be predicted before creation. Therefore, `status.predictedArn` is omitted from `MSKCluster` and `MSKConfiguration` resources. After creation, `status.clusterArn` and `status.configurationArn` (populated from the underlying ACK resource metadata) provide the full ARN.

## Eight-Tier Governance Cascade

Kropath employs an eight-tier governance cascade (ADR-010, ADR-015 §5.3) to resolve the effective configuration for each MSK resource. The cascade is split between **GLOBAL** (organization-wide, via `KropathConfig`) and **LOCAL** (per-profile, via `MSKConfig`) governance:

**GLOBAL (org-wide via KropathConfig):**
1. **`KropathConfig.mandatory`** — org-wide forced values (any MSK field)
2. **`KropathConfig.mandatory.msk`** — org-wide forced MSK-specific fields

**LOCAL (per-profile via MSKConfig):**
3. **`MSKConfig.mandatory`** — profile-specific forced values (any MSK field)
4. **Resource `spec`** — instance-level overrides
5. **`MSKConfig.defaults`** — profile-specific defaults (any MSK field)

**GLOBAL defaults (org-wide via KropathConfig):**
6. **`KropathConfig.defaults.msk`** — org-wide MSK-specific defaults
7. **`KropathConfig.defaults`** — org-wide defaults (any MSK field)

**Built-in:**
8. **Built-in defaults** — hardcoded defaults in the RGD schema

Tiers 1–5 are **mandatory-or-override** tiers (they enforce or override values). Tiers 6–8 are **defaults-only** tiers (they apply only when no mandatory or override value is present). Within each tier group, more specific scopes (MSK-specific, then profile-level, then org-wide) take precedence over general scopes.

The `kropath-controller` pre-merges all governance sources and writes `status.effectiveConfig` onto the namespaced `MSKConfig` CR. Resource instances (clusters, configurations, etc.) read this single, pre-merged configuration and do not directly access the cascade — this ensures a consistent view of governance.

**Mutation rule:** Mandatory fields cannot be overridden by lower-priority tiers. If a field is set in any `mandatory` tier (levels 1–3), that value is fixed regardless of instance-level or defaults-tier settings.

## Validation Rules

The `MSKConfig` CRD enforces the following validation rules via `x-kubernetes-validations`:

*   **Mutual exclusivity per scalar field:** For each scalar field (e.g., `kafkaVersion`, `instanceType`, `encryptionAtRestKmsKeyId`), you **cannot** set a non-empty value in both `spec.mandatory` and `spec.defaults` simultaneously. Choose one tier per field.

*   **Example violation:**
    ```yaml
    spec:
      mandatory:
        kafkaVersion: "3.7.0"  # ❌ Error: both tiers set
      defaults:
        kafkaVersion: "3.6.0"
    ```
    Result: "kafkaVersion must be set in either mandatory or defaults, not both."

*   **Map fields (tags, syncedLabels, syncedAnnotations):** These are exempt from the mutual-exclusivity rule. Both `mandatory` and `defaults` may contain map values simultaneously — they are merged additively.

## Encryption by Default

The `general-policy` profile and `KropathConfig` defaults are designed for security-first operation:

*   **Encryption in transit:** `encryptionInTransitClientBroker: "TLS"` (secure-by-default; clients and brokers communicate over TLS)
*   **Inter-broker encryption:** `encryptionInTransitInCluster: "true"` (secure-by-default; brokers encrypt traffic to each other)
*   **Encryption at rest:** An empty `encryptionAtRestKmsKeyId` (default) means AWS service-managed key encryption is applied

These defaults align with AWS best practices and security frameworks. Teams can adjust them via `MSKConfig` profiles for specific compliance or operational needs.

## Multi-Profile Governance

Platform teams may deploy multiple `MSKConfig` profiles to support different workload requirements:

*   **`general-policy`:** Default for most clusters
*   **`pci`:** For PCI DSS environments (stricter encryption, monitoring, audit logging)
*   **`hipaa`:** For HIPAA-covered entities
*   **`dev`:** For development/test clusters (lighter governance, cost optimization)

Each profile captures a set of governance policies. Resource instances select a profile via `spec.configRef`, and the controller resolves the effective configuration from that profile and the org-wide `KropathConfig`.

## Cross-Provider Notes

The MSK family is AWS-specific. GCP has a Managed Service for Apache Kafka (via GCP managed Kafka), and Azure has Event Hubs with Kafka-compatible endpoints. Each provider will have its own family design (e.g., `ManagedKafkaConfig` in `gcp.kropath.run`, `EventHubsConfig` in `azure.kropath.run`) when `kropath-gcp` and `kropath-azure` are bootstrapped. Field names and governance structures may differ due to provider-specific capabilities.

## Reference

For detailed schema specifications and acceptance criteria, see [MSKConfig Specification](https://github.com/kropath/kropath-core/blob/main/docs/specs/aws/aws-msk-01-mskconfig.md) in kropath-core.

For end-to-end resource implementation examples and RGD field references, see the individual resource guides (MSKCluster, MSKConfiguration, MSKServerlessCluster, MSKVPCConnection) — available when those resources are documented.
