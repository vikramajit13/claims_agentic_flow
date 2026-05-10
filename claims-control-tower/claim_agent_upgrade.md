Phase 2 outcome

By the end of Weeks 3–4, your demo should show this:

Claim is submitted
        ↓
Workflow runs automatically
        ↓
System detects risk/payment issue
        ↓
Workflow pauses
        ↓
Human review task is created
        ↓
Adjuster sees task in dashboard
        ↓
Adjuster approves, rejects, or modifies payout
        ↓
Workflow resumes
        ↓
Payment guardrails run again
        ↓
Payment instruction is created or blocked
        ↓
Every decision is visible in audit trail

This is the key enterprise capability:

Controlled automation with human override and auditability.
What you need to build in Phase 2

You need five things:

1. Stronger pause/resume workflow model
2. Human task lifecycle
3. Adjuster dashboard
4. Decision handling: approve/reject/modify payout
5. Decision audit trail

Do not add LLMs yet unless the backend and UI flow are solid.

Phase 2 core demo scenario

Your demo statement is excellent:

“Auto-payment blocked because invoice date predates incident date and customer had 3 claims in 12 months.”

This means your system needs to detect two things:

1. Invoice date is before incident date
2. Customer has too many recent claims

Then the workflow should pause and create a review task.

Example automated decision:

{
  "decision": "REFER_TO_HUMAN",
  "reason": "Payment blocked due to invoice date anomaly and high claim frequency",
  "risk_factors": [
    "Invoice date 2026-04-20 predates incident date 2026-04-25",
    "Customer has 3 claims in the last 12 months"
  ],
  "recommended_action": "ADJUSTER_REVIEW_REQUIRED"
}

This is a strong demo because it shows:

Business rule
Risk signal
Payment control
Human-in-the-loop
Auditability
Updated Phase 2 architecture

After Phase 2, your flow should look like this:

Claim Submitted
      ↓
Workflow Started
      ↓
Coverage Validation
      ↓
Evidence Validation
      ↓
Risk & Leakage Evaluation
      ↓
Adjudication Recommendation
      ↓
Payment Guardrail Pre-check
      ↓
Human Review Required?
      ↓
YES → Pause Workflow
      ↓
Create Human Task
      ↓
Adjuster Dashboard
      ↓
Adjuster Decision
      ↓
Resume Workflow
      ↓
Payment Guardrail Final Check
      ↓
Payment Instruction / Rejection / More Info
      ↓
Audit Trail

Notice something important:

In Phase 1, human review may have been created after adjudication.

In Phase 2, human review can be triggered by multiple points:

coverage issue
missing evidence
fraud risk
invoice anomaly
payout amount threshold
payment guardrail failure

That is more realistic.

The most important design change

Do not treat human review as one generic task only.

Use task types.

class HumanTaskType(str, Enum):
    CLAIM_REVIEW = "CLAIM_REVIEW"
    FRAUD_REVIEW = "FRAUD_REVIEW"
    PAYMENT_REVIEW = "PAYMENT_REVIEW"
    EVIDENCE_REVIEW = "EVIDENCE_REVIEW"

For your demo, the task should probably be:

PAYMENT_REVIEW

or

FRAUD_REVIEW

Better:

PAYMENT_REVIEW

Because the demo says:

Auto-payment blocked

So your system is not rejecting the claim yet. It is saying:

Payment cannot proceed without adjuster review.
Main backend changes
1. Upgrade human_tasks

Your current table is probably basic.

For Phase 2, extend it.

human_tasks

Should include:

id
claim_id
workflow_run_id
task_type
status
priority
assigned_to
created_reason
risk_factors
recommended_decision
recommended_payout_amount
reviewer_decision
reviewer_notes
reviewer_modified_payout_amount
completed_by
created_at
updated_at
completed_at

Important fields:

created_reason
risk_factors
recommended_decision
recommended_payout_amount
reviewer_decision
reviewer_modified_payout_amount

These make the dashboard useful.

2. Add better task status

Use:

class HumanTaskStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

Do not overdo it.

For Phase 2, these are enough.

3. Add task decision enum

The human reviewer can decide:

class HumanDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MODIFY_PAYOUT = "MODIFY_PAYOUT"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"
    ESCALATE = "ESCALATE"

For your demo, the key one is:

