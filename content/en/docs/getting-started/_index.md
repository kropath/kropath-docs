---
title: Getting Started
linkTitle: Getting Started
description: >
  Prerequisites, installation, and provisioning your first governed resource.
weight: 10
doc_type: getting-started
---

This section guides you through setting up kropath for the first time. Learn what you need
before deployment, how to install the platform components into your Kubernetes clusters, and
how to provision your first governed resource end to end.

## Before you start

Familiarize yourself with the foundational concepts in the [Concepts]({{< relref "/docs/concepts" >}})
section — in particular governance tiers, configuration profiles, and how kropath resources
compose within a namespace.

## What is kropath?

kropath is a multi-cloud golden path platform that unifies resource governance across AWS, GCP,
and Azure. It bridges the gap between cloud provider APIs and your platform's operational model,
letting you define once and provision consistently across multiple clouds and multiple accounts.

## Is kropath for you?

kropath is designed for platform teams that manage cloud resources across multiple AWS accounts,
GCP projects, or Azure subscriptions, and want to enforce consistent governance and policy. If you
are building a shared platform where developers provision resources through a standardized
interface, kropath lets you:

- Define policies once and enforce them across all clouds
- Manage permissions and resource naming conventions at scale
- Compose configuration from multiple sources to prevent duplication
- Audit and control what permissions every resource carries

If you are just learning Kubernetes or cloud infrastructure, start with the provider's
documentation and return to kropath once you are managing multiple clouds or multiple accounts.

## Next steps

Choose a starting point based on your role:

- **Platform engineers:** Proceed to the [Tasks]({{< relref "/docs/tasks" >}}) section to learn
  how to set up your first kropath namespace and platform foundation resources.
- **Developers:** Start with the Concepts section to understand how governance works, then
  follow the tasks that apply to your role.
- **Contributors:** See the [Contribution]({{< relref "/docs/contribution" >}}) section to learn
  how to write and submit documentation changes.
