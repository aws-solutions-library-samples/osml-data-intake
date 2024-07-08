#  Copyright 2024 Amazon.com, Inc. or its affiliates.

import json
import time
from math import ceil, degrees, log
from typing import List, Optional

from osgeo import gdal

from aws.osml.gdal.gdal_utils import load_gdal_dataset
from aws.osml.photogrammetry.coordinates import ImageCoordinate
from aws.osml.photogrammetry.sensor_model import SensorModel
from src.aws.osml.data_intake.utils.logger import logger

gdal.UseExceptions()


class ImageData:
    def __init__(self, source_file: str) -> None:
        """
        Initialize the ImageData object.

        :param source_file: The source image file path.
        :returns: None
        """
        self.image_hash = None
        self.source_file = source_file
        self.dataset: Optional[gdal.Dataset] = None
        self.sensor_model: Optional[SensorModel] = None
        self.geo_polygon: Optional[List[List[float]]] = None
        self.geo_bbox: Optional[
            tuple[float | int, float | int, float | int, float | int]
            | tuple[float | int, float | int, float | int, float | int, float | int, float | int]
        ] = None
        self.width: Optional[int] = None
        self.height: Optional[int] = None
        self.image_corners: Optional[List[List[float]]] = None
        self.generate_metadata()

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
        Calculates geographic coordinates from the given image corners.

        :returns: None
        """
        coordinates = []
        for corner in self.image_corners:
            world_coordinate = self.sensor_model.image_to_world(ImageCoordinate(corner))
            coordinates.append((degrees(world_coordinate.longitude), degrees(world_coordinate.latitude)))
        coordinates.append(coordinates[0])
        self.geo_polygon = coordinates

    def calculate_bbox(self) -> None:
        """
        Calculate the bounding box (bbox) for a GeoJSON polygon.

        :returns: None
        Example of polygon format:
        polygon = [
            [100.0, 0.0],    # First vertex
            [101.0, 0.0],    # Second vertex
            [101.0, 1.0],    # Third vertex
            [100.0, 1.0],    # Fourth vertex
            [100.0, 0.0]     # Closing vertex (same as first vertex)
        ]
        """
        min_lon = min(coord[0] for coord in self.geo_polygon)
        min_lat = min(coord[1] for coord in self.geo_polygon)
        max_lon = max(coord[0] for coord in self.geo_polygon)
        max_lat = max(coord[1] for coord in self.geo_polygon)

        self.geo_bbox = [min_lon, min_lat, max_lon, max_lat]

    def generate_ovr_file(self, preview_size: int = 1024) -> str:
        """
        Generates an .ovr overview file using the given dataset.

        :param preview_size: The size of the preview to be generated.
        :returns: Path to the generated overview file.
        """
        ovr_file = self.source_file + ".ovr"
        min_side = min(self.width, self.height)
        num_overviews = ceil(log(min_side / preview_size) / log(2))
        overviews = [2**i for i in range(1, num_overviews + 1)] if num_overviews > 0 else []
        self.dataset.BuildOverviews("CUBIC", overviews)
        logger.info(f"Generated overview file {ovr_file}")

        return self.source_file + ".ovr"

    def generate_aux_file(self) -> str:
        """
        Generates an .aux file for the given dataset.

        :returns: Path to the generated aux.xml file.
        """
        gdal.SetConfigOption("GDAL_PAM_ENABLED", "YES")
        aux_file = self.source_file + ".aux.xml"
        logger.info(f"Calculating image statistics for {self.source_file}")
        start_time = time.perf_counter()
        temp_ds = gdal.Open(self.source_file)
        gdal.Info(temp_ds, stats=True, approxStats=True, computeMinMax=True, reportHistograms=True)
        del temp_ds
        end_time = time.perf_counter()
        logger.info(f"Generated aux file in {end_time - start_time} seconds")

        return aux_file

    def generate_gdalinfo(self) -> str:
        """
        Writes the full gdalinfo report to a text file.

        :returns: The path the GDAL info file
        """
        info_file = self.source_file + "_gdalinfo.txt"
        logger.info(f"Writing gdalinfo report to {info_file}")
        with open(info_file, "w") as f:
            gdal_info_report = json.dumps(gdal.Info(self.dataset, format="json"))
            f.write(gdal_info_report)
        logger.info(f"gdalinfo report written to {info_file}")

        return info_file

    def generate_thumbnail(self, width: int = 512, height: int = 512) -> str:
        """
        Generates a thumbnail image from a source image.

        :param width: The width, in pixels, to assign the thumbnail.
        :param height: The height, in pixels, to assign the thumbnail.
        :returns: The path the generated thumbnail
        """
        gdal.SetConfigOption("GDAL_PAM_ENABLED", "NO")
        # Set the gdal options for Translate
        translate_options = gdal.TranslateOptions(
            format="PNG", width=width, height=height, outputType=gdal.GDT_Byte, creationOptions=["COMPRESS=NONE"]
        )

        # Generate and save the thumbnail as a PNG
        thumbnail_file = self.source_file + ".thumbnail.png"

        gdal.Translate(destName=thumbnail_file, srcDS=self.dataset, options=translate_options)
        gdal.SetConfigOption("GDAL_PAM_ENABLED", "NO")
        return thumbnail_file

    def clean_dataset(self) -> None:
        """
        Cleans up the dataset GDAL creates.

        :returns: None
        """
        self.dataset = None