MODIFY_PAYOUT

That is what makes this feel real.

The claim/document model needs one addition

To support:

invoice date predates incident date

Your claim_documents table needs metadata.

Add:

document_metadata JSONB

Example:

{
  "invoice_date": "2026-04-20",
  "invoice_amount": 4200,
  "vendor_name": "ABC Repairs"
}

Your claim has:

{
  "incident_date": "2026-04-25"
}

The risk rule checks:

invoice_date < incident_date

That produces a risk factor.

You also need claim history

To support:

customer had 3 claims in 12 months

You need a way to fetch previous claims.

Do not build a new system.

Use your existing claims table.

Your ClaimsSystemAdapter can do:

get_claims_for_customer_last_12_months(customer_id)

Implementation:

SELECT claims
WHERE customer_id = :customer_id
AND incident_date >= today - 12 months
AND id != current_claim_id

Then if count >= 3, flag it.

Important detail:

If the demo says “customer had 3 claims in 12 months”, you need seed data.

Add three previous claims for the same customer.

New Phase 2 services

You likely already have some services from Phase 1.

Add or strengthen these:

HumanTaskService
WorkflowPauseService
WorkflowResumeService
AdjusterDecisionService
RiskSignalService
PaymentGuardrailService
AuditService

You do not necessarily need separate physical classes for all of these, but the responsibilities should exist.

1. Workflow pause service

Purpose:

Pause workflow safely when automation cannot proceed.

When pause happens:

workflow_run.status = WAITING_FOR_HUMAN
workflow_run.current_step = HUMAN_REVIEW
claim.status = PENDING_HUMAN_REVIEW
human_task created
audit event written

Pseudo-code:

def pause_for_human_review(
    workflow_run,
    claim,
    task_type,
    reason,
    risk_factors,
    recommended_decision,
    recommended_payout_amount
):
    workflow_run.status = "WAITING_FOR_HUMAN"
    workflow_run.current_step = "HUMAN_REVIEW"

    claim.status = "PENDING_HUMAN_REVIEW"

    task = human_task_service.create_task(
        claim_id=claim.id,
        workflow_run_id=workflow_run.id,
        task_type=task_type,
        priority="HIGH",
        created_reason=reason,
        risk_factors=risk_factors,
        recommended_decision=recommended_decision,
        recommended_payout_amount=recommended_payout_amount
    )

    audit_service.record_event(
        event_type="WORKFLOW_PAUSED",
        step_name="HUMAN_REVIEW",
        payload={
            "reason": reason,
            "task_id": task.id,
            "risk_factors": risk_factors
        }
    )

    return task
2. Adjuster decision service

Purpose:

Apply the human decision safely.

The reviewer should not directly update payment tables.

The reviewer completes a task.

Then the workflow resumes and decides what to do next.

This separation is important.

Bad design:

Adjuster clicks approve → payment created immediately

Better design:

Adjuster clicks approve → human task completed → workflow resumes → guardrails run → payment created

That is enterprise-grade.

3. Workflow resume service

Purpose:

Resume from WAITING_FOR_HUMAN using the completed human task decision.

Resume logic:

Get workflow_run
Check status is WAITING_FOR_HUMAN
Find completed human task
Read reviewer decision
Apply decision
Continue workflow from correct step
Write audit events

Pseudo-flow:

if reviewer_decision == REJECT:
    claim.status = REJECTED
    workflow_run.status = COMPLETED
    write audit
    stop

if reviewer_decision == REQUEST_MORE_INFO:
    claim.status = PENDING_MORE_INFO
    workflow_run.status = WAITING_FOR_INFO
    write audit
    stop

if reviewer_decision == ESCALATE:
    create another human task
    workflow_run.status = WAITING_FOR_HUMAN
    write audit
    stop

if reviewer_decision in APPROVE/MODIFY_PAYOUT:
    claim.status = APPROVED
    run payment guardrail final check
    if passed:
        create payment instruction
    else:
        block payment
Important: modify payout flow

If the adjuster modifies payout, you need to store:

original_recommended_amount
reviewer_modified_payout_amount
final_approved_amount

For Phase 2, you can store this in human_tasks.

Later you may add claim_decisions table, but not required yet.

Example:

