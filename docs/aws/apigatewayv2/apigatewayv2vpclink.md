# ApiGatewayV2VpcLink — Private VPC Integrations

The `ApiGatewayV2VpcLink` resource enables API Gateway V2 to reach private resources inside a VPC. VPC Links use ENI-based networking to securely route API requests to private ALBs, NLBs, and other backend services without exposing them to the internet.

## Overview

Use `ApiGatewayV2VpcLink` to:

- **Access private backends** — Connect APIs to internal services (ALB, NLB, ECS)
- **Avoid NAT Gateway costs** — Direct ENI-based connectivity without internet gateway
- **Maintain security** — Backend services remain private; API Gateway is the single ingress point
- **Scale elastically** — Multiple APIs can share the same VPC Link

VPC Links are standalone resources that multiple APIs can reference via `connectionRef` in their route integrations.

## Creating a VPC Link

### Basic VPC Link

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2VpcLink
metadata:
  name: internal-vpc-link
  namespace: api-prod
spec:
  configRef: general-policy
  subnetIds:
    - "subnet-12345678"
    - "subnet-87654321"
```

This VPC Link:
- Uses two subnets for redundancy
- Uses the default VPC security group
- Is named `api-prod-internal-vpc-link` (from naming template)

### VPC Link with Custom Security Groups

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2VpcLink
metadata:
  name: secure-vpc-link
  namespace: api-prod
spec:
  configRef: general-policy
  subnetIds:
    - "subnet-12345678"
    - "subnet-87654321"
    - "subnet-99999999"
  securityGroupIds:
    - "sg-api-gateway"
```

This VPC Link:
- Uses three subnets for availability across AZs
- Uses a custom security group (`sg-api-gateway`)
- Enables fine-grained network access control

### Multi-AZ VPC Link

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2VpcLink
metadata:
  name: multi-az-vpc-link
  namespace: api-prod
spec:
  configRef: general-policy
  subnetIds:
    - "subnet-us-east-1a"  # AZ a
    - "subnet-us-east-1b"  # AZ b
    - "subnet-us-east-1c"  # AZ c
  securityGroupIds:
    - "sg-apigw"
```

Spreads VPC Link ENIs across three availability zones for high availability.

## Configuration

### Subnets

**`subnetIds[]`** — Subnets where VPC Link places ENIs

- Type: array of strings
- Required
- Immutable (cannot be changed)
- Minimum 1, typically 2+ for redundancy
- Must be in the same VPC as backend resources

```yaml
spec:
  subnetIds:
    - "subnet-12345678"
    - "subnet-87654321"
```

ENIs are placed in these subnets to reach backend services. API Gateway creates one ENI per subnet.

**Subnet selection guidelines:**

- **Private subnets** — Use private subnets; backends don't need internet connectivity
- **Multiple AZs** — Spread across at least 2 availability zones for fault tolerance
- **Routing to backends** — Route tables must allow traffic to backend service IPs

### Security Groups

**`securityGroupIds[]`** — Security groups controlling ENI-level access

- Type: array of strings
- Default: `[]` (use default VPC security group)
- Immutable (cannot be changed)
- Security groups control which backend services ENIs can reach

```yaml
spec:
  securityGroupIds:
    - "sg-12345678"  # Allow traffic to internal ALB
```

**Security group rules example:**

```
Outbound Rule:
  Protocol: TCP
  Port Range: 80, 443
  Destination: sg-internal-alb  # Security group of backend ALB
```

## Naming

Resource names are generated from a naming template. Default: `{namespace}-{name}`

```yaml
metadata:
  namespace: api-prod
  name: internal-link
# Resulting name: api-prod-internal-link
```

Override:

```yaml
spec:
  nameOverride: "vpc-link-prod"  # Use exactly this name
```

Max length: 128 characters.

## Tags and Labels

Add organization metadata:

```yaml
spec:
  tags:
    team: platform
    environment: production
  syncedLabels:
    app: api-gateway
    vpc-id: vpc-12345678
  syncedAnnotations:
    slack-channel: "#platform-alerts"
```

## Deletion Policy

### Retain (default)

```yaml
spec:
  deletionPolicy: "retain"
```

The VPC Link remains in API Gateway.

### Delete

```yaml
spec:
  deletionPolicy: "delete"
```

The VPC Link is deleted when the CR is deleted.

## Using a VPC Link in an API

Reference the VPC Link by name in route integrations.

### HTTP Proxy Integration with VPC Link

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2HttpApi
metadata:
  name: internal-api
  namespace: api-prod
spec:
  configRef: general-policy
  routes:
    - routeKey: "GET /orders"
      integration:
        type: HTTP_PROXY
        integrationUri: "http://internal-alb.example.internal:8080/orders"
        connectionType: VPC_LINK
        connectionRef: internal-vpc-link  # Reference the VPC Link
```

