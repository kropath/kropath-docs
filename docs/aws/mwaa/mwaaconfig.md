# MWAAConfig — Governance and Compliance Profiles

The `MWAAConfig` resource defines governance policies for all MWAA (Managed Workflows for Apache Airflow) environments in your organization. Platform teams create named profiles (e.g., `general-policy`, `production`, `data-team`) that enforce Airflow versions, environment sizing, security modes, per-component logging, worker/web server autoscaling, and naming conventions. MWAA environment instances select a profile via `spec.configRef` to inherit those policies.

## Core Concepts

**Mandatory Tier** — Policies that cannot be overridden. Use for compliance requirements, security constraints, and non-negotiable performance settings (e.g., "all production environments must use PRIVATE_ONLY access mode").

**Defaults Tier** — Sensible baselines that developers can override. Use for standard recommendations (e.g., secure-by-default settings, reasonable compute sizing).

The kropath controller pre-merges both tiers and all KropathConfig org-wide settings into a single `status.effectiveConfig` that all MWAA environments read.

## Governance Fields

| Field | Purpose | Mandatory | Defaults |
|---|---|---|---|
| `airflowVersion` | Enforce or recommend Airflow version | "" (empty) = not enforced | "2.10.3" (example); "" = latest |
| `environmentClass` | Enforce or recommend environment sizing (mw1.micro–mw1.2xlarge) | "" = not enforced | "mw1.small" = secure-by-default |
| `webserverAccessMode` | Enforce web server access (PUBLIC_ONLY \| PRIVATE_ONLY) | "" = not enforced | "PRIVATE_ONLY" = secure-by-default |
| `endpointManagement` | Enforce VPC endpoint model (SERVICE \| CUSTOMER) | "" = not enforced | "SERVICE" = AWS-managed |
| `kmsKeyARN` | Enforce KMS encryption key ARN | "" = not enforced | "" = AWS-managed encryption |
| `maxWorkers` / `minWorkers` | Enforce or recommend Celery worker autoscaling bounds | 0 = not enforced | 10 / 1 = defaults |
| `maxWebservers` / `minWebservers` | Enforce or recommend web server autoscaling | 0 = not enforced | 2 / 2 = defaults |
| `schedulers` | Enforce or recommend scheduler count | 0 = not enforced | 2 = default |
| `weeklyMaintenanceWindowStart` | Enforce or recommend maintenance window (DAY:HH:MM UTC) | "" = not enforced | "" = MWAA chooses |
| `dagProcessingLogsEnabled` / `Level` | Enforce DAG processing logging state and level | nil / "" = not enforced | true / "INFO" = default |
| `schedulerLogsEnabled` / `Level` | Enforce scheduler logging state and level | nil / "" = not enforced | true / "INFO" = default |
| `taskLogsEnabled` / `Level` | Enforce task logging state and level | nil / "" = not enforced | true / "INFO" = default |
| `webserverLogsEnabled` / `Level` | Enforce web server logging state and level | nil / "" = not enforced | true / "INFO" = default |
| `workerLogsEnabled` / `Level` | Enforce worker logging state and level | nil / "" = not enforced | true / "INFO" = default |
| `airflowConfigurationOptions` | Enforce or provide Airflow `airflow.cfg` key-value overrides | {} = empty (not enforced) | {} = empty (not enforced) |
| `namingTemplate` | Enforce or suggest naming pattern for environments | "" = not enforced | "mwaa-{namespace}-{name}" |
| `tags` | AWS tags for all MWAA environments | {} = no mandatory tags | {} = no default tags |
| `syncedLabels` | Kubernetes labels and corresponding AWS tags | {} = no mandatory labels | {} = no default labels |
| `syncedAnnotations` | Kubernetes annotations | {} = no mandatory annotations | {} = no default annotations |

## Core Fields

### Governance Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `name` | string | required | Profile name; selected by environments via `spec.configRef` |
| `namespace` | string | required | Always `kro-system` for org-wide profiles; can be namespaced for local policies |

### Spec Structure

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MWAAConfig
metadata:
  name: general-policy      # Profile name referenced by environments
  namespace: kro-system     # Global namespace for org-wide policies
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}             # Policies that cannot be overridden by environments
  defaults: {}              # Sensible baselines that can be overridden
