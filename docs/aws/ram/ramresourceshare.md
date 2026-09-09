# RAMResourceShare — Sharing AWS Resources Across Accounts

`RAMResourceShare` is a Kubernetes resource that represents an AWS RAM resource share — a bundle of AWS resources, principals, and permissions that enables cross-account access.

Application teams use resource shares to distribute AWS resources (VPC subnets, Transit Gateways, License Manager configurations, Route 53 Resolver rules, etc.) to other AWS accounts, including principals outside your AWS Organization if governance allows.

## Overview

A `RAMResourceShare` defines:

- **Resources to share** — AWS resource ARNs (subnets, Transit Gateways, etc.)
- **Principals to grant access to** — AWS account IDs, Organization/OU ARNs, or IAM role/user ARNs
- **Permissions** — Custom or AWS-managed permissions that define what principals can do
- **External principal control** — Whether principals outside your Organization are allowed (governed via `RAMConfig`)
- **Governance** — Naming, tags, deletion behavior (inherited from `RAMConfig`)

Resource shares are the primary consumer-facing construct in the RAM family — they enable teams to distribute resources with controlled access.

## Prerequisites

- A Kubernetes cluster running kropath-aws
- `kropath-controller` deployed in the cluster
- At least one `RAMConfig` profile deployed (defaults to `general-policy`)
- AWS resources that can be shared (subnets, Transit Gateways, etc.) in the target account
- Principal identifiers (AWS account IDs, ARNs) that will receive access

## Basic Structure

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RAMResourceShare
metadata:
  name: vpc-share
  namespace: production
spec:
  configRef: general-policy            # RAMConfig profile to use
  nameOverride: ""                      # Override naming template (empty = use template)
  deletionPolicy: retain                # retain | delete

  # Resource access control
  allowExternalPrincipals: null         # nil (governed) | false | true
  resourceARNs:
    - "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abcdef"
    - "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-ghijkl"
  principals:
    - "222233334444"                    # External AWS account
    - "arn:aws:iam::222233334444:role/ShareRecipient"

  # Permissions — choose ONE: permissionRefs OR permissionARNs
  permissionRefs:
    - from:
        name: subnet-readonly           # In-cluster RAMPermission
        namespace: production

  # OR

  permissionARNs:
    - "arn:aws:ram::123456789012:permission/abcdef-1234567890"

  # Metadata and governance
  tags:
    team: platform-network
    sharing-model: cross-account
  syncedLabels: {}
  syncedAnnotations: {}
  sources: []                           # For AWS-managed integrations

status:
  resourceName: production-vpc-share    # Resolved name from template
  namingStatus: "valid"                 # valid | invalid-unresolved-tokens
  resourceShareArn: arn:aws:ram::123456789012:resource-share/12345678-1234-1234-1234-123456789abc
  predictedArn: arn:aws:ram::123456789012:resource-share/12345678-1234-1234-1234-123456789abc
  shareStatus: "ACTIVE"                 # ACTIVE | PENDING | FAILED | DELETING | DELETED
```

## Core Fields

### Resources to Share (`resourceARNs`)

List of AWS resource ARNs that will be shared through this share.

**Format:** Full ARN of the resource (not just name)

**Common resource ARNs:**
- Subnets: `arn:aws:ec2:region:account:subnet/subnet-id`
- Transit Gateways: `arn:aws:ec2:region:account:transit-gateway/tgw-id`
- License Manager configs: `arn:aws:license-manager:region:account:license-configuration:lic-id`
- Route 53 Resolver rules: `arn:aws:route53resolver:region:account:resolver-rule/rule-id`

**Example:**
```yaml
spec:
  resourceARNs:
    - "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-12345678"
    - "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-87654321"
```

### Principals (`principals`)

List of AWS principals that can access the shared resources. Accepts account IDs, Organization/OU ARNs, and IAM resource ARNs.

**Valid principal formats:**
- AWS account ID: `"123456789012"`
- Organization ARN: `"arn:aws:organizations::123456789012:organization/o-a1b2c3d4e5"`
- Organizational Unit ARN: `"arn:aws:organizations::123456789012:ou/o-a1b2c3d4e5/ou-a1b2-12345678"`
- IAM role ARN: `"arn:aws:iam::123456789012:role/ShareRecipient"`
- IAM user ARN: `"arn:aws:iam::123456789012:user/recipient"`

**Important:** Not all resource types support IAM role/user principals. Subnet shares, for example, work with account IDs and Organization ARNs, but some resource types may be restricted to account-level access.

**Example:**
```yaml
spec:
  principals:
    - "222233334444"                                                    # Account ID
    - "arn:aws:organizations::123456789012:ou/o-a1b2c3d4e5/ou-a1b2-12345678"  # OU
    - "arn:aws:iam::222233334444:role/ShareRecipient"                  # Role