{
  "reviewer_decision": "MODIFY_PAYOUT",
  "reviewer_notes": "Invoice predates incident date. Approving only verified repair portion.",
  "reviewer_modified_payout_amount": 2800
}

Then on resume:

final_approved_amount = reviewer_modified_payout_amount

Payment guardrail checks against this final amount.

API endpoints to add or improve
Human task list for dashboard
GET /human-tasks?status=OPEN

Response:

[
  {
    "task_id": "TASK-001",
    "claim_id": "CLM-001",
    "claim_number": "CLM-2026-001",
    "task_type": "PAYMENT_REVIEW",
    "priority": "HIGH",
    "status": "OPEN",
    "created_reason": "Auto-payment blocked due to invoice anomaly and high claim frequency",
    "risk_factors": [
      "Invoice date 2026-04-20 predates incident date 2026-04-25",
      "Customer has 3 claims in the last 12 months"
    ],
    "recommended_payout_amount": 4200,
    "created_at": "2026-05-09T10:00:00Z"
  }
]
Human task detail
GET /human-tasks/{task_id}

This should return all detail needed by adjuster.

Response:

{
  "task_id": "TASK-001",
  "task_type": "PAYMENT_REVIEW",
  "status": "OPEN",
  "priority": "HIGH",
  "claim": {
    "claim_id": "CLM-001",
    "claim_number": "CLM-2026-001",
    "customer_id": "CUST-123",
    "policy_id": "POL-001",
    "claim_type": "MOTOR",
    "claim_amount": 4200,
    "incident_date": "2026-04-25",
    "description": "Rear bumper repair after accident"
  },
  "risk_factors": [
    "Invoice date 2026-04-20 predates incident date 2026-04-25",
    "Customer has 3 claims in the last 12 months"
  ],
  "documents": [
    {
      "document_type": "INVOICE",
      "file_name": "repair-invoice.pdf",
      "document_metadata": {
        "invoice_date": "2026-04-20",
        "invoice_amount": 4200,
        "vendor_name": "ABC Repairs"
      }
    }
  ],
  "recommendation": {
    "system_decision": "REFER_TO_HUMAN",
    "recommended_payout_amount": 4200,
    "reason": "Payment review required"
  }
}
Assign task to adjuster

Optional but useful:

POST /human-tasks/{task_id}/assign

Request:

{
  "assigned_to": "adjuster_001"
}

This updates:

status = IN_PROGRESS
assigned_to = adjuster_001

For Phase 2, this is useful but not mandatory.

Complete human task
POST /human-tasks/{task_id}/complete

Request for approve:

{
  "decision": "APPROVE",
  "decision_notes": "Reviewed invoice and claim history. Approving payout.",
  "approved_amount": 4200,
  "completed_by": "adjuster_001"
}

Request for reject:

{
  "decision": "REJECT",
  "decision_notes": "Invoice date predates incident and customer could not justify discrepancy.",
  "completed_by": "adjuster_001"
}

Request for modify payout:

{
  "decision": "MODIFY_PAYOUT",
  "decision_notes": "Approving only verified damage component. Reducing payout.",
  "approved_amount": 2800,
  "completed_by": "adjuster_001"
}

Request for more info:

{
  "decision": "REQUEST_MORE_INFO",
  "decision_notes": "Need corrected invoice from repairer.",
  "completed_by": "adjuster_001"
}
Resume workflow
POST /workflow-runs/{workflow_run_id}/resume

Response:

{
  "workflow_run_id": "WFR-001",
  "status": "COMPLETED",
  "claim_status": "PAYMENT_READY",
  "final_decision": "APPROVED",
  "final_approved_amount": 2800,
  "payment_instruction_id": "PAY-001"
}
Frontend: adjuster dashboard

Do not build a full enterprise UI. Build a simple React/Next.js dashboard.

Minimum pages:

1. Human task queue
2. Human task detail
3. Claim audit timeline

That is enough.

Page 1: Human task queue

Route:

/review-tasks

Show table:

Task ID
Claim Number
Task Type
Priority
Reason
Status
Created At
Action

Example row:

CLM-2026-001 | PAYMENT_REVIEW | HIGH | Invoice date anomaly + 3 claims in 12 months | OPEN | Review

Add filters:

status
task_type
priority

Do not overbuild.

Page 2: Human task detail

Route:

