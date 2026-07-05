resource "aws_ecs_cluster" "this" {
  name = local.name_prefix
  tags = merge(local.common_tags, { Name = local.name_prefix })
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.name_prefix}-api"
  retention_in_days = 14
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "ocr_worker" {
  name              = "/ecs/${local.name_prefix}-ocr-worker"
  retention_in_days = 14
  tags              = local.common_tags
}

resource "aws_lb" "api" {
  name               = "${local.name_prefix}-alb"
  load_balancer_type = "application"
  subnets            = [for subnet in aws_subnet.public : subnet.id]
  security_groups    = [aws_security_group.alb.id]
  idle_timeout       = 60
  tags               = merge(local.common_tags, { Name = "${local.name_prefix}-alb" })
}

resource "aws_lb_target_group" "api" {
  name        = substr("${local.name_prefix}-api-tg", 0, 32)
  port        = var.api_container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.this.id

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
    matcher             = "200"
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-api-tg" })
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name_prefix}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.api_task_cpu)
  memory                   = tostring(var.api_task_memory)
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = var.api_container_name
      image     = var.api_bootstrap_image
      essential = true
      command   = var.api_bootstrap_command
      portMappings = [
        {
          containerPort = var.api_container_port
          hostPort      = var.api_container_port
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "PYTHONPATH"
          value = "/app"
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "S3_BUCKET_DEFAULT"
          value = aws_s3_bucket.documents.bucket
        },
        {
          name  = "OCR_QUEUE_URL"
          value = aws_sqs_queue.ocr_jobs.id
        }
      ]
      secrets = concat(
        var.database_url_secret_arn == null ? [] : [
          {
            name      = "DATABASE_URL"
            valueFrom = var.database_url_secret_arn
          }
        ],
        var.langsmith_api_key_secret_arn == null ? [] : [
          {
            name      = "LANGSMITH_API_KEY"
            valueFrom = var.langsmith_api_key_secret_arn
          }
        ]
      )
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.api.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-api" })
}

resource "aws_ecs_task_definition" "ocr_worker" {
  family                   = "${local.name_prefix}-ocr-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.ocr_task_cpu)
  memory                   = tostring(var.ocr_task_memory)
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = var.ocr_container_name
      image     = var.ocr_bootstrap_image
      essential = true
      command   = var.ocr_bootstrap_command
      environment = [
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "OCR_QUEUE_URL"
          value = aws_sqs_queue.ocr_jobs.id
        },
        {
          name  = "S3_BUCKET_DEFAULT"
          value = aws_s3_bucket.documents.bucket
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ocr_worker.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-ocr-worker" })
}

resource "aws_ecs_service" "api" {
  name            = "${local.name_prefix}-api"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 60

  network_configuration {
    subnets          = [for subnet in aws_subnet.public : subnet.id]
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = var.api_container_name
    container_port   = var.api_container_port
  }

  depends_on = [aws_lb_listener.http]
  tags       = merge(local.common_tags, { Name = "${local.name_prefix}-api" })
}

resource "aws_ecs_service" "ocr_worker" {
  name            = "${local.name_prefix}-ocr-worker"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.ocr_worker.arn
  desired_count   = var.ocr_worker_desired_count
  launch_type     = "FARGATE"

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  network_configuration {
    subnets          = [for subnet in aws_subnet.public : subnet.id]
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-ocr-worker" })
}
