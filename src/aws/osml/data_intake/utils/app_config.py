#  Copyright 2024 Amazon.com, Inc. or its affiliates.

import json
import os
from dataclasses import dataclass, field
from typing import Dict

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
    bulk_s3_uri = os.getenv("S3_URI")
    bulk_input_path = os.getenv("S3_INPUT_PATH")
    bulk_output_path = os.getenv("S3_OUTPUT_PATH")
    bulk_output_bucket = os.getenv("S3_OUTPUT_BUCKET")
    bulk_stac_endpoint = os.getenv("STAC_ENDPOINT")
    bulk_collection_id = os.getenv("COLLECTION_ID")
    bulk_max_workers = int(os.getenv("THREAD_WORKERS", 1))
    bulk_enable_debugging = os.getenv("ENABLE_DEBUGGING")
    stac_post_processing_topic: str = os.getenv("STAC_POST_PROCESSING_TOPIC_ARN", None)
    post_processing_asset_data_titles: list = field(
        default_factory=lambda: json.loads(os.getenv("POST_PROCESS_ASSET_DATA_TITLES", "[]"))
    )


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


def get_minimal_collection_dict(collection_id: str) -> Dict:
    return {
        "type": "Collection",
        "stac_version": "1.0.0",
        "id": collection_id,
        "description": f"{collection_id} STAC Collection",
        "license": "",
        "extent": {"spatial": {"bbox": [[-180.0, -90.0, 180.0, 90.0]]}, "temporal": {"interval": []}},
        "links": [{"href": "", "rel": "self"}],
    }
