#  Copyright 2023-2024 Amazon.com, Inc. or its affiliates.

import os
import shutil
from typing import Optional
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

from src.aws.osml.data_intake.utils.logger import logger


class S3Url:
    """
    A class to parse and represent an S3 URL.

    :param url: The S3 URL to be parsed.
    """

    def __init__(self, url: str) -> None:
        """
        Initialize an S3Url instance.

        :param url: The S3 URL to be parsed.
        """
        self._parsed = urlparse(url, allow_fragments=False)

    @property
    def bucket(self) -> str:
        """
        Get the bucket name from the parsed URL.

        :return: The bucket name.
        """
        return self._parsed.netloc

    @property
    def key(self) -> str:
        """
        Get the object key from the parsed URL.

        :return: The object key.
        """
        if self._parsed.query:
            return self._parsed.path.lstrip("/") + "?" + self._parsed.query
        else:
            return self._parsed.path.lstrip("/")

    @property
    def url(self) -> str:
        """
        Get the full URL as a string.

        :return: The full URL.
        """
        return self._parsed.geturl()


class S3Manager:
    """
    A class to manage S3 file downloads and uploads.

    :param output_bucket: The name of the S3 bucket used for uploads.
    :returns: None
    """

    def __init__(self, output_bucket: str) -> None:
        """
        Initialize an S3Manager instance.

        :param output_bucket: The name of the S3 bucket used for uploads.
        """
        self.output_bucket = output_bucket
        self.s3_client = boto3.client("s3")
        self.tmp_dir = "/tmp/images"
        self.s3_url: Optional[S3Url] = None

    def download_file(self, s3_url: S3Url) -> str:
        """
        Download the object from S3 to the local `/tmp` directory.

        :param s3_url: An object representing the S3 bucket and key for the source data.
        :return: None
        :raises ClientError: If downloading from S3 fails.
        :raises Exception: If any other error occurs during the download process.
        """
        # Clean up directory before we start processing
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

        # Create a storage directory in /tmp to use
        os.makedirs(self.tmp_dir, exist_ok=True)

        # Extract metadata
        self.s3_url = s3_url
        source_key: str = s3_url.key
        source_bucket: str = s3_url.bucket
        file_path: str = f"{self.tmp_dir}/{source_key}"

        # Try and download the file
        logger.debug(f"Downloading {s3_url.url} to {file_path}")
        try:
            self.s3_client.download_file(source_bucket, source_key, file_path)
            return file_path
        except ClientError as err:
            detailed_error: Optional[str] = ""
            if err.response["Error"]["Code"] == "404":
                detailed_error = f"The {source_bucket} bucket does not exist!"
            elif err.response["Error"]["Code"] == "403":
                detailed_error = f"You do not have permission to access {source_bucket} bucket!"
            error_message: str = f"S3 error: {err} {detailed_error}".strip()
            logger.error(error_message)
            raise err
        except Exception as err:
            raise err

    def upload_file(self, file_path: str, file_type: str) -> None:
        """
        Upload the specified file to the configured S3 bucket.

        :param file_path: The path to the file on the local system.
        :param file_type: The type of file being uploaded (for logging purposes).
        :raises ClientError: If uploading to S3 fails.
        """
        try:
            key = self.strip(file_path)
            self.s3_client.upload_file(file_path, self.output_bucket, key)
            logger.info(f"Uploaded {file_type} file to s3://{self.output_bucket}/{key}")
        except ClientError as err:
            logger.error(f"Failed to upload {file_type} file: {err}")
            raise err

    @staticmethod
    def strip(file_path: str) -> str:
        """
        Extracts the base file name from a given file path.

        :param file_path: The path of the file as a string.
        :returns: The base file name.
        """
        return os.path.basename(file_path).split("/")[-1]