```

### External Principal Control (`allowExternalPrincipals`)

Controls whether this share may include principals outside your AWS Organization. This setting is governed by `RAMConfig.mandatory.allowExternalPrincipals` — your instance value can be overridden by organization-wide policy.

**Levels:**
- `null` (omitted) — Defer to governance cascade (RAMConfig)
- `false` — This share disallows external principals (Organization members only)
- `true` — This share allows external principals (cross-account, cross-org)

**Governance cascade:**
1. Organization-wide mandatory (`KropathConfig.mandatory.ram.allowExternalPrincipals`)
2. RAMConfig mandatory (`RAMConfig.mandatory.allowExternalPrincipals`)
3. Instance value (`spec.allowExternalPrincipals`)
4. RAMConfig defaults (`RAMConfig.defaults.allowExternalPrincipals`)
5. Built-in default: `false` (secure-by-default)

**Example:**
```yaml
spec:
  allowExternalPrincipals: true  # Allow cross-account/cross-org access
```

If `RAMConfig.mandatory.allowExternalPrincipals: false`, this instance value is overridden and external principals are NOT allowed.

### Permissions

Permissions define what actions principals can perform on the shared resources. Choose ONE approach: `permissionRefs` (in-cluster) or `permissionARNs` (direct ARN).

#### Option 1: Permission References (`permissionRefs`)

Reference `RAMPermission` CRs by name. This approach uses Kubernetes object references.

**Format:**
```yaml
spec:
  permissionRefs:
    - from:
        name: subnet-readonly           # RAMPermission metadata.name
        namespace: production           # (optional, defaults to current namespace)
```

**Example:**
```yaml
spec:
  permissionRefs:
    - from:
        name: subnet-readonly
        namespace: production
```

**Advantages:**
- Declarative reference to Kubernetes objects
- Change the permission in one place; all shares using the reference see the update
- Supports cross-namespace references

#### Option 2: Permission ARNs (`permissionARNs`)

Directly specify AWS RAM permission ARNs. This approach gives fine-grained control but requires tracking ARNs.

**Format:**
```yaml
spec:
  permissionARNs:
    - "arn:aws:ram::123456789012:permission/abcdef-1234567890"
```

**Example:**
```yaml
spec:
  permissionARNs:
    - "arn:aws:ram::123456789012:permission/subnet-readonly-xyz"
    - "arn:aws:ram::123456789012:permission/tgw-access-abc"
```

**Advantages:**
- Direct control — no Kubernetes object dependency
- Supports AWS-managed permissions (though not shown here, AWS provides built-in permissions)
- Can reference permissions from other accounts

#### Mutual Exclusivity

You must choose ONE approach — `permissionRefs` OR `permissionARNs`, not both. Using both will be rejected with an error:

```yaml
# WRONG: both specified
spec:
  permissionRefs:
    - from: { name: subnet-readonly }
  permissionARNs:
    - "arn:aws:ram::123456789012:permission/abcdef-1234567890"

# Result: Error — "permissionARNs and permissionRefs are mutually exclusive"
```

### Resource Type Restrictions

If `RAMConfig.mandatory.allowedResourceTypes` is set, only resources of those types may be shared.

**Example:** If `RAMConfig` restricts sharing to only `ec2:Subnet` and `ec2:TransitGateway`, you cannot share License Manager configurations or Route 53 Resolver rules.

The restriction is enforced by the Kubernetes API:
```
Error: resourceARNs contains resource types not in the allowed list
```

## Governance Fields

All governance is inherited from the selected `RAMConfig` profile via `status.effectiveConfig`:

| Field | Source | Meaning |
|---|---|---|
| `allowExternalPrincipals` | RAMConfig (with cascade) | Whether external principals are allowed |
| `namingTemplate` | RAMConfig | Resolved to `status.resourceName` |
| `tags` | RAMConfig (merged with instance) | Applied to the AWS share resource |
| `syncedLabels` | RAMConfig (merged with instance) | Kubernetes labels + cloud tags |
| `syncedAnnotations` | RAMConfig (merged with instance) | Kubernetes annotations |
| `deletionPolicy` | Instance `spec.deletionPolicy` | `retain` or `delete` |

### Naming

Resource names follow the naming template from `RAMConfig`. The resolved name is stored in `status.resourceName`.

**Example:** If `RAMConfig.defaults.namingTemplate: "{namespace}-{name}"` and you create:
```yaml
metadata:
  name: vpc-share
  namespace: production
```

Then `status.resourceName: "production-vpc-share"`

### Deletion Policy

Controls what happens when you delete the Kubernetes CR.

**Options:**
- `retain` (default) — Keep the AWS resource share; only delete the Kubernetes CR
- `delete` — Delete the AWS resource share when the Kubernetes CR is deleted

**Example:**
```yaml
spec:
  deletionPolicy: retain    # Keep AWS share after CR deletion

  deletionPolicy: delete    # Delete AWS share when CR deleted
