#  Copyright 2024 Amazon.com, Inc. or its affiliates.

import os
import shutil
import unittest


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
        from aws.osml.data_intake.data import ImageData

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
        for file in files_to_remove:
            if os.path.exists(file):
                os.remove(file)


if __name__ == "__main__":
    unittest.main()
