# kropath Engineering Standards

**kropath** (kro + golden path) is a multi-cloud golden path platform built on Kubernetes. This
document is the canonical, provider-neutral reference for CRD/RGD schema conventions, naming
rules, API group rules, and required wiring that all kropath resources follow.

Provider repos (`kropath-aws`, `kropath-gcp`, `kropath-azure`) carry provider-specific deltas on
top of this shared baseline. Each provider repo's contributing guide links here for the shared
layer.

---

## 1. API Group Convention

**Rule:** All kropath custom resources use a **provider-prefixed** API group.

| Provider | `apiVersion` |
|---|---|
| AWS | `aws.kropath.run/v1alpha1` |
| GCP | `gcp.kropath.run/v1alpha1` |
| Azure | `azure.kropath.run/v1alpha1` |

> **Migration note:** The bare `kropath.run` API group is **deprecated**. Resources that previously
> used `kropath.run/v1alpha1` must migrate to the provider-prefixed form. No new CRDs or RGDs may
> use the bare `kropath.run` group.

---

## 2. Kind Naming Convention

**Rule:** Kind names carry **no provider prefix**. The kind describes the resource type; the API
group already encodes the provider.

### Correct examples

| Resource | Kind | API group |
|---|---|---|
| AWS S3 bucket configuration | `S3Config` | `aws.kropath.run/v1alpha1` |
| AWS S3 bucket instance | `S3Bucket` | `aws.kropath.run/v1alpha1` |
| Org-wide platform configuration | `KropathConfig` | `aws.kropath.run/v1alpha1` |
| GCP Cloud Storage configuration | `StorageConfig` | `gcp.kropath.run/v1alpha1` |
| Azure Blob container configuration | `BlobConfig` | `azure.kropath.run/v1alpha1` |

### Prohibited patterns

| Anti-pattern | Reason |
|---|---|
| `AWSS3BucketConfig` | Provider prefix in kind is redundant; API group already encodes provider |
| `AWSKropathConfig` | Same — redundant prefix |
| `GCPStorageConfig` | Same |
| `AzureBlobConfig` | Same |

### Config CR kinds

The two canonical config CR kinds across all providers are:

- **`<ResourceFamily>Config`** — per-resource-family governance configuration (e.g. `S3Config`,
  `IAMConfig`, `StorageConfig`). Always a hand-authored CRD with `spec.mandatory` / `spec.defaults`.
- **`KropathConfig`** — org-wide and namespace-scoped platform configuration. Always a hand-authored
  CRD with `spec.mandatory` / `spec.defaults`.

---

## 3. Label and Annotation Key Convention

**Rule:** All kropath-managed label keys, annotation keys, and `externalRef` `matchLabels` keys
are **provider-prefixed**.

| Provider | Key prefix | Example label key |
|---|---|---|
| AWS | `aws.kropath.run/` | `aws.kropath.run/resource-name` |
| GCP | `gcp.kropath.run/` | `gcp.kropath.run/resource-name` |
| Azure | `azure.kropath.run/` | `azure.kropath.run/resource-name` |

> **Migration note:** The bare `kropath.run/resource-name` and `kropath.run/config-name` label
> forms are **deprecated**. No new RGDs, CRDs, or test fixtures may use them.

### Required labels on every config CR and externally-referenced resource

Every config CR (e.g. `S3Config`, `KropathConfig`) and every resource referenced via `externalRef`
(e.g. `PolicyDocument`) **must** carry the provider-prefixed `resource-name` label so
`selector.matchLabels` lookups can resolve them:

```yaml
# AWS example
metadata:
  labels:
    aws.kropath.run/resource-name: general-policy

# GCP example
metadata:
  labels:
    gcp.kropath.run/resource-name: general-policy

# Azure example
metadata:
  labels:
    azure.kropath.run/resource-name: general-policy
```

---

## 4. CRD Schema Rules

- Every governance field must appear in **both** `spec.mandatory` and `spec.defaults` with safe
  zero-value defaults, so callers can set a field in either tier without schema errors.
