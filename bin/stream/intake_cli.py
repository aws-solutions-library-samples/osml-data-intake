#  Copyright 2024 Amazon.com, Inc. or its affiliates.


import argparse
import json
import time
from datetime import datetime, timezone
from typing import Optional

import boto3


class RunCLI:
    def __init__(self, s3_uri: str, topic_arn: str, collection_id: Optional[str] = None, monitor_logs: bool = False) -> None:
        """
        Initializes the PublishMessage with S3 URI, SNS topic ARN, and start time.

        :param s3_uri: The S3 URI of the file to publish as a message to the SNS topic.
        :param topic_arn: The ARN of the SNS topic.
        :param collection_id: The collection ID to associate with the message.
        :param monitor_logs: Whether to monitor logs or not.

        :returns: None
        """
        self.sns_client: boto3.client = boto3.client("sns")
        self.logs_client: boto3.client = boto3.client("logs")
        self.lambda_client: boto3.client = boto3.client("lambda")
        self.s3_resource: boto3.resource = boto3.resource("s3")
        self.topic_arn: Optional[str] = topic_arn
        self.start_time: Optional[datetime] = datetime.now(timezone.utc)
        self.lambda_log_group = Optional[str]
        self.message: str = self.check_s3_uri(s3_uri, collection_id)
        self.monitor_logs = monitor_logs

    def check_s3_uri(self, s3_uri: str, collection_id: str):
        """
        Construct a message to submit to SNS Topic, if s3_uri is a bucket, construct a list of
            objects to be sent to SNS topic.

        :param s3_uri: The S3 URI of the file / bucket to publish to

        :returns: A formatted message to be sent to SNS topic
        """
        if not s3_uri.startswith("s3://"):
            raise ValueError("Invalid S3 URI")

        uri_parts = s3_uri[5:].split("/", 1)
        bucket_name = uri_parts[0]

        if len(uri_parts) == 1:
            message = []
            bucket = self.s3_resource.Bucket(bucket_name)

            all_objects = bucket.objects.all()
            if all_objects:
                for obj in all_objects:
                    uri = f"s3://{bucket_name}/{obj.key}"
                    if collection_id:
                        message.append({"image_uri": uri, "collection_id": collection_id})
            else:
                print(f"The bucket, {bucket_name}, is empty.")

            return message
        else:
            if collection_id:
                return [{"image_uri": s3_uri, "collection_id": collection_id}]

            return [{"image_uri": s3_uri}]

    def publish_s3_uri(self):
        """
        Publishes the SNSRequest to the specified SNS topic.
        """
        for message in self.messages:
            try:
                response = self.sns_client.publish(TopicArn=self.topic_arn, Message=json.dumps(message))
                print(f"Message published to topic {self.topic_arn}. Message ID: {response['MessageId']}")
                return response["MessageId"]
            except Exception as err:
                print(f"Failed to publish message: {err}")
                raise

    def get_lambda_log_group(self) -> Optional[None]:
        """
        Fetches the log group name of the Lambda function subscribed to the specified SNS topic.

        :returns: Log group name of the Lambda function, or None if not found.
        """
        response = self.sns_client.list_subscriptions_by_topic(TopicArn=self.topic_arn)
        for subscription in response["Subscriptions"]:
            if subscription["Protocol"] == "lambda":
                lambda_arn = subscription["Endpoint"]
                lambda_name = lambda_arn.split(":")[-1]
                self.lambda_log_group = f"/aws/lambda/{lambda_name}"
                print(f"Lambda log group name: {self.lambda_log_group}")
                return None
        raise ValueError("No Lambda function subscribed to this SNS topic.")

    def get_lambda_logs(self) -> bool:
        """
        Fetches and displays logs from the Lambda function.

        :returns: Boolean saying whether logs were found
        """
        log_streams = self.logs_client.describe_log_streams(
            logGroupName=self.lambda_log_group, orderBy="LastEventTime", descending=True
        )["logStreams"]

        for log_stream in log_streams:
            stream_name = log_stream["logStreamName"]
            events = self.logs_client.get_log_events(
                logGroupName=self.lambda_log_group,
                logStreamName=stream_name,
                startFromHead=True,
                startTime=int(self.start_time.timestamp()) * 1000,
                endTime=int(datetime.now(timezone.utc).timestamp()) * 1000,
            )["events"]
            if len(events) > 0:
                for event in events:
                    print(event["message"].strip())
                return True

            return False

    def fetch_logs(self, poll_interval: int = 5, timeout: int = 300) -> None:
        """
        Waits for the Lambda function to process the SNS message and then fetches logs.

        :param poll_interval: Time (in seconds) to wait between polling attempts.
        :param timeout: Maximum waiting time (in seconds) before giving up.
        :returns: None
        """
        log_group = self.lambda_log_group
        start_time = time.time()
        while time.time() - start_time < timeout:
            latest_logs = self.logs_client.describe_log_streams(
                logGroupName=log_group, orderBy="LastEventTime", descending=True
            )["logStreams"]
            if latest_logs:
                break
            print(f"Waiting for logs, polling again in {poll_interval} seconds...")
            time.sleep(poll_interval)

        while time.time() - start_time < timeout:
            if self.get_lambda_logs():
                break
            else:
                print(f"Waiting for logs, polling again in {poll_interval} seconds...")
                time.sleep(poll_interval)

    def run(self) -> None:
        """
        Executes the main publishing and logging retrieval process.
        :returns: None
        """
        self.publish_s3_uri(),
        if self.monitor_logs:
            self.get_lambda_log_group()
            self.fetch_logs()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publish an S3 URI to an SNS topic and collect Lambda logs.")
    parser.add_argument("--s3-uri", required=True, help="S3 URI to publish as the SNS message.")
    parser.add_argument("--topic-arn", required=True, help="SNS topic ARN to publish to.")
    parser.add_argument("--collection-id", required=False, help="The collection to place the item in.")
    parser.add_argument("--monitor-logs", action="store_true", help="Enable to monitor the Lambda Logs")

    args = parser.parse_args()

    sns_logger = RunCLI(args.s3_uri, args.topic_arn, args.collection_id, args.monitor_logs)
    sns_logger.run()
