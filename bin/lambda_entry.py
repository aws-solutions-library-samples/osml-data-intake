#  Copyright 2023-2024 Amazon.com, Inc. or its affiliates.

from typing import Any, Dict

from src.aws.osml.data_intake.image_processor import ImageProcessor


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    The AWS Lambda handler function to process an event.

    :param event: The event payload containing the SNS message.
    :param context: The Lambda execution context (unused).
    :return: The response from the ImageProcessingLambda process.
    """
    # Log the event payload to see the raw SNS message
    message = event["Records"][0]["Sns"]["Message"]
    return ImageProcessor(message).process()
