---
title: ACMPrivateCA — Private Certificate Authority Management
description: "The `ACMPrivateCA` resource represents an AWS Certificate Manager Private Certificate Authority (CA)."
doc_type: reference
---
# ACMPrivateCA — Private Certificate Authority Management

The `ACMPrivateCA` resource represents an AWS Certificate Manager Private Certificate Authority (CA). `ACMPrivateCA` supports root CAs (self-signed) and subordinate CAs (signed by another CA). The CA follows a two-step lifecycle: creation in `PENDING_CERTIFICATE` state, followed by activation via a signed certificate.

## Workflows

### Root CA

Create a root CA and sign its certificate externally:

1. Create `ACMPrivateCA` without `spec.activationCertificateSecret`
2. Retrieve the CSR from `status.certificateSigningRequest`
3. Self-sign the CSR externally
4. Store the signed certificate in a Kubernetes Secret
5. Set `spec.activationCertificateSecret` to complete activation

### Subordinate CA

Create a subordinate CA signed by another CA:

1. Create `ACMPrivateCA` without `spec.activationCertificateSecret`
2. Retrieve the CSR from `status.certificateSigningRequest`
3. Have another CA (kropath-managed or external) sign the CSR
4. Store the signed certificate and chain in Kubernetes Secrets
5. Set `spec.activationCertificateSecret` and `spec.activationCertificateChainSecret` to complete activation

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `ACMConfig` governance profile to apply |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` (safe) or `"delete"` |

### CA Configuration (Immutable After Creation)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `type` | string | required | CA type: `ROOT` or `SUBORDINATE`. Immutable. |
| `keyAlgorithm` | string | governed by ACMConfig | Key algorithm (RSA_2048, RSA_4096, EC_prime256v1, EC_secp384r1). Immutable. |
| `signingAlgorithm` | string | required | Signing algorithm (SHA256WITHRSA, SHA384WITHRSA, SHA512WITHRSA, SHA256WITHECDSA). Must match the key family. Immutable. |
| `subject` | object | required | X.500 distinguished name for the CA certificate. Immutable. |
| `subject.commonName` | string | required | CA common name (e.g., `"internal.example.com"`) |
| `subject.country` | string | optional | Country code (ISO 3166-1 alpha-2, e.g., `"US"`) |
| `subject.state` | string | optional | State or province name |
| `subject.locality` | string | optional | City or locality name |
| `subject.organization` | string | optional | Organization name |
| `subject.organizationalUnit` | string | optional | Organizational unit name |
| `usageMode` | string | governed by ACMConfig | `GENERAL_PURPOSE` or `SHORT_LIVED_CERTIFICATE`. Immutable. |
| `keyStorageSecurityStandard` | string | governed by ACMConfig | FIPS level (FIPS_140_2_LEVEL_2_OR_HIGHER or FIPS_140_2_LEVEL_3_OR_HIGHER). Immutable. |

### Revocation Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `crlEnabled` | boolean | `false` | Enable CRL distribution point |
| `crlExpirationInDays` | integer | (not set) | CRL validity period in days (1–5000 days) |
| `crlS3BucketName` | string | `""` | S3 bucket for CRL publication |
| `crlCustomCNAME` | string | `""` | Custom CNAME for the CRL distribution point |
| `crlS3ObjectACL` | string | `""` | S3 object ACL for CRL files (e.g., `public-read`) |
| `ocspEnabled` | boolean | `false` | Enable OCSP responder |
| `ocspCustomCNAME` | string | `""` | Custom CNAME for OCSP responder |

### CA Activation

| Field | Type | Default | Purpose |
|---|---|---|---|
| `activationCertificateSecret` | string | `""` | Kubernetes Secret name containing the signed CA certificate (key: `"tls.crt"`). Immutable. When set, triggers activation. |
| `activationCertificateChainSecret` | string | `""` | Kubernetes Secret name containing the certificate chain (key: `"ca.crt"`). Required for subordinate CAs. Immutable. |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After creation, the CA's status contains:

| Field | Type | Purpose |
|---|---|---|
| `certificateAuthorityARN` | string | Full ARN of the CA in AWS |
| `caStatus` | string | Current status (CREATING, PENDING_CERTIFICATE, ACTIVE, DISABLED, DELETED, EXPIRED, FAILED) |
| `certificateSigningRequest` | string | PEM-encoded CSR (populated while in PENDING_CERTIFICATE state) |
| `serial` | string | CA certificate serial number (populated after activation) |
| `notBefore` | string | CA certificate validity start (populated after activation) |
| `notAfter` | string | CA certificate expiry (populated after activation) |

## Complete Examples

### Root CA with External Signing

Create a root CA and self-sign it externally:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMPrivateCA
metadata:
  name: root-ca
  namespace: security
spec:
  configRef: general-policy
  type: ROOT
  keyAlgorithm: EC_prime256v1
  signingAlgorithm: SHA256WITHECDSA
  subject:
    commonName: "root.internal.example.com"
    country: "US"
    state: "California"
    locality: "San Francisco"
    organization: "ACME Corp"
  usageMode: GENERAL_PURPOSE
  crlEnabled: true
  crlExpirationInDays: 7
  crlS3BucketName: "my-crl-bucket"
  deletionPolicy: retain
```

