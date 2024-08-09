#  Copyright 2023-2024 Amazon.com, Inc. or its affiliates.

import os
import shutil
import traceback
from typing import Optional
from urllib.parse import urlparse

import boto3
from boto3.resources.base import ServiceResource
from botocore.exceptions import ClientError

from ..utils import logger


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

    @property
    def prefix(self) -> str:
        """
        Get the prefix (directory path) from the S3 key, excluding the file name and extension.

        :return: The prefix.
        """
        return os.path.dirname(self.key)

    @property
    def filename(self) -> str:
        """
        Get the filename with extension from the S3 key.

        :return: The filename with extension.
        """
        return os.path.basename(self.key)


class S3Manager:
    """
    A class to manage S3 file downloads and uploads.

    :param output_bucket: The name of the S3 bucket used for uploads.
    :returns: None
    """

    def __init__(self, output_bucket: str, aws_s3: ServiceResource = None, input_dir: str = "/tmp/images") -> None:
        """
        Initialize an S3Manager instance.

        :param output_bucket: The name of the S3 bucket used for uploads.
        """
        self.output_bucket = "s3://" + output_bucket if not output_bucket.startswith("s3://") else output_bucket
        self.s3_client = aws_s3 if aws_s3 else boto3.resource("s3")
        self.tmp_dir = input_dir
        self.s3_url: Optional[S3Url] = None
        self.output_folder = None

    def set_output_folder(self, output_folder: str) -> None:
        """
        Set the output folder for the S3Manager

        :param output_folder: The name of the output folder.
        :return: None
        """
        self.output_folder = output_folder

    def download_file(self, s3_url: S3Url) -> str:
        """
        Download the object from S3 to the local `/tmp` directory.

        :param s3_url: An object representing the S3 bucket and key for the source data.

        :return: the path to the downloaded imagery file

        :raises Exception: If any other error occurs during the download process.
        """
        # Clean up directory before we start processing
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

        # Create a storage directory in /tmp to use
        os.makedirs(self.tmp_dir, exist_ok=True)

        # Extract metadata
        self.s3_url = s3_url
        source_bucket: str = s3_url.bucket
        source_key: str = s3_url.key
        source_filename: str = s3_url.filename
        file_path: str = f"{self.tmp_dir}/{source_filename}"

        # Try and download the file
        logger.info(f"Downloading {s3_url.url} to {file_path}")
        try:
            logger.info(f"Beginning download of {s3_url.url}")
            self.s3_client.meta.client.download_file(source_bucket, source_key, file_path)
            logger.info(f"Successfully download to {file_path}.")
            return file_path
        except ClientError as err:
            detailed_error: Optional[str] = ""
            if err.response["Error"]["Code"] == "404":
                detailed_error = f"The {source_bucket} bucket does not exist!"
            elif err.response["Error"]["Code"] == "403":
                detailed_error = f"You do not have permission to access {source_bucket} bucket!"
            error_message: str = f"S3 error: {err} {detailed_error}".strip()
            logger.error(error_message)
        except Exception as err:
            logger.error(f"S3 Download {err} / {traceback.format_exc()}")

    def upload_file(self, file_path: str, file_type: str, upload_args=None) -> None:
        """
        Upload the specified file to the configured S3 bucket.

        :param file_path: The path to the file on the local system.
        :param file_type: The type of file being uploaded (for logging purposes).
        :param upload_args: Optional arguments for boto3 ExtraArgs
        :raises ClientError: If uploading to S3 fails.
        """
        if upload_args is None:
            upload_args = {}
        try:
            key = f"{self.output_folder}/{self.strip(file_path)}" if self.output_folder else self.strip(file_path)
            self.s3_client.meta.client.upload_file(
                file_path, self.output_bucket.replace("s3://", ""), key, ExtraArgs=upload_args
            )
            logger.info(f"Uploaded {file_type} file to {self.output_bucket}/{key}")
        except ClientError as err:
            logger.error(f"Failed to upload {file_type} file: {err}")

    @staticmethod
    def strip(file_path: str) -> str:
        """
        Extracts the base file name from a given file path.

        :param file_path: The path of the file as a string.
        :returns: The base file name.
        """
        return os.path.basename(file_path).split("/")[-1]
