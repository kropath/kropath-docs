---
doc_type: task
title: Onboard a Data Team Namespace and Resources
---

# Onboard a Data Team Namespace and Resources

**Document Type:** Task

This task describes how to onboard a new data team namespace in kropath, including creating the namespace, configuring governance policies, and provisioning the resources needed for a data pipeline that processes S3 events.

## What you'll accomplish

By following this task, you will:

- Create a new Kubernetes namespace with appropriate governance configurations and cross-account IAM annotations
- Provision AWS resources for a data pipeline: an S3 bucket, SNS topic, SQS queue, EventBridge rule, Lambda function, and IAM roles
- Establish an event-driven trigger chain: S3 object creation → EventBridge rule → Lambda invocation → SQS message + SNS notification
- Verify that all resources are correctly configured and the end-to-end pipeline works

## Before you begin

You need:

- **Cluster access:** kubectl access to the target EKS cluster in kropath
- **AWS credentials:** Permissions to create S3 buckets, Lambda functions, EventBridge rules, SQS queues, SNS topics, and IAM roles in the target AWS account
- **Platform prerequisites:**
  - A `KropathConfig` profile configured in the target namespace with appropriate mandatory and default settings
  - An `S3AdvancedConfig` profile for your organization's S3 governance policies (e.g., encryption, tagging)
  - The central logging S3 bucket already provisioned (from the platform-shared namespace story)
  - Access logging must be configured to send S3 logs to the central logging bucket
- **Lambda artifact:** The Lambda function artifact built and promoted to the target account's artifacts bucket by the lambda build repository (see [KRO-1190](https://github.com/kropath/kropath/issues/KRO-1190))
- **Knowledge prerequisites:**
  - Basic Kubernetes manifest authoring (deployments, namespaces, secrets)
  - Understanding of AWS IAM, S3 event notifications, EventBridge, Lambda, and SQS/SNS
  - Familiarity with kropath's governance model and the effectiveConfig cascade (see [AWS S3 Buckets](../aws/s3/s3.md))

## Onboarding Steps

### Step 1: Create the namespace and apply governance configurations

Create a Kubernetes namespace with appropriate labels and annotations for cross-account resource management.

```yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: data-team
  labels:
    kropath.run/governance: enabled
  annotations:
    # ACK annotations for cross-account resource management (ADR-019)
    ack.aws.com/account-id: "123456789012"
    ack.aws.com/region: "us-east-1"

---
# Local KropathConfig for this namespace
apiVersion: kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: data-team-config
  namespace: data-team
spec:
  # Mandatory governance for the data team
  mandatory:
    tags:
      team: data-team
      cost-center: data-platform
      data-classification: internal
  
  # Default values for this namespace
  defaults:
    tags:
      environment: production
    annotations:
      managed-by: kropath

---
# Local S3AdvancedConfig for data team buckets
apiVersion: aws.kropath.run/v1alpha1
kind: S3AdvancedConfig
metadata:
  name: data-team-policy
  namespace: data-team
spec:
  mandatory:
    # Enforce encryption for all data team S3 buckets
    encryptionAlgorithm: "aws:kms"
    # (Replace with your organization's KMS key ARN)
    kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
    # Enforce public access blocking
    blockPublicAccess: true
  
  defaults:
    # Default naming template for data team buckets
    namingTemplate: "data-team-{name}-{account_id}"
    # Enable versioning by default
    versioning: "Enabled"
    # Enable access logging
    accessLogging: true
    accessLoggingTargetBucket: "central-logging-123456789012-us-east-1"
    accessLoggingTargetPrefix: "data-team/"
```

Apply this manifest to your cluster:

```bash
kubectl apply -f namespace-and-config.yaml
```

Verify the namespace was created:

```bash
kubectl get ns data-team
kubectl get kropath data-team-config -n data-team
```

### Step 2: Create the S3 bucket with access logging

Create the S3 bucket that will trigger the data pipeline.

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: data-input
  namespace: data-team
spec:
  # Reference the data team governance profile
  configRef: data-team-policy
  
  # Additional tags for cost tracking and data governance
  tags:
    data-pipeline: enabled
    retention-days: "90"
  
  syncedLabels:
    pipeline-stage: ingestion
  
  # Retention policy: keep the S3 bucket even if the CR is deleted
  deletionPolicy: retain
  
  # Enable versioning for audit trail
  versioning: "Enabled"
```

### Step 3: Create the SNS topic for notifications

Create an SNS topic that the Lambda function will publish to.

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: SNSTopic
metadata:
  name: data-pipeline-notifications
  namespace: data-team
spec:
  # Topic name follows kropath naming conventions
  displayName: "Data Pipeline Notifications"
  
  # Enable server-side encryption
  kmsMasterKeyId: "alias/aws/sns"
  
  tags:
    data-pipeline: enabled
    notification-type: pipeline-events
  
  syncedLabels:
    critical: "true"
```

