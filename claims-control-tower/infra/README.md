# Terraform Infrastructure

This directory is split into:

- `bootstrap/`: shared foundation for GitHub OIDC access
- `environments/dev/`: the actual low-cost development environment

## Apply Order

1. `infra/bootstrap`
2. `infra/environments/dev`

## Remote State

Both stacks are configured to use the existing S3 backend bucket:

- `claims-agent-terraform-state-819926065191-ap-southeast-2-an`

The backend uses the S3 lockfile feature instead of DynamoDB locking.

## Cost Strategy

This setup is intentionally optimized for low cost:

- no NAT Gateway
- ECS tasks run in public subnets with public IPs
- one API service
- one OCR worker service with `desired_count = 0` by default
- static frontend on S3 + CloudFront
- no database provisioning from Terraform yet

## S3 To OCR Lambda Flow

The dev stack now wires this path:

1. the documents bucket emits `s3:ObjectCreated:*`
2. the S3 event Lambda receives the event
3. the Lambda reads object metadata from S3
4. the Lambda posts back to the API internal endpoint to mark the document uploaded
5. if OCR is required, the Lambda sends a message to the OCR SQS queue
6. the OCR Lambda receives the SQS message through an event source mapping
7. the OCR Lambda posts back to the API internal endpoint to run OCR processing

This keeps Lambda handlers thin and makes it easier to add more event-driven handlers later without copying the full API runtime into every Lambda.

## Required Secrets

The dev environment expects these Secrets Manager ARNs in `infra/environments/dev/terraform.tfvars`:

- `database_url_secret_arn`
- `internal_service_token_secret_arn`
- `langsmith_api_key_secret_arn` optional

`internal_service_token_secret_arn` should contain a plain string token. Terraform injects that secret into the ECS API task as `INTERNAL_SERVICE_TOKEN`, and both Lambdas read the same secret to authenticate their internal callback requests.

## GitHub Actions Alignment

The deployment workflow now reads live Terraform outputs from `infra/environments/dev` instead of relying on copied GitHub repository variables for ECS, ECR, ALB, and S3 names.

This removes the biggest source of drift between Terraform and GitHub Actions for this phase.

### GitHub repository configuration

Required secret:

- `AWS_ROLE_ARN`

Optional repository variables for frontend runtime:

- `VITE_SSE_URL`
- `VITE_WEBSOCKET_URL`

Required repository variables only when using `deploy_infra=true` in the deploy workflow:

- `TF_VAR_DATABASE_URL_SECRET_ARN`
- `TF_VAR_INTERNAL_SERVICE_TOKEN_SECRET_ARN`

Optional repository variable for LangSmith injection during Terraform apply:

- `TF_VAR_LANGSMITH_API_KEY_SECRET_ARN`

### Important bootstrap note

The GitHub OIDC deploy role must be re-applied from `infra/bootstrap` after these changes so it can read the Terraform remote state bucket.

Without that bootstrap apply, the GitHub deployment workflow will not be able to load Terraform outputs.

## How To Apply And Test

1. Create or update `infra/environments/dev/terraform.tfvars` from the example file.
2. Create the `internal-service-token` secret in AWS Secrets Manager with a random string value.
3. Run `terraform apply` in `infra/environments/dev`.
4. Re-apply `infra/bootstrap` so the GitHub OIDC deploy role can read the Terraform state bucket.
5. Run the `Deploy AWS` GitHub Actions workflow.
   - Use `deploy_infra=false` if infrastructure is already up to date.
   - Use `deploy_infra=true` if Lambda packaging, ECS bootstrap changes, or other Terraform-managed infrastructure changed.
6. Call `POST /v1/claims/{claim_id}/documents/presign` and keep the returned `upload_headers`.
7. Upload the file to the returned pre-signed URL and include every header from `upload_headers`.
8. Confirm in CloudWatch:
   - the S3 event Lambda ran
   - a message landed in the OCR queue
   - the OCR queue Lambda ran
9. Fetch the claim again from the API and confirm the document moved to `ocr_completed`.

## Important

Before applying:

- review the bucket names
- review the GitHub repo owner/name values in `bootstrap/terraform.tfvars`
- replace example values in any local `terraform.tfvars`

No secrets are stored in this repository.
