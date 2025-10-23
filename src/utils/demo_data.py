"""
Demo data generator for Terrain Tunneling Calculator.

This module provides utilities for generating realistic demo contour data
for testing and demonstration purposes.
"""

import numpy as np
import json
from typing import List, Dict, Any, Tuple
from datetime import datetime

from models.contour_data import ContourData, ContourLine, ContourMetadata, CoordinateSystem
from utils.file_utils import FileUtils


class DemoDataGenerator:
    """Generator for demo contour data."""

    def __init__(self):
        self.file_utils = FileUtils()

    def generate_hill_terrain(self, size: float = 100.0, num_contours: int = 10,
                             complexity: str = "medium") -> ContourData:
        """
        Generate a simple hill terrain with concentric contours.

        Args:
            size: Size of the terrain area
            num_contours: Number of contour lines
            complexity: Terrain complexity ("simple", "medium", "complex")

        Returns:
            ContourData object with generated terrain
        """
        # Create elevation levels
        min_elevation = 100.0
        max_elevation = 150.0
        elevations = np.linspace(min_elevation, max_elevation, num_contours)

        contours = []
        center_x, center_y = size / 2, size / 2

        for i, elevation in enumerate(elevations):
            # Calculate radius for this elevation (higher elevation = smaller radius)
            radius_factor = 1.0 - (elevation - min_elevation) / (max_elevation - min_elevation)
            max_radius = size * 0.45 * radius_factor

            # Generate contour points
            if complexity == "simple":
                num_points = 20
                # Perfect circle
                angles = np.linspace(0, 2 * np.pi, num_points, endpoint=False)
                points = []
                for angle in angles:
                    x = center_x + max_radius * np.cos(angle)
                    y = center_y + max_radius * np.sin(angle)
                    points.append([x, y])

            elif complexity == "medium":
                num_points = 30
                # Slightly irregular circle
                angles = np.linspace(0, 2 * np.pi, num_points, endpoint=False)
                points = []
                for j, angle in enumerate(angles):
                    # Add some variation to radius
                    variation = 0.1 * np.sin(j * 3) * np.cos(j * 2)
                    radius = max_radius * (1 + variation)
                    x = center_x + radius * np.cos(angle)
                    y = center_y + radius * np.sin(angle)
                    points.append([x, y])

            else:  # complex
                num_points = 50
                # Irregular shape with multiple variations
                angles = np.linspace(0, 2 * np.pi, num_points, endpoint=False)
                points = []
                for j, angle in enumerate(angles):
                    # Multiple frequency variations
                    variation1 = 0.15 * np.sin(j * 2)
                    variation2 = 0.1 * np.cos(j * 5)
                    variation3 = 0.05 * np.sin(j * 7)
                    radius = max_radius * (1 + variation1 + variation2 + variation3)

                    # Add slight offset to center for each contour
                    offset_x = 5 * np.sin(i * 0.5)
                    offset_y = 5 * np.cos(i * 0.5)

                    x = center_x + offset_x + radius * np.cos(angle)
                    y = center_y + offset_y + radius * np.sin(angle)
                    points.append([x, y])

            # Close the contour
            if not points or (len(points) > 0 and not np.allclose(points[0], points[-1])):
                points.append(points[0])

            contour = ContourLine(
                elevation=float(elevation),
                points=np.array(points),
                is_closed=True
            )
            contours.append(contour)

        # Create metadata
        metadata = ContourMetadata(
            name="Demo Hill Terrain",
            units="meters",
            coordinate_system=CoordinateSystem.LOCAL,
            created_date=datetime.now().isoformat(),
            source="generated",
            description="Simple hill terrain with concentric contour lines"
        )

        # Create bounding box
        margin = 5.0
        bounds = self._create_bounds_from_contours(contours, margin)

        return ContourData(
            metadata=metadata,
            contours=contours,
            bounds=bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )

    def generate_valley_terrain(self, width: float = 150.0, depth: float = 100.0,
                               num_contours: int = 12) -> ContourData:
        """
        Generate a valley terrain with U-shaped contours.

        Args:
            width: Width of the valley
            depth: Depth of the valley
            num_contours: Number of contour lines

        Returns:
            ContourData object with generated terrain
        """
        min_elevation = 120.0
        max_elevation = 140.0
        elevations = np.linspace(min_elevation, max_elevation, num_contours)

        contours = []

        for elevation in reversed(elevations):
            # Calculate valley width at this elevation
            elevation_factor = (elevation - min_elevation) / (max_elevation - min_elevation)
            valley_width = width * (0.3 + 0.7 * elevation_factor)

            points = []
            num_points = 40

            # Left side of valley
            for i in range(num_points // 2):
                y = i * depth / (num_points // 2)
                x = valley_width / 2 + (width - valley_width) * (1 - y / depth)
                points.append([x, y])

            # Bottom of valley
            points.append([valley_width / 2, depth])

            # Right side of valley
            for i in range(num_points // 2, 0, -1):
                y = i * depth / (num_points // 2)
                x = valley_width / 2 + (width - valley_width) * (1 - y / depth)
                points.append([x, y])

            contour = ContourLine(
                elevation=float(elevation),
                points=np.array(points),
                is_closed=True
            )
            contours.append(contour)

        # Create metadata
        metadata = ContourMetadata(
            name="Demo Valley Terrain",
            units="meters",
            coordinate_system=CoordinateSystem.LOCAL,
            created_date=datetime.now().isoformat(),
            source="generated",
            description="U-shaped valley terrain"
        )

        # Create bounding box
        margin = 5.0
        bounds = self._create_bounds_from_contours(contours, margin)

        return ContourData(
            metadata=metadata,
            contours=contours,
            bounds=bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )

    def generate_ridge_terrain(self, length: float = 200.0, width: float = 80.0,
                               height: float = 60.0, num_contours: int = 8) -> ContourData:
        """
        Generate a ridge terrain with elongated contours.

        Args:
            length: Length of the ridge
            width: Width of the ridge base
            height: Height of the ridge peak
            num_contours: Number of contour lines

        Returns:
            ContourData object with generated terrain
        """
        min_elevation = 100.0
        max_elevation = min_elevation + height
        elevations = np.linspace(min_elevation, max_elevation, num_contours)

        contours = []

        for elevation in elevations:
            # Calculate ridge width at this elevation
            elevation_factor = (elevation - min_elevation) / height
            ridge_width = width * (1 - 0.8 * elevation_factor)

            # Create elongated contour
            points = []
            num_points = 60

            for i in range(num_points):
                x = i * length / (num_points - 1)

                # Add some curve to the ridge
                curve_factor = 0.1 * np.sin(4 * np.pi * i / (num_points - 1))
                actual_width = ridge_width * (1 + curve_factor)

                # Points on both sides of ridge
                y = length / 2 + actual_width / 2
                points.append([x, y])
                points.append([x, length / 2 - actual_width / 2])

            # Close the contour
            points.append(points[0])

            contour = ContourLine(
                elevation=float(elevation),
                points=np.array(points),
                is_closed=True
            )
            contours.append(contour)

        # Create metadata
        metadata = ContourMetadata(
            name="Demo Ridge Terrain",
            units="meters",
            coordinate_system=CoordinateSystem.LOCAL,
            created_date=datetime.now().isoformat(),
            source="generated",
            description="Elongated ridge terrain with curved profile"
        )

        # Create bounding box
        margin = 5.0
        bounds = self._create_bounds_from_contours(contours, margin)

        return ContourData(
            metadata=metadata,
            contours=contours,
            bounds=bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )

    def create_complex_demo_data(self) -> ContourData:
        """
        Create a complex demo terrain combining multiple features.

        Returns:
            Complex ContourData object
        """
        # Generate base hill
        hill = self.generate_hill_terrain(size=200.0, num_contours=12, complexity="complex")

        # Add some additional features
        additional_contours = []

        # Add a small secondary peak
        for elevation in [125.0, 130.0, 135.0]:
            center_x, center_y = 150.0, 120.0
            max_radius = 25.0

            angles = np.linspace(0, 2 * np.pi, 25, endpoint=False)
            points = []
            for angle in angles:
                # Add some variation
                variation = 0.1 * np.sin(angle * 3)
                radius = max_radius * (1 + variation)
                x = center_x + radius * np.cos(angle)
                y = center_y + radius * np.sin(angle)
                points.append([x, y])

            points.append(points[0])  # Close contour

            contour = ContourLine(
                elevation=elevation,
                points=np.array(points),
                is_closed=True
            )
            additional_contours.append(contour)

        # Combine all contours
        all_contours = hill.contours + additional_contours

        # Update metadata
        metadata = ContourMetadata(
            name="Complex Demo Terrain",
            units="meters",
            coordinate_system=CoordinateSystem.LOCAL,
            created_date=datetime.now().isoformat(),
            source="generated",
            description="Complex terrain with main hill and secondary peak"
        )

        # Create bounding box
        margin = 10.0
        bounds = self._create_bounds_from_contours(all_contours, margin)

        return ContourData(
            metadata=metadata,
            contours=all_contours,
            bounds=bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )

    def save_demo_data(self, contour_data: ContourData, file_path: str) -> None:
        """
        Save demo contour data to a JSON file.

        Args:
            contour_data: ContourData object to save
            file_path: Output file path
        """
        # Convert to dictionary format
        data_dict = {
            "metadata": {
                "name": contour_data.metadata.name,
                "units": contour_data.metadata.units,
                "coordinate_system": contour_data.metadata.coordinate_system.value,
                "created_date": contour_data.metadata.created_date,
                "source": contour_data.metadata.source,
                "description": contour_data.metadata.description
            },
            "contours": []
        }

        for contour in contour_data.contours:
            contour_dict = {
                "elevation": contour.elevation,
                "points": contour.points.tolist(),
                "is_closed": contour.is_closed
            }
            data_dict["contours"].append(contour_dict)

        # Save to file
        self.file_utils.write_json_file(file_path, data_dict)

    def generate_all_demo_files(self, output_dir: str = "data/examples") -> None:
        """
        Generate all types of demo data files.

        Args:
            output_dir: Directory to save demo files
        """
        output_path = self.file_utils.ensure_directory_exists(output_dir)

        # Generate different terrain types
        terrains = [
            ("hill_terrain", self.generate_hill_terrain()),
            ("valley_terrain", self.generate_valley_terrain()),
            ("ridge_terrain", self.generate_ridge_terrain()),
            ("complex_terrain", self.create_complex_demo_data())
        ]

        for filename, contour_data in terrains:
            file_path = f"{output_dir}/{filename}.json"
            self.save_demo_data(contour_data, file_path)
            print(f"Generated demo data: {file_path}")

    def _create_bounds_from_contours(self, contours: List[ContourLine], margin: float) -> 'BoundingBox':
        """Create bounding box from contour points."""
        from utils.math_utils import BoundingBox

        if not contours:
            return BoundingBox(0, 0, 0, 0)

        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')

        for contour in contours:
            points = contour.points
            if len(points) > 0:
                min_x = min(min_x, np.min(points[:, 0]))
                max_x = max(max_x, np.max(points[:, 0]))
                min_y = min(min_y, np.min(points[:, 1]))
                max_y = max(max_y, np.max(points[:, 1]))

        return BoundingBox(
            min_x=min_x - margin,
            max_x=max_x + margin,
            min_y=min_y - margin,
            max_y=max_y + margin
        )