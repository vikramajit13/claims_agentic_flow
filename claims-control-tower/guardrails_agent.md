This Phase 3 should be treated as a dedicated Business Guardrails layer, not scattered rules inside workflow code. The key is to make each guardrail explicit, auditable, configurable, and able to return either PASS, BLOCK, or REVIEW_REQUIRED.

Thought for a couple of seconds

Yes. Phase 3 should formalise your rules into a Business Guardrails Engine.

Do not bury these checks randomly inside workflow_service.py.

Build a clean layer like this:

Workflow
  ↓
BusinessGuardrailService
  ↓
Individual Guardrails
  ↓
GuardrailResult
  ↓
PASS / BLOCK / REVIEW_REQUIRED
  ↓
Audit event
  ↓
Workflow continues, pauses, or blocks

This is where the project becomes much more enterprise-relevant.

Phase 3 goal

Phase 3 should prove this:

The claims workflow does not rely only on model output or simple adjudication. It enforces deterministic business, policy, fraud, payment, and compliance guardrails before allowing a payout or payment instruction.

That is a strong insurance/banking message.

The guardrails you listed

You want to implement:

1. Policy active check
2. Has claim been raised within 15 days of buying policy?
3. Incident date within coverage period
4. Claim amount threshold
5. Invoice date cannot predate incident date
6. Payout near threshold triggers review
7. Repeat claims trigger review
8. Has claim been rejected earlier? If yes, send for human feedback
9. Final payout cannot exceed approved amount
10. Payment instruction cannot be created without human approval when high-risk

Good list.

But they should not all behave the same way.

Some should block.

Some should trigger review.

Some should just flag risk.

Recommended guardrail outcomes

Use three outcomes:

class GuardrailDecision(str, Enum):
    PASS = "PASS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCK = "BLOCK"

Meaning:

PASS
The workflow can continue.

REVIEW_REQUIRED
The workflow must pause and create a human review task.

BLOCK
The workflow cannot continue unless corrected or overridden by a permitted human process.

For your MVP, avoid override complexity. BLOCK means stop or reject/block payment.

Guardrail severity

Also track severity:

class GuardrailSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

This helps dashboard and audit.

Guardrail categories

Group your rules into four categories.

POLICY_GUARDRAIL
CLAIM_GUARDRAIL
FRAUD_RISK_GUARDRAIL
PAYMENT_GUARDRAIL

Mapping:

Guardrail	Category	Outcome
Policy active check	Policy	BLOCK
Claim within 15 days of buying policy	Fraud/Risk	REVIEW_REQUIRED
Incident date within coverage period	Policy	BLOCK
Claim amount threshold	Claim/Payment	REVIEW_REQUIRED or BLOCK
Invoice date predates incident date	Fraud/Risk	REVIEW_REQUIRED
Payout near threshold	Payment	REVIEW_REQUIRED
Repeat claims	Fraud/Risk	REVIEW_REQUIRED
Previously rejected claim	Claim/Fraud	REVIEW_REQUIRED
Final payout exceeds approved amount	Payment	BLOCK
High-risk payment without human approval	Payment	BLOCK

This distinction is important.

You want to show that not every issue is a rejection. Some are governance checkpoints.

Architecture change

Add this:

services/
  business_guardrails/
    guardrail_service.py
    guardrail_context.py
    guardrail_result.py
    rules/
      policy_active_guardrail.py
      early_claim_guardrail.py
      coverage_period_guardrail.py
      claim_amount_threshold_guardrail.py
      invoice_date_guardrail.py
      payout_threshold_guardrail.py
      repeat_claims_guardrail.py
      prior_rejection_guardrail.py
      final_payout_guardrail.py
      high_risk_payment_guardrail.py

Or keep it simpler:

services/
  business_guardrail_service.py

For your project, I’d start with one service file and clean methods. Later split into rule classes if it gets large.

Recommended MVP structure:

app/
  services/
    business_guardrails/
      __init__.py
      guardrail_models.py
      business_guardrail_service.py
      guardrail_config.py
Add these models
GuardrailResult
from enum import Enum
from pydantic import BaseModel
from typing import Any, Optional


class GuardrailDecision(str, Enum):
    PASS = "PASS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCK = "BLOCK"


class GuardrailSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class GuardrailCategory(str, Enum):
    POLICY = "POLICY"
    CLAIM = "CLAIM"
    FRAUD_RISK = "FRAUD_RISK"
    PAYMENT = "PAYMENT"


class GuardrailResult(BaseModel):
    code: str
    category: GuardrailCategory
    decision: GuardrailDecision
    severity: GuardrailSeverity
    message: str
    details: dict[str, Any] = {}

Example result:

{
  "code": "INVOICE_DATE_BEFORE_INCIDENT",
  "category": "FRAUD_RISK",
  "decision": "REVIEW_REQUIRED",
  "severity": "HIGH",
  "message": "Invoice date 2026-04-20 predates incident date 2026-04-25",
  "details": {
    "invoice_date": "2026-04-20",
    "incident_date": "2026-04-25"
  }
}
Add GuardrailEvaluationSummary

