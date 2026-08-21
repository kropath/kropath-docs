# AWS Step Functions

AWS Step Functions is a serverless orchestration service that allows you to coordinate complex workflows across AWS services. kropath provides three resource types for managing Step Functions workloads:

- **StepFunctionsConfig** — Governance and control policies for the Step Functions family
- **StepFunctionsStateMachine** — Serverless workflows that coordinate AWS service calls through a declarative state machine definition
- **StepFunctionsActivity** — Named tasks that external workers poll for work, enabling non-AWS compute to participate in workflows

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

**StepFunctionsConfig** is for platform teams to:
- Enforce minimum observability standards (mandatory logging levels, tracing)
- Enforce naming conventions across all state machines and activities
- Apply consistent tagging and labeling policies

## Getting Started

See the [Getting Started](./getting-started.md) guide for a complete walkthrough of setting up governance and creating your first state machine.

## Resource Guides

- [StepFunctionsConfig](./stepfunctionsconfig.md) — Governance and control policies
- [StepFunctionsStateMachine](./stepfunctionsstatemachine.md) — State machine user guide
- [StepFunctionsActivity](./stepfunctionsactivity.md) — Activity user guide
