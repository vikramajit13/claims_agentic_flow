output "aws_region" {
  description = "AWS region for GitHub Actions variables."
  value       = var.aws_region
}

output "ecr_repository" {
  description = "Primary API ECR repository name."
  value       = aws_ecr_repository.api.name
}

output "ecr_repository_url" {
  description = "Primary API ECR repository URL."
  value       = aws_ecr_repository.api.repository_url
}

output "ocr_ecr_repository" {
  description = "OCR worker ECR repository name."
  value       = aws_ecr_repository.ocr_worker.name
}

output "ecs_cluster" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.this.name
}

output "ecs_service" {
  description = "API ECS service name."
  value       = aws_ecs_service.api.name
}

output "ocr_ecs_service" {
  description = "OCR worker ECS service name."
  value       = aws_ecs_service.ocr_worker.name
}

output "ecs_task_definition_family" {
  description = "API ECS task definition family."
  value       = aws_ecs_task_definition.api.family
}

output "ecs_container_name" {
  description = "API container name."
  value       = var.api_container_name
}

output "ocr_container_name" {
  description = "OCR worker container name."
  value       = var.ocr_container_name
}

output "frontend_bucket" {
  description = "Frontend S3 bucket."
  value       = aws_s3_bucket.frontend.bucket
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID."
  value       = aws_cloudfront_distribution.frontend.id
}

output "cloudfront_distribution_arn" {
  description = "CloudFront distribution ARN."
  value       = aws_cloudfront_distribution.frontend.arn
}

output "documents_bucket" {
  description = "Claim documents S3 bucket."
  value       = aws_s3_bucket.documents.bucket
}

output "ocr_queue_url" {
  description = "OCR SQS queue URL."
  value       = aws_sqs_queue.ocr_jobs.id
}

output "s3_event_lambda_name" {
  description = "Lambda name for S3 object created to OCR queue bridge."
  value       = aws_lambda_function.s3_event_to_ocr_queue.function_name
}

output "ocr_queue_lambda_name" {
  description = "Lambda name for OCR SQS consumer."
  value       = aws_lambda_function.ocr_queue_to_api.function_name
}

output "alb_dns_name" {
  description = "Public API ALB DNS name."
  value       = aws_lb.api.dns_name
}

output "api_base_url" {
  description = "Public base URL for the API service."
  value       = "http://${aws_lb.api.dns_name}"
}

output "api_healthcheck_url" {
  description = "Public healthcheck URL for the API service."
  value       = "http://${aws_lb.api.dns_name}/health"
}

output "frontend_cloudfront_domain_name" {
  description = "Public CloudFront domain name for the frontend."
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "frontend_base_url" {
  description = "Public HTTPS URL for the frontend."
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "ecs_execution_role_arn" {
  description = "ECS execution role ARN."
  value       = aws_iam_role.ecs_execution.arn
}

output "ecs_task_role_arn" {
  description = "ECS task role ARN."
  value       = aws_iam_role.ecs_task.arn
}