The workflow should not deal with 10 individual results directly. It should receive a summary.

class GuardrailEvaluationSummary(BaseModel):
    overall_decision: GuardrailDecision
    results: list[GuardrailResult]

    @property
    def blocking_results(self) -> list[GuardrailResult]:
        return [r for r in self.results if r.decision == GuardrailDecision.BLOCK]

    @property
    def review_results(self) -> list[GuardrailResult]:
        return [r for r in self.results if r.decision == GuardrailDecision.REVIEW_REQUIRED]

Overall decision logic:

If any BLOCK → overall_decision = BLOCK
Else if any REVIEW_REQUIRED → overall_decision = REVIEW_REQUIRED
Else → PASS
Guardrail config

Do not hardcode all thresholds inside methods.

Create:

from decimal import Decimal


class GuardrailConfig:
    EARLY_CLAIM_DAYS = 15
    LARGE_CLAIM_AMOUNT_THRESHOLD = Decimal("5000")
    PAYOUT_NEAR_THRESHOLD_PERCENTAGE = Decimal("0.90")
    REPEAT_CLAIMS_MONTHS = 12
    REPEAT_CLAIMS_THRESHOLD = 3

Later this can move to DB/config.

For Phase 3, config file is fine.

Where the guardrails fit in the workflow

Your workflow should run guardrails in two places.

1. Pre-adjudication guardrails

These check whether the claim itself is acceptable/risky.

policy active check
claim within 15 days of buying policy
incident date within coverage period
claim amount threshold
invoice date cannot predate incident date
repeat claims trigger review
has claim been rejected earlier

These run before recommendation/payment.

Claim Submitted
  ↓
Coverage Validation
  ↓
Evidence Validation
  ↓
Business Guardrails: Pre-Adjudication
  ↓
Adjudication
  ↓
Human Review if required
2. Pre-payment guardrails

These check whether payment is allowed.

payout near threshold triggers review
final payout cannot exceed approved amount
payment instruction cannot be created without human approval when high-risk

These run before payment instruction creation.

Approved / Human Decision
  ↓
Business Guardrails: Pre-Payment
  ↓
Payment Instruction Created or Blocked

This separation is important.

The two service methods you need

Build this:

class BusinessGuardrailService:
    def evaluate_pre_adjudication(self, claim_id: UUID) -> GuardrailEvaluationSummary:
        ...

    def evaluate_pre_payment(
        self,
        claim_id: UUID,
        approved_amount: Decimal,
        final_payout_amount: Decimal,
        human_approval_present: bool,
        is_high_risk: bool,
    ) -> GuardrailEvaluationSummary:
        ...

Do not make one giant method for everything.

Implement each guardrail
1. Policy active check
Rule
Policy must be ACTIVE.
Decision
If not active → BLOCK
Example
def check_policy_active(self, policy) -> GuardrailResult:
    if policy.status != "ACTIVE":
        return GuardrailResult(
            code="POLICY_NOT_ACTIVE",
            category=GuardrailCategory.POLICY,
            decision=GuardrailDecision.BLOCK,
            severity=GuardrailSeverity.CRITICAL,
            message="Policy is not active",
            details={
                "policy_id": str(policy.id),
                "policy_status": policy.status,
            },
        )

    return GuardrailResult(
        code="POLICY_ACTIVE",
        category=GuardrailCategory.POLICY,
        decision=GuardrailDecision.PASS,
        severity=GuardrailSeverity.LOW,
        message="Policy is active",
    )
Workflow impact
BLOCK → reject claim or mark as BLOCKED_POLICY

For MVP:

claim.status = REJECTED
workflow.status = COMPLETED
2. Claim raised within 15 days of buying policy
Rule
If incident/claim occurs within 15 days of policy start date → REVIEW_REQUIRED

Be precise here. There are two possible interpretations:

A. Claim submitted within 15 days of policy purchase
B. Incident occurred within 15 days of policy purchase

For fraud/leakage, use incident date, not submitted date.

Better rule:

Incident date within 15 days of policy start date triggers review.
Decision
REVIEW_REQUIRED
Example
def check_early_claim_after_policy_start(self, claim, policy) -> GuardrailResult:
    days_since_policy_start = (claim.incident_date - policy.active_from).days

    if 0 <= days_since_policy_start <= GuardrailConfig.EARLY_CLAIM_DAYS:
        return GuardrailResult(
            code="EARLY_CLAIM_AFTER_POLICY_START",
            category=GuardrailCategory.FRAUD_RISK,
            decision=GuardrailDecision.REVIEW_REQUIRED,
            severity=GuardrailSeverity.HIGH,
            message=f"Incident occurred {days_since_policy_start} days after policy start",
            details={
                "policy_start_date": str(policy.active_from),
                "incident_date": str(claim.incident_date),
                "days_since_policy_start": days_since_policy_start,
                "threshold_days": GuardrailConfig.EARLY_CLAIM_DAYS,
            },
        )

    return GuardrailResult(
        code="EARLY_CLAIM_AFTER_POLICY_START",
        category=GuardrailCategory.FRAUD_RISK,
        decision=GuardrailDecision.PASS,
        severity=GuardrailSeverity.LOW,
        message="Incident did not occur within early-claim review window",
    )
