# MemoryDBParameterGroup — Engine Tuning Parameters

The `MemoryDBParameterGroup` resource represents a named collection of Redis OSS engine configuration parameters (e.g. `maxmemory-policy`, `timeout`, `tcp-keepalive`) applied to MemoryDB clusters to enforce consistent engine tuning. Parameter groups are independently useful and shareable across clusters.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `MemoryDBConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses naming template; sets parameter group name directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` (keep AWS resources) or `"delete"` (remove them) |

### Parameter Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `family` | string | required | Engine family (e.g. `memorydb7` for Redis 7.x) |
| `description` | string | `""` | Human-readable description |
| `parameters` | map | {} | Redis engine parameters as key-value pairs |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | {} | AWS tags; merged with governance tags |
| `syncedLabels` | map | {} | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | {} | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBParameterGroup
metadata:
  name: app-params
  namespace: cache-prod
spec:
  configRef: general-policy
  deletionPolicy: retain
  
  family: memorydb7           # Redis 7.x
  description: "Application cache tuning"
  
  # Redis engine parameters
  parameters:
    maxmemory-policy: "allkeys-lru"    # Eviction policy
    timeout: "300"                     # Client timeout (seconds)
    tcp-keepalive: "60"                # TCP keepalive (seconds)
    appendonly: "no"                   # AOF persistence
    appendfsync: "everysec"            # AOF fsync frequency
  
  # Metadata
  tags:
    service: cache
    environment: production
  syncedLabels:
    team: platform
```

## Common Parameters

| Parameter | Default | Purpose | Example |
|-----------|---------|---------|---------|
| `maxmemory-policy` | `noeviction` | Eviction policy when memory is full | `allkeys-lru` \| `allkeys-lfu` \| `volatile-lru` \| `noeviction` |
| `timeout` | 0 | Client connection timeout (seconds) | `300` (5 minutes) |
| `tcp-keepalive` | 300 | TCP keepalive interval (seconds) | `60` \| `300` |
| `appendonly` | `no` | AOF persistence mode | `no` \| `yes` |
| `appendfsync` | `everysec` | AOF fsync frequency | `always` \| `everysec` \| `no` |
| `databases` | 16 | Number of databases | `16` \| `32` |
| `loglevel` | `notice` | Log level | `debug` \| `verbose` \| `notice` \| `warning` |

**Eviction policies:**
- `noeviction` — Return error when memory full (safe but can block apps)
- `allkeys-lru` — Remove any key using LRU (good for caches)
- `allkeys-lfu` — Remove any key using LFU (good for working sets)
- `allkeys-random` — Remove any key randomly
- `volatile-lru` — Remove expiring keys using LRU
- `volatile-lfu` — Remove expiring keys using LFU

## How to Reference in Clusters

After creating the parameter group, reference it in clusters:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: session-store
  namespace: cache-prod
spec:
  parameterGroupName: app-params  # Reference by name
  # ... other cluster fields
```

## Status Fields

After creation:

```yaml
status:
  resourceName: "cache-prod-app-params"        # effectiveName
  namingStatus: "valid"                        # "valid" | "invalid-unresolved-tokens"
  predictedArn: "arn:aws:memorydb:ap-southeast-2:123456789012:parametergroup/cache-prod-app-params"
  conditions:
    - type: Ready
      status: "True"
      message: "Parameter group is ready"
```

## Governance

`MemoryDBParameterGroup` has **no functional governance fields** beyond tags, labels, and naming. Platform teams do not enforce specific parameter values — those are workload-specific decisions.

Governance fields available:
- **tags** / **syncedLabels** / **syncedAnnotations** — Metadata governance
- **namingTemplate** — Naming convention

See [MemoryDBConfig governance](./memorydbconfig.md) for full governance cascade details.

## Naming

Parameter group names are generated via the governance naming template:

```yaml
# Default: "{namespace}-{name}"
# With namespace=cache-prod, name=app-params
# Result: cache-prod-app-params

# Custom: "params-{tag.env}"
# With tag.env=prod
# Result: params-prod
```

See [Naming Template — Dynamic Tags](../resources/naming-template-dynamic-tags.md) for full syntax.

**AWS constraints:** Starts with letter, alphanumeric + hyphens.

## Update and Delete

### Modify Parameters

Update the `parameters` map:

```yaml
spec:
  parameters:
    maxmemory-policy: "allkeys-lfu"  # Changed from allkeys-lru
    timeout: "300"
    tcp-keepalive: "60"
```

Push the update — all clusters using this group will be updated.

### Delete Parameter Group

By default, parameter groups are retained:

