# ACMEDomainValidation — ACME Domain Prevalidation

The `ACMEDomainValidation` resource prevalidates domain ownership against an ACME endpoint using DNS (Route 53). Domain prevalidation is optional but recommended — it proves domain ownership to the ACME endpoint before ACME clients request certificates, reducing validation latency during certificate issuance.

## Breaking Changes (KRO-1054)

If upgrading from earlier versions, note the following breaking changes to field names and types:

| Old field | Change | New field | Action Required |
|---|---|---|---|
| `dnsPrevalidationEnabled` | Dropped | — | Removed. DNS prevalidation is now enabled automatically when `hostedZoneID` is non-empty. Delete any references to this field. |
| `dnsPrevalidationExactDomain` | Renamed | `domainScopeExactDomain` | Rename field. Value unchanged — was already `"ENABLED"` or `"DISABLED"`. |
| `dnsPrevalidationSubdomains` | Renamed + type change | `domainScopeSubdomains` | Update field name and change from `boolean` to `string`. Use `"ENABLED"` or `"DISABLED"` instead of `true`/`false`. |
| `dnsPrevalidationWildcards` | Renamed + type change | `domainScopeWildcards` | Update field name and change from `boolean` to `string`. Use `"ENABLED"` or `"DISABLED"` instead of `true`/`false`. |

**Migration example:**

```yaml
# OLD (no longer works)
spec:
  dnsPrevalidationEnabled: true
  dnsPrevalidationExactDomain: "ENABLED"
  dnsPrevalidationSubdomains: true
  dnsPrevalidationWildcards: false

# NEW (required)
spec:
  hostedZoneID: "Z1234567890ABC"  # Enables DNS prevalidation
  domainScopeExactDomain: "ENABLED"
  domainScopeSubdomains: "ENABLED"
  domainScopeWildcards: "DISABLED"
```

## Use Cases

- **Reduce issuance latency:** Pre-validate domains so certificate requests complete faster
- **Bulk domain setup:** Validate many domains at once before applications request certificates
- **Wildcard prevalidation:** Validate wildcard domains and their subdomains in advance
- **Compliance:** Prove domain ownership in bulk for compliance or audit purposes

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `ACMConfig` governance profile to apply |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` (safe) or `"delete"` |

### Domain and Endpoint Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `domainName` | string | required | Domain to validate (e.g., `"www.example.com"` or `"*.example.com"`). Immutable. |
| `acmeEndpointARN` | string | `""` | ARN of the ACME endpoint. Immutable. Mutually exclusive with `acmeEndpointRef`. |
| `acmeEndpointRef` | string | `""` | Local `ACMEEndpoint` CR name. RGD reads `status.acmeEndpointARN`. Immutable. Mutually exclusive with `acmeEndpointARN`. |

### DNS Validation Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `hostedZoneID` | string | `""` | Route 53 hosted zone ID for DNS prevalidation (e.g., `"Z1234567890ABC"`). Optional. |
| `domainScopeExactDomain` | string | `""` | Validate exact domain (ENABLED or DISABLED). Immutable. |
| `domainScopeSubdomains` | string | `""` | Validate subdomains (ENABLED or DISABLED). Immutable. |
| `domainScopeWildcards` | string | `""` | Validate wildcard domains (ENABLED or DISABLED). Immutable. |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After validation, the domain's status contains:

| Field | Type | Purpose |
|---|---|---|
| `validationARN` | string | Full ARN of the domain validation in AWS |
| `validationStatus` | string | Current status (SUCCESS, PENDING, FAILED) |
| `prevalidationDetails` | object | Details about the validation (DNS records used, validation method, etc.) |

## Complete Examples

### Basic Domain Prevalidation

Prevalidate a single domain against an ACME endpoint:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMEDomainValidation
metadata:
  name: www-validation
  namespace: kro-system
spec:
  configRef: general-policy
  domainName: "www.example.com"
  acmeEndpointRef: internal-acme
  hostedZoneID: "Z1234567890ABC"
  deletionPolicy: retain
```