/review-tasks/{task_id}

Show four panels:

Claim Summary
Risk Flags
Documents
Decision Panel
Claim Summary
Claim Number
Customer ID
Policy ID
Claim Type
Claim Amount
Incident Date
Description
Risk Flags

Show as red/yellow alert cards:

Invoice date predates incident date
Customer has 3 claims in 12 months
Documents

Show metadata:

Invoice file
Invoice date
Invoice amount
Vendor

No real PDF viewer yet.

Decision Panel

Buttons:

Approve
Reject
Modify Payout
Request More Info

If modify payout:

Approved Amount input
Reviewer Notes input
Submit Decision
Page 3: Claim audit timeline

Route:

/claims/{claim_id}/audit

Display:

CLAIM_SUBMITTED
WORKFLOW_STARTED
COVERAGE_VALIDATED
DOCUMENTS_VALIDATED
RISK_EVALUATED
PAYMENT_BLOCKED
HUMAN_TASK_CREATED
HUMAN_TASK_COMPLETED
WORKFLOW_RESUMED
PAYMENT_GUARDRAIL_PASSED
PAYMENT_INSTRUCTION_CREATED
WORKFLOW_COMPLETED

This page is important. It proves governance.

What the demo should look like
Demo claim input

Use this claim:

{
  "customer_id": "CUST-999",
  "policy_id": "POL-MOTOR-001",
  "claim_type": "MOTOR",
  "claim_amount": 4200,
  "incident_date": "2026-04-25",
  "description": "Rear bumper damage after accident",
  "documents": [
    {
      "document_type": "INVOICE",
      "file_name": "repair-invoice.pdf",
      "document_metadata": {
        "invoice_date": "2026-04-20",
        "invoice_amount": 4200,
        "vendor_name": "ABC Repairs"
      }
    },
    {
      "document_type": "PHOTO",
      "file_name": "damage-photo.jpg"
    },
    {
      "document_type": "REPAIR_ESTIMATE",
      "file_name": "repair-estimate.pdf"
    }
  ]
}

Also seed previous claims:

CUST-999 had 3 previous MOTOR claims in the last 12 months.
Demo flow
Step 1: Submit suspicious claim
POST /claims

Claim status:

SUBMITTED
Step 2: Start and execute workflow
POST /claims/{claim_id}/workflow/start
POST /workflow-runs/{workflow_run_id}/execute

System detects:

Invoice date predates incident date
Customer has 3 claims in 12 months

Workflow result:

{
  "decision": "REFER_TO_HUMAN",
  "workflow_status": "WAITING_FOR_HUMAN",
  "claim_status": "PENDING_HUMAN_REVIEW",
  "human_task_created": true,
  "reason": "Auto-payment blocked due to invoice anomaly and high claim frequency"
}
Step 3: Open adjuster dashboard

Dashboard shows:

PAYMENT_REVIEW task
Priority: HIGH
Reason: Auto-payment blocked
Risk flags: invoice anomaly, claim frequency

This is the “enterprise” moment.

Step 4: Adjuster modifies payout

Adjuster enters:

{
  "decision": "MODIFY_PAYOUT",
  "approved_amount": 2800,
  "decision_notes": "Invoice date anomaly found. Approving only verified damage portion."
}

Human task status:

COMPLETED

Workflow still not completed until resume.

Step 5: Resume workflow
POST /workflow-runs/{workflow_run_id}/resume

System:

Reads human decision
Sets final approved amount = 2800
Runs payment guardrail
Creates payment instruction
Completes workflow

Response:

{
  "claim_status": "PAYMENT_READY",
  "workflow_status": "COMPLETED",
  "final_approved_amount": 2800,
  "payment_instruction_status": "READY_FOR_PAYMENT"
}
Step 6: Show audit trail

Audit timeline should show:

CLAIM_SUBMITTED
WORKFLOW_STARTED
COVERAGE_VALIDATION_STARTED
COVERAGE_VALIDATION_COMPLETED
EVIDENCE_VALIDATION_STARTED
EVIDENCE_VALIDATION_COMPLETED
RISK_EVALUATION_STARTED
RISK_EVALUATION_COMPLETED
PAYMENT_GUARDRAIL_FAILED
WORKFLOW_PAUSED
HUMAN_TASK_CREATED
HUMAN_TASK_ASSIGNED
HUMAN_TASK_COMPLETED
ADJUSTER_DECISION_RECORDED
WORKFLOW_RESUMED
PAYMENT_GUARDRAIL_PASSED
PAYMENT_INSTRUCTION_CREATED
WORKFLOW_COMPLETED

