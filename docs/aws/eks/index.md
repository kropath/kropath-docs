# AWS EKS

Elastic Kubernetes Service (EKS) provides managed Kubernetes cluster control plane, compute resources via node groups and Fargate, add-on lifecycle management, and IAM-based cluster access for container orchestration across AWS.

## Resources

*   [EKS Overview & Configuration](eks.md) — Comprehensive guide to EKS governance, cluster configuration, compute options, and resource types.

## Resource Types

*   **EKSConfig** — Governance configuration for EKS-wide settings (version, authentication, encryption, logging, endpoint access, support policy, naming).
*   **EKSCluster** — Manages EKS cluster control plane with networking, security, logging, and encryption.
*   **EKSNodegroup** — Manages EKS managed node groups with scaling, instance types, and compute configuration.
*   **EKSFargateProfile** — Manages EKS Fargate profiles for serverless pod scheduling via namespace and label selectors.
*   **EKSAddon** — Manages EKS add-ons (CoreDNS, kube-proxy, VPC CNI, EBS CSI driver) with version pinning and conflict resolution.
*   **EKSAccessEntry** — Manages cluster access entries for IAM principals with access policies and RBAC groups.
*   **EKSPodIdentityAssociation** — Manages Pod Identity associations binding service accounts to IAM roles.
*   **EKSIdentityProviderConfig** — Manages OIDC identity provider configuration for external IdP federation.
