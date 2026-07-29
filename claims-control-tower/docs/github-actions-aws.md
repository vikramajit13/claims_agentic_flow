# GitHub Actions AWS Deployment

This repository now includes:

- `.github/workflows/ci.yml`
- `.github/workflows/deploy-aws.yml`
- `infra/bootstrap`
- `infra/environments/dev`

The setup is designed to be:

- low-cost
- GitHub free-tier friendly
- safe for public or private repos
- free of long-lived AWS keys in code

## Security Model

Use GitHub OIDC to assume an AWS IAM role at deploy time.

That means:

- no AWS access key in the repo
- no AWS secret key in the repo
- one GitHub secret only:
  - `AWS_ROLE_ARN`

Everything else should go in GitHub repository or environment variables, not secrets, unless it is sensitive.

## Recommended Low-Cost Shape

For the current codebase, the cheapest reasonable deployment pattern is:

- web: S3 static hosting + optional CloudFront
- api: single ECS Fargate service using the smallest task size you can tolerate
- database: existing Postgres/pgvector instance, not provisioned from GitHub Actions

Why this is cost-conscious:

- the web app is static and cheap to host
- GitHub Actions only runs when you ask it to or on CI events
- no infrastructure is provisioned from the workflow
- you avoid accidental spend from auto-creating large AWS resources

## Required GitHub Secret

Add this in GitHub:

- `AWS_ROLE_ARN`

This should be the ARN of an IAM role trusted by GitHub OIDC.

## Required GitHub Variables

For API deploys:

- `AWS_REGION`
- `ECR_REPOSITORY`
- `ECS_CLUSTER`
- `ECS_SERVICE`
- `ECS_TASK_DEFINITION`
- `ECS_CONTAINER_NAME`

For web deploys:

- `FRONTEND_S3_BUCKET`

Optional:

- `CLOUDFRONT_DISTRIBUTION_ID`
- `VITE_API_BASE_URL`
- `VITE_SSE_URL`
- `VITE_WEBSOCKET_URL`

## AWS Resources You Need First

If you use the Terraform in `infra/`, most of these will be created for you.

The deploy workflow assumes these exist before the first deployment run:

1. ECR repository for the API image
2. ECS cluster
3. ECS service
4. ECS task execution role
5. ECS task role
6. Secrets Manager or SSM secret for:
   - `DATABASE_URL`
   - `LANGSMITH_API_KEY`
7. S3 bucket for the frontend
8. optional CloudFront distribution

## ECS Deployment Shape

The deploy workflow does not store a static task definition in the repository.

Instead it:

1. reads the current ECS task definition from AWS
2. swaps only the container image
3. registers the new revision
4. updates the ECS service

That keeps Terraform as the source of truth for:

- roles
- secrets
- log configuration
- CPU and memory
- networking

## Suggested AWS IAM Trust Policy

The GitHub deploy role should trust GitHub OIDC and restrict access to this repo.

At minimum, scope it to:

- your GitHub org/user
- this repository
- optionally the `main` branch or production environment

## How to Deploy

Apply Terraform first:

1. `cd infra/bootstrap`
2. `terraform init`
3. `terraform apply`
4. `cd ../environments/dev`
5. `terraform init`
6. `terraform apply`

Then copy the Terraform outputs into GitHub repository variables where needed.

Typical mappings:

- `aws_region` -> `AWS_REGION`
- `ecr_repository` -> `ECR_REPOSITORY`
- `ecs_cluster` -> `ECS_CLUSTER`
- `ecs_service` -> `ECS_SERVICE`
- `ecs_task_definition_family` -> `ECS_TASK_DEFINITION`
- `ecs_container_name` -> `ECS_CONTAINER_NAME`
- `frontend_bucket` -> `FRONTEND_S3_BUCKET`
- `cloudfront_distribution_id` -> `CLOUDFRONT_DISTRIBUTION_ID`
- `api_base_url` -> `VITE_API_BASE_URL`

Additional worker outputs are also available for later use:

- `ocr_ecr_repository`
- `ocr_ecs_service`
- `ocr_container_name`

The bootstrap output:

- `github_actions_role_arn`

should be stored in GitHub as the `AWS_ROLE_ARN` secret.

For the current frontend deployment, `VITE_API_BASE_URL` is required.
If it is not set in GitHub Actions, the built web app will fall back to the
local development default `http://127.0.0.1:8000`, which is incorrect for AWS.

After that, deploy from GitHub Actions:

From GitHub Actions:

1. Open `Deploy AWS`
2. Click `Run workflow`
3. Choose whether to deploy:
   - API
   - web
   - both

## Cost Notes

To keep costs low:

- keep ECS at `256 CPU / 512 MB` unless you need more
- use one Fargate service only for now
- do not provision RDS from Actions
- use S3 for the web app
- only enable CloudFront if you need global caching or custom domains
- run deploy manually with `workflow_dispatch` instead of every push

## What I Still Need From You

Before this can deploy for real, I need:

- AWS account ID
- AWS region
- target ECS cluster/service names
- ECR repository name
- S3 bucket name for the frontend
- whether you want CloudFront now or later

I do not need your AWS secret keys.

Use GitHub OIDC and IAM role assumption instead.
