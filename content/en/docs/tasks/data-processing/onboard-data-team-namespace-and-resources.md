---
doc_type: task
title: Onboard the data-team namespace and its file-processing resources
description: "The data team runs a **file-processing data flow**."
---

# Onboard the data-team namespace and its file-processing resources

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

This is the data team's slice of the kropath golden path. It builds on the foundation your platform
team provides: a central-logging bucket for access records, and an artifacts bucket the Lambda build
pipeline publishes to.

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
- **Two platform-provided buckets in this account.** Your platform team provisions
  `central-logging-<account_id>-<region>` and `artifacts-<account_id>-<region>` into each account,
  so both live alongside the resources you are about to create. For this page that means
  `central-logging-111122223333-ap-southeast-2` and `artifacts-111122223333-ap-southeast-2`.
- **The Lambda artifact.** `file-process-lambda` is built from TypeScript by your build pipeline,
  which uploads the ZIP to this account's artifacts bucket. The artifact must exist before Step 7 —
  a `LambdaFunction` whose code source points at a missing key reconciles into an error, and one
  pointed at an empty placeholder reports `Ready` while running no real code.
- **Familiarity** with the governance cascade
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

## Step 1: Onboard the namespace

Create the namespace, its ACK cross-account annotations, and the local config CRs. Every config CR
carries the `aws.kropath.run/resource-name` label — that label is how `externalRef` lookups resolve
the profile, and a config CR without it is invisible to the resources that need it.

```yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: data-team
  annotations:
    # Both are required: they tell ACK which account and region to create
    # this namespace's AWS resources in.
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
profile that does not exist falls back to `general-policy`; if that is missing too, the resource
cannot resolve its effective configuration and never becomes ready.

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
[Region Handling](../../reference/aws/s3/_index.md#region-handling-the-us-east-1-special-case).

Note that `enforceHttpsOnly` currently writes the `DenyNonTLSAccess` statement straight into the
bucket policy field, so kropath owns that field outright — do not attach another bucket policy to
this bucket until the `bucketPolicyRef` composition work lands. See
[AWS S3 Buckets](../../reference/aws/s3/_index.md#https-enforcement).

### Why the log target is in your own account

S3 server access logging requires the target bucket to be **owned by the same AWS account as the
source bucket and to be in the same Region** — AWS rejects a cross-account target outright. This is
why `central-logging-<account_id>-<region>` is provisioned per product account rather than as one
bucket in a shared account, and why the manifest above names
`central-logging-111122223333-ap-southeast-2`.

If you ever do need S3 access records centralized into another account, server access logging is
not the mechanism — use **CloudTrail S3 data events**, which support a cross-account destination
bucket.

### Enable EventBridge notifications on the bucket

The `S3Bucket` resource cannot yet express this — `spec.notification` covers Lambda, SQS, and SNS
targets, but not EventBridge. Until it does, turn the notification on with the AWS CLI:

```bash
aws s3api put-bucket-notification-configuration \
  --bucket file-process-bucket \
  --notification-configuration '{"EventBridgeConfiguration": {}}' \
  --region ap-southeast-2
```

This step is not optional — without it the bucket publishes nothing and every later step is inert.

Because kropath manages the bucket's notification configuration, changing `spec.notification` later
can overwrite this. Re-apply it after any such change, and confirm before trusting the pipeline:

```bash
aws s3api get-bucket-notification-configuration \
  --bucket file-process-bucket --region ap-southeast-2
```

`EventBridgeConfiguration` must appear in the output.

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

## Step 6: Create the IAM role

### Execution role for the Lambda

Least privilege: no wildcard actions, no wildcard resources.

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
                "Action": ["sqs:SendMessage"],
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
object. `logs:CreateLogGroup` is deliberately absent: Step 5 already created the group, and omitting the permission keeps the
function from silently creating an ungoverned one if the name ever drifts.

### EventBridge does not need a role here

EventBridge does not assume an IAM role to invoke a Lambda function — it relies on a policy attached
to the function itself, which [Step 8](#step-8-let-eventbridge-invoke-the-lambda) sets up. Do not
create a role for it; one would grant nothing.

## Step 7: Deploy the Lambda function

The code comes from the artifacts bucket in this account, which your build pipeline publishes to.

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

  environment:
    SQS_QUEUE_URL: "https://sqs.ap-southeast-2.amazonaws.com/111122223333/file-process-message-queue"
    SNS_TOPIC_ARN: "arn:aws:sns:ap-southeast-2:111122223333:file-process-sns-topic"

  loggingConfig:
    logFormat: JSON
    applicationLogLevel: INFO

  tags:
    data-pipeline: file-process
```

Prefer `roleRef` over a hardcoded `role` ARN: the controller resolves it from the `IAMRole` CR's
`status.predictedArn`, so the role can be changed without editing the function. Pin `s3Key` to a
version rather than `latest` — a mutable key makes it impossible to tell which build is running.

### Giving the function its queue URL and topic ARN

The `LambdaFunction.spec.environment` field injects configuration as environment variables at
runtime. Use it to pass the queue URL and topic ARN to the handler.

In the `LambdaFunction` manifest (Step 7), add the `environment` block:

```yaml
spec:
  environment:
    SQS_QUEUE_URL: "https://sqs.ap-southeast-2.amazonaws.com/111122223333/file-process-message-queue"
    SNS_TOPIC_ARN: "arn:aws:sns:ap-southeast-2:111122223333:file-process-sns-topic"
```