3. Incident date within coverage period
Rule
policy.active_from <= claim.incident_date <= policy.active_to
Decision
If outside period → BLOCK
Example
def check_incident_within_coverage_period(self, claim, policy) -> GuardrailResult:
    if not (policy.active_from <= claim.incident_date <= policy.active_to):
        return GuardrailResult(
            code="INCIDENT_OUTSIDE_COVERAGE_PERIOD",
            category=GuardrailCategory.POLICY,
            decision=GuardrailDecision.BLOCK,
            severity=GuardrailSeverity.CRITICAL,
            message="Incident date is outside the policy coverage period",
            details={
                "incident_date": str(claim.incident_date),
                "policy_active_from": str(policy.active_from),
                "policy_active_to": str(policy.active_to),
            },
        )

    return GuardrailResult(
        code="INCIDENT_WITHIN_COVERAGE_PERIOD",
        category=GuardrailCategory.POLICY,
        decision=GuardrailDecision.PASS,
        severity=GuardrailSeverity.LOW,
        message="Incident date is within policy coverage period",
    )
4. Claim amount threshold
Rule
If claim amount exceeds configured threshold → REVIEW_REQUIRED

This is not always a block. Large claims often require review.

Decision
REVIEW_REQUIRED
Example
def check_claim_amount_threshold(self, claim) -> GuardrailResult:
    threshold = GuardrailConfig.LARGE_CLAIM_AMOUNT_THRESHOLD

    if claim.claim_amount >= threshold:
        return GuardrailResult(
            code="CLAIM_AMOUNT_ABOVE_REVIEW_THRESHOLD",
            category=GuardrailCategory.CLAIM,
            decision=GuardrailDecision.REVIEW_REQUIRED,
            severity=GuardrailSeverity.MEDIUM,
            message="Claim amount exceeds manual review threshold",
            details={
                "claim_amount": str(claim.claim_amount),
                "threshold": str(threshold),
            },
        )

    return GuardrailResult(
        code="CLAIM_AMOUNT_ABOVE_REVIEW_THRESHOLD",
        category=GuardrailCategory.CLAIM,
        decision=GuardrailDecision.PASS,
        severity=GuardrailSeverity.LOW,
        message="Claim amount is below manual review threshold",
    )
5. Invoice date cannot predate incident date
Rule
invoice_date >= incident_date
Decision
REVIEW_REQUIRED

You could block, but review is better because there may be legitimate cases: pre-authorised quote, estimate, booking date, invoice correction issue.

Example
def check_invoice_date_not_before_incident(self, claim, documents) -> GuardrailResult:
    invoice_docs = [
        doc for doc in documents
        if doc.document_type == "INVOICE"
    ]

    for doc in invoice_docs:
        metadata = doc.document_metadata or {}
        invoice_date = metadata.get("invoice_date")

        if not invoice_date:
            continue

        invoice_date = date.fromisoformat(invoice_date)

        if invoice_date < claim.incident_date:
            return GuardrailResult(
                code="INVOICE_DATE_BEFORE_INCIDENT",
                category=GuardrailCategory.FRAUD_RISK,
                decision=GuardrailDecision.REVIEW_REQUIRED,
                severity=GuardrailSeverity.HIGH,
                message="Invoice date predates incident date",
                details={
                    "document_id": str(doc.id),
                    "file_name": doc.file_name,
                    "invoice_date": str(invoice_date),
                    "incident_date": str(claim.incident_date),
                },
            )

    return GuardrailResult(
        code="INVOICE_DATE_BEFORE_INCIDENT",
        category=GuardrailCategory.FRAUD_RISK,
        decision=GuardrailDecision.PASS,
        severity=GuardrailSeverity.LOW,
        message="No invoice date anomaly detected",
    )
6. Payout near threshold triggers review
Rule

This needs a defined threshold.

Possible interpretations:

A. Payout near policy coverage limit
B. Payout near approval limit
C. Payout near claim amount

Use policy coverage limit first.

Rule:

If final/recommended payout >= 90% of policy coverage limit → REVIEW_REQUIRED
Decision
REVIEW_REQUIRED
Example
def check_payout_near_policy_limit(self, policy, payout_amount) -> GuardrailResult:
    ratio = payout_amount / policy.coverage_limit
    threshold_ratio = GuardrailConfig.PAYOUT_NEAR_THRESHOLD_PERCENTAGE

    if ratio >= threshold_ratio:
        return GuardrailResult(
            code="PAYOUT_NEAR_POLICY_LIMIT",
            category=GuardrailCategory.PAYMENT,
            decision=GuardrailDecision.REVIEW_REQUIRED,
            severity=GuardrailSeverity.HIGH,
            message="Payout amount is near policy coverage limit",
            details={
                "payout_amount": str(payout_amount),
                "coverage_limit": str(policy.coverage_limit),
                "ratio": str(ratio),
                "threshold_ratio": str(threshold_ratio),
            },
        )

    return GuardrailResult(
        code="PAYOUT_NEAR_POLICY_LIMIT",
        category=GuardrailCategory.PAYMENT,
        decision=GuardrailDecision.PASS,
        severity=GuardrailSeverity.LOW,
        message="Payout amount is not near policy coverage limit",
    )
7. Repeat claims trigger review
Rule
If customer has >= 3 claims in last 12 months → REVIEW_REQUIRED

You can include current claim or exclude it. Be explicit.

Better:

If customer has 3 or more prior claims in the last 12 months, excluding current claim → REVIEW_REQUIRED
Decision
REVIEW_REQUIRED
Example
def check_repeat_claims(self, claim) -> GuardrailResult:
    prior_claims = self.claim_repository.get_claims_for_customer_in_last_months(
        customer_id=claim.customer_id,
        months=GuardrailConfig.REPEAT_CLAIMS_MONTHS,
        exclude_claim_id=claim.id,
    )

    prior_claim_count = len(prior_claims)

    if prior_claim_count >= GuardrailConfig.REPEAT_CLAIMS_THRESHOLD:
        return GuardrailResult(
            code="REPEAT_CLAIMS_REVIEW_REQUIRED",
            category=GuardrailCategory.FRAUD_RISK,
            decision=GuardrailDecision.REVIEW_REQUIRED,
            severity=GuardrailSeverity.HIGH,
            message=f"Customer has {prior_claim_count} prior claims in the last 12 months",
            details={
                "customer_id": claim.customer_id,
                "prior_claim_count": prior_claim_count,
                "months": GuardrailConfig.REPEAT_CLAIMS_MONTHS,
                "threshold": GuardrailConfig.REPEAT_CLAIMS_THRESHOLD,
                "prior_claim_ids": [str(c.id) for c in prior_claims],
            },
        )

    return GuardrailResult(
        code="REPEAT_CLAIMS_REVIEW_REQUIRED",
        category=GuardrailCategory.FRAUD_RISK,
        decision=GuardrailDecision.PASS,
        severity=GuardrailSeverity.LOW,
        message="Repeat claim threshold not met",
    )
8. Has claim been rejected earlier?

This one needs better wording.

A single claim being “rejected earlier” implies re-open, resubmission, appeal, or duplicate claim.

There are two versions:

A. Same claim was previously rejected and is now being resubmitted.
B. Similar claim from same customer was rejected earlier.

For MVP, implement the simpler one:

If the same customer has a prior rejected claim with same claim_type and similar incident date/amount, require human review.

Or if your model supports parent claim:

If claim.previous_claim_id points to a rejected claim, require human review.

Simpler for your current system:

Add optional field to claims:

previous_claim_id nullable

If present and previous claim status is REJECTED, then:

REVIEW_REQUIRED
Recommended data model addition
claims.previous_claim_id
claims.reopened_from_claim_id

For MVP use one:

previous_claim_id
Example
def check_prior_rejected_claim(self, claim) -> GuardrailResult:
    if not claim.previous_claim_id:
        return GuardrailResult(
            code="PRIOR_REJECTED_CLAIM",
            category=GuardrailCategory.CLAIM,
            decision=GuardrailDecision.PASS,
            severity=GuardrailSeverity.LOW,
            message="No prior rejected claim linked",
        )

    previous_claim = self.claim_repository.get_by_id(claim.previous_claim_id)

    if previous_claim and previous_claim.status == "REJECTED":
        return GuardrailResult(
            code="PRIOR_REJECTED_CLAIM",
            category=GuardrailCategory.CLAIM,
            decision=GuardrailDecision.REVIEW_REQUIRED,
            severity=GuardrailSeverity.HIGH,
            message="Claim is linked to a previously rejected claim and requires human review",
            details={
                "current_claim_id": str(claim.id),
                "previous_claim_id": str(previous_claim.id),
                "previous_claim_status": previous_claim.status,
            },
        )

    return GuardrailResult(
        code="PRIOR_REJECTED_CLAIM",
        category=GuardrailCategory.CLAIM,
        decision=GuardrailDecision.PASS,
        severity=GuardrailSeverity.LOW,
        message="Linked previous claim was not rejected",
    )
Human feedback wording

Instead of “share for human feedback”, call it:

Create human review task with previous rejection context.

That is more enterprise/professional.

9. Final payout cannot exceed approved amount
Rule
final_payout_amount <= approved_amount
Decision
BLOCK

This is a hard payment control.

