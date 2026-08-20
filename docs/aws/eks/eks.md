# AWS EKS Managed Kubernetes

The AWS Elastic Kubernetes Service (EKS) family within kropath provides abstractions for managing Kubernetes cluster lifecycles, compute resources, add-ons, and cluster access. It enables platform engineers to enforce organization-wide controls such as Kubernetes version policies, encryption-at-rest of secrets via KMS, authentication mode enforcement, control plane logging requirements, and endpoint access restrictions, while allowing application teams to provision and manage EKS clusters, managed node groups, Fargate profiles for serverless pods, cluster add-ons, access entries for RBAC, Pod Identity associations for workload IAM, and OIDC identity provider configurations.

## Prerequisites and Setup

EKS resources in kropath require the following baseline setup:

*   **IAM Integration:** EKS clusters require a cluster service role. Node groups require a node instance role. Fargate profiles require a Fargate pod execution role. These IAM roles must be created beforehand via the `IAMRole` resource.
*   **VPC and Networking:** EKS clusters require VPC subnets for control plane ENIs and must be associated with an EC2 security group configuration. Node groups require additional subnets for node placement. Fargate profiles require private subnets (no direct internet route).
*   **KMS (optional):** For envelope encryption of Kubernetes secrets, a KMS key must be available. Secrets encryption enforces encryption at rest for all Kubernetes secrets in the cluster.
*   **CloudWatch Logs (optional):** Control plane logs can be exported to CloudWatch Logs log groups for audit and operational logging. Specify log group names or pre-create them separately.

The EKS family consists of eight resource kinds:

*   **`EKSConfig`** — Governance configuration for EKS-wide settings (Kubernetes version, authentication mode, encryption key, logging, endpoint access, support policy, naming).
*   **`EKSCluster`** — Manages the EKS cluster control plane with VPC networking, security, encryption, logging, endpoint access, and support policy configuration.
*   **`EKSNodegroup`** — Manages EKS managed node groups with scaling configuration, instance types, capacity type (on-demand or spot), and compute setup.
*   **`EKSFargateProfile`** — Manages EKS Fargate profiles that define which pods run serverless on Fargate via namespace and label selectors.
*   **`EKSAddon`** — Manages EKS managed add-ons (CoreDNS, kube-proxy, VPC CNI, EBS CSI driver, etc.) with version pinning and conflict resolution.
*   **`EKSAccessEntry`** — Manages cluster access entries granting IAM principals access to the cluster with specified access policies and Kubernetes RBAC groups.
*   **`EKSPodIdentityAssociation`** — Manages Pod Identity associations binding Kubernetes service accounts to IAM roles for workload-based IAM permissions.
*   **`EKSIdentityProviderConfig`** — Manages OIDC identity provider configuration for external user authentication and SSO integration.

## Configuration

Kropath's EKS configuration is managed through governance layers and resource instances:

### EKSConfig: Governance Model

`EKSConfig` CRs define per-profile governance settings for all EKS resources. These profiles are referenced by EKS instances via `spec.configRef`. Each `EKSConfig` includes `mandatory` and `defaults` sections for governance fields:

*   **`mandatory`:** Fields set in this section enforce strict policies that cannot be overridden by resource instances. If a `mandatory` field is set, the instance's corresponding field is ignored or validated against the mandatory setting.
*   **`defaults`:** Fields set here provide baseline configurations that resource instances can override. They apply only when the instance's corresponding field is not explicitly set.

#### EKSConfig Core Fields

