"""
Unit tests for upload_handler Lambda function
"""

import json
import base64
import unittest
from unittest.mock import patch, MagicMock, ANY
from upload_handler import (
    lambda_handler,
    validate_file_type,
    validate_file_size,
    decode_file_data,
    get_file_extension,
    ValidationError,
)


class TestFileValidation(unittest.TestCase):
    """Test file validation functions"""

    def test_valid_pdf_extension(self):
        """Test valid PDF file extension"""
        ext = get_file_extension("document.pdf")
        self.assertEqual(ext, "pdf")

    def test_valid_csv_extension(self):
        """Test valid CSV file extension"""
        ext = get_file_extension("data.csv")
        self.assertEqual(ext, "csv")

    def test_valid_xlsx_extension(self):
        """Test valid XLSX file extension"""
        ext = get_file_extension("spreadsheet.xlsx")
        self.assertEqual(ext, "xlsx")

    def test_missing_extension(self):
        """Test file without extension"""
        with self.assertRaises(ValidationError):
            get_file_extension("document")

    def test_case_insensitive_extension(self):
        """Test that extensions are case-insensitive"""
        ext = get_file_extension("document.PDF")
        self.assertEqual(ext, "pdf")

    def test_validate_file_type_pdf(self):
        """Test PDF file type validation"""
        validate_file_type("document.pdf")  # Should not raise

    def test_validate_file_type_csv(self):
        """Test CSV file type validation"""
        validate_file_type("data.csv")  # Should not raise

    def test_validate_file_type_xlsx(self):
        """Test XLSX file type validation"""
        validate_file_type("spreadsheet.xlsx")  # Should not raise

    def test_validate_file_type_invalid(self):
        """Test invalid file type"""
        with self.assertRaises(ValidationError):
            validate_file_type("document.docx")

    def test_validate_file_size_valid(self):
        """Test valid file size"""
        data = b"x" * 1024  # 1KB
        validate_file_size(data)  # Should not raise

    def test_validate_file_size_empty(self):
        """Test empty file validation"""
        with self.assertRaises(ValidationError):
            validate_file_size(b"")

    def test_validate_file_size_max(self):
        """Test file at maximum size"""
        data = b"x" * (10 * 1024 * 1024)  # 10MB
        validate_file_size(data)  # Should not raise

    def test_validate_file_size_exceeds_max(self):
        """Test file exceeding maximum size"""
        data = b"x" * (10 * 1024 * 1024 + 1)  # 10MB + 1 byte
        with self.assertRaises(ValidationError):
            validate_file_size(data)

    def test_decode_file_data_valid(self):
        """Test valid base64 decoding"""
        original_data = b"Test data"
        encoded = base64.b64encode(original_data).decode()
        decoded = decode_file_data(encoded)
        self.assertEqual(decoded, original_data)

    def test_decode_file_data_invalid(self):
        """Test invalid base64 decoding"""
        with self.assertRaises(ValidationError):
            decode_file_data("not-valid-base64-!!!!")


class TestUploadHandler(unittest.TestCase):
    """Test upload_handler Lambda function"""

    @patch.dict(
        "os.environ",
        {
            "UPLOAD_BUCKET": "test-bucket",
            "AUDIT_TABLE": "test-table",
            "KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456789:key/test",
        },
    )
    @patch("upload_handler.s3_client")
    @patch("upload_handler.dynamodb")
    def test_successful_upload(self, mock_dynamodb, mock_s3):
        """Test successful file upload"""
        # Setup mocks
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table

        # Create test event
        test_data = b"Test PDF content"
        encoded = base64.b64encode(test_data).decode()

        event = {
            "body": json.dumps({
                "filename": "document.pdf",
                "file_data": encoded
            })
        }

        # Execute
        result = lambda_handler(event, None)

        # Verify
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["message"], "File uploaded successfully")
        self.assertIn("document_id", body["data"])
        self.assertEqual(body["data"]["filename"], "document.pdf")
        self.assertEqual(body["data"]["file_size"], len(test_data))

        # Verify S3 upload was called
        mock_s3.put_object.assert_called_once()

        # Verify DynamoDB write was called
        mock_table.put_item.assert_called_once()

    @patch.dict(
        "os.environ",
        {
            "UPLOAD_BUCKET": "test-bucket",
            "AUDIT_TABLE": "test-table",
            "KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456789:key/test",
        },
    )
    def test_missing_filename(self):
        """Test upload with missing filename"""
        event = {
            "body": json.dumps({
                "file_data": base64.b64encode(b"test").decode()
            })
        }

        result = lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 400)

    @patch.dict(
        "os.environ",
        {
            "UPLOAD_BUCKET": "test-bucket",
            "AUDIT_TABLE": "test-table",
            "KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456789:key/test",
        },
    )
    def test_missing_file_data(self):
        """Test upload with missing file data"""
        event = {
            "body": json.dumps({
                "filename": "document.pdf"
            })
        }

        result = lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 400)

    @patch.dict(
        "os.environ",
        {
            "UPLOAD_BUCKET": "test-bucket",
            "AUDIT_TABLE": "test-table",
            "KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456789:key/test",
        },
    )
    def test_invalid_file_type(self):
        """Test upload with invalid file type"""
        test_data = b"Test content"
        encoded = base64.b64encode(test_data).decode()

        event = {
            "body": json.dumps({
                "filename": "document.docx",
                "file_data": encoded
            })
        }

        result = lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertIn("Invalid file type", body["message"])

    @patch.dict(
        "os.environ",
        {
            "UPLOAD_BUCKET": "test-bucket",
            "AUDIT_TABLE": "test-table",
            "KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456789:key/test",
        },
    )
    def test_file_exceeds_size_limit(self):
        """Test upload with file exceeding size limit"""
        large_data = b"x" * (10 * 1024 * 1024 + 1)
        encoded = base64.b64encode(large_data).decode()

        event = {
            "body": json.dumps({
                "filename": "large.pdf",
                "file_data": encoded
            })
        }

        result = lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertIn("exceeds maximum", body["message"])

    @patch.dict(
        "os.environ",
        {
            "UPLOAD_BUCKET": None,
            "AUDIT_TABLE": "test-table",
            "KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456789:key/test",
        },
    )
    def test_missing_environment_variables(self):
        """Test with missing environment variables"""
        test_data = b"Test"
        encoded = base64.b64encode(test_data).decode()

        event = {
            "body": json.dumps({
                "filename": "document.pdf",
                "file_data": encoded
            })
        }

        result = lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 500)

    @patch.dict(
        "os.environ",
        {
            "UPLOAD_BUCKET": "test-bucket",
            "AUDIT_TABLE": "test-table",
            "KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456789:key/test",
        },
    )
    @patch("upload_handler.s3_client")
    def test_s3_access_denied(self, mock_s3):
        """Test S3 access denied error"""
        from botocore.exceptions import ClientError

        # Setup mock to raise AccessDenied error
        error_response = {"Error": {"Code": "AccessDenied"}}
        mock_s3.put_object.side_effect = ClientError(error_response, "PutObject")

        test_data = b"Test PDF content"
        encoded = base64.b64encode(test_data).decode()

        event = {
            "body": json.dumps({
                "filename": "document.pdf",
                "file_data": encoded
            })
        }

        result = lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 403)


if __name__ == "__main__":
    unittest.main()
