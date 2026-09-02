# AWS Kinesis Data Streams

AWS Kinesis Data Streams is a serverless, scalable data stream service that captures, processes, and stores data from various sources in real-time. Kropath provides governance and automation for managing Kinesis streams at scale across your organization.

## Overview

Kinesis streams support two capacity modes:

*   **ON_DEMAND** — Automatic scaling based on demand; billed per GB written. Ideal for unpredictable or bursty workloads.
*   **PROVISIONED** — Fixed number of shards with manual capacity planning. Ideal for predictable, steady-state traffic with known throughput requirements.

Kropath automates stream creation and management through two resources:

*   **`KinesisConfig`** — Governance configuration that defines policies for capacity mode, shard counts, naming conventions, and tagging. Platform teams define named profiles that developers reference.
*   **`KinesisStream`** — The resource that creates actual AWS Kinesis streams, inheriting governance policies from the selected `KinesisConfig` profile.

## Getting Started

1. **Review the governance configuration**: Read [`KinesisConfig` documentation](kinesisconfig.md) to understand available governance profiles and policies.
2. **Create your first stream**: Follow the [`KinesisStream` usage guide](kinesisstream.md) to create streams with appropriate capacity modes and tagging.
3. **Set up cross-family integrations**: Use the stream's ARN (available in `status.predictedArn`) to configure Lambda event source mappings or CloudWatch alarms.

## Key Features

### Governance Policies

Platform teams define `KinesisConfig` profiles to enforce:

*   Mandatory capacity mode (ON_DEMAND or PROVISIONED) for compliance or performance requirements
*   Minimum shard counts for provisioned streams
*   Naming conventions using templates like `{namespace}-{name}` or `{tag.environment}-{name}`
*   Mandatory tags for cost allocation, team attribution, and compliance tracking

### Capacity Mode Management

Switch streams between ON_DEMAND and PROVISIONED modes without disruption. The stream enters an UPDATING state during the transition and returns to ACTIVE once complete.

### Naming and Tagging

*   **Automatic naming** — Naming templates resolve tokens like `{namespace}`, `{name}`, and `{tag.X}` to generate compliant stream names.
*   **Tag inheritance** — Tags merge from governance tiers (mandatory, defaults) and instance-level specifications, with mandatory tags overriding all others.
*   **Label/annotation sync** — Kubernetes labels and annotations are automatically mirrored as AWS resource tags.

### Cross-Family References

Use stream ARNs for:

*   Lambda event source mappings to trigger functions on incoming records
*   CloudWatch alarms to monitor stream metrics and throughput
*   Integration with other AWS services via stream endpoints

## Governance Hierarchy

Kinesis governance follows kropath's standard three-tier cascade:

1. **Mandatory tier** — Platform enforcement; cannot be overridden by developers
2. **Instance tier** — Developer customization; overrides defaults but respects mandatory policies
3. **Defaults tier** — Fallback configuration when instance tier is empty

For example, if a platform team sets `KinesisConfig.mandatory.streamMode: "provisioned"`, all streams using that profile will be provisioned, even if the stream resource specifies `streamMode: "on_demand"`.

## Common Use Cases

### Cost-Optimized Development Streams

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: events
  namespace: dev
spec:
  configRef: dev-policy  # Uses ON_DEMAND by default
```

### High-Throughput Production Streams

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: events
  namespace: prod
spec:
  configRef: high-throughput  # Enforces PROVISIONED with 8+ shards
  shardCount: 16              # Override for higher workloads
```

### Compliance-Regulated Streams

Platform teams create a `compliance` profile with mandatory policies:

```yaml
# KinesisConfig
metadata:
  name: compliance
spec:
  mandatory:
    streamMode: "provisioned"
    namingTemplate: "regulated-{namespace}-{name}"
    tags:
      compliance-tier: regulated
```

Developers then reference it:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: payment-events
  namespace: payments
spec:
  configRef: compliance  # Enforces all governance policies
```

## Related Resources

*   [KinesisConfig Governance Documentation](kinesisconfig.md)
*   [KinesisStream Resource Guide](kinesisstream.md)
*   Kropath architecture: [ADR-010](https://github.com/kropath/kropath-core/blob/main/docs/adrs/010-ten-tier-governance.md) (Governance cascade), [ADR-015](https://github.com/kropath/kropath-core/blob/main/docs/adrs/015-consolidated-platform-decisions.md) (Platform decisions)

## Limitations and Out of Scope

The following Kinesis features are not managed by kropath and require direct AWS configuration:

*   **Encryption at rest** — Configure KMS keys directly via the AWS console or API
*   **Data retention** — Set retention periods per-stream (default 24 hours)
*   **Enhanced monitoring** — Enable shard-level metrics in AWS
*   **Kinesis Data Firehose, Analytics, Video Streams** — Separate AWS services with their own management model
*   **Stream consumers and enhanced fan-out** — Managed outside of kropath
