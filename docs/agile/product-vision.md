# Product Vision

## Product

**finopser** is a self-hosted cloud governance and FinOps platform that gives organizations a single interface for understanding, governing, securing, and optimizing cloud environments.

## Vision

Build a cloud-management control plane that begins with AWS while remaining provider-neutral at the domain and application layers so Azure, Google Cloud, OCI, SaaS, and on-premises sources can be added later without redesigning the core platform.

## Value Proposition

finopser will centralize:

- cloud visibility and resource inventory;
- cost management and FinOps;
- budgets and financial governance;
- compliance monitoring;
- policies and guardrails;
- cloud account and organizational management;
- access governance;
- recommendations;
- automation and remediation;
- reporting and audit evidence.

## Safety Principle

The platform must remain useful with read-only cloud permissions. All cloud-changing capabilities follow the operating model:

1. **OBSERVE** — inspect and report;
2. **RECOMMEND** — propose an action with evidence and impact;
3. **ENFORCE** — execute only after explicit authorization.

## Initial Provider

AWS is the first supported provider. AWS-specific implementation must live behind provider interfaces rather than becoming the core application architecture.

## Deployment Direction

- Local development and testing: Docker Compose.
- Initial production target: AWS.
- Core application behavior must not depend on managed AWS services when running locally.

## Primary Personas

- Platform Administrator
- Cloud Administrator
- FinOps Analyst
- Security / Compliance Engineer
- Project / Application Owner
- Auditor

## Initial Product Boundaries

Sprint 0 defines product and architecture only. Product functionality begins only after the Sprint 0 readiness gate is approved.

Early implementation is intentionally limited to the application foundation, organizational model, AWS onboarding, resource inventory, FinOps MVP, dashboard, compliance, policies, budgets, recommendations, and eventually automation.

## Explicit Early Non-Goals

The following are valid future capabilities but are deliberately excluded from the early MVP unless reprioritized through backlog refinement:

- AI-generated remediation;
- multi-cloud provider implementations;
- AWS account vending;
- destructive automatic remediation;
- enterprise SAML/SSO;
- a Terraform provider;
- mobile applications;
- custom report designers;
- complex forecasting models;
- Kubernetes-first deployment.
