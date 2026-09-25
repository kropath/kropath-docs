---
title: StepFunctionsActivity — User Guide
description: "`StepFunctionsActivity` is a Kubernetes resource that provisions AWS Step Functions activities for external worker-based task polling."
doc_type: reference
---
# StepFunctionsActivity — User Guide

`StepFunctionsActivity` is a Kubernetes resource that provisions AWS Step Functions activities for external worker-based task polling.

## Overview

Activities allow non-AWS compute (on-premises servers, other cloud providers, custom applications) to participate in Step Functions workflows by polling for work. Unlike Lambda functions (which are invoked directly), activities are named tasks that your external workers poll for and complete.

**Use activities when:**
- You have long-running tasks in non-AWS environments (on-premises, other cloud providers)
- Your compute is custom code that runs in containers or on VMs
- You need explicit worker lifecycle management (your workers connect to AWS and pull tasks)

**Don't use activities for:**
- AWS Lambda functions (invoke directly via `"Resource": "arn:aws:states:::lambda:invoke"`)
- Managed AWS services (SNS, SQS, DynamoDB, etc. have direct Step Functions integrations)

## Prerequisites

- A Kubernetes cluster running kropath-aws
- A `StepFunctionsConfig` resource in your namespace (or fallback to `general-policy` in `kro-system`)
- External worker application that polls for tasks (uses the Activity ARN and AWS SDK)

## Basic Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsActivity
metadata:
  name: data-processor
  namespace: workflows-prod
spec:
  # Governance profile (defaults to "general-policy")
  configRef: "general-policy"

  # Optional: custom tags
  tags:
    service: data-processing
    team: engineering

  # Optional: Kubernetes labels synced to cloud
  syncedLabels:
    team: data-science

  # Optional: Kubernetes annotations
  syncedAnnotations:
    runbook: "https://wiki.example.com/data-processor"

  # Optional: deletion policy (retain | delete; defaults to retain)
  deletionPolicy: retain

  # Optional: override the computed resource name
  nameOverride: "custom-data-processor"
```

After applying this resource, external workers can poll for tasks using the activity ARN (shown in `status.activityArn`).

## Resource Fields

### `spec.configRef` (optional, default: "general-policy")

Reference to a `StepFunctionsConfig` governance profile.

The profile defines:
- Naming conventions
- Default tags and labels
- Deletion policies

**Example:**
```yaml
configRef: "pci"  # Use the PCI-DSS compliance profile
```

If the named profile doesn't exist, the system falls back to `general-policy`.

### `spec.tags` (optional)

Custom tags applied to the AWS activity resource.

Merged with governance profile tags. Mandatory tags from the profile cannot be overridden.

**Example:**
```yaml
tags:
  service: data-processing
  cost-center: engineering
```

### `spec.syncedLabels` (optional)

Kubernetes labels synced to both the Kubernetes resource and cloud tags.

These labels appear:
- In Kubernetes `metadata.labels` (prefixed with `aws.kropath.run/`)
- In AWS resource tags (via `allCloudMetadata`)

**Example:**
```yaml
syncedLabels:
  team: data-science
  data-class: internal
```

### `spec.syncedAnnotations` (optional)

Kubernetes annotations synced to the Kubernetes resource metadata.

**Example:**
```yaml
syncedAnnotations:
  runbook: "https://wiki.example.com/data-processor"
  alerts: "pd-oncall-engineering"
```

### `spec.deletionPolicy` (optional, default: "retain")

Deletion policy when the Kubernetes resource is deleted.

- `retain` — Keep the AWS activity (default, safer)
- `delete` — Delete the AWS activity

**Example:**
```yaml
deletionPolicy: delete  # Clean up when resource is deleted
```

### `spec.nameOverride` (optional)

Bypass the computed naming template and use this exact name for the AWS resource.

If omitted, the resource name is computed from the naming template.

**Example:**
```yaml
nameOverride: "my-custom-activity"
```

## Status Fields

After the activity is created, inspect the status:

```bash
kubectl get stepfunctionsactivity data-processor -n workflows-prod -o yaml
```

**Common status fields:**

- `status.resourceName` — The computed AWS resource name
- `status.namingStatus` — `valid` or `invalid-unresolved-tokens`
- `status.predictedArn` — Expected AWS ARN format
- `status.activityArn` — Actual AWS ARN after provisioning (e.g., `arn:aws:states:us-east-1:123456789012:activity:workflows-prod-data-processor`)
- `status.conditions` — Kubernetes standard conditions

## External Worker Pattern

Once the activity is created, external workers connect to AWS and poll for tasks:

### 1. Get the Activity ARN

```bash
kubectl get stepfunctionsactivity data-processor -n workflows-prod \
  -o jsonpath='{.status.activityArn}'
# Output: arn:aws:states:us-east-1:123456789012:activity:workflows-prod-data-processor
```

### 2. Worker Application Polls for Tasks

Example Python worker using Boto3:

```python
import boto3
import json
import time

sfn_client = boto3.client('stepfunctions', region_name='us-east-1')
activity_arn = 'arn:aws:states:us-east-1:123456789012:activity:workflows-prod-data-processor'

def worker_loop():
    while True:
        try:
            # Poll for a task
            response = sfn_client.get_activity_task(
                activityArn=activity_arn,
                workerName='worker-1'
            )
            
            if 'taskToken' in response:
                # Got a task
                task_input = json.loads(response['input'])
                task_token = response['taskToken']
                
                # Do work
                result = process_data(task_input)
                
                # Send result back
                sfn_client.send_task_success(
                    taskToken=task_token,
                    output=json.dumps(result)
                )
            else:
                # No task available, wait and retry
                time.sleep(5)
        
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