```

## Status Outputs

After the controller reconciles an `MWAAConfig`, the `status.effectiveConfig` contains the merged governance:

| Field | Type | Purpose |
|---|---|---|
| `status.effectiveConfig.mandatory.*` | object | Merged mandatory policies from org-wide `KropathConfig` and `MWAAConfig` |
| `status.effectiveConfig.defaults.*` | object | Merged defaults from org-wide `KropathConfig` and `MWAAConfig` |
| `status.effectiveConfig.aws.region` | string | AWS region from `KropathConfig` |
| `status.effectiveConfig.aws.accountId` | string | AWS account ID from `KropathConfig` |

All MWAA environments read this single merged view via an `externalRef` lookup.

## Field Validation

`MWAAConfig` enforces mutual exclusivity on scalar fields: a field cannot be set to a non-default value in both `mandatory` and `defaults` simultaneously. Map fields like `tags`, `syncedLabels`, `syncedAnnotations`, and `airflowConfigurationOptions` can appear in both tiers and merge additively.

The CRD validates this at admission time via `x-kubernetes-validations`.

## Complete Examples

### General Policy (Secure-by-Default)

A standard profile for most workloads with secure defaults and no mandatory enforcement:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MWAAConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}  # No enforcement; all fields optional for developers
  defaults:
    environmentClass: mw1.small
    airflowVersion: "2.10.3"
    webserverAccessMode: PRIVATE_ONLY
    endpointManagement: SERVICE
    kmsKeyARN: ""  # AWS-managed encryption
    maxWorkers: 10
    minWorkers: 1
    maxWebservers: 2
    minWebservers: 2
    schedulers: 2
    weeklyMaintenanceWindowStart: ""  # MWAA random
    dagProcessingLogsEnabled: true
    dagProcessingLogsLevel: INFO
    schedulerLogsEnabled: true
    schedulerLogsLevel: INFO
    taskLogsEnabled: true
    taskLogsLevel: INFO
    webserverLogsEnabled: true
    webserverLogsLevel: INFO
    workerLogsEnabled: true
    workerLogsLevel: INFO
    airflowConfigurationOptions: {}
    namingTemplate: "mwaa-{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

Developers can override all defaults unless org-wide `KropathConfig` mandatory settings apply.

### Production Profile (Security + Compliance Enforced)

A hardened profile for production workloads with mandatory encryption, network isolation, and logging:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MWAAConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  mandatory:
    airflowVersion: "2.10.3"           # Enforce tested version
    environmentClass: mw1.medium       # Enforce sizing for consistent performance
    webserverAccessMode: PRIVATE_ONLY  # No internet exposure
    endpointManagement: SERVICE        # Use AWS-managed VPC endpoints
    maxWorkers: 20                      # Cap scaling for cost control
    dagProcessingLogsEnabled: true
    dagProcessingLogsLevel: INFO
    schedulerLogsEnabled: true
    schedulerLogsLevel: INFO
    taskLogsEnabled: true
    taskLogsLevel: INFO
    webserverLogsEnabled: true
    webserverLogsLevel: INFO
    workerLogsEnabled: true
    workerLogsLevel: INFO
    tags:
      environment: production
      cost-centre: data-eng
      compliance: required
  defaults:
    minWorkers: 5
    minWebservers: 2
    minWebservers: 2
    schedulers: 2
    weeklyMaintenanceWindowStart: "SUN:03:00"  # Off-hours maintenance
    airflowConfigurationOptions:
      core.parallelism: "32"
      core.dag_concurrency: "16"
    namingTemplate: "mwaa-prod-{namespace}-{name}"
    syncedLabels:
      audit-required: "true"
    syncedAnnotations: {}
```

Environments using `configRef: production` cannot override mandatory fields. Developers can adjust defaults for their workload but must accept all compliance requirements.

### Development Profile (Permissive and Cost-Conscious)

A profile for non-production workloads with minimal overhead:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MWAAConfig
metadata:
  name: dev
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: dev
spec:
  mandatory: {}  # No enforcement for dev workloads
  defaults:
    environmentClass: mw1.micro         # Minimal sizing
    airflowVersion: ""                  # Latest version
    webserverAccessMode: PRIVATE_ONLY   # Still secure by default
    endpointManagement: SERVICE
    maxWorkers: 5
    minWorkers: 1
    maxWebservers: 1
    minWebservers: 1
    schedulers: 1
    dagProcessingLogsEnabled: true
    dagProcessingLogsLevel: WARNING     # Less verbose in dev
    schedulerLogsEnabled: true
    schedulerLogsLevel: WARNING
    taskLogsEnabled: true
    taskLogsLevel: WARNING
    webserverLogsEnabled: true
    webserverLogsLevel: WARNING
    workerLogsEnabled: true
    workerLogsLevel: WARNING
    airflowConfigurationOptions: {}
    namingTemplate: "mwaa-dev-{namespace}-{name}"
    tags:
      environment: development