Your TypeScript handler then reads them directly:

```ts
const queueUrl = process.env.SQS_QUEUE_URL!;
const topicArn = process.env.SNS_TOPIC_ARN!;
```

This approach keeps the handler simple, avoids runtime discovery calls on every cold start, and decouples the artifact from account-specific details.

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
      # No roleARN — EventBridge does not use one for Lambda targets. See below.

  tags:
    data-pipeline: file-process
```

Use `wildcard` rather than separate `prefix` and `suffix` entries. Entries in a key array are
OR-ed, so `[{"prefix": "data-service1/output/"}, {"suffix": ".json"}]` would match every object
under the prefix *and* every `.json` anywhere in the bucket — not the intersection you want.

### Allow EventBridge to invoke the function

Applying the rule above is not enough. EventBridge splits its targets by how it authorizes them:

| Target type | How EventBridge authorizes the call |
|---|---|
| Kinesis, Step Functions, ECS, API Gateway, cross-account buses | Assumes the IAM role in the target's `roleARN` |
| **Lambda**, SNS, SQS, CloudWatch Logs | **Resource-based policy on the target itself** — `roleARN` is not used |

A Lambda target therefore needs a resource-based policy on the *function*, granting
`events.amazonaws.com` permission to invoke it, conditioned on the rule's ARN. That is what
`aws lambda add-permission` creates, and what `AWS::Lambda::Permission` emits in CloudFormation.

kropath has no resource for this yet, so grant it with the AWS CLI:

```bash
aws lambda add-permission \
  --function-name file-process-lambda \
  --statement-id eventbridge-file-process-rule \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:ap-southeast-2:111122223333:rule/file-process-rule \
  --region ap-southeast-2
```

Keep `--source-arn`: without it, any account's EventBridge rule could invoke your function. Verify
with `aws lambda get-policy --function-name file-process-lambda`.

Nothing overwrites this once set — unlike the bucket notification in Step 2, a function's policy is
not a field kropath manages. But it also lives in no manifest, so it has to be re-applied by hand
whenever the function is recreated in another account or region.

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
the notification step in Step 2 was never applied or has since been overwritten, and nothing
downstream will fire.

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
missing family config CR, or one missing its `aws.kropath.run/resource-name` label — the label
lookup then resolves nothing and the resource waits forever.

**Nothing happens when a file lands.** Work the chain in order rather than guessing:

1. Is the EventBridge notification on the bucket?
   `aws s3api get-bucket-notification-configuration --bucket file-process-bucket`. If not, re-run the
   enable step in Step 2.
2. Does the pattern match? Test it without uploading anything:
   ```bash
   aws events test-event-pattern \
     --event-pattern file://pattern.json \
     --event file://sample-s3-event.json --region ap-southeast-2
   ```
3. Is the rule firing? Check the `TriggeredRules` metric in the `AWS/Events` namespace. If it is
   firing but the Lambda is not running, check `FailedInvocations` — that is almost always the
   missing invoke permission from Step 8. Confirm with
   `aws lambda get-policy --function-name file-process-lambda`; an empty or absent policy is the
   answer.
4. Is the Lambda erroring? `aws logs tail /aws/lambda/file-process-lambda --since 15m`.

**The Lambda runs but SQS or SNS stays empty.** Read the log output: an `AccessDenied` on
`sqs:SendMessage` or `sns:Publish` means the execution role's inline policy did not apply. Remember
that **only the first entry of `spec.policies` is honored** — if you split the statements across
several entries, everything after the first was silently dropped.

**`s3:GetObject` fails on the input object.** The bucket is SSE-KMS, so the role needs `kms:Decrypt`
on the bucket's key as well as `s3:GetObject`. Check the key policy too: a grant in the role's
policy is not enough if the key policy does not allow the account.

**The function deploys but runs no code.** The artifact key is wrong or empty. Check `CodeSize`
(above), then confirm your build pipeline actually published the artifact to **this account's**
artifacts bucket — a function cannot read a bucket in another account or another Region.

**Access logs never appear in the central-logging bucket.** Check that `logging.targetBucket` names
the bucket in **this** account and Region — a cross-account target is rejected outright. See
[Why the log target is in your own account](#why-the-log-target-is-in-your-own-account).

## Next steps

- **Add a dead-letter queue** to the SQS queue and a `FailedInvocations` alarm on the rule.
- **Add subscribers** to `file-process-sns-topic` as other teams ask for the events — no change to
  this pipeline is needed.
- **Add a second consumer** by adding a target to the EventBridge rule, which is the payoff for
  keeping EventBridge in the path.

## Reference

- [AWS S3 Buckets](../../reference/aws/s3/_index.md)
- [EventBridgeRule](../../reference/aws/eventbridge/eventbridgerule.md)
- [LambdaFunction](../../reference/aws/lambda/lambda-function.md)
- [SQSQueue](../../reference/aws/sqs/sqsqueue.md)
- [SNSTopic](../../reference/aws/sns/snstopic.md)
- [CloudWatchLogsLogGroup](../../reference/aws/cloudwatchlogs/cloudwatchlogsloggroup.md)
- [IAMRole](../../reference/aws/iam/iamrole.md)
