#  Copyright 2023-2024 Amazon.com, Inc. or its affiliates.

import logging


def get_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """
    Configures the logging setup for AWS Lambda.

    :param name: The name of the logger.
    :param level: The logging level to be used if no other handler is already configured. Default is INFO.

    :returns: The configured logger instance.
    """
    lambda_logger = logging.getLogger(name)
    root_logger = logging.getLogger()

    # Check if the root logger already has any handlers
    if root_logger.hasHandlers():
        root_logger.setLevel(level)
    else:
        logging.basicConfig(level=level)

    return lambda_logger


logger = get_logger()