```

## Share Status

After creation, the share moves through states. Monitor `status.shareStatus`:

- `ACTIVE` — Share is ready and principals have access
- `PENDING` — Share is being created
- `FAILED` — Share creation failed (check Kubernetes events)
- `DELETING` — Share is being deleted
- `DELETED` — Share has been deleted

**Example:**
```yaml
status:
  shareStatus: "ACTIVE"
```

## Accessing Shared Resources

Once a share is ACTIVE, principals (other AWS accounts) can accept the invitation and access the resources. The consumer-side acceptance workflow is outside the scope of this document (it's handled in the recipient account).

## Common Patterns

### Share Subnets to Another Account (Read-Only)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RAMResourceShare
metadata:
  name: vpc-subnet-share
  namespace: production
spec:
  configRef: general-policy
  allowExternalPrincipals: true
  resourceARNs:
    - "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-12345678"
    - "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-87654321"
  principals:
    - "222233334444"  # Recipient AWS account
  permissionRefs:
    - from:
        name: subnet-readonly
        namespace: production
  tags:
    sharing-model: cross-account
    team: platform-network
```

### Share Transit Gateway Within Organization

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RAMResourceShare
metadata:
  name: tgw-share
  namespace: production
spec:
  configRef: general-policy
  allowExternalPrincipals: false  # Organization members only
  resourceARNs:
    - "arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-12345678"
  principals:
    - "arn:aws:organizations::123456789012:ou/o-a1b2c3d4e5/ou-a1b2-12345678"
  permissionRefs:
    - from:
        name: tgw-full-access
        namespace: production
  tags:
    sharing-model: org-internal
    team: network-engineering
```

### Share License Manager Configuration with Full Access

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RAMResourceShare
metadata:
  name: license-config-share
  namespace: production
spec:
  configRef: general-policy
  resourceARNs:
    - "arn:aws:license-manager:us-east-1:123456789012:license-configuration:lic-1234567890abcdef"
  principals:
    - "222233334444"
    - "333344445555"
  permissionARNs:
    - "arn:aws:ram::123456789012:permission/license-manager-access-xyz"
  tags:
    team: license-compliance
    access-level: full
```

### Share Multiple Resources with Different Permissions

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RAMResourceShare
metadata:
  name: multi-resource-share
  namespace: production
spec:
  configRef: cross-account
  resourceARNs:
    - "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-12345678"
    - "arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-87654321"
  principals:
    - "222233334444"
  permissionRefs:
    - from:
        name: subnet-readonly
        namespace: production
    - from:
        name: tgw-full-access
        namespace: production
  tags:
    team: platform-network
```

## Troubleshooting

**"Resource share is not being created"**
- Check if the specified `configRef` profile exists (falls back to `general-policy`)
- Verify all `resourceARNs` are valid and in the correct format
- Ensure `principals` contain valid AWS account IDs or ARNs
- Check Kubernetes events: `kubectl describe ramresourceshare <name> -n <namespace>`

**"Naming is invalid"**
- Check `status.namingStatus` on the share
- If it shows `"invalid-unresolved-tokens"`, verify your naming template can resolve all tokens
- Check that tag tokens (`{tag.env}`) reference tags that actually exist

**"External principals are rejected even though I specified allowExternalPrincipals: true"**
- Check if `RAMConfig.mandatory.allowExternalPrincipals: false` — mandatory overrides instance values
- Check if `KropathConfig.mandatory.ram.allowExternalPrincipals: false` — org-wide overrides all
- Verify you're using valid external principal ARNs, not just account IDs if IDs are required

**"Resource type is not allowed even though it's valid"**
- Check `RAMConfig.mandatory.allowedResourceTypes` — if non-empty, only those types are allowed
- Verify the resource ARN matches the type restriction (e.g., `ec2:Subnet` for subnets)
- Check the resource type format in your ARN against the pattern `<service>:<resourceType>`

**"Principals can't find or accept the share invitation"**
- Share status should be `ACTIVE` — check `status.shareStatus`
- Verify principal ARNs are correct and valid
- In the recipient account, check that the share invitation appears in the AWS RAM console
- Some resource types have restrictions on which principals (account vs. role) can receive access

**"Tags aren't appearing on the AWS share resource"**
- Check both `RAMConfig` and instance `spec.tags` (both are merged)
- Verify mandatory tags are in `RAMConfig.mandatory.tags`
- Check the merged tags in `status.effectiveConfig.tags`
- Ensure `syncedLabels` are prefixed with `aws.kropath.run/` in Kubernetes

## See Also

- [RAMConfig Reference](./ramconfig.md)
- [RAMPermission User Guide](./rampermission.md)
- [RAM Resource Family Overview](./README.md)
- [AWS RAM Resource Shares Documentation](https://docs.aws.amazon.com/ram/latest/userguide/working-with-shared-resources.html)
- [AWS RAM Principals Documentation](https://docs.aws.amazon.com/ram/latest/userguide/principals.html)
