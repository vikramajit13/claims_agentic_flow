variable "aws_region" {
  description = "AWS region for the development environment."
  type        = string
  default     = "ap-southeast-2"
}

variable "aws_account_id" {
  description = "AWS account ID."
  type        = string
  default     = "819926065191"
}

variable "project_name" {
  description = "Project name prefix."
  type        = string
  default     = "claims-agent"
}

variable "environment" {
  description = "Environment name."
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR range for the VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs."
  type        = list(string)
  default     = ["10.42.1.0/24", "10.42.2.0/24"]
}

variable "api_container_name" {
  description = "Primary API container name."
  type        = string
  default     = "api"
}

variable "ocr_container_name" {
  description = "OCR worker container name."
  type        = string
  default     = "ocr-worker"
}

variable "api_container_port" {
  description = "API container port."
  type        = number
  default     = 8000
}

variable "api_task_cpu" {
  description = "CPU units for API task definition."
  type        = number
  default     = 256
}

variable "api_task_memory" {
  description = "Memory for API task definition."
  type        = number
  default     = 512
}

variable "ocr_task_cpu" {
  description = "CPU units for OCR worker task definition."
  type        = number
  default     = 256
}

variable "ocr_task_memory" {
  description = "Memory for OCR worker task definition."
  type        = number
  default     = 512
}

variable "api_desired_count" {
  description = "Desired count for the API service."
  type        = number
  default     = 1
}

variable "ocr_worker_desired_count" {
  description = "Desired count for the OCR worker. Defaults to 0 to reduce cost until the worker image is ready."
  type        = number
  default     = 0
}

variable "api_bootstrap_image" {
  description = "Temporary image so ECS can provision before GitHub Actions pushes the real API image."
  type        = string
  default     = "public.ecr.aws/docker/library/python:3.11-slim"
}

variable "ocr_bootstrap_image" {
  description = "Temporary image so ECS can provision before GitHub Actions pushes the real OCR image."
  type        = string
  default     = "public.ecr.aws/docker/library/python:3.11-slim"
}

variable "api_bootstrap_command" {
  description = "Bootstrap command for the API placeholder container."
  type        = list(string)
  default     = ["python", "-m", "http.server", "8000"]
}

variable "ocr_bootstrap_command" {
  description = "Bootstrap command for the OCR placeholder worker."
  type        = list(string)
  default     = ["python", "-c", "import time; time.sleep(3600)"]
}

variable "database_url_secret_arn" {
  description = "Secrets Manager ARN for DATABASE_URL."
  type        = string
  default     = null
}

variable "langsmith_api_key_secret_arn" {
  description = "Secrets Manager ARN for LANGSMITH_API_KEY."
  type        = string
  default     = null
}

variable "internal_service_token_secret_arn" {
  description = "Secrets Manager ARN for INTERNAL_SERVICE_TOKEN used by internal Lambda to API callbacks."
  type        = string
  default     = null
}

variable "frontend_bucket_name_override" {
  description = "Optional override for the frontend bucket name."
  type        = string
  default     = null
}

variable "documents_bucket_name_override" {
  description = "Optional override for the documents bucket name."
  type        = string
  default     = null
}

variable "llm_provider" {
  description = "LLM provider for document intelligence. Supported values: openai, bedrock."
  type        = string
  default     = "bedrock"
}

variable "document_intelligence_model" {
  description = "Model identifier used by document intelligence."
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}

variable "enable_llm_document_intelligence" {
  description = "Enable LLM-backed document intelligence."
  type        = bool
  default     = true
}