### Step 4: Create the SQS queue

Create an SQS queue to receive messages from the Lambda function.

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: SQSQueue
metadata:
  name: data-pipeline-messages
  namespace: data-team
spec:
  # Retain messages for 4 days
  messageRetentionPeriod: 345600
  
  # Enable server-side encryption
  kmsMasterKeyId: "alias/aws/sqs"
  
  # Visibility timeout: Lambda gets 5 minutes to process
  visibilityTimeout: 300
  
  # Dead-letter queue for failed messages
  redrivePolicy:
    deadLetterTargetArn: ""  # Will be configured separately
    maxReceiveCount: 3
  
  tags:
    data-pipeline: enabled
    queue-type: processing
```

### Step 5: Create the EventBridge rule

Create an EventBridge rule that triggers on S3 object creation.

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeRule
metadata:
  name: s3-to-lambda
  namespace: data-team
spec:
  # React to S3 object creation in the data-input bucket
  eventPattern:
    source:
      - aws.s3
    detail-type:
      - "Object Created"
    detail:
      bucket:
        name:
          - data-input  # Will be resolved to the actual bucket name by effectiveName
      object:
        key:
          - prefix: "ingestion/"
  
  # Route events to the Lambda function
  targets:
    - arn: "arn:aws:lambda:us-east-1:123456789012:function:data-team-processor"
      roleArn: "arn:aws:iam::123456789012:role/EventBridgeToLambdaRole"
  
  # Enable the rule
  state: "ENABLED"
  
  tags:
    data-pipeline: enabled
    integration-type: s3-to-lambda
```

### Step 6: Create IAM roles for the Lambda function

Create an IAM role with the minimum permissions needed for the Lambda function to:
- Be invoked by EventBridge
- Write messages to SQS
- Publish to SNS
- Log to CloudWatch

```yaml
---
apiVersion: iam.aws.kropath.run/v1alpha1
kind: IAMRole
metadata:
  name: data-team-lambda-role
  namespace: data-team
spec:
  assumeRolePolicyDocument: |
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": "lambda.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }
  
  # Inline policy with minimal permissions
  inlinePolicies:
    - name: data-pipeline-permissions
      policyDocument: |
        {
          "Version": "2012-10-17",
          "Statement": [
            {
              "Effect": "Allow",
              "Action": [
                "sqs:SendMessage"
              ],
              "Resource": "arn:aws:sqs:us-east-1:123456789012:data-pipeline-messages"
            },
            {
              "Effect": "Allow",
              "Action": [
                "sns:Publish"
              ],
              "Resource": "arn:aws:sns:us-east-1:123456789012:data-pipeline-notifications"
            },
            {
              "Effect": "Allow",
              "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
              ],
              "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/*"
            }
          ]
        }
  
  tags:
    data-pipeline: enabled
    role-type: lambda-execution
  
  syncedLabels:
    security: strict
```

### Step 7: Deploy the Lambda function

Deploy the Lambda function using the artifact from the lambda build repository.

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunction
metadata:
  name: data-team-processor
  namespace: data-team
spec:
  # Function runtime and handler
  runtime: nodejs18.x
  handler: index.handler
  role: "arn:aws:iam::123456789012:role/data-team-lambda-role"
  
  # Code from S3 artifact bucket
  code:
    s3Bucket: "artifacts-123456789012-us-east-1"
    s3Key: "data-team-processor/latest/function.zip"
  
  # Environment variables
  environment:
    variables:
      SQS_QUEUE_URL: "https://sqs.us-east-1.amazonaws.com/123456789012/data-pipeline-messages"
      SNS_TOPIC_ARN: "arn:aws:sns:us-east-1:123456789012:data-pipeline-notifications"
  
  # Function timeout: 60 seconds
  timeout: 60
  
  # Memory allocation: 256 MB
  memorySize: 256
  
  tags:
    data-pipeline: enabled
    function-type: event-processor
  
  syncedLabels:
    critical: "true"
```

### Step 8: Give EventBridge permission to invoke the Lambda

Create a Lambda permission to allow EventBridge to invoke the function.

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaPermission
metadata:
  name: allow-eventbridge-invoke
  namespace: data-team
spec:
  functionName: data-team-processor
  action: lambda:InvokeFunction
  principal: events.amazonaws.com
  sourceArn: "arn:aws:events:us-east-1:123456789012:rule/data-team/s3-to-lambda"
```

## Verification

After applying all manifests, verify that the resources are provisioned correctly.

### Verify namespace and configurations

```bash
# Check namespace
kubectl get ns data-team

# Check local configurations
kubectl get kropath -n data-team
kubectl get s3advanced -n data-team
```

Expected output: All resources should show `Ready` or `Synced` status.

### Verify S3 bucket

