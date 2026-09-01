# AWS Kinesis Governance Configuration

The `KinesisConfig` CRD is the governance configuration for all AWS Kinesis resources in kropath. It enables platform teams to enforce organization-wide policies for data streaming resources, including capacity mode (ON_DEMAND vs PROVISIONED), shard count, naming conventions, and tagging strategies. Platform teams deploy named configuration profiles (such as `general-policy` and `high-throughput`) to codify capacity and compliance postures for different workload tiers.

## Prerequisites and Setup

Kinesis resources are created independently, but all Kinesis resources leverage the `KinesisConfig` CRD for governance. Ensure that:

- kropath is installed in your cluster with the `kinesis` family enabled
- The `kropath-controller` is running and has permissions to reconcile `KinesisConfig` CRs
- At least one `KinesisConfig` profile exists in the `kro-system` namespace (the default `general-policy` profile ships with kropath)

## Configuration

Kropath's Kinesis governance is managed through `KinesisConfig` custom resource instances in the `kro-system` namespace or locally in resource namespaces. Each `KinesisConfig` CR defines a named profile (e.g., `general-policy`, `high-throughput`) that Kinesis resources reference via the `configRef` field.

### KinesisConfig Core Structure

A `KinesisConfig` CR contains two governance tiers: `mandatory` (enforced rules) and `defaults` (baseline configuration). These two tiers follow the kropath governance cascade (ADR-010, ADR-015 §5.3).

*   **`mandatory`** section: Fields set here enforce strict policies that cannot be overridden by Kinesis resource instances. Use this tier for compliance requirements that must not be violated.
*   **`defaults`** section: Fields set here provide baseline configurations that Kinesis resource instances can override. Use this tier for sensible defaults that operators can customize per-resource.

**Note:** Scalar fields (strings, integers) cannot be set in both tiers simultaneously — the CRD validation rules prevent this. Map fields (`tags`, `syncedLabels`, `syncedAnnotations`) are additive and can be set in both tiers.

### KinesisConfig Governance Fields

KinesisConfig governs four categories of fields: capacity mode, shard count, naming, and metadata.

#### Capacity Mode Governance

*   `streamMode` (string, sentinel=""): Specifies the capacity mode for Kinesis Data Streams. Valid values are `"on_demand"` (pay-per-request, auto-scaling) or `"provisioned"` (fixed shard count, predictable throughput). When set in `mandatory`, all streams using this profile are forced to the specified mode. When set in `defaults`, it applies to streams that don't specify a capacity mode.

#### Shard Count Governance

*   `shardCount` (integer, sentinel=0): Specifies the number of shards for provisioned-mode streams. Used only when `streamMode` is `"provisioned"`; ignored in `"on_demand"` mode. When set in `mandatory`, all provisioned streams are forced to this shard count. When set in `defaults`, it applies to provisioned streams that don't specify a shard count.

#### Naming Governance

*   `namingTemplate` (string, sentinel=""): Specifies a naming template for Kinesis stream resources. The template uses tokens like `{namespace}`, `{name}`, `{account_id}`, `{region}`, and `{tag.<key>}`. When set in `mandatory`, this template is forced; when set in `defaults`, it applies to resources that don't specify a naming template. Default: `{namespace}-{name}`.

#### Metadata Governance

*   `tags` (map<string,string>): Cloud tags (AWS resource tags) applied to all Kinesis resources. Merged across mandatory and defaults tiers.
*   `syncedLabels` (map<string,string>): Kubernetes labels that are mirrored as AWS resource tags, prefixed with `aws.kropath.run/`. Merged across tiers.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations that are mirrored as AWS resource tags, prefixed with `aws.kropath.run/`. Merged across tiers.

### KinesisConfig Organization-Wide Blanket Governance

Two KinesisConfig fields are also available in `KropathConfig` for org-wide enforcement:

*   `KropathConfig.spec.mandatory.kinesis.streamMode` (string): Org-wide requirement for capacity mode across all Kinesis resources in all namespaces.
*   `KropathConfig.spec.mandatory.kinesis.shardCount` (integer): Org-wide requirement for shard count across all provisioned Kinesis resources.

When set in `KropathConfig`, these fields override the corresponding `KinesisConfig` settings, ensuring organization-wide compliance.

**Tagging fields** (`tags`, `syncedLabels`, `syncedAnnotations`) live at `KropathConfig.spec.mandatory.tags` / `spec.defaults.tags` (org-wide, NOT under `spec.kinesis`). `KinesisConfig` has its own per-type copies under `spec.mandatory.tags` / `spec.defaults.tags`. The `kropath-controller` pre-merges both sources into `status.effectiveConfig`.

### Ten-Tier Governance Cascade

Kropath employs a ten-tier governance cascade to resolve effective configuration for Kinesis resources. The `kropath-controller` pre-merges all governance sources (from `KropathConfig` and `KinesisConfig`) into `status.effectiveConfig` on the namespaced `KinesisConfig` CR. Kinesis resource RGDs read this `status.effectiveConfig` to determine the final, resolved settings.

**When to use `KropathConfig.kinesis` vs. `KinesisConfig`:**

