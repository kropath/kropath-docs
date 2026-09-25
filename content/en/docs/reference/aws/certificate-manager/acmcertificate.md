---
title: ACMCertificate — TLS Certificate Provisioning
description: "The `ACMCertificate` resource represents a single AWS ACM certificate."
doc_type: reference
---
# ACMCertificate — TLS Certificate Provisioning

The `ACMCertificate` resource represents a single AWS ACM certificate. A single `ACMCertificate` resource supports three workflows through mutually exclusive field groups: public certificate request (with DNS or email validation), private certificate issuance (via a private CA), or imported certificate.

## Workflows

Choose one workflow by setting the appropriate fields:

| Workflow | Use | Set these fields |
|---|---|---|
| **Public Certificate** | Request a public TLS certificate with automatic validation | `domainName`, `subjectAlternativeNames`, optionally `domainValidationOptions` |
| **Private Certificate** | Issue a certificate from a private CA | `domainName`, `certificateAuthorityRef` or `certificateAuthorityARN` |
| **Imported Certificate** | Use an externally-obtained certificate | `importCertificateSecret`, `importPrivateKeySecret`, optionally `importCertificateChainSecret` |

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `ACMConfig` governance profile to apply |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` (safe) or `"delete"` |

### Public Certificate Workflow

| Field | Type | Default | Purpose |
|---|---|---|---|
| `domainName` | string | required | Primary FQDN to secure (e.g., `"www.example.com"` or `"*.example.com"`). Max 64 octets. Immutable after creation. |
| `subjectAlternativeNames` | array | `[]` | Additional FQDNs for the SAN extension. Max 100 total domain names. Immutable. |
| `keyAlgorithm` | string | governed by ACMConfig | Key algorithm (RSA_2048, EC_prime256v1, EC_secp384r1). Defaults from ACMConfig if not set. Immutable. |
| `certificateTransparencyLogging` | string | governed by ACMConfig | CT logging preference (ENABLED or DISABLED). Only applies to public certificates. Immutable. |
| `domainValidationOptions` | array | `[]` | Per-domain email validation overrides. Each entry: `{domainName, validationDomain}`. Immutable. |

### Private Certificate Workflow

| Field | Type | Default | Purpose |
|---|---|---|---|
| `certificateAuthorityARN` | string | `""` | ARN of the private CA issuing the certificate. Immutable. Mutually exclusive with `certificateAuthorityRef`. |
| `certificateAuthorityRef` | string | `""` | Local `ACMPrivateCA` CR name. RGD reads `status.certificateAuthorityARN`. Immutable. Mutually exclusive with `certificateAuthorityARN`. |
| `domainName` | string | required | Primary FQDN or internal identity. Immutable. |
| `keyAlgorithm` | string | governed by ACMConfig | Key algorithm (RSA_2048, EC_prime256v1, EC_secp384r1). Immutable. |

### Imported Certificate Workflow

| Field | Type | Default | Purpose |
|---|---|---|---|
| `importCertificateSecret` | string | `""` | Name of the Kubernetes Secret containing the PEM-encoded certificate body (key: `"tls.crt"`). Immutable. |
| `importPrivateKeySecret` | string | `""` | Name of the Kubernetes Secret containing the PEM-encoded private key (key: `"tls.key"`). Immutable. |
| `importCertificateChainSecret` | string | `""` | Name of the Kubernetes Secret containing the PEM-encoded certificate chain (key: `"ca.crt"`). Optional. Immutable. |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation, the certificate's status contains:

| Field | Type | Purpose |
|---|---|---|
| `certificateARN` | string | Full ARN of the certificate in AWS |
| `certificateStatus` | string | Current status (PENDING_VALIDATION, ISSUED, INACTIVE, EXPIRED, VALIDATION_TIMED_OUT, REVOKED, FAILED) |
| `notAfter` | string | Certificate expiry timestamp |
| `domainValidations` | array | Per-domain validation status including CNAME records (for DNS validation) |

## Complete Examples

### Public Certificate with DNS Validation

Request a public certificate that ACM automatically validates via DNS:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMCertificate
metadata:
  name: www-cert
  namespace: app-team
spec:
  configRef: general-policy
  domainName: "www.example.com"
  subjectAlternativeNames:
    - "example.com"
    - "*.example.com"
  deletionPolicy: retain
```

**Result:**
- ACM requests a certificate for `www.example.com`, `example.com`, and `*.example.com`
- DNS validation: CNAME records are shown in `status.domainValidations`; add these to Route 53 (or your DNS provider)
- Once CNAME records are validated, the certificate reaches `ISSUED` status
- Certificate auto-renews 60 days before expiry (AWS handles this automatically)
- Deletion of this Kubernetes resource retains the AWS certificate

### Private Certificate from Local CA

Issue a certificate from a private CA defined in the same cluster:

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
  keyAlgorithm: EC_prime256v1
  deletionPolicy: retain
```

**Result:**
- The RGD reads the private CA's ARN from `internal-ca.status.certificateAuthorityARN`
- ACM issues the certificate via the private CA
- Certificate reaches `ISSUED` status immediately (no validation needed)
- Certificate is not auto-renewed; you manage lifecycle via the resource

### Private Certificate from External CA

Reference an existing private CA by ARN:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMCertificate
metadata:
  name: external-ca-cert
  namespace: app-team
spec:
  configRef: general-policy
  domainName: "service.example.com"
  certificateAuthorityARN: "arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/12345678-1234-1234-1234-123456789012"
  deletionPolicy: retain
```

### Imported Certificate

Use an externally-obtained certificate:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: external-cert-secret
  namespace: app-team
