---
title: Concepts
linkTitle: Concepts
description: >
  Understand kropath's governance architecture, configuration cascade, and resource model.
weight: 10
doc_type: concept
---

# Concepts

kropath is a **governance layer on top of Kubernetes-native cloud provisioning**. It lets platform teams declare policy once — mandatory settings, defaults, naming conventions, and tagging rules — and have every cloud resource created by application teams automatically inherit and enforce those policies.

## Who Uses kropath

- **Platform teams** who need to enforce organization-wide policy across cloud resources without requiring every application team to include the same boilerplate in their manifests.
- **Application teams** who want to provision cloud resources with just the details they care about, leaving governance and defaults to their platform.

## What kropath Provides

1. **A governance model** — Organize policy into organization-wide (`KropathConfig`) and per-service (`<ServiceName>Config`) rules, with a clear precedence so mandatory settings always win.
2. **A resource model** — Simple, high-level resource CRs (`S3Bucket`, `IAMRole`, `LambdaFunction`) that platform teams design, and application teams provision.
3. **A control plane** — A controller that merges governance with application specs and projects the result onto Kubernetes-native provider operators (AWS Controllers for Kubernetes, Google Cloud Controllers, Azure Controllers).

## Getting Started

Read these pages to understand how kropath works:

- **[kropath Architecture]({{< relref "architecture" >}})** — How the pieces fit together: governance CRs, the controller, resource definitions, and cloud providers.
- **[Configuration / Governance]({{< relref "configuration" >}})** — How platform teams declare policy, and how application teams inherit it.
- **[Resources (RGDs)]({{< relref "resources" >}})** — What a resource definition is and how application teams use it.

For hands-on guidance, see the [Tasks]({{< relref "/docs/tasks" >}}) section.
