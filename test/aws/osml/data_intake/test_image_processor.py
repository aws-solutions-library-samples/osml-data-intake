#  Copyright 2024 Amazon.com, Inc. or its affiliates.

import json
import os
import shutil
import unittest

import boto3
from moto import mock_aws


@mock_aws
class TestImageProcessor(unittest.TestCase):
    """
    A test suite for the ImageProcessor class.

    This suite runs tests to ensure that the ImageProcessor can handle both
    successful and unsuccessful image processing tasks.
    """

    def setUp(self):
        """
        Set up the test environment for ImageProcessor tests.

        This involves creating a test S3 bucket, uploading a test image file,
        creating an SNS topic, and initializing the ImageProcessor with
        a mock S3 image URL and mock AWS clients.
        """
        from aws.osml.data_intake.image_processor import ImageProcessor

        # Retrieve environment variables or set default values
        test_bucket = "test-bucket"
        test_topic = "test-topic"

        # Create S3 bucket and upload test image
        s3 = boto3.resource("s3", region_name="us-east-1")
        s3.meta.client.create_bucket(Bucket=test_bucket)
        s3.meta.client.upload_file("./test/data/small.tif", test_bucket, "small.tif")

        # Create an SNS topic
        sns = boto3.client("sns", region_name="us-east-1")
        response = sns.create_topic(Name=test_topic)
        sns_topic_arn = response["TopicArn"]

        # Mock the ImageProcessor
        self.message = {"image_uri": f"s3://{test_bucket}/small.tif"}
        self.processor = ImageProcessor(message=json.dumps(self.message))
        self.processor.sns_manager.sns_client = sns
        self.processor.sns_manager.output_topic = sns_topic_arn
        self.processor.s3_manager.s3_client = s3
        self.processor.s3_manager.output_bucket = test_bucket
        self.processor.s3_manager = self.processor.s3_manager

    def test_process_success(self):
        """
        Test the process method of ImageProcessor for a successful scenario.
        """
        # Run the process method
        response = self.processor.process()

        # Check the response
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("successfully", response["body"])

    def test_process_failure(self):
        """
        Test the process method of ImageProcessor for a failure scenario.
        """
        self.processor.sns_request.image_uri = "s3://invalid-bucket/invalid-image.tif"

        # Run the process method
        response = self.processor.process()

        # Check the response
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Unable to Load", response["body"])


class TestImageData(unittest.TestCase):
    """
    A test suite for the ImageData class in the AWS OSML data intake module.

    This suite tests the instantiation and properties of the ImageData class to ensure
    that it properly handles image files and associated metadata.
    """

    def setUp(self):
        """
        Set up the test environment for testing ImageData.
        """
        from aws.osml.data_intake.image_processor import ImageData

        self.original_source = "./test/data/small.tif"
        self.source_file = "./test/data/small-test.tif"
        shutil.copyfile(self.original_source, self.source_file)
        self.image_data = ImageData(self.source_file)
        self.original_files = {
            "aux": f"{self.original_source}.aux.xml",
            "ovr": f"{self.original_source}.ovr",
            "gdalinfo": f"{self.original_source}_gdalinfo.txt",
            "thumbnail": f"{self.original_source}.thumbnail.png",
        }

    def test_generate_metadata(self):
        """
        Test the generate_metadata method of ImageData.
        """
        self.image_data.generate_metadata()
        self.assertIsNotNone(self.image_data.dataset)
        self.assertIsNotNone(self.image_data.sensor_model)
        self.assertEqual(self.image_data.width, self.image_data.dataset.RasterXSize)
        self.assertEqual(self.image_data.height, self.image_data.dataset.RasterYSize)
        self.assertEqual(
            self.image_data.image_corners,
            [
                [0, 0],
                [self.image_data.width, 0],
                [self.image_data.width, self.image_data.height],
                [0, self.image_data.height],
            ],
        )

    def test_create_image_data(self):
        """
        Test the creation and initialization of ImageData.
        """
        self.assertIsNotNone(self.image_data.geo_polygon)
        self.assertIsNotNone(self.image_data.geo_bbox)

    def test_generate_aux_file(self):
        """
        Test the generate_aux_file method of ImageData.
        """
        aux_file = self.image_data.generate_aux_file()
        self.assertEqual(aux_file, self.source_file + ".aux.xml")
        self.assertTrue(os.path.exists(aux_file))

    def test_generate_ovr_file(self):
        """
        Test the generate_ovr_file method of ImageData.
        """
        ovr_file = self.image_data.generate_ovr_file()
        self.assertEqual(ovr_file, self.source_file + ".ovr")
        self.assertTrue(os.path.exists(ovr_file))

    def test_generate_gdalinfo(self):
        """
        Test the generate_gdalinfo method of ImageData.
        """
        info_file = self.image_data.generate_gdalinfo()
        self.assertEqual(info_file, self.source_file + "_gdalinfo.txt")
        self.assertTrue(os.path.exists(info_file))

    def test_generate_thumbnail(self):
        """
        Test the generate_thumbnail method of ImageData.
        """
        thumbnail_file = self.image_data.generate_thumbnail()
        self.assertEqual(thumbnail_file, self.source_file + ".thumbnail.png")
        self.assertTrue(os.path.exists(thumbnail_file))

    def test_clean_dataset(self):
        """
        Test the clean_dataset method of ImageData.
        """
        self.image_data.clean_dataset()
        self.assertIsNone(self.image_data.dataset)

    def tearDown(self):
        """
        Clean up any files generated during testing.
        """
        files_to_remove = [
            self.source_file,
            self.source_file + ".aux.xml",
            self.source_file + ".ovr",
            self.source_file + "_gdalinfo.txt",
            self.source_file + ".thumbnail.png",
        ]
        self.image_data.delete_files(files_to_remove)


if __name__ == "__main__":
    unittest.main()
