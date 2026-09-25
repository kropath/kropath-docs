---
title: AWS Step Functions
description: AWS Step Functions is a serverless orchestration service that allows you to coordinate complex workflows across AWS services.
doc_type: reference
weight: 530
---
# AWS Step Functions

AWS Step Functions is a serverless orchestration service that allows you to coordinate complex workflows across AWS services. kropath provides four resource types for managing Step Functions workloads:

- **StepFunctionsConfig** — Governance and control policies for the Step Functions family
- **StepFunctionsStateMachine** — Serverless workflows that coordinate AWS service calls through a declarative state machine definition
- **StepFunctionsActivity** — Named tasks that external workers poll for work, enabling non-AWS compute to participate in workflows
- **StepFunctionsStateMachineAlias** — Stable endpoints that route traffic between state machine versions for blue/green and canary deployments

## When to Use Each

**StepFunctionsStateMachine** is the primary resource. Use it for:
- Durable long-running workflows (Standard type)
- High-throughput short-duration workflows (Express type)
- Coordinating multiple AWS services via Amazon States Language (ASL)
- Executing workflows with built-in error handling, retries, and branching logic

**StepFunctionsActivity** is for:
- External worker-based task polling (on-premises, other cloud providers, custom applications)
- Integrating non-AWS compute into Step Functions workflows
- Less common than direct state machine provisioning

**StepFunctionsStateMachineAlias** is for:
- Blue/green deployments — Instantly switch all traffic from one version to another
- Canary deployments — Route a small percentage of traffic to a new version while keeping most traffic on the stable version
- Traffic splitting — Gradually migrate traffic between workflow versions

**StepFunctionsConfig** is for platform teams to:
- Enforce minimum observability standards (mandatory logging levels, tracing)
- Enforce naming conventions across all state machines, activities, and aliases
- Apply consistent tagging and labeling policies

## Getting Started

See the [Getting Started](./getting-started.md) guide for a complete walkthrough of setting up governance and creating your first state machine.

## Resource Guides

- [StepFunctionsConfig](./stepfunctionsconfig.md) — Governance and control policies
- [StepFunctionsStateMachine](./stepfunctionsstatemachine.md) — State machine user guide
- [StepFunctionsActivity](./stepfunctionsactivity.md) — Activity user guide
- [StepFunctionsStateMachineAlias](./stepfunctionsstatemachinealias.md) — State machine alias user guide
