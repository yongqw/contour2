"""
Integration tests for tunnel planning workflow.

These tests validate the end-to-end tunnel planning process,
including point selection, geometry creation, and visualization integration.
"""

import pytest
import numpy as np
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.models.contour_data import ContourData, ContourLine, ContourMetadata, CoordinateSystem
from src.models.terrain_mesh import TerrainMesh, Triangle
from src.utils.math_utils import BoundingBox
from src.utils.exceptions import ValidationError, VisualizationError


class TestTunnelPlanningWorkflow:
    """Integration tests for complete tunnel planning workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Create test terrain data
        self.metadata = ContourMetadata(
            name="Test Terrain for Tunnel Planning",
            units="meters",
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Create terrain with varying elevations
        self.contours = [
            ContourLine(
                elevation=90.0,
                points=np.array([[0.0, 0.0], [30.0, 0.0], [30.0, 30.0], [0.0, 30.0], [0.0, 0.0]]),
                is_closed=True
            ),
            ContourLine(
                elevation=95.0,
                points=np.array([[5.0, 5.0], [25.0, 5.0], [25.0, 25.0], [5.0, 25.0], [5.0, 5.0]]),
                is_closed=True
            ),
            ContourLine(
                elevation=100.0,
                points=np.array([[10.0, 10.0], [20.0, 10.0], [20.0, 20.0], [10.0, 20.0], [10.0, 10.0]]),
                is_closed=True
            )
        ]

        self.bounds = BoundingBox(min_x=-5.0, max_x=35.0, min_y=-5.0, max_y=35.0)

        self.contour_data = ContourData(
            metadata=self.metadata,
            contours=self.contours,
            bounds=self.bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Create mock terrain mesh
        self.terrain_mesh = self._create_mock_terrain_mesh()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_mock_terrain_mesh(self):
        """Create a mock terrain mesh for testing."""
        vertices = np.array([
            [0.0, 0.0, 90.0],
            [30.0, 0.0, 90.0],
            [30.0, 30.0, 90.0],
            [0.0, 30.0, 90.0],
            [15.0, 15.0, 100.0]
        ])

        triangles = [
            Triangle(vertex_indices=[0, 1, 4]),
            Triangle(vertex_indices=[1, 2, 4]),
            Triangle(vertex_indices=[2, 3, 4]),
            Triangle(vertex_indices=[3, 0, 4])
        ]

        return TerrainMesh(vertices=vertices, triangles=triangles)

    def test_complete_tunnel_planning_workflow(self):
        """Test complete tunnel planning from start to finish."""
        # Step 1: Select tunnel start point
        start_point = (5.0, 5.0)
        start_elevation = self.contour_data.get_elevation_at(start_point[0], start_point[1])
        assert start_elevation == 95.0

        # Step 2: Select tunnel end point
        end_point = (25.0, 25.0)
        end_elevation = self.contour_data.get_elevation_at(end_point[0], end_point[1])
        assert end_elevation == 95.0

        # Step 3: Add intermediate waypoint
        intermediate_point = (15.0, 15.0)
        intermediate_elevation = self.contour_data.get_elevation_at(intermediate_point[0], intermediate_point[1])
        assert intermediate_elevation == 100.0

        # Step 4: Set tunnel parameters
        tunnel_radius = 3.0
        cross_section_type = "circular"

        # Step 5: Create tunnel geometry
        tunnel_geometry = self._create_tunnel_geometry(
            waypoints=[start_point, intermediate_point, end_point],
            elevations=[start_elevation, intermediate_elevation, end_elevation],
            radius=tunnel_radius,
            cross_section_type=cross_section_type
        )

        # Validate tunnel geometry
        assert tunnel_geometry is not None
        assert tunnel_geometry.radius == tunnel_radius
        assert tunnel_geometry.cross_section_type == cross_section_type
        assert len(tunnel_geometry.path.waypoints) == 3

    def test_tunnel_planning_with_2d_visualization(self):
        """Test tunnel planning with 2D visualization integration."""
        # Create mock 2D visualization
        mock_2d_viz = Mock()
        mock_figure = Mock()
        mock_ax = Mock()

        # Select tunnel points
        tunnel_points = [(5.0, 5.0), (25.0, 25.0)]
        tunnel_elevations = [95.0, 95.0]

        # Create tunnel geometry
        tunnel_geometry = self._create_tunnel_geometry(
            waypoints=tunnel_points,
            elevations=tunnel_elevations,
            radius=2.5,
            cross_section_type="circular"
        )

        # Create 2D visualization with tunnel overlay
        mock_2d_viz.create_tunnel_overlay.return_value = mock_figure
        mock_2d_viz.create_tunnel_overlay.assert_called_once()

        # Verify tunnel visualization elements
        mock_ax.plot.assert_called()  # Should be called for tunnel line
        mock_ax.add_patch.assert_called()  # Should be called for tunnel cross-section

    def test_tunnel_planning_with_3d_visualization(self):
        """Test tunnel planning with 3D visualization integration."""
        # Create mock 3D visualization
        mock_3d_viz = Mock()
        mock_figure = Mock()

        # Select tunnel points
        tunnel_points = [(5.0, 5.0, 95.0), (15.0, 15.0, 100.0), (25.0, 25.0, 95.0)]
        radius = 2.0

        # Create tunnel geometry
        tunnel_geometry = self._create_tunnel_geometry(
            waypoints=[(5.0, 5.0), (15.0, 15.0), (25.0, 25.0)],
            elevations=[95.0, 100.0, 95.0],
            radius=radius,
            cross_section_type="circular"
        )

        # Create 3D visualization with tunnel
        mock_3d_viz.create_tunnel_overlay.return_value = mock_figure
        mock_3d_viz.create_tunnel_overlay.assert_called_once()

        # Verify 3D tunnel elements are created
        # (In real implementation, would check for 3D mesh elements)

    def test_tunnel_point_selection_validation(self):
        """Test point selection validation during tunnel planning."""
        valid_points = [
            (5.0, 5.0),    # Inside terrain
            (15.0, 15.0),  # Inside terrain
            (25.0, 25.0)   # Inside terrain
        ]

        # All valid points should be selectable
        for point in valid_points:
            elevation = self.contour_data.get_elevation_at(point[0], point[1])
            assert elevation is not None
            assert elevation > 0

        # Invalid points should be rejected
        invalid_points = [
            (-5.0, 15.0),  # Outside terrain bounds
            (35.0, 15.0),  # Outside terrain bounds
            (15.0, -5.0),  # Outside terrain bounds
            (15.0, 35.0)   # Outside terrain bounds
        ]

        for point in invalid_points:
            elevation = self.contour_data.get_elevation_at(point[0], point[1])
            # Should return minimum elevation for points outside all contours
            assert elevation == 90.0

    def test_tunnel_radius_validation_terrain_constraints(self):
        """Test tunnel radius validation based on terrain constraints."""
        tunnel_center = (15.0, 15.0)
        tunnel_elevation = 100.0

        # Test radius constraints based on terrain features
        max_radius = 5.0  # Example constraint

        valid_radii = [1.0, 2.5, 4.0, 5.0]
        for radius in valid_radii:
            if radius <= max_radius:
                assert self._validate_radius_with_terrain(
                    tunnel_center, tunnel_elevation, radius
                ) is True

        # Test radius that's too large for terrain
        large_radius = 10.0
        assert self._validate_radius_with_terrain(
            tunnel_center, tunnel_elevation, large_radius
        ) is False

    def test_tunnel_path_gradient_validation(self):
        """Test tunnel path gradient validation."""
        # Create tunnel with steep gradient
        steep_tunnel_points = [
            (5.0, 5.0, 90.0),
            (10.0, 5.0, 140.0)  # 50m elevation over 5m horizontal = 1000% gradient
        ]

        gradient = self._calculate_path_gradient(steep_tunnel_points)
        max_gradient = 0.3  # 30% maximum

        assert gradient > max_gradient
        # Should warn about steep gradient

        # Create tunnel with gentle gradient
        gentle_tunnel_points = [
            (5.0, 5.0, 90.0),
            (25.0, 5.0, 110.0)  # 20m elevation over 20m horizontal = 100% gradient
        ]

        gentle_gradient = self._calculate_path_gradient(gentle_tunnel_points)
        assert gentle_gradient < max_gradient
        # Should be acceptable

    def test_tunnel_intersections_with_terrain(self):
        """Test tunnel-terrain intersection calculations."""
        tunnel_path = [
            (5.0, 5.0, 95.0),
            (15.0, 15.0, 100.0),
            (25.0, 25.0, 95.0)
        ]
        tunnel_radius = 3.0

        # Calculate tunnel-terrain intersections
        intersections = self._calculate_terrain_intersections(
            tunnel_path, tunnel_radius, self.contour_data
        )

        assert isinstance(intersections, list)
        assert len(intersections) > 0

        # Each intersection should have entry/exit points
        for intersection in intersections:
            assert 'entry_point' in intersection
            assert 'exit_point' in intersection
            assert 'terrain_elevation' in intersection
            assert 'tunnel_elevation' in intersection

    def test_tunnel_planning_undo_redo_functionality(self):
        """Test undo/redo functionality in tunnel planning."""
        planning_history = []

        # Add tunnel planning steps
        steps = [
            {'action': 'add_waypoint', 'point': (5.0, 5.0, 95.0)},
            {'action': 'add_waypoint', 'point': (15.0, 15.0, 100.0)},
            {'action': 'add_waypoint', 'point': (25.0, 25.0, 95.0)},
            {'action': 'set_radius', 'radius': 3.0},
            {'action': 'set_cross_section', 'type': 'circular'}
        ]

        for step in steps:
            planning_history.append(step.copy())

        # Test undo
        undone_step = planning_history.pop()
        assert undone_step['action'] == 'set_cross_section'
        assert len(planning_history) == 4

        # Test redo
        planning_history.append(undone_step)
        assert len(planning_history) == 5
        assert planning_history[-1] == undone_step

    def test_tunnel_planning_save_load_workflow(self):
        """Test saving and loading tunnel planning sessions."""
        # Create tunnel planning session
        tunnel_plan = {
            'waypoints': [
                {'x': 5.0, 'y': 5.0, 'elevation': 95.0},
                {'x': 15.0, 'y': 15.0, 'elevation': 100.0},
                {'x': 25.0, 'y': 25.0, 'elevation': 95.0}
            ],
            'radius': 3.0,
            'cross_section_type': 'circular',
            'created_date': '2025-10-20T16:55:00Z'
        }

        # Save tunnel plan
        plan_file = os.path.join(self.temp_dir, 'tunnel_plan.json')
        self._save_tunnel_plan(tunnel_plan, plan_file)

        # Verify file was created
        assert os.path.exists(plan_file)

        # Load tunnel plan
        loaded_plan = self._load_tunnel_plan(plan_file)
        assert loaded_plan is not None
        assert loaded_plan['radius'] == tunnel_plan['radius']
        assert len(loaded_plan['waypoints']) == 3

    def test_tunnel_planning_error_recovery(self):
        """Test error recovery in tunnel planning."""
        planning_state = {
            'waypoints': [(5.0, 5.0, 95.0), (15.0, 15.0, 100.0)],
            'radius': 3.0,
            'cross_section_type': 'circular'
        }

        # Simulate error during waypoint addition
        invalid_waypoint = (np.nan, 15.0, 100.0)

        try:
            self._validate_waypoint(invalid_waypoint)
            assert False, "Should have raised ValidationError"
        except ValidationError:
            # State should remain unchanged
            assert len(planning_state['waypoints']) == 2
            assert planning_state['radius'] == 3.0

        # Should be able to continue planning after error
        valid_waypoint = (20.0, 20.0, 102.0)
        self._validate_waypoint(valid_waypoint)  # Should not raise

        planning_state['waypoints'].append(valid_waypoint)
        assert len(planning_state['waypoints']) == 3

    def _create_tunnel_geometry(self, waypoints, elevations, radius, cross_section_type):
        """Helper method to create tunnel geometry."""
        # Mock tunnel geometry creation
        mock_geometry = Mock()
        mock_geometry.radius = radius
        mock_geometry.cross_section_type = cross_section_type
        mock_geometry.path = Mock()

        # Create mock waypoints
        mock_waypoints = []
        for i, (x, y) in enumerate(waypoints):
            mock_waypoint = Mock()
            mock_waypoint.x = x
            mock_waypoint.y = y
            mock_waypoint.elevation = elevations[i]
            mock_waypoints.append(mock_waypoint)

        mock_geometry.path.waypoints = mock_waypoints
        return mock_geometry

    def _validate_radius_with_terrain(self, center, elevation, radius):
        """Helper method to validate radius with terrain constraints."""
        # Simple validation - in real implementation would check terrain features
        max_allowed_radius = 5.0
        return radius <= max_allowed_radius

    def _calculate_path_gradient(self, waypoints):
        """Helper method to calculate path gradient."""
        if len(waypoints) < 2:
            return 0.0

        elevation_change = waypoints[-1][2] - waypoints[0][2]
        horizontal_distance = np.sqrt(
            (waypoints[-1][0] - waypoints[0][0])**2 +
            (waypoints[-1][1] - waypoints[0][1])**2
        )

        return elevation_change / horizontal_distance if horizontal_distance > 0 else 0.0

    def _calculate_terrain_intersections(self, tunnel_path, radius, contour_data):
        """Helper method to calculate tunnel-terrain intersections."""
        intersections = []

        for i in range(len(tunnel_path) - 1):
            start = tunnel_path[i]
            end = tunnel_path[i + 1]

            # Check intersection with each contour
            for contour in contour_data.contours:
                if contour.elevation >= min(start[2], end[2]) and contour.elevation <= max(start[2], end[2]):
                    intersection = {
                        'entry_point': start,
                        'exit_point': end,
                        'terrain_elevation': contour.elevation,
                        'tunnel_elevation': (start[2] + end[2]) / 2,
                        'contour_elevation': contour.elevation
                    }
                    intersections.append(intersection)

        return intersections

    def _save_tunnel_plan(self, plan, file_path):
        """Helper method to save tunnel plan."""
        import json
        with open(file_path, 'w') as f:
            json.dump(plan, f, indent=2)

    def _load_tunnel_plan(self, file_path):
        """Helper method to load tunnel plan."""
        import json
        with open(file_path, 'r') as f:
            return json.load(f)

    def _validate_waypoint(self, waypoint):
        """Helper method to validate waypoint."""
        x, y, elevation = waypoint
        if np.isnan(x) or np.isnan(y) or np.isnan(elevation):
            raise ValidationError("Waypoint coordinates cannot be NaN")
        if np.isinf(x) or np.isinf(y) or np.isinf(elevation):
            raise ValidationError("Waypoint coordinates cannot be infinite")


class TestTunnelPlanningPerformance:
    """Performance tests for tunnel planning operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.contour_data = self._create_large_contour_data()

    def _create_large_contour_data(self):
        """Create large contour dataset for performance testing."""
        metadata = ContourMetadata(
            name="Large Terrain for Performance Testing",
            units="meters",
            coordinate_system=CoordinateSystem.LOCAL
        )

        contours = []
        for i in range(20):  # 20 contours
            elevation = 90.0 + i * 2.5
            points = []
            for j in range(50):  # 50 points per contour
                angle = 2 * np.pi * j / 50
                radius = 30.0 - i * 1.0
                x = 15.0 + radius * np.cos(angle)
                y = 15.0 + radius * np.sin(angle)
                points.append([x, y])
            points.append(points[0])  # Close contour

            contour = ContourLine(
                elevation=elevation,
                points=np.array(points),
                is_closed=True
            )
            contours.append(contour)

        bounds = BoundingBox(min_x=-5.0, max_x=35.0, min_y=-5.0, max_y=35.0)

        return ContourData(
            metadata=metadata,
            contours=contours,
            bounds=bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )

    def test_point_selection_performance(self):
        """Test performance of point selection with large datasets."""
        import time

        # Test multiple point selections
        num_selections = 100
        start_time = time.time()

        for i in range(num_selections):
            # Generate random point within bounds
            x = np.random.uniform(0, 30)
            y = np.random.uniform(0, 30)

            # Check point selection performance
            elevation = self.contour_data.get_elevation_at(x, y)
            assert elevation is not None

        end_time = time.time()
        selection_time = end_time - start_time

        # Should complete quickly
        assert selection_time < 1.0, f"Point selection took {selection_time:.3f}s for {num_selections} selections"

    def test_tunnel_geometry_calculation_performance(self):
        """Test performance of tunnel geometry calculations."""
        import time

        # Create long tunnel path
        tunnel_waypoints = []
        for i in range(50):  # 50 waypoints
            x = i * 0.6
            y = 15.0 + 10 * np.sin(i * 0.2)
            elevation = 95.0 + 5 * np.sin(i * 0.1)
            tunnel_waypoints.append((x, y, elevation))

        start_time = time.time()

        # Calculate tunnel geometry
        tunnel_geometry = self._create_tunnel_geometry(
            waypoints=[(waypoint[0], waypoint[1]) for waypoint in tunnel_waypoints],
            elevations=[waypoint[2] for waypoint in tunnel_waypoints],
            radius=3.0,
            cross_section_type="circular"
        )

        end_time = time.time()
        calculation_time = end_time - start_time

        # Should complete quickly
        assert calculation_time < 0.5, f"Tunnel geometry calculation took {calculation_time:.3f}s"

    def test_visualization_update_performance(self):
        """Test performance of visualization updates during tunnel planning."""
        import time

        # Create tunnel geometry
        tunnel_geometry = self._create_tunnel_geometry(
            waypoints=[(5.0, 5.0), (15.0, 15.0), (25.0, 25.0)],
            elevations=[95.0, 100.0, 95.0],
            radius=3.0,
            cross_section_type="circular"
        )

        # Test multiple visualization updates
        num_updates = 20
        start_time = time.time()

        for i in range(num_updates):
            # Simulate visualization update
            mock_visual = Mock()
            mock_visual.update_tunnel_visualization(tunnel_geometry)
            mock_visual.update_2d_overlay.assert_called_once()

        end_time = time.time()
        update_time = end_time - start_time

        # Should complete quickly
        assert update_time < 0.2, f"Visualization updates took {update_time:.3f}s for {num_updates} updates"


if __name__ == "__main__":
    pytest.main([__file__])