```bash
# Check bucket creation in Kubernetes
kubectl get s3bucket -n data-team

# Verify in AWS
aws s3api head-bucket --bucket data-team-data-input-123456789012 --region us-east-1

# Check access logging
aws s3api get-bucket-logging --bucket data-team-data-input-123456789012 --region us-east-1
```

### Verify SNS and SQS

```bash
# Check SNS topic
kubectl get snstopic -n data-team
aws sns list-topics --region us-east-1 | grep data-pipeline-notifications

# Check SQS queue
kubectl get sqsqueue -n data-team
aws sqs list-queues --region us-east-1 | grep data-pipeline-messages
```

### Verify EventBridge rule and Lambda

```bash
# Check EventBridge rule
kubectl get eventbridgerule -n data-team
aws events describe-rule --name s3-to-lambda --region us-east-1

# Check Lambda function
kubectl get lambdafunction -n data-team
aws lambda get-function --function-name data-team-processor --region us-east-1
```

### End-to-end trigger test

Verify that the complete S3 → EventBridge → Lambda → SQS/SNS trigger chain works:

1. **Upload a test file to S3:**
   ```bash
   echo "test data" > test.txt
   aws s3 cp test.txt s3://data-team-data-input-123456789012/ingestion/test.txt --region us-east-1
   ```

2. **Check Lambda logs:**
   ```bash
   # Get the latest log stream
   LATEST_STREAM=$(aws logs describe-log-streams \
     --log-group-name /aws/lambda/data-team-processor \
     --order-by LastEventTime \
     --descending --max-items 1 \
     --query 'logStreams[0].logStreamName' \
     --output text \
     --region us-east-1)
   
   # View logs
   aws logs get-log-events \
     --log-group-name /aws/lambda/data-team-processor \
     --log-stream-name "$LATEST_STREAM" \
     --region us-east-1
   ```

3. **Verify SQS message:**
   ```bash
   # Check if a message was written to the queue
   aws sqs receive-message \
     --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/data-pipeline-messages \
     --region us-east-1
   ```

4. **Verify SNS notification:**
   ```bash
   # Check SNS subscription and message history
   aws sns list-subscriptions-by-topic \
     --topic-arn arn:aws:sns:us-east-1:123456789012:data-pipeline-notifications \
     --region us-east-1
   ```

If all checks pass and the Lambda function executed successfully, the trigger chain is working end-to-end.

## Troubleshooting

**S3 bucket not created:**
- Check that the `S3AdvancedConfig` profile (`data-team-policy`) exists and is `Ready`
- Verify that the cluster has permissions to create S3 buckets in the target account
- Check the bucket CR status: `kubectl describe s3bucket data-input -n data-team`

**Lambda not invoked on S3 events:**
- Verify that the EventBridge rule is enabled: `aws events describe-rule --name s3-to-lambda`
- Check that the Lambda function ARN in the rule target is correct
- Verify that the EventBridge role has permissions to invoke the Lambda
- Check CloudTrail logs for EventBridge invocation attempts

**SQS/SNS messages not received:**
- Verify that the Lambda code is actually writing to SQS and SNS
- Check IAM role permissions for the Lambda function
- Verify SQS queue and SNS topic ARNs are correct in Lambda environment variables

**Access logging not working:**
- Verify that the central logging bucket exists and is accessible
- Check S3 bucket ACLs and permissions for log delivery
- Verify the logging target prefix is correct

## Related Issues and Tickets

For detailed implementation notes, see:

- **[KRO-1182](https://github.com/kropath/kropath/issues/KRO-1182)** — Parent tracker for this onboarding story
- **[KRO-1185](https://github.com/kropath/kropath/issues/KRO-1185)** — Onboard namespace subtask (creating the namespace and local configs)
- **[KRO-1186](https://github.com/kropath/kropath/issues/KRO-1186)** — Create resources subtask (S3, SNS, SQS, EventBridge, Lambda, IAM roles)
- **[KRO-1190](https://github.com/kropath/kropath/issues/KRO-1190)** — Lambda build repository + CI/CD pipeline for the Lambda artifact

## Next Steps

After onboarding the data team namespace, you can:

- **Add data processing logic** — Update the Lambda function in the lambda build repository to implement your specific data processing requirements
- **Scale to additional data sources** — Add more EventBridge rules to process events from other S3 buckets or AWS services
- **Monitor and alert** — Set up CloudWatch Alarms and SNS subscriptions to monitor the data pipeline
- **Test in AWS** — Follow the verification steps in [KRO-1187](https://github.com/kropath/kropath/issues/KRO-1187) to verify the pipeline end-to-end in AWS

## See Also

- [AWS S3 Buckets Configuration](../aws/s3/s3.md)
- [Kubernetes API Conventions](https://kubernetes.io/docs/concepts/overview/working-with-objects/)
