---
title: ApiGatewayV2WebSocketApi — Real-Time Bidirectional APIs
description: "The `ApiGatewayV2WebSocketApi` resource creates serverless WebSocket APIs for real-time, bidirectional communication."
doc_type: reference
---
# ApiGatewayV2WebSocketApi — Real-Time Bidirectional APIs

The `ApiGatewayV2WebSocketApi` resource creates serverless WebSocket APIs for real-time, bidirectional communication. WebSocket APIs enable applications like chat, notifications, live dashboards, and collaborative tools.

## Overview

Use `ApiGatewayV2WebSocketApi` to create:

- **Chat applications** — Real-time message exchange between users
- **Live notifications** — Server-to-client push notifications
- **Collaborative tools** — Shared document editing, shared whiteboards
- **Live dashboards** — Real-time data streaming and updates
- **Multiplayer games** — Player interactions and state synchronization

WebSocket APIs use route-key-based message routing:
- `$connect` — Triggered when a client connects
- `$disconnect` — Triggered when a client disconnects
- `$default` — Catch-all for unmatched messages
- Custom keys (e.g., `sendMessage`, `updateStatus`) — Application-specific message types

## Creating a WebSocket API

### Basic Chat API

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2WebSocketApi
metadata:
  name: chat-api
  namespace: api-prod
spec:
  configRef: general-policy
  description: "Real-time chat application"
  routeSelectionExpression: "$request.body.action"
  routes:
    - routeKey: "$connect"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:on-connect"
    
    - routeKey: "$disconnect"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:on-disconnect"
    
    - routeKey: "$default"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:send-message"
```

This API:
- Handles connections with `on-connect` Lambda
- Cleans up disconnections with `on-disconnect` Lambda
- Routes all other messages to `send-message` Lambda
- Is named `api-prod-chat-api` (from naming template)
- Is accessible at `wss://<api-id>.execute-api.region.amazonaws.com/`

### Chat API with Custom Routes

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2WebSocketApi
metadata:
  name: chat-app
  namespace: api-prod
spec:
  configRef: general-policy
  routeSelectionExpression: "$request.body.action"
  
  routes:
    - routeKey: "$connect"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:connect"
    
    - routeKey: "$disconnect"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:disconnect"
    
    - routeKey: "sendMessage"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:send-message"
    
    - routeKey: "updateStatus"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:update-status"
    
    - routeKey: "joinRoom"
      authorizationType: CUSTOM
      authorizerRef: custom-auth
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:join-room"
    
    - routeKey: "$default"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:default-handler"
```

### WebSocket API with Lambda Authorizer

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ApiGatewayV2WebSocketApi
metadata:
  name: secure-chat
  namespace: api-prod
spec:
  configRef: general-policy
  routeSelectionExpression: "$request.body.type"
  
  authorizers:
    - name: auth0
      identitySource:
        - "$request.header.Authorization"
      authorizerUri: "arn:aws:lambda:us-east-1:123456789012:function:ws-authorizer"
      resultTtlInSeconds: 300
  
  routes:
    - routeKey: "$connect"
      authorizationType: CUSTOM
      authorizerRef: auth0
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:connect"
    
    - routeKey: "$default"
      integration:
        type: AWS_PROXY
        integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:handle-message"
```

Authorizers protect the `$connect` route. Clients must authenticate before connecting.

## Configuration

### Route Selection

`routeSelectionExpression` determines how messages are routed:

```yaml
spec:
  routeSelectionExpression: "$request.body.action"
```

Clients send messages with an `action` field in the JSON body:

```json
{
  "action": "sendMessage",
  "message": "Hello"
}
```

WebSocket API matches the `action` value against route keys.

### Route Keys

**Reserved routes:**

- `$connect` — Client connects (handshake complete)
- `$disconnect` — Client disconnects (connection closed)
- `$default` — Unmatched messages (fallback)

**Custom routes:**

```yaml
routes:
  - routeKey: "sendMessage"
  - routeKey: "updateStatus"
  - routeKey: "joinRoom"
```

### Integrations

WebSocket integrations support multiple types:

**AWS_PROXY (Lambda):**

```yaml
integration:
  type: AWS_PROXY
  integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:handler"
```

**HTTP_PROXY:**

```yaml
integration:
  type: HTTP_PROXY
  integrationUri: "https://backend.example.com"
  integrationMethod: "POST"
```

**AWS (Service Calls):**

```yaml
integration:
  type: AWS
  integrationUri: "arn:aws:logs:us-east-1:123456789012:log-group:/websocket-logs"
```

**HTTP, MOCK:** Supported but less common.

### Authorizers

Protect routes with Lambda REQUEST authorizers (JWT is HTTP-only):

```yaml
authorizers:
  - name: custom-auth
    identitySource:
      - "$request.header.Authorization"
      - "$request.querystring.token"
    authorizerUri: "arn:aws:lambda:us-east-1:123456789012:function:authorizer"
    resultTtlInSeconds: 300
```

Identity sources can be headers, query string, or stages.

### Route Settings

Override settings per-route:

