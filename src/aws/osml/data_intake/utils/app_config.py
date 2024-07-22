#  Copyright 2024 Amazon.com, Inc. or its affiliates.

import os
from dataclasses import dataclass

from botocore.config import Config


@dataclass
class ServiceConfig:
    """
    ServiceConfig is a dataclass meant to house the high-level configuration settings required for Data Intake Bulk to
    operate that are provided through ENV variables. Note that required env parameters are enforced by the implied
    schema validation as os.environ[] is used to fetch the values. Optional parameters are fetched using, os.getenv(),
    which returns None.

    The data schema is defined as follows:
    aws_region:  (str) The AWS region where the Bulk Ingest is deployed.
    sts_arn: (str) The ARN of the STS role to assume for running the Bulk Ingest.
    max_conn_pool: (int) The maximum number of connections to maintain in the connection pool.
    """

    aws_region: str = os.getenv("AWS_DEFAULT_REGION", "us-west-2")
    sts_arn: str = os.getenv("STS_ARN", None)
    max_conn_pool: str = os.getenv("NUMBER_OF_CONN_POOL", 500)


@dataclass
class BotoConfig:
    """
    BotoConfig is a dataclass meant to vend our application the set of boto client configurations required for
        Data Intake Bulk

    The data schema is defined as follows:
    default:  (Config) the standard boto client configuration
    """

    default: Config = Config(
        region_name=ServiceConfig.aws_region,
        retries={"max_attempts": 15, "mode": "standard"},
        max_pool_connections=int(ServiceConfig.max_conn_pool),
    )
