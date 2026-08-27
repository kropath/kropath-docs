# Certificate Manager Family

The Certificate Manager family provides abstractions for TLS/SSL certificate lifecycle management and private certificate authority (CA) operations in AWS.

## Resources in This Family

| Resource | Purpose | Governance |
|---|---|---|
| [`ACMConfig`](acmconfig.md) | Governance configuration for certificate policies | Mandatory/defaults tiers |
| [`ACMCertificate`](acmcertificate.md) | Public, private, or imported TLS certificates | Configurable via ACMConfig |
| [`ACMPrivateCA`](acmprivateca.md) | Private certificate authorities (root or subordinate) | Configurable via ACMConfig |
| [`ACMPrivateCertificate`](acmprivatecertificate.md) | End-entity certificates issued by a private CA | Configurable via ACMConfig |
| [`ACMEEndpoint`](acmeendpoint.md) | ACME protocol endpoints for automated certificate issuance | Configurable via ACMConfig |
| [`ACMEDomainValidation`](acmedomainvalidation.md) | Domain prevalidation for ACME endpoints | Configurable via ACMConfig |

## Common Patterns

### Public Certificate Request

Request a public TLS certificate with automatic DNS validation:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMCertificate
metadata:
  name: example-cert
  namespace: app-team
spec:
  configRef: general-policy
  domainName: "www.example.com"
  subjectAlternativeNames:
    - "example.com"
    - "*.example.com"
  deletionPolicy: retain
```

### Private CA and Certificate

Create a private CA and issue a certificate from it:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMPrivateCA
metadata:
  name: internal-ca
  namespace: security
spec:
  configRef: general-policy
  type: ROOT
  keyAlgorithm: EC_prime256v1
  signingAlgorithm: SHA256WITHECDSA
  subject:
    commonName: "internal.example.com"
    country: "US"
    organization: "ACME Corp"
  deletionPolicy: retain
---
apiVersion: aws.kropath.run/v1alpha1
kind: ACMCertificate
metadata:
  name: service-cert
  namespace: app-team
spec:
  configRef: general-policy
  domainName: "service.internal.example.com"
  certificateAuthorityRef: internal-ca
  deletionPolicy: retain
```

## Governance

All resources in the Certificate Manager family support governance through `ACMConfig`. Platform teams can enforce:

- **Key algorithms** — mandatory or default (RSA_2048, EC_prime256v1, EC_secp384r1)
- **Certificate transparency logging** — required for public certificates
- **CA usage mode** — GENERAL_PURPOSE or SHORT_LIVED_CERTIFICATE for private CAs
- **FIPS compliance** — key storage security standard for private CAs
- **Tags and labels** — applied to all resources

Example `ACMConfig`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMConfig
metadata:
  name: pci
  namespace: kro-system
spec:
  mandatory:
    keyAlgorithm: "EC_prime256v1"
    certificateTransparencyLogging: "ENABLED"
  defaults:
    keyAlgorithm: "RSA_2048"
    certificateTransparencyLogging: "ENABLED"
```

## Cross-Family Integration

### Referenced By

- **ELB (load balancing)** — ALB/NLB TLS termination via `ELBListener.spec.certificateARN`
- **CloudFront (CDN)** — CloudFront viewer certificate via `CloudFrontDistribution.spec.viewerCertificateARN`
- **API Gateway** — custom domain TLS via `APIGatewayDomainName.spec.certificateARN`

### References

- `ACMCertificate` references `ACMPrivateCA` via `spec.certificateAuthorityRef` (private certificate workflow)
- `ACMPrivateCertificate` references `ACMPrivateCA` via `spec.certificateAuthorityRef` (certificate issuance)
- `ACMEDomainValidation` references `ACMEEndpoint` via `spec.acmeEndpointRef` (domain prevalidation)

## Key Behaviors

### Immutable Resource Names

All resources in the Certificate Manager family are named by AWS-assigned ARNs. There is no `spec.nameOverride` or naming template — resource names are determined by the provider and immutable.

### Two-Step CA Activation

Creating an `ACMPrivateCA` without `spec.activationCertificateSecret` creates the CA in `PENDING_CERTIFICATE` state. The CSR is exposed via `status.certificateSigningRequest`. After the CSR is signed (self-signed for root CAs, or signed by another CA for subordinate CAs), store the certificate in a Kubernetes Secret and set `spec.activationCertificateSecret` to complete activation.

### Workflow Detection in ACMCertificate

A single `ACMCertificate` resource handles three workflows:

- **Public certificate** — Set `spec.domainName`; ACM performs DNS or email validation
- **Private certificate** — Set `spec.certificateAuthorityRef` or `spec.certificateAuthorityARN`; ACM issues via the private CA
- **Imported certificate** — Set `spec.importCertificateSecret`, `spec.importPrivateKeySecret`, and optionally `spec.importCertificateChainSecret`

## Deletion Policies

All resources support:

- `retain` (default) — Deleting the Kubernetes resource keeps the AWS resource intact
- `delete` — Deleting the Kubernetes resource also deletes the AWS resource

Use `retain` for certificates in production; use `delete` for temporary or test certificates.

## Troubleshooting

- **Certificate not validating:** For public certificates, ensure DNS CNAME records are created in Route 53 (or your DNS provider) for domain validation.
- **Private CA stuck in PENDING_CERTIFICATE:** Ensure `activationCertificateSecret` is set with the signed CA certificate.
- **CSR signing fails:** For subordinate CAs, ensure the signing CA's certificate chain is provided in `activationCertificateChainSecret`.
- **ACME domain validation fails:** Check `status.prevalidationDetails` for the exact error; ensure the hosted zone ID is correct for the domain.

## Further Reading

- [ADR-015: Consolidated Platform Decisions](https://github.com/kropath/kropath-core/blob/main/docs/adrs/015-consolidated-platform-decisions.md) — governance cascade, naming, and field wiring rules
- [Certificate Manager Family Spec](https://github.com/kropath/kropath-core/blob/main/docs/families/aws/certificate-manager.md) — detailed design reference