*   `version` (string, default: `""` = not enforced): Enforces the Kubernetes version for all clusters. Valid values are EKS-supported versions (e.g., `"1.31"`, `"1.30"`). Mandatory tier overrides instance selection; defaults tier provides a baseline version.
*   `authenticationMode` (string, default: `"API"` in defaults): Enforces the cluster authentication mode. Valid values: `"API"` (modern API-based auth), `"API_AND_CONFIG_MAP"` (hybrid), `"CONFIG_MAP"` (legacy aws-auth ConfigMap). Recommended value: `"API"`.
*   `encryptionKeyArn` (string, default: `""` = not enforced): KMS key ARN for secrets envelope encryption. When set in `mandatory`, all clusters must encrypt secrets with this key. When set in `defaults`, clusters can override with a different key or omit encryption.
*   `loggingTypes` ([]string, default: `[]` = not enforced): Enables control plane logs. Valid types: `api`, `audit`, `authenticator`, `controllerManager`, `scheduler`. Mandatory tier log types are always exported; instance cannot disable them.
*   `endpointPublicAccess` (boolean, default: `true` in defaults): Controls whether the public API endpoint is enabled. When set in `mandatory`, enforces the setting for all clusters. Defaults to `true`. **Boolean Sentinel Note:** Setting `endpointPublicAccess: true` in the `mandatory` tier enforces that the endpoint **must be public**; setting `endpointPublicAccess: false` enforces that it **must be private** (disabled). This differs from "not enforced" — if the field is not in `mandatory` at all, instances can choose freely.
*   `endpointPrivateAccess` (boolean, default: `true` in defaults): Controls whether the private API endpoint is enabled. When set in `mandatory`, enforces the setting. Defaults to `true`. **Boolean Sentinel Note:** Setting `endpointPrivateAccess: true` in the `mandatory` tier enforces that the endpoint **must be private**; setting `endpointPrivateAccess: false` enforces that it **must not be private** (disabled). If the field is not in `mandatory`, instances can choose freely.
*   `supportType` (string, default: `"STANDARD"` in defaults): Enforces the cluster support policy. Valid values: `"STANDARD"` (standard support, 14-month availability), `"EXTENDED"` (extended support, longer availability). Mandatory tier overrides instance selection.
*   `namingTemplate` (string, default: `"{namespace}-{name}"` in defaults): The pattern for generating EKS cluster names. Token vocabulary: `{name}`, `{namespace}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.<key>}`.
*   `tags` (map<string,string>): Custom AWS tags applied to all EKS resources, merged with instance tags.
*   `syncedLabels` (map<string,string>): Kubernetes labels mirrored as AWS tags and prefixed with `aws.kropath.run/`.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations mirrored to AWS resource tags and prefixed with `aws.kropath.run/`.

**Example EKSConfig Profiles:**

*   `general-policy`: A baseline profile with no enforced policies, defaulting to `API` authentication mode and `STANDARD` support.
*   `production`: A hardened profile with mandatory `API` authentication mode, mandatory KMS secrets encryption, mandatory `api` and `audit` logging, and `EXTENDED` support.
*   `pci`: A compliance profile with mandatory `EXTENDED` support and mandatory encryption for all secrets.

**General-Policy EKSConfig Example:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EKSConfig
metadata:
  name: general-policy
  namespace: kropath-config
spec:
  defaults:
    authenticationMode: API
    supportType: STANDARD
    endpointPublicAccess: true
    endpointPrivateAccess: true
  mandatory: {}
  tags:
    Environment: general
  syncedLabels:
    governance-profile: general-policy
```

**Production EKSConfig Example:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EKSConfig
metadata:
  name: production
  namespace: kropath-config
spec:
  defaults:
    version: "1.31"
    supportType: EXTENDED
  mandatory:
    authenticationMode: API
    encryptionKeyArn: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
    loggingTypes:
      - api
      - audit
    endpointPublicAccess: true
    endpointPrivateAccess: true
  tags:
    Environment: production
  syncedLabels:
    governance-profile: production
```

#### Ten-Tier Governance Cascade

Kropath employs a ten-tier governance cascade (ADR-010, ADR-015 §5.3) to resolve effective EKS configuration. The `kropath-controller` pre-merges all governance sources (from `KropathConfig` and `EKSConfig`) into `status.effectiveConfig` on the namespaced `EKSConfig` CR. EKS RGDs read this `status.effectiveConfig` to determine final settings.

**Governance cascade precedence (highest to lowest):**

| Tier | Source | Scope | Example |
|------|--------|-------|---------|
| 1 | Instance spec (resource YAML) | Single resource | `EKSCluster.spec.version: "1.31"` |
| 2 | EKSConfig.spec.mandatory | Profile-scoped | `general-policy` EKSConfig enforces `authenticationMode: API` |
| 3 | EKSConfig.spec.defaults | Profile-scoped | `general-policy` EKSConfig defaults `supportType: STANDARD` |
| 4 | KropathConfig.spec.eks.mandatory (global) | Organization-wide | KropathConfig enforces `encryptionKeyArn` for all profiles |
| 5 | KropathConfig.spec.eks.defaults (global) | Organization-wide | KropathConfig defaults `version: "1.30"` for all clusters |
| 6 | Namespace-level defaults (future) | Namespace-scoped | Reserved for namespace governance |
| 7 | Workspace-level settings (future) | Workspace-scoped | Reserved for workspace governance |
| 8 | Provider defaults (AWS) | Provider-wide | AWS EKS default support policy |
| 9 | Implicit fallback | — | Field not set anywhere — use provider default |
| 10 | Hard-coded final default | — | Kropath built-in fallback (e.g., `endpointPublicAccess: true`) |

