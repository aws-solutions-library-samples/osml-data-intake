#  Copyright 2024 Amazon.com, Inc. or its affiliates.

import argparse
import json
from typing import Dict, List, Optional

import boto3


class StreamCLI:
    def __init__(
        self,
        s3_uri: str,
        topic_arn: str,
        item_id: str,
        collection_id: Optional[str] = None,
        tile_server_url: Optional[str] = None,
    ) -> None:
        """
        Initializes the PublishMessage with S3 URI, SNS topic ARN, and start time.

        :param s3_uri: The S3 URI of the file to publish as a message to the SNS topic.
        :param topic_arn: The ARN of the SNS topic.
        :param item_id: The ID of the item.
        :param collection_id: The ID of the collection to place the item in.
        :param tile_server_url: The optional URL to the associated tile server.
        :returns: None
        """
        self.sns_client: boto3.client = boto3.client("sns")
        self.s3_resource: boto3.resource() = boto3.resource("s3")
        self.topic_arn: Optional[str] = topic_arn
        self.tile_server_url: Optional[str] = tile_server_url
        self.messages = self.build_messages(s3_uri, item_id, collection_id, tile_server_url)

    def publish_messages(self):
        """
        Publishes the SNSRequest to the specified SNS topic.
        """
        for message in self.messages:
            try:
                response = self.sns_client.publish(TopicArn=self.topic_arn, Message=json.dumps(message))
                print(f"Message published to topic {self.topic_arn}. Message ID: {response['MessageId']}")
            except Exception as err:
                print(f"Failed to publish message: {err}")
                raise

    def build_messages(self, s3_uri: str, item_id: str, collection_id: str, tile_server_url: str) -> List[Dict[str, str]]:
        """
        Construct a list of messages to submit to SNS Topic. If s3_uri is a bucket, add each object to the list.

        :param s3_uri: The S3 URI of the file / bucket to publish to
        :param item_id: The ID of the item, or if multiple items in a bucket, the ID prefix.
        :param collection_id: The ID of the collection to place the item(s) in.
        :param tile_server_url: The optional URL to the associated tile server.

        :returns: A list of formatted messages to be sent to an SNS topic
        """

        if not s3_uri.startswith("s3://"):
            raise ValueError("Invalid S3 URI")

        uri_parts = s3_uri[5:].split("/", 1)
        bucket_name = uri_parts[0]

        if len(uri_parts) == 1:
            messages = []
            bucket = self.s3_resource.Bucket(bucket_name)

            all_objects = bucket.objects.all()
            if all_objects:
                for idx, obj in enumerate(all_objects):
                    uri = f"s3://{bucket_name}/{obj.key}"
                    messages.append(self._build_message(item_id, uri, collection_id, tile_server_url))
            else:
                print(f"The bucket, {bucket_name}, is empty.")
            return messages
        else:
            return [self._build_message(item_id, s3_uri, collection_id, tile_server_url)]

    @staticmethod
    def _build_message(item_id: str, s3_uri: str, collection_id: str = None, tile_server_url: str = None) -> Dict[str, str]:
        message = {"image_uri": s3_uri, "item_id": item_id}
        if collection_id:
            message["collection_id"] = collection_id
        if tile_server_url:
            message["tile_server_url"] = tile_server_url
        return message

    def run(self) -> None:
        """
        Executes the main publishing and logging retrieval process.
        :returns: None
        """
        self.publish_messages(),


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publish an S3 URI to an SNS topic and collect Lambda logs.")
    parser.add_argument("--s3-uri", required=True, help="S3 URI to publish as the SNS message.")
    parser.add_argument("--topic-arn", required=True, help="SNS topic ARN to publish to.")
    parser.add_argument("--item-id", required=True, help="The ID for the item.")
    parser.add_argument("--collection-id", required=False, help="The collection to place the item in.")
    parser.add_argument("--tile-server-url", required=False, help="The base url to the Tile Server")

    args = parser.parse_args()

    sns_logger = StreamCLI(args.s3_uri, args.topic_arn, args.item_id, args.collection_id, args.tile_server_url)
    sns_logger.run()
