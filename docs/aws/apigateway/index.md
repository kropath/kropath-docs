# API Gateway — REST APIs

The `APIGateway` family provides resources for AWS API Gateway REST APIs, including API configuration, REST API creation and management, authorizers, deployment, and access control.

## Overview

The API Gateway family enables platform teams and developers to define, secure, and publish REST APIs on AWS using Kubernetes-native resources. The family includes six core resources:

- **APIGatewayConfig** — Governance configuration; defines security policies, naming conventions, and compliance postures
- **APIGatewayRestAPI** — The primary REST API resource; creates REST API with resources, methods, integrations, and policies
- **APIGatewayAuthorizer** — Authorization layer; supports Lambda token, Lambda request, and Cognito User Pools authorizers
- **APIGatewayDeployment** — Deploying to stages; captures API state and publishes to named endpoints with caching and canary support
- **APIGatewayVPCLink** — Private integrations; connects API Gateway to NLB-backed backends inside VPCs
- **APIGatewayAPIKey** — Access control; API key lifecycle management for usage plans

## Architecture

REST APIs in kropath follow a composite resource model:

```
APIGatewayConfig (governance)
  └─ APIGatewayRestAPI (REST API + resources + methods + integrations)
      ├─ APIGatewayAuthorizer (optional; referenced by methods)
      └─ APIGatewayDeployment (stage + invoke URL)
          └─ APIGatewayVPCLink (optional; referenced by method integrations)

APIGatewayAPIKey (standalone; for usage plans)
```

**Governance cascade:** APIGatewayConfig defines mandatory and defaults tiers for endpoint type, TLS version, API key source, naming, and metadata. All other resources inherit these policies via the `configRef` field.

**Composite design:** APIGatewayRestAPI is a **Composite** resource (ADR-015 §2) that composes ACK `RestAPI`, `Resource`, `Method`, `Integration`, and response mapping CRs into one logical API surface. Similarly, APIGatewayDeployment composes `Deployment` and `Stage` CRs.

## Quick Start

### 1. Deploy a Governance Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory:
    endpointType: ""
    minimumTlsVersion: ""
    apiKeySource: ""
  defaults:
    endpointType: REGIONAL
    minimumTlsVersion: ""
    apiKeySource: HEADER
    namingTemplate: "{namespace}-{name}"
```

### 2. Create a REST API

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayRestAPI
metadata:
  name: orders-api
  namespace: api-prod
spec:
  configRef: general-policy
  description: Orders API
  resources:
    - pathPart: orders
      methods:
        - httpMethod: GET
          integration:
            type: HTTP_PROXY
            uri: https://api.example.com/orders
        - httpMethod: POST
          integration:
            type: AWS_PROXY
            uri: arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789012:function:create-order/invocations
```

### 3. Deploy to a Stage

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: APIGatewayDeployment
metadata:
  name: orders-prod
  namespace: api-prod
spec:
  configRef: general-policy
  restApiRef: orders-api
  stageName: prod
  description: Production stage
```

## Key Concepts

### Governance Cascade

Three layers apply to every API:

1. **Mandatory tier** — Platform-enforced policies (cannot be overridden)
2. **Instance spec** — Developer-specified values
3. **Defaults tier** — Fallback values applied when instance is unset

Example: If APIGatewayConfig.mandatory.endpointType=REGIONAL, all APIs **must** use REGIONAL (no overrides allowed).

### Composite Resources

**APIGatewayRestAPI** and **APIGatewayDeployment** are composite resources that map one Kubernetes CR to multiple AWS resources:

- **APIGatewayRestAPI** → RestAPI + Resources + Methods + Integrations + Response Mappings
- **APIGatewayDeployment** → Deployment + Stage

This design makes APIs "just work" — you don't need to manually manage child resources. kropath handles the wiring.

### Naming Convention

Resources use a naming template to generate AWS cloud names:

- **Template tokens:** `{namespace}`, `{name}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.<key>}`
- **Default:** `{namespace}-{name}` (e.g. `api-prod-orders-api`)
- **Override:** Set `spec.nameOverride` to use a custom name instead

**Note:** APIGatewayDeployment does not use naming templates (AWS assigns Deployment ID; Stage name comes from `spec.stageName`).

### Metadata Wiring

All resources support three levels of metadata:

- **Tags** — AWS cloud tags (for resources that support them)
- **Synced Labels** — Kubernetes labels that also appear as AWS tags (prefixed `aws.kropath.run/`)
- **Synced Annotations** — Kubernetes annotations (prefixed `aws.kropath.run/`)

The governance profile defines org-wide defaults; instances can add custom metadata.

### Deletion Policy

Two deletion policies control what happens when a Kubernetes resource is deleted:

- **retain** (default) — Keep AWS resources; delete only the Kubernetes CR
- **delete** — Delete both Kubernetes CR and AWS resources

```yaml
spec:
  deletionPolicy: retain  # Keep the REST API when the CR is deleted
```

## Resources

- [APIGatewayConfig](apigatewayconfig.md) — Governance profiles and configuration
- [APIGatewayRestAPI](apigatewayrestapi.md) — Create and manage REST APIs
- [APIGatewayAuthorizer](apigatewayauthorizer.md) — Authorization strategies
- [APIGatewayDeployment](apigatewaydeployment.md) — Deploy to stages
- [APIGatewayVPCLink](apigatewayvpclink.md) — Private backend integrations
- [APIGatewayAPIKey](apigatewayapikey.md) — API key lifecycle

## Cross-Provider Notes

- **APIGatewayConfig** is AWS-specific (REST API governance)
- GCP and Azure have their own API management models (deferred)
- This family covers AWS API Gateway REST API (v1); HTTP APIs and WebSocket APIs are in the separate APIGatewayV2 family

## See Also

- [AWS API Gateway REST API — Developer Guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/)
- [ADR-015 — Consolidated Platform Decisions](https://github.com/kropath/kropath-core/blob/main/docs/adrs/015-consolidated-platform-decisions.md) — Governance cascade design
- [APIGatewayV2 Family](../apigatewayv2/index.md) — HTTP APIs and WebSocket APIs
