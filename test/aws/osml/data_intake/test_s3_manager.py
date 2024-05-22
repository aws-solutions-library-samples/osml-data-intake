# Copyright 2024 Amazon.com, Inc. or its affiliates.

import unittest

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
        from aws.osml.data_intake.s3_manager import S3Url

        url = "s3://bucketname/example/object.txt"
        s3_url = S3Url(url)
        self.assertEqual(s3_url.bucket, "bucketname")
        self.assertEqual(s3_url.key, "example/object.txt")
        self.assertEqual(s3_url.url, url)


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
        from aws.osml.data_intake.s3_manager import S3Manager

        self.s3_client = boto3.client("s3", region_name="us-east-1")
        self.bucket_name = "output_bucket"
        self.s3_client.create_bucket(Bucket=self.bucket_name)
        self.s3_manager = S3Manager(self.bucket_name)

    def test_download_file(self):
        """
        Test the download functionality of S3Manager.

        Ensures a file can be downloaded from S3 and is correctly placed in the local temporary directory.
        """
        from aws.osml.data_intake.s3_manager import S3Url

        s3_url = S3Url("s3://output_bucket/test_download_file.txt")
        self.s3_client.put_object(Bucket=s3_url.bucket, Key=s3_url.key, Body=b"Hello world!")
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
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key="test_upload_file.txt")
        data = response["Body"].read()
        self.assertEqual(data.decode(), "Upload me!")

    def test_download_file_client_error(self):
        """
        Test error handling in download_file for non-existent buckets.

        Verifies that a ClientError is raised when attempting to download from a non-existent bucket.
        """
        from aws.osml.data_intake.s3_manager import S3Url

        s3_url = S3Url("s3://nonexistent_bucket/test_download_file.txt")
        with self.assertRaises(ClientError) as context:
            self.s3_manager.download_file(s3_url)
        self.assertIn("The specified bucket does not exist", str(context.exception))

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
