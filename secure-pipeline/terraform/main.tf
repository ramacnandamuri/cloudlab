terraform {
  required_version = ">= 1.0"
  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "eu-west-2"

  default_tags {
    tags = {
      Environment = "production"
      Project     = "secure-pipeline"
    }
  }
}

locals {
  environment = "production"
  project     = "secure-pipeline"
  region      = "eu-west-2"

  common_tags = {
    Environment = local.environment
    Project     = local.project
  }
}

# KMS Key
resource "aws_kms_key" "secure_pipeline" {
  description             = "KMS key for secure financial document processing pipeline"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = merge(local.common_tags, { Name = "secure-pipeline-key" })
}

resource "aws_kms_alias" "secure_pipeline" {
  name          = "alias/secure-pipeline"
  target_key_id = aws_kms_key.secure_pipeline.key_id
}

# Upload S3 Bucket
resource "aws_s3_bucket" "document_uploads" {
  bucket        = "secure-pipeline-uploads-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
  tags          = merge(local.common_tags, { Name = "secure-pipeline-uploads" })
}

resource "aws_s3_bucket_versioning" "document_uploads" {
  bucket = aws_s3_bucket.document_uploads.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "document_uploads" {
  bucket                  = aws_s3_bucket.document_uploads.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "document_uploads" {
  bucket = aws_s3_bucket.document_uploads.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.secure_pipeline.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_logging" "document_uploads" {
  bucket        = aws_s3_bucket.document_uploads.id
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "uploads/"
}

resource "aws_s3_bucket_policy" "document_uploads" {
  bucket = aws_s3_bucket.document_uploads.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyUnencryptedObjectUploads"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.document_uploads.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      },
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [aws_s3_bucket.document_uploads.arn, "${aws_s3_bucket.document_uploads.arn}/*"]
        Condition = {
          Bool = { "aws:SecureTransport" = "false" }
        }
      }
    ]
  })
}

# Processed Storage S3 Bucket
resource "aws_s3_bucket" "processed_storage" {
  bucket        = "secure-pipeline-processed-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
  tags          = merge(local.common_tags, { Name = "secure-pipeline-processed" })
}

resource "aws_s3_bucket_versioning" "processed_storage" {
  bucket = aws_s3_bucket.processed_storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "processed_storage" {
  bucket                  = aws_s3_bucket.processed_storage.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "processed_storage" {
  bucket = aws_s3_bucket.processed_storage.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.secure_pipeline.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_logging" "processed_storage" {
  bucket        = aws_s3_bucket.processed_storage.id
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "processed/"
}

resource "aws_s3_bucket_policy" "processed_storage" {
  bucket = aws_s3_bucket.processed_storage.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyUnencryptedObjectUploads"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.processed_storage.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      },
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [aws_s3_bucket.processed_storage.arn, "${aws_s3_bucket.processed_storage.arn}/*"]
        Condition = {
          Bool = { "aws:SecureTransport" = "false" }
        }
      }
    ]
  })
}

# Logs S3 Bucket — FIX: added force_destroy
resource "aws_s3_bucket" "logs" {
  bucket        = "secure-pipeline-logs-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
  tags          = merge(local.common_tags, { Name = "secure-pipeline-logs" })
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket                  = aws_s3_bucket.logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    id     = "delete-old-logs"
    status = "Enabled"
    filter {}
    expiration {
      days = 2555
    }
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# DynamoDB Audit Logs Table
resource "aws_dynamodb_table" "audit_logs" {
  name         = "secure-pipeline-audit-logs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "document_id"

  attribute {
    name = "document_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  global_secondary_index {
    name            = "TimestampIndex"
    hash_key        = "timestamp"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.secure_pipeline.arn
  }

  point_in_time_recovery {
    enabled = true
  }

  ttl {
    attribute_name = "expiration_time"
    enabled        = true
  }

  tags = merge(local.common_tags, { Name = "secure-pipeline-audit-logs" })
}

# SNS Topic
resource "aws_sns_topic" "pipeline_notifications" {
  name              = "secure-pipeline-notifications"
  kms_master_key_id = aws_kms_key.secure_pipeline.id
  tags              = merge(local.common_tags, { Name = "secure-pipeline-notifications" })
}

resource "aws_sns_topic_policy" "pipeline_notifications" {
  arn = aws_sns_topic.pipeline_notifications.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowLambdaPublish"
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action    = "SNS:Publish"
        Resource  = aws_sns_topic.pipeline_notifications.arn
      },
      {
        Sid       = "AllowS3Publish"
        Effect    = "Allow"
        Principal = { Service = "s3.amazonaws.com" }
        Action    = "SNS:Publish"
        Resource  = aws_sns_topic.pipeline_notifications.arn
      }
    ]
  })
}

