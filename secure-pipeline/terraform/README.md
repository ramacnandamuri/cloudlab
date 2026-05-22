# Secure Financial Document Processing Pipeline

Production-grade Terraform configuration for a secure document processing pipeline on AWS eu-west-2.

## Overview

This infrastructure implements a secure, compliant financial document processing system with:

- **Encryption**: KMS-managed encryption for all data at rest
- **Access Control**: Block public access, secure transport enforcement
- **Audit Trail**: DynamoDB audit logs with point-in-time recovery
- **Notifications**: Encrypted SNS topic for pipeline events
- **Compliance**: Server access logging, versioning, automatic expiration policies

## Architecture

```
Document Upload Flow:
┌─────────────────┐
│  Uploads S3     │ ──→ KMS Encrypted
│  Bucket         │ ──→ Versioned
│  (Public Block) │ ──→ Logged
└─────────────────┘
         ↓
   [Processing Logic]
         ↓
┌──────────────────────┐     ┌─────────────────┐
│ Processed Storage S3 │────→│ DynamoDB Audit  │
│ Bucket               │     │ Logs Table      │
│ (Public Block)       │     │ (TTL + PITR)    │
└──────────────────────┘     └─────────────────┘
         ↓
    ┌────────────┐
    │ SNS Topic  │
    │ (Encrypted)│
    └────────────┘
```

## Resources Created

### S3 Buckets (3 total)
- **document-uploads**: Ingestion point for raw documents
- **processed-storage**: Final destination for processed documents
- **logs**: Server access logs from both buckets

Each bucket includes:
- Block public access policies
- KMS encryption (with bucket key optimization)
- Versioning enabled
- Server access logging
- Policy enforcement for HTTPS only

### Encryption
- **KMS Key**: Customer-managed key with automatic rotation
- Encryption applied to: S3 buckets, DynamoDB table, SNS topic

### DynamoDB
- **audit-logs** table with:
  - Partition key: `document_id` (String)
  - GSI on `timestamp` for time-based queries
  - KMS encryption enabled
  - Point-in-time recovery enabled
  - TTL-based expiration (7 years default)

### Notifications
- **SNS Topic** with:
  - KMS encryption
  - Secure transport (HTTPS) only policy
  - Permissions for S3 event notifications

### Tagging
All resources tagged with:
- `Environment: production`
- `Project: secure-pipeline`

## Prerequisites

- Terraform >= 1.0
- AWS CLI configured with appropriate credentials
- Permissions for: IAM, S3, KMS, DynamoDB, SNS

## Deployment

### 1. Initialize Terraform
```bash
terraform init
```

### 2. Plan Changes
```bash
terraform plan -out=tfplan
```

### 3. Apply Configuration
```bash
terraform apply tfplan
```

### 4. Verify Deployment
```bash
terraform output
```

## Important Variables

See `variables.tf` for all configurable options:

- `aws_region`: Default "eu-west-2"
- `environment`: Default "production"
- `project_name`: Default "secure-pipeline"
- `kms_deletion_window_days`: KMS deletion grace period (default: 10)
- `audit_logs_ttl_days`: Document retention period (default: 2555 = 7 years)
- `s3_logs_retention_days`: Server log retention (default: 90)

## Compliance & Security Features

✓ **Encryption**: All data encrypted with KMS (customer-managed keys)
✓ **Access Control**: Public access blocked at bucket level
✓ **Transport Security**: HTTPS/TLS enforcement via bucket policies
✓ **Audit Logging**: Server access logs + DynamoDB audit trail
✓ **Data Retention**: TTL on audit logs, expiration on server logs
✓ **Disaster Recovery**: Versioning enabled, PITR for DynamoDB
✓ **Key Rotation**: Automatic KMS key rotation enabled
✓ **Monitoring**: SNS notifications for pipeline events

## Outputs

After deployment, retrieve resource details:

```bash
# All outputs
terraform output

# Specific output
terraform output uploads_bucket_name
terraform output dynamodb_table_arn
terraform output sns_topic_arn
```

## Cost Considerations

- **DynamoDB**: On-demand pricing (no reserved capacity)
- **S3**: Standard storage + access logging costs
- **KMS**: Key storage + request costs (high volume)
- **SNS**: Per-message costs for notifications

## Maintenance

### Key Rotation
KMS automatic key rotation is enabled. No action required.

### Audit Log Retention
Modify `audit_logs_ttl_days` variable to adjust retention period.

### Server Log Cleanup
S3 logs expire automatically after 90 days (configurable).

## Destruction

To remove all resources:

```bash
terraform destroy
```

**WARNING**: This will delete all data including versioned objects. Ensure backups exist before destroying.

## Security Best Practices

1. **Encrypt SNS subscriptions** with TLS
2. **Rotate KMS key regularly** (automatic)
3. **Review DynamoDB audit logs** periodically
4. **Enable CloudTrail** for API logging
5. **Use IAM policies** to restrict access by role
6. **Monitor S3 bucket access** via CloudWatch
7. **Enable MFA Delete** on S3 for additional protection

## Troubleshooting

### KMS Key Not Found
Verify KMS key exists and IAM user has `kms:DescribeKey` permission.

### S3 Upload Fails
Check bucket policy allows your IAM user and uses KMS encryption.

### DynamoDB PITR Not Working
Ensure `enable_dynamodb_pitr = true` in terraform.tfvars.

## Support

For issues or questions, contact the DevOps team or check AWS documentation:
- [S3 Security Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security.html)
- [KMS Best Practices](https://docs.aws.amazon.com/kms/latest/developerguide/best-practices.html)
- [DynamoDB Encryption](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/encryption.html)
