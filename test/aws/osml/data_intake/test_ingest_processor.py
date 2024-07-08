# Copyright 2024 Amazon.com, Inc. or its affiliates.

import asyncio
import json
import os
import unittest
from unittest.mock import patch

import boto3
from moto import mock_aws


@mock_aws()
@patch.dict(
    os.environ,
    {
        "STAC_FASTAPI_TITLE": "stac-fastapi-opensearch",
        "STAC_FASTAPI_DESCRIPTION": "A STAC FastAPI with an OpenSearch backend",
        "STAC_FASTAPI_VERSION": "2.4.1",
        "RELOAD": "true",
        "ENVIRONMENT": "local",
        "WEB_CONCURRENCY": "10",
        "ES_HOST": "test-host",
        "ES_PORT": "443",
        "ES_USE_SSL": "true",
        "ES_VERIFY_CERTS": "true",
        "STAC_FASTAPI_ROOT_PATH": "data-catalog",
    },
)
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

    @patch("stac_fastapi.opensearch.config.AsyncOpenSearch")
    async def test_handler_success(self, mock_opensearch):
        """
        Test the handler function for a successful scenario.

        Args:
            mock_opensearch (AsyncMock): Mock of the AsyncOpenSearch client.

        Returns:
            None: Asserts if the response status code is 200 and the body contains a success message.
        """
        from aws.osml.data_intake.ingest_processor import handler

        mock_opensearch.create_item = asyncio.Future()
        mock_opensearch.create_item.set_result(None)  # Simulate success

        event = self.sns_event()
        response = handler(event, None)

        self.assertEqual(response["statusCode"], 200)
        self.assertIn("successfully", json.loads(response["body"]))

    @patch("stac_fastapi.opensearch.config.AsyncOpenSearch")
    async def test_handler_failure(self, mock_opensearch):
        """
        Test the handler function for a failure scenario.
        """
        from aws.osml.data_intake.ingest_processor import handler

        mock_opensearch.create_item = asyncio.Future()
        mock_opensearch.create_item.set_exception(Exception("Database error"))

        event = self.sns_event()
        response = handler(event, None)

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Database error", json.loads(response["body"]))


if __name__ == "__main__":
    unittest.main()
