#  Copyright 2024 Amazon.com, Inc. or its affiliates.

import argparse
import json
import logging
import os
import sys
from secrets import token_hex
from typing import Any, Dict, List

import boto3

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class S3_Bulk_Manager:
    def __init__(self, input_bucket: str, output_bucket: str, region: str, instance_count: int) -> None:
        """
        Initialize the S3_Bulk_Manager class.

        :param input_bucket: The Amazon S3 URI (bucket and prefix) where the input data is located.
        :param output_bucket: The Amazon S3 URI (bucket and prefix) where the output data should be stored.
        :param region: The AWS region where the resources (S3 buckets, etc.) are located.
        :param instance_count: The number of instances to use for the SageMaker Processing Job.

        :returns: None
        """
        self.region = region
        self.input_bucket_name, self.input_prefix = self._parse_s3_uri(input_bucket)
        self.output_bucket_name, self.output_prefix = self._parse_s3_uri(output_bucket)
        self.s3_client = boto3.client("s3", region_name=region)
        self.instance_count = instance_count
        self.object_count = 0
        self.manifest_filename = []
        self.imagery_extensions = (".ntf", ".nitf", ".tif", ".tiff")

    def _parse_s3_uri(self, s3_uri: str) -> tuple:
        """
        Parse the S3 URI to extract the bucket name and prefix.

        :param s3_uri: The S3 URI to parse.
        :returns: A tuple containing the bucket name and prefix.
        """
        parts = s3_uri.split("//")[1].split("/", 1)
        bucket_name = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""
        return bucket_name, prefix

    def count_objects(self) -> None:
        """
        Count the total number of objects (files) in the input S3 bucket
        with specific imagery format extensions.

        :returns: None
        """
        logger.info("Fetching Objects count, this will take a moment...")
        paginator = self.s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.input_bucket_name, Prefix=self.input_prefix)

        object_count = 0

        for page in pages:
            if "Contents" in page:
                for obj in page["Contents"]:
                    if obj["Key"].lower().endswith(self.imagery_extensions) and "_preview" not in obj["Key"].lower():
                        object_count += 1

        logger.info(f"Completed, total # of objects: {object_count}")

        self.object_count = object_count

    def create_and_upload_manifest_files(self) -> None:
        """
        Create and upload manifest files containing the S3 URIs of the objects to be processed.

        The manifest files are created based on the total number of objects and the specified instance count
        for the SageMaker Processing Job. Each manifest file contains a subset of the objects, distributed
        evenly across the instances.

        :returns: None
        """
        paginator = self.s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.input_bucket_name, Prefix=self.input_prefix)

        # Calculate how many objects each instance should handle
        objects_per_instance_per_file = self.object_count // self.instance_count
        remainder = self.object_count % self.instance_count

        current_manifest = []
        count = 0
        manifest_index = 1

        logger.info("Creating manifest files...")

        for page in pages:
            if "Contents" in page:
                for obj in page["Contents"]:
                    if obj["Key"].lower().endswith(self.imagery_extensions) and "_preview" not in obj["Key"].lower():
                        current_manifest.append({"S3Uri": f"s3://{self.input_bucket_name}/{obj['Key']}"})
                        count += 1
                        if count >= objects_per_instance_per_file + (1 if remainder > 0 else 0):
                            manifest_filename = f"manifest_file_{manifest_index}.json"
                            self._save_and_upload_manifest(manifest_filename, current_manifest)
                            current_manifest = []
                            count = 0
                            manifest_index += 1
                            remainder -= 1  # Reduce the remainder after creating a manifest

        if current_manifest:
            manifest_filename = f"manifest_file_{manifest_index}.json"
            self._save_and_upload_manifest(manifest_filename, current_manifest)

    def _save_and_upload_manifest(self, manifest_filename: str, manifest: List[str]) -> None:
        """
        Save the manifest file locally and upload it to the input S3 bucket. Once uploaded,
        delete the manifest file from the local disk.

        :param manifest_filename: The name of the manifest file.
        :param manifest: The list of S3 URIs to be included in the manifest file.

        :returns: None
        """
        with open(manifest_filename, "w") as f:
            json.dump(manifest, f)

        s3_key = f"{self.output_prefix}/bulk_{manifest_filename}" if self.output_prefix else f"bulk_{manifest_filename}"
        manifest_file = f"s3://{self.output_bucket_name}/{s3_key}"

        self.s3_client.upload_file(manifest_filename, self.output_bucket_name, s3_key)
        self.manifest_filename.append(manifest_file)

        logger.info(f"Manifest {manifest_filename} saved to {manifest_file}")

        os.remove(manifest_filename)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments for the SageMaker Processing Job.

    This function uses the argparse module to define and parse command-line arguments
    required for configuring and executing a SageMaker Processing Job. The arguments
    include the S3 input and output buckets, and AWS Regions.

    :returns: A namespace object containing the parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Process data from an S3 bucket, generate aux/ovr files, and add to a STAC catalog."
    )
    parser.add_argument("--s3-uri", required=True, help="S3 bucket to process and add to STAC Catalog")
    parser.add_argument("--output-bucket", required=True, help="To store generated OVR / AUX files")
    parser.add_argument("--region", required=True, default="us-west-2", help="Provide AWS Region to execute the job in")
    parser.add_argument("--verbose", required=False, action="store_true", help="Enable DEBUGGING logs")

    return parser.parse_args()


