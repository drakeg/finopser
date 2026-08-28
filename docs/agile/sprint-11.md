# Sprint 11 — Automation / Remediation

## Goal
Introduce explicit, auditable remediation without turning recommendations into unattended cloud mutation.

## Safety model
Finopser keeps Observe → Recommend → Approve → Execute as separate stages. A recommendation, finding, policy violation, or budget alert never executes itself.

Every remediation action has:
- an allowlisted action key;
- one target resource/account;
- explicit parameters;
- a preview generated from persisted evidence;
- an evidence fingerprint;
- explicit approval by a Platform Administrator or Cloud Administrator;
- a separate execute step;
- immutable action events plus normal audit events;
- provider result/error and actor timestamps.

Preview never calls AWS. Simulation execution never calls AWS. A real execution is rejected when persisted resource evidence changed after preview.

## Initial action allowlist
Sprint 11 supports only `aws.add_tags` for:
- EC2 instances;
- RDS DB instances;
- Lambda functions;
- ECS clusters;
- ECS services.

Tag updates use the existing STS AssumeRole path. Reserved `aws:` tag keys are rejected. S3 is intentionally excluded because `PutBucketTagging` replaces the bucket tag set rather than performing the same additive operation.

The allowlist is code-controlled. Arbitrary AWS services, methods, or parameters cannot be supplied through the API.

## State transitions
1. `requested` — action request exists; nothing has run.
2. `previewed` — Finopser calculated the resulting tag set and stored an evidence fingerprint. No provider mutation occurred.
3. `approved` — Platform Administrator or Cloud Administrator explicitly approved the exact previewed evidence.
4. `succeeded` — simulation completed or the allowlisted provider mutation returned successfully.
5. `failed` — provider execution failed safely and the error was recorded.
6. `stale` — persisted evidence changed after preview. A fresh request/preview/approval is required.
7. `rejected` — an administrator explicitly declined the pending action.

There is no automatic transition from recommendation to remediation and no scheduled execution.

## RBAC
Authenticated users can read remediation records. Platform Administrator, Cloud Administrator, FinOps Analyst, and Security / Compliance Engineer may create and preview action requests. Only Platform Administrator and Cloud Administrator may approve, reject, or execute them.

## Precondition fingerprint
The preview fingerprint covers the target provider resource ID, type, region, state, active flag, last-seen timestamp, current persisted tags, and requested parameters. Execution recomputes this fingerprint immediately before any provider mutation. A mismatch marks the request stale and blocks execution.

## Real execution
For non-simulation `aws.add_tags`, Finopser assumes the connected account role and calls only the service-specific additive tag API:
- EC2 `CreateTags`;
- RDS `AddTagsToResource`;
- Lambda `TagResource`;
- ECS `TagResource`.

After a successful mutation, Finopser updates the persisted resource tags so subsequent previews and recommendations use the new evidence.

## Non-goals
- unattended or scheduled remediation;
- bulk execution;
- resource stop/start, resize, terminate, or delete;
- S3 mutation;
- IAM or SCP mutation;
- security-group, routing, networking, public-access, encryption, or database changes;
- arbitrary AWS API execution;
- shell commands, scripts, runbooks, or Terraform apply;
- external notification delivery;
- AWS production deployment or paid service activation.

## Acceptance criteria
- Preview and simulation do not call a provider.
- Execution cannot occur before explicit approval.
- Non-manager roles cannot approve or execute.
- A stale fingerprint blocks provider execution.
- Unsupported resource types/actions are rejected.
- Real execution uses only the allowlisted additive tagging APIs.
- Every request, preview, approval/rejection, execution, stale detection, and failure is auditable.
- The Automation UI shows approval posture and safety boundaries.
- Existing backend/frontend/Docker CI remains unchanged and green.
