---
title: "AWS Route53 — DNS & Network Resolution"
description: The AWS Route53 family within kropath provides abstractions for managing Amazon Route53 DNS zones, records, health checks, and hybrid DNS resolver infrastructure.
doc_type: reference
weight: 450
---
# AWS Route53 — DNS & Network Resolution

The AWS Route53 family within kropath provides abstractions for managing Amazon Route53 DNS zones, records, health checks, and hybrid DNS resolver infrastructure. It enables platform engineers to enforce organization-wide DNS controls such as default TTLs, health check intervals, and resolver endpoint types, while allowing application teams to provision hosted zones for application domains, create DNS records with advanced routing policies, configure health checks for DNS failover, and set up Route53 Resolver endpoints for hybrid DNS resolution between on-premises and AWS.

## Prerequisites and Setup

Route53 resources typically integrate with other kropath families:

*   **VPC/EC2 Family:** For private hosted zone VPC associations, resolver endpoint subnets, and security groups.
*   **S3 Family:** For destination buckets in Route53 Resolver query logging configurations.
*   **CloudWatch Family:** For CloudWatch metric health checks and query log destinations.
*   **ELB / CloudFront Family:** For alias records targeting load balancers and CloudFront distributions.

Route53 resources can be created independently, but networking infrastructure (VPCs, subnets, security groups) must exist before creating resolver endpoints.

## Configuration

Kropath's Route53 configuration is managed through two resources: instances of Route53 resource kinds (such as `Route53HostedZone`, `Route53RecordSet`, `Route53HealthCheck`, and resolver resources) for defining individual DNS resources, and `Route53Config` custom resource instances for establishing organization-wide or profile-specific governance policies. These resources leverage the governance cascade to ensure compliance while providing flexibility.

### Route53Config Governance Model

`Route53Config` CRs define per-profile governance settings for Route53 resources. These profiles are referenced by Route53 resource instances via `spec.configRef` (default: `"general-policy"`). Each `Route53Config` includes `mandatory` and `defaults` sections for governance fields:

*   **`mandatory`:** Fields set in this section enforce strict policies that cannot be overridden by resource instances. If a `mandatory` field is set, the instance's corresponding field (if present) is ignored or validated against the mandatory setting.
*   **`defaults`:** Fields set here provide baseline configurations that resource instances can override. They apply only when the instance's corresponding field is not explicitly set.

**Key Governance Fields:**

*   `defaultTTL` (integer): Default DNS cache TTL in seconds for `Route53RecordSet` instances. When set to a non-zero value in `mandatory`, all record sets must use this TTL. When set in `defaults`, it applies to record sets that do not explicitly set a TTL.
*   `healthCheckRequestInterval` (integer): Default health check request interval for `Route53HealthCheck` instances. Valid values: `10` (fast, higher cost) or `30` (standard). Mandatory values override instance choices; default values apply when instances do not specify an interval.
*   `healthCheckFailureThreshold` (integer): Default failure threshold for health checks (range 1–10). Mandatory values override instance choices; default values apply when instances do not specify a threshold.
*   `resolverEndpointType` (string): Default IP address type for `Route53ResolverEndpoint` instances. Valid values: `"IPV4"`, `"IPV6"`, or `"DUALSTACK"`. Mandatory values override instance choices; default values apply when instances do not specify a type. This allows network teams to enforce IPv6 readiness organization-wide.

**Example Profiles:**

*   `general-policy`: A baseline profile (e.g., `defaults.defaultTTL: 300`, `defaults.healthCheckRequestInterval: 30`).
*   `high-availability`: A profile for mission-critical applications (e.g., `mandatory.healthCheckRequestInterval: 10`, `mandatory.healthCheckFailureThreshold: 1`).
*   `ipv6-ready`: A profile enforcing DUALSTACK resolver endpoints (e.g., `mandatory.resolverEndpointType: "DUALSTACK"`).

### Governance Cascade