**Example cascade resolution for `authenticationMode`:**
- If `EKSCluster.spec.accessConfig.authenticationMode` is set, use that (Tier 1).
- Else if the cluster's `EKSConfig` profile has `mandatory.authenticationMode`, enforce that (Tier 2).
- Else if the cluster's `EKSConfig` profile has `defaults.authenticationMode`, use that (Tier 3).
- Else if `KropathConfig.spec.eks.mandatory.authenticationMode` is set, enforce that (Tier 4).
- Else if `KropathConfig.spec.eks.defaults.authenticationMode` is set, use that (Tier 5).
- Else use the provider default (Tier 8) or Kropath built-in default (Tier 10).

**When to use `KropathConfig.eks` vs. `EKSConfig`:**

*   **`KropathConfig.eks`:** Used for blanket, organization-wide governance that applies across *all* EKS profiles. For example, setting `KropathConfig.mandatory.eks.version: "1.31"` forces all clusters to use Kubernetes 1.31 regardless of profile.
*   **`EKSConfig`:** Used for per-profile governance. For instance, a `production` `EKSConfig` profile might mandate `API` authentication mode and `EXTENDED` support only for that profile, allowing other profiles to use mixed modes and `STANDARD` support.

### EKSCluster: Cluster Configuration

An `EKSCluster` resource manages an AWS EKS cluster control plane with networking, security configuration, encryption, logging, and upgrade policies.

#### Core Fields

*   `configRef` (string, default: `"general-policy"`): Specifies which `EKSConfig` profile to use for governance.
*   `nameOverride` (string): Allows overriding the cluster name derived from the naming template.
*   `deletionPolicy` (string, default: `"retain"`): Determines behavior upon deletion. Options: `"retain"` (preserve AWS cluster) or `"delete"` (terminate AWS cluster).
*   `tags` (map<string,string>): Custom AWS tags applied to the cluster, merged with governance tags.
*   `syncedLabels` (map<string,string>): Kubernetes labels mirrored as AWS tags.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations mirrored to AWS tags.

#### Cluster Configuration

*   `version` (string): Kubernetes version (e.g., `"1.31"`). Subject to governance cascade: mandatory tier > instance > defaults tier.
*   `roleArn` (string, required): ARN of the IAM cluster service role (e.g., `arn:aws:iam::123456789012:role/eks-service-role`).
*   `deletionProtection` (boolean, default: `false`): When `true`, prevents accidental cluster deletion.

#### VPC and Networking

*   `resourcesVPCConfig` (object, required): VPC configuration for cluster control plane ENIs.
    *   `subnetIds` ([]string, required): Subnet IDs for cluster control plane ENIs. Should span multiple AZs for high availability.
    *   `securityGroupIds` ([]string): Additional security group IDs to associate with the cluster.
    *   `endpointPublicAccess` (boolean): Enable public API endpoint. Subject to governance cascade. Defaults to `true`.
    *   `endpointPrivateAccess` (boolean): Enable private API endpoint. Subject to governance cascade. Defaults to `true`.
    *   `publicAccessCidrs` ([]string): CIDR blocks permitted to access the public endpoint. Defaults to `["0.0.0.0/0"]`.

#### Security and Encryption

*   `accessConfig` (object): API-mode RBAC configuration.
    *   `authenticationMode` (string): Authentication mode — `"API"`, `"API_AND_CONFIG_MAP"`, or `"CONFIG_MAP"`. Subject to governance cascade. Defaults to `"API"`.
    *   `bootstrapClusterCreatorAdminPermissions` (boolean, default: `true`): When `true`, grants the cluster creator admin permissions in the cluster.
*   `encryptionConfig` (object): Envelope encryption configuration for Kubernetes secrets.
    *   `keyArn` (string): KMS key ARN for secrets encryption. Subject to governance cascade.
    *   `resources` ([]string, default: `["secrets"]`): Resource types to encrypt. Typically `["secrets"]`.

