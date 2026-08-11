# Local-First Next Steps

This project has already proven the AWS path for:

- ECS deployment
- S3 upload flow
- OCR callback flow
- LLM-backed document intelligence
- investigation graph execution beyond the earlier tool-call failure

For the next stage, the cheapest and fastest path is to pause the AWS dev environment and continue feature work locally with Docker.

## Recommended Plan

1. Capture the current AWS config before destroying anything.
2. Pause the `dev` Terraform stack to stop Fargate, ALB, CloudFront, and related spend.
3. Continue feature development locally with Docker Compose and Postgres.
4. Recreate AWS only when the next milestone is ready.

## What To Keep Before Teardown

Save these values somewhere outside the live stack:

- AWS region: `ap-southeast-2`
- API service name used in practice: `claims-agent-dev-api-live`
- ECS task family: `claims-agent-dev-api`
- documents bucket name
- frontend CloudFront domain
- OpenAI-compatible base URL
- current model id
- Secrets Manager secret names and ARNs

Useful Terraform outputs:

```bash
cd infra/environments/dev
terraform output
```

Useful live checks:

```bash
AWS_PROFILE=claims-agent-bootstrap AWS_REGION=ap-southeast-2 aws ecs describe-services \
  --cluster claims-agent-dev \
  --services claims-agent-dev-api-live

AWS_PROFILE=claims-agent-bootstrap AWS_REGION=ap-southeast-2 aws ecr describe-repositories \
  --repository-names claims-agent-dev-api claims-agent-dev-ocr-worker
```

## Cost-Saving Teardown

To remove the Terraform-managed dev stack:

```bash
cd infra/environments/dev
AWS_PROFILE=claims-agent-bootstrap AWS_REGION=ap-southeast-2 terraform destroy
```

Notes:

- Review the destroy plan carefully before confirming.
- This will remove the Terraform-managed dev infrastructure, including the API load balancer, ECS services, CloudFront distribution, S3 buckets, Lambdas, and queue if they are still in Terraform state.
- ECR repositories and secrets may also be removed if they are still managed in state. Double-check the plan first if you want to keep them.
- The `bootstrap` stack should usually stay in place so GitHub OIDC access remains available for the next re-deploy.

## Local Development Path

Local Docker Compose already gives you:

- Postgres with pgvector
- the FastAPI API on `http://127.0.0.1:8000`
- mock S3, mock OCR, and mock SQS

Start local services:

```bash
cp .env.example .env
docker compose up --build
```

The local Docker defaults are now tuned for graph work:

- `DEFAULT_HITL_REQUIRED=false`
- Postgres-backed local state
- mock upload/OCR flow for fast iteration

## Local Smoke Test

Run the local end-to-end smoke test:

```bash
./scripts/local-dev-smoke.sh
```

This will:

- create a claim
- create a mock document upload
- complete the upload
- start the workflow with `hitl_required=false`
- print the final claim payload

## Next Build Targets

Build these locally before recreating AWS:

1. Make graph resume after human review work cleanly.
2. Make tool invocation visible in the UI or logs.
3. Replace any remaining SQLite-only drift with durable Postgres behavior.
4. Add a local and cloud smoke-test path for the same workflow.
5. Only then bring AWS back for a cleaner demo environment.