Kropath employs a governance cascade (ADR-010, ADR-015 §5.3) to resolve effective configuration for Route53 resources. The `kropath-controller` pre-merges all governance sources (from `KropathConfig` and `Route53Config`) into `status.effectiveConfig` on the namespaced `Route53Config` CR. Route53 RGDs read this `status.effectiveConfig` to determine the final, resolved settings.

**When to use `KropathConfig.route53` vs. `Route53Config`:**

*   **`KropathConfig.route53`:** Used for blanket, organization-wide governance that applies across *all* Route53 profiles. For example, setting `KropathConfig.mandatory.route53.defaultTTL: 600` would enforce a 600-second TTL on all Route53RecordSet resources in the organization, regardless of the `Route53Config` profile they use.
*   **`Route53Config`:** Used for per-profile governance. For instance, a `high-availability` `Route53Config` profile might mandate fast health check intervals (10 seconds) only for applications using that profile, allowing other profiles to use the standard 30-second interval.

## Core Route53 Resources

### Route53HostedZone

A Route53 hosted zone is a container for DNS records for a domain. Hosted zones can be public (internet-routable) or private (VPC-scoped for internal service discovery).

**Key Concepts:**

*   **Public zones:** Internet-facing DNS zones accessible to all internet users. Each public zone receives a set of nameservers that must be registered as the zone's authoritative nameservers.
*   **Private zones:** VPC-scoped zones used for internal service discovery within one or more VPCs. Private zones are not accessible from the internet.
*   **Delegation sets:** Reusable sets of nameservers that can be associated with multiple hosted zones. This is useful for DNSSEC and complex DNS management.
*   **Immutable fields:** The `domainName` and `privateZone` fields are immutable after zone creation.

**Core Fields:**

*   `domainName` (string, required, immutable): The fully-qualified domain name (FQDN) for the hosted zone, e.g., `"example.com."` or `"internal.app.local."`.
*   `privateZone` (boolean, default: `false`, immutable): When `true`, the zone is private and must be associated with one or more VPCs.
*   `vpcs` (array of objects, optional): For private zones, the VPCs to associate with the zone. Each entry specifies `vpcID` (string, required) and `vpcRegion` (string, required).
*   `delegationSetID` (string, default: `""`, immutable): ID of a reusable delegation set to associate with the zone.
*   `comment` (string, default: `""`): A human-readable description of the zone.
*   `configRef` (string, default: `"general-policy"`): Reference to the `Route53Config` profile for governance.
*   `deletionPolicy` (string, default: `"retain"`): Behavior upon deletion. Options: `"retain"` (preserve the AWS resource) or `"delete"` (delete the AWS resource).

**Naming Convention:**

Route53 hosted zones are identified by their `domainName` (the DNS identity) and an auto-assigned hosted zone ID. The naming convention does not apply — there is no `effectiveName`, `spec.nameOverride`, or `status.resourceName` field.

**Example:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: Route53HostedZone
metadata:
  name: example-public-zone
  namespace: dns-prod
spec:
  configRef: general-policy
  deletionPolicy: retain
  domainName: "example.com."
  privateZone: false
  tags:
    environment: production
    managed-by: platform-team
```

Private zone example:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: Route53HostedZone
metadata:
  name: internal-zone
  namespace: dns-prod
spec:
  configRef: general-policy
  domainName: "internal.app.local."
  privateZone: true
  vpcs:
    - vpcID: "vpc-12345678"
      vpcRegion: "us-east-1"
    - vpcID: "vpc-87654321"
      vpcRegion: "us-east-1"
  tags:
    environment: internal
```

### Route53RecordSet

A DNS record set within a Route53 hosted zone. Supports all routing policies: simple, weighted, latency-based, geolocation, failover, multivalue answer, and CIDR-based.

**Key Concepts:**

*   **Routing policies:** Advanced DNS routing options that distribute queries based on weights, geographic location, latency, or failover priority.
*   **Alias records:** Special Route53 records that reference AWS resources (ELB, CloudFront, S3 website endpoints). Alias records do not have a TTL — they inherit the TTL from the target resource.
*   **Standard records:** Records with explicit TTL values and resource record values (IP addresses, CNAMEs, etc.).
*   **Health check integration:** Record sets can reference Route53 health checks to control DNS failover behavior.
*   **Cloud tag limitation:** Route53 API does not support tags on record sets. Tag, label, and annotation metadata are applied to the Kubernetes resource only, not as AWS cloud tags.

