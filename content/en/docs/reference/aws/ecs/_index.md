---
title: AWS ECS Container Orchestration
description: The AWS Elastic Container Service (ECS) family within kropath provides abstractions for managing containerized workloads at scale.
doc_type: reference
weight: 200
---
# AWS ECS Container Orchestration

The AWS Elastic Container Service (ECS) family within kropath provides abstractions for managing containerized workloads at scale. It enables platform engineers to enforce organization-wide controls such as launch type policies, network configuration, task sizing constraints, and naming conventions, while allowing application teams to provision and manage ECS clusters, services, task definitions, and auto-scaling capacity providers for their specific container orchestration needs.

## Prerequisites and Setup

ECS resources in kropath require the following baseline setup:

*   **VPC and Networking:** ECS services must be launched in an AWS VPC with appropriate subnets and security groups configured for container communication.
*   **IAM Integration:** Task execution roles (for ECS agent operations) and task roles (for application permissions) must be defined via the `IAMRole` resource.
*   **CloudWatch (optional):** For Container Insights and logging, CloudWatch log groups must exist or be created alongside ECS resources.
*   **Load Balancing (optional):** Services can integrate with Application Load Balancers (ALB) or Network Load Balancers (NLB) for traffic distribution.
*   **Auto Scaling (optional):** Capacity providers enable automatic scaling of EC2 instances in Fargate or EC2 launch types.

The ECS family consists of five resource kinds:

*   **`ECSConfig`** — Governance configuration for ECS-wide settings (launch types, platform versions, networking, resource sizing, naming).
*   **`ECSCluster`** — Manages ECS clusters, capacity providers, Container Insights, execute command, and service connect defaults.
*   **`ECSService`** — Manages containerized services with deployment strategies, load balancing, networking, and auto-scaling.
*   **`ECSTaskDefinition`** — Defines task specifications including container images, IAM roles, networking, storage, and compute resources.
*   **`ECSCapacityProvider`** — Manages EC2 or Fargate capacity providers with managed auto-scaling and termination protection.

## Configuration

Kropath's ECS configuration is managed through governance and resource instances:

### ECSConfig: Governance Model

`ECSConfig` CRs define per-profile governance settings for all ECS resources. These profiles are referenced by ECS instances via `spec.configRef`. Each `ECSConfig` includes `mandatory` and `defaults` sections for governance fields:

*   **`mandatory`:** Fields set in this section enforce strict policies that cannot be overridden by resource instances. If a `mandatory` field is set, the instance's corresponding field is ignored or validated against the mandatory setting.
*   **`defaults`:** Fields set here provide baseline configurations that resource instances can override. They apply only when the instance's corresponding field is not explicitly set.

#### ECSConfig Core Fields

*   `containerInsights` (boolean, default: `false` in defaults): Controls Container Insights enablement across the cluster. When set in `mandatory`, all clusters must enable or disable Container Insights accordingly.
*   `defaultLaunchType` (string, default: `""` = not enforced): Enforces the launch type for services. Valid values: `"EC2"` (EC2 instances managed by ECS) or `"FARGATE"` (serverless Fargate). Mandatory tier overrides instance selection.
*   `defaultPlatformVersion` (string, default: `"LATEST"` in defaults): The Fargate platform version (e.g., `"1.4.0"`, `"LATEST"`). Applies to Fargate-launched tasks only.
*   `defaultNetworkMode` (string, default: `"awsvpc"` in defaults): The network mode for task definitions. Valid values: `"none"`, `"bridge"`, `"awsvpc"`, `"host"`. `"awsvpc"` is recommended for modern ECS deployments.
*   `defaultTaskCPU` (string, default: `""` = not set): Fargate-only default task CPU. Valid values: `"256"`, `"512"`, `"1024"`, `"2048"`, `"4096"`, etc.
*   `defaultTaskMemory` (string, default: `""` = not set): Fargate-only default task memory in MB. Must be compatible with the selected CPU value.
*   `namingTemplate` (string, default: `"{namespace}-{name}"` in defaults): The pattern for generating ECS resource names (clusters, services, task definition families). ECS resource names are account+region scoped.
*   `tags` (map<string,string>): Custom AWS tags applied to all ECS resources, merged with instance tags.
*   `syncedLabels` (map<string,string>): Kubernetes labels mirrored as AWS tags and prefixed with `aws.kropath.run/`.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations mirrored to AWS resource tags and prefixed with `aws.kropath.run/`.