**Result:**
- CA created in `PENDING_CERTIFICATE` state
- CSR is available in `status.certificateSigningRequest`
- Extract the CSR and self-sign it externally (using `openssl ca`, `cfssl`, or another CA tool)
- Store the signed certificate in a Kubernetes Secret:
  ```bash
  kubectl create secret generic root-ca-cert --from-file=tls.crt=root-ca.pem -n security
  ```
- Update the `ACMPrivateCA` to activate:
  ```yaml
  spec:
    activationCertificateSecret: root-ca-cert
  ```
- CA transitions to `ACTIVE` state

### Subordinate CA

Create a subordinate CA signed by a root CA:

```yaml
# Root CA (already created and activated)
apiVersion: aws.kropath.run/v1alpha1
kind: ACMPrivateCA
metadata:
  name: root-ca
  namespace: security
spec:
  configRef: general-policy
  type: ROOT
  keyAlgorithm: EC_prime256v1
  signingAlgorithm: SHA256WITHECDSA
  subject:
    commonName: "root.internal.example.com"
  activationCertificateSecret: root-ca-cert
  deletionPolicy: retain
---
# Subordinate CA (pending signing by root)
apiVersion: aws.kropath.run/v1alpha1
kind: ACMPrivateCA
metadata:
  name: intermediate-ca
  namespace: security
spec:
  configRef: general-policy
  type: SUBORDINATE
  keyAlgorithm: EC_prime256v1
  signingAlgorithm: SHA256WITHECDSA
  subject:
    commonName: "intermediate.internal.example.com"
  deletionPolicy: retain
```

**Result:**
- Subordinate CA created in `PENDING_CERTIFICATE` state
- Extract CSR from `status.certificateSigningRequest`
- Sign the CSR using the root CA's private key:
  ```bash
  # Pseudo-code: actual signing depends on your CA tool
  acm sign-csr --ca-arn=<root-ca-arn> --csr=intermediate.csr > intermediate-cert.pem
  ```
- Store the signed certificate and chain:
  ```bash
  kubectl create secret generic intermediate-ca-cert --from-file=tls.crt=intermediate-cert.pem -n security
  kubectl create secret generic intermediate-ca-chain --from-file=ca.crt=root-ca.pem -n security
  ```
- Update the subordinate CA to activate:
  ```yaml
  spec:
    activationCertificateSecret: intermediate-ca-cert
    activationCertificateChainSecret: intermediate-ca-chain
  ```
- Subordinate CA transitions to `ACTIVE` state

### CA with CRL and OCSP Revocation

Create a CA with both CRL and OCSP revocation:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMPrivateCA
metadata:
  name: revocable-ca
  namespace: security
spec:
  configRef: general-policy
  type: ROOT
  keyAlgorithm: RSA_2048
  signingAlgorithm: SHA256WITHRSA
  subject:
    commonName: "revocable-ca.internal.example.com"
    organization: "ACME Corp"
  usageMode: GENERAL_PURPOSE
  crlEnabled: true
  crlExpirationInDays: 30
  crlS3BucketName: "crl-distribution-bucket"
  crlCustomCNAME: "crl.internal.example.com"
  crlS3ObjectACL: "public-read"
  ocspEnabled: true
  ocspCustomCNAME: "ocsp.internal.example.com"
  activationCertificateSecret: revocable-ca-cert
  deletionPolicy: retain
```

**Result:**
- CA configured with both CRL and OCSP
- CRL published to S3 and accessible via `crl.internal.example.com`
- OCSP responder available via `ocsp.internal.example.com`
- Certificates issued by this CA can be revoked via either mechanism

### Short-Lived Certificate CA

Create a CA optimized for ephemeral certificates (e.g., mTLS between services):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMPrivateCA
metadata:
  name: ephemeral-ca
  namespace: security
spec:
  configRef: internal-services
  type: ROOT
  keyAlgorithm: EC_prime256v1
  signingAlgorithm: SHA256WITHECDSA
  subject:
    commonName: "ephemeral.internal.example.com"
  usageMode: SHORT_LIVED_CERTIFICATE
  crlEnabled: false
  activationCertificateSecret: ephemeral-ca-cert
  deletionPolicy: retain
```

**Result:**
- CA configured for short-lived certificate issuance (e.g., hours or days)
- `internal-services` profile applies modern cryptography and disables CT logging
- Ideal for high-frequency certificate issuance in service meshes

