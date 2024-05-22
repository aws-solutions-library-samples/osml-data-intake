#  Copyright 2024 Amazon.com, Inc. or its affiliates.

import unittest

import boto3
from botocore.exceptions import ClientError
from moto import mock_aws


@mock_aws
class TestSNSManager(unittest.TestCase):
    """
    Test suite for the SNSManager class.
    """

    def setUp(self):
        """
        Set up the test environment for SNSManager tests.

        Creates an SNS topic and initializes the SNSManager instance with the topic ARN.
        """
        from aws.osml.data_intake.sns_manager import SNSManager  # Adjust the import according to your file structure

        sns_client = boto3.client("sns", region_name="us-east-1")
        response = sns_client.create_topic(Name="MyTopic")
        self.sns_topic_arn = response["TopicArn"]
        self.sns_manager = SNSManager(self.sns_topic_arn)
        self.sns_manager.sns_client = sns_client

    def test_publish_message_success(self):
        """
        Test successful message publishing.

        Verifies that a message can be successfully published to the SNS topic.
        """
        message = "This is a test message."
        subject = "Test Subject"
        # No exception should be raised, indicating success
        self.sns_manager.publish_message(message=message, subject=subject)

    def test_publish_message_failure(self):
        """
        Test message publishing failure.

        Simulates a failure scenario by deleting the SNS topic before publishing
        and verifies that a ClientError is raised.
        """
        self.sns_manager.sns_client.delete_topic(TopicArn=self.sns_topic_arn)
        message = "This message should fail."
        subject = "Test Subject"

        with self.assertRaises(ClientError):
            self.sns_manager.publish_message(message=message, subject=subject)


if __name__ == "__main__":
    unittest.main()
