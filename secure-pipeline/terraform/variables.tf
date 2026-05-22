variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name for tagging"
  type        = string
  default     = "secure-pipeline"
}

variable "kms_deletion_window_days" {
  description = "KMS key deletion window in days"
  type        = number
  default     = 10
}

variable "audit_logs_ttl_days" {
  description = "Days before audit logs expire"
  type        = number
  default     = 2555  # 7 years for compliance
}

variable "s3_logs_retention_days" {
  description = "Days to retain S3 server access logs"
  type        = number
  default     = 90
}

variable "enable_dynamodb_pitr" {
  description = "Enable DynamoDB point-in-time recovery"
  type        = bool
  default     = true
}

variable "enable_kms_rotation" {
  description = "Enable automatic KMS key rotation"
  type        = bool
  default     = true
}
