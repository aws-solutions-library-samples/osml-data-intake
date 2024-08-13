#  Copyright 2023-2024 Amazon.com, Inc. or its affiliates.

import json
import unittest


class TestProcessorBase(unittest.TestCase):
    def test_success_message(self):
        from aws.osml.data_intake.processor_base import ProcessorBase

        message = "Processing completed successfully."
        expected_result = {"statusCode": 200, "body": json.dumps(message)}

        result = ProcessorBase.success_message(message)

        self.assertEqual(result, expected_result)

    def test_failure_message(self):
        from aws.osml.data_intake.processor_base import ProcessorBase

        exception_message = "An error occurred during processing."
        mock_exception = Exception(exception_message)

        result = ProcessorBase.failure_message(mock_exception)

        result_body = json.loads(result["body"])

        self.assertEqual(result["statusCode"], 500)
        self.assertIn("message", result_body)
        self.assertIn("stack_trace", result_body)
        self.assertEqual(result_body["message"], exception_message)
        self.assertIsInstance(result_body["stack_trace"], list)
        self.assertGreater(len(result_body["stack_trace"]), 0)


if __name__ == "__main__":
    unittest.main()