```

Developers have full flexibility to experiment; cost is optimized for non-production use.

### Data Platform Profile (Custom Airflow Config)

A profile for complex data pipelines with tuned Airflow configuration:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MWAAConfig
metadata:
  name: data-platform
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: data-platform
spec:
  mandatory:
    environmentClass: mw1.large        # Higher compute for complex DAGs
    webserverAccessMode: PRIVATE_ONLY
    maxWorkers: 50
    minWorkers: 10
    schedulers: 3                       # More schedulers for throughput
    dagProcessingLogsLevel: DEBUG       # Fine-grained troubleshooting
    taskLogsLevel: DEBUG
    airflowConfigurationOptions:
      core.parallelism: "128"
      core.dag_concurrency: "64"
      core.max_active_runs_per_dag: "3"
      scheduler.catchup_by_default: "false"
      smtp.smtp_host: "prod-mail.example.com"
    tags:
      platform: data
      sla-required: "true"
  defaults:
    weeklyMaintenanceWindowStart: "TUE:04:00"
    syncedLabels:
      data-tier: production
```

Developers cannot override the mandatory Airflow configuration keys—those are enforced by the platform team.

## Governance Cascade

The effective configuration for every MWAA environment is determined by merging three layers:

**Layer 1 (Org-wide, highest priority):** `KropathConfig.spec.mandatory.mwaa` and `KropathConfig.spec.defaults.mwaa`
- Only org-wide policies that apply to all environments
- Applies regardless of profile selection

**Layer 2 (Profile-specific):** `MWAAConfig.spec.mandatory` and `MWAAConfig.spec.defaults`
- All governance fields
- Selected by environment's `spec.configRef`

**Layer 3 (Developer instance):** `MWAAEnvironment.spec.airflowVersion`, `.environmentClass`, `.maxWorkers`, etc.
- Individual environment overrides
- Can override defaults but not mandatory policies

**Merge order for effective values:**
- **Mandatory:** Org-wide mandatory (Layer 1) wins over profile mandatory (Layer 2) wins over instance spec
- **Defaults:** Instance spec (Layer 3) wins over profile defaults (Layer 2) wins over org-wide defaults (Layer 1)
- **Instance spec is evaluated against both mandatory and defaults:** mandatory fields cannot be overridden; default fields can

**Map field merging (tags, syncedLabels, syncedAnnotations, airflowConfigurationOptions):**
- All values from all layers merge together (not exclusive)
- Mandatory map values cannot be removed by developers
- Defaults can be supplemented or overridden per-key

## Naming Convention

The `namingTemplate` field in `MWAAConfig` defines the naming pattern for all MWAA environments that reference this profile. The pattern is resolved at environment creation time.

**Available tokens:**
- `{name}` — The environment's Kubernetes resource name
- `{namespace}` — The environment's Kubernetes namespace
- `{configRef}` — The selected governance profile name
- `{account_id}` — AWS account ID from `KropathConfig`
- `{region}` — AWS region from `KropathConfig`
- `{tag.KEY}` — Any tag key from the merged tags (e.g., `{tag.environment}` → "production")

**AWS Constraints:** MWAA environment names:
- Must start with a letter (a–z, A–Z)
- May contain alphanumeric characters, hyphens, and underscores
- Maximum 80 characters

The naming template must produce names that start with a letter. The default template `mwaa-{namespace}-{name}` guarantees compliance through the fixed `mwaa-` prefix.

**Example:** With template `mwaa-{namespace}-{tag.environment}-{name}`, an environment named `airflow-dags` in namespace `data-team` with tag `environment: prod` produces the name `mwaa-data-team-prod-airflow-dags`.

## Per-Component Logging

MWAA environments support independent logging configuration for five components:

- **DAG processing** — Logic that evaluates and schedules your DAGs
- **Scheduler** — The Airflow scheduler process
- **Task** — Individual task execution
- **Web server** — The Airflow UI and REST API
- **Worker** — Celery worker processes executing tasks

Each component can be enabled/disabled and set to a log level independently:

| Log Level | Severity | Use Case |
|---|---|---|
| `CRITICAL` | Errors only | Production, minimal noise |
| `ERROR` | Errors + warnings | Production troubleshooting |
| `WARNING` | Warnings + info messages | Balanced production observability |
| `INFO` | Normal operation details | Default; recommended for most |
| `DEBUG` | Detailed internal state | Development and deep troubleshooting |

### Common Logging Profiles

**Production (default — all enabled at INFO):**
```yaml
spec:
  defaults:
    dagProcessingLogsEnabled: true
    dagProcessingLogsLevel: INFO
    schedulerLogsEnabled: true
    schedulerLogsLevel: INFO
    taskLogsEnabled: true
    taskLogsLevel: INFO
    webserverLogsEnabled: true
    webserverLogsLevel: INFO
    workerLogsEnabled: true
    workerLogsLevel: INFO
```

**Cost-Conscious (only errors):**
```yaml
spec:
  defaults:
    dagProcessingLogsLevel: ERROR
    schedulerLogsLevel: ERROR
    taskLogsLevel: ERROR
    webserverLogsLevel: ERROR
    workerLogsLevel: ERROR
```

