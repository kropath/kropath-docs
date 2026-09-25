---
title: Complete AWS Network Firewall Deployment Example
description: This example demonstrates a production-ready Network Firewall deployment with governance, rule groups, policies, and firewall instances.
doc_type: reference
---
# Complete AWS Network Firewall Deployment Example

This example demonstrates a production-ready Network Firewall deployment with governance, rule groups, policies, and firewall instances.

## Scenario

Deploy a Network Firewall for a production e-commerce application:
- Block SSH inbound (port 22)
- Allow HTTPS traffic outbound (port 443)
- Monitor all traffic with logging
- Enforce deletion protection and encryption via governance

## Step 1: Define Governance Profile

Create `NetworkFirewallConfig` for production environments:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  mandatory:
    # Enforce protections
    deleteProtection: true
    firewallPolicyChangeProtection: true
    subnetChangeProtection: true
    
    # Enforce encryption
    encryptionType: "CUSTOMER_KMS"
    
    # Enforce rule evaluation
    statefulRuleOrder: "STRICT_ORDER"
    statefulDefaultActions:
      - "aws:drop_strict"
    streamExceptionPolicy: "DROP"
    
    # Enforce logging
    loggingDestination:
      alertLogDestination:
        type: "CloudWatchLogs"
        destination:
          logGroup: "/aws/nfw/prod/alerts"
      flowLogDestination:
        type: "S3"
        destination:
          bucketName: "prod-nfw-logs"
          prefix: "flow/"
    
    # Enforce naming and tags
    namingTemplate: "prod-{namespace}-{name}"
    tags:
      environment: production
      compliance: required
  
  defaults:
    tags:
      cost-center: platform-security
```

## Step 2: Create Rule Groups

### Rule Group 1: Allow HTTPS (Stateless)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallRuleGroup
metadata:
  name: allow-https
  namespace: security-prod
spec:
  configRef: production
  type: STATELESS
  capacity: 100
  description: "Allow HTTPS traffic outbound"
  
  ruleGroup:
    rulesSource:
      statelessRulesAndCustomActions:
        statelessRules:
          - priority: 100
            ruleDefinition:
              actions:
                - "aws:pass"
              matchAttributes:
                protocols:
                  - 6  # TCP
                destinations:
                  - addressDefinition: "0.0.0.0/0"
                destinationPorts:
                  - fromPort: 443
                    toPort: 443
                sources:
                  - addressDefinition: "10.0.0.0/8"   # Internal only
  
  tags:
    rule-type: allowlist
    direction: outbound
```

### Rule Group 2: Block SSH (Stateful)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallRuleGroup
metadata:
  name: block-ssh
  namespace: security-prod
spec:
  configRef: production
  type: STATEFUL
  capacity: 100
  description: "Block SSH inbound (port 22)"
  
  ruleGroup:
    rulesSource:
      statefulRules:
        - action: DROP
          header:
            protocol: TCP
            source: "0.0.0.0/0"
            sourcePort: "ANY"
            destination: "10.0.0.0/8"
            destinationPort: "22"
            direction: FORWARD
          ruleOptions:
            - keyword: sid
              settings:
                - "1"
            - keyword: msg
              settings:
                - "Block SSH"
  
  tags:
    rule-type: blocklist
    direction: inbound
```

### Rule Group 3: Monitor All Traffic (Stateful)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallRuleGroup
metadata:
  name: monitor-all
  namespace: security-prod
spec:
  configRef: production
  type: STATEFUL
  capacity: 500
  description: "Monitor all traffic with alerts"
  
  ruleGroup:
    rulesSource:
      statefulRules:
        # Log all TCP traffic
        - action: ALERT
          header:
            protocol: TCP
            source: "ANY"
            sourcePort: "ANY"
            destination: "ANY"
            destinationPort: "ANY"
            direction: FORWARD
          ruleOptions:
            - keyword: sid
              settings:
                - "2"
            - keyword: msg
              settings:
                - "Monitor TCP traffic"
            - keyword: noalert
              settings: []
  
  tags:
    rule-type: monitoring
```

## Step 3: Create Firewall Policy

Bundle the rule groups into a policy:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallPolicy
metadata:
  name: production-policy
  namespace: security-prod
spec:
  configRef: production
  description: "Production firewall policy with monitoring"
  
  # Stateless processing
  statelessDefaultActions:
    - aws:forward_to_sfe  # Forward to stateful inspection
  statelessFragmentDefaultActions:
    - aws:forward_to_sfe
  statelessRuleGroupReferences:
    - ruleGroupRef: allow-https
      priority: 100
  
  # Stateful processing
  statefulDefaultActions:
    - aws:drop_strict  # Drop unmatched packets (from governance)
  statefulEngineOptions:
    ruleOrder: STRICT_ORDER
  statefulRuleGroupReferences:
    - ruleGroupRef: block-ssh
      priority: 100
    - ruleGroupRef: monitor-all
      priority: 200
  
  tags:
    policy-version: "1.0"
