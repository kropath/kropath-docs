# AWS Secrets Manager

AWS Secrets Manager resources in kropath enable you to create, manage, and rotate secrets with encryption, cross-region replication, and governance controls.

## Resources

- **[SecretsManagerConfig](./secretsmanagerconfig.md)** — Governance profiles that control encryption, replication, and naming across your organization
- **[SecretsManagerSecret](./secretsmanagersecret.md)** — The resource for creating and managing individual secrets in AWS Secrets Manager

## Quick Start

1. Create a `SecretsManagerConfig` profile to define governance rules (e.g., mandatory encryption, DR replication)
2. Create a `SecretsManagerSecret` instance that selects the config profile via `spec.configRef`
3. Optionally provide the secret value via `spec.secretRef` pointing to a Kubernetes Secret
4. kropath reconciles the secret in AWS Secrets Manager with your specified encryption and replication configuration

## Learn More

- See [SecretsManagerConfig](./secretsmanagerconfig.md) for governance setup and profile examples
- See [SecretsManagerSecret](./secretsmanagersecret.md) for creating and managing secrets
