# Copyright 2024 Amazon.com, Inc. or its affiliates.

import unittest
from unittest.mock import patch

import boto3
from boto3.exceptions import S3UploadFailedError
from botocore.exceptions import ClientError
from moto import mock_aws


class TestS3Url(unittest.TestCase):
    """
    A test suite for the S3Url class in the AWS OSML data intake module.

    Tests the initialization of the S3Url class to ensure that S3 URLs are parsed correctly.
    """

    def test_initialization(self):
        """
        Test the initialization of the S3Url class.

        Asserts that the bucket name, key, and full URL are correctly extracted from an S3 URL.
        """
        from aws.osml.data_intake.managers.s3_manager import S3Url

        url = "s3://bucketname/example/object.txt"
        s3_url = S3Url(url)
        self.assertEqual(s3_url.bucket, "bucketname")
        self.assertEqual(s3_url.key, "example/object.txt")
        self.assertEqual(s3_url.url, url)
        self.assertEqual(s3_url.prefix, "example")
        self.assertEqual(s3_url.filename, "object.txt")

    def test_key_with_query_string(self):
        from aws.osml.data_intake.managers.s3_manager import S3Url

        url = "s3://my-bucket/path/to/object?param1=value1&param2=value2"
        s3_url = S3Url(url)
        expected_key = "path/to/object?param1=value1&param2=value2"
        self.assertEqual(s3_url.key, expected_key)


@mock_aws
class TestS3Manager(unittest.TestCase):
    """
    A test suite for the S3Manager class in the AWS OSML data intake module.

    Tests file uploading and downloading functionality using a mocked AWS S3 environment.
    """

    def setUp(self):
        """
        Set up the test environment for S3Manager tests.
        """
        from aws.osml.data_intake.managers.s3_manager import S3Manager

        self.s3_client = boto3.resource("s3", region_name="us-east-1")
        self.bucket_name = "output_bucket"
        self.s3_client.meta.client.create_bucket(Bucket=self.bucket_name)
        self.s3_manager = S3Manager(self.bucket_name)

    def test_download_file(self):
        """
        Test the download functionality of S3Manager.

        Ensures a file can be downloaded from S3 and is correctly placed in the local temporary directory.
        """
        from aws.osml.data_intake.managers.s3_manager import S3Url

        s3_url = S3Url("s3://output_bucket/test_download_file.txt")
        self.s3_client.meta.client.put_object(Bucket=s3_url.bucket, Key=s3_url.key, Body=b"Hello world!")
        file_path = self.s3_manager.download_file(s3_url)

        with open(file_path, "rb") as f:
            content = f.read()
        self.assertEqual(content, b"Hello world!")

    def test_upload_file(self):
        """
        Test the upload functionality of S3Manager.

        Ensures a file can be uploaded to S3 and verifies the uploaded content matches the local file.
        """
        file_path = "/tmp/test_upload_file.txt"
        with open(file_path, "w") as f:
            f.write("Upload me!")

        self.s3_manager.upload_file(file_path, "text file")
        response = self.s3_client.meta.client.get_object(Bucket=self.bucket_name, Key="test_upload_file.txt")
        data = response["Body"].read()
        self.assertEqual(data.decode(), "Upload me!")

    def test_download_file_client_error(self):
        """
        Test error handling in download_file for non-existent buckets.

        Verifies that a Exception is raised when attempting to download from a non-existent bucket.
        """
        from aws.osml.data_intake.managers.s3_manager import S3Url

        s3_url = S3Url("s3://nonexistent_bucket/test_download_file.txt")
        s3_path = self.s3_manager.download_file(s3_url)
        self.assertEqual(None, s3_path)

    @patch("logging.Logger.error")
    def test_download_file_404_error(self, mock_error):
        from aws.osml.data_intake.managers.s3_manager import S3Url

        with patch("boto3.s3.transfer.S3Transfer.download_file") as download_file:
            download_file.side_effect = ClientError({"Error": {"Code": "404"}}, "unexpected")

            s3_url = S3Url("s3://my-bucket/my-key")
            self.s3_manager.download_file(s3_url)

            mock_error.assert_called_with(
                "S3 error: An error occurred (404) when calling the unexpected operation: Unknown The "
                + f"{s3_url.bucket} bucket does not exist!"
            )

    @patch("logging.Logger.error")
    def test_download_file_403_error(self, mock_error):
        from aws.osml.data_intake.managers.s3_manager import S3Url

        with patch("boto3.s3.transfer.S3Transfer.download_file") as download_file:
            download_file.side_effect = ClientError({"Error": {"Code": "403"}}, "unexpected")

            s3_url = S3Url("s3://my-bucket/my-key")
            self.s3_manager.download_file(s3_url)

            mock_error.assert_called_with(
                "S3 error: An error occurred (403) when calling the unexpected operation: Unknown You"
                + " do not have permission to access "
                + f"{s3_url.bucket} bucket!"
            )

    def test_download_file_exception_error(self):
        from aws.osml.data_intake.managers.s3_manager import S3Url

        with patch("boto3.s3.transfer.S3Transfer.download_file") as download_file:
            download_file.side_effect = Exception("Unexpected")

            s3_url = S3Url("s3://my-bucket/my-key")
            self.s3_manager.download_file(s3_url)

    def test_upload_file_client_error(self):
        """
        Test error handling in upload_file for incorrect bucket permissions.

        Verifies that an S3UploadFailedError is raised when attempting to upload to a bucket with incorrect permissions.
        """
        file_path = "/tmp/test_upload_file.txt"
        with open(file_path, "w") as f:
            f.write("Upload me!")
        self.s3_manager.output_bucket = "non-exist-bucket"
        with self.assertRaises(S3UploadFailedError):
            self.s3_manager.upload_file(file_path, "text file")


if __name__ == "__main__":
    unittest.main()
