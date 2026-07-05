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

## Important

Before applying:

- review the bucket names
- review the GitHub repo owner/name values in `bootstrap/terraform.tfvars`
- replace example values in any local `terraform.tfvars`

No secrets are stored in this repository.
