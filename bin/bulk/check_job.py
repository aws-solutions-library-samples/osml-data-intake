#  Copyright 2024 Amazon.com, Inc. or its affiliates.

import argparse
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Union

import boto3
from boto3.resources.base import ServiceResource

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_processing_job(sagemaker_client: ServiceResource, job_name: str) -> Union[Tuple[str, str, str, str], str]:
    """
    Get the latest status of a SageMaker processing job.

    :param sagemaker_client: The SageMaker client.
    :param job_name: The name of the SageMaker processing job.

    :returns: A tuple containing the job status, duration, creation time, and CloudWatch URL.
    """
    try:
        response = sagemaker_client.describe_processing_job(ProcessingJobName=job_name)
        status = response["ProcessingJobStatus"]

        creation_time = response["CreationTime"]

        if "ProcessingStartTime" not in response or "ProcessingEndTime" not in response:
            time_now = datetime.now().astimezone()
            duration = duration_in_human_readable(creation_time, time_now)
        else:
            processing_start_time = response["ProcessingStartTime"]
            processing_end_time = response["ProcessingEndTime"]
            duration = duration_in_human_readable(processing_start_time, processing_end_time)

        log_group = response.get("ProcessingJobArn").split(":processing-job/")[1]
        log_stream = response.get("ProcessingJobArn").split(":processing-job/")[1]
        region_name = sagemaker_client.meta.region_name
        cw_endpoint = f"https://{region_name}.console.aws.amazon.com/cloudwatch/home"
        cloudwatch_url = (
            f"{cw_endpoint}?region={region_name}#logsV2:log-groups/log-group/{log_group}/log-events/{log_stream}"
        )

        return status, duration, creation_time.strftime("%Y-%m-%d %H:%M:%S %Z"), cloudwatch_url
    except sagemaker_client.exceptions.ResourceNotFound:
        return "Processing job not found."
    except Exception as e:
        raise Exception(f"An error occurred: {str(e)}")


def duration_in_human_readable(start_time: datetime, end_time: datetime) -> str:
    """
    Calculate the duration between start and end times in a human-readable format.

    :param start_time: Start time.
    :param end_time: End time.

    :returns: Duration in a human-readable format (e.g., '1 day, 2 hours, 30 minutes').
    """
    duration = end_time - start_time
    days = duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days} days, {hours} hours, {minutes} minutes"
    elif hours > 0:
        return f"{hours} hours, {minutes} minutes"
    elif minutes > 0:
        return f"{minutes} minutes"
    else:
        return "Less than a minute"


def get_recent_processing_jobs(sagemaker_client: ServiceResource, max_results: int) -> Union[List[Dict], str]:
    """
    Get the most recent SageMaker processing jobs.

    :param sagemaker_client: The SageMaker client.
    :param max_results: The maximum number of recent jobs to retrieve.

    :returns: A list of processing job summaries or an error message.
    """
    try:
        response = sagemaker_client.list_processing_jobs(
            SortBy="CreationTime", SortOrder="Descending", MaxResults=max_results
        )
        job_summaries = response["ProcessingJobSummaries"]
        return job_summaries
    except Exception as e:
        raise Exception(f"An error occurred: {str(e)}")


def print_job_status_table(sagemaker_client: ServiceResource, jobs: List[Dict], region: str) -> None:
    """
    Print the job statuses in a formatted table.

    :param sagemaker_client: The SageMaker client.
    :param jobs: A list of processing job summaries.
    :param region: The AWS region where the SageMaker jobs are running.

    :returns: None
    """
    logger.info(f"{'Job Name':<60} {'Status':<15} {'Region':<15} {'Duration':<20} {'Creation Time':<20}")
    logger.info("=" * 150)

    # Print the job details
    for job_summary in jobs:
        job_name = job_summary["ProcessingJobName"]
        status, duration, creation_time, cloudwatch_url = get_processing_job(sagemaker_client, job_name)
        logger.info(f"{job_name:<60} {status:<15} {region:<15} {duration:<20} {creation_time:<20}")
        logger.info(f"Cloudwatch URL: {cloudwatch_url}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check the latest status of a SageMaker processing job.")
    parser.add_argument("--job-name", help="The name of the SageMaker processing job.")
    parser.add_argument("--region", required=True, help="The AWS region where the SageMaker job is running.")
    parser.add_argument(
        "--max-results", type=int, default=5, help="Maximum number of recent jobs to retrieve (default is 5)."
    )

    args = parser.parse_args()

    job_name = args.job_name
    region = args.region
    max_results = args.max_results

    sagemaker_client = boto3.client("sagemaker", region_name=region)

    if job_name:
        print_job_status_table(sagemaker_client, [{"ProcessingJobName": job_name}], region)
    else:
        logger.info("No job name provided. Fetching the status of the most recent 5 SageMaker processing jobs.")
        recent_jobs = get_recent_processing_jobs(sagemaker_client, max_results)

        if isinstance(recent_jobs, str):
            logger.info(recent_jobs)
        else:
            print_job_status_table(sagemaker_client, recent_jobs, region)


if __name__ == "__main__":
    main()
