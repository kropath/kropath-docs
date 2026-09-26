---
doc_type: task
title: Onboard the platform-shared namespace and its shared buckets
linkTitle: Onboard the platform-shared namespace
description: "The platform team needs one shared namespace per account so every other tenant has a consistent place to onboard from, and a working `central-logging` and `artifacts` bucket pair to build on."
weight: 10
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

```text
  shared account (999988887777)                 ns: platform-shared
  ┌──────────────────────────────────────────────┐
  │  central-logging-999988887777-us-east-1      │  ← log sink for this account
  │    ← S3 server access logs (same account)    │
  │    ← ALB / ELB access logs                   │
  │    ← other AWS service log delivery          │
  └──────────────────────────────────────────────┘

  product-dev account (111122223333)          product-test account (444455556666)
  ns: shared-product-dev  (+ BU namespaces)   ns: shared-product-test  (+ BU namespaces)
  ┌────────────────────────────────────┐      ┌────────────────────────────────────┐
  │ central-logging-111122223333-…     │      │ central-logging-444455556666-…     │
  │   ▲ server access logs             │      │   ▲ server access logs             │
  │   │                                │      │   │                                │
  │ artifacts-111122223333-us-east-1 ──┘      │ artifacts-444455556666-us-east-1 ──┘
  │   versioned; build artifacts,      │      │   versioned; build artifacts,      │
  │   Lambda ZIPs, promotion history   │      │   Lambda ZIPs, promotion history   │
  └────────────────────────────────────┘      └────────────────────────────────────┘

  Both buckets are owned by the PLATFORM TEAM and created from its shared-services
  namespace in each account. Business-unit namespaces in the same account create
  neither — they consume both by name.
```

Why it is shaped this way:

- **`central-logging` is provisioned once per account, not once for the estate.** S3 server access
  logging requires the target bucket to be owned by the same AWS account as the source bucket and
  to sit in the same Region — AWS rejects a cross-account target outright. A single shared log
  bucket would therefore be unusable as an S3 access-log target for every account but its own. See
  [Constraint C-1](#aws-constraints-that-shape-this-design).
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

The [data-team file-processing pipeline](../data-processing/onboard-data-team-namespace-and-resources.md) is the first
consumer of both: its bucket logs into its account's `central-logging` bucket, and its Lambda build
pipeline publishes into that account's `artifacts` bucket.

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
- **The `platform-global` governance namespace**, already present in the cluster. It holds the
  platform-wide baseline every resource namespace points at, and it deliberately carries **none**
  of the three placement annotations — it is a governance namespace, not a placement target.
  Giving it placement annotations breaks the cascade.
- **Familiarity** with the [governance cascade](../../reference/aws/s3/_index.md#ten-tier-governance-cascade)
  and with how kropath derives resource names from naming templates.

### Account topology

A namespace name carries its owner and the account it places into, so placement and ownership are
both readable from the name alone. The platform team's shared-services namespaces are
`platform-shared` in the identity account and `shared-product-<environment>` in each product
account. Business-unit namespaces alongside them are named for the business unit — `payments-dev`,
`data-dev` — not for a team; the group that operates a business unit's resources is not necessarily
a team of that name.

| Account | ID | Platform-team namespace | Buckets created here |
|---|---|---|---|
| platform-shared | `999988887777` | `platform-shared` | `central-logging-999988887777-us-east-1` |
| product-dev | `111122223333` | `shared-product-dev` | `central-logging-111122223333-us-east-1`, `artifacts-111122223333-us-east-1` |
| product-test | `444455556666` | `shared-product-test` | `central-logging-444455556666-us-east-1`, `artifacts-444455556666-us-east-1` |

Business-unit namespaces — `payments-dev`, `data-dev`, and their `-test` counterparts — place into
the same product accounts but **create neither bucket**. Both are platform-team-owned shared
services that happen to be deployed into the product accounts; business units consume them by name.

**Why ownership has to be explicit.** Bucket names resolve per account: `{account_id}` and
`{region}` expand identically in every namespace placed into the same account. If two namespaces in
one account both carried an `artifacts` CR, both would resolve to the same globally-unique bucket
name and the second would fail to create. Confining both CRs to the platform team's shared-services
namespace is what makes that situation impossible rather than merely unlikely.

### Naming: template versus `nameOverride`

The default S3 naming template is `{namespace}-{name}-{account_id}`, so an `S3Bucket` CR named
`artifacts` in namespace `shared-product-dev` would become `shared-product-dev-artifacts-111122223333`. The names
this foundation publishes are contracts other teams hard-code, so this task pins them with
`nameOverride` instead.

`nameOverride` is itself token-expanded before the name is used — `{account_id}`, `{region}`,
`{namespace}`, `{name}`, `{configRef}`, and `{tag.KEY}` are all substituted, and the result is
lower-cased. So:

```yaml
nameOverride: "artifacts-{account_id}-{region}"
```

resolves to `artifacts-111122223333-us-east-1` in the product-dev account. Do **not** hard-code the
Region as a literal — `{region}` resolves from the effective config, which keeps one manifest
correct across Regions.

If a token cannot be resolved, the name keeps the literal `{token}` text and
`status.namingStatus` reports `invalid-unresolved-tokens`. Check that field first when a name
looks wrong.

## AWS constraints that shape this design

Two AWS behaviours determine the topology above. Both are AWS platform behaviour, not kropath
limitations, and neither can be configured away. Each is restated at the step it affects.

| # | Constraint | Affects |
|---|---|---|
| C-1 | S3 server access logging requires the target bucket to be owned by the **same AWS account** as the source bucket and to be in the **same Region**. AWS rejects a cross-account target. This is why `central-logging` is provisioned per account. | [Step 3](#step-3-create-the-central-logging-bucket), [Step 5](#step-5-create-the-artifacts-bucket) |
| C-2 | Because of C-1, server access logging cannot centralize S3 access records across accounts. The mechanism that can is **CloudTrail S3 data events**, which do support a cross-account destination — at a per-event charge, where server access logging is free apart from the storage its logs consume. | [Step 3](#step-3-create-the-central-logging-bucket) |

## Step 1: Onboard the platform-shared namespace

Create the namespace, its ACK cross-account annotations, and the local config CRs. Every config CR
must carry the `aws.kropath.run/resource-name` label — that label is how `externalRef` lookups
resolve the profile, and a config CR without it is invisible to the resources that need it.

```yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: platform-shared
  annotations:
    # All three are required on every resource namespace. owner-account-id and
    # default-region let ACK's CARM chain resolve the target account;
    # global-config-namespace points kropath at the platform-global
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
that does not exist falls back to `general-policy`; if that is missing too, the effective config
cannot be resolved and the resource never becomes ready.

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

**On TLS enforcement.** You do not add a `DenyNonTLSAccess` statement here. When
`enforceHttpsOnly` is in effect, kropath prepends that statement to the resolved policy document,
so the mandatory tier from Step 1 and this `PolicyDocument` compose rather than replace one
another. Confirm the composed result with `aws s3api get-bucket-policy` after Step 3 — the
verification in [Step 7](#step-7-verify-in-aws) does exactly that.

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
    # Omitting kmsKeyArn uses the AWS managed key for S3 (aws/s3) — no key to
    # create, rotate, or pay for. Set kmsKeyArn to use a customer managed key.
    algorithm: "aws:kms"
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

## Step 4: Onboard the shared-services namespace in each product account

Repeat Step 1 for the platform team's shared-services namespace in each product account, changing
the namespace name and the owner account annotation. Business-unit namespaces in the same account
are onboarded separately by their own teams and are not part of this task. The config CRs are
otherwise identical apart from the account-local KMS key:

```yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: shared-product-dev
  annotations:
    services.k8s.aws/owner-account-id: "111122223333"
    services.k8s.aws/default-region: "us-east-1"
    aws.kropath.run/global-config-namespace: platform-global

---
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: baseline
  namespace: shared-product-dev
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
  namespace: shared-product-dev
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    encryptionAlgorithm: "aws:kms"
    blockPublicAccess: true
    enforceHttpsOnly: true
```

Then create this account's `central-logging` bucket with the manifests from Steps 2 and 3,
substituting `111122223333` for `999988887777` in the namespace, the policy resource ARNs, the
`aws:SourceAccount` condition, and the KMS key ARN. The `nameOverride` template needs no change —
`{account_id}` and `{region}` resolve per namespace.

Repeat for `shared-product-test` in the product-test account, `444455556666`.

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
  namespace: shared-product-dev
spec:
  configRef: general-policy
  nameOverride: "artifacts-{account_id}-{region}"
  deletionPolicy: retain

  encryption:
    # Omitting kmsKeyArn uses the AWS managed key for S3 (aws/s3) — no key to
    # create, rotate, or pay for. Set kmsKeyArn to use a customer managed key.
    algorithm: "aws:kms"
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
kubectl get s3bucket -n shared-product-dev
```

## Step 6: Verify in Kubernetes

```bash
kubectl get s3bucket -n platform-shared
kubectl get s3bucket -n shared-product-dev
kubectl describe s3bucket artifacts -n shared-product-dev
```

Check three things in the output:

- `status.namingStatus` is `valid`. Anything else means a naming token did not resolve, and the
  bucket name still contains literal `{...}` text.
- `status.resourceName` and `status.predictedArn` match the names in the topology table.
- The ACK-managed `Bucket` behind the instance reports `ACK.Synced: True`. The kro instance
  reaching `ACTIVE` means kropath rendered the underlying resources, not that AWS accepted them —
  check the child resource too:

```bash
kubectl get buckets.s3.services.k8s.aws -n shared-product-dev -o wide
kubectl describe buckets.s3.services.k8s.aws -n shared-product-dev artifacts-111122223333-us-east-1
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
`status.effectiveConfig.aws` on the namespace's `S3Config`, which kropath populates from the
namespace annotations. Confirm the annotations exist and the config CR carries its
`aws.kropath.run/resource-name` label:

```bash
kubectl get ns shared-product-dev -o jsonpath='{.metadata.annotations}' | jq .
kubectl get s3config general-policy -n shared-product-dev -o jsonpath='{.status.effectiveConfig.aws}' | jq .
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
   resources](../data-processing/onboard-data-team-namespace-and-resources.md) builds on this foundation.
2. **Point existing buckets at the log sink.** Any bucket already in these accounts can set
   `spec.logging` to its account's `central-logging` bucket.
3. **Publish the contract.** Other teams hard-code these bucket names. Record them, and the prefix
   convention from Step 2, wherever your teams look for platform interfaces.

## Reference

Field-by-field reference material:

- [AWS S3 Buckets](../../reference/aws/s3/_index.md) — `S3Bucket` fields, the
  [`S3Config` governance model](../../reference/aws/s3/_index.md#s3config-governance-model), and the governance
  cascade
- [PolicyDocument](../../concepts/configuration/policy-documents.md) — structured statements, service
  principals, conditions, and source composition
- [KMSKey](../../reference/aws/kms/kmskey.md) — provisioning a customer managed key, if you choose one over the
  AWS managed key this task uses
- [Dynamic tag fields in naming templates](../../concepts/configuration/naming-templates.md)
- [How kropath resolves your configuration](../../concepts/architecture/_index.md) — how governance
  CRs, the controller, and the provider layer combine to produce a cloud resource

Related tasks:

- [Onboard the data-team namespace and its file-processing resources](../data-processing/onboard-data-team-namespace-and-resources.md)
  — the first tenant to build on this foundation

External references:

- [AWS: logging requests with server access logging](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ServerLogs.html)
  — including the same-account, same-Region requirement behind C-1
- [AWS: logging data events with CloudTrail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-data-events-with-cloudtrail.html)
- [AWS: S3 Bucket Keys](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-key.html)
- [ACK: cross-account resource management (CARM)](https://aws-controllers-k8s.github.io/community/docs/user-docs/cross-account-resource-management/)
- [kro: ResourceGraphDefinition](https://kro.run/docs/concepts/resource-group-definitions)