def get_vpc_details(region: str) -> Dict[str, Any]:
    """
    Get the VPC details for the OpenSearch domain

    :param region: The AWS region where the OpenSearch domain is located.

    :returns: A dictionary containing the security group IDs and subnet IDs for the VPC.
    """
    oss_client = boto3.client("opensearch", region)
    list_response = oss_client.list_domain_names()
    domains = [domain["DomainName"] for domain in list_response["DomainNames"]]
    if not domains:
        logger.info("No OpenSearch domains found.")
        return

    logger.info("Available OpenSearch domains:")
    for idx, domain in enumerate(domains):
        logger.info(f"{idx + 1}. {domain}")

    choice = int(input("Enter the number of the OpenSearch domain to use: ")) - 1
    if choice < 0 or choice >= len(domains):
        logger.info("Invalid choice.")
        return

    domain_name = domains[choice]
    domain_details = oss_client.describe_domain(DomainName=domain_name)

    domain_endpoint = domain_details["DomainStatus"]["Endpoints"]["vpc"]
    vpc_options = domain_details["DomainStatus"].get("VPCOptions", {})

    logger.info(f"Domain: {domain_name}")
    logger.info(f"Endpoint: {domain_endpoint}")

    subnet_ids = vpc_options["SubnetIds"]
    security_groups_id = vpc_options["SecurityGroupIds"]

    logger.info(f"Subnets: {subnet_ids} / SecurityGroupIds: {security_groups_id}")

    return {"SecurityGroupIds": security_groups_id, "Subnets": subnet_ids}