#### Logging and Monitoring

*   `logging` (object): Control plane logging configuration.
    *   `types` ([]string): Log types to enable. Valid values: `api`, `audit`, `authenticator`, `controllerManager`, `scheduler`. Subject to governance cascade.

#### Kubernetes Networking

*   `kubernetesNetworkConfig` (object): Kubernetes networking configuration.
    *   `serviceIpv4Cidr` (string): Kubernetes service CIDR (e.g., `"172.20.0.0/16"`). AWS auto-assigns if not specified.
    *   `ipFamily` (string, default: `"ipv4"`): IP address family — `"ipv4"` or `"ipv6"`.

#### Upgrade Policy

*   `upgradePolicy` (object): Cluster support and upgrade policy.
    *   `supportType` (string): Support policy — `"STANDARD"` or `"EXTENDED"`. Subject to governance cascade. Defaults to `"STANDARD"`.

**Example EKSCluster (general-policy profile):**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EKSCluster
metadata:
  name: my-cluster
  namespace: platform-team
spec:
  configRef: general-policy
  version: "1.31"
  roleArn: "arn:aws:iam::123456789012:role/eks-service-role"
  deletionPolicy: retain
  resourcesVPCConfig:
    subnetIds:
      - subnet-0123456789abcdef0
      - subnet-abcdef0123456789
    securityGroupIds:
      - sg-0123456789abcdef0
    endpointPublicAccess: true
    endpointPrivateAccess: true
  accessConfig:
    authenticationMode: API
    bootstrapClusterCreatorAdminPermissions: true
  encryptionConfig:
    keyArn: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
  logging:
    types:
      - api
      - audit
  kubernetesNetworkConfig:
    serviceIpv4Cidr: "172.20.0.0/16"
  tags:
    Environment: production
    Team: platform
```

### EKSNodegroup: Node Group Configuration

An `EKSNodegroup` resource manages an EKS managed node group — a set of EC2 instances in an Auto Scaling group that register as Kubernetes nodes.

#### Core Fields

*   `configRef` (string, default: `"general-policy"`): Specifies which `EKSConfig` profile to use.
*   `nameOverride` (string): Allows overriding the node group name.
*   `deletionPolicy` (string, default: `"retain"`): Options: `"retain"` or `"delete"`.
*   `clusterName` (string, required): Name of the EKS cluster.
*   `nodeRoleArn` (string, required): ARN of the IAM role for node instances.
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata handling.

#### Compute Configuration

*   `subnets` ([]string, required): Subnet IDs for node instance placement.
*   `instanceTypes` ([]string): EC2 instance types (e.g., `["m5.large", "m5.xlarge"]`). Omit to use AWS defaults.
*   `amiType` (string): AMI type for the node group. Valid values: `AL2_x86_64`, `AL2_ARM_64`, `BOTTLEROCKET_x86_64`, `BOTTLEROCKET_ARM_64`, `AL2023_x86_64_STANDARD`, `AL2023_ARM_64_STANDARD`, `WINDOWS_CORE_2022_x86_64`, `WINDOWS_CORE_2025_x86_64`.
*   `capacityType` (string, default: `"ON_DEMAND"`): Capacity type — `"ON_DEMAND"` (always available) or `"SPOT"` (cost-optimized, interruptible).
*   `diskSize` (integer): Root disk size in GiB. Omit to use AMI default.
*   `version` (string): Kubernetes version. Omit to inherit cluster version.

#### Scaling Configuration

*   `scalingConfig` (object): Auto Scaling configuration.
    *   `minSize` (integer, default: `1`): Minimum number of nodes.
    *   `maxSize` (integer, default: `2`): Maximum number of nodes.
    *   `desiredSize` (integer, default: `1`): Desired number of nodes.

#### Node Labels and Taints

*   `labels` (map<string,string>): Kubernetes labels applied to all nodes in this group.
*   `taints` ([]object): Kubernetes taints applied to all nodes. Each taint includes:
    *   `key` (string, required): Taint key.
    *   `value` (string): Taint value.
    *   `effect` (string, required): Taint effect — `NoSchedule`, `NoExecute`, or `PreferNoSchedule`.

#### Launch Template (Advanced)

*   `launchTemplate` (object): Optional EC2 launch template for advanced customization. Mutually exclusive with `amiType`, `diskSize`.
    *   `id` (string): Launch template ID.
    *   `name` (string): Launch template name.
    *   `version` (string): Launch template version.

#### Rolling Update Configuration

*   `updateConfig` (object): Rolling update strategy.
    *   `maxUnavailable` (integer): Maximum number of nodes unavailable during update.
    *   `maxUnavailablePercentage` (integer): Percentage alternative to `maxUnavailable`.

#### Remote Access (SSH)

*   `remoteAccess` (object): SSH access configuration.
    *   `ec2SshKey` (string): EC2 key pair name for SSH access.
    *   `sourceSecurityGroups` ([]string): Security group IDs permitted for SSH access.

**Example EKSNodegroup:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EKSNodegroup
metadata:
  name: general-nodes
  namespace: platform-team
spec:
  configRef: general-policy
  clusterName: my-cluster
  nodeRoleArn: "arn:aws:iam::123456789012:role/eks-node-role"
  subnets:
    - subnet-0123456789abcdef0
    - subnet-abcdef0123456789
  instanceTypes:
    - m5.large
    - m5.xlarge
  amiType: AL2_x86_64
  capacityType: ON_DEMAND
  scalingConfig:
    minSize: 2
    maxSize: 10
    desiredSize: 3
  labels:
    workload-type: general
  tags:
    NodeGroup: general
```

