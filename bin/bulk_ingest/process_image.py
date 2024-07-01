#  Copyright 2024 Amazon.com, Inc. or its affiliates.

import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
import requests
from app_config import BotoConfig
from boto3.resources.base import ServiceResource
from botocore.exceptions import ClientError

from aws.osml.data_intake.image_data import ImageData
from aws.osml.data_intake.managers.s3_manager import S3Manager, S3Url
from aws.osml.data_intake.managers.stac_manager import STACManager
from aws.osml.data_intake.utils import logger

stac_catalog_items_lock = threading.Lock()


class DataIntakeManager:
    def __init__(
        self, aws_s3: ServiceResource, output_path: str, output_bucket: str, stac_endpoint: str, collection_id: str = "OSML"
    ):
        """
        Initializes the DataIntakeManager class.

        :param aws_s3: The AWS S3 client object.
        :param output_path: The output path for storing processed data.
        :param output_bucket: The output bucket for storing processed data.
        :param collection_id: The ID of the STAC collection.
        :param stac_endpoint: The URL of the STAC endpoint.
        """
        self.stac_catalog_items = []
        self.collection_id = collection_id
        self.output_bucket = output_bucket
        self.output_path = output_path
        self.stac_endpoint = stac_endpoint
        self.s3_manager = S3Manager(self.output_bucket, aws_s3)


def process_image(image: str, dataIntakeManager: DataIntakeManager) -> None:
    """
    Process a single image

    :param image: Path or S3 URL of the image.
    :param dataIntakeManager: An instance of the DataIntakeManager class.
    """
    s3_url = S3Url(image)
    local_object_path = dataIntakeManager.s3_manager.download_file(s3_url)

    image_data = ImageData(local_object_path, f"{dataIntakeManager.output_path}/{s3_url.key}")

    aux_file = image_data.generate_aux_file()
    ovr_file = image_data.generate_ovr_file()

    logger.info(f"Generated aux file: {aux_file}")
    logger.info(f"Generated ovr file: {ovr_file}")

    dir_list = os.listdir(dataIntakeManager.output_path)
    logger.info(f"Listing the files in this {dataIntakeManager.output_path} directory:\n{dir_list}")

    stac_manager = STACManager(None, dataIntakeManager.s3_manager, dataIntakeManager.stac_endpoint)
    stac_item = stac_manager.construct_stac_item(image_data, dataIntakeManager.collection_id)
    logger.info(f"STAC item for {image}: {stac_item}")

    with stac_catalog_items_lock:
        dataIntakeManager.stac_catalog_items.append(stac_item)


def submit_data_catalog(dataIntakeManager):
    """
    TODO: Add docstrings and return types
    """
    headers = {"Content-Type": "application/json; charset=utf-8"}
    url_collection = f"{dataIntakeManager.stac_endpoint}/collections/"
    collection_id = dataIntakeManager.collection_id

    try:
        data = {
            "type": "FeatureCollection",
            "features": dataIntakeManager.stac_catalog_items,
        }
        resp = requests.post(f"{url_collection}/{collection_id}/items", json=json.dumps(data), headers=headers)
        logger.info(f"It has been added! The status code: {resp.status_code}")
    except Exception as err:
        logger.error(f"Unable to submit data catalog item... {err}")


def start_workers(image_batch, dataIntakeManager):
    """
    Starts worker threads to process a batch of images.

    :param aws_s3: The AWS S3 client object.
    :param image_batch: A list of image paths or S3 URLs.
    :param output_path: The output path for storing processed data.
    """
    with ThreadPoolExecutor(max_workers=25) as executor:
        future_to_image = {executor.submit(process_image, image, dataIntakeManager): image for image in image_batch}
        for future in as_completed(future_to_image):
            image = future_to_image[future]
            try:
                future.result()
            except Exception as exc:
                logger.error(f"Image {image} generated an exception: {exc}")

        # Publish them to Stac Catalog
        logger.info(dataIntakeManager.stac_catalog_items)
        submit_data_catalog(dataIntakeManager)

        # Then clear the list
        logger.info("All images processed.")

    logger.info("End of ThreadPoolExecutor")


def process_manifest_file(input_manifest_path):
    """
    Processes a manifest file containing a list of S3 object paths.

    :param input_manifest_path: The path to the input manifest file.

    :return: A list of S3 object paths if the manifest file exists, otherwise None.
    """
    input_manifest_path = input_manifest_path + "/input-manifest"
    if os.path.exists(input_manifest_path):
        s3_list = []
        with open(input_manifest_path, "r", encoding="utf-8") as manifest_file:
            for s3_object in manifest_file:
                if s3_object.strip():
                    logger.info(f"Object file from Manifest file: {s3_object}")
                    s3_list.append(s3_object.strip())
                else:
                    logger.debug("Skipping empty lines")

        return s3_list

    return None


if __name__ == "__main__":
    input_manifest_path = os.getenv("S3_INPUT_PATH")
    output_path = os.getenv("S3_OUTPUT_PATH")
    output_bucket = os.getenv("S3_OUTPUT_BUCKET")
    stac_endpoint = os.getenv("STAC_ENDPOINT")
    collection_id = os.getenv("COLLECTION_ID")

    try:
        aws_s3 = boto3.resource("s3", config=BotoConfig.default)
    except ClientError as err:
        sys.exit(f"Fatal error occurred while initializing AWS services. Exiting. {err}")

    if input_manifest_path:
        s3_list = process_manifest_file(input_manifest_path)
        if s3_list:
            batch_size = 25
            for i in range(0, len(s3_list), batch_size):
                dataIntakeManager = DataIntakeManager(aws_s3, output_path, output_bucket, stac_endpoint)

                image_batch = s3_list[i : i + batch_size]
                start_workers(image_batch, dataIntakeManager)
        else:
            logger.error("The manifest file is empty or not found.")

    else:
        logger.error("The environment variable S3_INPUT_PATH is not set.")
        raise ValueError("The environment variable S3_INPUT_PATH is not set.")
