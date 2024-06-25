#  Copyright 2023-2024 Amazon.com, Inc. or its affiliates.

import datetime
import json
import uuid

from stac_fastapi.types.stac import Item

from .image_data import ImageData
from .lambda_logger import logger
from .s3_manager import S3Manager
from .sns_manager import SNSManager


class STACManager:
    """
    A class to handle the creation of STAC items.

    :param sns_manager: An instance of SNSManager for publishing messages.
    :param s3_manager: An object containing the s3 metadata required for publishing.
    :param stac_catalog: The link to the catalog the STAC item is being sent to.
    """

    def __init__(self, sns_manager: SNSManager, s3_manager: S3Manager, stac_catalog: str = "") -> None:
        """
        Initialize a new StacManager instance.

        :param sns_manager: An instance of SNSManager for publishing messages.
        :param s3_manager: An object containing the s3 metadata required for publishing.
        :returns: None
        """
        self.sns_manager = sns_manager
        self.s3_manager = s3_manager
        self.stac_catalog = stac_catalog

    def publish_stac_item(self, image_data: ImageData, collection_id: str) -> None:
        """
        Create and publish a STAC item using the configured SNS manager.

        :param image_data: The image data associated with the processed image.
        :param collection_id: The collection to place the item in.
        :raises ClientError: If publishing to SNS fails.
        """
        logger.info("Creating STAC item.")
        stac_item = Item(
            **{
                "id": str(uuid.uuid4()),
                "collection": collection_id,
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": image_data.geo_polygon},
                "bbox": image_data.geo_bbox,
                "properties": {
                    "datetime": str(datetime.datetime.now(datetime.timezone.utc)),
                    "description": f"STAC Item for image {self.s3_manager.s3_url.url}",
                },
                "assets": {
                    "sourceImage": {
                        "href": f"s3://{self.s3_manager.s3_url.bucket}/{self.s3_manager.s3_url.key}",
                        "title": "Source Image",
                        "type": "image/tiff",
                    },
                    "processedAux": {
                        "href": f"s3://{self.s3_manager.output_bucket}/{self.s3_manager.s3_url.key}.aux",
                        "title": "Processed Auxiliary",
                        "type": "application/octet-stream",
                    },
                    "processedOvr": {
                        "href": f"s3://{self.s3_manager.output_bucket}/{self.s3_manager.s3_url.key}.ovr",
                        "title": "Processed Overview",
                        "type": "application/octet-stream",
                    },
                },
                "links": [{"href": self.stac_catalog, "rel": "self"}],
                "stac_version": "1.0.0",
            }
        )

        message = json.dumps(stac_item)
        logger.info(f"Publishing STAC item: {message}")
        self.sns_manager.publish_message(message)
