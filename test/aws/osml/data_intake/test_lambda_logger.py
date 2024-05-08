#  Copyright 2023-2024 Amazon.com, Inc. or its affiliates.

import logging
import unittest
from unittest.mock import patch

from aws.osml.data_intake.lambda_logger import get_logger  # Adjust this import as needed


class TestLambdaLogger(unittest.TestCase):
    @patch("logging.Logger.hasHandlers", return_value=False)
    @patch("logging.basicConfig")
    def test_logger_no_handlers(self, mock_basic_config, mock_has_handlers):
        """
        Test that basicConfig is called if no handlers are present on the root logger.
        """
        logger = get_logger("test_logger", logging.DEBUG)

        # Check that basicConfig was called correctly
        mock_basic_config.assert_called_once_with(level=logging.DEBUG)

        # Check that the logger returned has the correct name
        self.assertEqual(logger.name, "test_logger")

    @patch("logging.Logger.hasHandlers", return_value=True)
    @patch("logging.basicConfig")
    def test_logger_with_handlers(self, mock_basic_config, mock_has_handlers):
        """
        Test that basicConfig is called if no handlers are present on the root logger.
        """
        logger = get_logger("test_logger", logging.DEBUG)

        # Check that basicConfig was called correctly
        mock_basic_config.assert_not_called()

        # Check that the logger returned has the correct name
        self.assertEqual(logger.name, "test_logger")


if __name__ == "__main__":
    unittest.main()