**Core Fields:**

*   `recordName` (string, required, immutable): The fully-qualified domain name for the record, e.g., `"www.example.com."`.
*   `recordType` (string, required, immutable): DNS record type: `"A"`, `"AAAA"`, `"CNAME"`, `"MX"`, `"TXT"`, `"SRV"`, `"NS"`, `"CAA"`, etc.
*   `hostedZoneRef` (string, required): The name of the `Route53HostedZone` CR in the same namespace.
*   `configRef` (string, default: `"general-policy"`): Reference to the `Route53Config` profile for governance.

**For standard records:**

*   `ttl` (integer, default: `0`): Cache TTL in seconds. When `0`, the TTL from the `Route53Config` cascade is used. Must not be set for alias records.
*   `resourceRecords` (array of strings): DNS record values (IP addresses, CNAMEs, text strings, etc.).

**For alias records:**

*   `aliasTarget` (object): Reference to an AWS resource. Contains:
    *   `dnsName` (string, required): DNS name of the alias target (e.g., ELB DNS name).
    *   `hostedZoneID` (string, required): Hosted zone ID of the alias target.
    *   `evaluateTargetHealth` (boolean, default: `true`): When `true`, the alias record's health depends on the target resource's health.

**Routing Policy Fields** (at most one policy per record set):

*   `setIdentifier` (string, default: `""`, immutable): Unique identifier for weighted, latency, geolocation, or failover record sets.
*   `weight` (integer, default: `-1`): Weight for weighted routing (0–255). `-1` indicates not a weighted record; `0` is valid and means "never route here".
*   `region` (string, default: `""`): AWS region for latency-based routing.
*   `geoLocation` (object): For geolocation routing:
    *   `continentCode` (string, default: `""`): Continent code (e.g., `"NA"`).
    *   `countryCode` (string, default: `""`): Country code (e.g., `"US"`) or `"*"` for default geolocation record.
    *   `subdivisionCode` (string, default: `""`): State/province code.
*   `failover` (string, default: `""`): Failover routing: `"PRIMARY"` or `"SECONDARY"`.
*   `multiValueAnswer` (boolean, default: `false`): When `true`, Route53 returns all healthy values.
*   `cidrRoutingConfig` (object): For CIDR-based routing:
    *   `collectionID` (string, default: `""`): CIDR collection ID.
    *   `locationName` (string, default: `""`): Location name or `"*"` for default CIDR record.

**Health Check Association:**

*   `healthCheckRef` (string, default: `""`): Name of a `Route53HealthCheck` CR in the same namespace. Used to control DNS failover behavior.

**Naming Convention:**

Route53 record sets are identified by their `recordName`, `recordType`, and (for routed records) `setIdentifier`. The naming convention does not apply.

**TTL Governance:**

The `ttl` field follows the `Route53Config` governance cascade:

1. If `Route53Config.mandatory.defaultTTL > 0`, that TTL is enforced for all record sets.
2. Otherwise, if `spec.ttl > 0`, the instance's TTL is used.
3. Otherwise, if `Route53Config.defaults.defaultTTL > 0`, the default TTL is used.
4. Otherwise, a built-in fallback of 300 seconds (5 minutes) is used.

**Example:**

Simple A record:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: Route53RecordSet
metadata:
  name: www-record
  namespace: dns-prod
spec:
  hostedZoneRef: example-public-zone
  recordName: "www.example.com."
  recordType: A
  ttl: 300
  resourceRecords:
    - "192.0.2.1"
  tags:
    service: web
```

Alias record to ELB:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: Route53RecordSet
metadata:
  name: api-alias
  namespace: dns-prod
spec:
  hostedZoneRef: example-public-zone
  recordName: "api.example.com."
  recordType: A
  aliasTarget:
    dnsName: "my-load-balancer-123456.us-east-1.elb.amazonaws.com"
    hostedZoneID: "Z35SXDOTRQ7X7K"
    evaluateTargetHealth: true
```