*   **`KropathConfig.kinesis`:** Used for blanket, organization-wide governance that applies across *all* Kinesis configuration profiles. For example, setting `KropathConfig.mandatory.kinesis.streamMode: "on_demand"` would force all Kinesis streams in the organization to use ON_DEMAND mode, regardless of the `KinesisConfig` profile they reference.
*   **`KinesisConfig`:** Used for per-profile governance. For instance, a `high-throughput` `KinesisConfig` profile might mandate `streamMode: "provisioned"` with `shardCount: 8` for high-volume workloads, allowing other profiles different defaults.

## KinesisConfig Profiles

Kropath ships with two example `KinesisConfig` profiles. Platform teams can create additional profiles as needed.

### general-policy Profile

The default profile for most workloads. It provides sensible defaults for cost-optimization and general use:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}  # No mandatory overrides; allows per-resource customization
  defaults:
    streamMode: "on_demand"        # Cost-optimized: pay per request
    shardCount: 0                   # Not used in ON_DEMAND mode
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

### high-throughput Profile

A performance-optimized profile for high-volume, latency-sensitive workloads:

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
    streamMode: "provisioned"      # Enforce provisioned mode for predictable throughput
    shardCount: 8                   # Mandatory shard count for high-throughput workloads
    tags:
      workload-tier: premium
  defaults:
    namingTemplate: "{namespace}-{name}"
    tags:
      cost-center: analytics
    syncedLabels:
      performance-tier: high
```

## Naming Conventions

Kinesis stream names follow AWS constraints:

- **Length:** 1–128 characters
- **Characters:** Alphanumeric (`a-zA-Z0-9`), hyphens (`-`), underscores (`_`), and periods (`.`)
- **Case sensitivity:** Stream names are case-sensitive

### Naming Template Tokens

The `namingTemplate` field supports these tokens for dynamic name generation:

| Token | Description | Example |
|---|---|---|
| `{name}` | CR metadata.name | `my-stream` |
| `{namespace}` | CR namespace | `streaming-prod` |
| `{account_id}` | AWS account ID | `123456789012` |
| `{region}` | AWS region | `us-east-1` |
| `{configRef}` | Configuration profile name | `high-throughput` |
| `{tag.<key>}` | Value of a tag/label/annotation | `{tag.env}` → `prod` |

### Example Naming

Given a `KinesisStream` CR named `click-events` in namespace `streaming-prod` with tags `{env: prod, service: analytics}`:

- Template `{namespace}-{name}` → `streaming-prod-click-events`
- Template `{tag.env}-{tag.service}-{name}` → `prod-analytics-click-events`
- Template `corp-{region}-{name}` → `corp-us-east-1-click-events`

**Missing tokens:** If a `{tag.*}` token refers to a tag that doesn't exist, it resolves to an empty string. For example, if template is `{tag.env}-{name}` but the `env` tag is missing, the result is `-click-events` and `status.namingStatus` is `"valid"`. Unrecognized tokens (e.g., `{env}` instead of `{tag.env}`) remain verbatim and set `status.namingStatus` to `"invalid-unresolved-tokens"`.

## Complete Example: Custom KinesisConfig Profile

Platform teams can create custom profiles for specific workload requirements:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisConfig
metadata:
  name: analytics-pipeline
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: analytics-pipeline
spec:
  mandatory:
    tags:
      environment: production
      compliance: pci-dss
      data-classification: sensitive
    namingTemplate: "analytics-{tag.env}-{name}"
  defaults:
    streamMode: "provisioned"
    shardCount: 4
    tags:
      owner-team: data-platform
      cost-center: analytics
    syncedLabels:
      workload-type: analytics
      sla-tier: standard
    syncedAnnotations:
      runbook-url: "https://wiki.internal/analytics-runbook"
      pagerduty-service-id: "P12345"
```

Streams referencing this profile (`configRef: analytics-pipeline`) will:

- Be forced into `provisioned` mode with 4 shards (mandatory)
- Receive mandatory tags for compliance and environment tracking (cannot be removed)
- Receive default tags for team ownership and cost allocation (can be extended per-stream)
- Have Kubernetes labels and annotations synced to both the CR and AWS resource tags

## Cross-Family Integration

Kinesis streams integrate with other AWS services via `status.predictedArn`, enabling:

**Lambda Event Source Mapping:** Reference the stream ARN in Lambda's event source mapping configuration:
```yaml
EventSourceArn: "arn:aws:kinesis:<region>:<account>:stream/<streamName>"
```

**CloudWatch Alarms:** Monitor stream metrics using CloudWatch, which uses the ARN for dimension matching:
```yaml
Dimensions:
  - Name: StreamName
    Value: <status.resourceName>
```

## Out of Scope

The following Kinesis features are managed outside kropath and not exposed via `KinesisConfig`:

- **Encryption at rest:** Use AWS KMS or managed keys via the AWS console or SDKs
- **Data retention period:** Configured per-stream via separate API; default is 24 hours
- **Enhanced monitoring:** Configure shard-level metrics via AWS console
- **Kinesis Data Firehose:** A separate AWS service; not covered in this resource family
- **Kinesis Data Analytics:** A separate AWS service; not covered in this resource family

## See Also

- [KinesisStream Usage Guide](kinesisstream.md) — Configure individual stream instances
- [ADR-015](https://github.com/kropath/kropath-core/blob/main/docs/adrs/015-consolidated-platform-decisions.md) — Governance cascade design
- [ADR-010](https://github.com/kropath/kropath-core/blob/main/docs/adrs/010-effectiveconfig-cascade-architecture.md) — EffectiveConfig architecture