That is a very good demo.

Backend implementation order

Do it in this order.

Step 1: Add document metadata

Add to claim_documents:

document_metadata JSONB

Why first?

Because the invoice-date rule needs it.

Step 2: Add claim history query

In ClaimsSystemAdapter or ClaimRepository:

get_claims_for_customer_in_last_months(
    customer_id: str,
    months: int,
    exclude_claim_id: UUID
)

This powers the “3 claims in 12 months” rule.

Step 3: Add risk signals

Create a clean result object.

class RiskSignal(BaseModel):
    code: str
    severity: str
    message: str
    source: str

Example:

{
  "code": "INVOICE_DATE_BEFORE_INCIDENT",
  "severity": "HIGH",
  "message": "Invoice date 2026-04-20 predates incident date 2026-04-25",
  "source": "DOCUMENT_VALIDATION"
}

And:

{
  "code": "HIGH_CLAIM_FREQUENCY",
  "severity": "HIGH",
  "message": "Customer has 3 claims in the last 12 months",
  "source": "CLAIM_HISTORY"
}

This is better than just free-text reasons.

Step 4: Update risk evaluation service

Add rules:

invoice_date_before_incident
customer_claim_count_last_12_months >= 3

Return:

{
  "risk_score": 85,
  "risk_level": "HIGH",
  "risk_signals": [
    {
      "code": "INVOICE_DATE_BEFORE_INCIDENT",
      "severity": "HIGH",
      "message": "Invoice date predates incident date"
    },
    {
      "code": "HIGH_CLAIM_FREQUENCY",
      "severity": "HIGH",
      "message": "Customer has 3 claims in the last 12 months"
    }
  ]
}
Step 5: Update adjudication

Rule:

If invoice date before incident OR high claim frequency:
    decision = REFER_TO_HUMAN
    task_type = PAYMENT_REVIEW
    reason = "Auto-payment blocked due to invoice anomaly and high claim frequency"

This can happen before payment instruction creation.

Step 6: Strengthen pause workflow

Add explicit event:

WORKFLOW_PAUSED

Payload:

{
  "pause_reason": "HUMAN_REVIEW_REQUIRED",
  "task_type": "PAYMENT_REVIEW",
  "risk_signals": [
    "INVOICE_DATE_BEFORE_INCIDENT",
    "HIGH_CLAIM_FREQUENCY"
  ]
}
Step 7: Complete human task

Your complete_human_task method should:

validate task is OPEN or IN_PROGRESS
store reviewer decision
store reviewer notes
store approved amount if supplied
set task.status = COMPLETED
set completed_at
write HUMAN_TASK_COMPLETED event
write ADJUSTER_DECISION_RECORDED event

Do not resume automatically unless you decide to keep the demo simpler.

My recommendation:

Complete task first.
Resume workflow second.

This makes pause/resume visible.

Step 8: Resume workflow

Add:

POST /workflow-runs/{workflow_run_id}/resume

Validation:

workflow_run.status must be WAITING_FOR_HUMAN
there must be a completed human task
human decision must be valid

Then continue.

Step 9: Frontend dashboard

Build after backend is reliable.

Minimum UI:

Task queue
Task detail
Decision form
Audit timeline

Do not start frontend first.

Data model changes summary
claim_documents

Add:

document_metadata JSONB
human_tasks

Add or confirm:

priority
created_reason
risk_factors JSONB
recommended_decision
recommended_payout_amount
reviewer_decision
reviewer_notes
reviewer_modified_payout_amount
completed_by
workflow_events

Make sure payload is JSONB:

event_payload JSONB
payment_instructions

Add:

approved_amount
source_decision
created_from_human_task_id

This helps trace payout source.

Example:

source_decision = HUMAN_MODIFIED_PAYOUT
created_from_human_task_id = TASK-001

Very useful for audit.

Should you create a claim_decisions table?

Not yet.

You may be tempted to add:

claim_decisions

But for Phase 2, use:

workflow_events
human_tasks
payment_instructions