This route:
- Routes to `http://internal-alb.example.internal:8080/orders`
- Uses the `internal-vpc-link` VPC Link for connectivity
- Reaches the ALB through the private VPC

### AWS Service Integration with VPC Link

```yaml
routes:
  - routeKey: "POST /events"
    integration:
      type: AWS
      integrationUri: "arn:aws:apigateway:us-east-1:events:action/PutEvents"
      connectionType: VPC_LINK
      connectionRef: internal-vpc-link
```

Invoke AWS services through the VPC Link.

### WebSocket API with VPC Link

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2WebSocketApi
metadata:
  name: internal-ws-api
  namespace: api-prod
spec:
  routeSelectionExpression: "$request.body.action"
  routes:
    - routeKey: "$default"
      integration:
        type: HTTP_PROXY
        integrationUri: "http://ws-backend.internal:5000"
        connectionType: VPC_LINK
        connectionRef: internal-vpc-link
```

## Backend Configuration

### ALB (Application Load Balancer)

Configure ALB target group for API Gateway:

```
Target Group Configuration:
  Protocol: HTTP
  Port: 80
  Health Check Path: /health
  Health Check Protocol: HTTP
  Matcher: 200
```

Ensure ALB security group allows inbound traffic from VPC Link security group.

### NLB (Network Load Balancer)

Similar configuration to ALB:

```
Protocol: TCP
Port: 80
Health Check: TCP:80
```

### Private HTTP Service

Any HTTP service in the VPC can be a backend:

```
Requirements:
  - Listening on HTTP or HTTPS
  - Reachable from VPC Link subnets via security groups
  - Optional: DNS record (Route53) for service discovery
```

## Monitoring and Verification

### Check VPC Link Status

```bash
kubectl describe vpclink internal-vpc-link -n api-prod
```

Look for:
- `status.resourceName` — The VPC Link name in AWS
- `status.conditions` — Ready, error, or warning states
- `spec.subnetIds` — Configured subnets

### Test Backend Connectivity

```bash
# SSH into a subnet to test connectivity
ssh -i key.pem ec2-user@<bastion>

# From bastion, test backend
curl http://internal-alb.example.internal:8080/health
```

### View VPC Link Details in AWS

```bash
aws apigatewayv2 get-vpc-link \
  --vpc-link-id <vpc-link-id> \
  --region us-east-1
```

### Monitor CloudWatch Logs

APIs using the VPC Link will show integration latency in CloudWatch metrics:

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name IntegrationLatency \
  --dimensions Name=ApiName,Value=internal-api \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 300 \
  --statistics Average,Maximum
```

Higher integration latency may indicate VPC Link network issues.

## Best Practices

1. **Use multiple subnets** — Distribute ENIs across 2–3 subnets for redundancy
2. **Span availability zones** — Place subnets in different AZs for fault tolerance
3. **Tight security groups** — Restrict outbound rules to necessary backend ports/services
4. **Health checks** — Configure health checks on backends for quick failure detection
5. **Avoid bottlenecks** — VPC Link capacity is tied to the number of ENIs; consider backend load capacity
6. **Document backends** — Maintain a list of which APIs use which VPC Link
7. **Cost optimization** — Share VPC Links across multiple APIs when possible
8. **Monitor latency** — VPC Link adds minimal latency but monitor it to detect issues

## Limitations

- Immutable after creation (subnets and security groups cannot change)
- VPC Link scaling is tied to ENI capacity in target subnets
- Max ENI capacity per subnet is dependent on instance type density
- No cross-VPC VPC Links (backends must be in same VPC)
- Each VPC Link name must be unique per API Gateway region

## Troubleshooting

### VPC Link Creation Fails

**Cause:** Subnets don't exist or are in wrong VPC
**Solution:** Verify subnet IDs exist and are in the correct VPC

### Integration Times Out

**Cause:** Security group rules block traffic or backend is down
**Solution:** 
- Verify security group outbound rules allow backend ports
- Check backend health checks
- Verify backend is reachable from test instance in same subnet

### High Integration Latency

**Cause:** VPC Link overloaded or backend issues
**Solution:**
- Add more subnets to scale VPC Link
- Check backend performance and CPU/memory
- Review CloudWatch logs for errors

## Cross-Provider Notes

- VPC Link is AWS-specific using ENI-based connectivity
- GCP uses Serverless VPC Access Connector for similar functionality
- Azure uses VNet integration or private endpoints
- Each cloud provider has different network architecture and connectivity models

## See Also

- [API Gateway V2](index.md) — Family overview
- [HTTP APIs](apigatewayv2httpapi.md) — Create HTTP APIs with VPC Link integrations
- [WebSocket APIs](apigatewayv2websocketapi.md) — Create WebSocket APIs with VPC Link
- [Stages](apigatewayv2stage.md) — Configure deployment stages
- [Custom Domains](apigatewayv2domainname.md) — Use custom domains with private APIs
