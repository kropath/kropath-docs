# AWS Kinesis Governance Configuration

The `KinesisConfig` CRD is the governance configuration for all AWS Kinesis streams in kropath. It enables platform teams to enforce organization-wide policies for capacity mode, shard counts, and naming conventions across Kinesis Data Streams. Platform teams deploy named configuration profiles (such as `general-policy` and `high-throughput`) to codify capacity and compliance postures for different workload tiers.

## Prerequisites and Setup

Kinesis streams are created through the `KinesisStream` resource, but all Kinesis resources leverage the `KinesisConfig` CRD for governance. No additional prerequisites are required beyond a Kubernetes cluster with kropath installed.

## Configuration

Kropath's Kinesis governance is managed through `KinesisConfig` custom resource instances in the `kro-system` namespace. Each `KinesisConfig` CR defines a named profile (e.g., `general-policy`, `high-throughput`) that Kinesis stream resources reference via the `configRef` field.

### KinesisConfig Core Structure

A `KinesisConfig` CR contains two governance tiers: `mandatory` (enforced rules) and `defaults` (baseline configuration). These two tiers follow the kropath governance cascade (ADR-010, ADR-015 §5.3).

*   **`mandatory`** section: Fields set here enforce strict policies that cannot be overridden by Kinesis stream instances. Use this tier for compliance requirements that must not be violated.
*   **`defaults`** section: Fields set here provide baseline configurations that Kinesis stream instances can override. Use this tier for sensible defaults that operators can customize per-resource.

**Note:** Scalar fields (strings, integers) cannot be set in both tiers simultaneously. Map fields (`tags`, `syncedLabels`, `syncedAnnotations`) are additive and can be set in both tiers.

### KinesisConfig Governance Fields

KinesisConfig governs capacity mode, shard counts, naming, and metadata.

#### Capacity Mode Governance

*   `streamMode` (string, sentinel=""): Controls whether streams use ON_DEMAND or PROVISIONED capacity mode. Valid values: `"on_demand"` (auto-scaling), `"provisioned"` (manual shard count). When set in `mandatory`, this mode is forced; when set in `defaults`, it applies to streams that don't specify one. The default business default is `"on_demand"` if no tier specifies a value.
*   `shardCount` (integer, sentinel=0): Number of shards for provisioned streams. Only applies when `streamMode` is `"provisioned"`; ignored in ON_DEMAND mode. When set in `mandatory`, this count is forced; when set in `defaults`, it applies to provisioned streams that don't specify one. The RGD built-in default is 1 shard if no tier specifies a value.

#### Naming and Metadata Governance

*   `namingTemplate` (string, sentinel=""): Specifies a naming template for stream names. The template uses tokens like `{namespace}`, `{name}`, `{account_id}`, and `{region}`. When set in `mandatory`, this template is forced; when set in `defaults`, it applies to streams that don't specify a naming override. AWS Kinesis stream names allow `a-zA-Z0-9_.-` characters (case-sensitive) and must be 1–128 characters long.
*   `tags` (map<string,string>): Cloud tags (AWS resource tags) applied to all Kinesis streams. Merged across mandatory and defaults tiers.
*   `syncedLabels` (map<string,string>): Kubernetes labels that are mirrored as AWS resource tags, prefixed with `aws.kropath.run/`.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations that are mirrored as AWS resource tags, prefixed with `aws.kropath.run/`.

### KinesisConfig Organization-Wide Blanket Governance

Two KinesisConfig fields are also available in `KropathConfig` for org-wide enforcement:

*   `KropathConfig.spec.mandatory.kinesis.streamMode` (string): Org-wide requirement for capacity mode across all Kinesis streams in all namespaces.
*   `KropathConfig.spec.mandatory.kinesis.shardCount` (integer): Org-wide requirement for shard count in provisioned streams.

When set in `KropathConfig`, these fields override the corresponding `KinesisConfig` settings, ensuring organization-wide compliance.

### Ten-Tier Governance Cascade

Kropath employs a ten-tier governance cascade to resolve effective configuration for Kinesis streams. The `kropath-controller` pre-merges all governance sources (from `KropathConfig` and `KinesisConfig`) into `status.effectiveConfig` on the namespaced `KinesisConfig` CR. Kinesis stream RGDs read this `status.effectiveConfig` to determine the final, resolved settings.

**When to use `KropathConfig.kinesis` vs. `KinesisConfig`:**

