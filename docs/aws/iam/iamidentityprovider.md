# IAMIdentityProvider — OIDC and SAML Federation

The `IAMIdentityProvider` resource registers OIDC and SAML identity providers in your AWS account, enabling external workload authentication and federation.

## Overview

An identity provider is a trusted external system that issues credentials. Common use cases:

- **EKS IRSA** — Kubernetes service accounts assuming AWS roles via OIDC
- **GitHub Actions** — CI/CD workflows accessing AWS resources
- **GitLab** — Self-hosted or cloud deployments  
- **Corporate IdP** — SAML federation with your organization's identity provider

## OIDC Providers

OIDC (OpenID Connect) providers issue tokens that Kubernetes service accounts can use to assume AWS roles.

### Creating an OIDC Provider

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMIdentityProvider
metadata:
  name: eks-oidc
  namespace: kro-system
spec:
  configRef: general-policy
  type: oidc
  oidc:
    url: "https://oidc.eks.us-east-1.amazonaws.com/id/1234567890ABCDEF"
    thumbprints:
      - "9e99a48a9960b14926bb7f3b02e22da2b0ab7280"
    audiences:
      - "sts.amazonaws.com"
```

Fields:
- **url** — HTTPS URL of the OIDC issuer (no trailing slash)
- **thumbprints** — SHA-1 thumbprints of the certificate signing the tokens (1-5 values). AWS can auto-fetch these for most trusted CAs; provide explicitly for custom CAs
- **audiences** — Intended token audience (default: `sts.amazonaws.com` for role assumption)

### Using OIDC with EKS

After creating the provider, create an IAM role that trusts it:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMRole
metadata:
  name: app-role
  namespace: default
spec:
  configRef: general-policy
  type: eks-irsa
  oidcProviderArn: "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/1234567890ABCDEF"
  serviceAccountNamespace: "app-namespace"
  serviceAccountName: "app-sa"
  policies:
    - arn: "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
```

The role's trust policy now permits the Kubernetes service account `app-namespace/app-sa` to assume it.

Deploy the service account and workload:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: app-namespace
---
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  namespace: app-namespace
spec:
  serviceAccountName: app-sa
  containers:
  - name: app
    image: my-app:latest
```

The pod automatically receives AWS credentials via the IAM role.

### GitHub Actions Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMIdentityProvider
metadata:
  name: github-oidc
  namespace: kro-system
spec:
  configRef: general-policy
  type: oidc
  oidc:
    url: "https://token.actions.githubusercontent.com"
    thumbprints:
      - "6938fd4d98bab03faadb97b34396831e3780aea1"
---
apiVersion: aws.kropath.run/v1alpha1
kind: IAMRole
metadata:
  name: github-ci-role
  namespace: kro-system
spec:
  configRef: general-policy
  type: generic
  trustPolicyJSON: |
    {
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {
          "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
        },
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {
          "StringEquals": {
            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
          },
          "StringLike": {
            "token.actions.githubusercontent.com:sub": "repo:my-org/my-repo:*"
          }
        }
      }]
    }
```

## SAML Providers

**SAML providers are not supported by ACK controller yet. This results in a ConfigMap generated with error message.**

SAML (Security Assertion Markup Language) enables federation with corporate identity providers.

### Creating a SAML Provider

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMIdentityProvider
metadata:
  name: corporate-idp
  namespace: kro-system
spec:
  configRef: general-policy
  type: saml
  saml:
    metadataDocument: |
      <?xml version="1.0" encoding="UTF-8"?>
      <EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata" ...>
        <!-- Full SAML metadata from your IdP -->
      </EntityDescriptor>
```

Obtain the SAML metadata XML from your identity provider (Okta, Azure AD, OneLogin, etc.) and paste it into the `metadataDocument` field.

## Account-Scoped vs Namespace-Scoped

Identity providers are **account-scoped** — a single provider ARN is shared across all clusters and roles in your AWS account that reference it.

Plan accordingly:
- Create providers in a central namespace (e.g., `kro-system`)
- Document which roles and clusters use each provider
- Coordinate deletion with all dependent workloads

## Monitoring

Check provider status:

```bash
kubectl describe iamidentityprovider eks-oidc -n kro-system
```

Look for `status.providerArn` — this is the ARN other resources reference.

## Deletion and Retention

By default, providers use `deletionPolicy: retain` to prevent accidental deletion of shared account infrastructure. When you delete the provider, the underlying AWS provider remains.

To delete the underlying provider:

```yaml
spec:
  deletionPolicy: delete
```

Caution: Deleting a provider breaks all roles that reference it. Update those roles' trust policies first.
