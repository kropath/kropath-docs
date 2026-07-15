# IAMGroup — Operator Access Groups

The `IAMGroup` resource creates IAM groups for organizing human operators who need AWS console or programmatic access. Groups simplify permission management by allowing you to attach policies once and assign multiple users.

## Overview

An IAM group is a collection of users who share the same permissions. Use groups to:

- Organize team members by function (developers, DevOps, data analysts)
- Grant the same permissions to multiple users without duplicating policy attachments
- Simplify permission updates — change the group's policies once, all members get the new permissions

**Key difference from roles:** Groups are for human access; roles are for workload identities. Use `IAMRole` for applications and services.

## Creating a Group

### Basic Group

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMGroup
metadata:
  name: developers
  namespace: default
spec:
  configRef: general-policy
```

This creates an empty group with no permissions.

### Group with AWS Managed Policies

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMGroup
metadata:
  name: data-engineers
  namespace: default
spec:
  configRef: general-policy
  policies:
    - arn: "arn:aws:iam::aws:policy/AmazonAthenaReadOnlyAccess"
    - arn: "arn:aws:iam::aws:policy/AmazonS3FullAccess"
```

Members automatically receive these permissions.

### Group with Custom Policies

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMPolicy
metadata:
  name: dev-resources
  namespace: default
spec:
  configRef: general-policy
  documentJSON: |
    {
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Action": ["ec2:Describe*", "ec2:StartInstances", "ec2:StopInstances"],
        "Resource": "*"
      }]
    }
---
apiVersion: aws.kropath.run/v1alpha1
kind: IAMGroup
metadata:
  name: devops-team
  namespace: default
spec:
  configRef: general-policy
  policies:
    - ref: dev-resources
    - arn: "arn:aws:iam::aws:policy/CloudWatchLogsReadOnlyAccess"
```

## Adding Users to Groups

Users inherit all permissions from their groups:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMUser
metadata:
  name: alice
  namespace: default
spec:
  configRef: general-policy
  groups:
    - devops-team  # Alice automatically gets all policies from this group
    - developers   # And all policies from this group
```

If a user is in multiple groups, they have the union of all group permissions.

## Path Prefix

Organize groups with a path:

```yaml
spec:
  path: "/engineering/"
```

This creates: `arn:aws:iam::ACCOUNT_ID:group/engineering/developers`

Paths help organize groups logically but don't affect permissions.

## Inline Policies

For policies used only by one group, attach inline:

```yaml
spec:
  policies:
    - ref: shared-policy  # Reusable policy
  inlinePolicies:
    - name: group-specific
      documentJSON: |
        {
          "Version": "2012-10-17",
          "Statement": [{
            "Effect": "Allow",
            "Action": "organizations:DescribeAccount",
            "Resource": "*"
          }]
        }
```

## Tagging and Metadata

```yaml
spec:
  syncedLabels:
    team: platform
    cost-center: engineering
  tags:
    Environment: production
```

Tags are synced to the cloud resource; labels apply to the Kubernetes resource.

## Common Patterns

### Team-Based Organization

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: IAMGroup
metadata:
  name: frontend-team
  namespace: default
spec:
  configRef: general-policy
  policies:
    - ref: frontend-resources
---
apiVersion: aws.kropath.run/v1alpha1
kind: IAMGroup
metadata:
  name: backend-team
  namespace: default
spec:
  configRef: general-policy
  policies:
    - ref: backend-resources
```

Create a group per team with team-specific permissions.

### Role-Based Access

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: IAMGroup
metadata:
  name: admins
  namespace: default
spec:
  configRef: general-policy
  policies:
    - arn: "arn:aws:iam::aws:policy/AdministratorAccess"
---
apiVersion: aws.kropath.run/v1alpha1
kind: IAMGroup
metadata:
  name: read-only
  namespace: default
spec:
  configRef: general-policy
  policies:
    - arn: "arn:aws:iam::aws:policy/ReadOnlyAccess"
---
apiVersion: aws.kropath.run/v1alpha1
kind: IAMGroup
metadata:
  name: developers
  namespace: default
spec:
  configRef: general-policy
  policies:
    - ref: developer-permissions
```

Create groups by access level and assign users accordingly.

## Monitoring

List all group members:

```bash
kubectl get awsiamuser -A -o yaml | grep -A5 "groups:"
```

Check group permissions:

```bash
kubectl describe awsiamgroup devops-team -n default
```

## Deletion

By default, groups are retained. To delete the underlying group:

```yaml
spec:
  deletionPolicy: delete
```

Caution: Deleting a group doesn't affect users (they keep their individual policies), but it removes the shared group permissions.
