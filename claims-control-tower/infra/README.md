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

## How To Apply And Test

1. Create or update `infra/environments/dev/terraform.tfvars` from the example file.
2. Create the `internal-service-token` secret in AWS Secrets Manager with a random string value.
3. Run `terraform apply` in `infra/environments/dev`.
4. Deploy the API container so the ALB target serves the latest backend code.
   Then copy Terraform outputs into GitHub Actions variables:
   - `aws_region` -> `AWS_REGION`
   - `ecr_repository` -> `ECR_REPOSITORY`
   - `ecs_cluster` -> `ECS_CLUSTER`
   - `ecs_service` -> `ECS_SERVICE`
   - `ecs_task_definition_family` -> `ECS_TASK_DEFINITION`
   - `ecs_container_name` -> `ECS_CONTAINER_NAME`
   - `frontend_bucket` -> `FRONTEND_S3_BUCKET`
   - `cloudfront_distribution_id` -> `CLOUDFRONT_DISTRIBUTION_ID`
   - `api_base_url` -> `VITE_API_BASE_URL`
5. Call `POST /v1/claims/{claim_id}/documents/presign` and keep the returned `upload_headers`.
6. Upload the file to the returned pre-signed URL and include every header from `upload_headers`.
7. Confirm in CloudWatch:
   - the S3 event Lambda ran
   - a message landed in the OCR queue
   - the OCR queue Lambda ran
8. Fetch the claim again from the API and confirm the document moved to `ocr_completed`.

## Important

Before applying:

- review the bucket names
- review the GitHub repo owner/name values in `bootstrap/terraform.tfvars`
- replace example values in any local `terraform.tfvars`

No secrets are stored in this repository.
