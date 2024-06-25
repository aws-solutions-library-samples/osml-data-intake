#  Copyright 2024 Amazon.com, Inc. or its affiliates.

import json
import os
import traceback
from typing import Any, Dict

from .image_data import ImageData
from .lambda_logger import logger
from .s3_manager import S3Manager, S3Url
from .sns_manager import SNSManager, SNSRequest
from .stac_manager import STACManager

# Retrieve environment variables
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]
OUTPUT_TOPIC = os.getenv("OUTPUT_TOPIC")


class ImageProcessor:
    """
    Manages the entire image processing workflow in a serverless environment.

    :param message: The incoming SNS request message.
    """

    def __init__(self, message: str) -> None:
        """
        Initialize an ImageProcessingLambda instance.

        :param message: The incoming SNS request message.
        :returns: None
        """
        self.s3_manager = S3Manager(OUTPUT_BUCKET)
        self.sns_manager = SNSManager(OUTPUT_TOPIC)
        self.stac_manager = STACManager(self.sns_manager, self.s3_manager)
        self.sns_request = SNSRequest(**json.loads(message))

    def process(self) -> Dict[str, Any]:
        """
        Process the incoming SNS message, download and process the image, and publish the results.

        :returns: A response indicating the status of the process.
        """
        try:
            # Extract the S3 information from the URI
            s3_url = S3Url(self.sns_request.image_uri)

            # Download the source image
            file_path = self.s3_manager.download_file(s3_url)

            # Create the image metadata files
            image_data = ImageData(file_path)

            # Generate and upload aux file
            aux_file = image_data.generate_aux_file()
            self.s3_manager.upload_file(aux_file, ".AUX")

            # Generate and upload .ovr file
            ovr_file = image_data.generate_ovr_file()
            self.s3_manager.upload_file(ovr_file, ".OVR")

            # Publish the STAC item to the SNS topic
            self.stac_manager.publish_stac_item(image_data, self.sns_request.collection_id)

            # Clean up the GDAL dataset
            image_data.clean_dataset()

            # Return a response indicating success
            return self.success_message("Message processed successfully")

        except Exception as err:
            # Return a response indicating failure
            return self.failure_message(err)

    @staticmethod
    def success_message(message: str) -> Dict[str, Any]:
        """
        Returns a success message in the form of a dictionary, intended for an HTTP response.

        :param message: The success message to send when complete.
        :returns: A dictionary with 'statusCode' set to 200 and a 'body' containing a success message.
        """
        logger.info(message)
        return {"statusCode": 200, "body": json.dumps(message)}

    @staticmethod
    def failure_message(e: Exception) -> Dict[str, Any]:
        """
        Returns an error message in the form of a dictionary, including a stack trace, intended for an HTTP response.

        :param e: The exception that triggered the failure.
        :returns: A dictionary with 'statusCode' set to 400 and a 'body' containing the error message and stack trace.
        """
        # Log the error and stack trace
        stack_trace = traceback.format_exc()
        logger.error(f"Error creating STAC items: {e}\nStack trace: {stack_trace}")

        # Return the error message and stack trace in the response
        error_response = {"message": str(e), "stack_trace": stack_trace.splitlines()}
        return {"statusCode": 400, "body": json.dumps(error_response)}
