# Copyright 2024 Amazon.com, Inc. or its affiliates.

import asyncio
import json
from typing import Any, Dict

from stac_fastapi.opensearch.database_logic import AsyncSearchSettings, DatabaseLogic
from stac_fastapi.types.stac import Item

from .processor_base import ProcessorBase
from .utils import logger


class IngestProcessor(ProcessorBase):
    """
    A class to process STAC items from an SNS event source, integrated with OpenSearch
    database logic from stac_fastapi.opensearch.database_logic.
    """

    def __init__(self, message: str):
        """
        Initialize the STACProcessor with an OpenSearch client from AsyncSearchSettings.

        :param message: The incoming SNS request message.
        """
        self.database = DatabaseLogic(AsyncSearchSettings().create_client)
        self.stac_item = Item(**json.loads(message))

    async def process(self) -> Dict[str, Any]:
        """
        Process the incoming SNS message, download and process the image, and publish the results.

        :returns: A response indicating the status of the process.
        :raises Exception: Raised if there is an error during item ingestion.
        """
        try:
            # Here we assume 'item' includes necessary fields like 'id'
            logger.info(f'Creating STAC item with ID {self.stac_item["id"]}.')

            # Create a STAC item in the open search database
            await self.database.create_item(self.stac_item)

            # Return a success message
            return self.success_message("STAC item created successfully")
        except Exception as error:
            # Return a failure message with the stack trace
            return self.failure_message(error)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    The AWS Lambda handler function to process an event.

    :param event: The event payload contains the SNS message.
    :param context: The Lambda execution context (unused).
    :return: The response from the IngestProcessor process.
    """
    # Log the event payload to see the raw SNS message
    message = event["Records"][0]["Sns"]["Message"]
    return asyncio.get_event_loop().run_until_complete(IngestProcessor(message).process())
