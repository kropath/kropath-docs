# ACMPrivateCertificate — Private CA-Issued Certificates

The `ACMPrivateCertificate` resource represents an end-entity certificate issued by a private CA against a PEM-encoded certificate signing request (CSR). Use `ACMPrivateCertificate` when you need certificates issued directly from a private CA (e.g., mutual TLS between microservices or workload identity) rather than going through ACM's managed certificate lifecycle.

## Use Cases

- **Service-to-service mTLS:** Issue certificates for mutual TLS between microservices
- **Workload identity:** Provide identity certificates for containerized workloads
- **Internal APIs:** Secure internal API endpoints with CA-issued certificates
- **Ephemeral certificates:** Issue short-lived certificates for temporary workloads
- **High-volume issuance:** Programmatically issue many certificates from a private CA

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `ACMConfig` governance profile to apply |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` (safe) or `"delete"` |

### Certificate Issuance

| Field | Type | Default | Purpose |
|---|---|---|---|
| `certificateAuthorityARN` | string | `""` | ARN of the issuing private CA. Immutable. Mutually exclusive with `certificateAuthorityRef`. |
| `certificateAuthorityRef` | string | `""` | Local `ACMPrivateCA` CR name. RGD reads `status.certificateAuthorityARN`. Immutable. Mutually exclusive with `certificateAuthorityARN`. |
| `certificateSigningRequest` | string | required | PEM-encoded CSR. Immutable. |
| `signingAlgorithm` | string | required | Signing algorithm (SHA256WITHRSA, SHA384WITHRSA, SHA512WITHRSA, SHA256WITHECDSA). Must match the CA's key family. Immutable. |
| `validity` | object | required | Certificate validity period. Immutable. |
| `validity.type` | string | required | Validity type: END_DATE, ABSOLUTE, DAYS, MONTHS, or YEARS |
| `validity.value` | string | required | Validity value (e.g., "365" for 365 days, or a specific date for END_DATE/ABSOLUTE) |
| `templateARN` | string | `""` | ACM PCA certificate template ARN. Defaults to `EndEntityCertificate/V1`. Immutable. |
| `certificateOutputSecret` | string | `""` | Kubernetes Secret name to write the issued certificate PEM into (key: `"tls.crt"`). Immutable. |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After issuance, the certificate's status contains:

| Field | Type | Purpose |
|---|---|---|
| `certificateARN` | string | Full ARN of the issued certificate in AWS |

## Complete Examples

### Certificate with 365-Day Validity

Issue a certificate valid for one year:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMPrivateCertificate
metadata:
  name: app-service-cert
  namespace: app-team
spec:
  configRef: general-policy
  certificateAuthorityRef: internal-ca
  certificateSigningRequest: |
    -----BEGIN CERTIFICATE REQUEST-----
    MIICljCCAX4C...
    -----END CERTIFICATE REQUEST-----
  signingAlgorithm: SHA256WITHECDSA
  validity:
    type: DAYS
    value: "365"
  deletionPolicy: retain
```

**Result:**
- Certificate issued via the `internal-ca` private CA
- Valid for 365 days from issuance
- AWS generates and stores the certificate ARN in `status.certificateARN`

### Certificate with Output to Kubernetes Secret

Issue a certificate and automatically write it to a Kubernetes Secret:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMPrivateCertificate
metadata:
  name: worker-cert
  namespace: workloads
spec:
  configRef: general-policy
  certificateAuthorityRef: workload-ca
  certificateSigningRequest: |
    -----BEGIN CERTIFICATE REQUEST-----
    MIICljCCAX4C...
    -----END CERTIFICATE REQUEST-----
  signingAlgorithm: SHA256WITHECDSA
  validity:
    type: DAYS
    value: "90"
  certificateOutputSecret: worker-tls-cert
  deletionPolicy: retain
```

**Result:**
- Certificate issued via `workload-ca`
- Valid for 90 days (short-lived for ephemeral workloads)
- Certificate automatically written to Secret `worker-tls-cert` at key `tls.crt`
- Workload can mount and use the Secret for mTLS

### Certificate with Specific Expiry Date

Issue a certificate that expires on a specific date:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMPrivateCertificate
metadata:
  name: audit-cert
  namespace: security
spec:
  configRef: general-policy
  certificateAuthorityRef: audit-ca
  certificateSigningRequest: |
    -----BEGIN CERTIFICATE REQUEST-----
    MIICljCCAX4C...
    -----END CERTIFICATE REQUEST-----
  signingAlgorithm: SHA256WITHECDSA
  validity:
    type: ABSOLUTE
    value: "2025-12-31T23:59:59Z"
  deletionPolicy: retain
```

