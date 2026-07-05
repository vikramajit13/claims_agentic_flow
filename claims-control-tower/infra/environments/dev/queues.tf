resource "aws_sqs_queue" "ocr_dlq" {
  name                      = "${local.name_prefix}-ocr-dlq"
  message_retention_seconds = 1209600
  tags                      = merge(local.common_tags, { Name = "${local.name_prefix}-ocr-dlq" })
}

resource "aws_sqs_queue" "ocr_jobs" {
  name                       = "${local.name_prefix}-ocr-jobs"
  visibility_timeout_seconds = 180
  message_retention_seconds  = 345600
  receive_wait_time_seconds  = 10

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ocr_dlq.arn
    maxReceiveCount     = 5
  })

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-ocr-jobs" })
}