**Result:**
- Domain `www.example.com` prevalidated
- Validation performed via DNS (Route 53 hosted zone `Z1234567890ABC`)
- `status.validationStatus` shows `SUCCESS` once validation completes
- ACME clients can now request certificates for this domain faster (no additional validation needed)

### Wildcard Domain Prevalidation

Prevalidate a wildcard domain and its subdomains:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMEDomainValidation
metadata:
  name: wildcard-validation
  namespace: kro-system
spec:
  configRef: general-policy
  domainName: "*.internal.example.com"
  acmeEndpointRef: internal-acme
  hostedZoneID: "Z1234567890ABC"
  domainScopeExactDomain: ENABLED
  domainScopeSubdomains: ENABLED
  domainScopeWildcards: ENABLED
  deletionPolicy: retain
```

**Result:**
- Wildcard domain `*.internal.example.com` prevalidated
- Exact domain `internal.example.com` also validated
- Subdomains (e.g., `api.internal.example.com`) validated
- Wildcard certificates issued for this domain complete validation immediately

### Domain with External ACME Endpoint

Reference an existing ACME endpoint by ARN:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMEDomainValidation
metadata:
  name: external-acme-validation
  namespace: kro-system
spec:
  configRef: general-policy
  domainName: "api.example.com"
  acmeEndpointARN: "arn:aws:acm:us-east-1:123456789012:acme-endpoint/12345678-1234-1234-1234-123456789012"
  hostedZoneID: "Z1234567890ABC"
  deletionPolicy: retain
```

**Result:**
- Domain validated against external ACME endpoint
- ACME clients connecting to that endpoint can request certificates for this domain without re-validating

### Bulk Domain Prevalidation

Prevalidate multiple domains at once:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMEDomainValidation
metadata:
  name: api-validation
  namespace: kro-system
spec:
  configRef: general-policy
  domainName: "api.example.com"
  acmeEndpointRef: internal-acme
  hostedZoneID: "Z1234567890ABC"
  deletionPolicy: retain
---
apiVersion: aws.kropath.run/v1alpha1
kind: ACMEDomainValidation
metadata:
  name: www-validation
  namespace: kro-system
spec:
  configRef: general-policy
  domainName: "www.example.com"
  acmeEndpointRef: internal-acme
  hostedZoneID: "Z1234567890ABC"
  deletionPolicy: retain
---
apiVersion: aws.kropath.run/v1alpha1
kind: ACMEDomainValidation
metadata:
  name: cdn-validation
  namespace: kro-system
spec:
  configRef: general-policy
  domainName: "cdn.example.com"
  acmeEndpointRef: internal-acme
  hostedZoneID: "Z1234567890ABC"
  deletionPolicy: retain
```

**Result:**
- Three domains prevalidated simultaneously
- Each reaches `SUCCESS` status once validation completes
- Applications can now request certificates for these domains via ACME without delay

## Domain Scope Options

Domain scope controls which certificate identities are valid for the prevalidated domain:

| Option | When ENABLED | When DISABLED |
|---|---|---|
| `domainScopeExactDomain` | Exact domain matches are valid (e.g., cert for `www.example.com` when validating `www.example.com`) | Exact domain matches fail validation |
| `domainScopeSubdomains` | Subdomain matches are valid (e.g., cert for `api.www.example.com` when validating `www.example.com`) | Subdomain matches fail validation |
| `domainScopeWildcards` | Wildcard matches are valid (e.g., cert for `*.www.example.com` when validating `www.example.com`) | Wildcard matches fail validation |

**Default behavior:** If domain scope options are not set, AWS applies a default configuration that typically validates exact domain and subdomains.

**Common patterns:**

```yaml
# Exact domain only
domainScopeExactDomain: ENABLED
domainScopeSubdomains: DISABLED
domainScopeWildcards: DISABLED

# Exact domain and subdomains (most common)
domainScopeExactDomain: ENABLED
domainScopeSubdomains: ENABLED
domainScopeWildcards: DISABLED