def process_data(data):
    # Your processing logic here
    return {"status": "processed", "data": data}

if __name__ == '__main__':
    worker_loop()
```

Example Node.js worker using AWS SDK:

```javascript
const AWS = require('aws-sdk');
const sfn = new AWS.StepFunctions({ region: 'us-east-1' });
const ACTIVITY_ARN = 'arn:aws:states:us-east-1:123456789012:activity:workflows-prod-data-processor';

async function workerLoop() {
  while (true) {
    try {
      // Poll for a task
      const response = await sfn.getActivityTask({
        activityArn: ACTIVITY_ARN,
        workerName: 'worker-1'
      }).promise();

      if (response.taskToken) {
        // Got a task
        const taskInput = JSON.parse(response.input);
        const taskToken = response.taskToken;

        // Do work
        const result = await processData(taskInput);

        // Send result back
        await sfn.sendTaskSuccess({
          taskToken: taskToken,
          output: JSON.stringify(result)
        }).promise();
      } else {
        // No task available, wait and retry
        await new Promise(resolve => setTimeout(resolve, 5000));
      }
    } catch (error) {
      console.error('Error:', error);
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
  }
}

async function processData(data) {
  // Your processing logic here
  return { status: 'processed', data: data };
}

workerLoop().catch(console.error);
```

### 3. State Machine Invokes the Activity

In your state machine definition, reference the activity ARN:

```json
{
  "StartAt": "ProcessData",
  "States": {
    "ProcessData": {
      "Type": "Task",
      "Resource": "arn:aws:states:::activity:process-data",
      "TimeoutSeconds": 3600,
      "Next": "CompleteWorkflow"
    },
    "CompleteWorkflow": {
      "Type": "Pass",
      "End": true
    }
  }
}
```

Or reference dynamically:

```json
{
  "StartAt": "ProcessData",
  "States": {
    "ProcessData": {
      "Type": "Task",
      "Resource.$": "$.activityArn",
      "TimeoutSeconds": 3600,
      "End": true
    }
  }
}
```

## Naming Conventions

By default, activity names follow the pattern `{namespace}-{name}`.

Example:
- Namespace: `workflows-prod`
- Resource name: `data-processor`
- Computed name: `workflows-prod-data-processor`

AWS requires activity names to:
- Use characters `[a-zA-Z0-9\-_]+`
- Maximum 80 characters
- Not contain whitespace
- Be unique per AWS account and region for 90 days after deletion

If you need a custom naming pattern, update the `StepFunctionsConfig` profile's naming template.

## Examples

### Basic Activity

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsActivity
metadata:
  name: simple-worker
  namespace: default
spec:
  tags:
    service: simple
  deletionPolicy: delete
```

### Activity with Full Governance

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsActivity
metadata:
  name: data-processor
  namespace: workflows-prod
spec:
  configRef: "pci"  # PCI-DSS compliance profile
  tags:
    application: data-processing
    cost-center: engineering
  syncedLabels:
    team: data-science
    data-class: internal
  syncedAnnotations:
    runbook: "https://wiki.example.com/data-processor"
    alerts: "pd-oncall-data"
  deletionPolicy: retain
```

### Multiple Activities for Different Workloads

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsActivity
metadata:
  name: cpu-intensive
  namespace: workflows-prod
spec:
  tags:
    workload-type: cpu-intensive
  configRef: "high-performance"

---
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsActivity
metadata:
  name: io-intensive
  namespace: workflows-prod
spec:
  tags:
    workload-type: io-intensive
  configRef: "general-policy"

---
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsActivity
metadata:
  name: batch-processing
  namespace: workflows-prod
spec:
  tags:
    workload-type: batch
  configRef: "batch-policy"
```

## Troubleshooting

**"My activity isn't being created"**
- Check `kubectl get stepfunctionsactivity -n <namespace>` for status
- View detailed events: `kubectl describe stepfunctionsactivity <name> -n <namespace>`
- Ensure the `StepFunctionsConfig` profile exists (or `general-policy` fallback)

**"Workers can't poll for tasks"**
- Verify the `status.activityArn` is correct
- Ensure your workers have AWS credentials configured (IAM role or access keys)
- Verify the worker has permission to call `stepfunctions:GetActivityTask`
- Check CloudWatch Logs for worker errors

**"Tasks aren't being delivered to workers"**
- Verify the activity ARN in your state machine definition matches the actual activity ARN
- Check that workers are polling with the correct `workerName`
- Ensure workers are polling from the same AWS region

**"Activity name conflicts (90-day reuse restriction)"**
- If you deleted an activity and immediately try to recreate it with the same name, AWS will reject it for 90 days
- Workaround: Use a unique suffix with `nameOverride` (e.g., `nameOverride: "data-processor-v2"`)

## See Also

- [StepFunctionsConfig Governance Reference](./stepfunctionsconfig.md)
- [StepFunctionsStateMachine User Guide](./stepfunctionsstatemachine.md)
- [Getting Started](./getting-started.md)
- [AWS Step Functions Activities](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-activities.html)
- [GetActivityTask API Reference](https://docs.aws.amazon.com/step-functions/latest/apireference/API_GetActivityTask.html)
- [SendTaskSuccess API Reference](https://docs.aws.amazon.com/step-functions/latest/apireference/API_SendTaskSuccess.html)