Weighted routing policy:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: Route53RecordSet
metadata:
  name: app-weighted-primary
  namespace: dns-prod
spec:
  hostedZoneRef: example-public-zone
  recordName: "app.example.com."
  recordType: A
  setIdentifier: primary
  weight: 70
  ttl: 60
  resourceRecords:
    - "192.0.2.10"
  healthCheckRef: app-primary-health
---
apiVersion: aws.kropath.run/v1alpha1
kind: Route53RecordSet
metadata:
  name: app-weighted-secondary
  namespace: dns-prod
spec:
  hostedZoneRef: example-public-zone
  recordName: "app.example.com."
  recordType: A
  setIdentifier: secondary
  weight: 30
  ttl: 60
  resourceRecords:
    - "192.0.2.11"
  healthCheckRef: app-secondary-health
```

Geolocation routing:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: Route53RecordSet
metadata:
  name: content-geo-us
  namespace: dns-prod
spec:
  hostedZoneRef: example-public-zone
  recordName: "content.example.com."
  recordType: A
  setIdentifier: us-servers
  geoLocation:
    countryCode: "US"
  ttl: 300
  resourceRecords:
    - "192.0.2.20"
---
apiVersion: aws.kropath.run/v1alpha1
kind: Route53RecordSet
metadata:
  name: content-geo-eu
  namespace: dns-prod
spec:
  hostedZoneRef: example-public-zone
  recordName: "content.example.com."
  recordType: A
  setIdentifier: eu-servers
  geoLocation:
    continentCode: "EU"
  ttl: 300
  resourceRecords:
    - "192.0.2.21"
---
apiVersion: aws.kropath.run/v1alpha1
kind: Route53RecordSet
metadata:
  name: content-geo-default
  namespace: dns-prod
spec:
  hostedZoneRef: example-public-zone
  recordName: "content.example.com."
  recordType: A
  setIdentifier: default
  geoLocation:
    countryCode: "*"
  ttl: 300
  resourceRecords:
    - "192.0.2.22"
```

### Route53HealthCheck

A Route53 health check monitors the availability of an endpoint or CloudWatch metric. Health checks are used by record sets to control DNS failover behavior.

**Health Check Types:**

*   **Endpoint checks** (`HTTP`, `HTTPS`, `HTTP_STR_MATCH`, `HTTPS_STR_MATCH`, `TCP`): Monitor HTTP/HTTPS/TCP endpoints for availability.
*   **Calculated checks** (`CALCULATED`): Aggregate the health of multiple child health checks.
*   **CloudWatch metric checks** (`CLOUDWATCH_METRIC`): Monitor a CloudWatch alarm's status.

**Core Fields:**

*   `type` (string, required): Health check type. Note: `RECOVERY_CONTROL` is excluded (requires Route53 Application Recovery Controller, which is out of scope).
*   `configRef` (string, default: `"general-policy"`): Reference to the `Route53Config` profile.
*   `deletionPolicy` (string, default: `"retain"`): Behavior upon deletion.

**For endpoint checks:**

*   `ipAddress` (string, default: `""`): IPv4 or IPv6 address of the endpoint.
*   `fullyQualifiedDomainName` (string, default: `""`): Domain name of the endpoint (for Host header).
*   `port` (integer, default: `0`): Port number; `0` uses protocol default (80 for HTTP, 443 for HTTPS).
*   `resourcePath` (string, default: `""`): Path for HTTP/HTTPS checks (e.g., `"/health"`).
*   `searchString` (string, default: `""`): Response body match for `STR_MATCH` types.
*   `enableSNI` (boolean, default: `true`): Send TLS SNI extension for HTTPS checks.

**Request and Failure Thresholds:**