Example
def check_final_payout_not_above_approved_amount(
    self,
    approved_amount,
    final_payout_amount,
) -> GuardrailResult:
    if final_payout_amount > approved_amount:
        return GuardrailResult(
            code="FINAL_PAYOUT_EXCEEDS_APPROVED_AMOUNT",
            category=GuardrailCategory.PAYMENT,
            decision=GuardrailDecision.BLOCK,
            severity=GuardrailSeverity.CRITICAL,
            message="Final payout amount exceeds approved amount",
            details={
                "approved_amount": str(approved_amount),
                "final_payout_amount": str(final_payout_amount),
            },
        )

    return GuardrailResult(
        code="FINAL_PAYOUT_EXCEEDS_APPROVED_AMOUNT",
        category=GuardrailCategory.PAYMENT,
        decision=GuardrailDecision.PASS,
        severity=GuardrailSeverity.LOW,
        message="Final payout amount does not exceed approved amount",
    )
10. Payment instruction cannot be created without human approval when high-risk
Rule
If claim is high-risk and no completed human approval exists → BLOCK payment instruction
Decision
BLOCK

This is one of your most important enterprise controls.

Example
def check_high_risk_payment_has_human_approval(
    self,
    is_high_risk: bool,
    human_approval_present: bool,
) -> GuardrailResult:
    if is_high_risk and not human_approval_present:
        return GuardrailResult(
            code="HIGH_RISK_PAYMENT_REQUIRES_HUMAN_APPROVAL",
            category=GuardrailCategory.PAYMENT,
            decision=GuardrailDecision.BLOCK,
            severity=GuardrailSeverity.CRITICAL,
            message="Payment instruction cannot be created for high-risk claim without human approval",
            details={
                "is_high_risk": is_high_risk,
                "human_approval_present": human_approval_present,
            },
        )

    return GuardrailResult(
        code="HIGH_RISK_PAYMENT_REQUIRES_HUMAN_APPROVAL",
        category=GuardrailCategory.PAYMENT,
        decision=GuardrailDecision.PASS,
        severity=GuardrailSeverity.LOW,
        message="High-risk payment approval requirement satisfied",
    )
The BusinessGuardrailService

Here is the shape.

class BusinessGuardrailService:
    def __init__(
        self,
        claim_repository,
        policy_repository,
        document_repository,
        human_task_repository,
        audit_service,
    ):
        self.claim_repository = claim_repository
        self.policy_repository = policy_repository
        self.document_repository = document_repository
        self.human_task_repository = human_task_repository
        self.audit_service = audit_service

    def evaluate_pre_adjudication(self, claim_id):
        claim = self.claim_repository.get_by_id(claim_id)
        policy = self.policy_repository.get_by_id(claim.policy_id)
        documents = self.document_repository.get_by_claim_id(claim_id)

        results = [
            self.check_policy_active(policy),
            self.check_early_claim_after_policy_start(claim, policy),
            self.check_incident_within_coverage_period(claim, policy),
            self.check_claim_amount_threshold(claim),
            self.check_invoice_date_not_before_incident(claim, documents),
            self.check_repeat_claims(claim),
            self.check_prior_rejected_claim(claim),
        ]

        summary = self._summarise(results)

        self.audit_service.record_event(
            claim_id=claim.id,
            event_type="BUSINESS_GUARDRAILS_EVALUATED",
            step_name="PRE_ADJUDICATION_GUARDRAILS",
            payload=summary.model_dump(mode="json"),
        )

        return summary

    def evaluate_pre_payment(
        self,
        claim_id,
        approved_amount,
        final_payout_amount,
        is_high_risk,
    ):
        claim = self.claim_repository.get_by_id(claim_id)
        policy = self.policy_repository.get_by_id(claim.policy_id)

        human_approval_present = (
            self.human_task_repository.has_completed_approval_for_claim(claim_id)
        )

        results = [
            self.check_payout_near_policy_limit(policy, final_payout_amount),
            self.check_final_payout_not_above_approved_amount(
                approved_amount=approved_amount,
                final_payout_amount=final_payout_amount,
            ),
            self.check_high_risk_payment_has_human_approval(
                is_high_risk=is_high_risk,
                human_approval_present=human_approval_present,
            ),
        ]

        summary = self._summarise(results)

        self.audit_service.record_event(
            claim_id=claim.id,
            event_type="BUSINESS_GUARDRAILS_EVALUATED",
            step_name="PRE_PAYMENT_GUARDRAILS",
            payload=summary.model_dump(mode="json"),
        )

        return summary

    def _summarise(self, results):
        if any(r.decision == GuardrailDecision.BLOCK for r in results):
            overall_decision = GuardrailDecision.BLOCK
        elif any(r.decision == GuardrailDecision.REVIEW_REQUIRED for r in results):
            overall_decision = GuardrailDecision.REVIEW_REQUIRED
        else:
            overall_decision = GuardrailDecision.PASS

        return GuardrailEvaluationSummary(
            overall_decision=overall_decision,
            results=results,
        )
