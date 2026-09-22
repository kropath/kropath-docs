---
doc_type: task
title: Onboard the platform-shared namespace and its shared buckets
---

# Onboard the platform-shared namespace and its shared buckets

**Document type:** Task — this page walks you through one concrete goal in a sequence of steps. It
is not a concept page or a tutorial. For field-by-field reference material, follow the links in
[Reference](#reference).

## The business case

Every tenant that onboards to kropath — the data team, the payments team, and the ones after them —
needs two things to exist before their first resource can be created: somewhere for their logs to
land, and somewhere for their build artifacts to live. If each team invents those for itself, you
get a different retention policy, a different encryption posture, and a different bucket-naming
scheme per team, and no way to answer "who read this object" consistently across the estate.

This task builds that foundation. The platform team onboards the `platform-shared` namespace and
provisions two kinds of bucket:

```
  shared account (999988887777)                 ns: platform-shared
  ┌──────────────────────────────────────────────┐
  │  central-logging-999988887777-us-east-1      │  ← log sink for this account
  │    ← S3 server access logs (same account)    │
  │    ← ALB / ELB access logs                   │
  │    ← other AWS service log delivery          │
  └──────────────────────────────────────────────┘

  dev account (111122223333)                  test account (444455556666)
  ns: platform-dev, payments-dev, data-dev    ns: platform-test, payments-test, data-test
  ┌────────────────────────────────────┐      ┌────────────────────────────────────┐
  │ central-logging-111122223333-…     │      │ central-logging-444455556666-…     │
  │   ▲ server access logs             │      │   ▲ server access logs             │
  │   │                                │      │   │                                │
  │ artifacts-111122223333-us-east-1 ──┘      │ artifacts-444455556666-us-east-1 ──┘
  │   versioned; build artifacts,      │      │   versioned; build artifacts,      │
  │   Lambda ZIPs, promotion history   │      │   Lambda ZIPs, promotion history   │
  └────────────────────────────────────┘      └────────────────────────────────────┘

  One pair per ACCOUNT, not per namespace — every tenant namespace placed into the
  dev account shares that account's two buckets.
```

Why it is shaped this way:

- **`central-logging` is provisioned once per account, not once for the estate.** S3 server access
  logging requires the target bucket to be owned by the same AWS account as the source bucket and
  to sit in the same Region — AWS rejects a cross-account target outright. A single shared log
  bucket would therefore be unusable as an S3 access-log target for every account but its own. See
  [Constraint C-1](#constraints-and-platform-gaps).
- **`central-logging` does not log itself.** It is the target, not a source. Turning server access
  logging on for a log sink either loops it back onto itself or doubles the object count for no
  added signal.
- **`artifacts` is provisioned per dev/test account and is accessed only from within that
  account.** Its consumers — Lambda functions loading deployment packages, build pipelines
  publishing them — live alongside it, so the bucket policy carries no cross-account grants and the
  KMS key needs no external principals. Keeping it same-account is what makes the policy small
  enough to read.
- **`artifacts` is versioned; `central-logging` is not.** Artifact history is the point of the
  former — a bad deploy is rolled back by pointing at the previous object version. Log objects are
  write-once and are aged out by lifecycle rules instead.

The data team's pipeline ([KRO-1184](https://github.com/kropath/kropath-docs/pull/75)) is the first
consumer of both: its `file-process-bucket` logs into its account's `central-logging` bucket, and
its Lambda build pipeline ([KRO-1190](https://github.com/kropath/kropath-core/issues/1190))
publishes into that account's `artifacts` bucket.

## What you will accomplish

- Onboard the `platform-shared` namespace with its ACK cross-account annotations and local config CRs
- Provision `central-logging-<account_id>-<region>` in the platform-shared account, with a bucket
  policy that accepts log delivery from S3, ALB, and other AWS services
- Onboard a namespace per dev/test account and provision
  `artifacts-<account_id>-<region>` and that account's `central-logging` bucket
- Verify both bucket kinds in Kubernetes and in AWS

## Before you begin

You need:

- **Cluster access** — `kubectl` against the kropath management cluster, with permission to create
  namespaces and resources in them.
- **The target AWS accounts and Region.** This page uses the accounts in the table below and
  `us-east-1` throughout. Substitute your own.
- **A KMS key per account** for bucket encryption. This page references existing key ARNs; if you
  manage keys through kropath, create them first with
  [`KMSKey`](../aws/kms/kmskey.md) and reference the resulting ARN.
- **The `platform-global` governance namespace**, already present in the cluster. It holds the
  platform-wide baseline every resource namespace points at, and it deliberately carries **none**
  of the three placement annotations (ADR-019 D-5) — it is a governance namespace, not a placement
  target. Rendering it with placement annotations breaks the cascade.
- **Familiarity** with the [governance cascade](../engineering-standards.md#5-governance-config-hierarchy)
  and with how kropath derives resource names from naming templates.

### Account topology

Namespaces are named `<team>-<environment>` (KRO-1164) — the suffix names the AWS account the
namespace places into, so placement is readable from the name alone. `platform-shared` is the
exception to the pattern: `kropath-platform-shared` *is* the environment, and it is a placement
target as well as the identity account.

| Account | ID | Namespaces placed here | Buckets created here | Created from |
|---|---|---|---|---|
| shared | `999988887777` | `platform-shared` | `central-logging-999988887777-us-east-1` | `platform-shared` |
| dev | `111122223333` | `platform-dev`, `payments-dev`, `data-dev` | `central-logging-111122223333-us-east-1`, `artifacts-111122223333-us-east-1` | `platform-dev` |
| test | `444455556666` | `platform-test`, `payments-test`, `data-test` | `central-logging-444455556666-us-east-1`, `artifacts-444455556666-us-east-1` | `platform-test` |

**Create each bucket from exactly one namespace per account.** Several tenant namespaces place into
the same account, and `{account_id}` and `{region}` resolve identically in all of them — so an
`artifacts` CR in both `payments-dev` and `data-dev` would resolve to the same globally-unique
bucket name and the second would fail to create. The platform team's namespace in each environment
(`platform-dev`, `platform-test`) owns both buckets; tenants consume them by name.

### Naming: template versus `nameOverride`

The default S3 naming template is `{namespace}-{name}-{account_id}`, so an `S3Bucket` CR named
`artifacts` in namespace `platform-dev` would become `platform-dev-artifacts-111122223333`. The names
this foundation publishes are contracts other teams hard-code, so this task pins them with
`nameOverride` instead.

`nameOverride` is itself token-expanded before the name is used — `{account_id}`, `{region}`,
`{namespace}`, `{name}`, `{configRef}`, and `{tag.KEY}` are all substituted, and the result is
lower-cased. So:

```yaml
nameOverride: "artifacts-{account_id}-{region}"
```

resolves to `artifacts-111122223333-us-east-1` in the platform-dev account. Do **not** hard-code the
Region as a literal — `{region}` resolves from the effective config, which keeps one manifest
correct across Regions.

If a token cannot be resolved, the name keeps the literal `{token}` text and
`status.namingStatus` reports `invalid-unresolved-tokens`. Check that field first when a name
looks wrong.

## Constraints and platform gaps

Each is called out again at the step it affects.

| # | Constraint | Affects |
|---|---|---|
| C-1 | S3 server access logging requires the target bucket in the **same account and Region** as the source. AWS rejects a cross-account target. This is why `central-logging` is per account. | [Step 3](#step-3-create-the-central-logging-bucket), [Step 5](#step-5-create-the-artifacts-bucket) |
| C-2 | To centralize S3 access records across accounts anyway, server access logging is not the mechanism — use **CloudTrail S3 data events**, which do support a cross-account destination. Data events are billed per event, unlike server access logging, which is free apart from log storage. | [Step 3](#step-3-create-the-central-logging-bucket) |
| C-3 | `S3Bucket.spec.notification` has no EventBridge option. Not needed by this task, but it affects tenants that build on these buckets. | Tenant onboarding |
| C-4 | All three namespace annotations are required. A missing `owner-account-id` or `default-region` is a reconcile failure; a missing `global-config-namespace` silently makes the namespace resolve governance-only. None of them defaults (ADR-019 D-4/D-5, amended by KRO-1139). | [Step 1](#step-1-onboard-the-platform-shared-namespace), [Step 4](#step-4-onboard-each-product-account-namespace) |
| C-5 | Bucket names resolve per **account**, not per namespace, so two namespaces placed in the same account cannot both create the same bucket. | [Account topology](#account-topology) |

## Step 1: Onboard the platform-shared namespace

Create the namespace, its ACK cross-account annotations, and the local config CRs. Every config CR
must carry the `aws.kropath.run/resource-name` label — that label is how `externalRef` lookups
resolve the profile, and a config CR without it is invisible to the RGDs that need it.

```yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: platform-shared
  annotations:
    # All three are required on every resource namespace (ADR-019 §5.6/§5.8).
    # owner-account-id and default-region let ACK's CARM chain resolve the target
    # account; global-config-namespace points kropath-controller at the platform-global
    # baseline for the global tier.
    services.k8s.aws/owner-account-id: "999988887777"
    services.k8s.aws/default-region: "us-east-1"
    aws.kropath.run/global-config-namespace: platform-global

---
# Namespace-scoped platform configuration
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: baseline
  namespace: platform-shared
  labels:
    aws.kropath.run/resource-name: baseline
spec:
  mandatory:
    tags:
      team: platform
      cost-center: platform-engineering
      data-classification: internal
  defaults:
    tags:
      environment: production

---
# S3 governance for this namespace
apiVersion: aws.kropath.run/v1alpha1
kind: S3Config
metadata:
  name: general-policy
  namespace: platform-shared
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    encryptionAlgorithm: "aws:kms"
    blockPublicAccess: true
    enforceHttpsOnly: true
  defaults:
    kmsKeyArn: "arn:aws:kms:us-east-1:999988887777:key/11111111-2222-3333-4444-555555555555"
```

`aws.kropath.run/global-config-namespace: platform-global` is what makes the global tier of the
cascade resolve for this namespace. Omitting it is not a fallback to some default — the namespace
resolves governance-only, and the buckets below inherit nothing from the platform baseline. Confirm
all three annotations landed before moving on:

```bash
kubectl get ns platform-shared -o jsonpath='{.metadata.annotations}' | jq .
```

Because the `mandatory` tier wins over anything an instance sets, every bucket in this namespace
gets KMS encryption, public-access blocking, and a `DenyNonTLSAccess` bucket policy statement
whether or not its spec asks for them. Note that `versioning` is deliberately **not** in the
`defaults` tier here — the two bucket kinds want opposite answers, so each sets it explicitly.

Apply and confirm:

```bash
kubectl apply -f platform-shared-namespace.yaml
kubectl get ns platform-shared
kubectl get kropathconfig baseline -n platform-shared
kubectl get s3config general-policy -n platform-shared
```

Create the remaining family configs the same way for any other resource family this namespace will
hold — each named `general-policy` and each carrying the
`aws.kropath.run/resource-name: general-policy` label. A resource whose `configRef` names a profile
that does not exist falls back to `general-policy`; if that is missing too, the RGD cannot resolve
its effective config and the resource never becomes ready.

## Step 2: Define the central-logging bucket policy

`central-logging` is a delivery target, so its bucket policy is the substance of the resource: it
has to let AWS services in this account write into it while keeping everyone else out. Express it
as a `PolicyDocument` rather than raw JSON so the statements are validated at apply time and can be
composed from reusable sources.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: central-logging-policy
  namespace: platform-shared
spec:
  statements:
    # S3 server access logging from buckets in this account
    - sid: AllowS3ServerAccessLogDelivery
      effect: Allow
      principals:
        - type: Service
          arn: "logging.s3.amazonaws.com"
      actions:
        - "s3:PutObject"
      resources:
        - arn: "arn:aws:s3:::central-logging-999988887777-us-east-1/s3/*"
      conditions:
        - operator: StringEquals
          key: "aws:SourceAccount"
          values: ["999988887777"]

    # ALB / ELB access logs
    - sid: AllowALBAccessLogDelivery
      effect: Allow
      principals:
        - type: Service
          arn: "logdelivery.elasticloadbalancing.amazonaws.com"
      actions:
        - "s3:PutObject"
      resources:
        - arn: "arn:aws:s3:::central-logging-999988887777-us-east-1/alb/*"
      conditions:
        - operator: StringEquals
          key: "s3:x-amz-acl"
          values: ["bucket-owner-full-control"]

    # CloudTrail trail delivery
    - sid: AllowCloudTrailDelivery
      effect: Allow
      principals:
        - type: Service
          arn: "cloudtrail.amazonaws.com"
      actions:
        - "s3:PutObject"
      resources:
        - arn: "arn:aws:s3:::central-logging-999988887777-us-east-1/cloudtrail/*"
      conditions:
        - operator: StringEquals
          key: "s3:x-amz-acl"
          values: ["bucket-owner-full-control"]
    - sid: AllowCloudTrailBucketAcl
      effect: Allow
      principals:
        - type: Service
          arn: "cloudtrail.amazonaws.com"
      actions:
        - "s3:GetBucketAcl"
      resources:
        - arn: "arn:aws:s3:::central-logging-999988887777-us-east-1"
```

Each source writes under its own prefix, which is what makes lifecycle rules in Step 3 able to age
log classes at different rates.

**On TLS enforcement.** You do not add a `DenyNonTLSAccess` statement here. The `S3Bucket` RGD
splices that statement into the front of the resolved policy document whenever `enforceHttpsOnly`
is in effect, so the mandatory tier from Step 1 and this `PolicyDocument` compose rather than
conflict.

> **Verify before relying on this in production.** [AWS S3 Buckets](../aws/s3/s3.md#https-enforcement)
> currently documents Phase-1 behaviour in which `enforceHttpsOnly` owns `spec.policy` outright and
> conflicts with `bucketPolicyRef`. The RGD's `bucketWithUserPolicy*` variants do compose the two,
> so that note appears stale — confirm against your deployed RGD version, and check the rendered
> policy with `aws s3api get-bucket-policy` after Step 4.

**Cross-account delivery (optional).** Services whose log delivery does support a cross-account
destination — ALB and CloudTrail among them — can additionally target the platform-shared
`central-logging` bucket if you want estate-wide aggregation. Add the delivering account to
`aws:SourceAccount` in the relevant statement. S3 server access logging cannot do this (C-1); use
CloudTrail S3 data events instead, at the per-event cost noted in C-2.

## Step 3: Create the central-logging bucket

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: central-logging
  namespace: platform-shared
spec:
  configRef: general-policy
  nameOverride: "central-logging-{account_id}-{region}"
  deletionPolicy: retain

  # Enforced by the mandatory tier; repeated for clarity
  encryption:
    algorithm: "aws:kms"
    kmsKeyArn: "arn:aws:kms:us-east-1:999988887777:key/11111111-2222-3333-4444-555555555555"
    bucketKeyEnabled: true
  blockPublicAccess: true
  enforceHttpsOnly: true

  # A log sink keeps one copy of each write-once object
  versioning: "Suspended"

  # The log delivery grants from Step 2
  bucketPolicyRef: central-logging-policy

  # No spec.logging: this bucket is the target, not a source. See C-1.

  lifecycle:
    - id: age-out-s3-access-logs
      status: Enabled
      filter:
        prefix: "s3/"
      transitions:
        - days: 30
          storageClass: STANDARD_IA
        - days: 90
          storageClass: GLACIER_IR
      expiration:
        days: 365
    - id: age-out-alb-logs
      status: Enabled
      filter:
        prefix: "alb/"
      transitions:
        - days: 30
          storageClass: STANDARD_IA
      expiration:
        days: 365
    - id: age-out-cloudtrail-logs
      status: Enabled
      filter:
        prefix: "cloudtrail/"
      transitions:
        - days: 90
          storageClass: GLACIER_IR
      expiration:
        days: 2555   # 7 years, typical audit retention
    - id: abort-stalled-uploads
      status: Enabled
      abortIncompleteMultipartUpload:
        daysAfterInitiation: 7

  tags:
    purpose: central-logging
```

`bucketKeyEnabled: true` matters more here than anywhere else in this task — a log sink takes a
very large number of small `PutObject` calls, and S3 Bucket Keys collapse the per-object KMS
requests those would otherwise generate.

Apply it:

```bash
kubectl apply -f central-logging-bucket.yaml
```

## Step 4: Onboard each product account namespace

Repeat Step 1 for each dev/test account, changing the namespace name and the owner account
annotation. The config CRs are otherwise identical apart from the account-local KMS key:

```yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: platform-dev
  annotations:
    services.k8s.aws/owner-account-id: "111122223333"
    services.k8s.aws/default-region: "us-east-1"
    aws.kropath.run/global-config-namespace: platform-global

---
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: baseline
  namespace: platform-dev
  labels:
    aws.kropath.run/resource-name: baseline
spec:
  mandatory:
    tags:
      team: platform
      cost-center: platform-engineering
      environment: dev
  defaults:
    tags:
      data-classification: internal

---
apiVersion: aws.kropath.run/v1alpha1
kind: S3Config
metadata:
  name: general-policy
  namespace: platform-dev
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    encryptionAlgorithm: "aws:kms"
    blockPublicAccess: true
    enforceHttpsOnly: true
  defaults:
    kmsKeyArn: "arn:aws:kms:us-east-1:111122223333:key/22222222-3333-4444-5555-666666666666"
```

Then create this account's `central-logging` bucket with the manifests from Steps 2 and 3,
substituting `111122223333` for `999988887777` in the namespace, the policy resource ARNs, the
`aws:SourceAccount` condition, and the KMS key ARN. The `nameOverride` template needs no change —
`{account_id}` and `{region}` resolve per namespace.

Repeat for `platform-test` with `444455556666`.

## Step 5: Create the artifacts bucket

One per dev/test account. Unlike `central-logging`, this bucket is a source of access logs
rather than a target, and it carries no bucket policy of its own — the `DenyNonTLSAccess` statement
from the mandatory tier is the whole policy, because every consumer lives in this same account and
is authorized through its own IAM role.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: artifacts
  namespace: platform-dev
spec:
  configRef: general-policy
  nameOverride: "artifacts-{account_id}-{region}"
  deletionPolicy: retain

  encryption:
    algorithm: "aws:kms"
    kmsKeyArn: "arn:aws:kms:us-east-1:111122223333:key/22222222-3333-4444-5555-666666666666"
    bucketKeyEnabled: true
  blockPublicAccess: true
  enforceHttpsOnly: true

  # Artifact history is the point: rollback means reading a previous object version
  versioning: "Enabled"

  # Server access logging into this account's own log sink (C-1)
  logging:
    enabled: true
    targetBucket: "central-logging-111122223333-us-east-1"
    targetPrefix: "s3/artifacts/"

  lifecycle:
    - id: expire-old-artifact-versions
      status: Enabled
      noncurrentVersionExpiration:
        noncurrentDays: 90
      noncurrentVersionTransitions:
        - noncurrentDays: 30
          storageClass: STANDARD_IA
    - id: clean-expired-delete-markers
      status: Enabled
      expiration:
        expiredObjectDeleteMarker: true
    - id: abort-stalled-uploads
      status: Enabled
      abortIncompleteMultipartUpload:
        daysAfterInitiation: 7

  tags:
    purpose: artifacts
```

`targetBucket` names this account's own `central-logging` bucket. Pointing it at the
platform-shared one is rejected by AWS (C-1), and the failure surfaces as a reconcile error on the
bucket rather than as silently missing logs.

There is no `expiration.days` rule on current versions: an artifact that is still the current
object is still deployable, and expiring it would break rollback for any long-lived release. Only
superseded versions age out.

Apply:

```bash
kubectl apply -f artifacts-bucket.yaml
kubectl get s3bucket -n platform-dev
```

## Step 6: Verify in Kubernetes

```bash
kubectl get s3bucket -n platform-shared
kubectl get s3bucket -n platform-dev
kubectl describe s3bucket artifacts -n platform-dev
```

Check three things in the output:

- `status.namingStatus` is `valid`. Anything else means a naming token did not resolve, and the
  bucket name still contains literal `{...}` text.
- `status.resourceName` and `status.predictedArn` match the names in the topology table.
- The ACK-managed `Bucket` behind the instance reports `ACK.Synced: True`. The kro instance
  reaching `ACTIVE` means the RGD rendered its resources, not that AWS accepted them — check the
  child resource too:

```bash
kubectl get buckets.s3.services.k8s.aws -n platform-dev -o wide
kubectl describe buckets.s3.services.k8s.aws -n platform-dev artifacts-111122223333-us-east-1
```

If a bucket is stuck, the ACK S3 controller's log is the place to look. The controller is
per-service, so select it by name:

```bash
kubectl get pods -n ack-system | grep s3
kubectl logs -n ack-system <ack-s3-controller-pod> --tail=100
```

## Step 7: Verify in AWS

Run these against the account that owns each bucket.

```bash
BUCKET=artifacts-111122223333-us-east-1

# Exists
aws s3api head-bucket --bucket "$BUCKET"

# Encryption: SSEAlgorithm aws:kms, BucketKeyEnabled true
aws s3api get-bucket-encryption --bucket "$BUCKET"

# Public access: all four flags true
aws s3api get-public-access-block --bucket "$BUCKET"

# Versioning: Enabled on artifacts, Suspended on central-logging
aws s3api get-bucket-versioning --bucket "$BUCKET"

# Access logging: target is this account's central-logging bucket
aws s3api get-bucket-logging --bucket "$BUCKET"

# Lifecycle: the rules from the spec, all Enabled
aws s3api get-bucket-lifecycle-configuration --bucket "$BUCKET"

# Policy: DenyNonTLSAccess present
aws s3api get-bucket-policy --bucket "$BUCKET" --query Policy --output text | jq .
```

For the log sink, confirm the delivery grants composed with the TLS denial:

```bash
aws s3api get-bucket-policy \
  --bucket central-logging-999988887777-us-east-1 \
  --query Policy --output text | jq '.Statement[].Sid'
```

Expected: `DenyNonTLSAccess` alongside `AllowS3ServerAccessLogDelivery`,
`AllowALBAccessLogDelivery`, `AllowCloudTrailDelivery`, and `AllowCloudTrailBucketAcl`. If only
`DenyNonTLSAccess` appears, `bucketPolicyRef` did not resolve — see Troubleshooting.

End-to-end check that logging actually flows, after allowing for S3's delivery delay (often hours,
not minutes):

```bash
echo test | aws s3 cp - "s3://artifacts-111122223333-us-east-1/verify/probe.txt"
aws s3 ls "s3://central-logging-111122223333-us-east-1/s3/artifacts/"
```

## Troubleshooting

### `status.namingStatus: invalid-unresolved-tokens`

A token in `nameOverride` could not be resolved. `{account_id}` and `{region}` come from
`status.effectiveConfig.aws` on the namespace's `S3Config`, which the kropath-controller populates
from the namespace annotations. Confirm the annotations exist and the config CR carries its
`aws.kropath.run/resource-name` label:

```bash
kubectl get ns platform-dev -o jsonpath='{.metadata.annotations}' | jq .
kubectl get s3config general-policy -n platform-dev -o jsonpath='{.status.effectiveConfig.aws}' | jq .
```

### The bucket policy contains only `DenyNonTLSAccess`

`bucketPolicyRef` resolves the `PolicyDocument` by label in the same namespace, and references are
same-namespace only. Check that the document exists beside the bucket and that it resolved:

```bash
kubectl get policydocument central-logging-policy -n platform-shared
kubectl get policydocument central-logging-policy -n platform-shared \
  -o jsonpath='{.status.resolvedDocumentJSON}' | jq .
```

An empty `resolvedDocumentJSON` means the document itself failed validation — its own status
conditions carry the reason.

### Access logs never appear in central-logging

In order of likelihood:

1. **Cross-account target.** `targetBucket` must be in the same account and Region as the source
   (C-1). Compare the two account IDs.
2. **Delivery delay.** S3 delivers access logs on a best-effort basis, typically within a few
   hours. Do not conclude failure from a check minutes after the probe.
3. **Missing delivery grant.** The target's policy needs the `logging.s3.amazonaws.com` statement
   from Step 2, with `aws:SourceAccount` matching the source account.
4. **KMS.** If the target uses SSE-KMS, its key policy must allow the S3 log delivery service to
   encrypt. A key created outside kropath may not have this.

### The bucket exists in Kubernetes but not in AWS

Check the bucket ARN in `status` for the account and Region actually used, then confirm
`services.k8s.aws/owner-account-id` on the namespace matches the account you are looking in. A
namespace annotated for the wrong account creates real buckets — just somewhere else.

## Next steps

Once both bucket kinds exist and verify:

1. **Onboard the first tenant.** [Onboard the data-team namespace and its file-processing
   resources](onboard-data-team-namespace-and-resources.md) builds on this foundation.
2. **Point existing buckets at the log sink.** Any bucket already in these accounts can set
   `spec.logging` to its account's `central-logging` bucket.
3. **Publish the contract.** Other teams hard-code these bucket names. Record them, and the prefix
   convention from Step 2, wherever your teams look for platform interfaces.

## Reference

This task is sub-issue 1 of the platform-shared onboarding story,
[KRO-1176](https://github.com/kropath/kropath-core/issues/1176). The steps here are the
documentation counterpart of:

| Sub-issue | Ticket |
|---|---|
| Onboard namespace (Steps 1 and 4) | [KRO-1178](https://github.com/kropath/kropath-core/issues/1178) |
| Create resources (Steps 2, 3, and 5) | [KRO-1183](https://github.com/kropath/kropath-core/issues/1183) |
| Verify in AWS (Steps 6 and 7) | [KRO-1179](https://github.com/kropath/kropath-core/issues/1179) |
| Namespace onboarding template | [KRO-1175](https://github.com/kropath/kropath-core/issues/1175) |

Field-by-field reference material:

- [AWS S3 Buckets](../aws/s3/s3.md) — `S3Bucket` fields, the
  [`S3Config` governance model](../aws/s3/s3.md#s3config-governance-model), and the ten-tier cascade
- [PolicyDocument](../resources/aws-policy-document.md) — structured statements, service
  principals, conditions, and source composition
- [KMSKey](../aws/kms/kmskey.md) — key provisioning and key policies
- [Dynamic tag fields in naming templates](../resources/naming-template-dynamic-tags.md)
- [Engineering standards](../engineering-standards.md) — governance cascade and wiring conventions

For design and governance details, see these references in kropath-core:

- **ADR-019** — cross-account resource management (annotations, role configuration)
- **ADR-015 §5.3** — governance cascade for S3 configuration
- **ADR-010** — kropath-controller effective-config cascade
