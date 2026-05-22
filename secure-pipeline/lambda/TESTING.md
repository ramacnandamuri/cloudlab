# API Testing Guide

This guide provides examples and tools for testing the secure pipeline Lambda functions.

## Prerequisites

- `curl` command-line tool
- `jq` for JSON processing (optional but recommended)
- Files to upload (PDF, CSV, or XLSX)
- API Gateway endpoint URL

## Upload Handler Testing

### 1. Prepare Test File

Create a test PDF file or use an existing one:

```bash
# Create a simple test PDF (requires ghostscript)
echo "Test Document" > test.txt

# Or encode an existing file
FILE_PATH="./document.pdf"
ENCODED_FILE=$(base64 -i "$FILE_PATH" | tr -d '\n')
```

### 2. Upload via curl

#### Basic Upload (without jq)

```bash
API_ENDPOINT="https://your-api-id.execute-api.region.amazonaws.com/prod"
FILE_PATH="./document.pdf"

# Encode the file
ENCODED_FILE=$(base64 -i "$FILE_PATH" | tr -d '\n')

# Upload
curl -X POST "${API_ENDPOINT}/upload" \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"$(basename $FILE_PATH)\",
    \"file_data\": \"$ENCODED_FILE\"
  }"
```

#### Upload with Pretty JSON Output (with jq)

```bash
API_ENDPOINT="https://your-api-id.execute-api.region.amazonaws.com/prod"
FILE_PATH="./document.pdf"

ENCODED_FILE=$(base64 -i "$FILE_PATH" | tr -d '\n')

curl -X POST "${API_ENDPOINT}/upload" \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"$(basename $FILE_PATH)\",
    \"file_data\": \"$ENCODED_FILE\"
  }" | jq '.'
```

#### Upload Script Helper

Save this as `upload_test.sh`:

```bash
#!/bin/bash

if [ $# -ne 2 ]; then
    echo "Usage: $0 <api-endpoint> <file-path>"
    echo "Example: $0 https://abc123.execute-api.us-east-1.amazonaws.com/prod ./document.pdf"
    exit 1
fi

API_ENDPOINT="$1"
FILE_PATH="$2"

if [ ! -f "$FILE_PATH" ]; then
    echo "Error: File not found: $FILE_PATH"
    exit 1
fi

echo "Uploading file: $FILE_PATH"
echo "API Endpoint: $API_ENDPOINT"
echo ""

FILENAME=$(basename "$FILE_PATH")
ENCODED_FILE=$(base64 -i "$FILE_PATH" | tr -d '\n')

RESPONSE=$(curl -s -X POST "${API_ENDPOINT}/upload" \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"$FILENAME\",
    \"file_data\": \"$ENCODED_FILE\"
  }")

if command -v jq &> /dev/null; then
    echo "$RESPONSE" | jq '.'
else
    echo "$RESPONSE"
fi

# Extract document_id if successful
DOC_ID=$(echo "$RESPONSE" | grep -o '"document_id":"[^"]*' | cut -d'"' -f4)
if [ -n "$DOC_ID" ]; then
    echo ""
    echo "Document ID: $DOC_ID"
fi
```

Usage:
```bash
chmod +x upload_test.sh
./upload_test.sh https://your-api-id.execute-api.region.amazonaws.com/prod document.pdf
```

### 3. Test File Type Validation

#### Test with Valid File Types

```bash
# Test PDF
./upload_test.sh $API_ENDPOINT ./document.pdf

# Test CSV
./upload_test.sh $API_ENDPOINT ./data.csv

# Test XLSX
./upload_test.sh $API_ENDPOINT ./spreadsheet.xlsx
```

#### Test with Invalid File Types

```bash
# Create a test .docx file
echo "test" > document.docx
ENCODED_FILE=$(base64 -i document.docx | tr -d '\n')

curl -X POST "${API_ENDPOINT}/upload" \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"document.docx\",
    \"file_data\": \"$ENCODED_FILE\"
  }" | jq '.'

# Expected response (400 error):
# {
#   "message": "Invalid file type: docx. Allowed types: pdf, csv, xlsx",
#   "data": {}
# }
```