- `x-kubernetes-validations` rules must prevent a field from being set in both tiers simultaneously
  (mutual exclusion at the field level).
- `crds/` directories contain CRDs only; `rgds/` directories contain kro RGDs only. Never mix.

This tier-symmetry requirement ensures that any governance field is available in both tiers. Without
it, a platform team that wants to mandate a field in `mandatory` would face a schema error if the
same field was absent from `defaults` (or vice versa). The mutual-exclusion validation prevents
conflicting values across tiers.

---

## 5. Governance Config Hierarchy

kropath-controller pre-merges governance inputs from three layers and writes the result onto the
namespaced `<ResourceFamily>Config` CR as `status.effectiveConfig`. RGDs read only this
pre-merged value — they never merge layers themselves.

| Layer | Kind | Scope |
|---|---|---|
| 1 | `KropathConfig` | Org-wide + namespace |
| 2 | `<ResourceFamily>Config` | Per resource-family (controller writes `status.effectiveConfig`) |
| 3 | Resource instance `spec` | Developer overrides |

This three-layer model lets platform teams set org-wide defaults and mandatory values at layer 1,
resource-family-specific governance at layer 2, and still allows developers to override non-mandatory
fields at layer 3.

---

## 6. `externalRef` Pattern — `selector.matchLabels` Required

**Rule:** `externalRef` entries in RGDs **must** use `selector.matchLabels` to locate the target
resource. CEL expressions in `externalRef.metadata.name` are **not** evaluated by kro — that field
is treated as a literal string and the lookup silently fails.

### Correct pattern (all providers)

```yaml
# AWS example — S3Config lookup
- id: rsrcCfg
  externalRef:
    apiVersion: aws.kropath.run/v1alpha1
    kind: S3Config
    selector:
      matchLabels:
        aws.kropath.run/resource-name: ${schema.?spec.?configRef.orValue("general")}

# GCP example — StorageConfig lookup
- id: rsrcCfg
  externalRef:
    apiVersion: gcp.kropath.run/v1alpha1
    kind: StorageConfig
    selector:
      matchLabels:
        gcp.kropath.run/resource-name: ${schema.?spec.?configRef.orValue("general")}

# Azure example — BlobConfig lookup
- id: rsrcCfg
  externalRef:
    apiVersion: azure.kropath.run/v1alpha1
    kind: BlobConfig
    selector:
      matchLabels:
        azure.kropath.run/resource-name: ${schema.?spec.?configRef.orValue("general")}
```

### Accessing effectiveConfig fields

Always access pre-merged config through `status.effectiveConfig`:

```yaml
# Correct
tags: ${rsrcCfg.status.effectiveConfig.mandatory.tags + schema.spec.tags + rsrcCfg.status.effectiveConfig.defaults.tags}

# Wrong — never access via spec
tags: ${rsrcCfg.spec.mandatory.tags}
```

Access pattern:
- `rsrcCfg.status.effectiveConfig.mandatory.*`
- `rsrcCfg.status.effectiveConfig.defaults.*`
- `rsrcCfg.status.effectiveConfig.<provider>.*` (provider-specific fields)

Status definitions go in `spec.schema.status` inside the RGD schema block, **not** `spec.status`.

---

## 7. Required Wiring on Child Resources

Every child Kubernetes resource produced by an RGD must receive:

| Wiring | Source |
|---|---|
| `metadata.labels` with `<provider>.kropath.run/` prefix | `mergedSyncedLabels` |
| `metadata.labels["app.kubernetes.io/managed-by"]` = `kro` | Literal |
| `metadata.labels["app.kubernetes.io/instance"]` = `${schema.metadata.name}` | CEL |
| `metadata.annotations` with `<provider>.kropath.run/` prefix | `mergedSyncedAnnotations` |
| Provider deletion policy (see below) | Config or policy CR |
| Cloud resource tags | `allCloudMetadata` |

### Deletion policy per provider