def execute_sm_processing_job() -> None:
    """
    Executes a SageMaker Processing Job for bulk ingestion of overhead imagery data.

    This function performs the following steps:
        1. Parses command-line arguments for input and output S3 buckets, and AWS region.
        2. Loads configuration settings from a JSON file.
        3. Retrieves VPC details if not provided in the configuration.
        4. Creates an S3 Bulk Manager instance to count objects and generate manifest files.
        5. Submits a SageMaker Processing Job for each manifest file, with the specified configurations.
        6. logger.infos the job name, status code, and ARN for each submitted job.

    The Processing Job runs a Docker container that ingests the imagery data from the input S3 bucket,
    processes it, and stores the output in the specified output S3 bucket. The job also updates a
    SpatioTemporal Asset Catalog (STAC) endpoint and an OpenSearch cluster with metadata about the
    ingested data.

    Note: This function requires AWS credentials to be configured with appropriate permissions for
    SageMaker, S3, and other relevant services.
    """
    args = parse_arguments()

    # Setting up the parameter values
    input_bucket = args.s3_uri
    output_bucket = args.output_bucket
    aws_region = args.region
    enable_debugging = "true" if args.verbose else ""

    # Load the json file
    config_file = json.load(open("bin/bulk/config/bulk_config.json"))

    s3_input_config = config_file["S3InputConfig"]
    s3_input_config["S3Uri"] = input_bucket

    s3_output_config = config_file["S3OutputConfig"]
    s3_output_config["S3Uri"] = output_bucket

    instance_config = config_file["InstanceConfig"]
    cluster_config = instance_config["ClusterConfig"]

    stac_endpoint = config_file["StacEndpoint"]
    opensearch_config = config_file["OpenSearchConfig"]
    thread_workers = instance_config["ThreadWorkers"]
    collection_id = config_file["CollectionId"]
    vpc_config = config_file["VpcConfig"]
    max_runtime = config_file["MaxRuntimeInSeconds"]
    image_uri = instance_config["ImageUri"]
    role_arn = instance_config["RoleArn"]

    if not vpc_config["Subnets"] and not vpc_config["SecurityGroupIds"]:
        vpc_config = get_vpc_details(aws_region)

        if vpc_config is None:
            logger.error("Failed to retrieve VPC details.")
            sys.exit(1)

    s3_bulk = S3_Bulk_Manager(input_bucket, output_bucket, aws_region, cluster_config["InstanceCount"])
    s3_bulk.count_objects()
    s3_bulk.create_and_upload_manifest_files()

    sagemaker_client = boto3.client("sagemaker", aws_region)

    logger.info("Now submitting the jobs...")

    for manifest_file in s3_bulk.manifest_filename:
        s3_input_config["S3Uri"] = manifest_file

        input_config = {
            "InputName": "input",
            "S3Input": s3_input_config,
        }

        output_config = {
            "OutputName": "output",
            "S3Output": s3_output_config,
        }

        cluster_config["InstanceCount"] = 1
        job_name = f"bulk-ingest-job-{token_hex(16)}"
        response_exec = sagemaker_client.create_processing_job(
            ProcessingInputs=[input_config],
            ProcessingOutputConfig={"Outputs": [output_config]},
            ProcessingJobName=job_name,
            ProcessingResources={"ClusterConfig": cluster_config},
            StoppingCondition={"MaxRuntimeInSeconds": max_runtime},
            AppSpecification={
                "ImageUri": image_uri,
                "ContainerEntrypoint": [
                    "/entry.sh",
                    "/bin/bash",
                    "-c",
                    "python3 osml-data-intake/src/aws/osml/data_intake/bulk_processor.py",
                ],
            },
            NetworkConfig={"EnableNetworkIsolation": False, "VpcConfig": vpc_config},
            RoleArn=role_arn,
            Environment={
                "S3_URI": manifest_file,
                "S3_INPUT_PATH": s3_input_config["LocalPath"],
                "S3_OUTPUT_PATH": s3_output_config["LocalPath"],
                "S3_OUTPUT_BUCKET": output_bucket,
                "STAC_ENDPOINT": stac_endpoint,
                "COLLECTION_ID": collection_id,
                "ES_HOST": opensearch_config["ES_HOST"],
                "ES_PORT": opensearch_config["ES_PORT"],
                "ES_USE_SSL": opensearch_config["ES_USE_SSL"],
                "ES_VERIFY_CERTS": opensearch_config["ES_VERIFY_CERTS"],
                "THREAD_WORKERS": str(thread_workers),
                "ENABLE_DEBUGGING": enable_debugging,
            },
        )

        logger.info(f"{job_name} has been submitted!")

        if "ProcessingJobArn" in response_exec:
            arn = response_exec["ProcessingJobArn"]
            job_name = arn.split("/")[-1]
            status_code = response_exec["ResponseMetadata"]["HTTPStatusCode"]

            logger.info("==============================")
            logger.info(f"Job Name: {job_name}\nStatus Code:{status_code}\nArn: {arn}\nManifest File: {manifest_file}")
        else:
            logger.error("Error: Failed to retrieve processing job details.\n")


if __name__ == "__main__":
    execute_sm_processing_job()