**Example ECSConfig Profiles:**

*   `general-policy`: A baseline profile enabling Container Insights, defaulting to `awsvpc` network mode, and LATEST platform version.
*   `production`: A hardened profile with mandatory Fargate launch type, mandatory Container Insights, and strict platform version enforcement.
*   `ec2-only`: A profile restricting services to EC2 launch type with custom networking and resource constraints.

#### Ten-Tier Governance Cascade

Kropath employs a ten-tier governance cascade (ADR-010, ADR-015 §5.3) to resolve effective ECS configuration. The `kropath-controller` pre-merges all governance sources (from `KropathConfig` and `ECSConfig`) into `status.effectiveConfig` on the namespaced `ECSConfig` CR. ECS RGDs read this `status.effectiveConfig` to determine final settings.

**When to use `KropathConfig.ecs` vs. `ECSConfig`:**

*   **`KropathConfig.ecs`:** Used for blanket, organization-wide governance that applies across *all* ECS profiles. For example, setting `KropathConfig.mandatory.ecs.containerInsights: true` forces Container Insights on all clusters.
*   **`ECSConfig`:** Used for per-profile governance. For instance, a `production` `ECSConfig` profile might mandate Fargate launch type only for that profile, allowing other profiles to use EC2.

### ECSCluster: Cluster Configuration

An `ECSCluster` resource manages an AWS ECS cluster with capacity providers, Container Insights monitoring, task execution policies, and service defaults.

#### Core Fields

*   `configRef` (string, default: `"general-policy"`): Specifies which `ECSConfig` profile to use for governance.
*   `nameOverride` (string): Allows overriding the cluster name derived from the naming template.
*   `deletionPolicy` (string, default: `"retain"`): Determines behavior upon deletion. Options: `"retain"` (preserve AWS cluster) or `"delete"` (terminate AWS cluster and resources).
*   `tags` (map<string,string>): Custom AWS tags applied to the cluster, merged with governance tags.
*   `syncedLabels` (map<string,string>): Kubernetes labels mirrored as AWS tags.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations mirrored to AWS tags.

#### Capacity Providers

*   `capacityProviders` ([]string): List of capacity provider names (e.g., `["FARGATE", "my-asg-provider"]`). Defines which capacity providers are available to services in this cluster.
*   `defaultCapacityProviderStrategy` ([]object): Default strategy for service placement when no explicit strategy is specified. Each item includes:
    *   `capacityProvider` (string): The capacity provider name.
    *   `weight` (integer, default: `0`): Relative weight for traffic distribution.
    *   `base` (integer, default: `0`): Minimum number of tasks placed on this provider.

#### Container Insights

*   `containerInsights` (boolean, tri-state): Enables CloudWatch Container Insights for detailed cluster monitoring. Follows the governance cascade: mandatory tier > instance value > defaults tier. When not set, defaults to `false`.

#### Execute Command Configuration

Task execute command allows operators to run commands inside running tasks (e.g., for debugging).

```yaml
executeCommandConfiguration:
  logging: DEFAULT                           # Logging backend (NONE | DEFAULT | OVERRIDE)
  kmsKeyID: arn:aws:kms:region:account:key/  # KMS key for log encryption (optional)
  logConfiguration:
    cloudWatchLogGroupName: /ecs/cluster/     # CloudWatch log group name
    s3BucketName: my-ecs-logs                # S3 bucket for logs (if using S3)
    s3KeyPrefix: execute-command/             # S3 prefix for logs
    s3EncryptionEnabled: true                 # Enable S3 encryption
    cloudWatchEncryptionEnabled: true        # Enable CloudWatch encryption
```

#### Service Connect Defaults

Enables AWS service connect for DNS service discovery and inter-service networking.

```yaml
serviceConnectDefaults:
  namespace: "my-namespace"                   # AWS CloudMap namespace for service discovery
```

### ECSService: Service Configuration

An `ECSService` resource manages an ECS service—the construct that runs and maintains desired count of tasks from a task definition.

#### Core Fields

