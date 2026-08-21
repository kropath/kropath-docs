# Getting Started with Step Functions

This guide shows how a platform team sets up governance and how an application team creates and runs their first state machine.

## Prerequisites

- A Kubernetes cluster running kropath-aws
- AWS account with permissions to create Step Functions resources
- `kubectl` configured to access your cluster
- An IAM role for state machine execution

## Step 1: Platform Team — Set Up Governance

The platform team starts by creating a `StepFunctionsConfig` profile that defines policies for the organization.

### Create the general-policy Profile

```yaml
# stepfunctions-config.yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    # No mandatory fields by default (optional enforcement)
  defaults:
    # AWS defaults
    loggingLevel: "OFF"
    tracingEnabled: false
    includeExecutionData: false
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
      platform: step-functions
    syncedLabels:
      platform: kropath
    syncedAnnotations: {}
```

Apply the configuration:

```bash
kubectl apply -f stepfunctions-config.yaml
```

Verify it was created:

```bash
kubectl get stepfunctionsconfig -n kro-system
# NAME              AGE
# general-policy    2m
```

### Create a Production Profile (Optional)

For stricter compliance in production, create an additional profile:

```yaml
# stepfunctions-config-prod.yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsConfig
metadata:
  name: prod-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: prod-policy
spec:
  mandatory:
    loggingLevel: "ERROR"        # All production state machines must log errors
    tracingEnabled: true         # All production state machines must be traced
    tags:
      environment: production
      compliance: required
  defaults:
    includeExecutionData: false
    namingTemplate: "prod-{namespace}-{name}"
    syncedLabels:
      environment: production
    syncedAnnotations:
      runbook: "https://wiki.example.com/runbook"
```

Apply it:

```bash
kubectl apply -f stepfunctions-config-prod.yaml
```

## Step 2: Application Team — Create a Namespace

Create a namespace for your workflows:

```bash
kubectl create namespace workflows-demo
kubectl label namespace workflows-demo app=workflows
```

## Step 3: Application Team — Prepare AWS Resources

Before creating state machines, prepare the necessary AWS resources.

### Create an IAM Role for State Machine Execution

```bash
# Create the trust policy
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "states.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name step-functions-demo-role \
  --assume-role-policy-document file://trust-policy.json

# Attach a basic policy (for this demo, allow Lambda invocation)
cat > policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:*:*:function/*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name step-functions-demo-role \
  --policy-name step-functions-demo-policy \
  --policy-document file://policy.json

# Get the role ARN
aws iam get-role --role-name step-functions-demo-role --query 'Role.Arn'
# Output: arn:aws:iam::123456789012:role/step-functions-demo-role
```

### Create a CloudWatch Logs Log Group

```bash
aws logs create-log-group \
  --log-group-name /aws/states/workflows-demo \
  --region us-east-1
```

## Step 4: Application Team — Create Your First State Machine

Create a simple state machine that passes data through:

```yaml
# my-first-statemachine.yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsStateMachine
metadata:
  name: greeting
  namespace: workflows-demo
spec:
  # Simple state machine definition
  definition: |
    {
      "Comment": "A simple greeting state machine",
      "StartAt": "GreetUser",
      "States": {
        "GreetUser": {
          "Type": "Pass",
          "Result": {
            "message": "Hello from kropath Step Functions!"
          },
          "End": true
        }
      }
    }

  # Standard execution type (durable, full history)
  type: STANDARD

  # IAM role for execution (replace with your role ARN)
  roleArn: "arn:aws:iam::123456789012:role/step-functions-demo-role"

  # Enable logging for debugging
  loggingLevel: "ERROR"
  logDestinationArn: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/states/workflows-demo"

  # Use the general-policy profile (defaults to this anyway)
  configRef: "general-policy"

  # Custom tags
  tags:
    application: demo
    version: v1

  # Labels synced to K8s and cloud
  syncedLabels:
    app: workflows

  # Deletion policy: retain the AWS resource if K8s CR is deleted
  deletionPolicy: retain
```

Apply it:

```bash
kubectl apply -f my-first-statemachine.yaml
```

Verify the state machine was created:

```bash
kubectl get stepfunctionsstatemachine -n workflows-demo
# NAME       STATUS    RESOURCE NAME              ARN
# greeting   Ready     workflows-demo-greeting    arn:aws:states:us-east-1:123456789012:stateMachine:workflows-demo-greeting
```

Get detailed status:

```bash
kubectl describe stepfunctionsstatemachine greeting -n workflows-demo
```

Expected output:
```
Name:         greeting
Namespace:    workflows-demo
...
Status:
  Resource Name:  workflows-demo-greeting
  Naming Status:  valid
  Predicted ARN:  arn:aws:states:us-east-1:123456789012:stateMachine:workflows-demo-greeting
  State Machine ARN: arn:aws:states:us-east-1:123456789012:stateMachine:workflows-demo-greeting
  Conditions:
    Last Transition Time:  2024-01-15T10:30:00Z
    Status:                True
    Type:                  ReconcileSucceeded
```

## Step 5: Application Team — Trigger an Execution

Use the AWS CLI to start an execution:

```bash
# Get the state machine ARN
STATE_MACHINE_ARN=$(kubectl get stepfunctionsstatemachine greeting -n workflows-demo \
  -o jsonpath='{.status.stateMachineArn}')

echo "State Machine ARN: $STATE_MACHINE_ARN"

# Start an execution
aws stepfunctions start-execution \
  --state-machine-arn "$STATE_MACHINE_ARN" \
  --region us-east-1 \
  --input '{"name": "Alice"}'
# Output: {"executionArn": "arn:aws:states:us-east-1:123456789012:execution:workflows-demo-greeting:...", "startDate": 1705317000.0}
```

Get the execution result:

```bash
EXECUTION_ARN="arn:aws:states:us-east-1:123456789012:execution:workflows-demo-greeting:YOUR-EXECUTION-ID"

aws stepfunctions describe-execution \
  --execution-arn "$EXECUTION_ARN" \
  --region us-east-1

# Output includes status and output
```

## Step 6: Application Team — Advanced Example with Lambda

Create a more complex state machine that invokes Lambda functions:

```yaml
# order-processor.yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsStateMachine
metadata:
  name: order-processor
  namespace: workflows-demo
spec:
  definition: |
    {
      "Comment": "Process customer orders",
      "StartAt": "ValidateOrder",
      "States": {
        "ValidateOrder": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Parameters": {
            "FunctionName": "validate-order",
            "Payload.$": "$"
          },
          "Retry": [
            {
              "ErrorEquals": ["States.TaskFailed"],
              "IntervalSeconds": 2,
              "MaxAttempts": 3,
              "BackoffRate": 2.0
            }
          ],
          "Catch": [
            {
              "ErrorEquals": ["States.ALL"],
              "Next": "ValidationFailed"
            }
          ],
          "Next": "ProcessPayment"
        },
        "ProcessPayment": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Parameters": {
            "FunctionName": "process-payment",
            "Payload.$": "$"
          },
          "Next": "SendConfirmation"
        },
        "SendConfirmation": {
          "Type": "Task",
          "Resource": "arn:aws:states:::sns:publish",
          "Parameters": {
            "TopicArn": "arn:aws:sns:us-east-1:123456789012:order-notifications",
            "Message.$": "$"
          },
          "End": true
        },
        "ValidationFailed": {
          "Type": "Fail",
          "Error": "OrderValidationFailed",
          "Cause": "The order validation failed"
        }
      }
    }

  type: STANDARD
  roleArn: "arn:aws:iam::123456789012:role/step-functions-demo-role"
  loggingLevel: "ERROR"
  logDestinationArn: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/states/workflows-demo"
  tracingEnabled: true
  tags:
    application: order-service
  configRef: "general-policy"
  deletionPolicy: retain
```

Apply it:

```bash
kubectl apply -f order-processor.yaml
```

Trigger an execution:

```bash
EXECUTION_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn "arn:aws:states:us-east-1:123456789012:stateMachine:workflows-demo-order-processor" \
  --region us-east-1 \
  --input '{"orderId": "12345", "amount": 99.99}' \
  --query 'executionArn' \
  --output text)

echo "Execution started: $EXECUTION_ARN"

# Monitor execution
aws stepfunctions describe-execution \
  --execution-arn "$EXECUTION_ARN" \
  --region us-east-1
```

