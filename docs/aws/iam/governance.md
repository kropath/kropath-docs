# Governance Hierarchy and Cascade

This guide explains how IAM governance controls flow through your organization and how developer overrides interact with platform policies.

## Three-Layer Governance

IAM governance operates in three layers, each taking precedence over the next:

### Layer 1: Organization-Wide Defaults

The `AWSKropathConfig` resource sets org-wide baseline controls that apply to all namespaces and teams:

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSKropathConfig
metadata:
  name: default
  namespace: kro-system
spec:
  mandatory:
    iam:
      blockIamUserAccessKeys: true  # Enforced for entire org
  defaults:
    iam:
      maxSessionDurationSeconds: 3600  # Default for all roles
```

**Scope:** Organization-wide; affects all namespaces and teams.

**When to use:** Set non-negotiable controls that apply everywhere (security, compliance, audit).

### Layer 2: Namespace-Scoped Profiles

The `AWSIAMConfig` resource defines governance profiles per namespace. Teams select the profile they need:

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSIAMConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory:
    maxSessionDurationSeconds: 7200  # 2 hours (stricter than org default)
  defaults:
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
```

**Scope:** Namespace-scoped; affects resources that reference this profile.

**When to use:** Define team or namespace-specific policies without overriding org controls.

### Layer 3: Resource-Level Overrides

Individual resources can override defaults (but not mandatory controls):

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSIAMRole
metadata:
  name: my-role
  namespace: my-namespace
spec:
  configRef: general-policy
  maxSessionDuration: 3600  # Overrides profile default (but must respect mandatory)
```

**Scope:** Single resource.

**When to use:** Fine-tune specific workloads without affecting others.

## Cascade Rules

When a resource is created, governance controls cascade down in this order:

1. **Mandatory tier wins** — Org mandatory > profile mandatory > never from resource
2. **Resource override next** — If resource specifies a value and it's not blocked by mandatory
3. **Profile default last** — If resource and mandatory don't specify

### Example: Session Duration

Suppose your org, profile, and resource have different values:

```
Organization (AWSKropathConfig):
  mandatory.iam.maxSessionDurationSeconds: 0    (not enforced)
  defaults.iam.maxSessionDurationSeconds: 3600  (1 hour)

Profile (AWSIAMConfig):
  mandatory.maxSessionDurationSeconds: 900    (15 minutes - ENFORCED)
  defaults.maxSessionDurationSeconds: 7200    (2 hours)

Resource (AWSIAMRole):
  maxSessionDuration: 1800    (30 minutes - request)
```

**Result:** Role gets 900 seconds (15 minutes) because the profile's mandatory tier wins.

The resource requested 1800, but the profile mandatory is 900, so the role is clamped to 900.

### Example: Naming Template

```
Organization:
  No naming constraint

Profile:
  defaults.namingTemplate: "{namespace}-{name}"

Resource:
  nameOverride: "custom-name"
```

**Result:** Resource uses exact name "custom-name" (override wins).

## Mandatory vs Defaults Tier

### Mandatory Tier

Mandatory controls **cannot be overridden** by developers. Platform teams use this for:

- **Compliance** — Enforce permissions boundary for regulated workloads
- **Security** — Block access key creation for human users
- **Audit** — Require specific tagging or naming patterns
- **Cost control** — Limit session duration

```yaml
spec:
  mandatory:
    permissionsBoundaryArn: "arn:aws:iam::123456789012:policy/Boundary"  # ENFORCED
    blockIamUserAccessKeys: true  # ENFORCED
```

Developers cannot override these values.

### Defaults Tier

Default values apply only when the resource **doesn't specify** a value and mandatory doesn't apply:

```yaml
spec:
  defaults:
    maxSessionDurationSeconds: 3600  # Used only if resource doesn't specify
    namingTemplate: "{namespace}-{name}"  # Used only if resource doesn't override
```

Developers can override defaults by setting explicit values on their resources.

## Common Governance Patterns

### Pattern 1: Org Baseline, Team Profiles

**Organization:**
```yaml
mandatory:
  permissionsBoundaryArn: "arn:aws:iam::ACCOUNT:policy/OrgBoundary"
  blockIamUserAccessKeys: true
```

**Team Profile:**
```yaml
# Custom session duration for this team's workloads
defaults:
  maxSessionDurationSeconds: 7200
```

**Result:** All teams get org boundary and access key blocking. Each team's roles default to 2-hour sessions.

### Pattern 2: Strict Compliance Profile

For regulated workloads (PCI, HIPAA, SOC2):

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSIAMConfig
metadata:
  name: pci-compliance
spec:
  mandatory:
    permissionsBoundaryArn: "arn:aws:iam::ACCOUNT:policy/PCI-Boundary"
    blockIamUserAccessKeys: true
    maxSessionDurationSeconds: 900  # 15 minutes
    namingTemplate: "pci-{namespace}-{name}"
    syncedLabels:
      compliance: pci
  defaults: {}  # No defaults — everything is mandatory
```

Developers selecting `configRef: pci-compliance` get strict compliance controls they cannot override.

### Pattern 3: Development Flexibility

For development and testing:

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSIAMConfig
metadata:
  name: dev
spec:
  mandatory:
    syncedLabels:
      environment: development
  defaults:
    maxSessionDurationSeconds: 43200  # 12 hours
    permissionsBoundaryArn: "arn:aws:iam::ACCOUNT:policy/DevBoundary"
    tags:
      environment: dev
```

Developers get a generous default session duration but stay within the dev boundary.

## Monitoring and Debugging

### Check Effective Configuration

See what governance controls are actually applied:

```bash
kubectl describe awsiamrole my-role -n my-namespace
```

Look for `status.conditions` to see if governance rules were applied.

### Find Which Profile a Resource Uses

```bash
kubectl get awsiamrole my-role -n my-namespace -o jsonpath='{.spec.configRef}'
```

### List All Profiles in a Namespace

```bash
kubectl get awsiamconfig -n kro-system
```

### Check Organization-Wide Defaults

```bash
kubectl get awskropathconfig default -n kro-system -o yaml
```

## Governance Best Practices

1. **Start restrictive, loosen as needed** — Begin with strict mandatory controls, add flexibility through profiles
2. **Use mandatory sparingly** — Only for non-negotiable compliance or security requirements
3. **Create profiles for common use cases** — `general-policy`, `pci-compliance`, `dev`, `production`
4. **Document profile requirements** — Make it clear which teams should use which profile
5. **Audit ownership** — Regularly review who creates resources and which profiles they use
6. **Test before enforcing** — Deploy new profiles with defaults first, then move to mandatory once validated