*   `configRef` (string, default: `"general-policy"`): Specifies which `ECSConfig` profile to use.
*   `nameOverride` (string): Allows overriding the service name.
*   `deletionPolicy` (string, default: `"retain"`): Options: `"retain"` or `"delete"`.
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata handling.

#### Launch Type Governance

*   `launchType` (string): `"EC2"` or `"FARGATE"`. Subject to governance cascade (`mandatory` tier > instance > `defaults`).
*   `platformVersion` (string): Fargate platform version (e.g., `"1.4.0"`, `"LATEST"`). Applies when `launchType: FARGATE`.
*   `capacityProviderStrategy` ([]object): Advanced placement using capacity providers (alternative to fixed `launchType`). Each item:
    *   `capacityProvider` (string): Capacity provider name.
    *   `weight` (integer): Relative weight for task distribution.
    *   `base` (integer): Minimum tasks on this provider.

**Note:** `launchType` and `capacityProviderStrategy` are mutually exclusive. The RGD uses CEL validation to enforce this.

#### Networking

*   `networkConfiguration`:
    *   `awsvpcConfiguration`:
        *   `subnets` ([]string): VPC subnets for task ENI attachment.
        *   `securityGroups` ([]string): Security group IDs for task network traffic.
        *   `assignPublicIp` (string, default: `"DISABLED"`): `"ENABLED"` or `"DISABLED"` for public IP assignment.

#### Load Balancing

*   `loadBalancers` ([]object): Attach ALB/NLB to the service. Each item:
    *   `loadBalancerName` or `targetGroupArn`: Load balancer reference.
    *   `containerName` (string): Container in the task definition.
    *   `containerPort` (integer): Port in the container.

#### Deployment Configuration

*   `deploymentConfiguration`:
    *   `maximumPercent` (integer, default: `200`): Maximum % of desired tasks during update.
    *   `minimumHealthyPercent` (integer, default: `100`): Minimum % of healthy tasks.
    *   `deploymentCircuitBreaker`:
        *   `enable` (boolean): Enable circuit breaker to stop deployment on failures.
        *   `rollback` (boolean): Rollback to last stable deployment on failures.
*   `desiredCount` (integer): Desired number of running tasks. Explicitly set to `0` for scale-to-zero.

#### Service Connect

*   `serviceConnectConfiguration`:
    *   `enabled` (boolean): Enable service connect for this service.
    *   `namespace` (string): CloudMap namespace for DNS service discovery.
    *   `services` ([]object): Service endpoint definitions for service connect.

#### Placement (EC2 launch type only)

*   `placementConstraints` ([]object): EC2 instance placement rules (e.g., spread across AZs).

### ECSTaskDefinition: Task Configuration

An `ECSTaskDefinition` resource defines the template for tasks: container images, resource requirements, IAM roles, and volumes.

#### Core Fields

*   `configRef` (string): Governance configuration profile.
*   `nameOverride` (string): Override the task definition family name.
*   `deletionPolicy` (string): `"retain"` or `"delete"`.
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata.

#### Container Definitions

*   `containerDefinitions` ([]object): Array of container specifications. Each container includes:
    *   `name` (string): Container name (must be unique within the task).
    *   `image` (string): Docker image URI (e.g., `"123456789.dkr.ecr.us-east-1.amazonaws.com/my-app:latest"`).
    *   `essential` (boolean, default: `true` per RGD, AWS defaults to `true`): If true, task fails if this container exits.
    *   `cpu` (integer): CPU units (1024 = 1 vCPU).
    *   `memory` (integer): Memory in MB.
    *   `portMappings` ([]object): Container port bindings (requires `hostPort` for EC2, omitted for awsvpc mode).
    *   `environment` ([]object): Environment variables.
    *   `mountPoints` ([]object): Volume mount paths within the container.
    *   `logConfiguration`: CloudWatch logging (driver: `awslogs`).

#### Networking and Resource Sizing

*   `networkMode` (string): `"bridge"`, `"host"`, `"awsvpc"`, or `"none"`. Governed by cascade.
*   `cpu` (string, Fargate only): Task-level CPU (e.g., `"256"`, `"512"`, `"1024"`). Governed by cascade.
*   `memory` (string, Fargate only): Task-level memory in MB (e.g., `"512"`, `"1024"`, `"2048"`). Governed by cascade and must align with CPU selection.

