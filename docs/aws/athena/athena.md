# AWS Athena Query Analytics

The AWS Athena family within kropath provides abstractions for managing Amazon Athena query analytics resources. It enables platform engineers to enforce organization-wide controls such as query result encryption, engine versions, and CloudWatch metrics, while allowing application teams to provision workgroups for query isolation, register data catalogs for federated queries, and define reusable parameterized SQL statements.

The Athena family consists of four resource kinds:

*   **AthenaConfig:** A governance CRD that defines mandatory and default settings for Athena workgroups and prepared statements across your organization or per-profile.
*   **AthenaWorkGroup:** An RGD that provisions an AWS Athena workgroup for query isolation, controlling result storage, encryption, query configuration, and Spark session settings.
*   **AthenaDataCatalog:** An RGD that registers external or AWS-managed metastores (Glue, Lambda, Hive, Federated) with Athena for federated query support.
*   **AthenaPreparedStatement:** An RGD that defines reusable parameterized SQL statements scoped to a workgroup.

## Prerequisites and Setup

Athena resources can be created independently, but the Athena family integrates with other kropath families for advanced functionality:

*   **KMS Family:** For referencing AWS KMS keys to enable encryption of query results and Spark session content via `resultKmsKeyRef`, `managedResultsKmsKeyRef`, and `customerContentKmsKeyRef`.
*   **IAM Family:** For specifying IAM execution roles for Spark workgroups via `executionRoleRef`.
*   **S3 Family:** While not directly referenced by Athena resources, S3 buckets often serve as result storage locations. Ensure the bucket policy permits Athena query execution.

## Configuration

Kropath's Athena configuration is managed through governance profiles (`AthenaConfig` CRs) and resource instances (`AthenaWorkGroup`, `AthenaDataCatalog`, `AthenaPreparedStatement`) that reference them. These resources leverage a governance cascade (ADR-010, ADR-015 §5.3) to ensure compliance while providing flexibility.

### Governance Model

`AthenaConfig` CRs define per-profile governance settings for Athena workgroups. Each `AthenaConfig` includes `mandatory` and `defaults` sections:

*   **`mandatory`:** Fields set in this section enforce strict policies that cannot be overridden by resource instances. If a `mandatory` field is set, the instance's corresponding field (if present) is ignored or validated against the mandatory setting.
*   **`defaults`:** Fields set here provide baseline configurations that resource instances can override. They apply only when the instance's corresponding field is not explicitly set.

**Example Profiles:**

*   `general-policy`: A conservative baseline profile (defaults: no metrics, no scan limit, Athena-selected engine version).
*   `analytics`: A profile for analytics workloads (mandatory: CloudWatch metrics enabled, default scan limit of 10 GB, engine version 3).
*   `restricted`: A compliance profile (mandatory: minimum encryption required, workgroup configuration enforced, SSE-KMS result encryption, centralized result location).

The `kropath-controller` pre-merges all governance sources (from `KropathConfig` and `AthenaConfig`) into `status.effectiveConfig` on the namespaced `AthenaConfig` CR. Athena resource RGDs read this `status.effectiveConfig` to determine final settings.

**When to use `KropathConfig.athena` vs. `AthenaConfig`:**

*   **`KropathConfig.athena`:** Used for organization-wide governance that applies across *all* Athena workgroups. For example, setting `KropathConfig.mandatory.athena.enforceWorkGroupConfiguration: true` enforces workgroup isolation across all teams. These fields are WorkGroup-specific: `enforceWorkGroupConfiguration`, `enableMinimumEncryptionConfiguration`, `publishCloudWatchMetricsEnabled`.
*   **`AthenaConfig`:** Used for per-profile governance. For instance, a `pci` `AthenaConfig` profile might mandate SSE-KMS encryption and a specific KMS key only for workgroups using that profile, allowing other profiles more flexibility.

### AthenaConfig Fields

An `AthenaConfig` CRD defines governance settings. Both `mandatory` and `defaults` sections support the same fields:

**WorkGroup-Specific Fields (Governance Tiers):**