```yaml
spec:
  deletionPolicy: retain
```

To delete the AWS parameter group when the CR is deleted:

```yaml
spec:
  deletionPolicy: delete
```

**Warning:** If clusters are using this parameter group, they must be updated to reference a different group before deletion.

## Tagging

Parameter groups inherit tags from governance:

```yaml
# MemoryDBConfig/general-policy
spec:
  mandatory:
    tags:
      service: memorydb
  defaults:
    tags:
      team: platform

# MemoryDBParameterGroup instance
spec:
  tags:
    workload: session-cache

# Result in ACK ParameterGroup spec.tags:
#   service: memorydb (mandatory)
#   team: platform (defaults)
#   workload: session-cache (instance)
```

## Example: Multi-Workload Setup

```yaml
---
# Session cache (LRU eviction, high performance)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBParameterGroup
metadata:
  name: session-params
  namespace: cache-prod
spec:
  family: memorydb7
  parameters:
    maxmemory-policy: "allkeys-lru"
    timeout: "300"
    tcp-keepalive: "60"
  tags:
    workload: sessions

---
# Rate limiting (strict, no eviction)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBParameterGroup
metadata:
  name: ratelimit-params
  namespace: cache-prod
spec:
  family: memorydb7
  parameters:
    maxmemory-policy: "noeviction"
    timeout: "30"
    tcp-keepalive: "30"
  tags:
    workload: rate-limiting

---
# Leaderboard (sorted sets, LFU)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBParameterGroup
metadata:
  name: leaderboard-params
  namespace: cache-prod
spec:
  family: memorydb7
  parameters:
    maxmemory-policy: "allkeys-lfu"
    timeout: "0"
    tcp-keepalive: "300"
  tags:
    workload: leaderboards

---
# Session cluster using session parameters
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: sessions
  namespace: cache-prod
spec:
  parameterGroupName: session-params
  nodeType: db.r7g.large
  # ... other fields

---
# Rate limit cluster using strict parameters
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: rate-limiter
  namespace: cache-prod
spec:
  parameterGroupName: ratelimit-params
  nodeType: db.r7g.large
  # ... other fields

---
# Leaderboard cluster using LFU parameters
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: leaderboard
  namespace: cache-prod
spec:
  parameterGroupName: leaderboard-params
  nodeType: db.r7g.large
  # ... other fields
```

## Common Tasks

### Create default parameter group (all defaults)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBParameterGroup
metadata:
  name: default-params
  namespace: cache
spec:
  family: memorydb7
  # parameters omitted — uses AWS defaults
```

### Create LRU cache (cache-friendly eviction)

```yaml
spec:
  family: memorydb7
  parameters:
    maxmemory-policy: "allkeys-lru"
    timeout: "300"
```

### Create strict rate limiter (no eviction)

```yaml
spec:
  family: memorydb7
  parameters:
    maxmemory-policy: "noeviction"
    timeout: "10"
    tcp-keepalive: "10"
```

### Enable persistence (AOF)

```yaml
spec:
  family: memorydb7
  parameters:
    appendonly: "yes"
    appendfsync: "everysec"
```

### Adjust logging

```yaml
spec:
  family: memorydb7
  parameters:
    loglevel: "debug"       # More detail for troubleshooting
```

## Parameter Family

The `family` field specifies the Redis engine version:

| Family | Redis Version | Status |
|--------|---------------|--------|
| `memorydb7` | 7.0 and later | Current |
| `memorydb6` | 6.x | Legacy |

Use `memorydb7` for new deployments.

## AWS Defaults

If a parameter is not specified, AWS MemoryDB uses built-in defaults:

```yaml
# Explicit (safe for production)
parameters:
  maxmemory-policy: "allkeys-lru"
  timeout: "300"
  tcp-keepalive: "60"

# Implicit (uses AWS defaults; fine for most workloads)
# parameters: {}
```

## Updating Clusters with New Parameters

When a parameter group is updated, all clusters using it will be updated:

```yaml
# Update parameter group
spec:
  parameters:
    maxmemory-policy: "allkeys-lfu"  # Changed

# All clusters referencing this group are updated automatically
# Existing data is retained; only engine behavior changes
```

## Additional Resources

- **Cluster configuration:** [MemoryDBCluster](./memorydbcluster.md)
- **Governance policies:** [MemoryDBConfig](./memorydbconfig.md)
- **AWS parameter reference:** [MemoryDB Parameters](https://docs.aws.amazon.com/memorydb/latest/devguide/parameter-groups.html)
- **Redis engine documentation:** [Redis Configuration](https://redis.io/docs/management/config/)