```

## Step 4: Deploy Firewall

Deploy the firewall in production subnets:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallFirewall
metadata:
  name: perimeter-fw
  namespace: security-prod
spec:
  configRef: production
  description: "Production perimeter firewall for e-commerce"
  deletionPolicy: retain  # Prevent accidental deletion
  
  # VPC attachment
  vpcId: vpc-prod-12345678
  
  # Multi-AZ deployment
  subnetMappings:
    - subnetId: subnet-prod-us-east-1a
      ipAddressType: IPV4
    - subnetId: subnet-prod-us-east-1b
      ipAddressType: IPV4
  
  # Firewall policy
  firewallPolicyRef: production-policy
  
  # Protection settings (from governance)
  deleteProtection: true
  firewallPolicyChangeProtection: true
  subnetChangeProtection: true
  
  # Encryption (from governance)
  encryptionType: "CUSTOMER_KMS"
  kmsKeyId: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-5678-1234-567812345678"
  
  # Logging (from governance)
  loggingConfiguration:
    alertLogDestination:
      type: CloudWatchLogs
      destination:
        logGroup: /aws/nfw/prod/alerts
    flowLogDestination:
      type: S3
      destination:
        bucketName: prod-nfw-logs
        prefix: flow/
  
  tags:
    app: ecommerce
    tier: security
    ha: true
```

## Verification

### 1. Check Firewall Status

```bash
kubectl get networkfirewallfirewall -n security-prod
# NAME           RESOURCENAME                STATUS
# perimeter-fw   prod-security-prod-perimeter-fw   Active
```

### 2. Verify Policy Applied

```bash
kubectl describe networkfirewallfirewall perimeter-fw -n security-prod
# Status:
#   Predicted ARN:  arn:aws:network-firewall:us-east-1:123456789012:firewall/prod-security-prod-perimeter-fw
#   Resource Name:  prod-security-prod-perimeter-fw
```

### 3. Check Logs in CloudWatch

```bash
aws logs tail /aws/nfw/prod/alerts --follow
# 2026-01-15 10:30:45 Alert: SSH inbound from 203.0.113.5 to 10.0.1.10:22 BLOCKED
# 2026-01-15 10:30:46 Alert: HTTPS outbound from 10.0.1.5 to 93.184.216.34:443 ALLOWED
```

### 4. Check Flow Logs in S3

```bash
aws s3 ls s3://prod-nfw-logs/flow/ --recursive
# 2026-01-15 10:30:00 prod-nfw-logs flow/AWSLogs/123456789012/network-firewall/...
```

## Testing Rule Changes

### Test: Monitor-Only Mode

Before blocking SSH, run in monitoring mode:

```yaml
# Update block-ssh rule to ALERT instead of DROP
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallRuleGroup
metadata:
  name: block-ssh
  namespace: security-prod
spec:
  configRef: production
  type: STATEFUL
  capacity: 100
  
  ruleGroup:
    rulesSource:
      statefulRules:
        - action: ALERT  # Changed from DROP
          header:
            protocol: TCP
            source: "0.0.0.0/0"
            sourcePort: "ANY"
            destination: "10.0.0.0/8"
            destinationPort: "22"
            direction: FORWARD
          ruleOptions:
            - keyword: sid
              settings:
                - "1"
```

Apply and monitor alerts for 24 hours. Once confident, change back to DROP.

## Troubleshooting

### Issue: Firewall stuck in `Creating` state

1. Check resource conditions:
   ```bash
   kubectl describe networkfirewallfirewall perimeter-fw -n security-prod
   ```

2. Look for naming errors:
   ```bash
   kubectl get networkfirewallfirewall -n security-prod -o jsonpath='{.items[*].status.namingStatus}'
   ```

3. Check policy references:
   ```bash
   kubectl get networkfirewallpolicy -n security-prod
   ```

### Issue: Rules not matching traffic

1. Verify rule group is referenced in policy:
   ```bash
   kubectl describe networkfirewallpolicy production-policy -n security-prod
   ```

2. Check rule priority order (lower = higher priority):
   ```bash
   # Stateless rules 100, 110, 120...
   # Stateful rules 100, 200, 300...
   ```

3. Look for matching criteria mismatch (CIDR, port, protocol)

### Issue: Logs not appearing

1. Verify logging destination configuration:
   ```bash
   kubectl get networkfirewallconfig production -n kro-system -o yaml | grep -A 10 loggingDestination
   ```

2. Verify S3 bucket exists and firewall has write permissions:
   ```bash
   aws s3 ls s3://prod-nfw-logs/
   ```

3. Check CloudWatch log group exists:
   ```bash
   aws logs describe-log-groups --log-group-name-prefix /aws/nfw/
   ```

## Next Steps

1. **Route traffic through firewall** — Update VPC route tables to send traffic through firewall endpoints
2. **Set up CloudWatch alarms** — Alert on dropped packets, policy violations
3. **Enable enhanced logging** — Use Kinesis Data Firehose for centralized log analysis
4. **Implement auto-remediation** — Use Lambda to automatically block IPs or update policies based on threats
5. **Multi-region deployment** — Replicate this configuration to other regions

## Further Reading

- [AWS Network Firewall Documentation](https://docs.aws.amazon.com/network-firewall/)
- [Suricata Rule Writing Guide](https://suricata.readthedocs.io/en/suricata-master/rules/intro.html)
- [VPC Route Tables and Firewall Endpoints](https://docs.aws.amazon.com/network-firewall/latest/userguide/firewall-endpoints.html)