### EKSFargateProfile: Serverless Pod Configuration

An `EKSFargateProfile` resource manages an EKS Fargate profile that defines which pods run serverless on AWS Fargate based on namespace and label selectors.

#### Core Fields

*   `configRef` (string, default: `"general-policy"`): Specifies which `EKSConfig` profile to use.
*   `nameOverride` (string): Allows overriding the Fargate profile name.
*   `deletionPolicy` (string, default: `"retain"`): Options: `"retain"` or `"delete"`.
*   `clusterName` (string, required): Name of the EKS cluster.
*   `podExecutionRoleArn` (string, required): ARN of the IAM role for Fargate pod execution.
*   `subnets` ([]string, required): Private subnet IDs for Fargate pods. Must be private subnets.
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata handling.

#### Pod Selectors

*   `selectors` ([]object, required): Pod matching selectors. Pods matching any selector are scheduled on Fargate.
    *   `namespace` (string, required): Kubernetes namespace to match.
    *   `labels` (map<string,string>): Label key-value pairs; pod must match all labels.

**Example EKSFargateProfile:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EKSFargateProfile
metadata:
  name: default-fargate
  namespace: platform-team
spec:
  configRef: general-policy
  clusterName: my-cluster
  podExecutionRoleArn: "arn:aws:iam::123456789012:role/eks-fargate-pod-execution-role"
  subnets:
    - subnet-private-1
    - subnet-private-2
  selectors:
    - namespace: default
    - namespace: monitoring
      labels:
        workload-type: monitoring
```

### EKSAddon: Managed Add-On Configuration

An `EKSAddon` resource manages EKS managed Kubernetes components (CoreDNS, kube-proxy, VPC CNI, EBS CSI driver, etc.) with version pinning and conflict resolution.

#### Core Fields

*   `configRef` (string, default: `"general-policy"`): Specifies which `EKSConfig` profile to use.
*   `deletionPolicy` (string, default: `"retain"`): Options: `"retain"` or `"delete"`.
*   `clusterName` (string, required): Name of the EKS cluster.
*   `addonName` (string, required): Name of the add-on (e.g., `"coredns"`, `"kube-proxy"`, `"vpc-cni"`, `"aws-ebs-csi-driver"`, `"aws-efs-csi-driver"`).
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata handling.

#### Add-On Configuration

*   `addonVersion` (string): Specific add-on version (e.g., `"v1.29.1-eksbuild.2"`). Omit to use the latest compatible version.
*   `resolveConflicts` (string, default: `"OVERWRITE"`): Conflict resolution strategy. Options:
    *   `"NONE"`: Fail if add-on conflicts with existing resources.
    *   `"OVERWRITE"`: Overwrite existing add-on resources.
    *   `"PRESERVE"`: Keep existing resources (use carefully).
*   `configurationValues` (string): JSON configuration values specific to the add-on. See AWS documentation for each add-on's schema.

#### IRSA (IAM Roles for Service Accounts)

*   `serviceAccountRoleArn` (string): IAM role ARN for the add-on's Kubernetes service account (IRSA). Required for add-ons that need AWS API access (e.g., `vpc-cni`, `ebs-csi-driver`).

**Naming Note:** EKS add-ons are identified by the combination of `clusterName` + `addonName`. The `addonName` is canonical (e.g., `"coredns"`), not user-chosen. Naming convention does not apply to add-ons.

**Example EKSAddon (VPC CNI):**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EKSAddon
metadata:
  name: vpc-cni
  namespace: platform-team
spec:
  configRef: general-policy
  clusterName: my-cluster
  addonName: vpc-cni
  addonVersion: "v1.18.0-eksbuild.1"
  resolveConflicts: OVERWRITE
  serviceAccountRoleArn: "arn:aws:iam::123456789012:role/vpc-cni-irsa"
  tags:
    ManagedBy: kropath
```

