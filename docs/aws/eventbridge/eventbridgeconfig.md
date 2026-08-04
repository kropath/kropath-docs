# EventBridgeConfig — Governance Configuration

The `EventBridgeConfig` resource defines governance profiles that control EventBridge resource behavior across your organization and namespaces. Platform teams create named profiles; developers select the profile they need via `spec.configRef` on each EventBridge resource (event buses, rules, archives, and endpoints).

## Overview

`EventBridgeConfig` establishes two tiers of governance:

- **Mandatory tier** — Controls that cannot be overridden by developers (e.g., minimum archive retention for compliance)
- **Defaults tier** — Baseline values developers can override (e.g., default archive retention if not specified on the resource)

This two-tier approach lets platform teams enforce critical compliance controls while preserving developer flexibility.

## Configuration Fields

### Mandatory Tier

Mandatory values **always apply** and override developer choices:

| Field | Type | Purpose |
|---|---|---|
| `archiveRetentionDays` | integer | Minimum days to retain archived events (0 = not enforced) |
| `namingTemplate` | string | Template for resource names (cannot be overridden) |
| `tags` | map | Tags applied to all EventBridge resources (cannot be removed) |
| `syncedLabels` | map | Labels on Kubernetes and cloud resources |
| `syncedAnnotations` | map | Annotations on Kubernetes and cloud resources |

### Defaults Tier

Default values apply only when **not specified** at the resource level:

| Field | Type | Purpose |
|---|---|---|
| `archiveRetentionDays` | integer | Default retention for archived events (0 = indefinite) |
| `namingTemplate` | string | Default naming template for resources |
| `tags` | map | Default tags for resources |
| `syncedLabels` | map | Default labels |
| `syncedAnnotations` | map | Default annotations |

**Key rule:** Scalar fields (like `archiveRetentionDays` and `namingTemplate`) cannot be set in both mandatory and defaults tiers simultaneously. (Map fields like `tags` can appear in both — they are merged additively.)

## Archive Retention Governance

The `archiveRetentionDays` field controls compliance and operational requirements for event archives:

**Mandatory enforcement:**
```yaml
spec:
  mandatory:
    archiveRetentionDays: 90  # Minimum 90-day retention enforced
```

When set to a non-zero value, this becomes a floor — archives cannot have shorter retention:
- If the archive specifies `retentionDays: 30`, it is overridden to `90`
- If the archive specifies `retentionDays: 365`, it is preserved (exceeds the minimum)
- If the archive specifies `0` (unset), it is overridden to `90`

**Default retention:**
```yaml
spec:
  defaults:
    archiveRetentionDays: 30  # Default 30-day retention if not specified
```

When set, this provides a baseline that archives can override with any value.

**Indefinite retention:**
```yaml
archiveRetentionDays: 0  # 0 = indefinite retention (AWS default)
```

Used when no specific retention period is enforced or needed.

## Naming Templates

Control how EventBridge resources are named. The template supports tokens that are substituted at resource creation:

