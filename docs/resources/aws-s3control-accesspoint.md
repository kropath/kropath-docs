# S3ControlAccessPoint

`S3ControlAccessPoint` is a Kubernetes resource that represents an Amazon S3 access point — a named endpoint with its own permissions and network controls for accessing an S3 bucket. Access points simplify managing data access at scale for shared datasets.

## Scope

This resource is AWS-only. It wraps the ACK `AccessPoint` resource from the S3 Control service. GCP and Azure manage bucket access through different mechanisms (IAM bindings and RBAC/SAS).

## What it solves

Managing access to shared S3 buckets at scale creates challenges:

- **Shared bucket policies are complex** — policy documents grow unwieldy with many access patterns
- **No VPC isolation** — bucket-level access controls don't restrict to VPC access
- **Naming collisions** — application teams need separate access points but manage a shared bucket
- **Public access risks** — need to enforce public access blocking per access point
- **Cross-account sharing** — limited control over which accounts can access buckets

`S3ControlAccessPoint` solves this by providing:

- **Named endpoints** — each application team gets a dedicated access point with its own ARN and DNS alias
- **VPC restriction** — optional VPC-only access, enforced at the access point level
- **Per-point policies** — each access point can have independent permissions
- **Public access control** — enforce public access blocking at the access point
- **Cross-account support** — grant access points to external AWS accounts via bucket owner delegation
- **Governance integration** — inherit public access and VPC settings from `S3AdvancedConfig` profiles

## Core concepts

### Access points vs. bucket policies

Traditional bucket policies apply to all access to a bucket, making them complex and hard to audit. Access points let you:

- Create separate endpoints for different teams or applications
- Apply independent policies to each endpoint
- Delegate access between AWS accounts
- Restrict access to VPC traffic only

Think of an access point as a "gateway" to a bucket with its own permissions and network restrictions.

### VPC-only access

Restrict an access point to only work within a specific VPC:

```yaml
spec:
  vpcConfiguration:
    vpcID: vpc-12345678  # Only accessible from this VPC
```

This prevents internet-facing access, ensuring data stays within your VPC.

### Public access blocking

Control whether public access is allowed at the access point:

```yaml
spec:
  publicAccessBlockConfiguration:
    blockPublicACLs: true      # Ignore public ACLs
    blockPublicPolicy: true    # Ignore public policies
    ignorePublicACLs: true     # Ignore existing public ACLs
    restrictPublicBuckets: true  # Deny public bucket access
```

Set all to `true` for maximum security (recommended default).

### Cross-account access

Grant an access point to a different AWS account:

```yaml
spec:
  accountID: "111111111111"        # Current (bucket owner) account
  bucketAccountID: "222222222222"  # External (data consumer) account
  bucket: "data-bucket"            # Bucket name
```

The external account can then grant IAM permissions to users to access this access point.

## Complete example

Here's a VPC-restricted access point for a data analytics team:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: S3ControlAccessPoint
metadata:
  name: analytics-endpoint
  namespace: data-platform
spec:
  # Use the compliance profile, which mandates public access blocking
  configRef: compliance
  
  # AWS account ID (from cluster metadata if omitted)
  accountID: "123456789012"
  
  # Reference the shared data bucket
  bucket: shared-data-bucket
  
  # Restrict to VPC-only access
  vpcConfiguration:
    vpcID: vpc-12345678
  
  # Public access blocking is enforced by the profile
  publicAccessBlockConfiguration:
    blockPublicACLs: true
    blockPublicPolicy: true
    ignorePublicACLs: true
    restrictPublicBuckets: true
  
  # Optional: access point policy (JSON)
  policy: |
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "AWS": "arn:aws:iam::123456789012:role/analytics-role"
          },
          "Action": [
            "s3:GetObject",
            "s3:ListBucket"
          ],
          "Resource": [
            "arn:aws:s3:*:123456789012:accesspoint/*/object/*"
          ]
        }
      ]
    }
  
  # Deletion policy: retain
  deletionPolicy: retain
  
  # Tags for organization
  tags:
    team: data-platform
    purpose: analytics
```

## Cross-account sharing

Here's how to share a bucket's access point with another AWS account:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3ControlAccessPoint
metadata:
  name: external-partner-access
  namespace: data-platform
spec:
  accountID: "123456789012"        # Your AWS account (bucket owner)
  bucketAccountID: "987654321098"  # Partner's AWS account
  bucket: shared-data-bucket       # Your bucket name
  
  # VPC access for partners is optional; internet access is allowed by default
  publicAccessBlockConfiguration:
    blockPublicACLs: true
    blockPublicPolicy: true
    ignorePublicACLs: true
    restrictPublicBuckets: true
  
  # Partner account's IAM roles get permission via their own IAM policies
```

The partner account can then create an IAM role granting their users access to this access point's ARN.

## Naming

Access point names are generated from a template using:

| Token | Value |
|---|---|
| `{namespace}` | Kubernetes namespace |
| `{name}` | CR name |
| `{account_id}` | AWS account ID |
| `{region}` | AWS region |

**Default template**: `{namespace}-{name}`

**Example**: CR in namespace `data-platform` named `analytics-endpoint` produces access point name `data-platform-analytics-endpoint`.

## Governance

Access points inherit public access blocking settings from `S3AdvancedConfig` profiles. You can enforce:

- **Mandatory public access blocking** for all access points in the cluster
- **Mandatory VPC-only** access for compliance workloads
- **Org-wide policies** via `KropathConfig.s3Advanced` settings

## DNS and usage

After creation, the access point gets a DNS alias (e.g., `analytics-endpoint-123456789012.s3.us-east-1.amazonaws.com`). Applications can use this alias like a bucket name.

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `S3ControlAccessPoint`
- **Scope**: Namespaced
