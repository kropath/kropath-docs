---
doc_type: task
title: Onboard the data-team namespace and its file-processing resources
---

# Onboard the data-team namespace and its file-processing resources

**Document type:** Task — this page walks you through one concrete goal in a sequence of steps. It
is not a concept page or a tutorial. For field-by-field reference material, follow the links in
[Reference](#reference).

## The business case

The data team runs a **file-processing data flow**. An upstream service, `data-service1`, writes its
output into an S3 bucket. Every file that lands there has to be picked up, recorded for downstream
systems, and announced to other teams — without anyone watching a console.

The flow this task builds:

```
data-service1 writes  s3://file-process-bucket/data-service1/output/*.json
        │
        ▼  S3 sends the object-created event to EventBridge
EventBridge rule  (matches data-service1/output/*)
        │
        ▼  invokes
file-process-lambda  (TypeScript)
        ├──▶ sends a message to SQS  file-process-message-queue   → downstream processing
        ├──▶ writes a log line
        ├──▶ publishes a notification to SNS  file-process-sns-topic  → other teams subscribe
        └──▶ writes a log line
                 all logs → CloudWatch log group /aws/lambda/file-process-lambda
```

Why it is shaped this way:

- **SQS** gives downstream systems a durable, replayable work queue. If a consumer is down, the
  message waits instead of being lost.
- **SNS** lets other teams subscribe to the same event without the data team having to know who they
  are, or coupling anyone to the Lambda.
- **EventBridge** sits between S3 and the Lambda so that the routing rule — *which* key prefixes
  matter — is configuration rather than code, and so more consumers can be added later without
  touching the bucket.
- **CloudWatch Logs** makes the run observable: each stage writes a log line, so a failed file can
  be traced to the step that dropped it.

This is the data team's slice of the kropath golden path. It sits on top of the platform-shared
namespace foundation ([KRO-1176](https://github.com/kropath/kropath-core/issues/1176)), which
supplies the central-logging bucket and the artifacts bucket the Lambda build pipeline publishes to.

## What you will accomplish

- Onboard the `data-team` namespace with its local `KropathConfig` and family config CRs
- Provision the pipeline resources: S3 bucket, SQS queue, SNS topic, CloudWatch log group,
  EventBridge rule, Lambda function, and a least-privilege IAM role
- Wire the S3 → EventBridge → Lambda → SQS/SNS chain
- Verify the chain end to end by dropping a file in the bucket

## Before you begin

You need:

- **Cluster access** — `kubectl` against the kropath management cluster, with permission to create
  resources in a new namespace.
- **A target AWS account and region.** This page uses account `111122223333` and `ap-southeast-2`.
  Substitute your own.
- **The platform-shared foundation** from [KRO-1176](https://github.com/kropath/kropath-core/issues/1176).
  The platform team owns these buckets, but they are provisioned **into each product account**, not
  into a single shared account: `central-logging-<account_id>-<region>` and
  `artifacts-<account_id>-<region>` exist on every product-dev and product-test account. For this
  page that means `central-logging-111122223333-ap-southeast-2` and `artifacts-111122223333-ap-southeast-2`.
- **The Lambda artifact.** `file-process-lambda` is built from TypeScript by the pipeline in
  [KRO-1190](https://github.com/kropath/kropath-core/issues/1190), which uploads the ZIP to the
  **dev account's** artifacts bucket and promotes that same artifact to the **test account's**
  bucket on merge. Either way the bucket the function reads from is in the function's own account.
  The artifact must exist before Step 7 — a `LambdaFunction` whose code source points at a missing
  key reconciles into an error, and one pointed at an empty placeholder reports `Ready` while
  running no real code.
- **Familiarity** with the [governance cascade](../engineering-standards.md#5-governance-config-hierarchy)
  and with how kropath derives resource names from naming templates.

### Naming: template versus `nameOverride`

Every kropath resource family derives its AWS name from a naming template — by default
`{namespace}-{name}`, and `{namespace}-{name}-{account_id}` for S3 buckets. A CR named
`file-process-bucket` in namespace `data-team` would therefore become
`data-team-file-process-bucket-111122223333`.

This task uses `nameOverride` on each resource so the AWS names match the names the business flow
above specifies exactly, and so every ARN on this page is easy to follow. **Prefer the template on
resources you are not required to name exactly** — it keeps names collision-free across namespaces,
which matters most for S3, whose bucket names are globally unique across all AWS accounts.

The names this task produces:

| Resource | Kind | AWS name |
|---|---|---|
| Bucket | `S3Bucket` | `file-process-bucket` |
| Queue | `SQSQueue` | `file-process-message-queue` |
| Topic | `SNSTopic` | `file-process-sns-topic` |
| Log group | `CloudWatchLogsLogGroup` | `/aws/lambda/file-process-lambda` |
| Rule | `EventBridgeRule` | `file-process-rule` |
| Function | `LambdaFunction` | `file-process-lambda` |
| Execution role | `IAMRole` | `file-process-lambda-role` |
| EventBridge invoke role | `IAMRole` | `file-process-eventbridge-role` |

## Known platform gaps

Three parts of this flow cannot be expressed in kropath-aws today. Each is called out again at the
step it affects, with the supported workaround. They are tracked under
[KRO-1188](https://github.com/kropath/kropath-core/issues/1188).

| # | Gap | Affects |
|---|---|---|
| G-1 | `S3Bucket.spec.notification` has no EventBridge option — only `lambdaConfigurations`, `sqsConfigurations`, and `snsConfigurations` | [Step 2](#step-2-create-the-s3-bucket) |
| G-2 | `LambdaFunction` has no `environment` field, so the queue URL and topic ARN cannot be injected as environment variables | [Step 7](#step-7-deploy-the-lambda-function) |
| G-3 | There is no `LambdaPermission` resource, so EventBridge → Lambda invoke permission must come from the target's `roleARN` rather than a resource-based policy | [Step 8](#step-8-let-eventbridge-invoke-the-lambda) |

## Step 1: Onboard the namespace

Create the namespace, its ACK cross-account annotations, and the local config CRs. Every config CR
carries the `aws.kropath.run/resource-name` label — that label is how `externalRef` lookups resolve
the profile, and a config CR without it is invisible to the RGDs that need it.

```yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: data-team
  annotations:
    # ACK cross-account resource management (ADR-019 D-1/D-4)
    services.k8s.aws/owner-account-id: "111122223333"
    services.k8s.aws/default-region: "ap-southeast-2"

---
# Namespace-scoped platform configuration
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: baseline
  namespace: data-team
  labels:
    aws.kropath.run/resource-name: baseline
spec:
  mandatory:
    tags:
      team: data-team
      cost-center: data-platform
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
  namespace: data-team
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    encryptionAlgorithm: "aws:kms"
    blockPublicAccess: true
    enforceHttpsOnly: true
  defaults:
    versioning: "Enabled"
    kmsKeyArn: "arn:aws:kms:ap-southeast-2:111122223333:key/11111111-2222-3333-4444-555555555555"
```

Create the remaining family configs the same way — `SQSConfig`, `SNSConfig`, `CloudWatchLogsConfig`,
`EventBridgeConfig`, `LambdaConfig`, and `IAMConfig`, each named `general-policy` and each carrying
the `aws.kropath.run/resource-name: general-policy` label. A resource whose `configRef` names a
profile that does not exist falls back to `general-policy`; if that is missing too, the RGD cannot
resolve its effective config and the resource never becomes ready.

Apply and confirm:

```bash
kubectl apply -f namespace-and-configs.yaml
kubectl get ns data-team
kubectl get kropathconfig baseline -n data-team
kubectl get s3config general-policy -n data-team
```

> The mandatory tier wins over anything an instance sets. Because `general-policy` mandates
> `encryptionAlgorithm: "aws:kms"`, `blockPublicAccess: true`, and `enforceHttpsOnly: true`, every
> bucket in this namespace gets KMS encryption, public-access blocking, and a `DenyNonTLSAccess`
> bucket policy whether or not the bucket spec asks for them.

## Step 2: Create the S3 bucket

The bucket that `data-service1` writes into. Encryption, public-access blocking, and TLS
enforcement come from the mandatory tier in Step 1 — they are shown here explicitly only so the
manifest reads as a complete statement of intent.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: file-process
  namespace: data-team
spec:
  configRef: general-policy
  nameOverride: file-process-bucket
  deletionPolicy: retain
  region: ap-southeast-2   # required outside us-east-1 (sets locationConstraint)

  # Enforced by the mandatory tier; repeated for clarity
  encryption:
    algorithm: "aws:kms"
    kmsKeyArn: "arn:aws:kms:ap-southeast-2:111122223333:key/11111111-2222-3333-4444-555555555555"
    bucketKeyEnabled: true
  blockPublicAccess: true
  enforceHttpsOnly: true
  versioning: "Enabled"

  # Server access logging
  logging:
    enabled: true
    targetBucket: "central-logging-111122223333-ap-southeast-2"
    targetPrefix: "file-process-bucket/"

  # Lifecycle: expire raw input after 90 days, clean up old versions and failed uploads
  lifecycle:
    - id: expire-processed-input
      status: Enabled
      filter:
        prefix: "data-service1/output/"
      transitions:
        - days: 30
          storageClass: STANDARD_IA
      expiration:
        days: 90
      noncurrentVersionExpiration:
        noncurrentDays: 30
      abortIncompleteMultipartUpload:
        daysAfterInitiation: 7

  tags:
    data-pipeline: file-process
```

`spec.region` must be set for every region except `us-east-1`, where it has to be omitted — AWS
rejects a `locationConstraint` of `us-east-1`. See
[Region Handling](../aws/s3/s3.md#region-handling-the-us-east-1-special-case).

Note that `enforceHttpsOnly` currently writes the `DenyNonTLSAccess` statement straight into the
bucket policy field, so kropath owns that field outright — do not attach another bucket policy to
this bucket until the `bucketPolicyRef` composition work lands. See
[AWS S3 Buckets](../aws/s3/s3.md#https-enforcement).

### Why the log target is in your own account

S3 server access logging requires the target bucket to be **owned by the same AWS account as the
source bucket and to be in the same Region** — AWS rejects a cross-account target outright. This is
why `central-logging-<account_id>-<region>` is provisioned per product account rather than as one
bucket in a shared account, and why the manifest above names
`central-logging-111122223333-ap-southeast-2`.

If you ever do need S3 access records centralized into another account, server access logging is
not the mechanism — use **CloudTrail S3 data events**, which support a cross-account destination
bucket.

### Gap G-1: enabling the EventBridge notification

`S3Bucket.spec.notification` accepts only `lambdaConfigurations`, `sqsConfigurations`, and
`snsConfigurations`. There is no `eventBridgeConfiguration`, so **the S3 → EventBridge notification
in the diagram above cannot be turned on declaratively**. Two ways forward:

**Option A — enable it out of band (keeps the target architecture).**

```bash
aws s3api put-bucket-notification-configuration \
  --bucket file-process-bucket \
  --notification-configuration '{"EventBridgeConfiguration": {}}' \
  --region ap-southeast-2
```

Because ACK owns the bucket's notification configuration, a later reconcile can overwrite this.
Re-apply it after any change to `spec.notification`, and verify with
`aws s3api get-bucket-notification-configuration` before trusting the pipeline.

**Option B — skip EventBridge and invoke the Lambda directly from S3 (fully supported today).**

```yaml
spec:
  notification:
    lambdaConfigurations:
      - id: file-process-direct
        lambdaFunctionARN: "arn:aws:lambda:ap-southeast-2:111122223333:function:file-process-lambda"
        events:
          - "s3:ObjectCreated:*"
        filter:
          key:
            filterRules:
              - name: prefix
                value: "data-service1/output/"
              - name: suffix
                value: ".json"
```

Option B costs you the routing indirection — adding a second consumer later means editing the
bucket rather than adding a rule — so prefer Option A while G-1 is open if you expect more
consumers. If you take Option B, skip Steps 5 and 8.

## Step 3: Create the SQS queue

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SQSQueue
metadata:
  name: file-process-messages
  namespace: data-team
spec:
  configRef: general-policy
  nameOverride: file-process-message-queue

  encryptionType: "kms"
  kmsMasterKeyId: "alias/aws/sqs"

  # Give a consumer 5 minutes to process before the message reappears
  visibilityTimeout: 300
  messageRetentionPeriod: 345600  # 4 days

  tags:
    data-pipeline: file-process
```

Adding a dead-letter queue is worth doing before this reaches production. Create a second
`SQSQueue` and reference it by **CR name** — `redrivePolicy` takes `deadLetterTargetRef`, not an
ARN, and an empty reference is invalid:

```yaml
spec:
  redrivePolicy:
    deadLetterTargetRef: file-process-messages-dlq
    maxReceiveCount: 3
```

## Step 4: Create the SNS topic

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SNSTopic
metadata:
  name: file-process-notifications
  namespace: data-team
spec:
  configRef: general-policy
  nameOverride: file-process-sns-topic
  displayName: "File Process Notifications"
  kmsMasterKeyId: "alias/aws/sns"
  tags:
    data-pipeline: file-process
```

Other teams subscribe to this topic themselves; the data team does not manage their subscriptions.

## Step 5: Create the CloudWatch log group

Lambda creates `/aws/lambda/<function-name>` on first invocation if it does not exist, but that
auto-created group has no retention policy and no KMS key. Create it explicitly so it is governed:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsLogGroup
metadata:
  name: file-process-lambda-logs
  namespace: data-team
spec:
  configRef: general-policy
  nameOverride: "/aws/lambda/file-process-lambda"
  retentionDays: 90
  kmsKeyId: "arn:aws:kms:ap-southeast-2:111122223333:key/11111111-2222-3333-4444-555555555555"
  deletionPolicy: retain
  tags:
    data-pipeline: file-process
```

`kmsKeyId` must be a full KMS key ARN — CloudWatch Logs rejects an alias or a bare key ID. Create
this before the Lambda, so the function's first invocation writes into the governed group rather
than racing to create an ungoverned one.

## Step 6: Create the IAM roles

### Execution role for the Lambda

Least privilege, per [KRO-1186](https://github.com/kropath/kropath-core/issues/1186) AC-4: no
wildcard actions, no wildcard resources.

Two things to know about `IAMRole` before reading the manifest:

- `type: lambda` generates the `lambda.amazonaws.com` trust policy for you. There is no
  `assumeRolePolicyDocument` field.
- **Only the first entry of `spec.policies` and the first of `spec.inlinePolicies` are honored.**
  Put every statement into a single inline document rather than splitting it across entries.

`addLambdaBasicPolicy` is set to `false` deliberately: the managed `AWSLambdaBasicExecutionRole` it
would attach grants logs on `arn:aws:logs:*:*:*`, a wildcard resource. The inline policy below
scopes logging to the one log group instead.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMRole
metadata:
  name: file-process-lambda-role
  namespace: data-team
spec:
  configRef: general-policy
  type: lambda
  nameOverride: file-process-lambda-role
  description: "Execution role for file-process-lambda"
  addLambdaBasicPolicy: false
  policies:
    - inline:
        name: file-process-pipeline
        documentJSON: |
          {
            "Version": "2012-10-17",
            "Statement": [
              {
                "Sid": "ReadInputObjects",
                "Effect": "Allow",
                "Action": ["s3:GetObject"],
                "Resource": "arn:aws:s3:::file-process-bucket/data-service1/output/*"
              },
              {
                "Sid": "DecryptInputObjects",
                "Effect": "Allow",
                "Action": ["kms:Decrypt"],
                "Resource": "arn:aws:kms:ap-southeast-2:111122223333:key/11111111-2222-3333-4444-555555555555"
              },
              {
                "Sid": "SendToQueue",
                "Effect": "Allow",
                "Action": ["sqs:SendMessage", "sqs:GetQueueUrl"],
                "Resource": "arn:aws:sqs:ap-southeast-2:111122223333:file-process-message-queue"
              },
              {
                "Sid": "PublishNotification",
                "Effect": "Allow",
                "Action": ["sns:Publish"],
                "Resource": "arn:aws:sns:ap-southeast-2:111122223333:file-process-sns-topic"
              },
              {
                "Sid": "WriteOwnLogs",
                "Effect": "Allow",
                "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                "Resource": "arn:aws:logs:ap-southeast-2:111122223333:log-group:/aws/lambda/file-process-lambda:*"
              }
            ]
          }
  tags:
    data-pipeline: file-process
```

`kms:Decrypt` appears because the bucket is SSE-KMS: without it, `s3:GetObject` fails on every
object. `sqs:GetQueueUrl` is there because of gap G-2 — see Step 7. `logs:CreateLogGroup` is
deliberately absent: Step 5 already created the group, and omitting the permission keeps the
function from silently creating an ungoverned one if the name ever drifts.

### Invoke role for EventBridge

EventBridge assumes this role to call the function (see gap G-3):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMRole
metadata:
  name: file-process-eventbridge-role
  namespace: data-team
spec:
  configRef: general-policy
  type: aws-service
  servicePrincipal: "events.amazonaws.com"
  nameOverride: file-process-eventbridge-role
  description: "Lets the file-process EventBridge rule invoke file-process-lambda"
  policies:
    - inline:
        name: invoke-file-process-lambda
        documentJSON: |
          {
            "Version": "2012-10-17",
            "Statement": [{
              "Effect": "Allow",
              "Action": ["lambda:InvokeFunction"],
              "Resource": "arn:aws:lambda:ap-southeast-2:111122223333:function:file-process-lambda"
            }]
          }
  tags:
    data-pipeline: file-process
```

## Step 7: Deploy the Lambda function

The code comes from the artifacts bucket **in this same account**, which the pipeline in
[KRO-1190](https://github.com/kropath/kropath-core/issues/1190) publishes to.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunction
metadata:
  name: file-process
  namespace: data-team
spec:
  configRef: general-policy
  nameOverride: file-process-lambda

  runtime: nodejs20.x
  handler: index.handler
  roleRef: file-process-lambda-role   # resolves to the IAMRole from Step 6

  code:
    s3Bucket: "artifacts-111122223333-ap-southeast-2"   # same account as the function
    s3Key: "file-process-lambda/v1.4.0/function.zip"
    s3ObjectVersion: ""   # pin a version id for immutable deploys

  timeout: 60
  memorySize: 256

  loggingConfig:
    logFormat: JSON
    applicationLogLevel: INFO

  tags:
    data-pipeline: file-process
```

Prefer `roleRef` over a hardcoded `role` ARN: the controller resolves it from the `IAMRole` CR's
`status.predictedArn`, so the role can be changed without editing the function. Pin `s3Key` to a
version rather than `latest` — a mutable key makes it impossible to tell which build is running.

### Artifact access: who actually needs `s3:GetObject`

This is the part most teams get wrong. **The Lambda execution role does not need any permission on
the artifacts bucket.** Lambda reads the ZIP **once, at create/update time, using the credentials of
whoever is deploying the function** — here, the ACK lambda-controller's IAM role. At invoke time the
code is already inside the Lambda service; the execution role is never used to fetch it.

So what has to be true is:

| Requirement | Where it is configured | Who owns it |
|---|---|---|
| `s3:GetObject` on the artifact key | ACK lambda-controller's IAM role | Platform team |
| `kms:Decrypt` on the artifacts bucket's key, if it is SSE-KMS | The controller's role **and** the KMS key policy | Platform team |
| Artifacts bucket in the **same Region** as the function | Bucket placement | Platform team |

The execution role's `s3:GetObject` in Step 6 is a separate grant, scoped to the **data** bucket
prefix the Lambda reads at runtime.

#### Why the artifacts bucket is per-account, not shared

A Lambda *can* be created from a ZIP in another account's bucket, but it costs you a standing
cross-account setup: a bucket policy on the shared bucket granting each product account's ACK
controller role, a matching KMS key policy, and a copy of the bucket in **every Region** any
function runs in — because a Lambda cannot be created from a ZIP in a bucket in another Region,
cross-account or not. That is three moving parts to keep in sync per account and Region, each of
which fails at deploy time with an opaque error.

Provisioning `artifacts-<account_id>-<region>` into each product-dev and product-test account
removes all three: the controller reads a bucket in its own account and Region, and no bucket or key
policy has to name an external principal. The build-once, promote-the-artifact pipeline in
[KRO-1190](https://github.com/kropath/kropath-core/issues/1190) is what keeps the dev and test
buckets holding the identical build, so nothing is rebuilt per account.

### Gap G-2: getting the queue URL and topic ARN into the function

`LambdaFunction` has no `environment` field, so `SQS_QUEUE_URL` and `SNS_TOPIC_ARN` cannot be
injected as configuration. (`docs/aws/lambda/lambda-function.md` documents an `environment` field —
that reference page is wrong and is being corrected alongside this one.)

Until G-2 is closed, have the TypeScript handler resolve its targets at startup instead:

```ts
import { SQSClient, GetQueueUrlCommand } from "@aws-sdk/client-sqs";

const region = process.env.AWS_REGION!;               // always set by the Lambda runtime
const accountId = context.invokedFunctionArn.split(":")[4];

const { QueueUrl } = await sqs.send(
  new GetQueueUrlCommand({ QueueName: "file-process-message-queue" }),
);
const topicArn = `arn:aws:sns:${region}:${accountId}:file-process-sns-topic`;
```

`GetQueueUrl` is why `sqs:GetQueueUrl` appears in the execution role in Step 6. Resolve once at
module scope so the call is paid on cold start, not per invocation. Baking the names into the build
is the other option, but it couples the artifact to one account.

## Step 8: Let EventBridge invoke the Lambda

Create the rule on the **default** event bus — S3 delivers its notifications there, not to a custom
bus. Exactly one of `eventBusRef` or `eventBusName` must be set.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeRule
metadata:
  name: file-process
  namespace: data-team
spec:
  configRef: general-policy
  nameOverride: file-process-rule
  eventBusName: "default"
  state: "ENABLED"

  # eventPattern is a JSON *string*, not a YAML map
  eventPattern: |
    {
      "source": ["aws.s3"],
      "detail-type": ["Object Created"],
      "detail": {
        "bucket": {"name": ["file-process-bucket"]},
        "object": {"key": [{"wildcard": "data-service1/output/*.json"}]}
      }
    }

  targets:
    - id: file-process-lambda
      arn: "arn:aws:lambda:ap-southeast-2:111122223333:function:file-process-lambda"
      roleARN: "arn:aws:iam::111122223333:role/file-process-eventbridge-role"

  tags:
    data-pipeline: file-process
```

Use `wildcard` rather than separate `prefix` and `suffix` entries. Entries in a key array are
OR-ed, so `[{"prefix": "data-service1/output/"}, {"suffix": ".json"}]` would match every object
under the prefix *and* every `.json` anywhere in the bucket — not the intersection you want.

**Gap G-3:** there is no `LambdaPermission` resource in kropath-aws, so the function has no
resource-based policy granting `events.amazonaws.com` permission to invoke it. The `roleARN` above
is what makes the invocation work: EventBridge assumes that role instead. Do not remove it.

Because the rule is on the default bus, its ARN has no bus segment:

```
arn:aws:events:ap-southeast-2:111122223333:rule/file-process-rule
```

## Verification

### Resources are ready in Kubernetes

```bash
kubectl get s3bucket,sqsqueue,snstopic,cloudwatchlogsloggroup,eventbridgerule,lambdafunction,iamrole \
  -n data-team
```

Every resource should report `valid` under `NAMINGSTATUS` and a populated `PREDICTEDARN`. A
`NAMINGSTATUS` of `invalid-unresolved-tokens` means a naming template referenced a tag that does not
exist — fix the tag or the template before going further.

### Resources match in AWS

```bash
aws s3api head-bucket --bucket file-process-bucket --region ap-southeast-2
aws s3api get-bucket-notification-configuration --bucket file-process-bucket --region ap-southeast-2
aws s3api get-bucket-policy --bucket file-process-bucket --region ap-southeast-2   # DenyNonTLSAccess
aws s3api get-bucket-lifecycle-configuration --bucket file-process-bucket --region ap-southeast-2

aws sqs get-queue-url --queue-name file-process-message-queue --region ap-southeast-2
aws sns get-topic-attributes \
  --topic-arn arn:aws:sns:ap-southeast-2:111122223333:file-process-sns-topic --region ap-southeast-2
aws logs describe-log-groups \
  --log-group-name-prefix /aws/lambda/file-process-lambda --region ap-southeast-2

aws events describe-rule --name file-process-rule --region ap-southeast-2
aws events list-targets-by-rule --rule file-process-rule --region ap-southeast-2
aws lambda get-function --function-name file-process-lambda --region ap-southeast-2
```

The notification check matters most: if `EventBridgeConfiguration` is absent from its output, gap
G-1's out-of-band step was never applied or has been reconciled away, and nothing downstream will
fire.

Confirm the deployed code is the real artifact, not a placeholder — `CodeSize` of a few hundred
bytes means an empty ZIP:

```bash
aws lambda get-function --function-name file-process-lambda \
  --query 'Configuration.[CodeSize,LastModified,Runtime]' --region ap-southeast-2
```

### End-to-end: drop a file

```bash
echo '{"record": "test"}' > test.json
aws s3 cp test.json s3://file-process-bucket/data-service1/output/test.json --region ap-southeast-2
```

Then, within a minute or so:

```bash
# 1. The Lambda ran and logged both lines
aws logs tail /aws/lambda/file-process-lambda --since 5m --region ap-southeast-2

# 2. A message reached the queue
aws sqs receive-message \
  --queue-url "$(aws sqs get-queue-url --queue-name file-process-message-queue \
      --query QueueUrl --output text --region ap-southeast-2)" \
  --wait-time-seconds 10 --region ap-southeast-2

# 3. The notification was published — subscribe an endpoint first, or read the metric
aws cloudwatch get-metric-statistics \
  --namespace AWS/SNS --metric-name NumberOfMessagesPublished \
  --dimensions Name=TopicName,Value=file-process-sns-topic \
  --start-time "$(date -u -v-10M +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --period 300 --statistics Sum --region ap-southeast-2
```

SNS has no "read the last message" API — either attach a subscription (an SQS queue is easiest for
testing) or use the published-message metric as above.

Also confirm the negative case, since the rule's whole job is filtering: upload a file **outside**
the watched path and check that nothing fires.

```bash
aws s3 cp test.json s3://file-process-bucket/data-service1/other/test.json --region ap-southeast-2
```

## Troubleshooting

**A resource never becomes ready.** Check `status.conditions` first
(`kubectl describe <kind> <name> -n data-team`). The most common cause in a fresh namespace is a
missing family config CR, or one missing its `aws.kropath.run/resource-name` label — the RGD's
`externalRef` lookup then resolves nothing and the resource waits forever.

**Nothing happens when a file lands.** Work the chain in order rather than guessing:

1. Is the EventBridge notification on the bucket?
   `aws s3api get-bucket-notification-configuration --bucket file-process-bucket`. If not, gap G-1.
2. Does the pattern match? Test it without uploading anything:
   ```bash
   aws events test-event-pattern \
     --event-pattern file://pattern.json \
     --event file://sample-s3-event.json --region ap-southeast-2
   ```
3. Is the rule firing? Check the `TriggeredRules` metric in the `AWS/Events` namespace. If it is
   firing but the Lambda is not running, check `FailedInvocations` — that is almost always the
   invoke role (gap G-3).
4. Is the Lambda erroring? `aws logs tail /aws/lambda/file-process-lambda --since 15m`.

**The Lambda runs but SQS or SNS stays empty.** Read the log output: an `AccessDenied` on
`sqs:SendMessage` or `sns:Publish` means the execution role's inline policy did not apply. Remember
that **only the first entry of `spec.policies` is honored** — if you split the statements across
several entries, everything after the first was silently dropped.

**`s3:GetObject` fails on the input object.** The bucket is SSE-KMS, so the role needs `kms:Decrypt`
on the bucket's key as well as `s3:GetObject`. Check the key policy too: a grant in the role's
policy is not enough if the key policy does not allow the account.

**The function deploys but runs no code.** The artifact key is wrong or empty. Check `CodeSize`
(above), then confirm the pipeline in KRO-1190 actually promoted the build into **this account's**
artifacts bucket — a function in the test account cannot read the dev account's bucket. See
[Artifact access](#artifact-access-who-actually-needs-s3getobject).

**Access logs never appear in the central-logging bucket.** Check that `logging.targetBucket` names
the bucket in **this** account and Region — a cross-account target is rejected outright. See
[Why the log target is in your own account](#why-the-log-target-is-in-your-own-account).

## Related tickets

- [KRO-1182](https://github.com/kropath/kropath-core/issues/1182) — story tracker
- [KRO-1185](https://github.com/kropath/kropath-core/issues/1185) — onboard the namespace
- [KRO-1186](https://github.com/kropath/kropath-core/issues/1186) — create the resources
- [KRO-1187](https://github.com/kropath/kropath-core/issues/1187) — verify in AWS
- [KRO-1188](https://github.com/kropath/kropath-core/issues/1188) — gap tickets, including G-1/G-2/G-3
- [KRO-1190](https://github.com/kropath/kropath-core/issues/1190) — Lambda repo and build pipeline
- [KRO-1176](https://github.com/kropath/kropath-core/issues/1176) — platform-shared foundation

## Next steps

- **Add a dead-letter queue** to the SQS queue and a `FailedInvocations` alarm on the rule.
- **Add subscribers** to `file-process-sns-topic` as other teams ask for the events — no change to
  this pipeline is needed.
- **Add a second consumer** by adding a target to the EventBridge rule, which is the payoff for
  keeping EventBridge in the path.

## Reference

- [AWS S3 Buckets](../aws/s3/s3.md)
- [EventBridgeRule](../aws/eventbridge/eventbridgerule.md)
- [LambdaFunction](../aws/lambda/lambda-function.md)
- [SQSQueue](../aws/sqs/sqsqueue.md)
- [SNSTopic](../aws/sns/snstopic.md)
- [CloudWatchLogsLogGroup](../aws/cloudwatchlogs/cloudwatchlogsloggroup.md)
- [IAMRole](../aws/iam/iamrole.md)
- [kropath Engineering Standards](../engineering-standards.md)
