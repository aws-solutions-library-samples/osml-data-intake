#  Copyright 2023-2024 Amazon.com, Inc. or its affiliates.

from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError

from .lambda_logger import logger


@dataclass
class SNSRequest:
    image_uri: str


class SNSManager:
    """
    A helper class to manage interactions with AWS SNS.

    :param output_topic: The ARN of the SNS topic where messages are published.
    """

    def __init__(self, output_topic: str) -> None:
        """
        Initialize a new SNSManager instance.

        :param output_topic: The ARN of the SNS topic where messages will be published.
        :returns: None
        """
        self.sns_client = boto3.client("sns")
        self.output_topic = output_topic

    def publish_message(self, message: str, subject: str = "New STAC Item") -> None:
        """
        Publish a message to the configured SNS topic.

        :param message: The message to be published.
        :param subject: The subject of the message.
        :raises ClientError: If publishing to SNS fails.
        """
        try:
            self.sns_client.publish(TopicArn=self.output_topic, Message=message, Subject=subject)
        except ClientError as err:
            logger.error(f"Failed to publish message: {err}")
            raise err
