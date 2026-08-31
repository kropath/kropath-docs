# Cognito — User Authentication and Management

AWS Cognito enables you to add user authentication, authorization, and multi-factor authentication (MFA) to your applications at scale. kropath's Cognito family provides a golden path for deploying and governing user pools across your organization.

## Resources

### CognitoConfig — Governance Configuration

The `CognitoConfig` resource defines governance profiles that enforce security and compliance controls across all user pools in your organization.

- **Mandatory tier**: Controls that cannot be overridden (e.g., MFA enforcement, deletion protection, password policies)
- **Defaults tier**: Sensible baseline values developers can override

[Learn more about CognitoConfig →](cognitoconfig.md)

### CognitoUserPool — User Pool Instance

The `CognitoUserPool` resource represents a single user pool. Developers select a governance profile and configure pool-specific settings (custom attributes, Lambda triggers, email/SMS configuration, etc.).

[Learn more about CognitoUserPool →](cognitouserpool.md)

## Common Use Cases

### Development Environment

Use the `general-policy` profile with permissive defaults:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CognitoUserPool
metadata:
  name: dev-pool
  namespace: dev-team
spec:
  configRef: general-policy
```

### Production Environment

Use the `high-security` profile with mandatory MFA and deletion protection:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CognitoUserPool
metadata:
  name: prod-pool
  namespace: prod-team
spec:
  configRef: high-security
  tags:
    environment: production
```

### PCI-DSS Compliance

Use the `pci` profile for payment processing systems:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CognitoUserPool
metadata:
  name: payment-pool
  namespace: payments
spec:
  configRef: pci
```

## Getting Started

1. **Create governance profiles**: Platform teams deploy `CognitoConfig` CRs (e.g., `general-policy`, `high-security`, `pci`) to `kro-system` namespace.

2. **Create a pool**: Developers apply a `CognitoUserPool` CR that selects a profile and specifies pool-specific settings.

3. **Monitor compliance**: Inspect `status.effectiveConfig` on the selected `CognitoConfig` CR to audit governance cascade and active policies.

## Deferred Features

The following features are planned for future releases:

- **User Pool Clients** (G-1) — OAuth 2.0 / OIDC client applications
- **User Pool Domains** (G-2) — Custom domain for hosted UI
- **Resource Servers** (G-3) — API authorization for scope-based access
