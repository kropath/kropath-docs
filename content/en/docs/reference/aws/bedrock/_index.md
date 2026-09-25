---
title: AWS Bedrock — AI Agent Infrastructure
description: "The AWS Bedrock family within kropath provides abstractions for Amazon Bedrock's AI inference capabilities, agentic AI orchestration, and supporting runtime and tool infrastructure."
doc_type: reference
weight: 60
---
# AWS Bedrock — AI Agent Infrastructure

The AWS Bedrock family within kropath provides abstractions for Amazon Bedrock's AI inference capabilities, agentic AI orchestration, and supporting runtime and tool infrastructure. It enables platform engineers to enforce organization-wide safety controls—mandatory guardrails, approved foundation model allowlists, session timeout limits, and token budget caps—while allowing application teams to provision inference profiles for model access, agents with custom instructions and tool integrations, harnesses that compose models with tools and memory into deployable endpoints, API gateways that expose tools to agents, persistent memory stores for conversational context, and managed browser and code interpreter sandboxes as agent tools.

## Prerequisites and Setup

Bedrock resources integrate with other kropath families:

*   **IAM Family:** For execution role ARNs referenced by agents, harnesses, runtimes, gateways, browsers, and code interpreters via `spec.executionRoleArn` or `spec.executionRoleRef`.
*   **KMS Family:** For encryption key ARNs referenced by agents, gateways, memory stores, and policy engines via `spec.kmsKeyArn` or `spec.kmsKeyRef`.
*   **Lambda Family:** For custom orchestration (agents) and gateway interceptors (gateways) via `spec.customOrchestration.executor.lambda` or `spec.interceptorConfigurations[*].interceptorArn`.

## Configuration

Kropath's Bedrock configuration is managed through `BedrockConfig` custom resources (CRDs) for per-profile governance and `KropathConfig` for organization-wide controls. These resources leverage a ten-tier governance cascade to ensure safety compliance while providing flexibility.

### BedrockConfig Profiles

`BedrockConfig` CRs define per-profile governance settings for Bedrock resources. Each profile includes `mandatory` and `defaults` sections:

*   **`mandatory`:** Fields set in this section enforce strict policies that cannot be overridden by individual resource instances. Examples: forcing a specific guardrail, restricting allowed models, capping agent iterations.
*   **`defaults`:** Fields set here provide baseline configurations that resource instances can override. Examples: default model, default session timeout, default guardrail version.

**Example Profiles:**

*   `general-policy`: A baseline profile with no model restriction, no guardrail enforcement, and the default naming template.
*   `production`: A hardened compliance profile with mandatory guardrails, allowed models restricted to an approved list, max iterations capped at 100, and timeout at 300 seconds.
*   `sandbox`: A development profile with no restrictions and higher token/iteration limits for experimentation.

### BedrockConfig Fields

**Organization and Profile Selection:**
*   `configRef` (string, default: `"general-policy"`): Selects which `BedrockConfig` profile to use. If the named profile does not exist, it falls back to `"general-policy"`.

**Governance Fields (mandatory tier):**
*   `foundationModel` (string): Forces a specific foundation model. When set, instance-level model selection is restricted to this model.
*   `guardrailIdentifier` (string): Forces a specific guardrail to apply to all agents and harnesses using this profile.
*   `guardrailVersion` (string): The guardrail version (e.g., `"DRAFT"` or a numeric version). **Must always be paired with `guardrailIdentifier`.**
*   `allowedModels` ([]string): Restricts which foundation models agents and harnesses can use. An empty list means no restriction. Non-empty lists act as an allowlist.
*   `maxIterations` (integer): Hard cap on agent loop iterations. Prevents runaway loops.
*   `maxTokens` (integer): Hard cap on output tokens. Controls token budget and cost.
*   `timeoutSeconds` (integer): Hard execution time limit in seconds.
*   `idleSessionTTLInSeconds` (integer): Enforced session idle timeout.

**Governance Fields (defaults tier):**
All the above fields also have corresponding defaults values that apply when instances don't specify them and mandatory tiers don't enforce them.

**Metadata and Naming:**
*   `tags` (map<string,string>): Default AWS tags applied to all Bedrock resources using this profile.
*   `syncedLabels` (map<string,string>): Kubernetes labels mirrored as AWS tags with `aws.kropath.run/` prefix.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations mirrored as AWS tags with `aws.kropath.run/` prefix.
*   `namingTemplate` (string): Default naming template token resolution (e.g., `{namespace}-{name}`).