## Two-Step CA Lifecycle

### Step 1: CA Creation (PENDING_CERTIFICATE)

Creating an `ACMPrivateCA` without `spec.activationCertificateSecret`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMPrivateCA
metadata:
  name: my-ca
  namespace: security
spec:
  configRef: general-policy
  type: ROOT
  keyAlgorithm: EC_prime256v1
  signingAlgorithm: SHA256WITHECDSA
  subject:
    commonName: "my-ca.internal.example.com"
  # Note: activationCertificateSecret is NOT set
```

The CA is created in `PENDING_CERTIFICATE` state and cannot issue certificates. The CSR is exposed via:

```bash
kubectl get acmprivateca my-ca -n security -o jsonpath='{.status.certificateSigningRequest}'
```

### Step 2: CA Activation (ACTIVE)

Once the CSR is signed and the certificate is stored in a Kubernetes Secret:

```bash
kubectl create secret generic my-ca-cert --from-file=tls.crt=my-ca-signed.pem -n security
```

Update the `ACMPrivateCA` to set the secret:

```yaml
spec:
  activationCertificateSecret: my-ca-cert
```

The CA transitions to `ACTIVE` state and can issue certificates.

## Immutability

The following fields are **immutable after creation**:

- `type`
- `keyAlgorithm`
- `signingAlgorithm`
- `subject` (all subfields)
- `usageMode`
- `keyStorageSecurityStandard`
- `activationCertificateSecret`
- `activationCertificateChainSecret`

Revocation configuration (`crlEnabled`, `crlExpirationInDays`, `ocspEnabled`, etc.) can be updated after creation.

## Key Behaviors

### Region-Specific FIPS Constraints

`keyStorageSecurityStandard` defaults to `FIPS_140_2_LEVEL_3_OR_HIGHER`, but some AWS regions (e.g., `ap-northeast-3`, `ap-southeast-3`) only support `FIPS_140_2_LEVEL_2_OR_HIGHER`. If you get an AWS error about FIPS level, update your `ACMConfig.defaults.keyStorageSecurityStandard` to `FIPS_140_2_LEVEL_2_OR_HIGHER` for those regions.

### CSR Expiration

The CSR in `status.certificateSigningRequest` is valid for up to one hour. If you don't activate the CA within that window, the CSR expires and you must regenerate it. (There is no self-service CSR regeneration; contact AWS support or recreate the CA if the CSR expires.)

### Certificate Chain for Subordinate CAs

For subordinate CAs, always provide the complete certificate chain (including intermediate CAs and the root CA) in `activationCertificateChainSecret`. This allows clients to build the full trust chain to the root CA.

## Governance Cascade

Effective configuration is determined by three layers:

1. **Governance mandatory tier** (highest) — Platform-enforced settings
2. **CA `spec`** (middle) — Operator choices
3. **Governance defaults tier** (lowest) — Fallback values

For example, if the governance profile has `mandatory.keyAlgorithm: "EC_prime256v1"`, all CAs in that profile use EC_prime256v1 regardless of `spec.keyAlgorithm`.

## Cross-Family Integration

### Referenced By

- `ACMCertificate` (via `spec.certificateAuthorityRef` or `spec.certificateAuthorityARN`) — for private certificate issuance
- `ACMPrivateCertificate` (via `spec.certificateAuthorityRef` or `spec.certificateAuthorityARN`) — for end-entity certificate issuance

## Deletion Policies

- `retain` (default) — Deleting the Kubernetes resource keeps the AWS CA intact
- `delete` — Deleting the Kubernetes resource also deletes the AWS CA (use with caution)

Use `retain` for production CAs; use `delete` only for temporary or test CAs.

## Troubleshooting

### CSR Not Appearing in Status

Wait 30 seconds for the CA to be created in AWS. If the CSR still doesn't appear, check the controller logs:

```bash
kubectl logs -n kro-system -l app=kropath-controller | grep ACMPrivateCA
```

### CA Stuck in CREATING

The CA may be pending resource creation in AWS. Wait a few minutes; AWS typically completes creation within 1 minute.

### Can't Activate CA

Verify:
1. The `activationCertificateSecret` exists in the same namespace
2. The Secret contains the key `"tls.crt"`
3. The certificate in `tls.crt` is the signed CA certificate (not a CSR)
4. For subordinate CAs, `activationCertificateChainSecret` also exists and contains the parent chain

## Further Reading

- [Certificate Manager Family Spec](https://github.com/kropath/kropath-core/blob/main/docs/families/aws/certificate-manager.md) — detailed design reference
- [ACMPrivateCertificate](acmprivatecertificate.md) — issuing end-entity certificates from a private CA
- [ACMConfig Governance](acmconfig.md) — governance cascade and profile configuration
