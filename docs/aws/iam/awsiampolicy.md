# AWSIAMPolicy — Reusable Managed Policies

The `AWSIAMPolicy` resource creates AWS IAM managed policies — reusable permission sets that can be attached to multiple roles, groups, or users.

## Overview

Use `AWSIAMPolicy` to define permissions once and share them across multiple principals. This is the preferred pattern for any permission set used by more than one role, group, or user.

Key benefits:
- **Reusability** — Define once, attach to many principals
- **Consistency** — All principals referencing the policy get the same permissions
- **Lifecycle** — Update the policy once to affect all attached principals
- **Version control** — AWS maintains up to 5 policy versions automatically

## Creating a Policy

### Basic Managed Policy

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSIAMPolicy
metadata:
  name: s3-logs-access
  namespace: default
spec:
  configRef: general-policy
  description: "Policy for writing logs to S3"
  documentJSON: |
    {
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Action": ["s3:PutObject", "s3:PutObjectAcl"],
        "Resource": "arn:aws:s3:::my-logs-bucket/*"
      }]
    }
```

## Attaching to Roles

Reference the policy by name from `AWSIAMRole`:

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSIAMRole
metadata:
  name: lambda-logger
  namespace: default
spec:
  configRef: general-policy
  type: lambda
  policies:
    - ref: s3-logs-access  # References the AWSIAMPolicy above
```

The role automatically gets all permissions defined in the policy.

## Attaching to Groups and Users

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSIAMGroup
metadata:
  name: developers
  namespace: default
spec:
  configRef: general-policy
  policies:
    - ref: s3-logs-access
    - arn: "arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess"
---
apiVersion: kropath.run/v1alpha1
kind: AWSIAMUser
metadata:
  name: alice
  namespace: default
spec:
  configRef: general-policy
  groups:
    - developers
  policies:
    - ref: s3-logs-access
```

## Policy Document Storage

You can store policies in two ways:

### Option 1: Inline JSON (documentJSON)

For smaller policies or when policy is used by only one resource:

```yaml
spec:
  documentJSON: |
    {
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::bucket-name/*"
      }]
    }
```

### Option 2: External Policy Document (documentRef) — Recommended

For reusable policies or when policy document is managed separately, reference an `AWSPolicyDocument` CR:

```yaml
---
apiVersion: kropath.run/v1alpha1
kind: AWSPolicyDocument
metadata:
  name: s3-access-policy
  namespace: default
spec:
  policyJSON: |
    {
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Action": ["s3:GetObject", "s3:PutObject"],
        "Resource": "arn:aws:s3:::bucket-name/*"
      }]
    }
---
apiVersion: kropath.run/v1alpha1
kind: AWSIAMPolicy
metadata:
  name: reusable-s3-access
  namespace: default
spec:
  configRef: general-policy
  description: "Reusable S3 access policy"
  documentRef: s3-access-policy  # References the AWSPolicyDocument above
```

**Advantages of documentRef:**
- Separates policy content from IAM resource definitions
- Multiple IAM resources can reference the same policy document
- Policy document is versioned independently
- Teams can manage policy documents in a shared library

**When to use each:**
- **documentJSON** — Single-use policies specific to one role/group/user
- **documentRef** — Policies shared across multiple resources or managed centrally

## Policy Structure

Policies follow AWS IAM policy syntax:

```yaml
documentJSON: |
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:GetObject",
          "s3:PutObject"
        ],
        "Resource": "arn:aws:s3:::bucket-name/*"
      },
      {
        "Effect": "Deny",
        "Action": "s3:DeleteObject",
        "Resource": "arn:aws:s3:::bucket-name/*"
      }
    ]
  }
```

Refer to [AWS IAM policy syntax](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies.html) for complete documentation.

## Custom IAM Paths

Organize policies with a path prefix:

```yaml
spec:
  path: "/team-a/"
  # This creates: arn:aws:iam::ACCOUNT_ID:policy/team-a/policy-name
```

Paths help organize policies logically but have no effect on permissions.

## Policy Limits

- Maximum policy size: 6,144 characters
- Policy versioning: AWS keeps up to 5 versions automatically
- Updating the policy creates a new version and sets it as default

The size limit is enforced by AWS. If you exceed it, the update fails. Break large policies into multiple smaller ones.

## Monitoring

Check what principals are using a policy:

```bash
kubectl get awsiamrole -A -o yaml | grep "ref: policy-name"
kubectl get awsiamgroup -A -o yaml | grep "ref: policy-name"
kubectl get awsiamuser -A -o yaml | grep "ref: policy-name"
```

Verify policy ARN and version:

```bash
kubectl describe awsiampolicy s3-logs-access -n default
```

## Deletion

By default, policies are retained when deleted. To delete the underlying policy:

```yaml
spec:
  deletionPolicy: delete
```

Caution: Deleting a policy breaks any principals that reference it. Update those principals to use a different policy first.
