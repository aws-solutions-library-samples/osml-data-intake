#  Copyright 2024 Amazon.com, Inc. or its affiliates.

import json
import os
from typing import Any, Dict

from src.aws.osml.data_intake.data.image_data import ImageData
from src.aws.osml.data_intake.managers.s3_manager import S3Manager, S3Url
from src.aws.osml.data_intake.managers.sns_manager import SNSManager, SNSRequest
from src.aws.osml.data_intake.managers.stac_manager import STACManager
from src.aws.osml.data_intake.processors.processor_base import ProcessorBase

# Retrieve environment variables
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]
OUTPUT_TOPIC = os.getenv("OUTPUT_TOPIC")


class ImageProcessor(ProcessorBase):
    """
    Manages the entire image processing workflow in a serverless environment.

    :param message: The incoming SNS request message.
    """

    def __init__(self, message: str) -> None:
        """
        Initialize an ImageProcessor instance.

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

            # Generate and upload thumbnail
            thumbnail_file = image_data.generate_thumbnail()
            self.s3_manager.upload_file(thumbnail_file, ".PNG")

            # Publish the STAC item to the SNS topic
            self.stac_manager.publish_image(image_data, self.sns_request.collection_id)

            # Clean up the GDAL dataset
            image_data.clean_dataset()

            # Return a response indicating success
            return self.success_message("Message processed successfully")

        except Exception as err:
            # Return a response indicating failure
            return self.failure_message(err)
