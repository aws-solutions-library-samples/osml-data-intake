#  Copyright 2024 Amazon.com, Inc. or its affiliates.

import logging
import time
from math import ceil, degrees, log
from typing import List, Optional

from osgeo import gdal

from aws.osml.gdal.gdal_utils import load_gdal_dataset
from aws.osml.photogrammetry.coordinates import ImageCoordinate
from aws.osml.photogrammetry.sensor_model import SensorModel

from .lambda_logger import logger

gdal.UseExceptions()


class ImageData:
    def __init__(self, source_file: str) -> None:
        """
        Initialize the ImageData object.

        :param source_file: The source image file path.
        :param logger: The configured logger instance
        :returns: None
        """
        self.source_file = source_file
        self.aux_file = source_file + ".aux.xml"
        self.ovr_file = source_file + ".ovr"
        self.geo_polygon: Optional[List[List[float]]] = None
        self.geo_bbox: Optional[List[float]] = None
        self.generate_metadata()

    def generate_metadata(self) -> None:
        """
        Calculate image metadata and build auxiliary files like .ovr and .aux.
        """
        logging.info(f"Calculating metadata for {self.source_file}")
        start_time = time.perf_counter()

        # Load the gdal dataset and sensor model for image
        dataset, sensor_model = load_gdal_dataset(self.source_file)

        # Grab the width and height of the image
        width, height = dataset.RasterXSize, dataset.RasterYSize

        # Calculate the image corners to work with
        image_corners = [[0, 0], [width, 0], [width, height], [0, height]]

        # Calculate geographic coordinates for the polygon
        self.calculate_geo_polygon(sensor_model, image_corners)
        self.calculate_bbox()

        # Generate .ovr and .aux files
        self.generate_overview(dataset, width, height)
        self.generate_aux_file(dataset)

        # Clean up the dataset
        del dataset

        # Log processing time
        logger.info(f"\nProcessing time: {time.perf_counter() - start_time} for {self.source_file}")

    def calculate_geo_polygon(self, sensor_model: SensorModel, image_corners: List[List[int]]) -> None:
        """
        Calculates geographic coordinates from the given image corners.

        :param sensor_model: The sensor model object.
        :param image_corners: List of image corner coordinates.
        :returns: A list of geographic coordinates representing the polygon.
        """
        coordinates = []
        for corner in image_corners:
            world_coordinate = sensor_model.image_to_world(ImageCoordinate(corner))
            coordinates.append((degrees(world_coordinate.longitude), degrees(world_coordinate.latitude)))
        coordinates.append(coordinates[0])
        self.geo_polygon = coordinates

    def calculate_bbox(self) -> None:
        """
        Calculate the bounding box (bbox) for a GeoJSON polygon.

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

    @staticmethod
    def generate_overview(dataset: gdal.Dataset, width: int, height: int, preview_size: int = 1024):
        """
        Generates an .ovr overview file using the given dataset.

        :param dataset: The GDAL dataset object.
        :param width: The width of the dataset.
        :param height: The height of the dataset.
        :param preview_size: The size of the preview to be generated.
        """
        min_side = min(width, height)
        num_overviews = ceil(log(min_side / preview_size) / log(2))
        overviews = [2**i for i in range(1, num_overviews + 1)] if num_overviews > 0 else []
        dataset.BuildOverviews("CUBIC", overviews)

    @staticmethod
    def generate_aux_file(dataset: gdal.Dataset):
        """
        Generates an .aux file for the given dataset.

        :param dataset: The GDAL dataset object.
        """
        gdal.Info(dataset, stats=True, approxStats=True, computeMinMax=True, reportHistograms=True)
