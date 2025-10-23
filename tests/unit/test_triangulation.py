"""
Unit tests for triangulation algorithm.

These tests validate the Delaunay triangulation functionality,
including point reduction, triangle quality filtering, and mesh generation.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from src.services.triangulation import TriangulationService
from src.models.contour_data import ContourData, ContourLine, ContourMetadata, CoordinateSystem
from src.models.terrain_mesh import TerrainMesh, Triangle
from src.utils.math_utils import BoundingBox
from src.utils.exceptions import TriangulationError, ValidationError


class TestTriangulationService:
    """Test cases for TriangulationService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.triangulation_service = TriangulationService()

        # Create simple test contour data
        self.metadata = ContourMetadata(
            name="Test Terrain",
            units="meters",
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Create a simple square contour
        self.square_contour = ContourLine(
            elevation=100.0,
            points=np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]),
            is_closed=True
        )

        # Create a simple rectangular contour
        self.rect_contour = ContourLine(
            elevation=110.0,
            points=np.array([[2.0, 2.0], [8.0, 2.0], [8.0, 8.0], [2.0, 8.0], [2.0, 2.0]]),
            is_closed=True
        )

        self.bounds = BoundingBox(min_x=-5.0, max_x=15.0, min_y=-5.0, max_y=15.0)

        self.contour_data = ContourData(
            metadata=self.metadata,
            contours=[self.square_contour, self.rect_contour],
            bounds=self.bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )

    def test_triangulate_simple_contours(self):
        """Test triangulation of simple rectangular contours."""
        mesh = self.triangulation_service.triangulate_contours(self.contour_data)

        assert isinstance(mesh, TerrainMesh)
        assert len(mesh.vertices) > 0
        assert len(mesh.triangles) > 0
        assert mesh.vertex_count == len(mesh.vertices)
        assert mesh.triangle_count == len(mesh.triangles)

        # Verify mesh has reasonable number of triangles for simple geometry
        assert len(mesh.triangles) > 10  # Should have multiple triangles
        assert len(mesh.triangles) < 1000  # But not too many

    def test_triangulate_empty_contours(self):
        """Test triangulation with no contours."""
        empty_contour_data = ContourData(
            metadata=self.metadata,
            contours=[],
            bounds=self.bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )

        with pytest.raises(TriangulationError, match="No contours to triangulate"):
            self.triangulation_service.triangulate_contours(empty_contour_data)

    def test_triangulate_single_point_contours(self):
        """Test triangulation with contours that have too few points."""
        single_point_contour = ContourLine(
            elevation=100.0,
            points=np.array([[5.0, 5.0]]),  # Only 1 point
            is_closed=True
        )

        invalid_contour_data = ContourData(
            metadata=self.metadata,
            contours=[single_point_contour],
            bounds=self.bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )

        with pytest.raises(TriangulationError, match="Insufficient points for triangulation"):
            self.triangulation_service.triangulate_contours(invalid_contour_data)

    def test_point_reduction_algorithm(self):
        """Test point reduction algorithm for performance optimization."""
        # Create contour with many collinear points
        points = []
        for i in range(100):
            x = i * 0.1
            y = 5.0  # Constant y (collinear)
            points.append([x, y])
        points.append(points[0])  # Close contour

        dense_contour = ContourLine(
            elevation=100.0,
            points=np.array(points),
            is_closed=True
        )

        contour_data = ContourData(
            metadata=self.metadata,
            contours=[dense_contour],
            bounds=BoundingBox(min_x=0, max_x=10, min_y=0, max_y=10),
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Test with reduction enabled
        reduced_points = self.triangulation_service._reduce_points(
            dense_contour.points, tolerance=0.5
        )

        # Should significantly reduce number of points while preserving shape
        assert len(reduced_points) < len(dense_contour.points)
        assert len(reduced_points) >= 3  # At least 3 points needed

    def test_point_reduction_preserves_shape(self):
        """Test that point reduction preserves contour shape."""
        # Create an L-shaped contour
        points = [
            [0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [5.0, 5.1], [5.0, 5.2],
            [5.0, 10.0], [4.9, 10.0], [4.8, 10.0], [0.0, 10.0], [0.0, 0.0]
        ]

        contour = ContourLine(
            elevation=100.0,
            points=np.array(points),
            is_closed=True
        )

        reduced_points = self.triangulation_service._reduce_points(
            contour.points, tolerance=0.1
        )

        # Should preserve key corner points
        corners = [[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [5.0, 10.0], [0.0, 10.0]]

        for corner in corners:
            # Find closest point in reduced set
            distances = np.linalg.norm(reduced_points - np.array(corner), axis=1)
            min_distance = np.min(distances)
            assert min_distance < 0.5  # Corner should be preserved within tolerance

    def test_triangle_quality_filtering(self):
        """Test triangle quality filtering to remove sliver triangles."""
        # Create mesh with known poor quality triangles
        vertices = np.array([
            [0.0, 0.0, 100.0],
            [10.0, 0.0, 100.0],
            [5.0, 0.001, 100.0],  # Very skinny triangle (almost collinear)
            [5.0, 5.0, 110.0],
            [0.0, 10.0, 100.0],
            [10.0, 10.0, 100.0]
        ])

        # Create some triangles including a skinny one
        triangles = [
            Triangle(vertex_indices=[0, 1, 2]),  # Skinny triangle
            Triangle(vertex_indices=[0, 1, 3]),  # Good triangle
            Triangle(vertex_indices=[1, 4, 5]),  # Good triangle
        ]

        mesh = TerrainMesh(vertices=vertices, triangles=triangles)

        # Filter out poor quality triangles
        filtered_mesh = self.triangulation_service._filter_triangles_by_quality(
            mesh, min_angle=15.0, max_aspect_ratio=5.0
        )

        # Should have fewer triangles after filtering
        assert len(filtered_mesh.triangles) < len(mesh.triangles)
        assert len(filtered_mesh.triangles) >= 1  # At least one good triangle should remain

    def test_calculate_triangle_quality_metrics(self):
        """Test calculation of triangle quality metrics."""
        # Equilateral triangle (high quality)
        equilateral_vertices = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.5, np.sqrt(3)/2, 0.0]
        ])

        min_angle, aspect_ratio = self.triangulation_service._calculate_triangle_quality(
            equilateral_vertices
        )

        # Equilateral triangle should have good quality metrics
        assert abs(min_angle - 60.0) < 1.0  # All angles are 60 degrees
        assert aspect_ratio < 1.5  # Low aspect ratio

        # Very skinny triangle (low quality)
        skinny_vertices = np.array([
            [0.0, 0.0, 0.0],
            [10.0, 0.0, 0.0],
            [5.0, 0.001, 0.0]  # Almost collinear
        ])

        min_angle_skinny, aspect_ratio_skinny = self.triangulation_service._calculate_triangle_quality(
            skinny_vertices
        )

        # Skinny triangle should have poor quality metrics
        assert min_angle_skinny < 1.0  # Very small angle
        assert aspect_ratio_skinny > 100.0  # High aspect ratio

    def test_triangulation_performance_large_dataset(self):
        """Test triangulation performance with large datasets."""
        import time

        # Create contour data with many points
        large_contours = []
        for i in range(10):  # 10 contours
            elevation = 100.0 + i * 10.0
            points = []
            for j in range(50):  # 50 points per contour
                angle = 2 * np.pi * j / 50
                radius = 10.0 + i
                x = radius * np.cos(angle)
                y = radius * np.sin(angle)
                points.append([x, y])
            points.append(points[0])  # Close contour

            contour = ContourLine(
                elevation=elevation,
                points=np.array(points),
                is_closed=True
            )
            large_contours.append(contour)

        large_contour_data = ContourData(
            metadata=self.metadata,
            contours=large_contours,
            bounds=BoundingBox(min_x=-20, max_x=20, min_y=-20, max_y=20),
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Test performance
        start_time = time.time()
        mesh = self.triangulation_service.triangulate_contours(large_contour_data)
        end_time = time.time()

        # Should complete within reasonable time
        assert end_time - start_time < 3.0  # Less than 3 seconds
        assert len(mesh.vertices) > 100
        assert len(mesh.triangles) > 50

    def test_triangulation_with_concentric_contours(self):
        """Test triangulation with concentric circular contours."""
        contours = []

        # Create concentric circles
        for radius in [5.0, 10.0, 15.0]:
            points = []
            for i in range(20):
                angle = 2 * np.pi * i / 20
                x = radius * np.cos(angle)
                y = radius * np.sin(angle)
                points.append([x, y])
            points.append(points[0])

            contour = ContourLine(
                elevation=100.0 + radius,
                points=np.array(points),
                is_closed=True
            )
            contours.append(contour)

        concentric_data = ContourData(
            metadata=self.metadata,
            contours=contours,
            bounds=BoundingBox(min_x=-20, max_x=20, min_y=-20, max_y=20),
            coordinate_system=CoordinateSystem.LOCAL
        )

        mesh = self.triangulation_service.triangulate_contours(concentric_data)

        # Should create a proper mesh between concentric contours
        assert len(mesh.triangles) > 0
        assert mesh.vertex_count > 0

        # Check that mesh spans the area between contours
        x_coords = mesh.vertices[:, 0]
        y_coords = mesh.vertices[:, 1]

        assert np.min(x_coords) <= -15.0  # Should include outer contour
        assert np.max(x_coords) >= 15.0
        assert np.min(y_coords) <= -15.0
        assert np.max(y_coords) >= 15.0

    def test_handle_overlapping_contours(self):
        """Test triangulation with overlapping contours at same elevation."""
        # Create two overlapping contours at same elevation
        contour1 = ContourLine(
            elevation=100.0,
            points=np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]),
            is_closed=True
        )

        contour2 = ContourLine(
            elevation=100.0,  # Same elevation
            points=np.array([[5.0, 5.0], [15.0, 5.0], [15.0, 15.0], [5.0, 15.0], [5.0, 5.0]]),
            is_closed=True
        )

        overlapping_data = ContourData(
            metadata=self.metadata,
            contours=[contour1, contour2],
            bounds=BoundingBox(min_x=-5, max_x=20, min_y=-5, max_y=20),
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Should handle overlapping contours gracefully
        mesh = self.triangulation_service.triangulate_contours(overlapping_data)
        assert len(mesh.triangles) > 0

    def test_validate_mesh_integrity(self):
        """Test validation of generated mesh integrity."""
        mesh = self.triangulation_service.triangulate_contours(self.contour_data)

        # Validate mesh
        is_valid, issues = self.triangulation_service.validate_mesh(mesh)

        assert is_valid is True
        assert len(issues) == 0

        # Test with invalid mesh (corrupted triangle indices)
        invalid_triangles = [
            Triangle(vertex_indices=[0, 1, 999])  # Invalid vertex index
        ]
        invalid_mesh = TerrainMesh(vertices=mesh.vertices, triangles=invalid_triangles)

        is_valid_invalid, issues_invalid = self.triangulation_service.validate_mesh(invalid_mesh)

        assert is_valid_invalid is False
        assert len(issues_invalid) > 0

    def test_triangulation_service_configuration(self):
        """Test triangulation service configuration parameters."""
        # Create service with custom configuration
        config = {
            'point_reduction_tolerance': 0.01,
            'min_triangle_angle': 10.0,
            'max_triangle_aspect_ratio': 3.0,
            'max_points_per_contour': 1000
        }

        custom_service = TriangulationService(config=config)

        assert custom_service.point_reduction_tolerance == 0.01
        assert custom_service.min_triangle_angle == 10.0
        assert custom_service.max_triangle_aspect_ratio == 3.0
        assert custom_service.max_points_per_contour == 1000

    def test_memory_usage_during_triangulation(self):
        """Test memory usage during triangulation of large datasets."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create moderately large contour data
        large_contours = []
        for i in range(20):  # 20 contours
            points = []
            for j in range(100):  # 100 points per contour
                angle = 2 * np.pi * j / 100
                radius = 5.0 + i * 2
                x = radius * np.cos(angle) + i * 10
                y = radius * np.sin(angle) + i * 10
                points.append([x, y, 100.0 + i * 5])  # Include elevation
            points.append(points[0])

            contour = ContourLine(
                elevation=100.0 + i * 5,
                points=np.array(points),
                is_closed=True
            )
            large_contours.append(contour)

        large_data = ContourData(
            metadata=self.metadata,
            contours=large_contours,
            bounds=BoundingBox(min_x=-50, max_x=250, min_y=-50, max_y=250),
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Perform triangulation
        mesh = self.triangulation_service.triangulate_contours(large_data)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory usage should be reasonable (less than 200MB increase)
        assert memory_increase < 200.0
        assert len(mesh.triangles) > 0

    @patch('scipy.spatial.Delaunay')
    def test_triangulation_failure_handling(self, mock_delaunay):
        """Test handling of triangulation failures."""
        # Mock Delaunay to raise an exception
        mock_delaunay.side_effect = Exception("Delaunay triangulation failed")

        with pytest.raises(TriangulationError, match="Triangulation failed"):
            self.triangulation_service.triangulate_contours(self.contour_data)


if __name__ == "__main__":
    pytest.main([__file__])