locals {
  name_prefix = "${var.project_name}-${var.environment}"

  frontend_bucket_name = coalesce(
    var.frontend_bucket_name_override,
    "${local.name_prefix}-web-${var.aws_account_id}-${var.aws_region}"
  )

  documents_bucket_name = coalesce(
    var.documents_bucket_name_override,
    "${local.name_prefix}-documents-${var.aws_account_id}-${var.aws_region}"
  )

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  secret_arns = compact([
    var.database_url_secret_arn,
    var.langsmith_api_key_secret_arn
  ])
}
