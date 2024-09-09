#  Copyright 2024 Amazon.com, Inc. or its affiliates.

import json
import os
import time
from datetime import datetime, timezone
from math import ceil, degrees, log
from typing import Any, Dict, List, Optional

from osgeo import gdal
from stac_fastapi.types.stac import Item

from aws.osml.gdal.gdal_utils import load_gdal_dataset
from aws.osml.photogrammetry.coordinates import ImageCoordinate
from aws.osml.photogrammetry.sensor_model import SensorModel

from .managers import S3Manager, S3Url, SNSManager, SNSRequest
from .processor_base import ProcessorBase
from .utils import AsyncContextFilter, logger

os.environ["PROJ_LIB"] = "/opt/conda/envs/osml_data_intake/share/proj"

gdal.UseExceptions()


class ImageData:
    def __init__(self, source_file: str) -> None:
        """
        Initialize the ImageData object.

        :param source_file: The source image file path.
        :returns: None
        """
        self.source_file = source_file
        self.dataset: Optional[gdal.Dataset] = None
        self.sensor_model: Optional[SensorModel] = None
        self.geo_polygon: Optional[List[List[List[float]]]] = None
        self.geo_bbox: Optional[
            tuple[float | int, float | int, float | int, float | int]
            | tuple[float | int, float | int, float | int, float | int, float | int, float | int]
        ] = None
        self.width: Optional[int] = None
        self.height: Optional[int] = None
        self.image_corners: Optional[List[List[float]]] = None
        self.generate_metadata()
        self.aux_ext = ".aux.xml"
        self.gdalinfo_ext = ".gdalinfo.json"
        self.overview_ext = ".ovr"

    def generate_metadata(self) -> None:
        """
        Calculate image metadata and build auxiliary files like .ovr and .aux.
        :returns: None
        """
        logger.info(f"Calculating metadata for {self.source_file}")

        # Load the gdal dataset and sensor model for image
        self.dataset, self.sensor_model = load_gdal_dataset(self.source_file)

        # Grab the width and height of the image
        self.width, self.height = self.dataset.RasterXSize, self.dataset.RasterYSize

        # Calculate the image corners to work with
        self.image_corners = [[0, 0], [self.width, 0], [self.width, self.height], [0, self.height]]

        # Calculate geographic coordinates for the polygon
        self.calculate_geo_polygon()
        self.calculate_bbox()

    def calculate_geo_polygon(self) -> None:
        """
        Calculates geographic coordinates from the given image corners as a polygon
            https://geojson.org/geojson-spec.html

        :returns: None
        """
        coordinates = []
        for corner in self.image_corners:
            world_coordinate = self.sensor_model.image_to_world(ImageCoordinate(corner))
            coordinates.append((degrees(world_coordinate.longitude), degrees(world_coordinate.latitude)))
        coordinates.append(coordinates[0])
        self.geo_polygon = [coordinates]

    def calculate_bbox(self) -> None:
        """
        Calculate the bounding box (bbox) for a GeoJSON polygon.

        :returns: None
        Example of polygon format:
        polygon = [[
            [100.0, 0.0],    # First vertex
            [101.0, 0.0],    # Second vertex
            [101.0, 1.0],    # Third vertex
            [100.0, 1.0],    # Fourth vertex
            [100.0, 0.0]     # Closing vertex (same as first vertex)
        ]]
        """
        coords = self.geo_polygon[0]
        min_lon = min(coord[0] for coord in coords)
        min_lat = min(coord[1] for coord in coords)
        max_lon = max(coord[0] for coord in coords)
        max_lat = max(coord[1] for coord in coords)

        self.geo_bbox = [min_lon, min_lat, max_lon, max_lat]

    def generate_ovr_file(self, preview_size: int = 1024) -> Optional[str]:
        """
        Generates an .ovr overview file using the given dataset.

        :param preview_size: The size of the preview to be generated.
        :returns: Path to the generated overview file.
        """
        ovr_file = self.source_file + self.overview_ext

        existing_overviews = self.dataset.GetRasterBand(1).GetOverviewCount()

        new_full_path = None

        if existing_overviews > 0:
            logger.info("Existing internal overviews found.")
            directory_path = os.path.dirname(self.source_file)
            full_filename = os.path.basename(self.source_file)

            new_filename = f"{os.path.splitext(full_filename)[0]}_translated{os.path.splitext(full_filename)[1]}"
            new_full_path = os.path.join(directory_path, new_filename)
            gdal.Translate(new_full_path, self.dataset, width=self.width, height=self.height, overviewLevel=0)

        min_side = min(self.width, self.height)
        num_overviews = ceil(log(min_side / preview_size) / log(2))
        overviews = [2**i for i in range(1, num_overviews + 1)] if num_overviews > 0 else []

        if overviews:
            if new_full_path:
                new_dataset, new_sensor_model = load_gdal_dataset(new_full_path)
                ovr_file = new_full_path + self.overview_ext
                new_dataset.BuildOverviews("AVERAGE", overviews)
                # Clean up
                new_dataset = None
            else:
                self.dataset.BuildOverviews("AVERAGE", overviews)
            logger.info(f"Generated external overview file {ovr_file}")
            return ovr_file
        else:
            logger.info("No overviews to generate.")
            return None

    def generate_aux_file(self) -> str:
        """
        Generates an .aux file for the given dataset.

        :returns: Path to the generated aux.xml file.
        """
        gdal.SetConfigOption("GDAL_PAM_ENABLED", "YES")
        aux_file = self.source_file + self.aux_ext
        logger.info(f"Calculating image statistics for {self.source_file}")
        start_time = time.perf_counter()
        temp_ds = gdal.Open(self.source_file)
        gdal.Info(temp_ds, stats=True, approxStats=True, computeMinMax=True, reportHistograms=True)
        del temp_ds
        end_time = time.perf_counter()
        logger.info(f"Generated aux file, {aux_file} in {end_time - start_time} seconds")

        return aux_file

    def generate_gdalinfo(self) -> str:
        """
        Writes the full gdalinfo report to a text file.

        :returns: The path the GDAL info file
        """
        info_file = self.source_file + self.gdalinfo_ext
        logger.info(f"Writing gdalinfo report to {info_file}")
        with open(info_file, "w") as f:
            options = gdal.InfoOptions(stats=True, reportHistograms=True, format="json")
            gdal_info_report = json.dumps(gdal.Info(self.dataset, options=options))
            f.write(gdal_info_report)
        logger.info(f"gdalinfo report written to {info_file}")

        return info_file

    def generate_stac_item(
        self, s3_manager: S3Manager, item_id: str, collection_id: str, ovr_file, stac_catalog: str = ""
    ) -> Item:
        """
        Create and publish a STAC item using the configured SNS manager.

        :param: s3_manager: The s3 manager handling the source file.
        :param: collection_id: The ID of the STAC Item.
        :param: collection_id: The collection_id to place the STAC Item in.
        :param: stac_catalog: The catalog the item is intended for.
        :returns: The generated STAC item.
        :raises ClientError: If publishing to SNS fails.
        """
        logger.info("Creating STAC item.")
        key = s3_manager.s3_url.key
        assets = {
            "overview": {
                "href": "https://cu99me9cj3.execute-api.us-west-2.amazonaws.com/viewpoints",
                "title": "Image Overview",
                "type": "application/geotiff",
                "roles": ["overview"],
                "item_id": item_id,
                "collection_id": collection_id,
                "s3_uri": f"s3://{s3_manager.s3_url.bucket}/{key}",
                "tile_size": 512,
                "range_adjustment": "DRA",
            },
            "data": {
                "href": f"s3://{s3_manager.s3_url.bucket}/{key}",
                "title": "Source Image",
                "type": "image/tiff",
                "roles": ["data"],
            },
            "aux": {
                "href": f"s3://{s3_manager.output_bucket}/{item_id}/{key}{self.aux_ext}",
                "title": "Processed Auxiliary",
                "type": "application/xml",
                "roles": ["data"],
            },
            "info": {
                "href": f"s3://{s3_manager.output_bucket}/{item_id}/{key}{self.gdalinfo_ext}",
                "title": "GDAL Info",
                "type": "application/json",
                "roles": ["data"],
            },
        }
        if ovr_file:
            assets["ovr"] = {
                "href": f"s3://{s3_manager.output_bucket}/{item_id}/{key}{self.overview_ext}",
                "title": "Processed Overview",
                "type": "application/octet-stream",
                "roles": ["data"],
            }
        return Item(
            **{
                "id": item_id,
                "collection": collection_id,
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": self.geo_polygon},
                "bbox": self.geo_bbox,
                "properties": {
                    "datetime": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "description": f"STAC Item for image {s3_manager.s3_url.url}",
                },
                "assets": assets,
                "links": [{"href": stac_catalog, "rel": "self"}],
                "stac_version": "1.0.0",
            }
        )

    def clean_dataset(self) -> None:
        """
        Cleans up the dataset GDAL creates.

        :returns: None
        """
        self.dataset = None

    def delete_files(self, files: List) -> None:
        """
        Cleans up the leftover files
        :returns: None
        """
        for f in files:
            try:
                os.remove(f)
            except Exception as e:
                logger.error(f"Unable to delete the file, {f}, error: {e}")
                continue