### KropathConfig Bedrock Section

`KropathConfig` manages organization-wide governance that applies across *all* Bedrock profiles and instances:

```yaml
spec:
  mandatory:
    bedrock:
      guardrailIdentifier: "abc123def456"    # All profiles, all namespaces
      guardrailVersion: "1"
      allowedModels:                         # Restrict models org-wide
        - "anthropic.claude-3-5-sonnet-20241022-v2:0"
        - "anthropic.claude-3-haiku-20240307-v1:0"
        - "amazon.titan-text-premier-v1:0"
  defaults:
    bedrock:
      guardrailIdentifier: ""               # No default (override per profile)
      guardrailVersion: ""
```

**When to use `KropathConfig.bedrock` vs. `BedrockConfig`:**

*   **`KropathConfig.bedrock`:** Used for blanket, organization-wide governance. Setting `KropathConfig.mandatory.bedrock.allowedModels` forces all agents and harnesses in the organization to use only those models.
*   **`BedrockConfig`:** Used for per-profile governance. A `pci` profile might mandate a specific guardrail only for resources using that profile.

### Ten-Tier Governance Cascade

The `kropath-controller` pre-merges all governance sources into `status.effectiveConfig` on the namespaced `BedrockConfig` CR. Individual resource RGDs resolve effective configuration as:

```
mandatory.field (KropathConfig global)
  → mandatory.field (BedrockConfig profile)
    → instance spec.field
      → defaults.field (BedrockConfig profile)
        → defaults.field (KropathConfig global)
          → RGD built-in default
```

### Guardrail Pair Semantics

`guardrailIdentifier` and `guardrailVersion` must always be set together at the same governance tier. Setting one in `mandatory` and the other in `defaults` is a misconfiguration that the controller will reject with `status.conditions[type=Valid].status = False` and reason `InvalidGuardrailConfiguration`.

### Model Allowlist and Foundation Model Interaction

When both `foundationModel` (mandatory) and `allowedModels` (mandatory) are set on the resolved `BedrockConfig`, the controller validates that `foundationModel` is a member of `allowedModels`. A mismatch (e.g., `foundationModel: "anthropic.claude-v2"` with `allowedModels: ["anthropic.claude-3-sonnet"]`) causes the controller to set `status.conditions[type=Valid].status = False` with reason `InvalidModelNotInAllowedList`. The controller does not write `status.effectiveConfig` until the misconfiguration is resolved.

## Resource Kinds

### Phase 1 (P0) Resources

#### BedrockInferenceProfile

An application inference profile that tracks metrics and costs for a foundation model. Enables model access control and cost attribution per application.

**Core Fields:**
*   `configRef` (string, default: `"general-policy"`): Selects the BedrockConfig profile.
*   `nameOverride` (string): Bypasses the naming template when set.
*   `deletionPolicy` (string, default: `"retain"`): Retention policy on CR deletion.
*   `description` (string): Human-readable description (immutable after creation).
*   `modelSource` (object, required): The foundation model or system-defined profile to track. Contains `copyFrom` with the model identifier.
*   `tags`, `syncedLabels`, `syncedAnnotations`: Custom metadata.

**Immutable Fields:** `inferenceProfileName` (derived from `effectiveName`), `modelSource`, and `description`.

**Status Outputs:**
*   `resourceName`: Effective name after template substitution.
*   `namingStatus`: `"valid"` or `"invalid-unresolved-tokens"`.
*   `inferenceProfileId`: AWS-assigned inference profile ID.
*   `inferenceProfileArn`: Full ARN.

**Governance:** No governance cascade beyond tags/labels/annotations and naming template.

#### BedrockAgent

An Amazon Bedrock Agent that orchestrates foundation model calls with custom instructions, action groups, guardrails, and memory configuration.

