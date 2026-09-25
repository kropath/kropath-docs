---
title: ElastiCacheParameterGroup — Engine Parameter Tuning
description: "The `ElastiCacheParameterGroup` resource defines engine-specific parameters (Redis, Valkey, or Memcached settings) that can be applied to multiple caches."
doc_type: reference
---
# ElastiCacheParameterGroup — Engine Parameter Tuning

The `ElastiCacheParameterGroup` resource defines engine-specific parameters (Redis, Valkey, or Memcached settings) that can be applied to multiple caches. It centralizes performance tuning decisions and allows you to reuse parameter configurations across cache resources.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects the `ElastiCacheConfig` governance profile |
| `nameOverride` | string | `""` | Bypasses naming template; sets the parameter group name directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` keeps the group in AWS; `"delete"` removes it |

### Parameter Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `description` | string | required | Human-readable description of the parameter group |
| `cacheParameterGroupFamily` | string | required | Engine family (e.g., `"valkey8"`, `"redis7"`, `"memcached1.6"`); **IMMUTABLE after creation** |
| `parameters` | array | optional | Engine-specific parameter overrides (e.g., `maxmemory-policy`, `timeout`) |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | Effective parameter group name (from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if ready, `"invalid-unresolved-tokens"` if template has unresolved tokens |
| `conditions[]` | array | Standard kro conditions (ready, error, etc.) |

## Naming Convention

Parameter group names follow the default template `{namespace}-{name}` → e.g., `app-team-cache-params`.

**Override:** Set `spec.nameOverride` to use a custom name.

## Complete Examples

### Redis Memory Management

A parameter group optimizing Redis for memory efficiency with LRU eviction:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheParameterGroup
metadata:
  name: redis-memory-optimized
  namespace: infrastructure
spec:
  configRef: general-policy
  description: "Redis with LRU eviction for bounded memory"
  cacheParameterGroupFamily: redis7
  parameters:
    - name: maxmemory-policy
      value: "allkeys-lru"  # Evict any key using LRU when max memory reached
    - name: timeout
      value: "300"  # Disconnect idle clients after 300 seconds
    - name: tcp-keepalive
      value: "60"   # TCP keep-alive probe
  deletionPolicy: retain
  tags:
    engine: redis
    tuning: memory-bounded
```

**Result:**
- Applied to Redis 7.x clusters
- Automatic eviction prevents out-of-memory errors
- Idle clients disconnected

### Valkey High-Throughput Settings

A parameter group for high-performance Valkey caches:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheParameterGroup
metadata:
  name: valkey-high-throughput
  namespace: infrastructure
spec:
  configRef: production
  description: "Valkey optimized for high throughput"
  cacheParameterGroupFamily: valkey8
  parameters:
    - name: maxmemory-policy
      value: "noeviction"  # Prevent eviction (requires sufficient memory)
    - name: tcp-backlog
      value: "1024"  # Higher backlog for spike handling
    - name: hz
      value: "10"    # Higher event loop frequency
  deletionPolicy: retain
  tags:
    engine: valkey
    tuning: throughput
  syncedLabels:
    performance-tier: high
```

**Result:**
- Applied to Valkey 8.x clusters
- No eviction (must have sufficient memory)
- Optimized for rapid throughput

### Memcached Connection Tuning

A parameter group for Memcached with optimized connection handling:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheParameterGroup
metadata:
  name: memcached-connection-pool
  namespace: infrastructure
spec:
  configRef: general-policy
  description: "Memcached with optimized connection pool"
  cacheParameterGroupFamily: memcached1.6
  parameters:
    - name: max-item-size
      value: "16777216"  # 16 MB max item size
    - name: connection-max-bytes
      value: "67108864"  # 64 MB connection buffer
  deletionPolicy: retain
  tags:
    engine: memcached
    tuning: connection
```

**Result:**
- Applied to Memcached 1.6 clusters
- Supports larger item sizes
- Optimized connection buffer

## Governance Cascade

Parameter groups follow standard governance for naming and tagging. Engine parameter values are not governed—teams have full control over tuning decisions.

## Key Behaviors

### Family Is Immutable

The `cacheParameterGroupFamily` (e.g., `redis7`, `valkey8`) cannot be changed after creation. To use a different family, create a new parameter group.

### Family Mismatch Causes Failures

If a cache tries to use a parameter group with a mismatched family (e.g., Redis 6 cluster using Valkey 8 parameters), the cache fails to start.

### Parameter Values Are Validated

AWS validates all parameter values against the family's schema. Invalid values are rejected at creation time.

### Parameters Can Be Updated

After creation, you can add or modify parameters and apply the updated group to caches. Caches may need to restart to apply changes.

## Troubleshooting

### "Invalid Parameter Value" Error

A parameter value is outside the valid range or format for the family. Check AWS documentation for the parameter's constraints and adjust.

### "Unsupported Parameter for Family" Error

The parameter doesn't exist in the selected family. Verify the parameter name is valid for your engine (e.g., `maxmemory-policy` is Redis/Valkey only, not Memcached).

### Can't Change Family

The family is immutable. Create a new parameter group with the target family and update cache references.

### Caches Won't Start After Updating Parameters

Some parameters require a cache restart. Check `status.conditions` for error details, or manually restart the cache if needed.

## Common Parameters

### Redis / Valkey

| Parameter | Purpose | Example |
|---|---|---|
| `maxmemory-policy` | Eviction strategy | `"allkeys-lru"`, `"noeviction"` |
| `timeout` | Idle client timeout (seconds) | `"300"` |
| `tcp-keepalive` | TCP keep-alive probe (seconds) | `"60"` |
| `tcp-backlog` | TCP connection backlog | `"1024"` |
| `hz` | Event loop frequency | `"10"` |

### Memcached

| Parameter | Purpose | Example |
|---|---|---|
| `max-item-size` | Max value size (bytes) | `"16777216"` (16 MB) |
| `connection-max-bytes` | Connection buffer size | `"67108864"` (64 MB) |

## Cross-Family Integration

**Cache Resources:** Reference parameter groups via `cacheParameterGroupName` in `[ElastiCacheReplicationGroup](elasticachereplicationgroup.md)` and `[ElastiCacheCluster](elasticachecluster.md)`.

**Engine Versions:** Ensure the family matches your cache's engine (e.g., Valkey 8 clusters use `valkey8` family).

## Next Steps

- Create parameter groups for each engine type and tuning strategy
- Reference them in `[ElastiCacheReplicationGroup](elasticachereplicationgroup.md)` and `[ElastiCacheCluster](elasticachecluster.md)`
- Share parameter groups across multiple caches to standardize tuning
