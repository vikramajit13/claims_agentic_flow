variable "aws_region" {
  description = "AWS region for shared bootstrap resources."
  type        = string
  default     = "ap-southeast-2"
}

variable "aws_account_id" {
  description = "AWS account ID."
  type        = string
  default     = "819926065191"
}

variable "project_name" {
  description = "Project name prefix for IAM resources."
  type        = string
  default     = "claims-agent"
}

variable "github_owner" {
  description = "GitHub owner or organisation name."
  type        = string
}

variable "github_repository" {
  description = "GitHub repository name."
  type        = string
  default     = "claims_agentic_flow"
}

variable "github_subjects" {
  description = "Allowed GitHub OIDC token subjects for this repository."
  type        = list(string)
  default     = []
}

variable "frontend_bucket_name" {
  description = "Frontend bucket name used by the deploy role."
  type        = string
  default     = "claims-agent-dev-web-819926065191-ap-southeast-2"
}

variable "ecr_repository_arns" {
  description = "ECR repositories that GitHub Actions can push to."
  type        = list(string)
  default = [
    "arn:aws:ecr:ap-southeast-2:819926065191:repository/claims-agent-dev-api",
    "arn:aws:ecr:ap-southeast-2:819926065191:repository/claims-agent-dev-ocr-worker"
  ]
}

variable "ecs_cluster_arn" {
  description = "ECS cluster ARN that GitHub Actions can update."
  type        = string
  default     = "arn:aws:ecs:ap-southeast-2:819926065191:cluster/claims-agent-dev"
}

variable "ecs_service_arns" {
  description = "ECS services that GitHub Actions can update."
  type        = list(string)
  default = [
    "arn:aws:ecs:ap-southeast-2:819926065191:service/claims-agent-dev/claims-agent-dev-api",
    "arn:aws:ecs:ap-southeast-2:819926065191:service/claims-agent-dev/claims-agent-dev-ocr-worker"
  ]
}

variable "cloudfront_distribution_arn" {
  description = "CloudFront distribution ARN that GitHub Actions can invalidate."
  type        = string
  default     = null
}

variable "pass_role_arns" {
  description = "IAM roles that GitHub Actions can pass to ECS."
  type        = list(string)
  default = [
    "arn:aws:iam::819926065191:role/claims-agent-dev-ecs-execution",
    "arn:aws:iam::819926065191:role/claims-agent-dev-ecs-task"
  ]
}
