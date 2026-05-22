"""
Unit tests for process_handler Lambda function
"""

import json
import unittest
from unittest.mock import patch, MagicMock
from process_handler import (
    lambda_handler,
    validate_file_not_empty,
    extract_document_id_from_key,
    ProcessingError,
)


class TestProcessing(unittest.TestCase):
    """Test processing functions"""

    def test_validate_file_not_empty_valid(self):
        """Test validation with non-empty file"""
        validate_file_not_empty(1024)  # Should not raise

    def test_validate_file_not_empty_zero(self):
        """Test validation with empty file"""
        with self.assertRaises(ProcessingError):
            validate_file_not_empty(0)

    def test_extract_document_id_from_uploads_key(self):
        """Test extracting document ID from uploads key"""
        key = "uploads/20260522120000_document.pdf"
        doc_id = extract_document_id_from_key(key)
        self.assertEqual(doc_id, "20260522120000_document.pdf")

    def test_extract_document_id_from_processed_key(self):
        """Test extracting document ID from processed key"""
        key = "processed/20260522120000_document.pdf"
        doc_id = extract_document_id_from_key(key)
        self.assertEqual(doc_id, "20260522120000_document.pdf")

    def test_extract_document_id_simple_key(self):
        """Test extracting document ID from simple key"""
        key = "document.pdf"
        doc_id = extract_document_id_from_key(key)
        self.assertEqual(doc_id, "document.pdf")


class TestProcessHandler(unittest.TestCase):
    """Test process_handler Lambda function"""

    @patch.dict(
        "os.environ",
        {
            "PROCESSED_BUCKET": "processed-bucket",
            "AUDIT_TABLE": "test-table",
            "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789:test-topic",
            "KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456789:key/test",
        },
    )
    @patch("process_handler.s3_client")
    @patch("process_handler.dynamodb")
    @patch("process_handler.sns_client")
    def test_successful_processing(self, mock_sns, mock_dynamodb, mock_s3):
        """Test successful file processing"""
        # Setup mocks
        mock_s3.head_object.return_value = {"ContentLength": 1024, "ContentType": "application/pdf"}
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table

        # Create test event
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "upload-bucket"},
                        "object": {"key": "uploads/20260522120000_document.pdf"},
                    }
                }
            ]
        }

        # Execute
        result = lambda_handler(event, None)

        # Verify
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["message"], "File processed successfully")
        self.assertIn("document_id", body)

        # Verify S3 operations were called
        mock_s3.head_object.assert_called_once()
        mock_s3.copy_object.assert_called_once()

        # Verify DynamoDB update was called
        mock_table.update_item.assert_called_once()

        # Verify SNS publish was called
        mock_sns.publish.assert_called_once()

    @patch.dict(
        "os.environ",
        {
            "PROCESSED_BUCKET": "processed-bucket",
            "AUDIT_TABLE": "test-table",
            "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789:test-topic",
            "KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456789:key/test",
        },
    )
    def test_no_records_in_event(self):
        """Test event with no records"""
        event = {"Records": []}

        result = lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 400)

    @patch.dict(
        "os.environ",
        {
            "PROCESSED_BUCKET": "processed-bucket",
            "AUDIT_TABLE": None,
            "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789:test-topic",
            "KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456789:key/test",
        },
    )
    def test_missing_environment_variables(self):
        """Test with missing environment variables"""
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "upload-bucket"},
                        "object": {"key": "uploads/document.pdf"},
                    }
                }
            ]
        }

        result = lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 500)

    @patch.dict(
        "os.environ",
        {
            "PROCESSED_BUCKET": "processed-bucket",
            "AUDIT_TABLE": "test-table",
            "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789:test-topic",
            "KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456789:key/test",
        },
    )
    @patch("process_handler.s3_client")
    def test_file_not_found(self, mock_s3):
        """Test when file doesn't exist in S3"""
        from botocore.exceptions import ClientError

        # Setup mock to raise NoSuchKey error
        error_response = {"Error": {"Code": "NoSuchKey"}}
        mock_s3.head_object.side_effect = ClientError(error_response, "HeadObject")

        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "upload-bucket"},
                        "object": {"key": "uploads/nonexistent.pdf"},
                    }
                }
            ]
        }

        result = lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 500)

    @patch.dict(
        "os.environ",
        {
            "PROCESSED_BUCKET": "processed-bucket",
            "AUDIT_TABLE": "test-table",
            "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789:test-topic",
            "KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456789:key/test",
        },
    )
    @patch("process_handler.s3_client")
    def test_empty_file_validation(self, mock_s3):
        """Test empty file validation"""
        # Setup mock to return 0 byte file
        mock_s3.head_object.return_value = {"ContentLength": 0, "ContentType": "application/pdf"}

        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "upload-bucket"},
                        "object": {"key": "uploads/empty.pdf"},
                    }
                }
            ]
        }

        result = lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertIn("File size must be", body["error"])

    @patch.dict(
        "os.environ",
        {
            "PROCESSED_BUCKET": "processed-bucket",
            "AUDIT_TABLE": "test-table",
            "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789:test-topic",
            "KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456789:key/test",
        },
    )
    @patch("process_handler.s3_client")
    @patch("process_handler.dynamodb")
    @patch("process_handler.sns_client")
    def test_sns_notification_failure_continues(self, mock_sns, mock_dynamodb, mock_s3):
        """Test that processing continues if SNS notification fails"""
        from botocore.exceptions import ClientError

        # Setup mocks
        mock_s3.head_object.return_value = {"ContentLength": 1024, "ContentType": "application/pdf"}
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Make SNS fail
        error_response = {"Error": {"Code": "InvalidParameter"}}
        mock_sns.publish.side_effect = ClientError(error_response, "Publish")

        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "upload-bucket"},
                        "object": {"key": "uploads/document.pdf"},
                    }
                }
            ]
        }

        # Execute - should still succeed
        result = lambda_handler(event, None)

        # Verify S3 and DynamoDB operations still completed
        self.assertEqual(result["statusCode"], 200)
        mock_s3.copy_object.assert_called_once()
        mock_table.update_item.assert_called_once()

    @patch.dict(
        "os.environ",
        {
            "PROCESSED_BUCKET": "processed-bucket",
            "AUDIT_TABLE": "test-table",
            "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789:test-topic",
            "KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456789:key/test",
        },
    )
    @patch("process_handler.s3_client")
    @patch("process_handler.dynamodb")
    def test_audit_log_failure_continues(self, mock_dynamodb, mock_s3):
        """Test that processing continues if audit log update fails"""
        from botocore.exceptions import ClientError

        # Setup mocks
        mock_s3.head_object.return_value = {"ContentLength": 1024, "ContentType": "application/pdf"}
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        # Make DynamoDB fail
        error_response = {"Error": {"Code": "ProvisionedThroughputExceededException"}}
        mock_table.update_item.side_effect = ClientError(error_response, "UpdateItem")

        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "upload-bucket"},
                        "object": {"key": "uploads/document.pdf"},
                    }
                }
            ]
        }

        # Execute - should still succeed
        result = lambda_handler(event, None)

        # Verify S3 operations still completed
        self.assertEqual(result["statusCode"], 200)
        mock_s3.copy_object.assert_called_once()


if __name__ == "__main__":
    unittest.main()
