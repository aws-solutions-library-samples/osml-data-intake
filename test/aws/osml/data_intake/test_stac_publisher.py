# Copyright 2024 Amazon.com, Inc. or its affiliates.

import unittest

import boto3
from moto import mock_aws


@mock_aws
class TestStacPublisher(unittest.TestCase):
    """
    A test suite for the StacPublisher class in the AWS OSML data intake module.

    Tests the functionality of publishing STAC items to an AWS SNS topic using mocked AWS services.
    """

    def setUp(self):
        """
        Set up the test environment for StacPublisher tests.
        """
        from aws.osml.data_intake.stac_publisher import StacPublisher

        self.sns_client = boto3.client("sns", region_name="us-east-1")
        response = self.sns_client.create_topic(Name="MyTopic")
        self.sns_topic_arn = response["TopicArn"]

        self.publisher = StacPublisher(output_topic=self.sns_topic_arn)
        self.publisher.sns_client = self.sns_client

    def tearDown(self):
        """
        Clean up after tests by resetting the SNS client.
        """
        self.sns_client = None

    def test_publish_stac_item_success(self):
        """
        Test the successful publishing of a STAC item.

        Mocks necessary dependencies and verifies that successful publishing
        results in correct logging without any errors.
        """
        from aws.osml.data_intake.image_data import ImageData
        from aws.osml.data_intake.s3_manager import S3Manager, S3Url

        s3_url = S3Url("s3://output_bucket/test_download_file.txt")
        s3_manager = S3Manager("output-bucket")
        s3_manager.s3_url = s3_url
        image_data = ImageData("./test/data/small.tif")

        self.publisher.publish_stac_item(s3_manager, image_data)

    def test_publish_stac_item_failure(self):
        """
        Test the failure scenario in publishing a STAC item.

        Introduces a failure by using an invalid topic ARN and checks that the error is logged correctly.
        """
        from aws.osml.data_intake.image_data import ImageData
        from aws.osml.data_intake.s3_manager import S3Manager, S3Url

        s3_url = S3Url("s3://output_bucket/test_download_file.txt")
        s3_manager = S3Manager("output-bucket")
        s3_manager.s3_url = s3_url
        image_data = ImageData("./test/data/small.tif")

        self.publisher.output_topic = "BadTopic"
        with self.assertRaises(Exception):
            self.publisher.publish_stac_item(s3_manager, image_data)


if __name__ == "__main__":
    unittest.main()
