# OSML Data Intake

## Overview
This application facilitates the processing, conversion, and management of satellite imagery metadata as part of the
OversightML (OSML) framework and can be deployed as part of the
OSML [guidance package](https://github.com/aws-solutions-library-samples/guidance-for-processing-overhead-imagery-on-aws).
It leverages the GDAL library and integrates with Amazon S3 for seamless storage and sharing to provide imagery
metadata to other service components.
Below is an overview of the main features:

### Intake
The intake processes metadata from satellite imagery files, such as image dimensions and geographical coordinates.
Uploads auxiliary files and metadata to Amazon S3 and serves converted meta-data into STAC items on an SNS topic.

### Ingest
Ingests SpatioTemporal Asset Catalog (STAC) items placed on an SNS topic into via the STAC Fast API database logic.

### STAC
The STAC component powers a Fast API front end that allows for interacting with the OpenSearch database that houses
the processed geospatial assets.

### Table of Contents
* [Getting Started](#getting-started)
    * [Prerequisites](#prerequisites)
    * [Installation Guide](#installation-guide)
    * [Documentation](#documentation)
* [Testing Your Setup](#testing-your-setup)
* [Support & Feedback](#support--feedback)
* [Security](#security)
* [License](#license)


## Getting Started
### Prerequisites

First, ensure you have installed the following tools locally

1. [aws cli](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
2. [docker](https://nodejs.org/en)
3. [tox](https://tox.wiki/en/latest/installation.html)

### Installation Guide

1. Clone `osml-data-intake` package into your desktop

```sh
git clone https://github.com/aws-solutions-library-samples/osml-data-intake.git
```

2. Run `tox` to create a virtual environment

```sh
cd osml-data-intake
tox
```

### Documentation

You can find documentation for this library in the `./doc` directory. Sphinx is used to construct a searchable HTML
version of the API documents.

```shell
tox -e docs
```

## Testing Your Setup

After setting up your environment, you can verify your setup by sending a test message to the SNS topic that will trigger your application workflow. This is useful for ensuring that your processing pipeline works correctly with a given image.

**Prerequisites:**
- Ensure that your AWS credentials are configured properly in the environment.
- Make sure that you have the AWS CLI installed and configured.
- Deploy the osml-data-intake infrastructure using the [guidance package](https://github.com/aws-solutions-library-samples/guidance-for-processing-overhead-imagery-on-aws)

## Testing Data Intake

**Run the Test Command:**

1. Replace the following with your specific details: \
  **Topic ARN**: Update the `--topic-arn` argument with the ARN of the SNS topic that triggers your application.\
  **S3 URL**: Replace the S3 URL in the `--message` argument with the URL of the image file you want to test.

2. Execute the following command, substituting your actual values:
    ```bash
    python3 bin/intake_cli.py --topic-arn <YOUR_TOPIC_ARN> --s3-uri <YOUR_S3_URI>
    ```

3. Validate Expected Output:\
  This will trigger the processing of the specified image file in your application.
  Verify that the auxiliary files are generated and uploaded to your configured S3 bucket,
  and ensure that the logs indicate a successful run.

## Testing Data Catalog
1. To put a test item directly in your STAC catalog, update the following command and run it with your endpoint:
    ```bash
    curl -X "POST" "<<YOUR_API_URL>>/data-catalog/collections" \
         -H 'Content-Type: application/json; charset=utf-8' \
         -H "Authorization: Bearer $TOKEN" \
         -d $'{
      "type": "Feature",
      "stac_version": "1.0.0",
      "id": "example-item",
      "properties": {
        "datetime": "2024-06-01T00:00:00Z",
        "start_datetime": "2024-06-01T00:00:00Z",
        "end_datetime": "2024-06-01T01:00:00Z"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [-104.99404, 39.75621],
            [-104.99404, 39.74575],
            [-104.97342, 39.74575],
            [-104.97342, 39.75621],
            [-104.99404, 39.75621]
          ]
        ]
      },
      "links": [
        {
          "rel": "self",
          "href": "http://example.com/catalog/example-item.json",
          "type": "application/json"
        },
        {
          "rel": "root",
          "href": "http://example.com/catalog/catalog.json",
          "type": "application/json"
        }
      ],
      "assets": {
        "thumbnail": {
          "href": "http://example.com/thumbs/example-item.jpg",
          "title": "Thumbnail",
          "type": "image/jpeg"
        },
        "data": {
          "href": "http://example.com/data/example-item.tif",
          "title": "Geospatial Data",
          "type": "image/tiff; application=geotiff"
        }
      },
      "collection": "example-collection-3"
    }'

    ```

2. To get your item run:
```bash
  curl -X "GET" "<<YOUR_API_URL>>/data-catalog/collections"`
```

## Support & Feedback

To post feedback, submit feature ideas, or report bugs, please use the [Issues](https://github.com/aws-solutions-library-samples/osml-data-intake/issues) section of this GitHub repo.

If you are interested in contributing to OversightML Data Intake, see the [CONTRIBUTING](https://github.com/aws-solutions-library-samples/osml-data-intake/CONTRIBUTING.md) guide.

## Security

See [CONTRIBUTING](https://github.com/aws-solutions-library-samples/osml-data-intake/CONTRIBUTING.md) for more information.

## License

MIT No Attribution Licensed. See [LICENSE](https://github.com/aws-solutions-library-samples/osml-data-intake/LICENSE).