### EKSAccessEntry: Cluster Access Configuration

An `EKSAccessEntry` resource manages cluster access entries granting IAM principals (roles or users) access to the cluster with specified access policies and Kubernetes RBAC groups.

#### Core Fields

*   `configRef` (string, default: `"general-policy"`): Specifies which `EKSConfig` profile to use.
*   `deletionPolicy` (string, default: `"retain"`): Options: `"retain"` or `"delete"`.
*   `clusterName` (string, required): Name of the EKS cluster.
*   `principalArn` (string, required): ARN of the IAM principal (role or user) to grant access (e.g., `arn:aws:iam::123456789012:role/dev-team-role`).
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata handling.

#### Access Configuration

*   `type` (string, default: `"STANDARD"`): Entry type. Valid values: `"STANDARD"`, `"FARGATE_LINUX"`, `"EC2_LINUX"`, `"EC2_WINDOWS"`.
*   `accessPolicies` ([]object): Access policies to associate. Each policy includes:
    *   `policyArn` (string, required): EKS access policy ARN (e.g., `arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy`).
    *   `accessScope` (object, required): Scope of the policy.
        *   `type` (string, required): Scope type — `"cluster"` (full cluster access) or `"namespace"` (namespace-scoped).
        *   `namespaces` ([]string): Namespaces to grant access to (only when `type=namespace`).
*   `kubernetesGroups` ([]string): Kubernetes RBAC groups to bind the principal to (e.g., `["system:masters"]`).
*   `username` (string): Kubernetes username override. Defaults to the IAM principal ARN.

**Naming Note:** Access entries have no provider `name` field. They are identified by `clusterName` + `principalArn`. Naming convention does not apply to access entries.

**Example EKSAccessEntry:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EKSAccessEntry
metadata:
  name: dev-team-access
  namespace: platform-team
spec:
  configRef: general-policy
  clusterName: my-cluster
  principalArn: "arn:aws:iam::123456789012:role/dev-team-role"
  type: STANDARD
  accessPolicies:
    - policyArn: "arn:aws:eks::aws:cluster-access-policy/AmazonEKSDeveloperPolicy"
      accessScope:
        type: namespace
        namespaces:
          - dev
          - staging
  kubernetesGroups:
    - developers
```

### EKSPodIdentityAssociation: Pod-to-IAM Binding

An `EKSPodIdentityAssociation` resource manages Pod Identity associations binding Kubernetes service accounts to IAM roles, enabling pods using those service accounts to assume the roles for AWS API access.

#### Core Fields

*   `configRef` (string, default: `"general-policy"`): Specifies which `EKSConfig` profile to use.
*   `deletionPolicy` (string, default: `"retain"`): Options: `"retain"` or `"delete"`.
*   `clusterName` (string, required): Name of the EKS cluster.
*   `namespace` (string, required): Kubernetes namespace containing the service account.
*   `serviceAccount` (string, required): Kubernetes service account name.
*   `roleArn` (string, required): IAM role ARN to associate with the service account.
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata handling.

#### Optional Configuration

*   `targetRoleArn` (string): Target IAM role ARN for role chaining via `sts:AssumeRole`. When specified, the workload role assumes this target role.
*   `disableSessionTags` (boolean, default: `false`): When `true`, disables automatic session tags from Pod Identity.
*   `policy` (string): Inline IAM policy JSON applied to the session. Optional additional permissions for the association.

**Naming Note:** Pod Identity associations have no provider `name` field. They are identified by `clusterName` + `namespace` + `serviceAccount`. Naming convention does not apply to Pod Identity associations.

**Example EKSPodIdentityAssociation:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EKSPodIdentityAssociation
metadata:
  name: app-workload-identity
  namespace: apps
spec:
  configRef: general-policy
  clusterName: my-cluster
  namespace: apps
  serviceAccount: app-sa
  roleArn: "arn:aws:iam::123456789012:role/app-workload-role"
  tags:
    Application: my-app
```