How workflow should use pre-adjudication guardrails

Inside your workflow execution:

guardrail_summary = business_guardrail_service.evaluate_pre_adjudication(
    claim_id=claim.id
)

if guardrail_summary.overall_decision == GuardrailDecision.BLOCK:
    claim.status = "REJECTED"
    workflow_run.status = "COMPLETED"
    workflow_run.current_step = "COMPLETED"

    audit_service.record_event(
        event_type="CLAIM_BLOCKED_BY_GUARDRAILS",
        step_name="PRE_ADJUDICATION_GUARDRAILS",
        payload={
            "blocking_results": [
                r.model_dump(mode="json")
                for r in guardrail_summary.blocking_results
            ]
        },
    )

    return

if guardrail_summary.overall_decision == GuardrailDecision.REVIEW_REQUIRED:
    human_task_service.create_task(
        claim_id=claim.id,
        workflow_run_id=workflow_run.id,
        task_type="CLAIM_REVIEW",
        priority="HIGH",
        created_reason="Business guardrails require human review",
        risk_factors=[
            r.model_dump(mode="json")
            for r in guardrail_summary.review_results
        ],
        recommended_decision="REVIEW_REQUIRED",
        recommended_payout_amount=claim.claim_amount,
    )

    workflow_run.status = "WAITING_FOR_HUMAN"
    workflow_run.current_step = "HUMAN_REVIEW"
    claim.status = "PENDING_HUMAN_REVIEW"

    audit_service.record_event(
        event_type="WORKFLOW_PAUSED",
        step_name="HUMAN_REVIEW",
        payload={
            "reason": "BUSINESS_GUARDRAILS_REVIEW_REQUIRED",
            "review_results": [
                r.model_dump(mode="json")
                for r in guardrail_summary.review_results
            ],
        },
    )

    return

This is the heart of Phase 3.

How workflow should use pre-payment guardrails

Before creating payment instruction:

payment_guardrail_summary = business_guardrail_service.evaluate_pre_payment(
    claim_id=claim.id,
    approved_amount=approved_amount,
    final_payout_amount=final_payout_amount,
    is_high_risk=is_high_risk,
)

if payment_guardrail_summary.overall_decision == GuardrailDecision.BLOCK:
    claim.status = "PAYMENT_BLOCKED"
    workflow_run.status = "COMPLETED"
    workflow_run.current_step = "PAYMENT_BLOCKED"

    audit_service.record_event(
        event_type="PAYMENT_BLOCKED_BY_GUARDRAILS",
        step_name="PRE_PAYMENT_GUARDRAILS",
        payload={
            "blocking_results": [
                r.model_dump(mode="json")
                for r in payment_guardrail_summary.blocking_results
            ]
        },
    )

    return

if payment_guardrail_summary.overall_decision == GuardrailDecision.REVIEW_REQUIRED:
    human_task_service.create_task(
        claim_id=claim.id,
        workflow_run_id=workflow_run.id,
        task_type="PAYMENT_REVIEW",
        priority="HIGH",
        created_reason="Pre-payment guardrails require human review",
        risk_factors=[
            r.model_dump(mode="json")
            for r in payment_guardrail_summary.review_results
        ],
        recommended_decision="REVIEW_REQUIRED",
        recommended_payout_amount=final_payout_amount,
    )

    workflow_run.status = "WAITING_FOR_HUMAN"
    workflow_run.current_step = "PAYMENT_REVIEW"
    claim.status = "PENDING_HUMAN_REVIEW"

    audit_service.record_event(
        event_type="WORKFLOW_PAUSED",
        step_name="PAYMENT_REVIEW",
        payload={
            "reason": "PRE_PAYMENT_GUARDRAILS_REVIEW_REQUIRED",
            "review_results": [
                r.model_dump(mode="json")
                for r in payment_guardrail_summary.review_results
            ],
        },
    )

    return

payment_instruction_service.create_payment_instruction(
    claim_id=claim.id,
    workflow_run_id=workflow_run.id,
    amount=final_payout_amount,
)
Important: avoid infinite review loops

There is one trap.

If payout near threshold triggers review, and the human approves it, then when workflow resumes and checks pre-payment guardrails again, it may again trigger review.

You need to handle this.

Solution:

Some REVIEW_REQUIRED guardrails can be satisfied by prior human approval.

Example:

PAYOUT_NEAR_POLICY_LIMIT → review required only if no completed payment review exists.

So modify the pre-payment logic:

human_approval_present = self.human_task_repository.has_completed_approval_for_claim(
    claim_id
)

Then for review-type pre-payment rules:

if payout_near_limit and not human_approval_present:
    REVIEW_REQUIRED
else:
    PASS

Same for repeat claims or early claim review if already approved.

This is critical.

Add approval context

Your human task repository should have methods like:

def has_completed_approval_for_claim(self, claim_id) -> bool:
    ...

def has_completed_payment_approval_for_claim(self, claim_id) -> bool:
    ...

