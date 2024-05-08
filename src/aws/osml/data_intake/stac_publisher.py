#  Copyright 2023-2024 Amazon.com, Inc. or its affiliates.
import datetime
import json
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError

from .image_data import ImageData
from .lambda_logger import logger
from .s3_manager import S3Manager


@dataclass
class Link:
    """
    Represents a link to other resources.

    :param href: The URL of the link.
    :param rel: The relationship of the linked resource.
    :param type: The media type of the linked resource (optional).
    :param title: A human-readable title for the linked resource (optional).
    """

    href: str
    rel: str
    type: str = ""
    title: str = ""


@dataclass
class Asset:
    """
    Represents a geospatial asset.

    :param href: The URL of the asset.
    :param title: A human-readable title for the asset.
    :param type: The media type of the asset.
    :param roles: The roles of the asset (optional).
    """

    href: str
    title: str
    type: str
    roles: List[str] = field(default_factory=list)


@dataclass
class STACItem:
    """
    Represents a STAC (SpatioTemporal Asset Catalog) Item.

    :param id: The unique identifier for the STAC item.
    :param type: The type of the STAC item (typically "Feature").
    :param geometry: The geometric representation of the item.
    :param bbox: The bounding box of the item.
    :param properties: Additional properties of the item.
    :param assets: The assets associated with the item.
    :param links: Links to other resources.
    :param stac_version: The STAC version used.
    :param stac_extensions: Any STAC extensions used (optional).
    """

    id: str
    type: str
    geometry: Dict[str, Any]
    bbox: List[float]
    properties: Dict[str, Any]
    assets: Dict[str, Asset]
    links: List[Link]
    stac_version: str
    stac_extensions: List[str] = field(default_factory=list)


class StacPublisher:
    """
    A class to handle the creation and publishing of STAC items to an SNS topic.

    :param output_topic: The ARN of the SNS topic where STAC items will be published.
    """

    def __init__(self, output_topic: str) -> None:
        """
        Initialize a new StacPublisher instance.

        :param output_topic: The ARN of the SNS topic where STAC items will be published.
        :param logger: The configured logger instance
        :returns: None
        """
        self.sns_client = boto3.client("sns")
        self.output_topic = output_topic

    def publish_stac_item(self, s3_manager: S3Manager, image_data: ImageData) -> None:
        """
        Create and publish a STAC item to the configured SNS topic.

        :param s3_manager: An object containing the s3 metadata required for publishing.
        :param image_data: The image data associated with the processed image.
        :raises ClientError: If publishing to SNS fails.
        """
        logger.info("Creating STAC item.")
        stac_item = STACItem(
            id=str(uuid.uuid4()),
            type="Feature",
            geometry={"type": "Polygon", "coordinates": image_data.geo_polygon},
            bbox=image_data.geo_bbox,
            properties={
                "datetime": str(datetime.datetime.now(datetime.timezone.utc)),
                "description": f"STAC Item for image {s3_manager.s3_url.url}",
            },
            assets={
                "sourceImage": Asset(
                    href=f"s3://{s3_manager.s3_url.bucket}/{s3_manager.s3_url.key}", title="Source Image", type="image/tiff"
                ),
                "processedAux": Asset(
                    href=f"s3://{s3_manager.output_bucket}/{s3_manager.s3_url.key}.aux",
                    title="Processed Auxiliary",
                    type="application/octet-stream",
                ),
                "processedOvr": Asset(
                    href=f"s3://{s3_manager.output_bucket}/{s3_manager.s3_url.key}.ovr",
                    title="Processed Overview",
                    type="application/octet-stream",
                ),
            },
            links=[Link(href="http://example.com/catalog.json", rel="self")],
            stac_version="1.0.0",
        )

        message = json.dumps(asdict(stac_item))
        logger.info(f"Publishing STAC item: {message}")
        try:
            self.sns_client.publish(TopicArn=self.output_topic, Message=message, Subject="New STAC Item")
        except ClientError as err:
            logger.error(f"Failed to publish STAC item: {err}")
            raise err
