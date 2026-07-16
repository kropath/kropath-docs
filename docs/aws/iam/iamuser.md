# IAMUser — Operator Access

The `IAMUser` resource creates IAM users for human operators who need to access your AWS environment using the console or programmatic credentials.

## Overview

An IAM user is a permanent identity representing a human operator. Users can:

- Sign into the AWS Management Console
- Generate long-lived access keys for programmatic API access
- Assume roles for temporary elevated permissions
- Be members of groups to inherit group permissions

**Important:** IAM users are for human operator access only. For application and service identities, use `IAMRole`.

## Creating a User

### Basic User

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMUser
metadata:
  name: alice
  namespace: default
spec:
  configRef: general-policy
```

This creates a user with no group memberships or attached policies.

### User with Group Membership

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMGroup
metadata:
  name: developers
  namespace: default
spec:
  configRef: general-policy
  policies:
    - arn: "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
---
apiVersion: aws.kropath.run/v1alpha1
kind: IAMUser
metadata:
  name: bob
  namespace: default
spec:
  configRef: general-policy
  groups:
    - developers  # Bob automatically gets all developer group permissions
```

Users inherit all policies from their groups.

### User with Direct Policies

For user-specific permissions:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMUser
metadata:
  name: devops-admin
  namespace: default
spec:
  configRef: general-policy
  policies:
    - arn: "arn:aws:iam::aws:policy/AdministratorAccess"
  groups:
    - shared-logs-group  # Also members of this group
```

The user gets both direct policies and group policies.

## Access Keys

Long-lived access keys allow programmatic access to AWS APIs. **Use with caution** — access keys are sensitive credentials.

### Creating Access Keys

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMUser
metadata:
  name: ci-automation
  namespace: default
spec:
  configRef: general-policy
  createAccessKey: true
  policies:
    - arn: "arn:aws:iam::aws:policy/AmazonS3FullAccess"
```

The user's access keys appear in `status.accessKey` (retrieve via kubectl).

### Access Key Governance

Platform teams can block access key creation organization-wide:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory:
    blockIamUserAccessKeys: true  # Blocks ALL access key creation
```

When blocked, setting `createAccessKey: true` on a user is silently ignored (status shows `AccessKeyBlockedByGovernance`).

**Best practice:** Use temporary credentials via `AssumeRole` instead of long-lived access keys whenever possible.

## Temporary Credentials via AssumeRole

Instead of access keys, users can assume a role for temporary credentials:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMRole
metadata:
  name: elevated-permissions
  namespace: default
spec:
  configRef: general-policy
  type: generic
  trustPolicyJSON: |
    {
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::123456789012:user/alice"
        },
        "Action": "sts:AssumeRole"
      }]
    }
  policies:
    - arn: "arn:aws:iam::aws:policy/AdministratorAccess"
```

User `alice` can now assume this role to get temporary elevated permissions:

```bash
aws sts assume-role --role-arn arn:aws:iam::123456789012:role/elevated-permissions \
  --role-session-name alice-admin-session
```

## Path Prefix

Organize users with a path:

```yaml
spec:
  path: "/engineering/"
```

This creates: `arn:aws:iam::ACCOUNT_ID:user/engineering/alice`

Paths organize users logically but don't affect permissions.

## Inline Policies

For user-specific policies:

```yaml
spec:
  inlinePolicies:
    - name: personal-s3-bucket
      documentJSON: |
        {
          "Version": "2012-10-17",
          "Statement": [{
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": "arn:aws:s3:::alice-personal-bucket/*"
          }]
        }
```

Inline policies apply only to this user.

## Tagging

```yaml
spec:
  syncedLabels:
    team: platform
    location: us-west-2
  tags:
    email: alice@company.com
    hire-date: "2023-06-15"
```

Tags help track user metadata in your organization.

## Common Patterns

### CI/CD Service User

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMUser
metadata:
  name: github-actions-ci
  namespace: default
spec:
  configRef: general-policy
  createAccessKey: true
  policies:
    - ref: ci-deployment-policy
```

Create a dedicated user for CI/CD systems, with limited permissions and access keys stored securely.

### Developer User with Group Membership

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMUser
metadata:
  name: alice
  namespace: default
spec:
  configRef: general-policy
  groups:
    - developers
    - data-team
```

Alice gets all permissions from both groups.

### Admin User with Elevated Access

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMUser
metadata:
  name: admin-alice
  namespace: default
spec:
  configRef: general-policy
  groups:
    - admins
  policies:
    - ref: additional-audit-permissions
```

Admin gets group permissions plus additional policies.

## Monitoring

List all users:

```bash
kubectl get iamuser -A
```

Check user group membership:

```bash
kubectl describe iamuser alice -n default | grep -A5 "Groups:"
```

Verify access key status:

```bash
kubectl describe iamuser ci-automation -n default | grep "AccessKey"
```

## Deletion

By default, users are retained. To delete the underlying user:

```yaml
spec:
  deletionPolicy: delete
```

Caution: This deletes the user from AWS, which may be unrecoverable if the user had access keys.

## Security Best Practices

1. **Prefer roles over users** — Use `AssumeRole` for elevated permissions instead of long-lived access keys
2. **Rotate access keys regularly** — If you use access keys, rotate them every 90 days
3. **Use group membership** — Assign users to groups for permission management at scale
4. **Block access keys** — Use the `blockIamUserAccessKeys` mandatory config when possible
5. **MFA** — Require MFA for console access via IAM policy conditions
6. **Least privilege** — Grant only the minimum permissions needed
