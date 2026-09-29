---
title: Monitor kropath-aws-controller
linkTitle: Monitor kropath-aws-controller
description: >
  Set up Prometheus monitoring and alerting for the kropath-aws-controller operator.
weight: 10
doc_type: task
---

kropath-aws-controller exposes Prometheus metrics and alerting rules that help you detect common
configuration and operational issues. This guide covers what observability is available and how to
deploy it.

## What's monitored

The controller exposes metrics for:

- **Configuration health** — whether governance configurations are being resolved correctly across
  your cluster namespaces
- **Policy document resolution** — whether IAM policy documents are resolving resource references
  correctly and detecting statement conflicts
- **Label injection** — whether provider resource CRs are being discovered and labelled so that kro
  RGDs can resolve references correctly
- **Reconciler health** — whether reconcilers are active and their CRDs are installed

Alerts fire when:

- Configuration is withheld due to placement failures, leaving RGDs unable to read effective configs
- A namespace is missing required account or region annotations
- Policy document statements have conflicting SIDs or unresolved resource references
- A required CRD is missing from the cluster
- Label injection is off for a provider group, breaking resource discovery

## Common failure modes detected

### Configuration cascade failure — unreferenced config

The most common platform-breaking failure: a `KropathConfig` is in place and correct, but no
`<Service>Config` CR reads it, so `status.effectiveConfig` is never written. This leaves RGDs
unable to resolve configuration in CEL, and resources fail to reconcile. A human operator
investigating this failure has no good signal — the `KropathConfig` looks fine, and the
`<Service>Config` reconciler may not have logged an error.

The `KropathConfigUnreferenced` alert fires when this happens, pointing to the unmapped config
and the namespace where it sits.

## Deploying monitoring

Monitoring is optional and kept separate from the main operator deployment. To enable it:

1. **Install the Prometheus Operator** (if not already present):

   ```bash
   # Using Helm; refer to the Prometheus Operator docs for other install methods
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm install prometheus prometheus-community/kube-prometheus-stack \
     --namespace monitoring --create-namespace
   ```

2. **Deploy kropath-aws-controller's monitoring config**:

   ```bash
   make deploy-monitoring
   ```

   This creates a `PrometheusRule` in the same namespace as the controller, registering the
   alerting rules with Prometheus.

3. **Configure Prometheus to scrape `/metrics`**:

   The operator listens on `:8080` by default. Add a scrape config like:

   ```yaml
   - job_name: 'kropath-aws-controller'
     kubernetes_sd_configs:
     - role: pod
       namespaces:
         names:
         - kro-system  # or your chosen namespace
     relabel_configs:
     - source_labels: [__meta_kubernetes_pod_label_app]
       action: keep
       regex: kropath-operator
     - source_labels: [__meta_kubernetes_pod_container_port_number]
       action: keep
       regex: '8080'
   ```

## Dashboard

A pre-built Grafana dashboard is included in the operator image:

```bash
# Extract the dashboard from the controller source
make deploy-monitoring  # includes dashboard ConfigMap
```

The dashboard gives you at-a-glance visibility into:

- Configuration resolution and placement health
- Policy document ref resolution and SID conflicts
- Label injection and CRD discovery status
- Collector health (whether metric scrapers are working)

## Metric reference

For the detailed metric definitions, labels, and alert expressions, see
[kropath-controller Metrics and Alerts](../../reference/observability/kropath-controller-metrics.md).

## Alerting best practices

### Route by component

Every alert carries `component: kropath-aws-controller`, so you can route all kropath-aws-controller
alerts to a single receiver without enumerating each alert name:

```yaml
routes:
- match:
    component: kropath-aws-controller
  receiver: platform-team
```

### Severity levels

- **Critical** (`severity: critical`) — Tenant workloads are broken or will be immediately. Examples:
  effective config is withheld or label injection is off. Page on these.
- **Warning** (`severity: warning`) — Degraded visibility or transient issues. Examples:
  a policy document has unresolved refs or a reconciler is pending for too long. Investigate on
  your normal schedule.

## Troubleshooting

### Scrape fails with "no metrics endpoint"

Check that the operator's metrics port (default `:8080`) is open and reachable from Prometheus.
Verify the pod is running: `kubectl get pods -n kro-system -l app=kropath-operator`.

### Alerts not firing

Ensure `PrometheusRule` is installed:

```bash
kubectl get prometheusrule -n kro-system
```

If it's not present, run `make deploy-monitoring` again.

### Metrics endpoint shows no series

The operator emits metrics only when reconcilers are active. Verify that CRDs are installed:

```bash
kubectl get crd | grep kropath.run
```

If no CRDs are present, the operator will start but emit no metric series until you apply at least
one `KropathConfig` CR.