### EKSIdentityProviderConfig: OIDC IdP Configuration

An `EKSIdentityProviderConfig` resource manages OIDC identity provider configuration for external user authentication and SSO integration with the EKS cluster.

#### Core Fields

*   `configRef` (string, default: `"general-policy"`): Specifies which `EKSConfig` profile to use.
*   `deletionPolicy` (string, default: `"retain"`): Options: `"retain"` or `"delete"`.
*   `clusterName` (string, required): Name of the EKS cluster.
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata handling.

#### OIDC Configuration

*   `oidc` (object, required): OIDC provider configuration.
    *   `clientId` (string, required): OIDC client ID (audience) from your identity provider.
    *   `issuerUrl` (string, required): HTTPS issuer URL for the OIDC provider (e.g., `https://auth.example.com`).
    *   `identityProviderConfigName` (string): Human-readable name for this OIDC configuration. Defaults to auto-generated name.
    *   `groupsClaim` (string): JWT claim name containing group membership (e.g., `"groups"`).
    *   `groupsPrefix` (string): Prefix prepended to group claims (e.g., `"oidc:"`).
    *   `usernameClaim` (string): JWT claim used as Kubernetes username (defaults to `"sub"`).
    *   `usernamePrefix` (string): Prefix prepended to username claims (e.g., `"oidc:"`).
    *   `requiredClaims` (map<string,string>): Required JWT claims and their values (e.g., `{"aud": "my-app"}`).

**Naming Note:** Identity provider configs have no top-level `name` field. They are identified by `clusterName` + `oidc.identityProviderConfigName`. Naming convention does not apply to identity provider configs.

**Limit:** Only one OIDC identity provider can be associated per cluster.

**Example EKSIdentityProviderConfig:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EKSIdentityProviderConfig
metadata:
  name: corporate-sso
  namespace: platform-team
spec:
  configRef: general-policy
  clusterName: my-cluster
  oidc:
    issuerUrl: "https://auth.company.com"
    clientId: "eks-cluster-client"
    identityProviderConfigName: corporate-oidc
    usernameClaim: email
    usernamePrefix: "oidc:"
    groupsClaim: groups
    groupsPrefix: "oidc:"
    requiredClaims:
      aud: "eks-cluster-client"
```

## Naming Conventions

EKS cluster names follow the default naming template `{namespace}-{name}`:

*   **EKSCluster:** Cluster names are region-scoped within an account.
*   **EKSNodegroup:** Node group names follow the naming template and are cluster-scoped.
*   **EKSFargateProfile:** Fargate profile names follow the naming template and are cluster-scoped.

AWS EKS naming constraints:

*   Cluster names: 1–100 characters, alphanumeric, hyphens, and underscores. Must start with alphanumeric.
*   Node group names: 1–63 characters, alphanumeric, hyphens, and underscores.
*   Fargate profile names: 1–63 characters, alphanumeric, hyphens, and underscores.

**Naming Exemptions:**

*   **EKSAddon:** Add-ons are identified by canonical add-on names (e.g., `coredns`), not user-chosen names. Naming convention does not apply.
*   **EKSAccessEntry:** Access entries are identified by `clusterName` + `principalArn`. Naming convention does not apply.
*   **EKSPodIdentityAssociation:** Pod Identity associations are identified by `clusterName` + `namespace` + `serviceAccount`. Naming convention does not apply.
*   **EKSIdentityProviderConfig:** Identity provider configs are identified by `clusterName` + `oidc.identityProviderConfigName`. Naming convention does not apply.

The effective cluster name is resolved from the naming template or `spec.nameOverride` and exposed as `status.resourceName`. The `status.predictedArn` is built from the effective name for `EKSCluster` (other resources have non-derivable ARNs due to random suffixes added by AWS).
