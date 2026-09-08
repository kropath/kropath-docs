# MWAA (Managed Workflows for Apache Airflow)

AWS MWAA provides fully managed Apache Airflow environments for orchestrating data pipelines and workflows. kropath brings governance and multi-environment management to MWAA through:

- **[MWAAConfig](mwaaconfig.md)** — Governance profiles that define mandatory policies and default configurations across your organization
- **[MWAAEnvironment](mwaaenvironment.md)** — Individual MWAA environment instances that inherit governance policies and manage their own DAGs and infrastructure

## Get Started

1. **Platform teams:** Deploy an `MWAAConfig` governance profile (e.g., `general-policy`, `production`, `dev`) in the `kro-system` namespace
2. **Developers:** Create `MWAAEnvironment` resources that reference a governance profile via `spec.configRef`
3. **Governance cascade:** Mandatory policies cannot be overridden; defaults can be customized per environment

## Core Concepts

### Two-Tier Configuration Model

| Tier | Purpose | User |
|---|---|---|
| **MWAAConfig** | Organization-wide governance, compliance policies, baseline defaults | Platform teams |
| **MWAAEnvironment** | Individual Airflow runtime, DAG storage, team-specific settings | Data engineers, data teams |

### Governance Cascade

Every environment's effective configuration merges:
1. **Org-wide mandatory** (KropathConfig) — Highest priority
2. **Profile mandatory** (MWAAConfig) — Override instance settings
3. **Instance spec** (MWAAEnvironment) — Individual overrides
4. **Profile defaults** (MWAAConfig) — Baseline recommendations
5. **Org-wide defaults** (KropathConfig) — Lowest priority

Mandatory policies cannot be overridden; defaults can be customized or extended per environment.

## Common Use Cases

### Use `MWAAConfig`

- Enforce encryption and security settings across all environments
- Set standard environment sizing, autoscaling bounds, and maintenance windows
- Mandate specific Airflow versions for compliance
- Configure org-wide logging defaults and audit tags
- Define naming conventions for environment names
- Restrict which teams can use which governance profiles

### Use `MWAAEnvironment`

- Create a new Airflow environment for a team or project
- Select a governance profile (`configRef`) that matches your use case (dev, production, data-platform)
- Specify your DAG storage (S3 bucket and path)
- Configure per-component logging levels for troubleshooting
- Scale workers and web servers based on workload
- Override defaults where needed within governance constraints

## Key Features

### Per-Component Logging

Independently control logging for five Airflow components:
- DAG processing
- Scheduler
- Task execution
- Web server / UI
- Workers

Each component can have different log levels (CRITICAL, ERROR, WARNING, INFO, DEBUG) and can be toggled on/off.

### Flexible Autoscaling

Set min/max bounds for:
- Celery workers
- Web servers
- Scheduler processes

Autoscaling automatically adjusts based on workload.

### VPC Endpoint Management

Choose between AWS-managed (SERVICE) or customer-managed (CUSTOMER) VPC endpoints. Customer mode requires explicit readiness gates before environment creation.

### Governance Profiles

Create multiple profiles for different needs:
- **general-policy** — Secure-by-default, minimal enforcement
- **production** — Hardened security, compliance controls
- **dev** — Permissive, cost-optimized
- **data-platform** — High compute, custom Airflow configuration

## Next Steps

- Start with [MWAAConfig](mwaaconfig.md) to understand governance
- Create your first `MWAAEnvironment` using [MWAAEnvironment](mwaaenvironment.md)
- Review example profiles and use cases in both docs
