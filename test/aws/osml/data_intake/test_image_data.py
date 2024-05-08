# Copyright 2024 Amazon.com, Inc. or its affiliates.

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
        from aws.osml.data_intake.image_data import ImageData

        # Create an instance of ImageData with a test file path
        self.image_data = ImageData("./test/data/small.tif")

    def test_create_image_data(self):
        """
        Test the creation and initialization of ImageData.

        Asserts that the source file path and derived file paths (auxiliary and overview)
        are correctly assigned, and checks that the geographic bounding box and polygon
        are accurately determined.
        """
        self.assertEqual(self.image_data.source_file, "./test/data/small.tif")
        self.assertEqual(self.image_data.aux_file, "./test/data/small.tif.aux.xml")
        self.assertEqual(self.image_data.ovr_file, "./test/data/small.tif.ovr")
        self.assertEqual(
            self.image_data.geo_polygon,
            [
                (5.399047618346933, 50.04094857888587),
                (5.410723561083805, 50.04094857888587),
                (5.410723561083805, 50.032039447224086),
                (5.399047618346933, 50.032039447224086),
                (5.399047618346933, 50.04094857888587),
            ],
        )
        self.assertEqual(
            self.image_data.geo_bbox, [5.399047618346933, 50.032039447224086, 5.410723561083805, 50.04094857888587]
        )


if __name__ == "__main__":
    unittest.main()
