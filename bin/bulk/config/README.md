# SageMaker Processing Job Configuration

This configuration file is used to set up a SageMaker Processing Job for ingesting and processing data. The Processing Job is a managed service provided by Amazon SageMaker that allows you to run data processing workloads on a managed compute infrastructure.

## Usage

1. Update the configuration file located at `bin/bulk/config/bulk_config.json` according to your requirements.

2. Execute the processing job using the command:
   ```bash
   python3 ./bin/bulk/bulk_cli.py --s3-uri <S3 Input URI> --output-bucket <S3 Output URI> --region <AWS Region>
   ```

3. To monitor the ProcessingJob:
   - Navigate to the SageMaker Processing Console: AWS -> SageMaker -> Processing (Left Sidebar) -> Processing Job, and monitor it there.
   - Alternatively, monitor using the below command:

      ```bash
      python3 bin/bulk/check_job.py --region us-west-2 [--job name]
      ```

    **Note:** Replace [--job name] with your specific job name if needed.

## Configuration Parameters

| Parameter | Description | Recommended Value |
|------------|--------------|---------------|
| `S3InputConfig` |  |  |
| `S3InputConfig.LocalPath` | The local path on the Processing Job instances where the input data will be downloaded. | `"/opt/ml/processing/input"` |
| `S3InputConfig.S3DataType` | The type of input data, either `S3Prefix` or `ManifestFile`. | `"ManifestFile"` |
| `S3InputConfig.S3InputMode` | The mode for transferring input data, either `File` or `Pipe`. | `"File"` |
| `S3InputConfig.S3DataDistributionType` | The distribution strategy for input data across Processing Job instances, either `FullyReplicated` or `ShardedByS3Key`. | `"ShardedByS3Key"` |
| `S3OutputConfig` |  |  |
| `S3OutputConfig.LocalPath` | The local path on the Processing Job instances where the output data will be written. | `"/opt/ml/processing/output"` |
| `S3OutputConfig.S3UploadMode` | The mode for uploading output data to Amazon S3, either `Continuous` or `EndOfJob`. | `"Continuous"` |
| `InstanceConfig` |  |  |
| `InstanceConfig.ClusterConfig` | | |
| `InstanceConfig.ClusterConfig.InstanceCount` | The number of instances to use for the Processing Job. | `4` |
| `InstanceConfig.ClusterConfig.InstanceType` | The EC2 instance type for the Processing Job instances. | `"ml.c5.4xlarge"` |
| `InstanceConfig.ClusterConfig.VolumeSizeInGB` | The size (in GB) of the EBS volume attached to each Processing Job instance. | `100` |
| `InstanceConfig.ThreadWorkers` | The number of worker threads to use for the Processing Job. | `16` |
| `InstanceConfig.ImageUri` | The URI of the Docker container image to use for the Processing Job. | `""<account id>.dkr.ecr.<region>.amazonaws.com/data-bulk-ingest-container:latest"` |
| `InstanceConfig.RoleArn` | The Amazon Resource Name (ARN) of the IAM role that provides permissions for the Processing Job. | `"arn:aws:iam::"<account id>:role/BulkIngestSageMakerExecutionRole"` |
| `OpenSearchConfig` |  |  |
| `OpenSearchConfig.ES_HOST` | The hostname of the OpenSearch cluster. | `"<OSS endpoint>"` |
| `OpenSearchConfig.ES_PORT` | The port number of the OpenSearch cluster. | `"443"` |
| `OpenSearchConfig.ES_USE_SSL` | Whether to use SSL for communication with the OpenSearch cluster. | `"true"` |
| `OpenSearchConfig.ES_VERIFY_CERTS` | Whether to verify SSL certificates when communicating with the OpenSearch cluster. | `"true"` |
| `VpcConfig` |  |  |
| `VpcConfig.Subnets` | The list of subnet IDs for the VPC. | `["subnet-...", "subnet-...", ...]` |
| `VpcConfig.SecurityGroupIds` | The list of security group IDs for the Processing Job instances. | `["sg-..."]` |
| `CollectionId` | The ID of the collection where the processed data will be stored. | `"OSML"` |
| `StacEndpoint` | The endpoint for the SpatioTemporal Asset Catalog (STAC) service (if used). | `""` |
| `MaxRuntimeInSeconds` | The maximum runtime (in seconds) for the Processing Job. | `432000` |


**Notes:**
1. Ensure the script uses the same Subnets and Security Group as OpenSearch to seamlessly catalog items into the database. Failing to do so may result in a TimeOutError, indicating communication issues with the service.
2. To determine the appropriate number of `ThreadWorkers` for your instance, you need to first obtain the Instance Type specification by visiting the [SageMaker Pricing](https://aws.amazon.com/sagemaker/pricing/) page. **Importance:** Configuring the correct number of `ThreadWorkers` is crucial for optimizing the performance of your instance. By setting the `ThreadWorkers` as same as the vCPUs, you ensure that your instance can handle concurrent tasks efficiently without causing a bottleneck. This helps to maximize CPU utilization and avoids slowing down any processes, thereby improving the overall performance and throughput of your workloads.
3. Regarding `InstanceCount`, ensure your account quotas meet the requirements. You can check your quotas by visiting the [AWS Service Quotas](https://us-west-2.console.aws.amazon.com/servicequotas/home/services/sagemaker/quotas?region=us-west-2) page. Search for the instance type you intend to use, like `ml.c4.2xlarge for processing job usage`, to view your current limits.


## Recommended Template

Below is a recommend template, however, you will need to adjust your `ImageUri`, `RoleArn`, and `OpenSearchConfig`:

```
{
  "S3InputConfig": {
    "LocalPath": "/opt/ml/processing/input",
    "S3DataType": "ManifestFile",
    "S3InputMode": "File",
    "S3DataDistributionType": "ShardedByS3Key"
  },
  "S3OutputConfig": {
    "LocalPath": "/opt/ml/processing/output",
    "S3UploadMode": "Continuous"
  },
  "InstanceConfig": {
    "ClusterConfig": {
      "InstanceCount": 4,
      "InstanceType": "ml.c5.4xlarge",
      "VolumeSizeInGB": 100
    },
    "ThreadWorkers": 16,
    "ImageUri": "<account id>.dkr.ecr.<region>.amazonaws.com/data-bulk-ingest-container:latest",
    "RoleArn": "arn:aws:iam::<account id>:role/BulkIngestSageMakerExecutionRole"
  },
  "OpenSearchConfig": {
    "ES_HOST":"<OSS endpoint>",
    "ES_PORT": "443",
    "ES_USE_SSL": "true",
    "ES_VERIFY_CERTS": "true"
  },
  "CollectionId": "OSML",
  "StacEndpoint": "",
  "VpcConfig": {
    "Subnets": [],
    "SecurityGroupIds": []
  },
  "MaxRuntimeInSeconds": 432000
}
```