# Wildcard domain (validates *.example.com, api.example.com, etc.)
domainScopeExactDomain: ENABLED
domainScopeSubdomains: ENABLED
domainScopeWildcards: ENABLED
```

## Immutability

The following fields are **immutable after creation**:

- `domainName`
- `acmeEndpointARN`
- `acmeEndpointRef`
- `domainScopeExactDomain`
- `domainScopeSubdomains`
- `domainScopeWildcards`

You cannot change these fields without deleting and recreating the validation.

## Key Behaviors

### DNS Validation

Domain validation is performed via DNS. Specifically:

1. AWS generates a DNS TXT record to add to your Route 53 hosted zone
2. You add the TXT record to Route 53 (typically automated for AWS-managed zones)
3. AWS verifies the TXT record exists
4. Validation completes

The `status.prevalidationDetails` provides the exact DNS records to add, if you need to manually configure them.

### Hosted Zone ID

The `hostedZoneID` field is optional. If provided, it specifies the Route 53 hosted zone where validation DNS records are added. If not provided, AWS uses a default configuration (typically the zone for the domain).

**Example:**
```yaml
hostedZoneID: "Z1234567890ABC"  # ID for example.com zone
```

Find your hosted zone ID:
```bash
aws route53 list-hosted-zones-by-name --dns-name example.com --query 'HostedZones[0].Id' --output text
```

### Validation Time

Domain prevalidation typically completes within 30 seconds of creation. Check `status.validationStatus`:

- `PENDING` — Validation in progress
- `SUCCESS` — Domain validated successfully
- `FAILED` — Validation failed (check `status.prevalidationDetails` for error details)

## Cross-Family Integration

### References

- `ACMEEndpoint` (via `spec.acmeEndpointRef` or `spec.acmeEndpointARN`) — the ACME endpoint to validate against

## Governance Cascade

Effective configuration is determined by three layers:

1. **Governance mandatory tier** (highest) — Platform-enforced settings
2. **Validation `spec`** (middle) — Operator choices
3. **Governance defaults tier** (lowest) — Fallback values

For example, if governance has `mandatory.tags`, those tags are applied to all domain validations.

## Deletion Policies

- `retain` (default) — Deleting the Kubernetes resource keeps the AWS domain validation intact
- `delete` — Deleting the Kubernetes resource also deletes the AWS domain validation

Use `retain` for important validations; use `delete` for temporary or test validations.

## Troubleshooting

### Validation Stuck in PENDING

Validation should complete within 30 seconds. If still `PENDING` after 2 minutes:

1. Check if DNS records were added to Route 53:
   ```bash
   aws route53 list-resource-record-sets --hosted-zone-id Z1234567890ABC --query "ResourceRecordSets[?Name=='_acm-validations...']"
   ```
2. Verify the hosted zone ID is correct:
   ```bash
   kubectl get acmedomainvalidation www-validation -o jsonpath='{.spec.hostedZoneID}'
   ```
3. Check the controller logs:
   ```bash
   kubectl logs -n kro-system -l app=kropath-controller | grep ACMEDomainValidation
   ```

### Validation Failed

Check `status.prevalidationDetails` for the specific error:

- **"Invalid domain"** — Ensure the domain name is correct and properly formatted
- **"Hosted zone not found"** — Verify the hosted zone ID is correct and the zone exists
- **"DNS validation failed"** — Ensure the TXT record was added to Route 53 correctly
- **"Endpoint not found"** — Verify the ACME endpoint exists and is in `ACTIVE` status

### ACME Client Still Requires Domain Validation

If an ACME client still requires domain validation after prevalidation:

1. Verify the domain scope options match the certificate identity:
   - For exact domain certs, ensure `domainScopeExactDomain: ENABLED`
   - For subdomain certs, ensure `domainScopeSubdomains: ENABLED`
   - For wildcard certs, ensure `domainScopeWildcards: ENABLED`
2. Verify the validation reached `SUCCESS` status
3. Verify the ACME client is connecting to the same ACME endpoint that was prevalidated

## Further Reading

- [Certificate Manager Family Spec](https://github.com/kropath/kropath-core/blob/main/docs/families/aws/certificate-manager.md) — detailed design reference
- [ACMEEndpoint](acmeendpoint.md) — ACME endpoint setup and configuration
- [Route 53 Documentation](https://docs.aws.amazon.com/route53/) — AWS DNS and hosted zone management