*   `requestInterval` (integer, default: `0`): Health check request interval in seconds: `10` (fast) or `30` (standard). When `0`, the value from `Route53Config` cascade is used.
*   `failureThreshold` (integer, default: `0`): Number of consecutive failures before marking unhealthy (1–10). When `0`, the value from `Route53Config` cascade is used (default: 3).

**Additional fields:**

*   `measureLatency` (boolean, default: `false`, immutable): Enable latency measurement.
*   `inverted` (boolean, default: `false`): Invert health check result.
*   `disabled` (boolean, default: `false`): Disable the health check.
*   `regions` (array of strings, default: `[]`): Limit health checker regions; empty means all regions.

**For calculated checks:**

*   `healthThreshold` (integer, default: `0`): Minimum number of healthy child checks required.
*   `childHealthChecks` (array of strings, default: `[]`): Child health check IDs (raw IDs from Route53 API).

**For CloudWatch metric checks:**

*   `alarmIdentifier` (object): CloudWatch alarm reference:
    *   `name` (string): Alarm name.
    *   `region` (string): Alarm region.
*   `insufficientDataHealthStatus` (string, default: `""`): Status when insufficient data: `"Healthy"`, `"Unhealthy"`, or `"LastKnownStatus"`.

**Naming Convention:**

Route53 health checks are identified by an auto-assigned health check ID. The naming convention does not apply.

**Example:**

HTTP endpoint check:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: Route53HealthCheck
metadata:
  name: app-primary-health
  namespace: dns-prod
spec:
  configRef: high-availability
  type: HTTPS
  fullyQualifiedDomainName: "primary.example.com"
  port: 443
  resourcePath: "/health"
  requestInterval: 10
  failureThreshold: 2
  measureLatency: true
  enableSNI: true
  tags:
    service: app
```

Calculated health check:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: Route53HealthCheck
metadata:
  name: app-aggregate-health
  namespace: dns-prod
spec:
  type: CALCULATED
  healthThreshold: 2
  childHealthChecks:
    - "abc123def456"
    - "def456ghi789"
```

CloudWatch metric health check:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: Route53HealthCheck
metadata:
  name: app-cloudwatch-health
  namespace: dns-prod
spec:
  type: CLOUDWATCH_METRIC
  alarmIdentifier:
    name: "app-availability-alarm"
    region: "us-east-1"
  insufficientDataHealthStatus: "Unhealthy"
```

### Route53ResolverEndpoint

A Route53 Resolver endpoint is an ENI-backed DNS endpoint within a VPC that enables DNS query forwarding between on-premises and AWS. Inbound endpoints receive queries from on-premises; outbound endpoints forward queries to on-premises DNS servers.

**Key Concepts:**

*   **Inbound endpoints:** Receive DNS queries from on-premises or other networks and resolve them using Route53.
*   **Outbound endpoints:** Forward DNS queries from AWS to on-premises or other DNS servers.
*   **IP address types:** Endpoints can be IPv4-only, IPv6-only, or dual-stack (both IPv4 and IPv6).
*   **Multi-subnet requirement:** Endpoints require a minimum of 2 IP addresses in different subnets for high availability.

**Core Fields:**

*   `direction` (string, required): `"INBOUND"` or `"OUTBOUND"`.
*   `resolverEndpointType` (string, default: `""`): IP address type: `"IPV4"`, `"IPV6"`, or `"DUALSTACK"`. When empty, the value from `Route53Config` cascade is used.
*   `ipAddresses` (array of objects, required, minimum 2): Subnet and IP assignments:
    *   `subnetID` (string, required): Subnet in which to create the ENI.
    *   `ip` (string, default: `""`): Optional specific IPv4 address; Route53 auto-assigns if not specified.
    *   `ipv6` (string, default: `""`): Optional specific IPv6 address (for IPv6/DUALSTACK endpoints).
*   `securityGroupIDs` (array of strings, required): Security groups controlling endpoint access.
*   `configRef` (string, default: `"general-policy"`): Reference to the `Route53Config` profile.
*   `deletionPolicy` (string, default: `"retain"`): Behavior upon deletion.
*   `nameOverride` (string, default: `""`): Override the resource name derived from the naming template.

**Naming Convention:**

Resolver endpoints follow the standard naming convention with a default template of `{namespace}-{name}`.

**Example:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: Route53ResolverEndpoint
metadata:
  name: hybrid-inbound-endpoint
  namespace: network-prod
spec:
  configRef: ipv6-ready
  direction: INBOUND
  resolverEndpointType: DUALSTACK
  ipAddresses:
    - subnetID: "subnet-12345678"
    - subnetID: "subnet-87654321"
  securityGroupIDs:
    - "sg-dns-inbound"
  tags:
    environment: production
```

