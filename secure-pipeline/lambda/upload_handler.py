"""
Upload Handler Lambda Function
Processes file uploads via API Gateway, validates files, and stores audit logs.
Security fixes applied:
- UUID document ID (no filename in ID)
- User identity captured from API Gateway context
- Presigned URL expiry reduced to 15 minutes
- IP address captured in audit log
"""

import json
import base64
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
UPLOAD_BUCKET = os.environ.get("UPLOAD_BUCKET")
AUDIT_TABLE = os.environ.get("AUDIT_TABLE")
KMS_KEY_ARN = os.environ.get("KMS_KEY_ARN")

# Constants
ALLOWED_FILE_TYPES = {"pdf", "csv", "xlsx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
PRESIGNED_URL_EXPIRY = 900  # 15 minutes (reduced from 1 hour for security)


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def get_file_extension(filename: str) -> str:
    """Extract and validate file extension."""
    if "." not in filename:
        raise ValidationError("File must have an extension")
    ext = filename.rsplit(".", 1)[1].lower()
    return ext


def validate_file_type(filename: str) -> None:
    """Validate that file type is allowed."""
    ext = get_file_extension(filename)
    if ext not in ALLOWED_FILE_TYPES:
        raise ValidationError(
            f"Invalid file type: {ext}. Allowed types: {', '.join(ALLOWED_FILE_TYPES)}"
        )
    logger.info(f"File type validation passed: {ext}")


def validate_file_size(file_data: bytes) -> None:
    """Validate that file size is within limits."""
    file_size = len(file_data)
    if file_size == 0:
        raise ValidationError("File cannot be empty")
    if file_size > MAX_FILE_SIZE:
        raise ValidationError(
            f"File size {file_size} bytes exceeds maximum {MAX_FILE_SIZE} bytes"
        )
    logger.info(f"File size validation passed: {file_size} bytes")


def decode_file_data(encoded_data: str) -> bytes:
    """Decode base64 encoded file data."""
    try:
        file_data = base64.b64decode(encoded_data)
        return file_data
    except Exception as e:
        raise ValidationError(f"Failed to decode base64 data: {str(e)}")


def upload_to_s3(
    bucket: str,
    key: str,
    file_data: bytes,
    kms_key_arn: str,
    filename: str,
    document_id: str
) -> None:
    """Upload file to S3 with KMS encryption."""
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=file_data,
            ServerSideEncryption="aws:kms",
            SSEKMSKeyId=kms_key_arn,
            Metadata={
                "document-id": document_id,
                "original-filename": filename,
                "uploaded-at": datetime.utcnow().isoformat(),
            }
        )
        logger.info(f"File uploaded to S3: s3://{bucket}/{key}")
    except ClientError as e:
        logger.error(f"S3 upload failed: {str(e)}")
        raise


def write_audit_log(
    table_name: str,
    document_id: str,
    filename: str,
    file_size: int,
    status: str,
    user_id: str,
    ip_address: str,
    s3_location: str
) -> None:
    """Write audit log entry to DynamoDB."""
    try:
        table = dynamodb.Table(table_name)
        item = {
            "document_id": document_id,
            "timestamp": int(datetime.utcnow().timestamp()),
            "filename": filename,
            "file_size": file_size,
            "status": status,
            "action": "file_upload",
            "user_id": user_id,           # FIX 1: capture who uploaded
            "ip_address": ip_address,      # FIX 1: capture where from
            "s3_location": s3_location,    # where file is stored
            "kms_key_arn": KMS_KEY_ARN,    # which key encrypted it
        }
        table.put_item(Item=item)
        logger.info(f"Audit log written for document: {document_id}")
    except ClientError as e:
        logger.error(f"DynamoDB write failed: {str(e)}")
        raise


def generate_presigned_url(
    bucket: str,
    key: str,
    expiry: int = PRESIGNED_URL_EXPIRY
) -> str:
    """Generate presigned URL for status checking."""
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiry
        )
        logger.info(f"Presigned URL generated for: {key}")
        return url
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {str(e)}")
        raise


def extract_request_context(event: Dict[str, Any]) -> tuple:
    """Extract user identity and IP from API Gateway request context."""
    request_context = event.get("requestContext", {})

    # Extract IP address
    identity = request_context.get("identity", {})
    ip_address = identity.get("sourceIp", "unknown")

    # Extract user identity — from Cognito or API key
    authorizer = request_context.get("authorizer", {})
    user_id = (
        authorizer.get("claims", {}).get("sub")      # Cognito user ID
        or authorizer.get("principalId")              # API key principal
        or identity.get("user")                       # IAM user
        or "anonymous"
    )

    return user_id, ip_address


def build_response(
    status_code: int,
    message: str,
    data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Build Lambda response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "X-Request-ID": os.environ.get("_X_AMZN_TRACE_ID", "unknown")
        },
        "body": json.dumps({
            "message": message,
            "data": data or {}
        })
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for file uploads.

    Expected request body:
    {
        "filename": "statement_jan2026.pdf",
        "file_data": "base64_encoded_string"
    }
    """
    try:
        logger.info("Processing upload request")

        # Validate environment variables
        if not all([UPLOAD_BUCKET, AUDIT_TABLE, KMS_KEY_ARN]):
            logger.error("Missing required environment variables")
            return build_response(500, "Server configuration error")

        # Extract user context from API Gateway
        user_id, ip_address = extract_request_context(event)

        # Parse request body
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", {})

        filename = body.get("filename", "").strip()
        encoded_file_data = body.get("file_data", "").strip()

        # Validate inputs
        if not filename:
            return build_response(400, "Filename is required")
        if not encoded_file_data:
            return build_response(400, "File data is required")

        # Validate file type and decode
        validate_file_type(filename)
        file_data = decode_file_data(encoded_file_data)
        validate_file_size(file_data)

        # FIX 2: Generate pure UUID document ID (no filename in ID)
        document_id = str(uuid.uuid4())
        s3_key = f"uploads/{document_id}"
        s3_location = f"s3://{UPLOAD_BUCKET}/{s3_key}"

        # Upload to S3 with KMS encryption
        upload_to_s3(UPLOAD_BUCKET, s3_key, file_data, KMS_KEY_ARN, filename, document_id)

        # Write full audit log
        write_audit_log(
            AUDIT_TABLE,
            document_id,
            filename,
            len(file_data),
            "uploaded",
            user_id,
            ip_address,
            s3_location
        )

        # FIX 3: Presigned URL expires in 15 minutes not 1 hour
        presigned_url = generate_presigned_url(UPLOAD_BUCKET, s3_key)

        logger.info(f"Upload completed successfully: {document_id}")

        return build_response(
            200,
            "File uploaded successfully",
            {
                "document_id": document_id,
                "filename": filename,
                "file_size": len(file_data),
                "status_url": presigned_url,
                "status_check_expires_in_seconds": PRESIGNED_URL_EXPIRY
            }
        )

    except ValidationError as e:
        logger.warning(f"Validation error: {str(e)}")
        return build_response(400, str(e))

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(f"AWS service error ({error_code}): {str(e)}")
        if error_code == "AccessDenied":
            return build_response(403, "Access denied to required resources")
        elif error_code == "NoSuchBucket":
            return build_response(500, "Upload bucket not found")
        else:
            return build_response(500, "Failed to process upload")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return build_response(500, "Internal server error")