*   `enforceWorkGroupConfiguration` (boolean, default: `false`): When `true`, workgroup isolation settings are strictly enforced.
*   `publishCloudWatchMetricsEnabled` (boolean, default: `false`): When `true`, per-query CloudWatch metrics are published.
*   `enableMinimumEncryptionConfiguration` (boolean, default: `false`): When `true`, encryption of query results is required.
*   `bytesScannedCutoffPerQuery` (integer, default: `0`): Maximum bytes scanned per query; `0` means no limit. Not supported for Spark workgroups.
*   `requesterPaysEnabled` (boolean, default: `false`): When `true`, requester-pays buckets are supported for result storage.
*   `resultEncryptionOption` (string, default: `""`): Specifies result encryption: `"SSE_S3"`, `"SSE_KMS"`, `"CSE_KMS"`, or `""` (no encryption).
*   `resultOutputLocation` (string, default: `""`): Default S3 URI for query results (e.g., `"s3://my-bucket/results/"`).
*   `engineVersion` (string, default: `""`): Athena engine version (e.g., `"Athena engine version 3"` or `"AUTO"`); empty means Athena selects the latest stable.

**Common Fields:**

*   `tags` (map<string,string>, default: `{}`): Tags merged across governance tiers and applied to all workgroups and catalogs.
*   `syncedLabels` (map<string,string>, default: `{}`): Kubernetes labels synced to cloud resource tags (prefixed `aws.kropath.run/`).
*   `syncedAnnotations` (map<string,string>, default: `{}`): Kubernetes annotations synced to cloud resource tags (prefixed `aws.kropath.run/`).
*   `namingTemplate` (string, default: `"{namespace}-{name}"` for WorkGroups/DataCatalogs; `"{namespace}_{name}"` for PreparedStatements): Template for deriving cloud resource names.

### AthenaWorkGroup Core Fields

An `AthenaWorkGroup` instance represents the desired state of an Athena workgroup:

*   `configRef` (string, default: `"general-policy"`): Specifies which `AthenaConfig` profile to use for governance.
*   `nameOverride` (string, default: `""`): Bypasses the naming template to use a literal workgroup name.
*   `deletionPolicy` (string, default: `"retain"`): Determines behavior upon deletion. Options: `"retain"` (workgroup preserved) or `"delete"` (workgroup deleted).
*   `description` (string, default: `""`): Human-readable workgroup description.

**Query Configuration (cascade-resolved from `AthenaConfig`):**

*   `enforceWorkGroupConfiguration` (*bool, default: `nil`): Overrides `AthenaConfig` cascade for workgroup isolation enforcement.
*   `publishCloudWatchMetricsEnabled` (*bool, default: `nil`): Overrides `AthenaConfig` cascade for CloudWatch metrics.
*   `bytesScannedCutoffPerQuery` (*int64, default: `nil`): Overrides `AthenaConfig` cascade for query data usage limits.
*   `enableMinimumEncryptionConfiguration` (*bool, default: `nil`): Overrides `AthenaConfig` cascade for encryption requirements.
*   `requesterPaysEnabled` (*bool, default: `nil`): Overrides `AthenaConfig` cascade for requester-pays support.
*   `engineVersion` (string, default: `""`): Athena engine version (overrides `AthenaConfig` cascade).

**Result Configuration (Client-Owned S3):**

*   `resultOutputLocation` (string, default: `""`): S3 URI where query results are stored (e.g., `"s3://bucket/prefix/"`). Mutually exclusive with `managedResultsEnabled`.
*   `resultEncryptionOption` (string, default: `""`): Result encryption method (`"SSE_S3"`, `"SSE_KMS"`, `"CSE_KMS"`, or `""`).
*   `resultKmsKeyID` (string, default: `""`): KMS key ARN for result encryption. Mutually exclusive with `resultKmsKeyRef`.
*   `resultKmsKeyRef` (string, default: `""`): Local `KMSKey` CR name; the RGD resolves the key ARN via `resources.get()`. Mutually exclusive with `resultKmsKeyID`.
*   `resultAclOption` (string, default: `""`): S3 canned ACL for result objects (e.g., `"BUCKET_OWNER_FULL_CONTROL"`).
*   `resultExpectedBucketOwner` (string, default: `""`): Expected AWS account ID of the result bucket owner.