*   **`KropathConfig.kinesis`:** Used for blanket, organization-wide governance that applies across *all* Kinesis configuration profiles. For example, setting `KropathConfig.mandatory.kinesis.streamMode: "on_demand"` would force all Kinesis streams in the organization to use ON_DEMAND capacity, regardless of the `KinesisConfig` profile they reference.
*   **`KinesisConfig`:** Used for per-profile governance. For instance, a `high-throughput` `KinesisConfig` profile might require provisioned streams with 8 shards for resource-intensive workloads, while the `general-policy` profile defaults to ON_DEMAND for cost-efficient, bursty traffic patterns.

## KinesisConfig Profiles

Kropath ships with two example `KinesisConfig` profiles. Platform teams can create additional profiles as needed.

### general-policy Profile

The default profile for most workloads. It provides sensible defaults for cost efficiency with ON_DEMAND capacity:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}  # No mandatory overrides; allows per-stream customization
  defaults:
    streamMode: "on_demand"
    shardCount: 0  # Zero-value sentinel; falls through to cascade
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

### high-throughput Profile

A stricter profile for workloads with high-throughput, low-latency requirements. Uses provisioned capacity with a higher shard count:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisConfig
metadata:
  name: high-throughput
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: high-throughput
spec:
  mandatory:
    streamMode: "provisioned"  # Force provisioned mode for predictable performance
    shardCount: 8               # Mandatory minimum capacity
  defaults:
    namingTemplate: "{namespace}-{name}"
    tags:
      workload-tier: high-throughput
    syncedLabels: {}
    syncedAnnotations: {}
```

## Governance Cascade Behavior

All governance fields follow a three-tier cascade (mandatory → instance → defaults):

| Field | Cascade behavior |
|---|---|
| `streamMode` | Mandatory tier forces a mode; instance can override if mandatory is not set; defaults applies if both mandatory and instance are empty. Final fallback: `"on_demand"` |
| `shardCount` | Mandatory tier forces a count; instance can override if mandatory is not set; defaults applies if both mandatory and instance are 0 (not set). Final fallback: 1 shard (RGD built-in default, only applies in provisioned mode) |
| `namingTemplate` | Mandatory tier forces a template; instance `nameOverride` bypasses the template; defaults applies if both mandatory and instance are empty |
| `tags` | Additive merge: mandatory + instance + defaults (keys in all tiers coexist; mandatory keys cannot be overridden by instances) |
| `syncedLabels` | Additive merge: mandatory + instance + defaults (applied as both K8s labels and cloud tags with `aws.kropath.run/` prefix) |
| `syncedAnnotations` | Additive merge: mandatory + instance + defaults (applied as both K8s annotations and cloud tags with `aws.kropath.run/` prefix) |

## Mutual-Exclusivity Validation

`KinesisConfig` enforces that scalar governance fields (streamMode, shardCount, namingTemplate) cannot be set in both `mandatory` and `defaults` tiers simultaneously. Any attempt to set the same field in both tiers is rejected with a validation error.

**Example — rejected configuration:**

```yaml
spec:
  mandatory:
    streamMode: "on_demand"
  defaults:
    streamMode: "provisioned"  # Rejected: streamMode in both tiers
```

## Naming Templates and AWS Constraints

Stream names follow AWS Kinesis constraints:

*   **Character set:** `a-zA-Z0-9_.-` (case-sensitive)
*   **Length:** 1–128 characters
*   **Scoping:** Account + region (not globally unique)

The default naming template is `{namespace}-{name}`, which produces names like `analytics-click-events` for a stream named `click-events` in the `analytics` namespace.

**Dynamic tag tokens in naming templates:** Naming templates support `{tag.X}` syntax to include tag values in the stream name. For example, `{tag.env}-{namespace}-{name}` uses the value of the `env` tag. If a referenced tag key is absent, the token is replaced with an empty string.

## Example KinesisConfig for Compliance

A compliance-focused profile for regulated workloads:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisConfig
metadata:
  name: compliance
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: compliance
spec:
  mandatory:
    streamMode: "provisioned"
    shardCount: 4
    namingTemplate: "regulated-{namespace}-{name}"  # Enforce naming prefix for audit
    tags:
      compliance-tier: regulated
      cost-center: security
    syncedLabels:
      data-classification: sensitive
  defaults:
    tags:
      monitoring: enabled
    syncedAnnotations:
      team: data-governance
```

## Out of Scope

The following Kinesis features are not managed by `KinesisConfig` and require direct AWS API or separate custom resources:

*   **Encryption at rest** — Configure via AWS KMS directly or Kinesis-specific encryption settings
*   **Data retention period** — Configured per-stream via the Kinesis API
*   **Enhanced monitoring** — Configure shard-level metrics directly in the stream settings
*   **Kinesis Data Firehose** — Separate AWS service; not part of the Kinesis governance model
*   **Kinesis Analytics** — Separate AWS service
*   **Kinesis Video Streams** — Separate AWS service