That is enough.

Add claim_decisions later if you need more formal decision history.

Events you must audit in Phase 2

Add these event types:

class WorkflowEventType(str, Enum):
    WORKFLOW_PAUSED = "WORKFLOW_PAUSED"
    WORKFLOW_RESUMED = "WORKFLOW_RESUMED"
    HUMAN_TASK_CREATED = "HUMAN_TASK_CREATED"
    HUMAN_TASK_ASSIGNED = "HUMAN_TASK_ASSIGNED"
    HUMAN_TASK_COMPLETED = "HUMAN_TASK_COMPLETED"
    ADJUSTER_DECISION_RECORDED = "ADJUSTER_DECISION_RECORDED"
    PAYOUT_MODIFIED = "PAYOUT_MODIFIED"
    PAYMENT_GUARDRAIL_FAILED = "PAYMENT_GUARDRAIL_FAILED"
    PAYMENT_GUARDRAIL_PASSED = "PAYMENT_GUARDRAIL_PASSED"

For every human decision, audit:

who
when
what decision
previous recommended amount
final approved amount
reason/note
risk factors visible at time of decision

That is what enterprise governance needs.

Week 3 plan
Day 11: Data model upgrade

Build migrations for:

claim_documents.document_metadata
human_tasks extra fields
payment_instructions source decision fields

Seed:

CUST-999 with 3 previous claims
Suspicious claim scenario

Done when:

You can create a claim with invoice metadata.
You can query prior claims for customer.
Day 12: Risk signals

Build:

RiskSignal model
invoice date rule
claim frequency rule
updated risk scoring

Done when:

Workflow detects:
- invoice date before incident
- 3 claims in 12 months
Day 13: Workflow pause

Build:

pause_for_human_review
WORKFLOW_PAUSED event
PAYMENT_REVIEW human task creation
claim status update
workflow status update

Done when:

Suspicious claim results in:
workflow_run.status = WAITING_FOR_HUMAN
claim.status = PENDING_HUMAN_REVIEW
human_task.status = OPEN
Day 14: Human task decision API

Build:

GET /human-tasks
GET /human-tasks/{task_id}
POST /human-tasks/{task_id}/assign
POST /human-tasks/{task_id}/complete

Done when:

Adjuster can approve/reject/modify payout/request info through API.
Decision is stored.
Decision is audited.
Week 4 plan
Day 15: Resume workflow

Build:

POST /workflow-runs/{workflow_run_id}/resume

Support:

APPROVE
REJECT
MODIFY_PAYOUT
REQUEST_MORE_INFO
ESCALATE

Done when:

Workflow resumes from human decision and lands in correct final state.
Day 16: Payment guardrail after human decision

Build:

final approved amount calculation
payment guardrail rerun
payment instruction creation
payment blocked path

Done when:

Modified payout creates payment instruction for modified amount only.
Day 17: Adjuster dashboard task queue

Build UI:

/review-tasks

Show:

open tasks
task type
priority
reason
risk flags
created date
review action

Done when:

You can see the auto-blocked claim in the dashboard.
Day 18: Task detail and decision form

Build UI:

/review-tasks/{task_id}

Show:

claim summary
risk flags
documents metadata
recommended payout
decision form

Done when:

You can modify payout from UI.
Day 19: Audit timeline UI

Build:

/claims/{claim_id}/audit

Done when:

You can show the full decision journey after resume.
Day 20: Demo hardening

Create demo script:

seed data
submit claim
execute workflow
open dashboard
modify payout
resume workflow
show audit trail

Add tests:

invoice before incident creates risk signal
3 claims in 12 months creates risk signal
workflow pauses
human task completes
modify payout resumes workflow
payment instruction uses modified amount
audit events created
Acceptance criteria for Phase 2

Phase 2 is complete when this works end-to-end:

Workflow can pause safely
Pause creates human task
Human task appears in adjuster dashboard
Task shows risk factors and recommendation
Adjuster can approve claim
Adjuster can reject claim
Adjuster can modify payout
Adjuster can request more info
Human decision is audited
Workflow can resume from decision
Payment guardrails run after decision
Modified payout creates payment instruction with modified amount
Audit timeline shows system and human decisions
Demo scenario works:
invoice date predates incident date + 3 claims in 12 months