**Core Fields:**
*   `configRef` (string, default: `"general-policy"`): Selects the BedrockConfig profile.
*   `nameOverride` (string): Bypasses the naming template when set.
*   `deletionPolicy` (string, default: `"retain"`): Retention policy.
*   `description` (string): Human-readable description.
*   `foundationModel` (string): Model identifier (base model, inference profile ARN, or provisioned model ARN). **Governable via `BedrockConfig`.**
*   `instruction` (string): Instructions for agent behavior.
*   `agentResourceRoleArn` / `agentResourceRoleRef` (string): IAM role ARN or reference for agent API permissions (mutually exclusive).
*   `guardrailIdentifier` / `guardrailVersion` (string): Guardrail to apply. **Governable via `BedrockConfig`.**
*   `idleSessionTTLInSeconds` (integer): Session idle timeout in seconds. **Governable via `BedrockConfig`.**
*   `orchestrationType` (string, default: `"DEFAULT"`): Orchestration strategy.
*   `memoryConfiguration` (object): Enabled memory types, session summary config, storage duration.
*   `customerEncryptionKeyArn` (string): KMS key ARN for agent encryption.
*   Other fields: `agentCollaboration`, `customOrchestration`, `promptOverrideConfiguration`.

**Governance Cascades:**
*   `foundationModel`: Validated against `allowedModels` if set.
*   `guardrailIdentifier` / `guardrailVersion`: Enforced as a pair.
*   `idleSessionTTLInSeconds`: Enforced or defaulted per the 10-tier cascade.

**Naming:** Default template `{namespace}-{name}`; max 100 characters, pattern `^([0-9a-zA-Z][_-]?){1,100}$`.

#### BedrockHarness

An end-to-end agent harness that wires together a model, tools, memory, and runtime into a deployable agent endpoint. The primary managed deployment primitive for AgentCore-based agents.

**Core Fields:**
*   `configRef`, `nameOverride`, `deletionPolicy`: Standard governance fields.
*   `model` (object, required): One of `bedrockModelConfig`, `geminiModelConfig`, `liteLlmModelConfig`, or `openAiModelConfig`. **`bedrockModelConfig` is governable.**
*   `systemPrompt` (array): List of content blocks (text strings).
*   `allowedTools` (array): Glob patterns for tool access (e.g., `"*"`, `"@builtin"`).
*   `maxIterations`, `maxTokens`, `timeoutSeconds` (integer): Safety controls. **Governable via `BedrockConfig`.**
*   `tools` (array): Agent tools (agentCoreBrowser, agentCoreCodeInterpreter, agentCoreGateway, inlineFunction, remoteMcp).
*   `memory` (object): agentCoreMemoryConfiguration, managedMemoryConfiguration, or disabled.
*   `environment` (object): AgentCore runtime environment with network, lifecycle, filesystem config.
*   `executionRoleArn` / `executionRoleRef` (string): IAM role for harness execution.
*   `authorizerConfiguration` (object): JWT auth config.
*   `truncation` (object): Context truncation strategy.

**Immutable Fields:** `harnessName` (derived from `effectiveName`).

**Governance Fields:** `maxIterations`, `maxTokens`, `timeoutSeconds` follow the 10-tier cascade for safety control.

**Naming:** Default template `{namespace}-{name}`.

#### BedrockHarnessEndpoint

An invocable endpoint for a specific Harness version. Creates a stable URL that routes invocations to the harness.

**Core Fields:**
*   `configRef`, `nameOverride`, `deletionPolicy`: Standard governance fields.
*   `description` (string): Human-readable description.
*   `harnessRef` / `harnessID` (string): Reference to the parent Harness (mutually exclusive, immutable after creation).
*   `targetVersion` (string): Harness version to route to (defaults to latest).

**Immutable Fields:** `name` (derived from `effectiveName`), `harnessID`/`harnessRef`.

**Naming:** Default template `{namespace}-{name}`.

### Phase 2 (P1) Resources

#### BedrockAgentRuntime

An AgentCore Runtime environment hosting agent code as containers or code bundles with configurable network, lifecycle, and filesystem settings.

**Core Fields:**
*   `configRef`, `nameOverride`, `deletionPolicy`: Standard governance fields.
*   `agentRuntimeArtifact` (object, required): CodeConfiguration (S3 location, entryPoint, runtime) or containerConfiguration (containerURI).
*   `networkConfiguration` (object, required): Network mode and optional VPC configuration (security groups, subnets).
*   `roleArn` (string, required): IAM role ARN for runtime permissions.
*   `description`, `environmentVariables`, `lifecycleConfiguration`, `authorizerConfiguration`, `filesystemConfigurations`, `protocolConfiguration`, `requestHeaderConfiguration`.

