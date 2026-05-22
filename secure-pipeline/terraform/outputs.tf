output "kms_key_id" {
  description = "KMS key ID for encryption"
  value       = aws_kms_key.secure_pipeline.id
}

output "kms_key_arn" {
  description = "KMS key ARN for encryption"
  value       = aws_kms_key.secure_pipeline.arn
}

output "uploads_bucket_name" {
  description = "Name of the document uploads S3 bucket"
  value       = aws_s3_bucket.document_uploads.id
}

output "uploads_bucket_arn" {
  description = "ARN of the document uploads S3 bucket"
  value       = aws_s3_bucket.document_uploads.arn
}

output "processed_storage_bucket_name" {
  description = "Name of the processed documents S3 bucket"
  value       = aws_s3_bucket.processed_storage.id
}

output "processed_storage_bucket_arn" {
  description = "ARN of the processed documents S3 bucket"
  value       = aws_s3_bucket.processed_storage.arn
}

output "logs_bucket_name" {
  description = "Name of the server access logs S3 bucket"
  value       = aws_s3_bucket.logs.id
}

output "logs_bucket_arn" {
  description = "ARN of the server access logs S3 bucket"
  value       = aws_s3_bucket.logs.arn
}

output "dynamodb_table_name" {
  description = "Name of the audit logs DynamoDB table"
  value       = aws_dynamodb_table.audit_logs.name
}

output "dynamodb_table_arn" {
  description = "ARN of the audit logs DynamoDB table"
  value       = aws_dynamodb_table.audit_logs.arn
}

output "sns_topic_arn" {
  description = "ARN of the SNS notification topic"
  value       = aws_sns_topic.pipeline_notifications.arn
}

output "sns_topic_name" {
  description = "Name of the SNS notification topic"
  value       = aws_sns_topic.pipeline_notifications.name
}

output "aws_account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "AWS Region"
  value       = "eu-west-2"
}
