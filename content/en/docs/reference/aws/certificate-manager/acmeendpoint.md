---
title: ACMEEndpoint — ACME Protocol Endpoints
description: "The `ACMEEndpoint` resource represents an AWS ACM ACME (Automated Certificate Management Environment) endpoint."
doc_type: reference
---
# ACMEEndpoint — ACME Protocol Endpoints

The `ACMEEndpoint` resource represents an AWS ACM ACME (Automated Certificate Management Environment) endpoint. ACME endpoints allow ACME-compatible clients (like `certbot`, `acme.sh`, or Kubernetes `cert-manager`) to request and automatically renew certificates via the ACME protocol, without requiring AWS API credentials.

## Use Cases

- **Automated certificate issuance:** Enable ACME clients to request certificates programmatically
- **cert-manager integration:** Use Kubernetes `cert-manager` to manage certificates via ACME
- **Third-party tooling:** Integrate with external ACME-compatible tools
- **Ephemeral workloads:** Automatically provision and renew certificates for temporary services

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `ACMConfig` governance profile to apply |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` (safe) or `"delete"` |

### ACME Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `authorizationBehavior` | string | required | Authorization behavior: `PRE_APPROVED` (auto-approve ACME clients). Immutable. |
| `allowedKeyAlgorithms` | array | `[]` | Key algorithms allowed for certificates issued through this endpoint (RSA_2048, EC_prime256v1, EC_secp384r1) |
| `contact` | string | `""` | Whether ACME clients must supply contact info: `REQUIRED` or `NOT_REQUIRED` |
| `certificateTags` | array | `[]` | Tags applied to certificates issued through this endpoint. Each entry: `{key, value}`. Immutable. |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After creation, the endpoint's status contains:

| Field | Type | Purpose |
|---|---|---|
| `acmeEndpointARN` | string | Full ARN of the ACME endpoint in AWS |
| `endpointURL` | string | ACME endpoint URL (used by ACME clients) |
| `endpointStatus` | string | Current status (CREATING, ACTIVE, DISABLED, DELETED, FAILED) |

## Complete Examples

### Basic ACME Endpoint

Create a simple ACME endpoint that pre-approves all client requests:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMEEndpoint
metadata:
  name: internal-acme
  namespace: kro-system
spec:
  configRef: general-policy
  authorizationBehavior: PRE_APPROVED
  allowedKeyAlgorithms:
    - RSA_2048
    - EC_prime256v1
  deletionPolicy: retain
```

**Result:**
- ACME endpoint created in AWS
- `status.endpointURL` contains the ACME endpoint URL
- ACME clients connect to this endpoint to request certificates
- All requests are automatically approved (no manual review)
- Certificates issued via this endpoint can use RSA_2048 or EC_prime256v1 keys

### ACME Endpoint with Certificate Tagging

Create an ACME endpoint that automatically tags issued certificates:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMEEndpoint
metadata:
  name: production-acme
  namespace: kro-system
spec:
  configRef: general-policy
  authorizationBehavior: PRE_APPROVED
  allowedKeyAlgorithms:
    - RSA_2048
    - EC_prime256v1
    - EC_secp384r1
  certificateTags:
    - key: source
      value: acme
    - key: environment
      value: production
    - key: managed-by
      value: kropath
  contact: NOT_REQUIRED
  deletionPolicy: retain
```

**Result:**
- ACME endpoint created with auto-approval
- All certificates issued via this endpoint automatically tagged with:
  - `source: acme`
  - `environment: production`
  - `managed-by: kropath`
- ACME clients can use three key algorithm options

### ACME Endpoint with cert-manager Integration

Create an ACME endpoint for use with Kubernetes `cert-manager`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMEEndpoint
metadata:
  name: cert-manager-acme
  namespace: cert-manager
spec:
  configRef: general-policy
  authorizationBehavior: PRE_APPROVED
  allowedKeyAlgorithms:
    - RSA_2048
    - EC_prime256v1
  contact: NOT_REQUIRED
  deletionPolicy: retain
---
# cert-manager Issuer using this ACME endpoint
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: acme-issuer
spec:
  acme:
    server: https://acme.aws.amazonaws.com/acme/v2/  # Example; actual URL from endpointURL
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-key
    solvers:
      - dns01:
          route53: {}
```

**Result:**
- ACME endpoint created
- cert-manager `ClusterIssuer` configured to use this endpoint
- Applications can request certificates via cert-manager `Certificate` resources
- Certificates automatically requested and renewed via ACME

## Authorization Behavior

### PRE_APPROVED

With `authorizationBehavior: PRE_APPROVED`, all certificate requests via the ACME protocol are automatically approved without manual review. This is suitable for:

- Internal environments with trusted ACME clients
- Automated certificate provisioning in Kubernetes clusters
- High-volume certificate issuance scenarios

**Important:** Only use `PRE_APPROVED` if you trust the ACME clients connecting to this endpoint. Untrusted clients can request arbitrary certificates.

## Allowed Key Algorithms

The `allowedKeyAlgorithms` list restricts which key algorithms ACME clients are permitted to use:

```yaml
allowedKeyAlgorithms:
  - RSA_2048      # 2048-bit RSA (traditional)
  - EC_prime256v1 # ECDSA P-256 (modern)
  - EC_secp384r1  # ECDSA P-384 (strong)
```

If an ACME client requests a key algorithm not in this list, the request is denied.

**Note:** If `allowedKeyAlgorithms` is empty, AWS applies a default set of algorithms. Specify the list explicitly to enforce your organization's key algorithm policy.

## Certificate Tagging

`certificateTags` are automatically applied to all certificates issued via this ACME endpoint, in addition to any tags the ACME client specifies:

```yaml
certificateTags:
  - key: source
    value: acme
  - key: environment
    value: production
```

These tags are useful for:
- Identifying certificates as ACME-issued
- Tracking certificate source/environment
- Enforcing organizational tagging policies
- Implementing cost allocation or compliance controls

## Immutability

The following fields are **immutable after creation**:

- `authorizationBehavior`
- `certificateTags` (all entries)

You cannot change these fields without deleting and recreating the endpoint.

## Key Behaviors

### Endpoint URL

The `status.endpointURL` is the ACME-compliant endpoint URL that clients use. It looks like:

```
https://acme.aws.amazonaws.com/acme/v2/endpoint/12345678-1234-1234-1234-123456789012
```

Provide this URL to ACME clients (e.g., in `certbot --server`, `cert-manager` Issuer config, etc.).

### Domain Validation

ACME requires domain validation to prove ownership. The validation method depends on your setup:

- **DNS challenge:** Client adds a DNS TXT record to prove domain ownership
- **HTTP challenge:** Client serves a validation file via HTTP to prove domain ownership

Typically, use `ACMEDomainValidation` resources to pre-validate domains before ACME clients request certificates, reducing validation latency.

### Certificate Renewal

ACME clients (like `cert-manager`) automatically renew certificates before expiry. The renewal process uses the same domain validation method as initial issuance.

## Governance Cascade

Effective configuration is determined by three layers:

1. **Governance mandatory tier** (highest) — Platform-enforced settings
2. **Endpoint `spec`** (middle) — Operator choices
3. **Governance defaults tier** (lowest) — Fallback values

For example, if governance has `mandatory.tags`, those tags are applied to all certificates issued via this endpoint.

## Cross-Family Integration

### Referenced By

- `ACMEDomainValidation` (via `spec.acmeEndpointRef` or `spec.acmeEndpointARN`) — for domain prevalidation

## Deletion Policies

- `retain` (default) — Deleting the Kubernetes resource keeps the AWS ACME endpoint intact
- `delete` — Deleting the Kubernetes resource also deletes the AWS ACME endpoint

Use `retain` for production endpoints; use `delete` for temporary or test endpoints.

## Troubleshooting

### Endpoint Stuck in CREATING

The endpoint may be pending resource creation in AWS. Wait a few minutes; AWS typically completes creation within 1 minute.

### ACME Client Connection Fails

1. Verify the `status.endpointURL` is correct and accessible
2. Verify DNS resolution for the endpoint URL:
   ```bash
   nslookup acme.aws.amazonaws.com
   ```
3. Check if the endpoint is in `ACTIVE` status:
   ```bash
   kubectl get acmeendpoint internal-acme -o jsonpath='{.status.endpointStatus}'
   ```

### Certificate Request Denied with "Algorithm Not Allowed"

The ACME client requested a key algorithm not in `allowedKeyAlgorithms`. Either:

1. Add the algorithm to `allowedKeyAlgorithms`
2. Configure the ACME client to use a supported algorithm

### Missing Certificates from ACME Clients

If certificates issued via ACME don't appear in AWS ACM:

1. Verify the ACME client successfully completed domain validation
2. Check the ACME client logs for errors
3. Verify `authorizationBehavior: PRE_APPROVED` (if not set, manual approval may be required)
4. Verify the endpoint `status.endpointStatus` is `ACTIVE`

## Further Reading

- [Certificate Manager Family Spec](https://github.com/kropath/kropath-core/blob/main/docs/families/aws/certificate-manager.md) — detailed design reference
- [ACMEDomainValidation](acmedomainvalidation.md) — domain prevalidation for ACME
- [cert-manager Documentation](https://cert-manager.io/docs/) — Kubernetes certificate management integration