def has_completed_review_for_guardrail_code(
    self,
    claim_id,
    guardrail_code: str,
) -> bool:
    ...

For MVP, start simple:

has_completed_approval_for_claim(claim_id)

Later make it guardrail-specific.

Add these audit event types

Add these to your enum:

BUSINESS_GUARDRAILS_EVALUATED
CLAIM_BLOCKED_BY_GUARDRAILS
PAYMENT_BLOCKED_BY_GUARDRAILS
GUARDRAIL_REVIEW_REQUIRED
GUARDRAIL_PASSED
GUARDRAIL_FAILED
HUMAN_APPROVAL_SATISFIED_GUARDRAIL

For every guardrail evaluation, audit:

guardrail code
decision
severity
message
input facts used
timestamp
workflow step

This is what makes it enterprise-grade.

Database changes

You may not need a separate table yet, because you can store results in workflow_events.

But if you want a better design, add:

guardrail_evaluations
Recommended for Phase 3

Add this table. It will make the project stronger.

guardrail_evaluations
  id
  claim_id
  workflow_run_id
  phase
  overall_decision
  evaluated_at

And:

guardrail_evaluation_results
  id
  guardrail_evaluation_id
  code
  category
  decision
  severity
  message
  details JSONB

However, if you want to move faster:

Store it in workflow_events.event_payload first.

My blunt recommendation:

For a portfolio/interview project, add the table if Phase 1 and 2 are already clean. It gives you better dashboard and evidence.

Minimal DB addition

At minimum, add this:

workflow_events.event_payload JSONB

If already present, no new table required.

Better DB addition

Add:

CREATE TABLE guardrail_evaluations (
    id UUID PRIMARY KEY,
    claim_id UUID NOT NULL REFERENCES claims(id),
    workflow_run_id UUID NOT NULL REFERENCES workflow_runs(id),
    phase VARCHAR(100) NOT NULL,
    overall_decision VARCHAR(50) NOT NULL,
    evaluated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE guardrail_evaluation_results (
    id UUID PRIMARY KEY,
    guardrail_evaluation_id UUID NOT NULL REFERENCES guardrail_evaluations(id),
    code VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    decision VARCHAR(50) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    details JSONB
);

This lets your UI show guardrails cleanly.

API endpoints for Phase 3

Add these:

GET /claims/{claim_id}/guardrails
GET /workflow-runs/{workflow_run_id}/guardrails

Optional manual test endpoint:

POST /claims/{claim_id}/guardrails/evaluate

For production, guardrails should run from workflow, not manually. But for demo/testing, this endpoint is useful.

Example response:

{
  "claim_id": "CLM-001",
  "workflow_run_id": "WFR-001",
  "phase": "PRE_ADJUDICATION",
  "overall_decision": "REVIEW_REQUIRED",
  "results": [
    {
      "code": "POLICY_ACTIVE",
      "category": "POLICY",
      "decision": "PASS",
      "severity": "LOW",
      "message": "Policy is active"
    },
    {
      "code": "EARLY_CLAIM_AFTER_POLICY_START",
      "category": "FRAUD_RISK",
      "decision": "REVIEW_REQUIRED",
      "severity": "HIGH",
      "message": "Incident occurred 8 days after policy start"
    },
    {
      "code": "INVOICE_DATE_BEFORE_INCIDENT",
      "category": "FRAUD_RISK",
      "decision": "REVIEW_REQUIRED",
      "severity": "HIGH",
      "message": "Invoice date predates incident date"
    }
  ]
}
Dashboard changes

Add a guardrails panel to the adjuster dashboard.

On the task detail page, show:

Business Guardrails

With a table:

Code | Category | Decision | Severity | Message

Example:

Code	Category	Decision	Severity	Message
POLICY_ACTIVE	POLICY	PASS	LOW	Policy is active
INVOICE_DATE_BEFORE_INCIDENT	FRAUD_RISK	REVIEW_REQUIRED	HIGH	Invoice date predates incident date
REPEAT_CLAIMS_REVIEW_REQUIRED	FRAUD_RISK	REVIEW_REQUIRED	HIGH	Customer has 3 prior claims in 12 months
PAYMENT_APPROVAL_REQUIRED	PAYMENT	BLOCK	CRITICAL	High-risk payment requires human approval

This is where the project becomes visibly strong.

Your main demo scenario

Use this scenario:

Customer bought policy on: 2026-04-15
Incident date: 2026-04-23
Invoice date: 2026-04-20
Claim submitted: 2026-04-26
Claim amount: 9,200
Policy coverage limit: 10,000
Customer prior claims in last 12 months: 3
No human approval initially

The guardrails should produce:

Policy active check → PASS
Claim within 15 days of policy start → REVIEW_REQUIRED
Incident date within coverage period → PASS
Claim amount threshold → REVIEW_REQUIRED
Invoice date before incident → REVIEW_REQUIRED
Payout near threshold → REVIEW_REQUIRED
Repeat claims → REVIEW_REQUIRED
Prior rejection → PASS or REVIEW_REQUIRED depending on seed data
Final payout > approved amount → PASS initially
High-risk payment without human approval → BLOCK

This lets you demo both:

review required
payment blocked
human approval
payment allowed after approval
Important business behaviour
Before human review

Payment should be blocked:

{
  "overall_decision": "BLOCK",
  "blocking_result": {
    "code": "HIGH_RISK_PAYMENT_REQUIRES_HUMAN_APPROVAL",
    "message": "Payment instruction cannot be created for high-risk claim without human approval"
  }
}
After human review

Adjuster modifies payout:

{
  "decision": "MODIFY_PAYOUT",
  "approved_amount": 7200,
  "notes": "Approved after reviewing invoice anomaly and claim history."
}

Then pre-payment guardrails run again:

Final payout cannot exceed approved amount → PASS
High-risk payment has human approval → PASS
Payment instruction created → YES

This is a great demo.

Build order

Do it in this order.

Step 1: Add guardrail models

Build:

GuardrailDecision
GuardrailSeverity
GuardrailCategory
GuardrailResult
GuardrailEvaluationSummary

Do this first.

Step 2: Add guardrail config

Build:

EARLY_CLAIM_DAYS = 15
LARGE_CLAIM_AMOUNT_THRESHOLD = 5000
PAYOUT_NEAR_THRESHOLD_PERCENTAGE = 0.90
REPEAT_CLAIMS_MONTHS = 12
REPEAT_CLAIMS_THRESHOLD = 3
Step 3: Implement pre-adjudication guardrails

Implement:

policy active
early claim
incident coverage period
claim amount threshold
invoice date before incident
repeat claims
prior rejected claim
Step 4: Implement pre-payment guardrails

Implement:

payout near threshold
final payout cannot exceed approved amount
high-risk payment requires human approval
Step 5: Integrate into workflow

Add:

PRE_ADJUDICATION_GUARDRAILS
PRE_PAYMENT_GUARDRAILS

Workflow states:

class WorkflowStep(str, Enum):
    CLAIM_INTAKE = "CLAIM_INTAKE"
    COVERAGE_VALIDATION = "COVERAGE_VALIDATION"
    EVIDENCE_VALIDATION = "EVIDENCE_VALIDATION"
    PRE_ADJUDICATION_GUARDRAILS = "PRE_ADJUDICATION_GUARDRAILS"
    ADJUDICATION = "ADJUDICATION"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    PRE_PAYMENT_GUARDRAILS = "PRE_PAYMENT_GUARDRAILS"
    PAYMENT_INSTRUCTION = "PAYMENT_INSTRUCTION"
    COMPLETED = "COMPLETED"
Step 6: Add audit events

Every guardrail evaluation should create:

BUSINESS_GUARDRAILS_EVALUATED

If review required:

GUARDRAIL_REVIEW_REQUIRED
WORKFLOW_PAUSED
HUMAN_TASK_CREATED

If blocked:

CLAIM_BLOCKED_BY_GUARDRAILS
or
PAYMENT_BLOCKED_BY_GUARDRAILS
Step 7: Add tests

Test every guardrail separately.

Minimum tests:

inactive policy blocks claim
incident outside coverage blocks claim
incident within 15 days triggers review
claim above threshold triggers review
invoice before incident triggers review
repeat claims trigger review
prior rejected claim triggers review
final payout above approved amount blocks payment
high-risk payment without human approval blocks payment
high-risk payment with human approval passes payment

Also add one end-to-end test:

high-risk claim pauses
human approves
workflow resumes
payment guardrails pass
payment instruction created
What to avoid

Do not turn this into a rules platform yet.

Avoid:

Drools
dynamic rule editor
database-configured rule DSL
complex policy versioning
multi-level approvals
manager approval hierarchy
real-time notifications
LLM reasoning
LangGraph migration

For Phase 3, deterministic Python guardrails are enough.

My recommended implementation scope

For Phase 3, build exactly this:

1. BusinessGuardrailService
2. GuardrailResult model
3. Pre-adjudication guardrails
4. Pre-payment guardrails
5. Human review integration
6. Audit logging
7. Dashboard guardrail panel
8. Unit tests
9. One strong end-to-end demo

That is enough.

The final Phase 3 flow
Claim submitted
    ↓
Workflow starts
    ↓
Coverage/evidence validation
    ↓
Pre-adjudication business guardrails
    ↓
If BLOCK:
    reject/block claim and audit
    ↓
If REVIEW_REQUIRED:
    pause workflow
    create human task
    show guardrails in dashboard
    ↓
Adjuster decision
    ↓
Resume workflow
    ↓
Pre-payment business guardrails
    ↓
If BLOCK:
    block payment and audit
    ↓
If REVIEW_REQUIRED:
    pause for payment review
    ↓
If PASS:
    create payment instruction
    ↓
Complete workflow