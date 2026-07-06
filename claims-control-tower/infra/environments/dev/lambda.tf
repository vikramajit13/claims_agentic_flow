data "archive_file" "s3_event_to_ocr_queue" {
  type        = "zip"
  source_dir  = "${path.module}/../../../apps/api/lambda_src"
  output_path = "${path.module}/.terraform-build/s3_event_to_ocr_queue.zip"
  excludes    = ["ocr_queue_to_api.py", "__pycache__"]
}

data "archive_file" "ocr_queue_to_api" {
  type        = "zip"
  source_dir  = "${path.module}/../../../apps/api/lambda_src"
  output_path = "${path.module}/.terraform-build/ocr_queue_to_api.zip"
  excludes    = ["s3_event_to_ocr_queue.py", "__pycache__"]
}

resource "aws_lambda_function" "s3_event_to_ocr_queue" {
  function_name    = "${local.name_prefix}-s3-event-to-ocr-queue"
  role             = aws_iam_role.s3_event_lambda.arn
  handler          = "s3_event_to_ocr_queue.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.s3_event_to_ocr_queue.output_path
  source_code_hash = data.archive_file.s3_event_to_ocr_queue.output_base64sha256
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      API_INTERNAL_BASE_URL             = "http://${aws_lb.api.dns_name}"
      AWS_REGION                        = var.aws_region
      INTERNAL_SERVICE_TOKEN_SECRET_ARN = coalesce(var.internal_service_token_secret_arn, "")
      OCR_QUEUE_URL                     = aws_sqs_queue.ocr_jobs.id
    }
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-s3-event-to-ocr-queue" })
}

resource "aws_lambda_function" "ocr_queue_to_api" {
  function_name    = "${local.name_prefix}-ocr-queue-to-api"
  role             = aws_iam_role.ocr_queue_lambda.arn
  handler          = "ocr_queue_to_api.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.ocr_queue_to_api.output_path
  source_code_hash = data.archive_file.ocr_queue_to_api.output_base64sha256
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      API_INTERNAL_BASE_URL             = "http://${aws_lb.api.dns_name}"
      AWS_REGION                        = var.aws_region
      INTERNAL_SERVICE_TOKEN_SECRET_ARN = coalesce(var.internal_service_token_secret_arn, "")
    }
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-ocr-queue-to-api" })
}

resource "aws_lambda_permission" "allow_documents_bucket_to_invoke" {
  statement_id  = "AllowExecutionFromS3DocumentsBucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.s3_event_to_ocr_queue.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.documents.arn
}

resource "aws_s3_bucket_notification" "documents_created" {
  bucket = aws_s3_bucket.documents.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.s3_event_to_ocr_queue.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.allow_documents_bucket_to_invoke]
}

resource "aws_lambda_event_source_mapping" "ocr_queue_consumer" {
  event_source_arn = aws_sqs_queue.ocr_jobs.arn
  function_name    = aws_lambda_function.ocr_queue_to_api.arn
  batch_size       = 5
  enabled          = true
}