type: Opaque
data:
  tls.crt: |
    -----BEGIN CERTIFICATE-----
    MIICljCCAX4C...
    -----END CERTIFICATE-----
  tls.key: |
    -----BEGIN RSA PRIVATE KEY-----
    MIIEpAIBAAKCAQEA...
    -----END RSA PRIVATE KEY-----
  ca.crt: |
    -----BEGIN CERTIFICATE-----
    MIIE...
    -----END CERTIFICATE-----
---
apiVersion: aws.kropath.run/v1alpha1
kind: ACMCertificate
metadata:
  name: imported-cert
  namespace: app-team
spec:
  configRef: general-policy
  importCertificateSecret: external-cert-secret
  importPrivateKeySecret: external-cert-secret
  importCertificateChainSecret: external-cert-secret
  deletionPolicy: retain
```

**Result:**
- Certificate imported into AWS ACM
- `domainName` is not required for imports
- Certificate is not auto-renewed; you manage lifecycle by updating the Secret and re-applying

### PCI Compliance Profile

Use governance to enforce strong cryptography and CT logging:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMCertificate
metadata:
  name: payment-cert
  namespace: payments
spec:
  configRef: pci
  domainName: "payment.example.com"
  subjectAlternativeNames:
    - "secure-payment.example.com"
  tags:
    business-critical: "true"
  syncedLabels:
    payment-processing: "true"
  deletionPolicy: retain
```

**Result:**
- PCI profile enforces `keyAlgorithm: "EC_prime256v1"` and `certificateTransparencyLogging: "ENABLED"`
- These values override any developer choices in `spec`
- Certificate created with PCI-compliant settings

## Immutability

The following fields are **immutable after creation** (enforced by Kubernetes validation). You cannot change them without deleting and recreating the certificate:

- `domainName`
- `subjectAlternativeNames`
- `keyAlgorithm`
- `domainValidationOptions`
- `certificateAuthorityARN`
- `certificateAuthorityRef`
- `importCertificateSecret`
- `importPrivateKeySecret`
- `importCertificateChainSecret`

## Key Behaviors

### Certificate Transparency Logging

`certificateTransparencyLogging` only applies to **public certificates**. For private or imported certificates, the field is silently ignored by the AWS API.

### Workflow Detection

The workflow is determined by which fields you set:

```
if importCertificateSecret is set
  → Import workflow
else if certificateAuthorityARN or certificateAuthorityRef is set
  → Private certificate workflow
else
  → Public certificate workflow
```

You must set exactly one set of workflow-specific fields. Setting multiple workflows (e.g., both `domainName` and `importCertificateSecret`) is an error.

### Auto-Renewal

- **Public certificates:** AWS automatically renews public certificates 60 days before expiry
- **Private/imported certificates:** No automatic renewal; you manage the lifecycle

### Domain Validation (Public Certificates)

After creating a public certificate, check `status.domainValidations` for CNAME records to add to your DNS provider:

```yaml
status:
  domainValidations:
    - domainName: "www.example.com"
      validationDomain: "_abcd1234.www.example.com.acm-validations.aws."
      validationRecordType: "CNAME"
      validationRecordValue: "_efgh5678.acm-validations.aws"
```

Add this CNAME to Route 53 (or your DNS provider) to complete validation.

## Governance Cascade

Effective configuration is determined by three layers:

1. **Governance mandatory tier** (highest) — Platform-enforced settings that cannot be overridden
2. **Certificate `spec`** (middle) — Developer choices
3. **Governance defaults tier** (lowest) — Fallback values

For example, if the PCI profile has `mandatory.keyAlgorithm: "EC_prime256v1"`, all certificates in that profile use EC_prime256v1 regardless of `spec.keyAlgorithm`.

## Cross-Family Integration

### Referenced By

- **ELB (load balancing)** — ALB/NLB TLS termination via `ELBListener.spec.certificateARN`
- **CloudFront (CDN)** — CloudFront viewer certificate via `CloudFrontDistribution.spec.viewerCertificateARN`
- **API Gateway** — custom domain TLS via `APIGatewayDomainName.spec.certificateARN`

### References

- `ACMPrivateCA` (via `certificateAuthorityRef` or `certificateAuthorityARN`) — for private certificate workflow

## Deletion Policies

- `retain` (default) — Deleting the Kubernetes resource keeps the AWS certificate intact
- `delete` — Deleting the Kubernetes resource also deletes the AWS certificate

Use `retain` for production certificates; use `delete` for temporary or test certificates.

## Troubleshooting

### Public Certificate Stuck in PENDING_VALIDATION

Check `status.domainValidations` for CNAME records to add. If the CNAME records are already in DNS:
- Wait 5-10 minutes for DNS propagation
- Verify the CNAME records match exactly (case-sensitive)

### Private Certificate Creation Fails

Verify the private CA exists and is in `ACTIVE` status:

```bash
kubectl get acmprivateca -n security
```

Check the CA's `status.caStatus` — it must be `ACTIVE`. If it's `PENDING_CERTIFICATE`, activate it first via `spec.activationCertificateSecret`.

### Import Certificate Fails

Verify the Kubernetes Secret exists and contains the correct keys:

```bash
kubectl get secret external-cert-secret -n app-team -o yaml
```

Ensure:
- `data["tls.crt"]` contains the PEM-encoded certificate
- `data["tls.key"]` contains the PEM-encoded private key
- `data["ca.crt"]` contains the certificate chain (if using a chain)

## Further Reading

- [Certificate Manager Family Spec](https://github.com/kropath/kropath-core/blob/main/docs/families/aws/certificate-manager.md) — detailed design reference
- [ACMConfig Governance](acmconfig.md) — governance cascade and profile configuration
