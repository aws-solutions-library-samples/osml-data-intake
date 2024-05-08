#  Copyright 2024 Amazon.com, Inc. or its affiliates.

import json
import os
from typing import Any, Dict

from .image_data import ImageData
from .lambda_logger import logger
from .s3_manager import S3Manager, S3Url
from .stac_publisher import StacPublisher

# Retrieve environment variables
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]
OUTPUT_TOPIC = os.environ["OUTPUT_TOPIC"]


class ImageProcessor:
    """
    Manages the entire image processing workflow in a serverless environment.
    """

    def __init__(self, message: str) -> None:
        """
        Initialize an ImageProcessingLambda instance.
        """
        self.s3_manager = S3Manager(OUTPUT_BUCKET)
        self.stac_publisher = StacPublisher(OUTPUT_TOPIC)
        self.s3_url = S3Url(message)

    def process(self) -> Dict[str, Any]:
        """
        Process the incoming SNS message, download and process the image, and publish the results.
        :return: A response indicating the status of the process.
        """
        try:
            # Download the source image
            self.s3_manager.download_file(self.s3_url)

            # Create the image metadata files
            image_data = ImageData(self.s3_manager.file_path)

            # Upload them to the S3
            self.s3_manager.upload_file(image_data.ovr_file, ".OVR")
            self.s3_manager.upload_file(image_data.aux_file, ".AUX")

            # Publish the STAC item to the SNS topic
            self.stac_publisher.publish_stac_item(self.s3_manager, image_data)

            # Return a response indicating success
            logger.info("Message processed successfully")
            return self.success_message()

        except Exception as err:
            # Return a response indicating failure
            logger.error(err)
            return self.failure_message(err)

    @staticmethod
    def success_message() -> Dict[str, Any]:
        """
        Returns a success message in the form of a dictionary, intended for an HTTP response.

        :returns: A dictionary with 'statusCode' set to 200 and a 'body' containing a success message.
        """
        return {"statusCode": 200, "body": json.dumps("Message processed successfully")}

    @staticmethod
    def failure_message(e: Exception) -> Dict[str, Any]:
        """
        Returns an error message in the form of a dictionary, intended for an HTTP response.

        :param e: The exception that triggered the failure.
        :returns: A dictionary with 'statusCode' set to 400 and a 'body' containing the error message.
        """
        return {"statusCode": 400, "body": json.dumps(str(e))}