## Step 7: Application Team — Use Production Profile

When you're ready for production, reference the `prod-policy` profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsStateMachine
metadata:
  name: order-processor-prod
  namespace: workflows-demo
spec:
  definition: |
    { ... }
  type: STANDARD
  roleArn: "arn:aws:iam::123456789012:role/step-functions-demo-role"
  
  # Use the production profile with mandatory policies
  configRef: "prod-policy"  # Mandatory logging + tracing enforced
  
  # Even if you specify different values, the mandatory tier wins
  loggingLevel: "OFF"  # Ignored — prod-policy mandatory is ERROR
  tracingEnabled: false  # Ignored — prod-policy mandatory is true
  
  tags:
    application: order-service
    environment: production
  deletionPolicy: retain
```

The actual state machine will have:
- `loggingConfiguration.level: "ERROR"` (from `prod-policy` mandatory, not your `OFF`)
- `tracingConfiguration.enabled: true` (from `prod-policy` mandatory, not your `false`)
- `prod-workflows-demo-order-processor-prod` as the name (from `prod-policy` naming template)

## Step 8: Activity Example (External Workers)

If you have external workers (on-premises, other cloud), create an activity:

```yaml
# data-processor-activity.yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsActivity
metadata:
  name: data-processor
  namespace: workflows-demo
spec:
  configRef: "general-policy"
  tags:
    workload-type: external-worker
  deletionPolicy: retain
```

Apply it:

```bash
kubectl apply -f data-processor-activity.yaml

# Get the activity ARN
kubectl get stepfunctionsactivity data-processor -n workflows-demo \
  -o jsonpath='{.status.activityArn}'
# Output: arn:aws:states:us-east-1:123456789012:activity:workflows-demo-data-processor
```

External workers then poll this activity (see [StepFunctionsActivity User Guide](./stepfunctionsactivity.md) for worker code examples).

## Common Tasks

### Update a State Machine Definition

Edit the resource and apply:

```bash
kubectl edit stepfunctionsstatemachine greeting -n workflows-demo
# Edit the definition field, save and exit
```

### Check Execution Logs

```bash
# View CloudWatch Logs for your state machine
aws logs tail /aws/states/workflows-demo --follow --region us-east-1
```

### List All State Machines in a Namespace

```bash
kubectl get stepfunctionsstatemachine -n workflows-demo -o wide
```

### Monitor State Machine Status

```bash
kubectl describe stepfunctionsstatemachine greeting -n workflows-demo

# Or watch in real-time
kubectl get stepfunctionsstatemachine -n workflows-demo --watch
```

### Delete a State Machine

```bash
# If deletionPolicy is retain, the AWS resource is kept
kubectl delete stepfunctionsstatemachine greeting -n workflows-demo

# If deletionPolicy is delete, the AWS resource is also deleted
```

## Troubleshooting

**"Execution is stuck in RUNNING state"**
- Check CloudWatch Logs: `aws logs tail /aws/states/workflows-demo --region us-east-1`
- Check if Lambda functions or other tasks are failing
- Verify the IAM role has correct permissions

**"Lambda invocation fails in state machine"**
- Verify the IAM role has `lambda:InvokeFunction` permission
- Check Lambda function logs in CloudWatch
- Ensure Lambda function exists and is in the same region

**"State machine name is too long or has invalid characters"**
- Check the naming template in your `StepFunctionsConfig`
- Verify namespace and resource names don't exceed the 80-character limit
- Use `nameOverride` to set a custom name

**"Changes to governance profile aren't being picked up"**
- The `kropath-controller` watches `StepFunctionsConfig` changes
- Verify the controller is running: `kubectl get deployment -n kro-system`
- Recreate the state machine resource to apply new policies

## Next Steps

- [StepFunctionsConfig Governance Reference](./stepfunctionsconfig.md) — Full governance options
- [StepFunctionsStateMachine User Guide](./stepfunctionsstatemachine.md) — Detailed field reference
- [StepFunctionsActivity User Guide](./stepfunctionsactivity.md) — External worker pattern
- [AWS Step Functions Documentation](https://docs.aws.amazon.com/step-functions/)
- [Amazon States Language Reference](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-amazon-states-language.html)