**Result:**
- Certificate valid until 2025-12-31T23:59:59Z

### Mass Issuance for Workloads

Issue certificates for a set of workloads:

```yaml
# Private CA
apiVersion: aws.kropath.run/v1alpha1
kind: ACMPrivateCA
metadata:
  name: workload-ca
  namespace: security
spec:
  configRef: general-policy
  type: ROOT
  keyAlgorithm: EC_prime256v1
  signingAlgorithm: SHA256WITHECDSA
  subject:
    commonName: "workload-ca.internal.example.com"
  usageMode: SHORT_LIVED_CERTIFICATE
  activationCertificateSecret: workload-ca-cert
  deletionPolicy: retain
---
# Service A certificate
apiVersion: aws.kropath.run/v1alpha1
kind: ACMPrivateCertificate
metadata:
  name: service-a-cert
  namespace: app-team
spec:
  configRef: general-policy
  certificateAuthorityRef: workload-ca
  certificateSigningRequest: |
    -----BEGIN CERTIFICATE REQUEST-----
    MIIC7zCCAdeC...
    -----END CERTIFICATE REQUEST-----
  signingAlgorithm: SHA256WITHECDSA
  validity:
    type: DAYS
    value: "7"
  certificateOutputSecret: service-a-tls
  deletionPolicy: retain
---
# Service B certificate
apiVersion: aws.kropath.run/v1alpha1
kind: ACMPrivateCertificate
metadata:
  name: service-b-cert
  namespace: app-team
spec:
  configRef: general-policy
  certificateAuthorityRef: workload-ca
  certificateSigningRequest: |
    -----BEGIN CERTIFICATE REQUEST-----
    MIIC7zCCAdeC...
    -----END CERTIFICATE REQUEST-----
  signingAlgorithm: SHA256WITHECDSA
  validity:
    type: DAYS
    value: "7"
  certificateOutputSecret: service-b-tls
  deletionPolicy: retain
```

**Result:**
- Workload CA created and activated
- Service A and Service B each issue a 7-day certificate
- Certificates written to Secrets `service-a-tls` and `service-b-tls`
- Workloads mount these Secrets for mTLS communication

## CSR Generation

You must provide a valid PEM-encoded CSR. Generate a CSR using standard tools:

### OpenSSL

```bash
# Generate a private key (if you don't have one)
openssl genrsa -out service.key 2048

# Generate a CSR
openssl req -new -key service.key \
  -subj "/CN=service.internal.example.com/O=ACME Corp/C=US" \
  -out service.csr

# Encode as PEM
cat service.csr
```

### cfssl

```bash
# Create a CSR JSON
cat > csr.json <<EOF
{
  "CN": "service.internal.example.com",
  "key": {"algo": "ecdsa", "size": 256},
  "names": [{
    "C": "US",
    "O": "ACME Corp"
  }]
}
EOF

# Generate CSR
cfssl genkey csr.json | cfssljson -bare service
cat service.csr
```

Then embed the CSR in `spec.certificateSigningRequest` (between `-----BEGIN CERTIFICATE REQUEST-----` and `-----END CERTIFICATE REQUEST-----`).

## Validity Periods

### Type: DAYS

Validity measured in days from issuance:

```yaml
validity:
  type: DAYS
  value: "365"  # 365 days
```

### Type: MONTHS

Validity measured in months from issuance:

```yaml
validity:
  type: MONTHS
  value: "12"   # 12 months
```

### Type: YEARS

Validity measured in years from issuance:

```yaml
validity:
  type: YEARS
  value: "5"    # 5 years
```

### Type: ABSOLUTE

Exact expiry date (RFC 3339 format):

```yaml
validity:
  type: ABSOLUTE
  value: "2026-12-31T23:59:59Z"
```

### Type: END_DATE

Alias for ABSOLUTE (RFC 3339):

```yaml
validity:
  type: END_DATE
  value: "2026-12-31T23:59:59Z"
```

