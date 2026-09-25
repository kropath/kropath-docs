---
title: CognitoUserPool — Creating and Managing User Pools
description: "The `CognitoUserPool` resource represents a single user pool in AWS Cognito."
doc_type: reference
---
# CognitoUserPool — Creating and Managing User Pools

The `CognitoUserPool` resource represents a single user pool in AWS Cognito. This guide covers all configuration fields, governance cascade, immutable constraints, and real-world usage patterns.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `CognitoConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the pool name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the pool resource is deleted: `"retain"` (safe) or `"delete"` |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags applied to the pool; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`); merged with governance |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`); merged with governance |

### Security and Protection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `mfaConfiguration` | string | `""` | MFA enforcement: `OFF`, `OPTIONAL`, or `ON`. Governed by CognitoConfig; defaults to `OFF`. |
| `advancedSecurityMode` | string | `""` | Advanced security mode: `OFF`, `AUDIT`, or `ENFORCED`. Governed by CognitoConfig. |
| `deletionProtection` | string | `""` | Deletion protection: `ACTIVE` or `INACTIVE`. Governed by CognitoConfig; defaults to `INACTIVE`. |

### Password Policy

Password policy fields are **independently governed** — each sub-field resolves through the cascade:

| Field | Type | Default | Purpose |
|---|---|---|---|
| `passwordPolicy.minimumLength` | integer | `0` | Minimum password length (6–99). 0 = use governance default. |
| `passwordPolicy.requireLowercase` | boolean | (omit) | Require lowercase. Omit to inherit governance default. |
| `passwordPolicy.requireNumbers` | boolean | (omit) | Require numbers. Omit to inherit governance default. |
| `passwordPolicy.requireSymbols` | boolean | (omit) | Require symbols. Omit to inherit governance default. |
| `passwordPolicy.requireUppercase` | boolean | (omit) | Require uppercase. Omit to inherit governance default. |
| `passwordPolicy.temporaryPasswordValidityDays` | integer | `0` | Temp password expiry (1–365 days). 0 = use governance default. |

### Sign-In Configuration (Immutable After Creation)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `usernameAttributes` | array | `[]` | Enable email or phone sign-in: `[email]`, `[phone_number]`, or `[email, phone_number]`. **Immutable**; mutually exclusive with `aliasAttributes`. |
| `aliasAttributes` | array | `[]` | Enable username aliases: subset of `[phone_number, email, preferred_username]`. **Immutable**; mutually exclusive with `usernameAttributes`. |
| `autoVerifiedAttributes` | array | `[]` | Attributes auto-verified on sign-up: `[email]`, `[phone_number]`, or `[email, phone_number]`. |
| `usernameConfiguration.caseSensitive` | boolean | (omit) | Case sensitivity for usernames. **Immutable after creation**. Omit to use default. |

### Admin User Creation

| Field | Type | Default | Purpose |
|---|---|---|---|
| `adminCreateUserConfig.allowAdminCreateUserOnly` | boolean | (omit) | Restrict user creation to admins only. Omit to allow self-registration (default). |
| `adminCreateUserConfig.inviteMessageTemplate.emailMessage` | string | `""` | Email message template for admin-created users. Must use `{username}` and `{####}` placeholders. |
| `adminCreateUserConfig.inviteMessageTemplate.emailSubject` | string | `""` | Email subject for invite messages. |
| `adminCreateUserConfig.inviteMessageTemplate.smsMessage` | string | `""` | SMS message template for invites. Must use `{username}` and `{####}` placeholders. |
| `adminCreateUserConfig.unusedAccountValidityDays` | integer | `0` | Expiry for temporary passwords (1–365 days). 0 = default (7 days). |

### Email Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `emailConfiguration.emailSendingAccount` | string | `""` | Email sender: `COGNITO_DEFAULT` (AWS managed) or `DEVELOPER` (custom SES). |
| `emailConfiguration.from` | string | `""` | Sender email address (DEVELOPER mode only). Must be verified in SES. |
| `emailConfiguration.replyToEmailAddress` | string | `""` | Reply-to address for emails. |
| `emailConfiguration.sourceARN` | string | `""` | SES verified identity ARN (DEVELOPER mode only). |
| `emailConfiguration.configurationSet` | string | `""` | SES configuration set for tracking and bounces. |

### SMS Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `smsConfiguration.snsCallerARN` | string | `""` | IAM role ARN for SNS publishing. |
| `smsConfiguration.externalID` | string | `""` | External ID for cross-account IAM role assumption. |
| `smsConfiguration.snsRegion` | string | `""` | SNS region override (defaults to pool's region). |
| `smsAuthenticationMessage` | string | `""` | SMS message template for MFA codes. Must contain `{####}` placeholder. |

### Lambda Triggers

Lambda triggers enable custom authentication flows and user lifecycle hooks:

| Field | Type | Default | Purpose |
|---|---|---|---|
| `lambdaConfig.preSignUp` | string | `""` | Lambda ARN for pre-signup validation and auto-confirmation. |
| `lambdaConfig.postConfirmation` | string | `""` | Lambda ARN invoked after user confirmation. |
| `lambdaConfig.preAuthentication` | string | `""` | Lambda ARN invoked before authentication. |
| `lambdaConfig.postAuthentication` | string | `""` | Lambda ARN invoked after successful authentication. |
| `lambdaConfig.customMessage` | string | `""` | Lambda ARN for customizing user messages (email/SMS). |
| `lambdaConfig.defineAuthChallenge` | string | `""` | Lambda ARN for custom auth challenges. |
| `lambdaConfig.createAuthChallenge` | string | `""` | Lambda ARN to create challenge parameters. |
| `lambdaConfig.verifyAuthChallengeResponse` | string | `""` | Lambda ARN to verify custom challenge responses. |
| `lambdaConfig.userMigration` | string | `""` | Lambda ARN for migrating users from legacy system. |
| `lambdaConfig.preTokenGeneration` | string | `""` | Lambda ARN for modifying ID and access tokens. |
| `lambdaConfig.customEmailSender.lambdaARN` | string | `""` | Lambda ARN for sending custom emails. |
| `lambdaConfig.customEmailSender.lambdaVersion` | string | `""` | Lambda version: `V1_0`. |
| `lambdaConfig.customSMSSender.lambdaARN` | string | `""` | Lambda ARN for sending custom SMS. |
| `lambdaConfig.customSMSSender.lambdaVersion` | string | `""` | Lambda version: `V1_0`. |
| `lambdaConfig.preTokenGenerationConfig.lambdaARN` | string | `""` | Lambda ARN for advanced token customization. |
| `lambdaConfig.preTokenGenerationConfig.lambdaVersion` | string | `""` | Lambda version: `V1_0`, `V2_0`, or `V3_0`. |
| `lambdaConfig.kmsKeyID` | string | `""` | KMS key ID for encrypting Lambda context. |

### Custom Attributes

| Field | Type | Default | Purpose |
|---|---|---|---|
| `schema` | array | `[]` | Custom and standard user attributes. Append-only — cannot remove or change `attributeDataType` after creation. |
| `schema[].name` | string | (required) | Attribute name (e.g., `email`, `custom:tenant_id`). |
| `schema[].attributeDataType` | string | (required) | Attribute type: `String`, `Number`, `DateTime`, `Boolean`. **Immutable**. |
| `schema[].mutable` | boolean | `false` | Whether users can change this attribute themselves. |
| `schema[].required` | boolean | `false` | Whether attribute is required at sign-up. |
| `schema[].developerOnlyAttribute` | boolean | `false` | If true, only admins can write this attribute. |
| `schema[].stringAttributeConstraints.minLength` | string | `""` | Minimum string length. |
| `schema[].stringAttributeConstraints.maxLength` | string | `""` | Maximum string length. |
| `schema[].numberAttributeConstraints.minValue` | string | `""` | Minimum numeric value. |
| `schema[].numberAttributeConstraints.maxValue` | string | `""` | Maximum numeric value. |

### Account Recovery

| Field | Type | Default | Purpose |
|---|---|---|---|
| `accountRecoverySetting.recoveryMechanisms` | array | `[]` | Ordered list of account recovery options. |
| `accountRecoverySetting.recoveryMechanisms[].name` | string | (required) | Recovery mechanism: `verified_email`, `verified_phone_number`, or `admin_only`. |
| `accountRecoverySetting.recoveryMechanisms[].priority` | integer | `1` | Priority order (1 = highest). |

### Device Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `deviceConfiguration.challengeRequiredOnNewDevice` | boolean | (omit) | Require MFA when signing in from a new device. Omit to use default (false). |
| `deviceConfiguration.deviceOnlyRememberedOnUserPrompt` | boolean | (omit) | Only remember device if user explicitly opts in. Omit to use default (false). |

### Verification Messages

| Field | Type | Default | Purpose |
|---|---|---|---|
| `verificationMessageTemplate.defaultEmailOption` | string | `""` | Email verification method: `CONFIRM_WITH_LINK` or `CONFIRM_WITH_CODE`. |
| `verificationMessageTemplate.emailMessage` | string | `""` | Email message with `{####}` for verification code. |
| `verificationMessageTemplate.emailMessageByLink` | string | `""` | Email message with `{##Click here##}` for verification link. |
| `verificationMessageTemplate.emailSubject` | string | `""` | Subject for email messages. |
| `verificationMessageTemplate.emailSubjectByLink` | string | `""` | Subject for link-based email messages. |
| `verificationMessageTemplate.smsMessage` | string | `""` | SMS message with `{####}` placeholder for verification code. |

### User Attribute Updates

| Field | Type | Default | Purpose |
|---|---|---|---|
| `userAttributeUpdateSettings.attributesRequireVerificationBeforeUpdate` | array | `[]` | Attributes requiring verification to change: `[email]`, `[phone_number]`, or `[email, phone_number]`. |

## Status Outputs

After reconciliation, the pool's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective pool name in AWS (derived from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if the pool name is ready, `"invalid-unresolved-tokens"` if naming template has unresolved tokens |
| `userPoolArn` | string | The AWS ARN of the user pool (e.g., `arn:aws:cognito-idp:us-east-1:123456789012:userpool/us-east-1_AbC123`) |
| `userPoolId` | string | The AWS user pool ID (e.g., `us-east-1_AbC123`), assigned by AWS at creation |

## Naming Convention

Pools are named using a configurable template. The default template is `{namespace}-{name}`, which produces names like `auth-team-main-pool`.

**Available naming tokens:**
- `{name}` — The pool's Kubernetes resource name
- `{namespace}` — The pool's Kubernetes namespace
- `{configRef}` — The selected governance profile name
- `{account_id}` — AWS account ID (from governance)
- `{region}` — AWS region (from governance)
- `{tag.KEY}` — Any tag key from merged tags (e.g., `{tag.environment}`)

Example: A profile with `namingTemplate: "{namespace}-{configRef}-{tag.environment}-{name}"` produces names like `auth-team-high-security-production-main-pool`.

**Important:** User pool names cannot be changed after creation in AWS. Changing `spec.nameOverride` or the governance naming template on an existing pool does not rename the AWS pool — it remains registered under its original name.

## Immutable Fields

The following fields cannot be changed after creation:

| Field | Constraint | Why |
|---|---|---|
| `usernameAttributes` | Immutable | Affects how users sign in; cannot be changed without recreation |
| `aliasAttributes` | Immutable | Mutually exclusive with `usernameAttributes`; cannot be changed after creation |
| `usernameConfiguration.caseSensitive` | Immutable | Affects username matching and user data; enforced by AWS |
| `schema` (attribute types) | Append-only | Can add new attributes, but cannot remove or change `attributeDataType` of existing ones |

## Complete Examples

### Basic User Pool Creation

Create a simple user pool with default settings from the general-policy profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CognitoUserPool
metadata:
  name: auth-pool
  namespace: app-team
spec:
  configRef: general-policy
  mfaConfiguration: "OPTIONAL"
  tags:
    environment: production
```

Result:
- Pool created with name `app-team-auth-pool` (from default template)
- MFA optional (overrides profile default of OFF)
- Deletion protection defaults to INACTIVE (from profile)
- Password policy uses profile defaults (8+ chars, uppercase/lowercase/numbers/symbols)

### High-Security Production Pool

Create a production pool with mandatory MFA and strong password requirements:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CognitoUserPool
metadata:
  name: prod-pool
  namespace: payments
spec:
  configRef: high-security
  passwordPolicy:
    minimumLength: 14
  tags:
    environment: production
    data-class: pii
  syncedLabels:
    payment-processing: "true"
```

Result:
- MFA mandatory ON (from high-security profile)
- Deletion protection ACTIVE (from profile)
- Advanced security ENFORCED (from profile)
- Minimum password length 14 (instance overrides profile's 12)
- Deletion policy defaults to RETAIN (safe)

### Pool with Custom Email Configuration

Configure the pool to send emails via a custom SES identity:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CognitoUserPool
metadata:
  name: branded-pool
  namespace: marketing
spec:
  configRef: general-policy
  emailConfiguration:
    emailSendingAccount: "DEVELOPER"
    from: "noreply@example.com"
    sourceARN: "arn:aws:ses:us-east-1:123456789012:identity/example.com"
    replyToEmailAddress: "support@example.com"
    configurationSet: "cognito-emails"
  verificationMessageTemplate:
    defaultEmailOption: "CONFIRM_WITH_LINK"
    emailMessageByLink: "Please verify your email by clicking: {##Click here##}"
    emailSubjectByLink: "Verify your email address"
```

Result:
- Emails sent from custom SES identity
- Bounce and complaint tracking via SES configuration set
- Verification uses email link instead of code

### Pool with Lambda-Driven Custom Auth

Configure Lambda triggers for custom authentication flow:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CognitoUserPool
metadata:
  name: custom-auth-pool
  namespace: auth-services
spec:
  configRef: general-policy
  lambdaConfig:
    defineAuthChallenge: "arn:aws:lambda:us-east-1:123456789012:function:define-auth-challenge"
    createAuthChallenge: "arn:aws:lambda:us-east-1:123456789012:function:create-auth-challenge"
    verifyAuthChallengeResponse: "arn:aws:lambda:us-east-1:123456789012:function:verify-challenge"
    preSignUp: "arn:aws:lambda:us-east-1:123456789012:function:pre-signup"
    postConfirmation: "arn:aws:lambda:us-east-1:123456789012:function:post-confirmation"
    preTokenGeneration: "arn:aws:lambda:us-east-1:123456789012:function:pre-token-generation"
```

Result:
- Custom authentication challenge flow
- Auto-confirmation via preSignUp Lambda
- Custom token claims via preTokenGeneration

### Pool with Custom User Attributes

Define a custom tenant attribute and API scope:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CognitoUserPool
metadata:
  name: multi-tenant-pool
  namespace: platform
spec:
  configRef: general-policy
  schema:
    - name: email
      attributeDataType: String
      required: true
      mutable: true
    - name: custom:tenant_id
      attributeDataType: String
      mutable: false
      required: true
      developerOnlyAttribute: false
    - name: custom:api_scope
      attributeDataType: String
      mutable: true
      required: false
```

Result:
- Standard email attribute (required, mutable)
- Custom tenant ID (required at sign-up, cannot be changed by users)
- Custom API scope (optional, users can update)

### PCI-Compliant Pool with Comprehensive Security

Create a PCI-DSS compliant pool with maximum security settings:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CognitoUserPool
metadata:
  name: payment-pool
  namespace: payments
spec:
  configRef: pci
  adminCreateUserConfig:
    allowAdminCreateUserOnly: true
    inviteMessageTemplate:
      emailMessage: "Your temporary password is: {####}"
      emailSubject: "Welcome to Payment Processing"
    unusedAccountValidityDays: 3
  smsConfiguration:
    snsCallerARN: "arn:aws:iam::123456789012:role/CognitoSNSRole"
  smsAuthenticationMessage: "Your authentication code is {####}. Do not share it."
  accountRecoverySetting:
    recoveryMechanisms:
      - name: verified_email
        priority: 1
      - name: verified_phone_number
        priority: 2
  tags:
    compliance: pci-dss
    business-critical: "true"
  syncedLabels:
    compliance: pci
    data-class: restricted
```

Result:
- Admin-only user creation (no self-service registration)
- Temporary passwords expire in 3 days
- SMS-based MFA with custom messaging
- Redundant recovery options (email preferred, phone backup)
- PCI compliance tags and labels applied
