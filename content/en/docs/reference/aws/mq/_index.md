---
title: Amazon MQ
description: Amazon MQ is a managed message broker service for ActiveMQ and RabbitMQ.
doc_type: reference
weight: 340
---
# Amazon MQ

Amazon MQ is a managed message broker service for ActiveMQ and RabbitMQ. Use Amazon MQ for reliable message queuing, event-driven architectures, and application integration.

## Resources

| Resource | Purpose |
|---|---|
| [MQConfig](mqconfig.md) | Define governance policies for brokers (engine type, deployment topology, encryption, logging) |
| [MQBroker](mqbroker.md) | Create and manage individual message brokers with governance applied |

## Quick Start

1. **Define a governance profile:** Create an `MQConfig` in `kro-system` (or your namespace) with your broker policies.
2. **Create a broker:** Deploy an `MQBroker` that references your config profile.
3. **Retrieve credentials:** The broker will pass user credentials via Kubernetes Secrets.

### Minimal Example

```yaml
# Step 1: Define a governance profile
apiVersion: aws.kropath.run/v1alpha1
kind: MQConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  defaults:
    engineType: ACTIVEMQ
    deploymentMode: SINGLE_INSTANCE
    hostInstanceType: mq.t2.micro
    namingTemplate: "{namespace}-{name}"

---
# Step 2: Create a broker
apiVersion: aws.kropath.run/v1alpha1
kind: MQBroker
metadata:
  name: app-broker
  namespace: default
spec:
  configRef: general-policy
  users:
    - username: admin
      passwordSecretRef:
        name: broker-creds
        key: password
  subnetIDs:
    - subnet-12345678
```

## When to Use

- **ActiveMQ:** Traditional JMS queue/topic messaging, message persistence, full AMQP support
- **RabbitMQ:** High-throughput message routing, complex routing rules, AMQP/MQTT/STOMP protocols

## Related Documentation

- [KropathConfig](../../../concepts/controller/label-operator.md) — Organization-wide configuration
- [Naming and Tags](../../../concepts/naming/dynamic-tag-fields-in-naming-templates.md) — Dynamic naming templates and tag propagation