#### IAM Roles

*   `executionRoleARN` (string): ARN of the task execution role (ECS agent permissions).
*   `taskRoleARN` (string): ARN of the task role (application permissions).

#### Volumes

Task definitions support three volume types:

**Host Volumes:**
```yaml
volumes:
  - name: my-host-volume
    host:
      sourcePath: /data         # Path on the EC2 instance
```

**Docker Volumes:**
```yaml
volumes:
  - name: my-docker-volume
    docker:
      sourcePath: /data
      scope: task               # task or shared
```

**EFS Volumes** (for persistent storage):
```yaml
volumes:
  - name: my-efs-volume
    efsVolumeConfiguration:
      fileSystemId: fs-xxxxx
      rootDirectory: /
      transitEncryption: ENABLED
      transportPort: 3049       # Optional: NFS port
      authorizationConfig:
        accessPointId: fsap-xxxx
        iam: ENABLED
```

#### Ephemeral Storage

*   `ephemeralStorage`:
    *   `sizeInGiB` (integer): Scratch space in GiB (20-200, Fargate only). Defaults to 20 GiB when omitted.

#### Revision Model

Task definitions are append-only and immutable: each apply creates a new numbered revision. The `family` field (derived from naming template or `nameOverride`) groups revisions, while `status.revision` exposes the AWS revision number. Services explicitly reference a family (not a revision) and use `"LATEST"` or a specific revision number for task launches.

### ECSCapacityProvider: Auto-Scaling Provider

An `ECSCapacityProvider` resource manages EC2 or Fargate capacity providers for auto-scaling clusters.

#### Core Fields

*   `configRef` (string): Governance configuration.
*   `nameOverride` (string): Override the capacity provider name.
*   `deletionPolicy` (string): `"retain"` or `"delete"`.
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata.

#### Capacity Provider Types

One of two provider types must be specified (mutually exclusive):

**Auto Scaling Group (ASG) Provider:**
```yaml
autoScalingGroupProvider:
  autoScalingGroupArn: arn:aws:autoscaling:region:account:autoScalingGroup:uuid:autoScalingGroupName/name
  managedScaling:
    status: ENABLED
    targetCapacity: 80              # Target CPU/memory utilization (1-100)
    minimumScalingStepSize: 1
    maximumScalingStepSize: 10000
  managedTerminationProtection: ENABLED
```

**Managed Instances Provider** (ECS-managed capacity):
```yaml
managedInstancesProvider:
  infrastructureRoleARN: arn:aws:iam::123456789:role/ecsInstanceRole
  instanceLaunchTemplate:
    launchTemplateId: lt-0123456789abcdef0
    version: "$Default"
```

#### Immutability Constraints

Capacity provider name and cluster association are immutable after creation — they cannot be changed without deleting and recreating the resource.

## Naming Conventions

ECS resource names follow the default naming template `{namespace}-{name}`:

*   **ECSCluster:** Cluster names are region-scoped (not globally unique).
*   **ECSService:** Service names are scoped per cluster.
*   **ECSTaskDefinition:** Task definition families are account-scoped; `effectiveName` applies to the `family` field.
*   **ECSCapacityProvider:** Capacity provider names are account-scoped.

AWS ECS naming constraints:
*   Alphanumeric characters, hyphens, and underscores only.
*   1-255 characters for most resources.
*   No reserved prefixes (e.g., `aws-`).

### Dynamic Tag Fields in Naming Templates

Naming templates support `{tag.fieldName}` placeholders to embed tag values. For example, `{tag.environment}-{name}` becomes `prod-my-service` if `tags.environment: "prod"`. Tag resolution follows the cascade: mandatory > instance > defaults.

For detailed information, see [Dynamic Tag Fields in Naming Templates](../../../concepts/configuration/naming-templates-fields-in-naming-templates.md).

## Example ECS Resources

### ECSConfig

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECSConfig
metadata:
  name: production
  namespace: kro-system
spec:
  mandatory:
    containerInsights: true
    defaultLaunchType: FARGATE
    defaultPlatformVersion: "1.4.0"
    defaultNetworkMode: awsvpc
    defaultTaskCPU: "512"
    defaultTaskMemory: "1024"
    tags:
      environment: production
      managed-by: kropath
  defaults:
    containerInsights: false
    namingTemplate: "{namespace}-{name}"
    tags:
      team: platform