class ImageProcessor(ProcessorBase):
    """
    Manages the entire image processing workflow in a serverless environment.

    :param message: The incoming SNS request message.
    """

    def __init__(self, message: str) -> None:
        """
        Initialize an ImageProcessor instance.

        :param message: The incoming SNS request message.
        :returns: None
        """
        self.s3_manager = S3Manager(os.getenv("OUTPUT_BUCKET", None))
        self.sns_manager = SNSManager(os.getenv("OUTPUT_TOPIC", None))
        self.sns_request = SNSRequest(**json.loads(message))

    def process(self) -> Dict[str, Any]:
        """
        Process the incoming SNS message, download and process the image, and publish the results.

        :returns: A response indicating the status of the process.
        :raises Exception: Raised if there is an error during processing incoming image.
        """
        try:
            AsyncContextFilter.set_context({"item_id": self.sns_request.item_id})
            # Extract the S3 information from the URI
            s3_url = S3Url(self.sns_request.image_uri)

            # Download the source image
            file_path = self.s3_manager.download_file(s3_url)

            # Create the image metadata files
            image_data = ImageData(file_path)

            # Generate info, aux, and ovr files
            info_file = image_data.generate_gdalinfo()
            aux_file = image_data.generate_aux_file()
            ovr_file = image_data.generate_ovr_file()

            # set the output folder to the item id
            self.s3_manager.set_output_folder(self.sns_request.item_id)

            # upload info, aux, ovr files file
            self.s3_manager.upload_file(info_file, "GDAL INFO", {"ContentType": "application/json"})
            self.s3_manager.upload_file(aux_file, "AUX", {"ContentType": "application/xml"})
            if ovr_file:
                self.s3_manager.upload_file(ovr_file, "OVR", {"ContentType": "image/tiff"})

            # Generate and publish the STAC item to the SNS topic
            stac_item = image_data.generate_stac_item(
                self.s3_manager, self.sns_request.item_id, self.sns_request.collection_id, ovr_file
            )
            self.sns_manager.publish_message(json.dumps(stac_item))

            # Clean up the GDAL dataset
            image_data.clean_dataset()

            # Return a response indicating success
            return self.success_message("Message processed successfully")

        except Exception as err:
            # Return a response indicating failure
            return self.failure_message(err)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    The AWS Lambda handler function to process an event.

    :param event: The event payload contains the SNS message.
    :param context: The Lambda execution context (unused).
    :return: The response from the ImageProcessor process.
    """
    # Log the event payload to see the raw SNS message
    message = event["Records"][0]["Sns"]["Message"]
    return ImageProcessor(message).process()