```yaml
defaultRouteSettings:
  dataTraceEnabled: true
  detailedMetricsEnabled: true
  loggingLevel: "INFO"

routeSettings:
  "joinRoom":
    dataTraceEnabled: false  # Disable data logging for sensitive operation
  "$default":
    loggingLevel: "ERROR"  # Only log errors
```

### API Key

Optionally require API keys for client authentication:

```yaml
spec:
  apiKeySelectionExpression: "$request.header.x-api-key"

routes:
  - routeKey: "$connect"
    apiKeyRequired: true
    integration: ...
```

Clients include the API key in the `x-api-key` header.

## Naming

Resource names are generated from a naming template. Default: `{namespace}-{name}`

```yaml
metadata:
  namespace: api-prod
  name: chat-api
# Resulting name: api-prod-chat-api
```

Override:

```yaml
spec:
  nameOverride: "my-chat-api"  # Use exactly this name
```

## Tags and Labels

Add organization metadata:

```yaml
spec:
  tags:
    team: realtime
    cost-center: "5678"
    environment: production
  syncedLabels:
    app: chat-service
  syncedAnnotations:
    slack-channel: "#realtime-alerts"
```

## Deletion Policy

### Retain (default)

```yaml
spec:
  deletionPolicy: "retain"
```

The WebSocket API remains in AWS.

### Delete

```yaml
spec:
  deletionPolicy: "delete"
```

The WebSocket API is deleted when the CR is deleted.

## Sending Messages from Lambda

Lambda functions use the API Gateway Management API to send messages to clients:

```python
import boto3

apigw = boto3.client('apigatewaymanagementapi', endpoint_url=api_endpoint)

# Send message to a specific client
apigw.post_to_connection(
    ConnectionId=connection_id,
    Data=json.dumps({"type": "notification", "message": "Hello"})
)

# Send message to all connected clients (requires storing connections)
for conn_id in connection_store.get_all():
    try:
        apigw.post_to_connection(
            ConnectionId=conn_id,
            Data=json.dumps({"type": "broadcast", "message": "Update"})
        )
    except apigw.exceptions.GoneException:
        connection_store.remove(conn_id)
```

## Monitoring and Verification

### Check API Status

```bash
kubectl describe websocketapi chat-api -n api-prod
```

Look for:
- `status.resourceName` — The API name in AWS
- `status.conditions` — Ready, error, or warning states

### Test Connection

```bash
# Using wscat (npm install -g wscat)
wscat -c wss://${API_ID}.execute-api.us-east-1.amazonaws.com/

# Send a message
> {"action": "sendMessage", "message": "Hello"}

# Receive a response
< {"type": "response", "data": {...}}
```

### View Logs

Enable CloudWatch logging through governance:

```bash
aws logs tail /aws/apigateway/chat-api --follow
```

### Monitor Connections

Check active connections:

```bash
aws apigatewayv2 get-api \
  --api-id ${API_ID} \
  --region us-east-1 \
  --query 'Tags' | jq
```

## Updating a WebSocket API

### Add a Route

Edit the CR and add a new route:

```yaml
routes:
  - routeKey: "$connect"
    # ...existing route...
  
  - routeKey: "typingIndicator"  # New route
    integration:
      type: AWS_PROXY
      integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:typing-indicator"
```

Apply:

```bash
kubectl apply -f api.yaml
```

### Remove a Route

Remove from the `routes` array and apply.

### Update Route Handler

Change the Lambda function:

```yaml
routes:
  - routeKey: "sendMessage"
    integration:
      type: AWS_PROXY
      integrationUri: "arn:aws:lambda:us-east-1:123456789012:function:send-message-v2"  # New version
```

## Best Practices

1. **Store connections** — Use DynamoDB or ElastiCache to track active `ConnectionId`s for broadcasting.
2. **Handle disconnections** — Clean up connection records when clients disconnect.
3. **Message ordering** — WebSocket doesn't guarantee message order for large volumes; add sequence numbers if strict ordering is required.
4. **Error handling** — Handle `GoneException` when clients disconnect.
5. **Timeouts** — WebSocket connections have default idle timeouts (2 hours); implement heartbeats for long-lived connections.
6. **Authorization** — Protect `$connect` with authorizers; validate tokens early.

## Limitations

- `RouteResponse` and `IntegrationResponse` ACK CRDs are not available in this version (G-4). Two-way WebSocket communication is limited.
- WebSocket APIs don't support CORS (not applicable to WebSocket protocol).
- Message size limit: 128 KB per message.

## Cross-Provider Notes

- WebSocket APIs are AWS-specific
- GCP doesn't have a native WebSocket gateway; use Cloud Run or App Engine
- Azure supports WebSocket pass-through in preview via API Management
- WebSocket support varies significantly across cloud providers

## See Also

- [API Gateway V2](index.md) — Family overview
- [HTTP APIs](apigatewayv2httpapi.md) — REST APIs
- [Stages](apigatewayv2stage.md) — Deploy WebSocket APIs to stages
- [Custom Domains](apigatewayv2domainname.md) — Use custom domain for WebSocket APIs
- [VPC Links](apigatewayv2vpclink.md) — Private integrations
