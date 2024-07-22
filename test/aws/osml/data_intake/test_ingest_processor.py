#  Copyright 2024 Amazon.com, Inc. or its affiliates.
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

import boto3
from moto import mock_aws


@mock_aws
class TestIngestProcessor(unittest.TestCase):
    """
    Test case class for validating the STAC ingestion Lambda functions.
    """

    @staticmethod
    def sns_event():
        """
        Constructs a mock SNS event for testing.

        Returns:
            dict: A dictionary representing the SNS event with a predefined message.
        """
        return {
            "Records": [
                {
                    "Sns": {
                        "Message": json.dumps(
                            {
                                "id": "123",
                                "type": "Feature",
                                "properties": {},
                                "geometry": {},
                                "links": [],
                                "assets": {},
                                "bbox": [],
                                "stac_version": "1.0.0",
                                "stac_extensions": [],
                                "collection": "test-collection",
                            }
                        )
                    }
                }
            ]
        }

    def setUp(self):
        """
        Set up method to initialize required AWS resources before each test.
        """
        self.sns = boto3.client("sns", region_name="us-east-1")
        self.sns.create_topic(Name="test-topic")

        self.s3 = boto3.client("s3", region_name="us-east-1")
        self.s3.create_bucket(Bucket="test-bucket")

    @patch("stac_fastapi.opensearch.database_logic.DatabaseLogic.create_item", new_callable=AsyncMock)
    def test_handler_success(self, mock_create_item):
        """
        Test the handler function for a successful scenario.
        """
        from aws.osml.data_intake.ingest_processor import handler

        mock_create_item.return_value = asyncio.Future()
        mock_create_item.return_value.set_result(None)  # Simulate success

        event = self.sns_event()
        response = handler(event, None)

        self.assertEqual(response["statusCode"], 200)
        self.assertIn("successfully", json.loads(response["body"]))

    @patch("stac_fastapi.opensearch.database_logic.DatabaseLogic.create_item", new_callable=AsyncMock)
    def test_handler_failure(self, mock_create_item):
        """
        Test the handler function for a unsuccessful scenario.
        """
        from aws.osml.data_intake.ingest_processor import handler

        mock_create_item.side_effect = Exception("Database error")

        event = self.sns_event()
        response = handler(event, None)

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Database error", json.loads(response["body"])["message"])


if __name__ == "__main__":
    unittest.main()