### Route53ResolverRule

A Route53 Resolver forwarding rule that specifies how to route DNS queries for a domain from a VPC to target IP addresses via an outbound resolver endpoint.

**Core Fields:**

*   `ruleType` (string, required): `"FORWARD"` (to on-premises DNS) or `"SYSTEM"` (Route53-managed recursion).
*   `domainName` (string, required): DNS domain to match (e.g., `"corp.example.com"`).
*   `resolverEndpointRef` (string, default: `""`): Name of the `Route53ResolverEndpoint` CR (required for FORWARD rules).
*   `targetIPs` (array of objects): Target DNS servers for FORWARD rules:
    *   `ip` (string, default: `""`): IPv4 address.
    *   `ipv6` (string, default: `""`): IPv6 address (cannot mix IPv4 and IPv6 in same rule).
    *   `port` (integer, default: `53`): DNS port.
*   `configRef` (string, default: `"general-policy"`): Reference to the `Route53Config` profile.
*   `deletionPolicy` (string, default: `"retain"`): Behavior upon deletion.
*   `nameOverride` (string, default: `""`): Override the resource name.

**Naming Convention:**

Resolver rules follow the standard naming convention with a default template of `{namespace}-{name}`.

**IPv6 Support and Constraints:**

*   Rules can use IPv4 or IPv6 target addresses, but not both in the same rule.
*   Create separate rules if both IPv4 and IPv6 forwarding are needed.

**Example:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: Route53ResolverEndpoint
metadata:
  name: hybrid-outbound-endpoint
  namespace: network-prod
spec:
  configRef: general-policy
  direction: OUTBOUND
  resolverEndpointType: IPV4
  ipAddresses:
    - subnetID: "subnet-12345678"
    - subnetID: "subnet-87654321"
  securityGroupIDs:
    - "sg-dns-outbound"

---
apiVersion: aws.kropath.run/v1alpha1
kind: Route53ResolverRule
metadata:
  name: corp-forwarding-rule
  namespace: network-prod
spec:
  configRef: general-policy
  ruleType: FORWARD
  domainName: "corp.example.com"
  resolverEndpointRef: hybrid-outbound-endpoint
  targetIPs:
    - ip: "10.0.0.1"
      port: 53
    - ip: "10.0.0.2"
      port: 53
  tags:
    environment: production
```

### Route53ResolverRuleAssociation

Associates a Route53 Resolver rule with a VPC so that DNS queries originating in the VPC are forwarded according to the rule.

**Core Fields:**

*   `resolverRuleRef` (string, required): Name of the `Route53ResolverRule` CR in the same namespace.
*   `vpcID` (string, required): ID of the VPC to associate.
*   `configRef` (string, default: `"general-policy"`): Reference to the `Route53Config` profile.
*   `deletionPolicy` (string, default: `"retain"`): Behavior upon deletion.
*   `nameOverride` (string, default: `""`): Override the resource name.

**Naming Convention:**

Rule associations follow the standard naming convention with a default template of `{namespace}-{name}`.

**Example:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: Route53ResolverRuleAssociation
metadata:
  name: prod-vpc-rule-association
  namespace: network-prod
spec:
  configRef: general-policy
  resolverRuleRef: corp-forwarding-rule
  vpcID: "vpc-prod-12345678"
```

### Route53ResolverQueryLogConfig

A Route53 Resolver query logging configuration that captures DNS queries from associated VPCs and delivers logs to S3, CloudWatch Logs, or Kinesis Data Firehose.

