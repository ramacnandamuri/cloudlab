# Secure Financial Document Processing Lambda Functions

This directory contains two Lambda functions that form the core of the secure document processing pipeline.

## Functions Overview

### 1. Upload Handler (`upload_handler.py`)

**Trigger:** API Gateway POST `/upload`

**Purpose:** Receives file uploads, validates them, stores in S3, and creates audit logs.

**Request Format:**
```json
{
  "filename": "document.pdf",
  "file_data": "base64_encoded_file_content"
}
```

**Response Format (Success - 200):**
```json
{
  "message": "File uploaded successfully",
  "data": {
    "document_id": "20260522120000_document.pdf",
    "filename": "document.pdf",
    "file_size": 1024,
    "status_url": "https://s3.amazonaws.com/...",
    "status_check_expires_in_seconds": 3600
  }
}
```

**Environment Variables:**
- `UPLOAD_BUCKET`: S3 bucket for storing uploaded files
- `AUDIT_TABLE`: DynamoDB table for audit logs
- `KMS_KEY_ARN`: ARN of KMS key for encryption

**Features:**
- ✅ Base64 file decoding
- ✅ File type validation (PDF, CSV, XLSX only)
- ✅ File size validation (max 10MB)
- ✅ KMS encryption on S3 upload
- ✅ Comprehensive audit logging to DynamoDB
- ✅ Presigned URL generation for status checking
- ✅ Detailed error responses with validation feedback

**Error Responses:**
- `400`: Invalid file type, empty file, or base64 decode error
- `403`: Access denied to required resources
- `500`: Server/AWS service errors

---

### 2. Process Handler (`process_handler.py`)

**Trigger:** S3 event from upload bucket

**Purpose:** Processes uploaded files, applies encryption, updates audit logs, and sends notifications.

**Event Format (S3 Event):**
```json
{
  "Records": [
    {
      "s3": {
        "bucket": {
          "name": "upload-bucket"
        },
        "object": {
          "key": "uploads/document.pdf"
        }
      }
    }
  ]
}
```

**Response Format:**
```json
{
  "statusCode": 200,
  "body": {
    "message": "File processed successfully",
    "document_id": "20260522120000_document.pdf",
    "destination": "s3://processed-bucket/processed/20260522120000_document.pdf"
  }
}
```

**Environment Variables:**
- `PROCESSED_BUCKET`: S3 bucket for storing processed files
- `AUDIT_TABLE`: DynamoDB table for audit logs
- `SNS_TOPIC_ARN`: SNS topic for notifications
- `KMS_KEY_ARN`: ARN of KMS key for encryption

**Features:**
- ✅ S3 event parsing
- ✅ File size validation (non-empty check)
- ✅ Secure file copy with KMS encryption
- ✅ Metadata preservation during copy
- ✅ DynamoDB audit log updates
- ✅ SNS notifications with processing details
- ✅ Graceful error handling with fallbacks

**Workflow:**
1. Receives S3 event when file lands in upload bucket
2. Validates file is not empty
3. Copies file to processed bucket with KMS encryption
4. Updates DynamoDB audit log with "processed" status
5. Sends SNS notification
6. Logs any errors without blocking the process

---

## Deployment

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt
```

### Package for Lambda

```bash
# For upload_handler
zip -j upload_handler.zip upload_handler.py
cd .. && zip -u lambda/upload_handler.zip python/* && cd lambda

# For process_handler
zip -j process_handler.zip process_handler.py
cd .. && zip -u lambda/process_handler.zip python/* && cd lambda
```

### AWS Lambda Configuration

#### Upload Handler
- **Runtime:** Python 3.11
- **Handler:** `upload_handler.lambda_handler`
- **Memory:** 256 MB
- **Timeout:** 30 seconds
- **Layers:** (if using Lambda Layers for dependencies)

#### Process Handler
- **Runtime:** Python 3.11
- **Handler:** `process_handler.lambda_handler`
- **Memory:** 512 MB
- **Timeout:** 60 seconds
- **Layers:** (if using Lambda Layers for dependencies)

### IAM Permissions Required

**Upload Handler:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::UPLOAD_BUCKET/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:GenerateDataKey"
      ],
      "Resource": "KMS_KEY_ARN"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem"
      ],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/AUDIT_TABLE"
    }
  ]
}
```

**Process Handler:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:HeadObject"],
      "Resource": "arn:aws:s3:::UPLOAD_BUCKET/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::PROCESSED_BUCKET/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:GenerateDataKey"
      ],
      "Resource": "KMS_KEY_ARN"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/AUDIT_TABLE"
    },
    {
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": "SNS_TOPIC_ARN"
    }
  ]
}
```

---

## Security Considerations

### Encryption
- All files are encrypted at rest using AWS KMS
- Presigned URLs expire after 1 hour
- S3 bucket policies should enforce encryption

### Access Control
- Upload bucket should be private with no public access
- Processed bucket should be private
- DynamoDB table should use proper IAM restrictions
- SNS topic should be restricted to authorized subscribers

### Audit Trail
- All uploads are logged in DynamoDB with:
  - Document ID
  - Filename
  - File size
  - Upload timestamp
  - Processing status
  - Any error messages

### Input Validation
- File type whitelist: PDF, CSV, XLSX only
- File size limit: 10 MB
- File cannot be empty
- Filename is required
- Base64 decoding validation

---

## Testing

### Test Upload Handler Locally
```python
import json
import base64
from upload_handler import lambda_handler

# Create test file
test_data = b"Test PDF content"
encoded = base64.b64encode(test_data).decode()

event = {
    "body": json.dumps({
        "filename": "test.pdf",
        "file_data": encoded
    })
}

context = None
result = lambda_handler(event, context)
print(json.dumps(result, indent=2))
```

### Test Process Handler Locally
```python
from process_handler import lambda_handler

event = {
    "Records": [
        {
            "s3": {
                "bucket": {"name": "upload-bucket"},
                "object": {"key": "uploads/test_document.pdf"}
            }
        }
    ]
}

context = None
result = lambda_handler(event, context)
print(json.dumps(result, indent=2))
```

---

## Logging

Both functions use Python's `logging` module with INFO level logging. Logs are automatically sent to CloudWatch where they can be monitored, searched, and analyzed.

**Common log entries:**
- File validation status
- S3 operations (upload/copy)
- DynamoDB operations
- SNS notifications
- Error details with exception info

---

## Error Handling

### Upload Handler
- Validates input before processing
- Returns specific error messages for debugging
- Logs all errors to CloudWatch
- Handles boto3 client errors gracefully

### Process Handler
- Continues processing even if audit log update fails
- Continues processing even if SNS notification fails
- Logs all errors with full context
- Updates audit log with error status when possible

---

## Monitoring

### CloudWatch Metrics to Track
- Lambda invocations
- Lambda errors
- Lambda duration
- S3 upload/copy operations
- DynamoDB write capacity usage
- SNS publish operations

### Recommended Alarms
- Upload Handler error rate > 5%
- Process Handler error rate > 5%
- Lambda duration > 25 seconds (upload) or 50 seconds (process)
- SNS publish failures

---

## Future Enhancements

- Add document scanning/virus detection
- Implement OCR for document analysis
- Add retry logic for transient failures
- Support for additional file types
- Progress tracking for large files
- Integration with AWS Step Functions for complex workflows