**Result Configuration (Athena-Managed S3):**

*   `managedResultsEnabled` (*bool, default: `nil`): When `true`, Athena stores query results in Athena-owned S3. Mutually exclusive with `resultOutputLocation`.
*   `managedResultsKmsKeyID` (string, default: `""`): KMS key ARN for managed result encryption. Mutually exclusive with `managedResultsKmsKeyRef`.
*   `managedResultsKmsKeyRef` (string, default: `""`): Local `KMSKey` CR name for managed result encryption. Mutually exclusive with `managedResultsKmsKeyID`.

**Spark Session Configuration:**

*   `executionRole` (string, default: `""`): IAM role ARN for Spark S3 and Glue access. Mutually exclusive with `executionRoleRef`.
*   `executionRoleRef` (string, default: `""`): Local `IAMRole` CR name; the RGD resolves the role ARN. Mutually exclusive with `executionRole`.
*   `customerContentKmsKeyID` (string, default: `""`): KMS key ARN for Spark session content encryption. Mutually exclusive with `customerContentKmsKeyRef`.
*   `customerContentKmsKeyRef` (string, default: `""`): Local `KMSKey` CR name for Spark content encryption. Mutually exclusive with `customerContentKmsKeyID`.

**Metadata and Tags:**

*   `tags` (map<string,string>, default: `{}`): Custom AWS tags merged with governance tiers.
*   `syncedLabels` (map<string,string>, default: `{}`): Kubernetes labels synced to cloud tags (prefixed `aws.kropath.run/`).
*   `syncedAnnotations` (map<string,string>, default: `{}`): Kubernetes annotations synced to cloud tags (prefixed `aws.kropath.run/`).

### AthenaDataCatalog Core Fields

An `AthenaDataCatalog` instance registers an external or AWS-managed metastore:

*   `configRef` (string, default: `"general-policy"`): Specifies which `AthenaConfig` profile to use.
*   `nameOverride` (string, default: `""`): Bypasses the naming template to use a literal catalog name.
*   `deletionPolicy` (string, default: `"retain"`): Determines behavior upon deletion.
*   `type` (string, required): Catalog type. Options: `"LAMBDA"`, `"GLUE"`, `"HIVE"`, `"FEDERATED"`.
*   `parameters` (map<string,string>, default: `{}`): Type-specific configuration parameters:
    *   **GLUE:** `catalog-id` (AWS account ID)
    *   **LAMBDA (single-function):** `function` (Lambda ARN)
    *   **LAMBDA (two-function):** `metadata-function` (ARN), `record-function` (ARN)
    *   **HIVE:** `metadata-function` (Lambda ARN)
    *   **FEDERATED:** `connection-arn` (Glue connection ARN) or `connection-type` + `connection-properties`
*   `description` (string, default: `""`): Human-readable catalog description.

**Metadata and Tags:**

*   `tags` (map<string,string>, default: `{}`): Custom AWS tags merged with governance tiers.
*   `syncedLabels` (map<string,string>, default: `{}`): Kubernetes labels synced to cloud tags.
*   `syncedAnnotations` (map<string,string>, default: `{}`): Kubernetes annotations synced to cloud tags.

**FEDERATED Catalogs:** Catalog names are limited to 41 characters due to derived CloudFormation stack and Lambda function naming constraints.

### AthenaPreparedStatement Core Fields

An `AthenaPreparedStatement` instance defines a reusable parameterized SQL statement:

*   `configRef` (string, default: `"general-policy"`): Specifies which `AthenaConfig` profile to use.
*   `nameOverride` (string, default: `""`): Bypasses the naming template to use a literal statement name.
*   `deletionPolicy` (string, default: `"retain"`): Determines behavior upon deletion.
*   `queryStatement` (string, required): The parameterized SQL query (e.g., `"SELECT * FROM orders WHERE id = ?"`).
*   `workGroup` (string, default: `""`): Literal target workgroup name. Mutually exclusive with `workGroupRef`.
*   `workGroupRef` (string, default: `""`): Local `AthenaWorkGroup` CR name; the RGD resolves the cloud workgroup name via `resources.get()`. Mutually exclusive with `workGroup`.
*   `description` (string, default: `""`): Human-readable statement description.