**Core Fields:**

*   `destinationARN` (string, required, immutable): ARN of the log destination. Valid types:
    *   S3 bucket ARN (e.g., `"arn:aws:s3:::my-bucket"`)
    *   CloudWatch Logs log group ARN (e.g., `"arn:aws:logs:region:account:log-group:/aws/route53/example.com"`)
    *   Kinesis Data Firehose delivery stream ARN
*   `configRef` (string, default: `"general-policy"`): Reference to the `Route53Config` profile.
*   `deletionPolicy` (string, default: `"retain"`): Behavior upon deletion.
*   `nameOverride` (string, default: `""`): Override the resource name.

**Naming Convention:**

Query log configs follow the standard naming convention with a default template of `{namespace}-{name}`.

**Immutability:**

The `destinationARN` is immutable after creation. To change the destination, delete and recreate the log config.

**Example:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: Route53ResolverQueryLogConfig
metadata:
  name: dns-query-logging
  namespace: network-prod
spec:
  configRef: general-policy
  destinationARN: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/route53"
  tags:
    environment: production
```

### Route53ResolverQueryLogConfigAssociation

Associates a VPC with a Route53 Resolver query logging configuration so that DNS queries from the VPC are logged.

**Core Fields:**

*   `resolverQueryLogConfigRef` (string, required): Name of the `Route53ResolverQueryLogConfig` CR in the same namespace.
*   `vpcID` (string, required): ID of the VPC to associate (must be in the same region as the log config).
*   `configRef` (string, default: `"general-policy"`): Reference to the `Route53Config` profile.
*   `deletionPolicy` (string, default: `"retain"`): Behavior upon deletion.

**Regional Constraint:**

The VPC must be in the same AWS region as the query log config. If query logging is needed across regions, create separate query log configs in each region.

**Example:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: Route53ResolverQueryLogConfigAssociation
metadata:
  name: prod-vpc-query-logging
  namespace: network-prod
spec:
  configRef: general-policy
  resolverQueryLogConfigRef: dns-query-logging
  vpcID: "vpc-prod-12345678"
```

## Governance Cascade Explained

The Route53 governance cascade resolves the effective configuration for each resource type:

**For `defaultTTL` (Route53RecordSet):**

1. If `Route53Config.mandatory.defaultTTL > 0`, use mandatory TTL.
2. Else if `spec.ttl > 0`, use instance TTL.
3. Else if `Route53Config.defaults.defaultTTL > 0`, use default TTL.
4. Else use built-in fallback (300 seconds).

**For `healthCheckRequestInterval` and `healthCheckFailureThreshold` (Route53HealthCheck):**

1. If `Route53Config.mandatory.<field> > 0`, use mandatory value.
2. Else if `spec.<field> > 0`, use instance value.
3. Else if `Route53Config.defaults.<field> > 0`, use default value.
4. Else use built-in fallback (30 seconds for interval, 3 for threshold).

**For `resolverEndpointType` (Route53ResolverEndpoint):**

1. If `Route53Config.mandatory.resolverEndpointType != ""`, use mandatory type.
2. Else if `spec.resolverEndpointType != ""`, use instance type.
3. Else if `Route53Config.defaults.resolverEndpointType != ""`, use default type.
4. Else omit (Route53 defaults to `IPV4`).

## Cross-Family References

**Route53 is referenced by:**

*   ELB / CloudFront families: For alias records targeting load balancers and distributions.
*   EKS family: For private hosted zones used in cluster DNS configuration.

**Route53 references:**

*   VPC / EC2 family: Private hosted zone VPC associations, resolver endpoint subnets, security groups.
*   S3 family: Query log destinations (S3 buckets).
*   CloudWatch family: Health check CloudWatch alarms, query log destinations (CloudWatch Logs).

## Known Gaps and Limitations

The following Route53 features are not supported in this phase:

*   **DNSSEC signing** (G-1): Requires KMS key management and `EnableHostedZoneDNSSEC` API calls. Deferred to v2.
*   **Route53 Resolver DNS Firewall** (G-2): Separate CRDs for firewall domains, rules, and associations. Deferred to v2.
*   **RecordSet cloud tags** (G-3): Route53 API does not support tags on record sets. Tags, labels, and annotations are applied to the Kubernetes resource only. This differs from other AWS resources.
*   **Calculated health check child IDs** (G-4): ACK stores child health check IDs as strings, not CR references. Cross-CR reference support deferred to v2.
*   **Private hosted zone VPC association updates** (G-5): ACK `HostedZone` `spec.vpcs` field manages associations at creation; post-creation changes require AWS API calls not directly supported by the ACK CR. Verify ACK controller behavior when updating `spec.vpcs`.

## Complete Example

A complete example setting up DNS with failover:

```yaml
# Route53Config: High-availability profile
apiVersion: aws.kropath.run/v1alpha1
kind: Route53Config
metadata:
  name: high-availability
  namespace: dns-prod
  labels:
    aws.kropath.run/resource-name: high-availability
spec:
  mandatory:
    healthCheckRequestInterval: 10
    healthCheckFailureThreshold: 1
  defaults:
    defaultTTL: 60

---
# Public hosted zone
apiVersion: aws.kropath.run/v1alpha1
kind: Route53HostedZone
metadata:
  name: example-zone
  namespace: dns-prod
spec:
  configRef: high-availability
  deletionPolicy: retain
  domainName: "example.com."
  privateZone: false
  tags:
    environment: production

---
# Primary health check
apiVersion: aws.kropath.run/v1alpha1
kind: Route53HealthCheck
metadata:
  name: primary-health
  namespace: dns-prod
spec:
  configRef: high-availability
  type: HTTPS
  fullyQualifiedDomainName: "primary.example.com"
  port: 443
  resourcePath: "/health"
  enableSNI: true

---
# Secondary health check
apiVersion: aws.kropath.run/v1alpha1
kind: Route53HealthCheck
metadata:
  name: secondary-health
  namespace: dns-prod
spec:
  configRef: high-availability
  type: HTTPS
  fullyQualifiedDomainName: "secondary.example.com"
  port: 443
  resourcePath: "/health"
  enableSNI: true

---
# Primary failover record
apiVersion: aws.kropath.run/v1alpha1
kind: Route53RecordSet
metadata:
  name: app-primary
  namespace: dns-prod
spec:
  configRef: high-availability
  hostedZoneRef: example-zone
  recordName: "app.example.com."
  recordType: A
  setIdentifier: primary
  failover: PRIMARY
  ttl: 60
  resourceRecords:
    - "192.0.2.10"
  healthCheckRef: primary-health

---
# Secondary failover record
apiVersion: aws.kropath.run/v1alpha1
kind: Route53RecordSet
metadata:
  name: app-secondary
  namespace: dns-prod
spec:
  configRef: high-availability
  hostedZoneRef: example-zone
  recordName: "app.example.com."
  recordType: A
  setIdentifier: secondary
  failover: SECONDARY
  ttl: 60
  resourceRecords:
    - "192.0.2.11"
  healthCheckRef: secondary-health
```

## Cross-Provider Notes

While kropath aims for a consistent experience, Route53 features have AWS-specific nuances:

*   **Health check types:** Route53 provides endpoint, calculated, and CloudWatch metric health checks. Other cloud providers offer different health check mechanisms (e.g., GCP Uptime Checks, Azure Traffic Manager health probes).
*   **Routing policies:** Route53's geolocation, latency, and CIDR-based routing are AWS-specific. Other providers may have limited or no equivalents.
*   **Resolver endpoints:** Route53 Resolver is AWS-specific. GCP uses Cloud DNS Server Policies; Azure uses Private Resolver.
*   **Query logging:** Route53 Resolver query logging is AWS-specific; GCP and Azure offer alternative query logging mechanisms.
*   **Naming exemptions:** Several Route53 resources (HostedZone, RecordSet, HealthCheck, QueryLogConfigAssociation) have no provider `name` field and thus omit the naming convention.
