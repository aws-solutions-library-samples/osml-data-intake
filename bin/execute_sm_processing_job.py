#  Copyright 2024 Amazon.com, Inc. or its affiliates.

import argparse
import logging
from secrets import token_hex

import boto3


class SM_CONFIG:
    """
    Configuration settings for a SageMaker Processing Job.

    This class defines constants used to configure a SageMaker Processing Job
    for data processing tasks. The constants specify the input and output paths,
    data types, distribution modes, and other settings required by SageMaker.

    Attributes:
        LOCAL_INPUT_PATH (str): Local path where input data is downloaded.
        INPUT_DATA_TYPE (str): Type of input data source (e.g., S3Prefix).
        INPUT_MODE (str): Mode for sending input data to the processing job.
        INPUT_DATA_DISTRIBUTION_TYPE (str): How input data is distributed across instances.
        LOCAL_OUTPUT_PATH (str): Local path where output data is written.
        OUTPUT_UPLOAD_MODE (str): Mode for uploading output data from the processing job.
        MAX_RUNTIME_IN_SECONDS (int): Maximum runtime in seconds for the processing job.
    """

    LOCAL_INPUT_PATH = "/opt/ml/processing/input"
    INPUT_DATA_TYPE = "S3Prefix"
    INPUT_MODE = "Pipe"
    INPUT_DATA_DISTRIBUTION_TYPE = "ShardedByS3Key"

    LOCAL_OUTPUT_PATH = "/opt/ml/processing/output"
    OUTPUT_UPLOAD_MODE = "Continuous"

    MAX_RUNTIME_IN_SECONDS = 3600


def get_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """
    Configures the logging setup for AWS Lambda.

    :param name: The name of the logger.
    :param level: The logging level to be used if no other handler is already configured. Default is INFO.

    :returns: The configured logger instance.
    """
    logger = logging.getLogger(name)
    root_logger = logging.getLogger()

    # Check if the root logger already has any handlers
    if root_logger.hasHandlers():
        root_logger.setLevel(level)
    else:
        logging.basicConfig(level=level)

    return logger


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments for the SageMaker Processing Job.

    This function uses the argparse module to define and parse command-line arguments
    required for configuring and executing a SageMaker Processing Job. The arguments
    include the S3 input and output buckets, STAC endpoint, collection ID, instance
    types and counts, Docker image URI, IAM role, and AWS region.

    :returns  A namespace object containing the parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Process data from an S3 bucket, generate aux/ovr files, and add to a STAC catalog."
    )
    parser.add_argument("--s3-uri", required=True, help="S3 bucket to process and add to STAC Catalog")
    parser.add_argument("--output-bucket", required=True, help="To store generated OVR / AUX files")
    parser.add_argument("--stac-endpoint", required=True, help="STAC endpoint URL to add processed data")
    parser.add_argument(
        "--collection-id", default="OSML", help="The ID of the STAC collection where the processed data will be added."
    )
    parser.add_argument(
        "--cluster-instance-count", default=1, type=int, help="Number of instances to use for the processing job"
    )
    parser.add_argument("--cluster-instance-type", default="ml.m5.xlarge", help="Instance type for the processing job")
    parser.add_argument("--cluster-volume-size", default=10, type=int, help="Cluster volume size (in gb) storage")
    parser.add_argument(
        "--image-uri", required=True, help="The docker container which is responsible for processing the job"
    )
    parser.add_argument("--role-arn", required=True, help="ARN of the IAM role for the sagemaker processing job")
    parser.add_argument("--region", required=True, help="AWS region.", default="us-west-2")

    return parser.parse_args()


def execute_sm_processing_job() -> None:
    """
    Execute a SageMaker Processing Job to process data from an S3 bucket.

    This function creates and executes a SageMaker Processing Job to process data from an
    S3 bucket, generate auxiliary files (e.g., OVR, AUX), and add the processed data to a
    STAC (SpatioTemporal Asset Catalog) catalog.

    The function parses command-line arguments to configure the Processing Job, including
    the S3 input and output buckets, STAC endpoint, collection ID, instance types and counts,
    and IAM role. It then creates the necessary input and output configurations, and submits
    the Processing Job to SageMaker using the specified parameters.

    The Processing Job runs a docker container that processes the input data and generates
    the aux/ovr files, which are stored in the specified output bucket. The processed data
    is then added to the STAC catalog at the specified endpoint and collection.

    :returns None
    """
    logger = get_logger()
    args = parse_arguments()

    # Setting up the parameter values
    s3_uri = args.s3_uri
    output_bucket = args.output_bucket
    instance_count = args.cluster_instance_count
    instance_type = args.cluster_instance_type
    instance_size = args.cluster_volume_size
    role_arn = args.role_arn
    region = args.region
    collection_id = args.collection_id
    stac_endpoint = args.stac_endpoint
    image_uri = args.image_uri

    sagemaker_client = boto3.client("sagemaker", region)

    input_config = {
        "InputName": "input",
        "S3Input": {
            "S3Uri": s3_uri,
            "LocalPath": SM_CONFIG.LOCAL_INPUT_PATH,
            "S3DataType": SM_CONFIG.INPUT_DATA_TYPE,
            "S3InputMode": SM_CONFIG.INPUT_MODE,
            "S3DataDistributionType": SM_CONFIG.INPUT_DATA_DISTRIBUTION_TYPE,
        },
    }
    output_config = {
        "OutputName": "output",
        "S3Output": {
            "S3Uri": output_bucket,
            "LocalPath": SM_CONFIG.LOCAL_OUTPUT_PATH,
            "S3UploadMode": SM_CONFIG.OUTPUT_UPLOAD_MODE,
        },
    }

    job_name = f"bulk-ingest-job-{token_hex(16)}"

    cluster_config = {
        "InstanceCount": instance_count,
        "InstanceType": instance_type,
        "VolumeSizeInGB": instance_size,
    }

    job_name = sagemaker_client.create_processing_job(
        ProcessingInputs=[input_config],
        ProcessingOutputConfig={"Outputs": [output_config]},
        ProcessingJobName=job_name,
        ProcessingResources={"ClusterConfig": cluster_config},
        StoppingCondition={"MaxRuntimeInSeconds": SM_CONFIG.MAX_RUNTIME_IN_SECONDS},
        AppSpecification={
            "ImageUri": image_uri,
            "ContainerEntrypoint": [
                "/entry.sh",
                "/bin/bash",
                "-c",
                "python3 osml-data-intake/bin/bulk_ingest/process_image.py",
            ],
        },
        NetworkConfig={"EnableNetworkIsolation": False},
        RoleArn=role_arn,
        Environment={
            "S3_INPUT_PATH": SM_CONFIG.LOCAL_INPUT_PATH,
            "S3_OUTPUT_PATH": SM_CONFIG.LOCAL_OUTPUT_PATH,
            "S3_OUTPUT_BUCKET": output_bucket,
            "STAC_ENDPOINT": stac_endpoint,
            "COLLECTION_ID": collection_id,
        },
    )

    logger.info(f"The job has been executed it: {job_name}")


if __name__ == "__main__":
    execute_sm_processing_job()
