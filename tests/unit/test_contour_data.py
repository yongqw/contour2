"""
Unit tests for ContourData model.

These tests validate the contour data processing functionality,
including validation, elevation queries, and boundary calculations.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from src.models.contour_data import ContourData, ContourLine, ContourMetadata, CoordinateSystem
from src.utils.exceptions import ValidationError
from src.utils.math_utils import BoundingBox


class TestContourMetadata:
    """Test cases for ContourMetadata class."""

    def test_valid_metadata_creation(self):
        """Test creating valid metadata."""
        metadata = ContourMetadata(
            name="Test Terrain",
            units="meters",
            coordinate_system=CoordinateSystem.LOCAL
        )
        assert metadata.name == "Test Terrain"
        assert metadata.units == "meters"
        assert metadata.coordinate_system == CoordinateSystem.LOCAL
        assert metadata.validate() is True

    def test_empty_name_validation(self):
        """Test validation fails with empty name."""
        metadata = ContourMetadata(name="", units="meters")
        assert metadata.validate() is False

    def test_whitespace_name_validation(self):
        """Test validation fails with whitespace-only name."""
        metadata = ContourMetadata(name="   ", units="meters")
        assert metadata.validate() is False

    def test_invalid_units_validation(self):
        """Test validation fails with invalid units."""
        metadata = ContourMetadata(name="Test", units="inches")
        assert metadata.validate() is False


class TestContourLine:
    """Test cases for ContourLine class."""

    def test_valid_contour_creation(self):
        """Test creating a valid contour line."""
        points = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]])
        contour = ContourLine(elevation=100.0, points=points, is_closed=True)

        assert contour.elevation == 100.0
        assert contour.is_closed is True
        assert len(contour.points) == 5
        assert contour.points.shape == (5, 2)

    def test_invalid_points_shape(self):
        """Test contour creation fails with wrong points shape."""
        points = np.array([1.0, 2.0, 3.0])  # 1D array
        with pytest.raises(ValueError, match="must be a 2D array"):
            ContourLine(elevation=100.0, points=points)

    def test_insufficient_points(self):
        """Test contour creation fails with too few points."""
        points = np.array([[0.0, 0.0], [1.0, 1.0]])  # Only 2 points
        with pytest.raises(ValueError, match="must have at least 3 points"):
            ContourLine(elevation=100.0, points=points)

    def test_get_length_square(self):
        """Test length calculation for a square contour."""
        points = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]])
        contour = ContourLine(elevation=100.0, points=points)

        expected_length = 40.0  # 10 + 10 + 10 + 10
        assert abs(contour.get_length() - expected_length) < 0.001

    def test_get_area_square(self):
        """Test area calculation for a square contour."""
        points = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]])
        contour = ContourLine(elevation=100.0, points=points)

        expected_area = 100.0  # 10 * 10
        assert abs(contour.get_area() - expected_area) < 0.001

    def test_get_area_triangle(self):
        """Test area calculation for a triangular contour."""
        points = np.array([[5.0, 0.0], [10.0, 10.0], [0.0, 10.0], [5.0, 0.0]])
        contour = ContourLine(elevation=100.0, points=points)

        expected_area = 50.0  # Triangle area: base * height / 2
        assert abs(contour.get_area() - expected_area) < 0.001

    def test_contains_point_inside(self):
        """Test point inside contour detection."""
        points = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]])
        contour = ContourLine(elevation=100.0, points=points)

        assert contour.contains_point(5.0, 5.0) is True
        assert contour.contains_point(1.0, 1.0) is True

    def test_contains_point_outside(self):
        """Test point outside contour detection."""
        points = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]])
        contour = ContourLine(elevation=100.0, points=points)

        assert contour.contains_point(15.0, 5.0) is False
        assert contour.contains_point(-5.0, 5.0) is False
        assert contour.contains_point(5.0, 15.0) is False

    def test_contains_point_on_edge(self):
        """Test point on contour edge detection."""
        points = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]])
        contour = ContourLine(elevation=100.0, points=points)

        assert contour.contains_point(5.0, 0.0) is True  # On edge
        assert contour.contains_point(10.0, 5.0) is True  # On edge


class TestContourData:
    """Test cases for ContourData class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a simple contour data set
        self.metadata = ContourMetadata(
            name="Test Terrain",
            units="meters",
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Create some test contours
        self.contour1 = ContourLine(
            elevation=100.0,
            points=np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]),
            is_closed=True
        )

        self.contour2 = ContourLine(
            elevation=110.0,
            points=np.array([[2.0, 2.0], [8.0, 2.0], [8.0, 8.0], [2.0, 8.0], [2.0, 2.0]]),
            is_closed=True
        )

        self.bounds = BoundingBox(min_x=-5.0, max_x=15.0, min_y=-5.0, max_y=15.0)

        self.contour_data = ContourData(
            metadata=self.metadata,
            contours=[self.contour1, self.contour2],
            bounds=self.bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )

    def test_valid_contour_data_creation(self):
        """Test creating valid contour data."""
        assert self.contour_data.metadata.name == "Test Terrain"
        assert len(self.contour_data.contours) == 2
        assert self.contour_data.coordinate_system == CoordinateSystem.LOCAL

    def test_validation_success(self):
        """Test validation passes with valid data."""
        assert self.contour_data.validate() is True

    def test_validation_fails_with_no_contours(self):
        """Test validation fails with no contours."""
        empty_contour_data = ContourData(
            metadata=self.metadata,
            contours=[],
            bounds=self.bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )
        assert empty_contour_data.validate() is False

    def test_validation_fails_with_invalid_metadata(self):
        """Test validation fails with invalid metadata."""
        invalid_metadata = ContourMetadata(name="", units="meters")
        invalid_contour_data = ContourData(
            metadata=invalid_metadata,
            contours=[self.contour1],
            bounds=self.bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )
        assert invalid_contour_data.validate() is False

    def test_validation_fails_with_extreme_elevation(self):
        """Test validation fails with extreme elevation."""
        extreme_contour = ContourLine(
            elevation=15000.0,  # Too high
            points=np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]),
            is_closed=True
        )
        invalid_contour_data = ContourData(
            metadata=self.metadata,
            contours=[extreme_contour],
            bounds=self.bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )
        assert invalid_contour_data.validate() is False

    def test_get_elevation_at_inside_contour(self):
        """Test elevation lookup inside a contour."""
        # Point inside higher elevation contour should return that elevation
        elevation = self.contour_data.get_elevation_at(5.0, 5.0)
        assert elevation == 110.0  # Inside the inner contour

    def test_get_elevation_at_outside_contours(self):
        """Test elevation lookup outside all contours."""
        # Point outside all contours should return minimum elevation
        elevation = self.contour_data.get_elevation_at(12.0, 12.0)
        assert elevation == 100.0  # Minimum elevation

    def test_get_bounds(self):
        """Test getting bounding box."""
        bounds = self.contour_data.get_bounds()
        assert bounds == self.bounds

    def test_get_elevation_range(self):
        """Test getting elevation range."""
        min_elev, max_elev = self.contour_data.get_elevation_range()
        assert min_elev == 100.0
        assert max_elev == 110.0

    def test_get_contour_at_elevation_exact_match(self):
        """Test getting contour at exact elevation."""
        contour = self.contour_data.get_contour_at_elevation(100.0)
        assert contour is not None
        assert contour.elevation == 100.0

    def test_get_contour_at_elevation_tolerance(self):
        """Test getting contour with tolerance."""
        # Should find contour within tolerance
        contour = self.contour_data.get_contour_at_elevation(100.05, tolerance=0.1)
        assert contour is not None
        assert contour.elevation == 100.0

    def test_get_contour_at_elevation_out_of_range(self):
        """Test getting contour with elevation out of range."""
        contour = self.contour_data.get_contour_at_elevation(150.0, tolerance=0.1)
        assert contour is None

    def test_get_elevation_at_empty_contours(self):
        """Test elevation lookup with no contours."""
        empty_data = ContourData(
            metadata=self.metadata,
            contours=[],
            bounds=self.bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )
        elevation = empty_data.get_elevation_at(5.0, 5.0)
        assert elevation == 0.0

    def test_multiple_containing_contours(self):
        """Test point inside multiple overlapping contours returns highest elevation."""
        # Create overlapping contours
        outer_contour = ContourLine(
            elevation=100.0,
            points=np.array([[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0], [0.0, 0.0]]),
            is_closed=True
        )

        inner_contour = ContourLine(
            elevation=120.0,
            points=np.array([[5.0, 5.0], [15.0, 5.0], [15.0, 15.0], [5.0, 15.0], [5.0, 5.0]]),
            is_closed=True
        )

        overlapping_data = ContourData(
            metadata=self.metadata,
            contours=[outer_contour, inner_contour],
            bounds=self.bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Point inside both should return higher elevation
        elevation = overlapping_data.get_elevation_at(10.0, 10.0)
        assert elevation == 120.0


# Integration tests with mocking
class TestContourDataIntegration:
    """Integration tests for ContourData with external dependencies."""

    def test_contour_data_with_real_world_data(self):
        """Test with realistic contour data structure."""
        realistic_metadata = ContourMetadata(
            name="Mountain Pass Survey",
            units="meters",
            coordinate_system=CoordinateSystem.UTM,
            created_date="2025-10-20T12:00:00Z",
            source="survey_team",
            description="Mountain pass survey data from field measurements"
        )

        # Create realistic contour lines
        realistic_contours = []
        elevations = [950, 960, 970, 980, 990, 1000, 1010, 1020, 1030]

        for i, elevation in enumerate(elevations):
            # Simulate irregular contour shape
            num_points = 20 + i * 5
            angles = np.linspace(0, 2 * np.pi, num_points, endpoint=False)
            points = []

            for angle in angles:
                # Add realistic variation
                radius = 50 + i * 5
                variation = 0.1 * np.sin(angle * 3)
                noise = np.random.normal(0, 1)  # Small random noise

                r = radius * (1 + variation)
                x = 100 + r * np.cos(angle) + noise
                y = 100 + r * np.sin(angle) + noise
                points.append([x, y])

            # Close the contour
            points.append(points[0])

            contour = ContourLine(
                elevation=float(elevation),
                points=np.array(points),
                is_closed=True
            )
            realistic_contours.append(contour)

        realistic_bounds = BoundingBox(min_x=0, max_x=200, min_y=0, max_y=200)

        realistic_data = ContourData(
            metadata=realistic_metadata,
            contours=realistic_contours,
            bounds=realistic_bounds,
            coordinate_system=CoordinateSystem.UTM
        )

        # Should validate successfully
        assert realistic_data.validate() is True
        assert len(realistic_data.contours) == len(elevations)
        assert realistic_data.get_elevation_range() == (950.0, 1030.0)

    def test_performance_with_large_dataset(self):
        """Test performance with large contour datasets."""
        import time

        # Create large dataset
        large_contours = []
        for i in range(100):  # 100 contours
            num_points = 500
            angles = np.linspace(0, 2 * np.pi, num_points, endpoint=False)
            points = []

            for angle in angles:
                radius = 1000 + i * 10
                x = 5000 + radius * np.cos(angle)
                y = 5000 + radius * np.sin(angle)
                points.append([x, y])

            points.append(points[0])

            contour = ContourLine(
                elevation=1000 + i * 10,
                points=np.array(points),
                is_closed=True
            )
            large_contours.append(contour)

        large_bounds = BoundingBox(min_x=0, max_x=10000, min_y=0, max_y=10000)

        large_data = ContourData(
            metadata=self.metadata,
            contours=large_contours,
            bounds=large_bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Test performance
        start_time = time.time()
        result = large_data.validate()
        end_time = time.time()

        # Should complete quickly even with large dataset
        assert end_time - start_time < 1.0  # Less than 1 second
        assert result is True

        # Test elevation lookup performance
        start_time = time.time()
        for _ in range(100):
            large_data.get_elevation_at(5000.0, 5000.0)
        end_time = time.time()

        # Should handle 100 lookups quickly
        assert end_time - start_time < 0.1  # Less than 100ms for 100 lookups


if __name__ == "__main__":
    pytest.main([__file__])