**Naming:** Default template `{namespace}-{name}`.

#### BedrockAgentRuntimeEndpoint

An invocable endpoint for a specific AgentCore Runtime version.

**Core Fields:**
*   `configRef`, `nameOverride`, `deletionPolicy`: Standard governance fields.
*   `agentRuntimeID` (string, required): ID of the parent AgentCore Runtime.
*   `agentRuntimeVersion` (string): Specific version; defaults to latest.
*   `description`, `endpointName`.

**Naming:** Default template `{namespace}-{name}`.

#### BedrockGateway

An API gateway that exposes tools and data sources (MCP, REST, etc.) to agents with configurable authorization, interceptors, and policy enforcement.

**Core Fields:**
*   `configRef`, `nameOverride`, `deletionPolicy`: Standard governance fields.
*   `authorizerType` (string, required): `CUSTOM_JWT`, `AWS_IAM`, or `NONE`.
*   `protocolType` (string, required): Protocol type (e.g., `MCP`).
*   `description`: Human-readable description.
*   `authorizerConfiguration` (object): JWT config (required when `authorizerType=CUSTOM_JWT`).
*   `exceptionLevel` (string): `DEBUG` for detailed errors.
*   `interceptorConfigurations` (array): Lambda-backed interceptors.
*   `kmsKeyArn` / `kmsKeyRef` (string): KMS key for encryption at rest (mutually exclusive).
*   `policyEngineConfiguration` (object): Policy engine ARN and enforcement mode.
*   `protocolConfiguration` (object): MCP-specific instructions and search type.
*   `roleArn` / `roleRef` (string): IAM role ARN or reference (mutually exclusive).

**Naming:** Default template `{namespace}-{name}`.

#### BedrockGatewayTarget

A backend target registered behind a Gateway. Supports Lambda, API Gateway, MCP server, OpenAPI schema, and Smithy model target types.

**Core Fields:**
*   `configRef`, `nameOverride`, `deletionPolicy`: Standard governance fields.
*   `targetConfiguration` (object, required): One of apiGateway, lambda, mcpServer, openAPISchema, or smithyModel.
*   `gatewayIdentifier` / `gatewayIdentifierRef` (string): Parent gateway ID or reference (mutually exclusive).
*   `description`: Human-readable description.
*   `credentialProviderConfigurations` (array): API key or OAuth2 auth for the target.
*   `metadataConfiguration` (object): Header/query param allowlists.
*   `privateEndpoint` (object): VPC Lattice connectivity config.

**Note:** `GatewayTarget` in the ACK CRD has no `tags` field. Tags are tracked in Kubernetes metadata only, not propagated to the cloud resource.

**Naming:** Default template `{namespace}-{name}`.

#### BedrockMemory

A persistent memory store used by Harnesses to maintain conversational context across sessions. Supports multiple memory strategies (episodic, semantic, summary, user preference, custom).

**Core Fields:**
*   `configRef`, `nameOverride`, `deletionPolicy`: Standard governance fields.
*   `eventExpiryDuration` (integer, required): Duration (int64) after which events expire.
*   `description`: Human-readable description.
*   `encryptionKeyArn` / `encryptionKeyRef` (string): KMS key for encryption (immutable, mutually exclusive).
*   `memoryExecutionRoleArn` / `memoryExecutionRoleRef` (string): IAM role for memory access (mutually exclusive).
*   `memoryStrategies` (array): List of strategy configs (episodic, semantic, summary, user preference, custom).
*   `streamDeliveryResources` (object): Kinesis stream ARN for memory event streaming.

**Immutable Fields:** `name` (derived from `effectiveName`), `encryptionKeyArn`/`encryptionKeyRef`.

**Naming:** Default template `{namespace}-{name}`.

### Phase 3 (P2) Resources

#### BedrockBrowser

A managed browser instance available as an agent tool. Supports enterprise policies, session recording, and cryptographic HTTP message signing.

**Core Fields:**
*   `configRef`, `nameOverride`, `deletionPolicy`: Standard governance fields.
*   `networkConfiguration` (object, required): Network mode and optional VPC configuration (immutable).
*   `description`, `executionRoleArn` / `executionRoleRef`, `browserSigning`, `certificates`, `enterprisePolicies`, `recording` (all immutable after creation).

**Immutable Fields:** All configuration fields are immutable after creation.

