# Initial Domain Model

## Organizational Hierarchy

The platform supports hierarchical governance through recursive organizational nodes.

```text
Tenant
`-- Organization
    |-- Organizational Unit
    |   |-- Project
    |   |   |-- Cloud Account
    |   |   `-- Cloud Account
    |   `-- Project
    `-- Organizational Unit
```

A recursive internal node model avoids hard-coding a fixed organizational depth:

```text
OrganizationNode
- id
- parent_id
- node_type
- name
```

Projects and cloud accounts attach to appropriate scopes.

## Inheritance

Governance objects may be assigned high in the hierarchy and inherited by descendants. Candidate inheritable objects include:

- policies;
- compliance controls;
- budgets;
- access rules;
- required tags;
- automation rules.

Effective configuration is conceptually:

```text
direct configuration
+ inherited configuration
- approved exceptions
```

Override and conflict rules require an explicit ADR before implementation.

## Core Domain Objects

### Identity and Access

- User
- Group
- Role
- Permission

### Organization

- Organization
- OrganizationNode
- Project

### Cloud

- CloudProvider
- CloudAccount
- CloudCredentialReference
- CloudRegion
- CloudResource
- ResourceTag

### FinOps

- CostRecord
- CostAllocation
- Budget
- BudgetThreshold

### Governance

- Policy
- PolicyAssignment
- PolicyException
- ComplianceFramework
- ComplianceControl
- ComplianceCheck
- ComplianceFinding

### Recommendations and Automation

- Recommendation
- Remediation
- AutomationJob
- AutomationRun

### Platform

- Notification
- AuditEvent

## Normalized Cloud Resource

Provider inventory is normalized around common searchable fields while preserving provider-specific metadata.

Conceptual fields:

```text
id
provider
account
provider_resource_id
resource_type
name
region
state
first_seen
last_seen
metadata
```

For AWS, `provider_resource_id` will normally be an ARN where one exists.

## Cost Dimensions

The FinOps model should support, at minimum:

- date;
- provider;
- account;
- project;
- organizational node;
- service;
- region;
- usage type;
- resource;
- tags;
- cost;
- currency.

## Compliance Lifecycle

```text
Framework
  -> Control
    -> Check
      -> Finding
```

Proposed finding states:

- OPEN
- ACKNOWLEDGED
- EXEMPTED
- REMEDIATION_PENDING
- RESOLVED
- SUPPRESSED

Exceptions should record reason, approver, creation time, expiration, and scope.

## Recommendations

Recommendations are separate from compliance findings. A recommendation should be able to record:

- category;
- evidence;
- confidence;
- estimated savings where applicable;
- risk;
- proposed action;
- status.