**Available tokens:**
- `{name}` — The CR name
- `{namespace}` — The Kubernetes namespace
- `{account_id}` — The AWS account ID
- `{region}` — The AWS region
- `{configRef}` — The profile name
- `{tag.<key>}` — Value of a tag key (empty string if the tag doesn't exist)

**Examples:**
```yaml
spec:
  defaults:
    namingTemplate: "{namespace}-{name}"  # Default: app-prod-order-bus

  mandatory:
    namingTemplate: "corp-{namespace}-{name}"  # Enforced: corp-app-prod-order-bus

    # Using tags in naming:
    namingTemplate: "{tag.env}-{namespace}-{name}"  # prod-app-{name} if tag env=prod
```

Override the template per-resource:
```yaml
# In a specific EventBridgeEventBus or EventBridgeRule
spec:
  nameOverride: "my-custom-bus"  # Bypasses the template entirely
```

## Example Profiles

### Baseline (general-policy)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory: {}
  defaults:
    archiveRetentionDays: 0
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

This baseline profile:
- Does not enforce archive retention (defaults to indefinite)
- Generates resource names from namespace and CR name
- Tags all resources with the managed-by label
- Applies no mandatory naming or tagging constraints

### Compliance-Hardened (pci)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeConfig
metadata:
  name: pci
  namespace: kro-system
spec:
  mandatory:
    archiveRetentionDays: 90
    tags:
      compliance-profile: pci
      data-classification: restricted
    syncedLabels:
      compliance: pci
  defaults:
    namingTemplate: "pci-{namespace}-{name}"
    archiveRetentionDays: 365
```

This PCI profile:
- Enforces 90-day minimum retention for all archives
- Mandates compliance and data-classification tags
- Requires compliance labels on all Kubernetes resources
- Provides 365-day default retention (developers can use more, not less)
- Prefixes all resource names with "pci"

### HIPAA Compliance (hipaa)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeConfig
metadata:
  name: hipaa
  namespace: kro-system
spec:
  mandatory:
    archiveRetentionDays: 2555  # 7 years (minimum for PHI)
    tags:
      compliance-profile: hipaa
      pii-handling: restricted
    syncedAnnotations:
      audit-required: "true"
  defaults:
    namingTemplate: "hipaa-{namespace}-{name}"
```

This HIPAA profile:
- Enforces 7-year minimum retention for event archives (HIPAA requirement)
- Mandates PII handling and compliance tags
- Requires audit annotations on all resources
- Provides clear naming that resources are HIPAA-governed

## Using Profiles

Select a profile on any EventBridge resource:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeEventBus
metadata:
  name: order-events
  namespace: payments-prod
spec:
  configRef: pci  # Select the PCI compliance profile
```

If a named profile does not exist, resources fall back to `general-policy`.

## Organization-Wide Defaults

Set org-wide controls using the root configuration:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: default
  namespace: kro-system
spec:
  mandatory:
    eventbridge:
      archiveRetentionDays: 90  # All archives: minimum 90 days

  defaults:
    eventbridge:
      archiveRetentionDays: 30  # All archives: default 30 days
```

**Org mandatory** (e.g., `mandatory.eventbridge.archiveRetentionDays`) applies with **highest priority** — EventBridgeConfig profiles and resources cannot override it.

**Org defaults** (e.g., `defaults.eventbridge.archiveRetentionDays`) act as fallback values — used only when an EventBridgeConfig profile or resource does not specify a value.

## Governance Cascade

The configuration cascade follows a priority system with mandatory controls always winning:

**For mandatory fields:**
- Org mandatory → EventBridgeConfig mandatory → resource spec is ignored
- Mandatory controls cannot be overridden by developers

**For defaults and overrideable fields:**
- Resource-level spec (if provided) wins
- EventBridgeConfig defaults apply (if resource doesn't specify)
- Org-wide defaults apply (if EventBridgeConfig doesn't specify)
- Hardcoded kropath defaults apply (as final fallback)

**Example cascade for archive retention:**

```
User specifies archiveRetentionDays: 120
Config mandatory archiveRetentionDays: 90
Config defaults archiveRetentionDays: 365
Org mandatory archiveRetentionDays: 180  ← This wins (highest priority)

Result: Archive gets 180 days (org mandatory overrides everything)
```

## Monitoring

Verify a profile:

```bash
kubectl get eventbridgeconfig general-policy -n kro-system -o yaml
kubectl describe eventbridgeconfig pci -n kro-system
```

Check what profile a resource is using:

```bash
kubectl describe eventbridgeeventbus order-bus -n payments-prod | grep configRef
```

Inspect the effective configuration that the controller computed:

```bash
kubectl get eventbridgeconfig general-policy -n kro-system -o jsonpath='{.status.effectiveConfig}'
```

## Cross-Provider Notes

- Archive retention governance is AWS EventBridge–specific; GCP Eventarc and Azure Event Grid do not have native archive/replay equivalents
- The naming template token vocabulary is shared across all kropath providers, but each provider has different maximum name lengths and character restrictions
- EventBridge naming is case-sensitive (unlike S3 bucket names); templates are applied as-is
