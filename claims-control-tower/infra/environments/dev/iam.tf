data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "execution_secrets" {
  dynamic "statement" {
    for_each = length(local.secret_arns) == 0 ? [] : [1]
    content {
      effect = "Allow"
      actions = [
        "secretsmanager:GetSecretValue"
      ]
      resources = local.secret_arns
    }
  }
}

data "aws_iam_policy_document" "task_access" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.documents.arn,
      "${aws_s3_bucket.documents.arn}/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "sqs:ChangeMessageVisibility",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ReceiveMessage",
      "sqs:SendMessage"
    ]
    resources = [
      aws_sqs_queue.ocr_jobs.arn,
      aws_sqs_queue.ocr_dlq.arn
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "textract:DetectDocumentText",
      "bedrock:Converse",
      "bedrock:InvokeModel"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role" "ecs_execution" {
  name               = "${local.name_prefix}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  count  = length(local.secret_arns) == 0 ? 0 : 1
  name   = "${local.name_prefix}-ecs-execution-secrets"
  role   = aws_iam_role.ecs_execution.id
  policy = data.aws_iam_policy_document.execution_secrets.json
}

resource "aws_iam_role" "ecs_task" {
  name               = "${local.name_prefix}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy" "ecs_task_access" {
  name   = "${local.name_prefix}-ecs-task-access"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.task_access.json
}

data "aws_iam_policy_document" "s3_event_lambda_access" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:${var.aws_region}:${var.aws_account_id}:*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject"
    ]
    resources = ["${aws_s3_bucket.documents.arn}/*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "sqs:SendMessage"
    ]
    resources = [aws_sqs_queue.ocr_jobs.arn]
  }

  dynamic "statement" {
    for_each = var.internal_service_token_secret_arn == null ? [] : [1]
    content {
      effect = "Allow"
      actions = [
        "secretsmanager:GetSecretValue"
      ]
      resources = [var.internal_service_token_secret_arn]
    }
  }
}

data "aws_iam_policy_document" "ocr_queue_lambda_access" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:${var.aws_region}:${var.aws_account_id}:*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "sqs:ChangeMessageVisibility",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ReceiveMessage"
    ]
    resources = [aws_sqs_queue.ocr_jobs.arn]
  }

  dynamic "statement" {
    for_each = var.internal_service_token_secret_arn == null ? [] : [1]
    content {
      effect = "Allow"
      actions = [
        "secretsmanager:GetSecretValue"
      ]
      resources = [var.internal_service_token_secret_arn]
    }
  }
}

resource "aws_iam_role" "s3_event_lambda" {
  name               = "${local.name_prefix}-s3-event-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy" "s3_event_lambda_access" {
  name   = "${local.name_prefix}-s3-event-lambda-access"
  role   = aws_iam_role.s3_event_lambda.id
  policy = data.aws_iam_policy_document.s3_event_lambda_access.json
}

resource "aws_iam_role" "ocr_queue_lambda" {
  name               = "${local.name_prefix}-ocr-queue-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy" "ocr_queue_lambda_access" {
  name   = "${local.name_prefix}-ocr-queue-lambda-access"
  role   = aws_iam_role.ocr_queue_lambda.id
  policy = data.aws_iam_policy_document.ocr_queue_lambda_access.json
}
