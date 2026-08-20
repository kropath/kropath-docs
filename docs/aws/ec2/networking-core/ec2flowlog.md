# AWS EC2FlowLog

EC2FlowLog represents a VPC Flow Log—a managed AWS service that captures IP traffic flowing to and from network interfaces in a VPC. Flow logs are sent to CloudWatch Logs, S3, or Amazon Data Firehose for observability and troubleshooting.

## Configuration

*   `resourceId` (string, required): VPC or subnet ID to capture traffic for.
*   `trafficType` (string, required): Type of traffic to log (`"ACCEPT"` for accepted, `"REJECT"` for rejected, `"ALL"` for both).
*   `logDestination` (string, required): Destination for logs (`"CloudWatch"`, `"S3"`, or `"Firehose"`).
*   `logGroupName` (string, for CloudWatch): CloudWatch log group name.
*   `s3BucketName` (string, for S3): S3 bucket name for storing logs.
*   `deliveryStreamName` (string, for Firehose): Kinesis Data Firehose stream name.
*   `logFormat` (string, optional): Custom log format for flow log records.
*   `maxAggregationInterval` (integer, default: 600): Time in seconds to aggregate traffic (60 or 600).
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata merged with governance settings.

## Status Outputs

*   `status.flowLogId`: AWS-assigned Flow Log identifier (format: `fl-*`).
*   `status.flowLogStatus`: Current status (`"creating"`, `"created"`, `"failed"`, `"deleting"`, `"deleted"`).

## Governance

Flow logs respect `EC2Config` governance for `flowLogTrafficType` and `flowLogMaxAggregationInterval`. The `mandatory` tier enforces specific values; `defaults` provides fallbacks.

## Example EC2FlowLog

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2FlowLog
metadata:
  name: vpc-flowlog
  namespace: default
spec:
  resourceId: vpc-0123456789abcdef0
  trafficType: "ALL"
  logDestination: "CloudWatch"
  logGroupName: "/aws/vpc/flowlogs/prod"
  maxAggregationInterval: 600
  tags:
    environment: production
```

## Naming

Flow logs have no user-assigned name. AWS assigns a unique `flowLogId`.

See [EC2Config](../ec2config.md) for governance, [EC2VPC](./ec2vpc.md) for VPC configuration, and [EC2 Family](../ec2.md) for related resources.
