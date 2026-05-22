"""
Process Handler Lambda Function
Processes uploaded files from S3, validates content, applies encryption, and sends notifications.
Security fixes applied:
- URL decode S3 key to handle special characters
- Proper document ID extraction from UUID-based keys
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Tuple
from urllib.parse import unquote_plus
import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
sns_client = boto3.client("sns")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
PROCESSED_BUCKET = os.environ.get("PROCESSED_BUCKET")
AUDIT_TABLE = os.environ.get("AUDIT_TABLE")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")
KMS_KEY_ARN = os.environ.get("KMS_KEY_ARN")

# Constants
MIN_FILE_SIZE = 1  # 1 byte minimum


class ProcessingError(Exception):
    """Custom exception for processing errors"""
    pass


def get_s3_object_metadata(bucket: str, key: str) -> Tuple[int, str]:
    """Retrieve file size and metadata from S3."""
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        file_size = response["ContentLength"]
        content_type = response.get("ContentType", "application/octet-stream")
        logger.info(f"Object metadata retrieved: {key} ({file_size} bytes)")
        return file_size, content_type
    except ClientError as e:
        logger.error(f"Failed to retrieve object metadata: {str(e)}")
        raise ProcessingError(f"Cannot access file in S3: {str(e)}")


def validate_file_not_empty(file_size: int) -> None:
    """Validate that file is not empty."""
    if file_size < MIN_FILE_SIZE:
        raise ProcessingError(f"File size must be at least {MIN_FILE_SIZE} byte")
    logger.info(f"File size validation passed: {file_size} bytes")


def copy_file_with_encryption(
    source_bucket: str,
    source_key: str,
    destination_bucket: str,
    destination_key: str,
    kms_key_arn: str,
    content_type: str
) -> None:
    """Copy file from source to destination bucket with KMS encryption."""
    try:
        copy_source = {
            "Bucket": source_bucket,
            "Key": source_key
        }
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=destination_bucket,
            Key=destination_key,
            ServerSideEncryption="aws:kms",
            SSEKMSKeyId=kms_key_arn,
            ContentType=content_type,
            MetadataDirective="REPLACE",
            Metadata={
                "processed-at": datetime.utcnow().isoformat(),
                "original-key": source_key,
            }
        )
        logger.info(
            f"File copied with encryption: "
            f"s3://{source_bucket}/{source_key} -> "
            f"s3://{destination_bucket}/{destination_key}"
        )
    except ClientError as e:
        logger.error(f"S3 copy operation failed: {str(e)}")
        raise ProcessingError(f"Failed to copy file to secure bucket: {str(e)}")


def extract_document_id_from_key(key: str) -> str:
    """
    Extract document ID from S3 key.
    FIX: URL decode key to handle special characters in S3 events.
    Expected key format: uploads/{uuid}
    """
    decoded_key = unquote_plus(key)
    parts = decoded_key.split("/")
    return parts[-1] if len(parts) >= 2 else decoded_key


def update_audit_log(
    table_name: str,
    document_id: str,
    status: str,
    processed_key: str = None,
    error_message: str = None
) -> None:
    """Update audit log entry in DynamoDB."""
    try:
        table = dynamodb.Table(table_name)
        update_expression = "SET #status = :status, updated_at = :updated_at"
        expression_values = {
            ":status": status,
            ":updated_at": datetime.utcnow().isoformat(),
        }
        if processed_key:
            update_expression += ", processed_key = :processed_key"
            expression_values[":processed_key"] = processed_key
        if error_message:
            update_expression += ", error_message = :error_message"
            expression_values[":error_message"] = error_message

        table.update_item(
            Key={"document_id": document_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues=expression_values
        )
        logger.info(f"Audit log updated for document: {document_id} (status: {status})")
    except ClientError as e:
        logger.error(f"DynamoDB update failed: {str(e)}")
        logger.warning("Continuing despite audit log update failure")


def send_sns_notification(
    topic_arn: str,
    document_id: str,
    status: str,
    metadata: Dict[str, Any] = None
) -> None:
    """Send SNS notification about processing status."""
    try:
        message = {
            "document_id": document_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        sns_client.publish(
            TopicArn=topic_arn,
            Subject=f"Document Processing Update: {status}",
            Message=json.dumps(message, indent=2)
        )
        logger.info(f"SNS notification sent for document: {document_id} (status: {status})")
    except ClientError as e:
        logger.error(f"SNS publish failed: {str(e)}")
        logger.warning("Continuing despite SNS notification failure")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for file processing.
    Triggered by S3 event when file lands in upload bucket.
    """
    try:
        logger.info("Processing S3 event")

        # Validate environment variables
        if not all([PROCESSED_BUCKET, AUDIT_TABLE, SNS_TOPIC_ARN, KMS_KEY_ARN]):
            logger.error("Missing required environment variables")
            raise ProcessingError("Server configuration error")

        # Parse S3 event
        records = event.get("Records", [])
        if not records:
            logger.warning("No records found in S3 event")
            return {"statusCode": 400, "body": "No records in event"}

        # Process first record
        record = records[0]
        source_bucket = record["s3"]["bucket"]["name"]
        source_key = unquote_plus(record["s3"]["object"]["key"])

        logger.info(f"Processing file: s3://{source_bucket}/{source_key}")

        # Extract document ID
        document_id = extract_document_id_from_key(source_key)

        # Retrieve file metadata
        file_size, content_type = get_s3_object_metadata(source_bucket, source_key)

        # Validate file is not empty
        validate_file_not_empty(file_size)

        # Generate destination key
        destination_key = f"processed/{document_id}"

        # Copy file with encryption to secure bucket
        copy_file_with_encryption(
            source_bucket,
            source_key,
            PROCESSED_BUCKET,
            destination_key,
            KMS_KEY_ARN,
            content_type
        )

        # Update audit log with success
        update_audit_log(
            AUDIT_TABLE,
            document_id,
            "processed",
            processed_key=destination_key
        )

        # Send SNS notification
        send_sns_notification(
            SNS_TOPIC_ARN,
            document_id,
            "processed",
            metadata={
                "source": f"s3://{source_bucket}/{source_key}",
                "destination": f"s3://{PROCESSED_BUCKET}/{destination_key}",
                "file_size": file_size,
                "content_type": content_type,
            }
        )

        logger.info(f"File processing completed successfully: {document_id}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "File processed successfully",
                "document_id": document_id,
                "destination": f"s3://{PROCESSED_BUCKET}/{destination_key}"
            })
        }

    except ProcessingError as e:
        logger.error(f"Processing error: {str(e)}")
        try:
            document_id = extract_document_id_from_key(
                event["Records"][0]["s3"]["object"]["key"]
            )
            update_audit_log(
                AUDIT_TABLE,
                document_id,
                "processing_failed",
                error_message=str(e)
            )
        except Exception as log_error:
            logger.error(f"Could not update audit log: {str(log_error)}")

        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": "Processing failed",
                "error": str(e)
            })
        }

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(f"AWS service error ({error_code}): {str(e)}")
        try:
            document_id = extract_document_id_from_key(
                event["Records"][0]["s3"]["object"]["key"]
            )
            update_audit_log(
                AUDIT_TABLE,
                document_id,
                "processing_failed",
                error_message=f"AWS error: {error_code}"
            )
        except Exception:
            pass

        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Processing failed",
                "error": f"AWS service error: {error_code}"
            })
        }

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Internal server error",
                "error": "An unexpected error occurred"
            })
        }