**Naming:** Default template `{namespace}-{name}`.

#### BedrockBrowserProfile

A browser configuration profile that defines settings for browser tool instances.

**Core Fields:**
*   `configRef`, `nameOverride`, `deletionPolicy`: Standard governance fields.
*   `description` (string, immutable).

**Immutable Fields:** `name`, `description`.

**Naming:** Default template `{namespace}-{name}`.

#### BedrockCodeInterpreter

A managed code-interpreter sandbox available as an agent tool. Executes code in an isolated environment.

**Core Fields:**
*   `configRef`, `nameOverride`, `deletionPolicy`: Standard governance fields.
*   `networkConfiguration` (object, required): Network mode and optional VPC configuration (immutable).
*   `description`, `executionRoleArn` / `executionRoleRef`, `certificates` (all immutable after creation).

**Immutable Fields:** All configuration fields are immutable after creation.

**Naming:** Default template `{namespace}-{name}`.

### Phase 4 (P3) Resources

#### BedrockPolicyEngine

A Cedar policy engine that evaluates authorization decisions for Gateways. Supports LOG_ONLY and ACTIVE enforcement modes.

**Core Fields:**
*   `configRef`, `nameOverride`, `deletionPolicy`: Standard governance fields.
*   `description` (string, 1–4,096 chars).
*   `encryptionKeyArn` / `encryptionKeyRef` (string): KMS key for encryption (immutable, mutually exclusive).

**Immutable Fields:** `name`, `encryptionKeyArn`/`encryptionKeyRef`.

**Naming:** Default template `{namespace}-{name}`.

#### BedrockPolicy

A Cedar authorization policy attached to a PolicyEngine. Defines access control rules using Cedar policy language.

**Core Fields:**
*   `configRef`, `nameOverride`, `deletionPolicy`: Standard governance fields.
*   `definition` (object, required): Cedar policy statement (cedar.statement string).
*   `policyEngineID` / `policyEngineRef` (string): Parent policy engine ID or reference (immutable, mutually exclusive).
*   `description` (string, 1–4,096 chars).
*   `enforcementMode` (string): `LOG_ONLY` or `ACTIVE`; defaults to `ACTIVE`.
*   `validationMode` (string): `FAIL_ON_ANY_FINDINGS` or `IGNORE_ALL_FINDINGS`; defaults to `FAIL_ON_ANY_FINDINGS`.

**Immutable Fields:** `name`, `policyEngineID`/`policyEngineRef`.

**Note:** `Policy` has no `tags` field in the ACK CRD. Tags are tracked in Kubernetes metadata only.

**Naming:** Default template `{namespace}-{name}`.

#### BedrockAPIKeyCredentialProvider

An API key credential provider backed by a Kubernetes Secret. Used for authenticating against Gateway targets.

**Core Fields:**
*   `configRef`, `nameOverride`, `deletionPolicy`: Standard governance fields.
*   `apiKey` (object, required): Kubernetes Secret reference (name, namespace, key).

**Immutable Fields:** `name`.

**Naming:** Default template `{namespace}-{name}`.

#### BedrockWorkloadIdentity

A workload identity registration with allowed OAuth2 return URLs for agent authentication flows.

**Core Fields:**
*   `configRef`, `nameOverride`, `deletionPolicy`: Standard governance fields.
*   `allowedResourceOauth2ReturnURLs` (array): List of allowed OAuth2 return URLs.

**Immutable Fields:** `name`.

**Naming:** Default template `{namespace}-{name}`.

## Naming Conventions

All Bedrock resources follow the standard kropath naming convention. The default naming template is `{namespace}-{name}`, where:

*   `{namespace}`: The Kubernetes namespace where the resource is created.
*   `{name}`: The Kubernetes resource name (metadata.name).

You can override the template per-resource via `spec.configRef` to use a different `BedrockConfig` profile, or escape it entirely with `spec.nameOverride`. For detailed information on naming tokens, tag field syntax, and provider constraints, see the resource specifications in `kropath-core`.

## Cross-Provider Notes

The Bedrock family is AWS-specific. While kropath aims to provide consistent abstractions across clouds:

*   **GCP Vertex AI** and **Azure AI Service** provide agent orchestration but through fundamentally different API shapes and resource structures. Separate family designs for GCP and Azure will be created as those platforms develop equivalent capabilities.
*   **Inference profiles** are AWS Bedrock–specific; GCP and Azure achieve similar outcomes through general-purpose model serving endpoints.
*   **AgentCore runtime/harness/gateway/memory infrastructure** is unique to AWS Bedrock. GCP and Azure require compositions of general-purpose compute, APIs, and storage services.
*   **Cedar policy engines** for authorization are Bedrock-specific; other clouds use IAM-based access control.

## Example Bedrock Agent Resource Instance

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: BedrockAgent
metadata:
  name: my-support-agent
  namespace: ai-prod
spec:
  configRef: production    # Uses the 'production' BedrockConfig profile
  description: "Customer support agent with knowledge base lookup"
  foundationModel: "anthropic.claude-3-5-sonnet-20241022-v2:0"
  instruction: |
    You are a customer support agent. Help customers with their inquiries
    using the provided tools and knowledge base. Always be polite and helpful.
  agentResourceRoleRef: support-agent-role  # Reference to IAMRole CR
  guardrailIdentifier: "safety-guardrail-001"
  guardrailVersion: "1"
  idleSessionTTLInSeconds: 900
  memoryConfiguration:
    enabledMemoryTypes:
      - "EPISODIC"
      - "SEMANTIC"
    sessionSummaryConfiguration:
      maxRecentSessions: 5
    storageDays: 30
  tags:
    environment: production
    team: customer-support
    data-sensitivity: medium
  syncedLabels:
    compliance: pci
```

## Example Harness with Tools

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: BedrockHarness
metadata:
  name: research-harness
  namespace: ai-prod
spec:
  configRef: production
  model:
    bedrockModelConfig:
      modelIdentifier: "anthropic.claude-3-5-sonnet-20241022-v2:0"
  systemPrompt:
    - text: "You are a research assistant. Help users find information and synthesize knowledge."
  maxIterations: 50
  maxTokens: 100000
  timeoutSeconds: 300
  allowedTools: "*"
  tools:
    - name: web-search
      type: agentCoreGateway
      config:
        agentCoreGateway:
          gatewayIdentifierRef: research-gateway
    - name: browser
      type: agentCoreBrowser
      config:
        agentCoreBrowser:
          browserRef: research-browser
  memory:
    agentCoreMemoryConfiguration:
      memoryIdentifierRef: research-memory
  executionRoleRef: harness-execution-role
  environment:
    agentCoreRuntimeEnvironment:
      networkConfiguration:
        networkMode: "VPC"
        vpcConfiguration:
          securityGroups:
            - sg-12345678
          subnets:
            - subnet-12345678
  tags:
    environment: production
    team: research
```

## Security and Compliance

Bedrock resources inherit organization-wide security controls from `KropathConfig.mandatory.bedrock`:

*   **Guardrail Enforcement:** Mandatory guardrails ensure all agents meet safety baseline requirements.
*   **Model Allowlist:** Restricted model lists prevent use of unapproved or non-compliant models.
*   **Session Timeout:** Enforced idle session timeouts limit exposure windows.
*   **Token Budget:** Enforced token caps control costs and prevent runaway consumption.
*   **Encryption:** References to KMS keys ensure data at rest is encrypted.
*   **Execution Roles:** IAM role requirements ensure least-privilege access.

Platform engineers define these controls in `BedrockConfig` profiles or `KropathConfig.bedrock` section. Application teams provision resources using profiles that enforce compliance by default.

## Known Limitations and Deferred Features

*   **Knowledge Bases:** Not available in current ACK bedrockagent CRDs. Knowledge bases are managed through the AWS Bedrock console or IaC tools separately from kropath.
*   **Action Groups:** Configured inline on the Agent CR, not as standalone reusable resources.
*   **Guardrail Management:** Guardrails are referenced by identifier/version only; creation and management occur outside kropath.
*   **Provisioned Throughput:** Capacity reservation for model inference not yet available.
*   **Model Customization:** Custom model training and fine-tuning managed through AWS console or SageMaker.
*   **Cross-Account Sharing:** Agents and harnesses in one account accessible from another requires manual cross-account IAM configuration.
*   **Credential Rotation:** `BedrockAPIKeyCredentialProvider` credentials (Kubernetes Secrets) require manual rotation lifecycle management.

For details on these gaps and workarounds, see the family design document in `kropath-core`.