**Note:** `AthenaPreparedStatement` does not support cloud resource tags. `syncedLabels` and `syncedAnnotations` apply to the Kubernetes resource metadata only, not to cloud tags.

## Naming Conventions

Naming conventions follow `docs/design/naming-convention.md`. The `effectiveName` is the resolved cloud resource name derived from the naming template or `spec.nameOverride`.

### WorkGroup and DataCatalog Naming

*   **Default `namingTemplate`:** `{namespace}-{name}`
*   **Token vocabulary:** `{name}`, `{namespace}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.<key>}`
*   **`status.resourceName`:** The `effectiveName` after template resolution.
*   **`status.predictedArn`:** `arn:aws:athena:{region}:{account_id}:workgroup/{effectiveName}` for WorkGroups; `arn:aws:athena:{region}:{account_id}:datacatalog/{effectiveName}` for DataCatalogs.
*   **`status.namingStatus`:** `"valid"` or `"invalid-unresolved-tokens"` (e.g., missing tag references).

**Cloud Resource Name Immutability:** Both WorkGroup and DataCatalog names are immutable after creation. Changing `nameOverride` or the naming template after provisioning produces a new `effectiveName` that the AWS Athena API rejects.

### PreparedStatement Naming

*   **Default `namingTemplate`:** `{namespace}_{name}` — uses underscores instead of hyphens to comply with Athena's naming constraint `^[a-zA-Z_][a-zA-Z0-9_@:]{1,256}$`.
*   **Hyphen-to-Underscore Conversion:** Any hyphens in resolved `{namespace}` or `{name}` tokens are automatically converted to underscores at evaluation time.
*   **`status.resourceName`:** The `effectiveName` after template resolution and hyphen conversion.
*   **No ARN:** Prepared statements are not assigned an ARN by AWS. Resources are addressed by workgroup + statement name.

## Example AthenaWorkGroup Resource Instance

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AthenaWorkGroup
metadata:
  name: wg-analytics
  namespace: data-team
spec:
  configRef: analytics
  deletionPolicy: retain
  description: "Analytics team workgroup with CloudWatch metrics and 10 GB scan limit"
  enforceWorkGroupConfiguration: true
  publishCloudWatchMetricsEnabled: true
  bytesScannedCutoffPerQuery: 10737418240  # 10 GB
  resultOutputLocation: "s3://my-bucket/athena-results/"
  resultEncryptionOption: "SSE_KMS"
  resultKmsKeyRef: "my-kms-key"
  engineVersion: "Athena engine version 3"
  tags:
    environment: production
    team: analytics
  syncedLabels:
    data-sensitivity: high
```

## Example AthenaDataCatalog Resource Instance

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AthenaDataCatalog
metadata:
  name: glue-prod
  namespace: data-team
spec:
  configRef: general-policy
  type: GLUE
  parameters:
    catalog-id: "123456789012"
  description: "AWS Glue Data Catalog for production data"
  tags:
    environment: production
```

## Example AthenaPreparedStatement Resource Instance

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AthenaPreparedStatement
metadata:
  name: get-orders
  namespace: data-team
spec:
  configRef: general-policy
  workGroupRef: wg-analytics  # Resolves to the cloud workgroup name
  queryStatement: "SELECT * FROM orders WHERE id = ? AND status = ?"
  description: "Get orders by ID and status"
  deletionPolicy: retain
```

## Cross-Provider Notes

Athena query and data catalog management is specific to AWS. GCP BigQuery and Azure Synapse have different models:

*   **GCP BigQuery:** Uses datasets for query isolation (not workgroups). Query result storage is built-in and per-project. Parameterized queries exist at the API level, not as persistent resources.
*   **Azure Synapse:** Uses dedicated or serverless SQL pools for query execution. External data sources are managed via linked services (not named catalogs). Prepared statements are handled via SQL procedures, not as first-class resources.

The governance model (mandatory/defaults tiers for encryption, metrics, cost controls) will apply conceptually to GCP/Azure equivalents in future phases, but field mappings and APIs differ significantly.
