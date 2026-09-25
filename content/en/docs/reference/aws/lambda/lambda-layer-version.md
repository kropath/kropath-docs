---
title: LambdaLayerVersion — Shared Dependencies and Runtime Extensions
description: "The `LambdaLayerVersion` resource packages shared code, libraries, and runtime extensions for reuse across multiple Lambda functions."
doc_type: reference
---
# LambdaLayerVersion — Shared Dependencies and Runtime Extensions

The `LambdaLayerVersion` resource packages shared code, libraries, and runtime extensions for reuse across multiple Lambda functions. Layers reduce deployment package size and centralize common dependencies.

## Overview

Lambda layers enable:
- **Code reuse** — Package libraries once, use in many functions
- **Smaller deployment packages** — Separate application code from dependencies
- **Faster deployments** — Reduce artifact size and transfer time
- **Runtime extensions** — Custom runtimes or monitoring agents

A layer is a ZIP file containing:
- `/python/` — Python modules (installed via pip)
- `/nodejs/` — Node.js modules (node_modules)
- `/java/lib/` — JAR files for Java
- `/opt/` — Custom binaries or runtime extensions

Functions reference layers via ARN; a function can use up to 5 layers.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `LambdaConfig` governance profile to apply (for tags/labels only) |
| `deletionPolicy` | string | `"retain"` | Behavior on resource deletion: `"retain"` (keep AWS layer) or `"delete"` (remove layer) |

### Deployment Package

| Field | Type | Default | Purpose |
|---|---|---|---|
| `code.s3Bucket` | string | required | S3 bucket containing the layer ZIP file |
| `code.s3Key` | string | required | S3 object key for the ZIP file |
| `code.s3ObjectVersion` | string | `""` | Optional S3 version ID; uses latest if empty |

### Compatibility

| Field | Type | Default | Purpose |
|---|---|---|---|
| `compatibleRuntimes` | array | `[]` | Compatible runtimes (e.g., `python3.12`, `nodejs20.x`, `java17`) |
| `compatibleArchitectures` | array | `[]` | Compatible architectures: `x86_64` and/or `arm64` |

### Metadata

