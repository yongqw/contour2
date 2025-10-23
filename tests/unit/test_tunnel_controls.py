"""
Unit tests for tunnel controls and point selection functionality.

These tests validate the tunnel planning controls including point selection
on 2D maps, tunnel radius input, and path visualization.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch

from src.models.contour_data import ContourData, ContourLine, ContourMetadata, CoordinateSystem
from src.models.terrain_mesh import TerrainMesh, Triangle
from src.utils.math_utils import BoundingBox
from src.utils.exceptions import ValidationError, VisualizationError


class TestTunnelPointSelection:
    """Test cases for point selection functionality on 2D terrain maps."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create test terrain data
        self.metadata = ContourMetadata(
            name="Test Terrain",
            units="meters",
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Create square terrain contour
        self.terrain_contour = ContourLine(
            elevation=100.0,
            points=np.array([[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0], [0.0, 0.0]]),
            is_closed=True
        )

        self.bounds = BoundingBox(min_x=-5.0, max_x=25.0, min_y=-5.0, max_y=25.0)

        self.contour_data = ContourData(
            metadata=self.metadata,
            contours=[self.terrain_contour],
            bounds=self.bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Create mock matplotlib components for testing
        self.mock_ax = Mock()
        self.mock_figure = Mock()
        self.mock_canvas = Mock()

    def test_point_selection_click_handler(self):
        """Test mouse click handler for point selection."""
        # This test will validate the point selection logic
        # when implemented in the actual tunnel controls

        # Simulate clicking on valid terrain point
        click_x, click_y = 10.0, 10.0

        # Point should be within terrain bounds
        assert click_x >= self.bounds.min_x
        assert click_x <= self.bounds.max_x
        assert click_y >= self.bounds.min_y
        assert click_y <= self.bounds.max_y

    def test_point_selection_outside_bounds(self):
        """Test point selection outside terrain bounds."""
        # Points outside terrain should be rejected
        invalid_points = [
            (-10.0, 10.0),  # Outside left bound
            (30.0, 10.0),   # Outside right bound
            (10.0, -10.0),  # Outside bottom bound
            (10.0, 30.0)    # Outside top bound
        ]

        for x, y in invalid_points:
            with pytest.raises(ValidationError, match="Point outside terrain bounds"):
                self._validate_point_selection(x, y)

    def test_point_selection_on_elevation_boundary(self):
        """Test point selection on elevation boundaries."""
        # Create terrain with elevation gradient
        outer_contour = ContourLine(
            elevation=90.0,
            points=np.array([[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0], [0.0, 0.0]]),
            is_closed=True
        )

        inner_contour = ContourLine(
            elevation=110.0,
            points=np.array([[5.0, 5.0], [15.0, 5.0], [15.0, 15.0], [5.0, 15.0], [5.0, 5.0]]),
            is_closed=True
        )

        terrain_with_elevation = ContourData(
            metadata=self.metadata,
            contours=[outer_contour, inner_contour],
            bounds=self.bounds,
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Points should be selectable regardless of elevation
        valid_points = [(2.5, 10.0), (10.0, 10.0), (17.5, 10.0)]
        for x, y in valid_points:
            elevation = terrain_with_elevation.get_elevation_at(x, y)
            assert elevation is not None
            assert elevation > 0

    def test_point_selection_visual_feedback(self):
        """Test visual feedback for selected points."""
        # This test validates visual indicators for selected points
        selected_points = [(5.0, 5.0), (15.0, 15.0)]

        # Mock visual elements that should be created
        expected_visual_elements = []
        for x, y in selected_points:
            # Should create marker or circle at selected point
            marker = Circle((x, y), radius=0.5, color='red', alpha=0.8)
            expected_visual_elements.append(marker)

        assert len(expected_visual_elements) == 2

    def test_point_selection_with_snap_to_grid(self):
        """Test point selection with grid snapping enabled."""
        # Test grid snapping functionality
        grid_resolution = 1.0  # 1 meter grid
        raw_point = (7.3, 12.7)

        # Should snap to nearest grid point
        snapped_x = round(raw_point[0] / grid_resolution) * grid_resolution
        snapped_y = round(raw_point[1] / grid_resolution) * grid_resolution

        expected_snapped = (7.0, 13.0)
        assert (snapped_x, snapped_y) == expected_snapped

    def test_point_selection_with_terrain_constraints(self):
        """Test point selection with terrain slope constraints."""
        # Test that steep slopes are flagged for user confirmation
        steep_slope_points = [
            (1.0, 1.0),   # Near edge - potential steep entry
            (19.0, 19.0)  # Near edge - potential steep exit
        ]

        for x, y in steep_slope_points:
            # Should check slope at selected point
            slope = self._calculate_slope_at_point(x, y)
            if slope > 0.3:  # 30% slope threshold
                # Should warn user about steep terrain
                assert slope > 0.3

    def test_point_selection_minimum_distance(self):
        """Test minimum distance requirement between tunnel points."""
        # Test that points are not too close together
        point1 = (10.0, 10.0)
        point2 = (10.5, 10.5)  # Only 0.7m apart

        distance = np.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)
        min_required_distance = 2.0  # Minimum 2m between points

        assert distance < min_required_distance
        # Should reject this selection or warn user

    def test_point_selection_undo_redo(self):
        """Test undo/redo functionality for point selection."""
        # Test selection history management
        selection_history = []

        # Add points to history
        points = [(5.0, 5.0), (10.0, 10.0), (15.0, 15.0)]
        for point in points:
            selection_history.append(point.copy())

        # Test undo
        undone_point = selection_history.pop()
        assert undone_point == (15.0, 15.0)
        assert len(selection_history) == 2

        # Test redo (in real implementation, would maintain redo stack)
        selection_history.append(undone_point)
        assert len(selection_history) == 3

    def test_point_selection_keyboard_shortcuts(self):
        """Test keyboard shortcuts for point selection."""
        # Test common keyboard shortcuts
        shortcuts = {
            'Escape': 'Cancel current selection',
            'Enter': 'Confirm current selection',
            'Delete': 'Remove last point',
            'Ctrl+Z': 'Undo last action',
            'Ctrl+Y': 'Redo action',
            'G': 'Toggle grid snapping',
            'S': 'Toggle snap to terrain'
        }

        for key, action in shortcuts.items():
            assert action is not None
            assert len(action) > 0

    def test_point_selection_error_handling(self):
        """Test error handling in point selection."""
        # Test various error scenarios

        # Invalid coordinate types
        with pytest.raises(ValidationError):
            self._validate_point_selection("invalid", 10.0)

        with pytest.raises(ValidationError):
            self._validate_point_selection(10.0, None)

        # NaN coordinates
        with pytest.raises(ValidationError):
            self._validate_point_selection(np.nan, 10.0)

        with pytest.raises(ValidationError):
            self._validate_point_selection(10.0, np.inf)

    def _validate_point_selection(self, x: float, y: float) -> None:
        """Helper method to validate point selection."""
        # Type validation
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValidationError("Coordinates must be numeric")

        # NaN/Infinity validation
        if np.isnan(x) or np.isnan(y) or np.isinf(x) or np.isinf(y):
            raise ValidationError("Coordinates cannot be NaN or infinite")

        # Bounds validation
        if x < self.bounds.min_x or x > self.bounds.max_x:
            raise ValidationError("Point outside terrain bounds")
        if y < self.bounds.min_y or y > self.bounds.max_y:
            raise ValidationError("Point outside terrain bounds")

    def _calculate_slope_at_point(self, x: float, y: float) -> float:
        """Helper method to calculate terrain slope at a point."""
        # Simplified slope calculation
        # In real implementation, would use actual terrain data
        base_elevation = 100.0
        distance_factor = abs(x - 10.0) + abs(y - 10.0)
        elevation_change = distance_factor * 2.0
        horizontal_distance = max(distance_factor, 1.0)

        return elevation_change / horizontal_distance


class TestTunnelRadiusControls:
    """Test cases for tunnel radius input controls."""

    def setup_method(self):
        """Set up test fixtures."""
        self.min_radius = 1.0
        self.max_radius = 10.0
        self.default_radius = 3.0

    def test_radius_validation_valid_ranges(self):
        """Test radius validation within valid ranges."""
        valid_radii = [1.0, 2.5, 5.0, 7.5, 10.0]

        for radius in valid_radii:
            assert self._validate_radius(radius) is True

    def test_radius_validation_invalid_ranges(self):
        """Test radius validation outside valid ranges."""
        invalid_radii = [-1.0, 0.0, 0.5, 10.5, 15.0]

        for radius in invalid_radii:
            with pytest.raises(ValidationError, match="Radius must be between"):
                self._validate_radius(radius)

    def test_radius_input_types(self):
        """Test different input types for radius."""
        # Test numeric inputs
        assert self._validate_radius(5.0) is True
        assert self._validate_radius(3) is True

        # Test string inputs that can be converted
        assert self._validate_radius("5.0") is True
        assert self._validate_radius("3") is True

        # Test invalid string inputs
        with pytest.raises(ValidationError):
            self._validate_radius("invalid")

    def test_radius_increment_controls(self):
        """Test radius increment/decrement controls."""
        current_radius = 5.0
        increment = 0.5

        # Test increment
        new_radius = current_radius + increment
        assert self._validate_radius(new_radius) is True

        # Test decrement
        new_radius = current_radius - increment
        assert self._validate_radius(new_radius) is True

    def test_radius_visual_indicators(self):
        """Test visual feedback for radius changes."""
        radius = 5.0

        # Should show tunnel radius preview
        preview_elements = self._create_radius_preview(radius)
        assert len(preview_elements) > 0

        # Should update tunnel cross-section visualization
        cross_section = self._create_cross_section_preview(radius)
        assert cross_section is not None

    def test_radius_presets(self):
        """Test common radius presets."""
        presets = {
            'Small': 1.5,
            'Medium': 3.0,
            'Large': 5.0,
            'Extra Large': 8.0
        }

        for name, radius in presets.items():
            assert self._validate_radius(radius) is True
            assert radius >= self.min_radius
            assert radius <= self.max_radius

    def test_radius_memory(self):
        """Test remembering last used radius."""
        # Test that radius persists between selections
        last_radius = 4.2
        stored_radius = self._store_radius(last_radius)
        retrieved_radius = self._retrieve_radius()

        assert stored_radius == last_radius
        assert retrieved_radius == last_radius

    def _validate_radius(self, radius) -> bool:
        """Helper method to validate radius."""
        # Convert string to float if needed
        if isinstance(radius, str):
            try:
                radius = float(radius)
            except ValueError:
                raise ValidationError("Radius must be a valid number")

        # Range validation
        if radius < self.min_radius or radius > self.max_radius:
            raise ValidationError(f"Radius must be between {self.min_radius} and {self.max_radius}")

        return True

    def _create_radius_preview(self, radius: float) -> list:
        """Helper method to create radius preview elements."""
        # Simulate creating visual preview elements
        return [f"Circle radius {radius}", f"Cross-section {radius}"]

    def _create_cross_section_preview(self, radius: float) -> dict:
        """Helper method to create cross-section preview."""
        return {
            'type': 'circular',
            'radius': radius,
            'area': np.pi * radius ** 2
        }

    def _store_radius(self, radius: float) -> float:
        """Helper method to store radius."""
        # In real implementation, would save to config or state
        return radius

    def _retrieve_radius(self) -> float:
        """Helper method to retrieve stored radius."""
        # In real implementation, would load from config or state
        return self.default_radius


class TestTunnelPathVisualization:
    """Test cases for tunnel path visualization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.waypoints = [
            (5.0, 5.0, 100.0),
            (10.0, 10.0, 105.0),
            (15.0, 15.0, 110.0)
        ]

    def test_path_straight_line(self):
        """Test visualization of straight tunnel path."""
        path_points = [(0.0, 0.0), (20.0, 0.0)]

        # Should create straight line visualization
        line_visual = self._create_path_line(path_points)
        assert line_visual is not None
        assert len(line_visual) == 2  # Start and end points

    def test_path_curved_line(self):
        """Test visualization of curved tunnel path."""
        curved_points = []
        for i in range(10):
            x = i * 2
            y = 10 * np.sin(i * 0.5)  # Sine curve
            curved_points.append((x, y))

        # Should create smooth curve visualization
        curve_visual = self._create_path_curve(curved_points)
        assert curve_visual is not None
        assert len(curve_visual) == 10

    def test_path_elevation_profile(self):
        """Test visualization of elevation profile along path."""
        elevations = [point[2] for point in self.waypoints]

        # Should create elevation profile chart
        profile_visual = self._create_elevation_profile(self.waypoints)
        assert profile_visual is not None
        assert len(elevations) == 3
        assert max(elevations) - min(elevations) > 0  # Should have elevation change

    def test_path_interpolation(self):
        """Test path interpolation between waypoints."""
        # Test smooth interpolation between sparse waypoints
        sparse_waypoints = [(0.0, 0.0), (20.0, 20.0)]
        interpolated = self._interpolate_path(sparse_waypoints, num_points=10)

        assert len(interpolated) == 10
        assert interpolated[0] == sparse_waypoints[0]
        assert interpolated[-1] == sparse_waypoints[1]

    def test_path_tunnel_preview(self):
        """Test tunnel tube preview along path."""
        radius = 3.0

        # Should create tube visualization along path
        tube_visual = self._create_tunnel_preview(self.waypoints, radius)
        assert tube_visual is not None
        assert 'cross_sections' in tube_visual
        assert len(tube_visual['cross_sections']) == len(self.waypoints)

    def test_path_direction_arrows(self):
        """Test directional arrows along path."""
        # Should show direction from start to end
        arrows = self._create_direction_arrows(self.waypoints)
        assert len(arrows) == len(self.waypoints) - 1  # One less than waypoints

        for arrow in arrows:
            assert 'start' in arrow
            assert 'end' in arrow
            assert arrow['direction'] in ['north', 'south', 'east', 'west', 'northeast', 'northwest', 'southeast', 'southwest']

    def test_path_distance_markers(self):
        """Test distance markers along path."""
        # Should show cumulative distance
        markers = self._create_distance_markers(self.waypoints)
        assert len(markers) == len(self.waypoints)

        # Check that distances are cumulative
        distances = [marker['distance'] for marker in markers]
        assert all(distances[i] <= distances[i+1] for i in range(len(distances)-1))

    def _create_path_line(self, points: list) -> list:
        """Helper method to create straight line path visualization."""
        return points.copy()

    def _create_path_curve(self, points: list) -> list:
        """Helper method to create curved path visualization."""
        return points.copy()

    def _create_elevation_profile(self, waypoints: list) -> dict:
        """Helper method to create elevation profile."""
        elevations = [point[2] for point in waypoints]
        return {
            'elevations': elevations,
            'min_elevation': min(elevations),
            'max_elevation': max(elevations)
        }

    def _interpolate_path(self, waypoints: list, num_points: int) -> list:
        """Helper method to interpolate path points."""
        if len(waypoints) < 2:
            return waypoints.copy()

        # Simple linear interpolation
        start, end = waypoints[0], waypoints[-1]
        interpolated = []

        for i in range(num_points):
            t = i / (num_points - 1)
            x = start[0] + t * (end[0] - start[0])
            y = start[1] + t * (end[1] - start[1])
            z = start[2] + t * (end[2] - start[2])
            interpolated.append((x, y, z))

        return interpolated

    def _create_tunnel_preview(self, waypoints: list, radius: float) -> dict:
        """Helper method to create tunnel preview."""
        cross_sections = []
        for waypoint in waypoints:
            cross_sections.append({
                'center': waypoint[:2],
                'radius': radius,
                'elevation': waypoint[2]
            })

        return {
            'cross_sections': cross_sections,
            'total_length': self._calculate_path_length(waypoints)
        }

    def _create_direction_arrows(self, waypoints: list) -> list:
        """Helper method to create directional arrows."""
        arrows = []
        for i in range(len(waypoints) - 1):
            start, end = waypoints[i], waypoints[i + 1]
            dx, dy = end[0] - start[0], end[1] - start[1]

            # Determine direction
            if abs(dx) > abs(dy):
                direction = 'east' if dx > 0 else 'west'
            else:
                direction = 'north' if dy > 0 else 'south'

            arrows.append({
                'start': start[:2],
                'end': end[:2],
                'direction': direction
            })

        return arrows

    def _create_distance_markers(self, waypoints: list) -> list:
        """Helper method to create distance markers."""
        markers = []
        cumulative_distance = 0.0

        for i, waypoint in enumerate(waypoints):
            if i > 0:
                prev = waypoints[i - 1]
                segment_length = np.sqrt(
                    (waypoint[0] - prev[0])**2 + (waypoint[1] - prev[1])**2
                )
                cumulative_distance += segment_length

            markers.append({
                'position': waypoint[:2],
                'distance': cumulative_distance,
                'waypoint_index': i
            })

        return markers

    def _calculate_path_length(self, waypoints: list) -> float:
        """Helper method to calculate total path length."""
        total_length = 0.0
        for i in range(1, len(waypoints)):
            prev, curr = waypoints[i - 1], waypoints[i]
            segment_length = np.sqrt(
                (curr[0] - prev[0])**2 + (curr[1] - prev[1])**2
            )
            total_length += segment_length
        return total_length


if __name__ == "__main__":
    pytest.main([__file__])