| Provider | Field | Retain value | Delete value |
|---|---|---|---|
| AWS (ACK) | `metadata.annotations["services.k8s.aws/deletion-policy"]` | `retain` | `delete` |
| GCP (KCC) | `metadata.annotations["cnrm.cloud.google.com/deletion-policy"]` | `abandon` | `delete` |
| Azure (ASO) | `spec.reconcilePolicy.objectDeletionPolicy` | `Detach` | `Delete` |

This wiring ensures consistent labelling, annotation propagation, and lifecycle management across
all kropath-managed resources regardless of provider.

---

## 8. Naming Convention

- **`effectiveName`** is the cloud resource name, resolved from a naming template or `spec.nameOverride`.
- **`status.resourceName`** exposes `effectiveName`.
- **`status.predictedArn`** is built from `effectiveName` — **never from `metadata.name`**.
- **`status.namingStatus`** = `"valid"` | `"invalid-unresolved-tokens"` — required on every RGD that uses naming.
- **`spec.nameOverride: string`** with `default: ""` — required in every RGD schema that uses naming.

### Naming exemption

Not all cloud resources have a `name` field. For resources identified by URL, ARN, key ID, or
similar (rather than a `name`), the naming convention **does not apply**. Such resources must not
include `effectiveName`, `spec.nameOverride`, `status.resourceName`, `status.predictedArn`, or
`status.namingStatus`. The resource's spec section on naming must explicitly state that the naming
convention does not apply and explain why.

---

## 9. Feature Availability

**Rule:** kropath features are **always enabled**. There are no per-feature CLI flags (`--enable-*`).

Feature availability is expressed by **which image version you deploy**, not by runtime flags. Every
reconciler in kropath-controller self-registers in the feature registry on startup. The full list of
active reconcilers is queryable at the `/features` HTTP endpoint.

This design avoids the complexity of feature-flag permutations and makes it straightforward to
reason about which capabilities are present in a given deployment: upgrade the image to get new
features.

---

## 10. CRD vs RGD — When to Use Each

kropath uses two distinct Kubernetes resource types. Confusing them causes incorrect implementations.

### CRD — Custom Resource Definition

Hand-authored Kubernetes schema (`apiVersion: apiextensions.k8s.io/v1`). Defines field shapes and
validation rules. Lives in `crds/` in provider repos.

Only these kinds are hand-authored CRDs:
- **Config CRs** (e.g. `S3Config`, `IAMConfig`): governance configuration per resource type; carry
  `status.effectiveConfig` written by kropath-controller. Always have `spec.mandatory` /
  `spec.defaults` with tier-symmetry.
- **Standalone policy/document** (e.g. `PolicyDocument`): referenced by RGDs via `externalRef`; does
  not compose children.

### RGD — Resource Group Definition (kro)

A kro `ResourceGroup` YAML that defines a composition template. Lives in `rgds/` in provider repos.
RGDs define the resource instance schema (developer-facing `spec`), use CEL expressions (`${}`) for
all dynamic values, and produce child provider CRs via a single `externalRef` for the config lookup.

**Resource instances** (e.g. `S3Bucket`) are always RGDs — kro auto-generates the CRD from the RGD
schema.

### Decision table

| Artifact | Type | Where it lives |
|---|---|---|
| `<ResourceFamily>Config` schema (e.g. `S3Config`) | CRD | `crds/` |
| `KropathConfig` schema | CRD | `crds/` |
| `PolicyDocument` schema | CRD | `crds/` |
| Resource composition (e.g. `S3Bucket` → ACK Bucket) | RGD | `rgds/` |

**Rule of thumb:** Schema that Kubernetes validates on admission → CRD. Composes child resources → RGD.

---

## 11. Other Standards

- **Security first:** Default to secure; mandatory config overrides user-supplied values. Platform
  teams can enforce security baselines that individual developers cannot override.
- **Licensing:** Apache 2.0 license headers in every RGD file and script.
- **CEL:** Use `${}` for all dynamic values in RGD templates. Keep per-field expressions inline;
  do not centralize merged expressions in shared CEL variables.