## Immutability

The following fields are **immutable after creation**:

- `certificateAuthorityARN`
- `certificateAuthorityRef`
- `certificateSigningRequest`
- `signingAlgorithm`
- `validity` (all subfields)
- `templateARN`
- `certificateOutputSecret`

You cannot change these fields without deleting and recreating the certificate.

## Key Behaviors

### Certificate Output Secret

If `certificateOutputSecret` is set, the issued certificate is automatically written to a Kubernetes Secret at key `tls.crt`. The Secret is created if it doesn't exist.

**Note:** Only the certificate is written to the Secret. The CSR and private key are not written; you must manage the private key separately (typically stored alongside the CSR used to generate it).

### Signing Algorithm

The `signingAlgorithm` must be compatible with the issuing CA's key algorithm:

| CA Key Algorithm | Valid Signing Algorithms |
|---|---|
| RSA_2048, RSA_4096 | SHA256WITHRSA, SHA384WITHRSA, SHA512WITHRSA |
| EC_prime256v1 | SHA256WITHECDSA |
| EC_secp384r1 | SHA384WITHECDSA |

If you specify an incompatible algorithm, AWS returns an error via the ACK controller.

### Template ARN

Most use cases can omit `templateARN` — the default `EndEntityCertificate/V1` template is suitable for general-purpose end-entity certificates. Only set this if you need a custom certificate template (rare).

### Cross-CA References

The issuing CA (`certificateAuthorityRef` or `certificateAuthorityARN`) must be in `ACTIVE` status. If the CA is `PENDING_CERTIFICATE` or `DISABLED`, certificate issuance fails.

## Governance Cascade

Effective configuration is determined by three layers:

1. **Governance mandatory tier** (highest) — Platform-enforced settings
2. **Certificate `spec`** (middle) — Developer choices
3. **Governance defaults tier** (lowest) — Fallback values

For example, if the governance profile has `mandatory.tags`, those tags are applied to the certificate regardless of `spec.tags`.

## Cross-Family Integration

### References

- `ACMPrivateCA` (via `spec.certificateAuthorityRef` or `spec.certificateAuthorityARN`) — the issuing private CA

## Deletion Policies

- `retain` (default) — Deleting the Kubernetes resource keeps the AWS certificate intact
- `delete` — Deleting the Kubernetes resource also deletes the AWS certificate

Use `retain` for important certificates; use `delete` for temporary or test certificates.

## Troubleshooting

### Certificate Issuance Fails

Check the error in `status.conditions`:

- **"Certificate authority not active"** — Ensure the CA is in `ACTIVE` status. If it's in `PENDING_CERTIFICATE`, activate it first via `activationCertificateSecret`.
- **"Invalid CSR"** — Verify the CSR is a valid PEM-encoded certificate request (between `-----BEGIN CERTIFICATE REQUEST-----` and `-----END CERTIFICATE REQUEST-----`).
- **"Invalid signing algorithm"** — Ensure `signingAlgorithm` is compatible with the CA's key algorithm.
- **"Insufficient permissions"** — Verify the AWS IAM role has `acm-pca:IssueCertificate` permission.

### Certificate Not Written to Secret

If `certificateOutputSecret` is set but the Secret doesn't contain the certificate:

1. Verify the Secret exists:
   ```bash
   kubectl get secret <certificateOutputSecret> -n <namespace>
   ```
2. Check the controller logs:
   ```bash
   kubectl logs -n kro-system -l app=kropath-controller | grep ACMPrivateCertificate
   ```
3. Verify AWS IAM permissions for writing to Secrets

### CSR Compatibility Issues

If you generated the CSR with a different tool:

1. Verify the CSR is PEM-encoded (check `-----BEGIN CERTIFICATE REQUEST-----`)
2. Verify the CSR matches the private key you're using
3. Regenerate if you're unsure:
   ```bash
   openssl req -new -key service.key -out service.csr
   ```

## Further Reading

- [Certificate Manager Family Spec](https://github.com/kropath/kropath-core/blob/main/docs/families/aws/certificate-manager.md) — detailed design reference
- [ACMPrivateCA](acmprivateca.md) — private CA setup and activation
- [ACMCertificate](acmcertificate.md) — alternative for public/private ACM certificates
