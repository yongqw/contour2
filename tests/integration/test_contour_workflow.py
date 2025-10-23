"""
Integration tests for contour-to-3D workflow.

These tests validate the end-to-end workflow from loading contour files
to generating 3D terrain models, ensuring all components work together correctly.
"""

import pytest
import numpy as np
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.services.contour_parser import ContourParser
from src.services.triangulation import TriangulationService
from src.services.visualization_2d import Visualization2DService
from src.services.visualization_3d import Visualization3DService
from src.models.contour_data import ContourData, ContourLine, ContourMetadata, CoordinateSystem
from src.models.terrain_mesh import TerrainMesh, Triangle
from src.utils.math_utils import BoundingBox
from src.utils.exceptions import ContourError, ValidationError, TriangulationError


class TestContourWorkflow:
    """Integration tests for complete contour processing workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.parser = ContourParser()
        self.triangulation_service = TriangulationService()
        self.viz_2d = Visualization2DService()
        self.viz_3d = Visualization3DService()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_contour_file(self, filename: str) -> str:
        """Create a test contour file with realistic terrain data."""
        contour_data = {
            "metadata": {
                "name": "Integration Test Terrain",
                "units": "meters",
                "coordinate_system": "local",
                "created_date": "2025-10-20T12:00:00Z",
                "source": "integration_test",
                "description": "Test terrain for integration testing"
            },
            "contours": []
        }

        # Generate concentric contours with varying complexity
        base_center = [50.0, 50.0]
        elevations = [100.0, 105.0, 110.0, 115.0, 120.0, 125.0, 130.0]

        for i, elevation in enumerate(elevations):
            radius_factor = 1.0 - (i / len(elevations)) * 0.7
            base_radius = 30.0 * radius_factor

            points = []
            num_points = 20 + i * 5  # More points for outer contours

            for j in range(num_points):
                angle = 2 * np.pi * j / num_points

                # Add realistic variation
                variation = 0.1 * np.sin(angle * 3) * np.cos(angle * 2)
                noise = np.random.normal(0, 0.5)

                radius = base_radius * (1 + variation) + noise
                x = base_center[0] + radius * np.cos(angle)
                y = base_center[1] + radius * np.sin(angle)
                points.append([x, y])

            points.append(points[0])  # Close contour

            contour_data["contours"].append({
                "elevation": elevation,
                "points": points,
                "is_closed": True
            })

        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w') as f:
            json.dump(contour_data, f)

        return file_path

    def test_complete_workflow_simple_contours(self):
        """Test complete workflow from file to 3D visualization."""
        # Step 1: Create test contour file
        file_path = self.create_test_contour_file("simple_terrain.json")

        # Step 2: Parse contour file
        contour_data = self.parser.parse_file(file_path)
        assert isinstance(contour_data, ContourData)
        assert len(contour_data.contours) > 0

        # Step 3: Validate contour data
        self.parser.validate_contour_data(contour_data)

        # Step 4: Generate terrain mesh through triangulation
        mesh = self.triangulation_service.triangulate_contours(contour_data)
        assert isinstance(mesh, TerrainMesh)
        assert len(mesh.vertices) > 0
        assert len(mesh.triangles) > 0

        # Step 5: Validate mesh integrity
        is_valid, issues = self.triangulation_service.validate_mesh(mesh)
        assert is_valid is True
        assert len(issues) == 0

        # Step 6: Generate 2D visualization
        fig_2d = self.viz_2d.create_contour_plot(contour_data)
        assert fig_2d is not None

        # Step 7: Generate 3D visualization
        fig_3d = self.viz_3d.create_terrain_plot(mesh)
        assert fig_3d is not None

        # Verify workflow completed successfully
        assert contour_data.metadata.name == "Integration Test Terrain"
        assert mesh.vertex_count > 50  # Should have reasonable number of vertices
        assert mesh.triangle_count > 20  # Should have reasonable number of triangles

    def test_workflow_with_complex_terrain(self):
        """Test workflow with more complex terrain features."""
        # Create complex terrain with multiple features
        contour_data = {
            "metadata": {
                "name": "Complex Integration Terrain",
                "units": "meters",
                "coordinate_system": "local"
            },
            "contours": []
        }

        # Main hill contours
        center_x, center_y = 100.0, 100.0
        elevations = [90, 95, 100, 105, 110, 115, 120]

        for elevation in elevations:
            radius = 40.0 - (elevation - 90) * 2.0  # Higher elevation = smaller radius
            points = []

            for i in range(30):  # 30 points per contour
                angle = 2 * np.pi * i / 30

                # Add complex terrain variation
                variation1 = 0.15 * np.sin(angle * 2)
                variation2 = 0.1 * np.cos(angle * 5)

                r = radius * (1 + variation1 + variation2)
                x = center_x + r * np.cos(angle)
                y = center_y + r * np.sin(angle)
                points.append([x, y])

            points.append(points[0])

            contour_data["contours"].append({
                "elevation": float(elevation),
                "points": points,
                "is_closed": True
            })

        # Add secondary peak
        sec_center_x, sec_center_y = 140.0, 120.0
        for elevation in [105, 110, 115]:
            radius = 15.0 - (elevation - 105) * 2.0
            points = []

            for i in range(20):
                angle = 2 * np.pi * i / 20
                x = sec_center_x + radius * np.cos(angle)
                y = sec_center_y + radius * np.sin(angle)
                points.append([x, y])

            points.append(points[0])

            contour_data["contours"].append({
                "elevation": float(elevation),
                "points": points,
                "is_closed": True
            })

        file_path = os.path.join(self.temp_dir, "complex_terrain.json")
        with open(file_path, 'w') as f:
            json.dump(contour_data, f)

        # Process through complete workflow
        parsed_data = self.parser.parse_file(file_path)
        mesh = self.triangulation_service.triangulate_contours(parsed_data)

        # Verify complex terrain was processed correctly
        assert len(parsed_data.contours) == 10  # 7 main + 3 secondary
        assert mesh.vertex_count > 100
        assert mesh.triangle_count > 50

        # Check elevation range
        min_elev, max_elev = parsed_data.get_elevation_range()
        assert min_elev == 90.0
        assert max_elev == 120.0

    def test_workflow_error_handling_invalid_file(self):
        """Test workflow error handling with invalid contour file."""
        # Create invalid JSON file
        invalid_file = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json content")

        # Should fail at parsing stage
        with pytest.raises(Exception):  # Should raise InvalidContourFileError
            self.parser.parse_file(invalid_file)

    def test_workflow_error_handling_corrupted_contours(self):
        """Test workflow error handling with corrupted contour data."""
        # Create file with corrupted contour data
        corrupted_data = {
            "metadata": {
                "name": "Corrupted Terrain",
                "units": "meters",
                "coordinate_system": "local"
            },
            "contours": [
                {
                    "elevation": 100.0,
                    "points": [[0.0, 0.0]],  # Only 1 point - insufficient
                    "is_closed": True
                }
            ]
        }

        corrupted_file = os.path.join(self.temp_dir, "corrupted.json")
        with open(corrupted_file, 'w') as f:
            json.dump(corrupted_data, f)

        # Should fail at validation stage
        with pytest.raises(Exception):  # Should raise InvalidContourFileError
            self.parser.parse_file(corrupted_file)

    def test_workflow_performance_large_dataset(self):
        """Test workflow performance with large contour datasets."""
        import time

        # Create large contour dataset
        large_data = {
            "metadata": {
                "name": "Large Performance Test",
                "units": "meters",
                "coordinate_system": "local"
            },
            "contours": []
        }

        # Generate many contours
        for i in range(20):  # 20 contours
            elevation = 100.0 + i * 5.0
            radius = 50.0 - i * 2.0
            points = []

            for j in range(100):  # 100 points per contour
                angle = 2 * np.pi * j / 100
                x = radius * np.cos(angle) + np.random.normal(0, 0.5)
                y = radius * np.sin(angle) + np.random.normal(0, 0.5)
                points.append([x, y])

            points.append(points[0])

            large_data["contours"].append({
                "elevation": elevation,
                "points": points,
                "is_closed": True
            })

        large_file = os.path.join(self.temp_dir, "large_terrain.json")
        with open(large_file, 'w') as f:
            json.dump(large_data, f)

        # Measure workflow performance
        start_time = time.time()

        # Complete workflow
        contour_data = self.parser.parse_file(large_file)
        mesh = self.triangulation_service.triangulate_contours(contour_data)
        fig_2d = self.viz_2d.create_contour_plot(contour_data)
        fig_3d = self.viz_3d.create_terrain_plot(mesh)

        end_time = time.time()
        processing_time = end_time - start_time

        # Performance assertions
        assert processing_time < 5.0  # Should complete within 5 seconds
        assert len(contour_data.contours) == 20
        assert mesh.vertex_count > 500
        assert mesh.triangle_count > 200

    def test_workflow_visualization_output_consistency(self):
        """Test that visualization outputs are consistent with input data."""
        file_path = self.create_test_contour_file("consistency_test.json")

        # Process workflow
        contour_data = self.parser.parse_file(file_path)
        mesh = self.triangulation_service.triangulate_contours(contour_data)

        # Get elevation ranges
        contour_min_elev, contour_max_elev = contour_data.get_elevation_range()
        mesh_min_elev = np.min(mesh.vertices[:, 2])
        mesh_max_elev = np.max(mesh.vertices[:, 2])

        # Elevation ranges should be consistent (within tolerance)
        assert abs(contour_min_elev - mesh_min_elev) < 1.0
        assert abs(contour_max_elev - mesh_max_elev) < 1.0

        # Check that mesh covers the same geographic area
        contour_bounds = contour_data.get_bounds()
        mesh_x_coords = mesh.vertices[:, 0]
        mesh_y_coords = mesh.vertices[:, 1]

        assert np.min(mesh_x_coords) >= contour_bounds.min_x - 5.0
        assert np.max(mesh_x_coords) <= contour_bounds.max_x + 5.0
        assert np.min(mesh_y_coords) >= contour_bounds.min_y - 5.0
        assert np.max(mesh_y_coords) <= contour_bounds.max_y + 5.0

    def test_workflow_round_trip_data_preservation(self):
        """Test that data is preserved through parse -> process -> save -> parse cycle."""
        # Create original contour file
        original_file = self.create_test_contour_file("round_trip_original.json")

        # Parse and process
        original_data = self.parser.parse_file(original_file)

        # Save processed data
        saved_file = os.path.join(self.temp_dir, "round_trip_saved.json")
        self.parser.save_contour_data(original_data, saved_file)

        # Parse saved data
        reloaded_data = self.parser.parse_file(saved_file)

        # Verify data preservation
        assert original_data.metadata.name == reloaded_data.metadata.name
        assert original_data.metadata.units == reloaded_data.metadata.units
        assert len(original_data.contours) == len(reloaded_data.contours)

        # Check contour preservation
        for orig_contour, reloaded_contour in zip(original_data.contours, reloaded_data.contours):
            assert orig_contour.elevation == reloaded_contour.elevation
            assert orig_contour.is_closed == reloaded_contour.is_closed
            assert len(orig_contour.points) == len(reloaded_contour.points)

            # Check point coordinates (within tolerance)
            np.testing.assert_allclose(orig_contour.points, reloaded_contour.points, rtol=1e-10)

    def test_workflow_component_integration(self):
        """Test that all workflow components integrate properly."""
        file_path = self.create_test_contour_file("integration_test.json")

        # Step-by-step processing with validation at each step
        contour_data = self.parser.parse_file(file_path)
        assert contour_data.validate() is True

        mesh = self.triangulation_service.triangulate_contours(contour_data)
        is_valid, issues = self.triangulation_service.validate_mesh(mesh)
        assert is_valid is True, f"Mesh validation failed: {issues}"

        # Test that mesh vertices correspond to contour points
        contour_points = np.vstack([contour.points for contour in contour_data.contours])
        mesh_vertices_xy = mesh.vertices[:, :2]

        # All mesh vertices should be within the bounds of contour points
        min_x, min_y = np.min(contour_points[:, 0]), np.min(contour_points[:, 1])
        max_x, max_y = np.max(contour_points[:, 0]), np.max(contour_points[:, 1])

        assert np.all(mesh_vertices_xy[:, 0] >= min_x - 10.0)
        assert np.all(mesh_vertices_xy[:, 0] <= max_x + 10.0)
        assert np.all(mesh_vertices_xy[:, 1] >= min_y - 10.0)
        assert np.all(mesh_vertices_xy[:, 1] <= max_y + 10.0)

    def test_workflow_memory_efficiency(self):
        """Test workflow memory efficiency with moderate datasets."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process multiple files to test memory efficiency
        for i in range(3):
            file_path = self.create_test_contour_file(f"memory_test_{i}.json")

            # Complete workflow
            contour_data = self.parser.parse_file(file_path)
            mesh = self.triangulation_service.triangulate_contours(contour_data)
            fig_2d = self.viz_2d.create_contour_plot(contour_data)
            fig_3d = self.viz_3d.create_terrain_plot(mesh)

            # Clean up references to test garbage collection
            del contour_data, mesh, fig_2d, fig_3d

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100.0

    @patch('matplotlib.pyplot.savefig')
    def test_workflow_visualization_export(self, mock_savefig):
        """Test workflow visualization export functionality."""
        file_path = self.create_test_contour_file("export_test.json")

        # Process workflow
        contour_data = self.parser.parse_file(file_path)
        mesh = self.triangulation_service.triangulate_contours(contour_data)

        # Generate and export visualizations
        fig_2d = self.viz_2d.create_contour_plot(contour_data)
        fig_3d = self.viz_3d.create_terrain_plot(mesh)

        # Test export paths
        export_2d_path = os.path.join(self.temp_dir, "terrain_2d.png")
        export_3d_path = os.path.join(self.temp_dir, "terrain_3d.html")

        # Export 2D plot
        self.viz_2d.save_plot(fig_2d, export_2d_path)
        mock_savefig.assert_called()

        # Export 3D plot
        self.viz_3d.save_plot(fig_3d, export_3d_path)

        # Verify exports were attempted
        assert mock_savefig.called


if __name__ == "__main__":
    pytest.main([__file__])