### 4. Test File Size Validation

#### Test with Large File (should fail)

```bash
# Create a file larger than 10MB
dd if=/dev/zero bs=1M count=11 of=large_file.pdf

ENCODED_FILE=$(base64 -i large_file.pdf | tr -d '\n')

curl -X POST "${API_ENDPOINT}/upload" \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"large_file.pdf\",
    \"file_data\": \"$ENCODED_FILE\"
  }" | jq '.'

# Expected response (400 error):
# {
#   "message": "File size ... exceeds maximum ...",
#   "data": {}
# }
```

#### Test with Maximum Allowed Size (should pass)

```bash
# Create a file at exactly 10MB
dd if=/dev/zero bs=1M count=10 of=max_size.pdf

ENCODED_FILE=$(base64 -i max_size.pdf | tr -d '\n')

curl -X POST "${API_ENDPOINT}/upload" \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"max_size.pdf\",
    \"file_data\": \"$ENCODED_FILE\"
  }" | jq '.'
```

### 5. Test Edge Cases

#### Missing Filename

```bash
ENCODED_FILE=$(base64 -i document.pdf | tr -d '\n')

curl -X POST "${API_ENDPOINT}/upload" \
  -H "Content-Type: application/json" \
  -d "{
    \"file_data\": \"$ENCODED_FILE\"
  }" | jq '.'

# Expected: 400 Bad Request - "Filename is required"
```

#### Missing File Data

```bash
curl -X POST "${API_ENDPOINT}/upload" \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"document.pdf\"
  }" | jq '.'

# Expected: 400 Bad Request - "File data is required"
```

#### Invalid Base64

```bash
curl -X POST "${API_ENDPOINT}/upload" \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"document.pdf\",
    \"file_data\": \"not-valid-base64-!!!\"
  }" | jq '.'

# Expected: 400 Bad Request - "Failed to decode base64 data"
```

### 6. Check Upload Status

Use the presigned URL returned from successful upload:

```bash
# Extract from response
RESPONSE=$(curl -s -X POST "${API_ENDPOINT}/upload" ...)
STATUS_URL=$(echo "$RESPONSE" | jq -r '.data.status_url')

# Check file exists
curl -I "$STATUS_URL"

# Download file (if needed)
curl -o downloaded_file.pdf "$STATUS_URL"
```

## Process Handler Testing (CloudWatch Logs)

The process handler is triggered automatically by S3 events. To verify it's working:

### 1. Check CloudWatch Logs

```bash
# List log streams
aws logs describe-log-streams \
  --log-group-name /aws/lambda/secure-pipeline-process-handler \
  --query 'logStreams[*].[logStreamName,lastEventTimestamp]'

# View latest logs
aws logs tail /aws/lambda/secure-pipeline-process-handler --follow

# View logs for specific time
aws logs filter-log-events \
  --log-group-name /aws/lambda/secure-pipeline-process-handler \
  --start-time $(date -d '5 minutes ago' +%s)000
```

### 2. Verify DynamoDB Updates

```bash
# Check audit log entries
aws dynamodb scan \
  --table-name secure-pipeline-audit-log \
  --filter-expression "attribute_exists(#status)" \
  --expression-attribute-names '{"#status":"status"}' \
  --scan-index-forward false \
  --limit 10

# View specific document status
aws dynamodb get-item \
  --table-name secure-pipeline-audit-log \
  --key '{"document_id":{"S":"20260522120000_document.pdf"},"timestamp":{"S":"2026-05-22T12:00:00.000000"}}'
```

### 3. Check SNS Notifications

```bash
# List subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:region:account:secure-pipeline-processing-notifications

# Check published messages (if subscribed to email/SQS)
# Messages should contain document_id and processing status
```