# Data Sources
data "aws_caller_identity" "current" {}

# Lambda Zip Packages
data "archive_file" "upload_handler" {
  type        = "zip"
  source_file = "${path.module}/../lambda/upload_handler.py"
  output_path = "${path.module}/../lambda/upload_handler.zip"
}

data "archive_file" "process_handler" {
  type        = "zip"
  source_file = "${path.module}/../lambda/process_handler.py"
  output_path = "${path.module}/../lambda/process_handler.zip"
}

# IAM Role — Upload Handler
resource "aws_iam_role" "upload_handler" {
  name = "secure-pipeline-upload-handler-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "upload_handler" {
  name = "secure-pipeline-upload-handler-policy"
  role = aws_iam_role.upload_handler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "S3Upload"
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${aws_s3_bucket.document_uploads.arn}/*"
      },
      {
        Sid      = "S3PresignedUrl"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.document_uploads.arn}/*"
      },
      {
        Sid      = "KMS"
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
        Resource = aws_kms_key.secure_pipeline.arn
      },
      {
        Sid      = "DynamoDB"
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem"]
        Resource = aws_dynamodb_table.audit_logs.arn
      },
      {
        Sid      = "Logs"
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# IAM Role — Process Handler
resource "aws_iam_role" "process_handler" {
  name = "secure-pipeline-process-handler-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "process_handler" {
  name = "secure-pipeline-process-handler-policy"
  role = aws_iam_role.process_handler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "S3Read"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:HeadObject"]
        Resource = "${aws_s3_bucket.document_uploads.arn}/*"
      },
      {
        Sid      = "S3Write"
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${aws_s3_bucket.processed_storage.arn}/*"
      },
      {
        Sid      = "KMS"
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
        Resource = aws_kms_key.secure_pipeline.arn
      },
      {
        Sid      = "DynamoDB"
        Effect   = "Allow"
        Action   = ["dynamodb:UpdateItem"]
        Resource = aws_dynamodb_table.audit_logs.arn
      },
      {
        Sid      = "SNS"
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = aws_sns_topic.pipeline_notifications.arn
      },
      {
        Sid      = "Logs"
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Lambda Functions
resource "aws_lambda_function" "upload_handler" {
  filename         = data.archive_file.upload_handler.output_path
  function_name    = "secure-pipeline-upload-handler"
  role             = aws_iam_role.upload_handler.arn
  handler          = "upload_handler.lambda_handler"
  runtime          = "python3.12"
  memory_size      = 256
  timeout          = 30
  architectures    = ["arm64"]
  source_code_hash = data.archive_file.upload_handler.output_base64sha256

  environment {
    variables = {
      UPLOAD_BUCKET = aws_s3_bucket.document_uploads.id
      AUDIT_TABLE   = aws_dynamodb_table.audit_logs.name
      KMS_KEY_ARN   = aws_kms_key.secure_pipeline.arn
    }
  }

  tags = { Name = "secure-pipeline-upload-handler" }
}

resource "aws_lambda_function" "process_handler" {
  filename         = data.archive_file.process_handler.output_path
  function_name    = "secure-pipeline-process-handler"
  role             = aws_iam_role.process_handler.arn
  handler          = "process_handler.lambda_handler"
  runtime          = "python3.12"
  memory_size      = 512
  timeout          = 60
  architectures    = ["arm64"]
  source_code_hash = data.archive_file.process_handler.output_base64sha256

  environment {
    variables = {
      PROCESSED_BUCKET = aws_s3_bucket.processed_storage.id
      AUDIT_TABLE      = aws_dynamodb_table.audit_logs.name
      SNS_TOPIC_ARN    = aws_sns_topic.pipeline_notifications.arn
      KMS_KEY_ARN      = aws_kms_key.secure_pipeline.arn
    }
  }

  tags = { Name = "secure-pipeline-process-handler" }
}

# S3 Event Notification
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.process_handler.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.document_uploads.arn
}

resource "aws_s3_bucket_notification" "upload_trigger" {
  bucket = aws_s3_bucket.document_uploads.id
  lambda_function {
    lambda_function_arn = aws_lambda_function.process_handler.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
  }
  depends_on = [aws_lambda_permission.allow_s3]
}

# API Gateway
resource "aws_apigatewayv2_api" "upload_api" {
  name          = "secure-pipeline-upload-api"
  protocol_type = "HTTP"
  tags          = { Name = "secure-pipeline-api" }
}

resource "aws_apigatewayv2_integration" "upload_handler" {
  api_id                 = aws_apigatewayv2_api.upload_api.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  payload_format_version = "2.0"
  integration_uri        = aws_lambda_function.upload_handler.invoke_arn
}

resource "aws_apigatewayv2_route" "upload" {
  api_id    = aws_apigatewayv2_api.upload_api.id
  route_key = "POST /upload"
  target    = "integrations/${aws_apigatewayv2_integration.upload_handler.id}"
}

resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.upload_api.id
  name        = "prod"
  auto_deploy = true
  tags        = { Name = "secure-pipeline-prod" }
}

resource "aws_lambda_permission" "allow_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.upload_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.upload_api.execution_arn}/*/*"
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "upload_errors" {
  alarm_name          = "secure-pipeline-upload-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Alert when upload handler has 5+ errors in 5 minutes"
  alarm_actions       = [aws_sns_topic.pipeline_notifications.arn]
  dimensions = {
    FunctionName = aws_lambda_function.upload_handler.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "process_errors" {
  alarm_name          = "secure-pipeline-process-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Alert when process handler has 5+ errors in 5 minutes"
  alarm_actions       = [aws_sns_topic.pipeline_notifications.arn]
  dimensions = {
    FunctionName = aws_lambda_function.process_handler.function_name
  }
}

# Outputs
output "upload_api_endpoint" {
  description = "API endpoint for file uploads"
  value       = "${aws_apigatewayv2_stage.prod.invoke_url}/upload"
}

output "upload_handler_name" {
  description = "Upload Lambda function name"
  value       = aws_lambda_function.upload_handler.function_name
}

output "process_handler_name" {
  description = "Process Lambda function name"
  value       = aws_lambda_function.process_handler.function_name
}

output "aws_account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  value = "eu-west-2"
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.audit_logs.name
}

output "dynamodb_table_arn" {
  value = aws_dynamodb_table.audit_logs.arn
}

output "kms_key_id" {
  value = aws_kms_key.secure_pipeline.key_id
}

output "kms_key_arn" {
  value = aws_kms_key.secure_pipeline.arn
}

output "sns_topic_arn" {
  value = aws_sns_topic.pipeline_notifications.arn
}

output "sns_topic_name" {
  value = aws_sns_topic.pipeline_notifications.name
}

output "uploads_bucket_name" {
  value = aws_s3_bucket.document_uploads.id
}

output "uploads_bucket_arn" {
  value = aws_s3_bucket.document_uploads.arn
}

output "processed_storage_bucket_name" {
  value = aws_s3_bucket.processed_storage.id
}

output "processed_storage_bucket_arn" {
  value = aws_s3_bucket.processed_storage.arn
}

output "logs_bucket_name" {
  value = aws_s3_bucket.logs.id
}

output "logs_bucket_arn" {
  value = aws_s3_bucket.logs.arn
}