```

### ECSCluster

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECSCluster
metadata:
  name: api-cluster
  namespace: workloads
spec:
  configRef: production
  capacityProviders:
    - FARGATE
  containerInsights: true
  executeCommandConfiguration:
    logging: DEFAULT
    logConfiguration:
      cloudWatchLogGroupName: /ecs/api-cluster
      cloudWatchEncryptionEnabled: true
  serviceConnectDefaults:
    namespace: api-services
  tags:
    application: api-platform
```

### ECSService

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECSService
metadata:
  name: api-service
  namespace: workloads
spec:
  configRef: production
  cluster: api-cluster
  taskDefinition: api-task
  desiredCount: 3
  launchType: FARGATE
  platformVersion: "1.4.0"
  networkConfiguration:
    awsvpcConfiguration:
      subnets:
        - subnet-12345
        - subnet-67890
      securityGroups:
        - sg-abc123
      assignPublicIp: DISABLED
  loadBalancers:
    - targetGroupArn: arn:aws:elasticloadbalancing:region:account:targetgroup/api/uuid
      containerName: api
      containerPort: 8080
  deploymentConfiguration:
    maximumPercent: 200
    minimumHealthyPercent: 100
    deploymentCircuitBreaker:
      enable: true
      rollback: true
  tags:
    application: api-platform
```

### ECSTaskDefinition

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECSTaskDefinition
metadata:
  name: api-task
  namespace: workloads
spec:
  configRef: production
  family: api-task
  networkMode: awsvpc
  cpu: "512"
  memory: "1024"
  executionRoleARN: arn:aws:iam::123456789:role/ecsTaskExecutionRole
  taskRoleARN: arn:aws:iam::123456789:role/api-task-role
  containerDefinitions:
    - name: api
      image: 123456789.dkr.ecr.us-east-1.amazonaws.com/api:latest
      essential: true
      cpu: 512
      memory: 1024
      portMappings:
        - containerPort: 8080
      environment:
        - name: LOG_LEVEL
          value: "INFO"
      logConfiguration:
        logDriver: awslogs
        options:
          awslogs-group: /ecs/api
          awslogs-region: us-east-1
          awslogs-stream-prefix: ecs
  ephemeralStorage:
    sizeInGiB: 50
  tags:
    application: api-platform
```

### ECSCapacityProvider

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECSCapacityProvider
metadata:
  name: my-asg-provider
  namespace: kro-system
spec:
  configRef: general-policy
  autoScalingGroupProvider:
    autoScalingGroupArn: arn:aws:autoscaling:us-east-1:123456789:autoScalingGroup:uuid:autoScalingGroupName/my-asg
    managedScaling:
      status: ENABLED
      targetCapacity: 75
      minimumScalingStepSize: 1
      maximumScalingStepSize: 10000
    managedTerminationProtection: ENABLED
  tags:
    cluster: api-cluster
```

## Governance Cascade Hierarchy

The ECS governance cascade follows ADR-010 principles:

1. **KropathConfig** (`mandatory`) — Organization-wide enforcement for all ECS services.
2. **KropathConfig** (`defaults`) — Organization-wide baseline for all ECS services.
3. **ECSConfig** (`mandatory`) — Per-profile enforcement for a service family.
4. **ECSConfig** (`defaults`) — Per-profile baseline for a service family.
5. **ECS Resource Instance** (`spec`) — Developer-specified overrides.

Higher levels override lower ones for scalar fields (launch type, platform version, networking). For tags and labels, all levels merge additively, with mandatory tags always present in the final resource.

## Cross-Provider Notes

*   **Launch Type:** ECS-specific concept (EC2 vs. Fargate). GCP Cloud Run is always serverless; Azure Container Apps uses consumption/dedicated plans.
*   **Capacity Providers:** ECS-specific resource for ASG and Fargate capacity management. Other providers have different scaling models.
*   **Task Revisions:** The append-only immutable revision model is ECS-specific for backward compatibility and safe rollouts.
*   **Service Connect:** Native to AWS ECS; other providers use service mesh or ingress patterns.