### 4. Verify S3 Copy Operation

```bash
# List files in processed bucket
aws s3 ls s3://secure-pipeline-processed-<account-id>/ --recursive

# Check file metadata
aws s3api head-object \
  --bucket secure-pipeline-processed-<account-id> \
  --key processed/20260522120000_document.pdf
```

## Integration Testing

### End-to-End Workflow

```bash
#!/bin/bash

# Test complete workflow
API_ENDPOINT="https://your-api-id.execute-api.region.amazonaws.com/prod"
FILE_PATH="./test_document.pdf"

# Step 1: Upload file
echo "Step 1: Uploading file..."
RESPONSE=$(curl -s -X POST "${API_ENDPOINT}/upload" \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"$(basename $FILE_PATH)\",
    \"file_data\": \"$(base64 -i $FILE_PATH | tr -d '\n')\"
  }")

echo "$RESPONSE" | jq '.'

DOC_ID=$(echo "$RESPONSE" | jq -r '.data.document_id')
echo ""
echo "Document ID: $DOC_ID"

# Step 2: Wait for processing
echo ""
echo "Step 2: Waiting for processing (10 seconds)..."
sleep 10

# Step 3: Check audit log
echo ""
echo "Step 3: Checking audit log..."
aws dynamodb query \
  --table-name secure-pipeline-audit-log \
  --key-condition-expression "document_id = :doc_id" \
  --expression-attribute-values "{\":doc_id\":{\"S\":\"$DOC_ID\"}}" \
  --query 'Items[*].[#status,#timestamp,#size]' \
  --expression-attribute-names '{"#status":"status","#timestamp":"timestamp","#size":"file_size"}' | jq '.'

# Step 4: Check S3 processed bucket
echo ""
echo "Step 4: Checking processed bucket..."
aws s3 ls s3://secure-pipeline-processed-*/processed/ --recursive | grep "$DOC_ID"

echo ""
echo "✅ End-to-end test complete!"
```

## Performance Testing

### Load Testing with Apache Bench

```bash
# Generate multiple test files
for i in {1..10}; do
  echo "Test Document $i" > test_$i.pdf
done

# Run load test
API_ENDPOINT="https://your-api-id.execute-api.region.amazonaws.com/prod"

# Note: Apache Bench doesn't support POST with request body easily
# Use wrk or Apache JMeter for POST testing

# Alternative: Use wrk2
wrk -t4 -c100 -d30s \
  --script=post.lua \
  "${API_ENDPOINT}/upload"
```

## Troubleshooting

### Upload Handler Returns 500 Error

1. Check Lambda execution role permissions:
```bash
aws iam get-role-policy \
  --role-name secure-pipeline-upload-handler-role \
  --policy-name secure-pipeline-upload-handler-policy
```

2. Check CloudWatch logs:
```bash
aws logs tail /aws/lambda/secure-pipeline-upload-handler --follow
```

3. Verify environment variables:
```bash
aws lambda get-function-configuration \
  --function-name secure-pipeline-upload-handler \
  | jq '.Environment.Variables'
```

### Files Not Appearing in Processed Bucket

1. Check S3 event notification configuration:
```bash
aws s3api get-bucket-notification-configuration \
  --bucket secure-pipeline-uploads
```

2. Check Lambda permission for S3:
```bash
aws lambda list-policy --function-name secure-pipeline-process-handler
```

3. Check DynamoDB for error messages:
```bash
aws dynamodb scan \
  --table-name secure-pipeline-audit-log \
  --filter-expression "attribute_exists(error_message)"
```

### SNS Notifications Not Received

1. Verify topic subscriptions:
```bash
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:region:account:secure-pipeline-processing-notifications
```

2. Check SNS publish permissions for Lambda role

## Monitoring Dashboard

Create a CloudWatch dashboard to monitor the pipeline:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name SecureDocumentPipeline \
  --dashboard-body file://dashboard.json
```

See `dashboard.json` for example configuration.
