#  Copyright 2024 Amazon.com, Inc. or its affiliates.
import json
import unittest

import boto3
from moto import mock_aws


@mock_aws
class TestImageProcessor(unittest.TestCase):
    """
    A test suite for the ImageProcessor class.

    This suite runs tests to ensure that the ImageProcessor can handle both
    successful and unsuccessful image processing tasks.
    """

    def setUp(self):
        """
        Set up the test environment for ImageProcessor tests.

        This involves creating a test S3 bucket, uploading a test image file,
        creating an SNS topic, and initializing the ImageProcessor with
        a mock S3 image URL and mock AWS clients.
        """
        from aws.osml.data_intake.image_processor import ImageProcessor

        test_bucket = "test-bucket"
        test_topic = "test-topic"

        # Create S3 bucket and upload test image
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=test_bucket)
        s3.upload_file("./test/data/small.tif", test_bucket, "small.tif")

        # Create an SNS topic
        sns = boto3.client("sns", region_name="us-east-1")
        response = sns.create_topic(Name=test_topic)
        sns_topic_arn = response["TopicArn"]

        # Mock the ImageProcessor
        message = {"image_uri": f"s3://{test_bucket}/small.tif"}
        self.processor = ImageProcessor(message=json.dumps(message))
        self.processor.stac_manager.sns_manager.sns_client = sns
        self.processor.stac_manager.sns_manager.output_topic = sns_topic_arn
        self.processor.s3_manager.s3_client = s3
        self.processor.s3_manager.output_bucket = test_bucket
        self.processor.stac_manager.s3_manager = self.processor.s3_manager

    def test_process_success(self):
        """
        Test the process method of ImageProcessor for a successful scenario.
        """
        # Run the process method
        response = self.processor.process()

        # Check the response
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("successfully", response["body"])

    def test_process_failure(self):
        """
        Test the process method of ImageProcessor for a failure scenario.
        """
        self.processor.sns_request.image_uri = "s3://invalid-bucket/invalid-image.tif"

        # Run the process method
        response = self.processor.process()

        # Check the response
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("NoSuchBucket", response["body"])


if __name__ == "__main__":
    unittest.main()