| Field | Type | Default | Purpose |
|---|---|---|---|
| `layerDescription` | string | `""` | Human-readable description of the layer's purpose |
| `tags` | map | `{}` | Kubernetes metadata only (AWS Lambda layers do not support cloud tags) |
| `syncedLabels` | map | `{}` | Kubernetes labels (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

**Important:** Layers do NOT support cloud tags (AWS doesn't tag layers). `syncedLabels` and `syncedAnnotations` only apply to Kubernetes.

## Status Outputs

After reconciliation:

| Field | Type | Purpose |
|---|---|---|
| `layerArn` | string | ARN of the layer (without version) |
| `versionNumber` | integer | The published version number (1, 2, 3, ...) |
| `conditions[]` | array | Standard Kubernetes conditions tracking reconciliation progress |

**Note:** Unlike functions, layers have `status.layerArn` and `status.versionNumber` instead of `status.predictedArn`. There is no `status.layerVersionArn` — callers must construct it as `{layerArn}:{versionNumber}`.

## Naming Convention

**Layer names are not generated from templates.** The Kubernetes resource name becomes the layer name directly. AWS adds version numbers automatically as layers are published (v1, v2, v3, etc.).

Example:
- Kubernetes resource name: `db-client-layer`
- Layer name in AWS: `db-client-layer`
- Version 1 ARN: `arn:aws:lambda:us-east-1:123456789012:layer:db-client-layer:1`

## Complete Examples

### Python Database Library Layer

Package a Python database client for reuse:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaLayerVersion
metadata:
  name: db-client
  namespace: libraries
spec:
  code:
    s3Bucket: lambda-layers
    s3Key: db-client/db-client-v2.0.0.zip
  layerDescription: "PostgreSQL client library (psycopg2) for database access"
  compatibleRuntimes:
    - python3.11
    - python3.12
  compatibleArchitectures:
    - x86_64
    - arm64
  tags:
    library: "db-client"
    version: "2.0.0"
```

Result:
- Layer published as version 1
- Available for Python 3.11 and 3.12 functions
- Works on both x86_64 and ARM64

Function using the layer:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunction
metadata:
  name: db-query
  namespace: data-team
spec:
  configRef: general-policy
  code:
    s3Bucket: lambda-code
    s3Key: db-query.zip
  runtime: python3.12
  handler: query.lambda_handler
  layers:
    - "arn:aws:lambda:us-east-1:123456789012:layer:db-client-layer:1"
```

### Node.js HTTP Client Layer

Package a Node.js HTTP client library:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaLayerVersion
metadata:
  name: http-client
  namespace: libraries
spec:
  code:
    s3Bucket: lambda-layers
    s3Key: http-client/http-client-v1.5.0.zip
  layerDescription: "Axios HTTP client for Node.js functions"
  compatibleRuntimes:
    - nodejs18.x
    - nodejs20.x
  compatibleArchitectures:
    - x86_64
    - arm64
```

Result:
- Layer published; version 1 available for Node.js functions

### Custom Runtime Extension Layer

Package a custom monitoring agent or runtime extension:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaLayerVersion
metadata:
  name: monitoring-agent
  namespace: platform
spec:
  code:
    s3Bucket: lambda-layers
    s3Key: monitoring-agent/agent-v1.0.0.zip
  layerDescription: "Custom monitoring agent for CloudWatch integration"
  compatibleRuntimes:
    - python3.12
    - nodejs20.x
  compatibleArchitectures:
    - x86_64
    - arm64
```

Layer ZIP structure:

```
monitoring-agent.zip
├── opt/
│   └── extension  (binary executable)
└── python/
    └── monitoring/  (Python modules for runtime init)
```

Result:
- Extension binary runs as a Lambda extension
- Python modules available in `/opt/python`
- All functions using this layer get the custom agent

### Versioned Layer for Updates

Create a new layer version when dependencies are updated:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaLayerVersion
metadata:
  name: security-libs  # Same name as before
  namespace: libraries
spec:
  code:
    s3Bucket: lambda-layers
    s3Key: security-libs/security-libs-v3.0.0.zip  # Updated package
  layerDescription: "Security libraries (openssl 3.0, cryptography 40.0)"
  compatibleRuntimes:
    - python3.12
  compatibleArchitectures:
    - x86_64
    - arm64
  tags:
    version: "3.0.0"
```

Result:
- Layer published as version 2 (or 3, depending on prior versions)
- Old functions using version 1 continue working
- New functions use version 2
- Gradual migration path: update functions one at a time

## Layer Structure

Layers are extracted to the Lambda execution environment:

- `/opt/python/` → Python modules added to `sys.path`
- `/opt/nodejs/` → Node.js modules added to `NODE_PATH`
- `/opt/java/lib/` → JAR files added to classpath
- `/opt/` → Any directory for custom runtimes or extensions

Example layer ZIP for Python:

```
my-layer.zip
└── python/
    ├── requests/  (package directory)
    ├── boto3/
    └── botocore/
```

When extracted, the function sees:
```
/opt/python/requests
/opt/python/boto3
```

## Governance

**Note:** Layers inherit governance through `configRef` if specified, but layers typically don't have resource-specific governance like memory or encryption. Governance primarily applies to tag/label/annotation merging.

## Key Behaviors

### Immutable Layer Versions

Once a layer version is published, it is immutable. All references to version 1 always point to the exact same code. To update dependencies, create a new version.

### Version Numbers Auto-Increment

Layer versions are numbered automatically (1, 2, 3, ...). The version number is determined by AWS based on publish order.

### Layer Size Limits

Layer code size limit: 50 MB (uncompressed). Layers must be valid ZIP files.

### Function Can Use Up to 5 Layers

Functions can attach up to 5 layers. Layers are merged in order, with later layers overwriting earlier layers if there are file conflicts.

### Compatibility Metadata Optional

`compatibleRuntimes` and `compatibleArchitectures` are optional metadata for documentation. AWS does not enforce them — you can attach a layer to any function regardless of compatibility claims. Set them accurately to help developers choose correct layers.

## Troubleshooting

### "Layer ARN not found"

Ensure the layer ARN is correct and the layer version exists. Layer ARNs must include the version number (e.g., `:layer:db-client-layer:1`, not just `:layer:db-client-layer`).

### "Invalid layer structure"

ZIP file must have the correct directory structure (`python/`, `nodejs/`, `java/lib/`, or `opt/`). Files in the root of the ZIP are ignored.

### Function Still Uses Old Layer Version

Layer references are immutable. To use a new layer version, update the function's `spec.layers` array with the new ARN.

### Multiple Layers Conflicting

If two layers define the same file, the later layer in the array wins. Order matters. Rename files or reorganize layer structure to avoid conflicts.

## Reference

- **Design:** See `kropath-core/docs/families/aws/lambda.md` for layer design
- **AWS Lambda documentation:** https://docs.aws.amazon.com/lambda/latest/dg/layers.html