**Development (DEBUG for troubleshooting):**
```yaml
spec:
  defaults:
    dagProcessingLogsLevel: DEBUG
    schedulerLogsLevel: DEBUG
    taskLogsLevel: DEBUG
    webserverLogsLevel: DEBUG
    workerLogsLevel: DEBUG
```

Developers can override any component's log level in their environment instance without affecting others.

## VPC Endpoint Management

MWAA supports two VPC endpoint models:

| Mode | Behavior | Setup | Cost |
|---|---|---|---|
| `SERVICE` | AWS-managed VPC endpoints | Automatic; no customer setup required | Included in MWAA pricing |
| `CUSTOMER` | Customer-managed VPC endpoints | You create and configure endpoint resources | AWS charges per endpoint |

### SERVICE Mode (Default, Recommended)

AWS manages all VPC endpoint infrastructure. The environment is created immediately:

```yaml
spec:
  defaults:
    endpointManagement: SERVICE
```

No external setup required. Use this for most workloads.

### CUSTOMER Mode (Advanced)

You create and manage your own VPC interface endpoints. The environment waits for endpoint readiness before starting.

When `endpointManagement: CUSTOMER` is set, the RGD enforces a **readiness gate**:

1. A ConfigMap named `mwaa-vpc-endpoint-gate-<environment-name>` must exist in the same namespace
2. The ConfigMap must contain `data.ready: "true"` to unblock environment creation
3. Once endpoints are ready, update the ConfigMap and environment creation proceeds

Example readiness gate ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mwaa-vpc-endpoint-gate-my-airflow-env
  namespace: default
data:
  ready: "true"  # Set to "true" after VPC endpoints are created and verified
```

Use `CUSTOMER` mode only if you require custom VPC endpoint configuration or isolation.

## Key Behaviors

### Mutual Exclusivity on Mandatory vs Defaults

Each governance field can be set to a non-default value in either the `mandatory` tier or the `defaults` tier, but not both. The CRD validates this at admission time.

**Valid:**
```yaml
mandatory:
  environmentClass: mw1.large  # Enforcement
defaults:
  environmentClass: mw1.small  # Or left empty (default)
```

**Invalid:**
```yaml
mandatory:
  environmentClass: mw1.large
defaults:
  environmentClass: mw1.small  # Error: must be in only one tier
```

### Map Field Merging

The map fields (`tags`, `syncedLabels`, `syncedAnnotations`, `airflowConfigurationOptions`) merge additively across both tiers and org-wide settings. Mandatory values cannot be removed by developers; defaults can be overridden or supplemented per-key.

Example:
- `KropathConfig.mandatory.tags: {cost-centre: data-eng}`
- `MWAAConfig.mandatory.tags: {airflow-version: "2.10"}`
- Environment `spec.tags: {team: analytics}`
- **Result:** All three tag sets merged together (`{cost-centre: data-eng, airflow-version: "2.10", team: analytics}`)

### Label Auto-Injection

The controller label operator automatically adds the label `aws.kropath.run/resource-name: <metadata.name>` to every `MWAAConfig` CR. This label is used by environments' `externalRef` lookups to locate the config profile—no manual labeling is required (though explicitly setting it does not hurt).

## Troubleshooting

### "Must be set in either mandatory or defaults, not both"

An `MWAAConfig` CR was rejected at admission because a governance field is set to a non-default value in both tiers. Choose one tier for that field:
- Use `mandatory` for policies that cannot be overridden
- Use `defaults` for recommendations developers can override

Fix the profile and reapply.

### Environments Won't Find the Config Profile

Check:
1. The `MWAAConfig` CR exists and is in the `kro-system` namespace (or matching namespace if using local policies)
2. The environment's `spec.configRef` matches the profile's `metadata.name` exactly
3. The profile has the label `aws.kropath.run/resource-name: <profile-name>` (auto-injected by the label operator)

If the profile doesn't exist, environments fall back to looking for a `general-policy` profile in the same namespace.

### VPC Endpoint Gate Blocks Environment Creation

If your environment is in `PENDING` state:

1. Verify `spec.endpointManagement` is set to `CUSTOMER`
2. Check if the readiness gate ConfigMap exists: `kubectl get cm mwaa-vpc-endpoint-gate-<env-name> -n <namespace>`
3. If not, create it with `data.ready: "false"` initially
4. After VPC endpoints are created and verified, update the ConfigMap: `data.ready: "true"`
5. Environment creation should proceed immediately

### Airflow Configuration Override Conflicts

If `mandatory.airflowConfigurationOptions` includes a key your environment tries to override, the mandatory value wins. Contact your platform team if a configuration key needs adjustment.

## Next Steps

- Deploy a default profile: `general-policy` in `kro-system`
- Create governance profiles for your organization's compliance and cost requirements
- Reference profiles in MWAA environments via `spec.configRef`
- See [MWAAEnvironment](mwaaenvironment.md) for environment instance examples
