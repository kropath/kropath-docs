# AWS CloudTrail

The AWS CloudTrail family within kropath provides abstractions for managing Amazon CloudTrail audit logging. It enables platform engineers to enforce organization-wide audit controls such as log encryption, multi-region trail configuration, and log retention policies, while allowing application teams to provision and configure CloudTrail trails and event data stores for their specific compliance and operational needs.

## Resources

*   **[CloudTrailConfig](cloudtrailconfig.md):** Governance model for defining mandatory and default audit logging policies.
*   **[CloudTrailTrail](cloudtrailtrail.md):** Create and manage CloudTrail trails for API activity logging.
*   **[CloudTrailEventDataStore](cloudtraileventdatastore.md):** Create and manage CloudTrail Lake event data stores for SQL-based event querying.

## Overview

CloudTrail records API calls and events across your AWS environment. kropath provides three resource kinds to manage this:

*   **CloudTrailConfig:** A governance resource that defines per-profile mandatory and default settings for both trails and event data stores, enforcing organization-wide controls while allowing team-specific overrides.
*   **CloudTrailTrail:** An atomic resource that creates an AWS CloudTrail trail, delivering API activity logs to S3 with optional CloudWatch Logs streaming, SNS notifications, and KMS encryption.
*   **CloudTrailEventDataStore:** An atomic resource that creates a CloudTrail Lake event data store for SQL-based querying of audit events, with configurable retention, multi-region support, and termination protection.

## Getting Started

To provision CloudTrail resources in your cluster:

1. Create a `CloudTrailConfig` governance profile (or use the default `"general-policy"`).
2. Create one or more `CloudTrailTrail` instances for API logging, referencing your chosen config profile.
3. Optionally create `CloudTrailEventDataStore` instances for event querying and analysis.

Each resource follows kropath's ten-tier governance cascade, where organization-wide policies (via `KropathConfig`) take precedence over profile-specific defaults (via `CloudTrailConfig`), which in turn yield to instance-level overrides.
