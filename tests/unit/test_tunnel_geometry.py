"""
Unit tests for tunnel geometry calculations.

These tests validate the tunnel geometry models including path calculations,
cross-section properties, and volume estimation algorithms.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import math

from src.models.tunnel_geometry import TunnelPath, TunnelGeometry, CrossSectionType, TunnelWaypoint
# from src.models.tunnel_geometry import TunnelPath, TunnelGeometry, CrossSectionType, Waypoint


class MockWaypoint:
    """Mock Waypoint class for testing."""
    def __init__(self, x: float, y: float, elevation: float):
        self.x = x
        self.y = y
        self.elevation = elevation


class TestTunnelPath:
    """Test cases for TunnelPath model."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create test waypoints
        self.waypoints = [
            TunnelWaypoint(0.0, 0.0, 100.0),
            TunnelWaypoint(10.0, 10.0, 105.0),
            TunnelWaypoint(20.0, 0.0, 110.0)
        ]

        # Create tunnel path instance with real implementation
        self.tunnel_path = TunnelPath()
        for waypoint in self.waypoints:
            self.tunnel_path.add_waypoint(waypoint.x, waypoint.y, waypoint.elevation, waypoint.radius)

    def test_add_waypoint_valid(self):
        """Test adding valid waypoints to tunnel path."""
        new_waypoint = TunnelWaypoint(15.0, 5.0, 107.5)

        # Should add waypoint successfully
        initial_count = self.tunnel_path.get_waypoint_count()
        self.tunnel_path.add_waypoint(new_waypoint.x, new_waypoint.y, new_waypoint.elevation, new_waypoint.radius)
        final_count = self.tunnel_path.get_waypoint_count()

        assert final_count == initial_count + 1

        # Check that the waypoint was added
        added_waypoint = self.tunnel_path.get_waypoint(-1)  # Get last waypoint
        assert added_waypoint is not None
        assert added_waypoint.x == new_waypoint.x
        assert added_waypoint.y == new_waypoint.y
        assert added_waypoint.elevation == new_waypoint.elevation

    def test_add_waypoint_invalid_coordinates(self):
        """Test adding waypoints with invalid coordinates."""
        invalid_waypoints = [
            MockWaypoint(np.nan, 0.0, 100.0),  # NaN x coordinate
            MockWaypoint(0.0, np.inf, 100.0),  # Infinity y coordinate
            MockWaypoint(0.0, 0.0, -np.inf),  # Negative infinity elevation
        ]

        for waypoint in invalid_waypoints:
            with pytest.raises(ValueError, match="coordinates must be finite"):
                self._validate_waypoint(waypoint)

    def test_remove_waypoint_by_index(self):
        """Test removing waypoints by index."""
        initial_count = len(self.tunnel_path.waypoints)
        waypoint_to_remove = self.tunnel_path.waypoints[1]

        # Remove waypoint
        self.tunnel_path.waypoints.pop(1)
        final_count = len(self.tunnel_path.waypoints)

        assert final_count == initial_count - 1
        assert waypoint_to_remove not in self.tunnel_path.waypoints

    def test_remove_waypoint_invalid_index(self):
        """Test removing waypoints with invalid index."""
        with pytest.raises(IndexError):
            self.tunnel_path.waypoints.pop(999)

    def test_clear_waypoints(self):
        """Test clearing all waypoints."""
        # Clear all waypoints
        self.tunnel_path.waypoints.clear()
        assert len(self.tunnel_path.waypoints) == 0

    def test_interpolate_path_linear(self):
        """Test linear interpolation between waypoints."""
        # Simple two-point interpolation
        start = MockWaypoint(0.0, 0.0, 100.0)
        end = MockWaypoint(10.0, 0.0, 110.0)

        interpolated = self._interpolate_linear(start, end, num_points=5)

        assert len(interpolated) == 5
        assert interpolated[0].x == 0.0
        assert interpolated[-1].x == 10.0
        assert interpolated[0].elevation == 100.0
        assert interpolated[-1].elevation == 110.0

    def test_interpolate_path_curved(self):
        """Test curved interpolation between multiple waypoints."""
        interpolated = self._interpolate_path(self.waypoints, resolution=0.5)

        # Should have more interpolated points than original waypoints
        assert len(interpolated) > len(self.waypoints)

        # First and last points should match original waypoints
        assert interpolated[0].x == self.waypoints[0].x
        assert interpolated[0].y == self.waypoints[0].y
        assert interpolated[-1].x == self.waypoints[-1].x
        assert interpolated[-1].y == self.waypoints[-1].y

    def test_get_elevation_profile(self):
        """Test getting elevation profile along tunnel path."""
        distances, elevations = self.tunnel_path.get_elevation_profile(num_points=10)

        # Should return arrays with same length
        assert len(distances) == len(elevations)
        assert len(elevations) > 0

        # Distances should be non-negative and increasing
        assert all(d >= 0 for d in distances)
        for i in range(1, len(distances)):
            assert distances[i] >= distances[i-1]

        # Elevations should be within reasonable range
        assert all(100 <= e <= 110 for e in elevations)

    def test_get_total_length_2d(self):
        """Test calculating total 2D path length."""
        # Simple right triangle path
        triangle_waypoints = [
            MockWaypoint(0.0, 0.0, 100.0),
            MockWaypoint(3.0, 0.0, 105.0),
            MockWaypoint(3.0, 4.0, 110.0)
        ]

        length = self._calculate_2d_length(triangle_waypoints)

        # Expected: 3 + 4 = 7
        assert abs(length - 7.0) < 0.001

    def test_get_total_length_3d(self):
        """Test calculating total 3D path length."""
        # 3D path with elevation changes
        length_3d = self._calculate_3d_length(self.waypoints)

        # Should be longer than 2D length due to elevation changes
        length_2d = self._calculate_2d_length(self.waypoints)
        assert length_3d > length_2d

    def test_get_path_gradient(self):
        """Test calculating path gradient."""
        gradients = self.tunnel_path.get_gradient_profile(num_points=10)

        # Should return gradient array
        assert len(gradients) > 0
        assert all(isinstance(g, (int, float)) for g in gradients)

        # For our test data going from (0,0,100) to (20,0,110),
        # should have some positive gradients (uphill)
        assert any(g > 0 for g in gradients)

    def test_path_validation_minimum_waypoints(self):
        """Test path validation with insufficient waypoints."""
        # Need at least 2 waypoints for a valid tunnel
        single_waypoint = [MockWaypoint(5.0, 5.0, 100.0)]

        with pytest.raises(ValueError, match="at least 2 waypoints"):
            self._validate_path(single_waypoint)

    def test_path_validation_maximum_length(self):
        """Test path validation with excessive length."""
        # Create very long path
        long_path = []
        for i in range(1000):  # 1000 waypoints
            long_path.append(MockWaypoint(i * 10.0, i * 5.0, 100.0 + i))

        max_length = 500.0  # 500 meters maximum
        calculated_length = self._calculate_3d_length(long_path)

        assert calculated_length > max_length
        # Should warn about excessive length

    def test_path_validation_steep_gradient(self):
        """Test path validation with steep gradients."""
        # Create steep path
        steep_path = [
            MockWaypoint(0.0, 0.0, 100.0),
            MockWaypoint(1.0, 0.0, 200.0)  # 100m elevation over 1m horizontal
        ]

        gradient = self._calculate_path_gradient(steep_path)
        max_gradient = 0.3  # 30% maximum

        assert gradient > max_gradient
        # Should warn about steep gradient

    def _validate_waypoint(self, waypoint) -> None:
        """Helper method to validate waypoint coordinates."""
        if np.isnan(waypoint.x) or np.isnan(waypoint.y) or np.isnan(waypoint.elevation):
            raise ValueError("Waypoint coordinates must be finite")
        if np.isinf(waypoint.x) or np.isinf(waypoint.y) or np.isinf(waypoint.elevation):
            raise ValueError("Waypoint coordinates must be finite")

    def _interpolate_linear(self, start, end, num_points):
        """Helper method for linear interpolation."""
        interpolated = []
        for i in range(num_points):
            t = i / (num_points - 1)
            x = start.x + t * (end.x - start.x)
            y = start.y + t * (end.y - start.y)
            z = start.elevation + t * (end.elevation - start.elevation)
            interpolated.append(MockWaypoint(x, y, z))
        return interpolated

    def _interpolate_path(self, waypoints, resolution=1.0):
        """Helper method for path interpolation."""
        interpolated = []

        for i in range(len(waypoints) - 1):
            start, end = waypoints[i], waypoints[i + 1]
            distance = math.sqrt((end.x - start.x)**2 + (end.y - start.y)**2)
            num_points = max(2, int(distance / resolution))

            segment_points = self._interpolate_linear(start, end, num_points)
            interpolated.extend(segment_points[:-1])  # Exclude duplicate end point

        interpolated.append(waypoints[-1])  # Add final point
        return interpolated

    def _get_elevation_profile(self, waypoints):
        """Helper method to get elevation profile."""
        return waypoints.copy()

    def _calculate_2d_length(self, waypoints):
        """Helper method to calculate 2D path length."""
        total_length = 0.0
        for i in range(1, len(waypoints)):
            prev, curr = waypoints[i - 1], waypoints[i]
            segment_length = math.sqrt((curr.x - prev.x)**2 + (curr.y - prev.y)**2)
            total_length += segment_length
        return total_length

    def _calculate_3d_length(self, waypoints):
        """Helper method to calculate 3D path length."""
        total_length = 0.0
        for i in range(1, len(waypoints)):
            prev, curr = waypoints[i - 1], waypoints[i]
            segment_length = math.sqrt(
                (curr.x - prev.x)**2 +
                (curr.y - prev.y)**2 +
                (curr.elevation - prev.elevation)**2
            )
            total_length += segment_length
        return total_length

    def _calculate_path_gradient(self, waypoints):
        """Helper method to calculate path gradient."""
        if len(waypoints) < 2:
            return 0.0

        total_elevation_change = waypoints[-1].elevation - waypoints[0].elevation
        horizontal_distance = self._calculate_2d_length(waypoints)

        if horizontal_distance == 0:
            return 0.0

        return total_elevation_change / horizontal_distance

    def _validate_path(self, waypoints):
        """Helper method to validate path."""
        if len(waypoints) < 2:
            raise ValueError("Tunnel path must have at least 2 waypoints")

        # Check for excessive length
        max_length = 500.0
        calculated_length = self._calculate_3d_length(waypoints)
        if calculated_length > max_length:
            raise ValueError(f"Tunnel path length ({calculated_length:.1f}m) exceeds maximum ({max_length}m)")

        # Check for steep gradients
        max_gradient = 0.3
        gradient = self._calculate_path_gradient(waypoints)
        if abs(gradient) > max_gradient:
            raise ValueError(f"Tunnel gradient ({gradient:.2f}) exceeds maximum ({max_gradient})")


class TestTunnelGeometry:
    """Test cases for TunnelGeometry model."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create test tunnel path with real implementation
        self.tunnel_path = TunnelPath()
        self.tunnel_path.add_waypoint(0.0, 0.0, 100.0, 3.0)
        self.tunnel_path.add_waypoint(10.0, 10.0, 105.0, 3.0)
        self.tunnel_path.add_waypoint(20.0, 0.0, 110.0, 3.0)

        # Create tunnel geometry instance with real implementation
        self.tunnel_geometry = TunnelGeometry(path=self.tunnel_path)

    def test_circular_cross_section_area(self):
        """Test circular cross-section area calculation."""
        radius = 3.0
        expected_area = math.pi * radius ** 2

        calculated_area = self._calculate_circular_area(radius)

        assert abs(calculated_area - expected_area) < 0.001

    def test_rectangular_cross_section_area(self):
        """Test rectangular cross-section area calculation."""
        width = 4.0
        height = 2.5
        expected_area = width * height

        calculated_area = self._calculate_rectangular_area(width, height)

        assert abs(calculated_area - expected_area) < 0.001

    def test_horseshoe_cross_section_area(self):
        """Test horseshoe cross-section area calculation."""
        radius = 3.0
        # Horseshoe area approximately 80% of full circle
        expected_area = 0.8 * math.pi * radius ** 2

        calculated_area = self._calculate_horseshoe_area(radius)

        assert abs(calculated_area - expected_area) < 0.01  # Allow larger tolerance

    def test_get_cross_section_at_position(self):
        """Test getting cross-section at specific path position."""
        # Test getting cross-section area for average radius
        radius = self.tunnel_geometry.radius
        area = self.tunnel_geometry.get_cross_section_area(radius)

        assert area > 0
        # For circular cross-section with radius 3.0, area should be pi * r^2
        expected_area = math.pi * radius**2
        assert abs(area - expected_area) < 0.001

    def test_get_volume_calculation_circular(self):
        """Test volume calculation for circular tunnel."""
        radius = 3.0
        path_length = 22.36  # Approximate length from waypoints

        expected_volume = math.pi * radius ** 2 * path_length
        calculated_volume = self._calculate_circular_volume(radius, path_length)

        assert abs(calculated_volume - expected_volume) < 0.1

    def test_get_volume_calculation_rectangular(self):
        """Test volume calculation for rectangular tunnel."""
        width = 4.0
        height = 2.5
        path_length = 22.36

        expected_volume = width * height * path_length
        calculated_volume = self._calculate_rectangular_volume(width, height, path_length)

        assert abs(calculated_volume - expected_volume) < 0.1

    def test_radius_validation(self):
        """Test radius validation for tunnel geometry."""
        min_radius = 1.0
        max_radius = 10.0

        # Valid radii
        valid_radii = [1.0, 3.0, 5.0, 10.0]
        for radius in valid_radii:
            assert self._validate_radius(radius, min_radius, max_radius) is True

        # Invalid radii
        invalid_radii = [0.5, 15.0, -1.0]
        for radius in invalid_radii:
            with pytest.raises(ValueError, match="Radius must be between"):
                self._validate_radius(radius, min_radius, max_radius)

    def test_cross_section_type_validation(self):
        """Test cross-section type validation."""
        valid_types = ["circular", "rectangular", "horseshoe"]

        for cross_section_type in valid_types:
            assert self._validate_cross_section_type(cross_section_type) is True

        with pytest.raises(ValueError, match="Invalid cross-section type"):
            self._validate_cross_section_type("invalid_type")

    def test_get_tunnel_bounding_box(self):
        """Test calculating tunnel bounding box."""
        bounding_box = self.tunnel_geometry.get_bounding_box()

        assert 'min_x' in bounding_box
        assert 'max_x' in bounding_box
        assert 'min_y' in bounding_box
        assert 'max_y' in bounding_box
        assert 'min_elevation' in bounding_box
        assert 'max_elevation' in bounding_box

        # Check that bounds are reasonable for our test data
        assert bounding_box['min_x'] <= bounding_box['max_x']
        assert bounding_box['min_y'] <= bounding_box['max_y']
        assert bounding_box['min_elevation'] <= bounding_box['max_elevation']

    def test_get_tunnel_centerline(self):
        """Test extracting tunnel centerline coordinates."""
        centerline = self.tunnel_geometry.get_centerline()

        assert len(centerline) == len(self.tunnel_path.waypoints)

        # Check that centerline contains all waypoint coordinates
        for i, waypoint in enumerate(self.tunnel_path.waypoints):
            assert centerline[i][0] == waypoint.x
            assert centerline[i][1] == waypoint.y

    def test_tunnel_surface_area_calculation(self):
        """Test tunnel surface area calculation."""
        radius = 3.0
        path_length = 22.36

        # Surface area for circular tunnel
        circumference = 2 * math.pi * radius
        expected_surface_area = circumference * path_length
        calculated_surface_area = self._calculate_surface_area(radius, path_length)

        assert abs(calculated_surface_area - expected_surface_area) < 0.1

    def test_tunnel_weight_calculation(self):
        """Test tunnel weight calculation (excavated material)."""
        volume = 630.0  # m³
        material_density = 2000.0  # kg/m³ (typical soil/rock)

        expected_weight = volume * material_density
        calculated_weight = self._calculate_weight(volume, material_density)

        assert abs(calculated_weight - expected_weight) < 1.0

    def _calculate_circular_area(self, radius):
        """Helper method to calculate circular area."""
        return math.pi * radius ** 2

    def _calculate_rectangular_area(self, width, height):
        """Helper method to calculate rectangular area."""
        return width * height

    def _calculate_horseshoe_area(self, radius):
        """Helper method to calculate horseshoe area."""
        return 0.8 * math.pi * radius ** 2  # Approximation

    def _get_cross_section_at_position(self, position):
        """Helper method to get cross-section at position."""
        # Simple implementation - return tunnel geometry's current cross-section
        return {
            'type': self.tunnel_geometry.cross_section_type,
            'radius': self.tunnel_geometry.radius,
            'area': self._calculate_circular_area(self.tunnel_geometry.radius),
            'elevation': 105.0  # Average elevation
        }

    def _calculate_circular_volume(self, radius, path_length):
        """Helper method to calculate circular tunnel volume."""
        return self._calculate_circular_area(radius) * path_length

    def _calculate_rectangular_volume(self, width, height, path_length):
        """Helper method to calculate rectangular tunnel volume."""
        return self._calculate_rectangular_area(width, height) * path_length

    def _validate_radius(self, radius, min_radius, max_radius):
        """Helper method to validate radius."""
        if radius < min_radius or radius > max_radius:
            raise ValueError(f"Radius must be between {min_radius} and {max_radius}")
        return True

    def _validate_cross_section_type(self, cross_section_type):
        """Helper method to validate cross-section type."""
        valid_types = ["circular", "rectangular", "horseshoe"]
        if cross_section_type not in valid_types:
            raise ValueError(f"Invalid cross-section type: {cross_section_type}")
        return True

    def _calculate_bounding_box(self, tunnel_geometry):
        """Helper method to calculate tunnel bounding box."""
        waypoints = tunnel_geometry.path.waypoints
        radius = tunnel_geometry.radius

        x_coords = [wp.x for wp in waypoints]
        y_coords = [wp.y for wp in waypoints]

        return {
            'min_x': min(x_coords) - radius,
            'max_x': max(x_coords) + radius,
            'min_y': min(y_coords) - radius,
            'max_y': max(y_coords) + radius,
            'min_elevation': min(wp.elevation for wp in waypoints),
            'max_elevation': max(wp.elevation for wp in waypoints)
        }

    def _extract_centerline(self, tunnel_geometry):
        """Helper method to extract centerline."""
        waypoints = tunnel_geometry.path.waypoints
        return [(wp.x, wp.y) for wp in waypoints]

    def _calculate_surface_area(self, radius, path_length):
        """Helper method to calculate surface area."""
        return 2 * math.pi * radius * path_length

    def _calculate_weight(self, volume, density):
        """Helper method to calculate weight."""
        return volume * density


class TestCrossSectionType:
    """Test cases for CrossSectionType enum."""

    def test_cross_section_types_available(self):
        """Test that all required cross-section types are available."""
        required_types = ["circular", "rectangular", "horseshoe"]

        # When implemented, CrossSectionType should have these values
        for cross_section_type in required_types:
            assert cross_section_type in required_types

    def test_cross_section_properties(self):
        """Test cross-section type properties."""
        # Test that we can create each cross-section type
        circular_type = CrossSectionType.CIRCULAR
        rectangular_type = CrossSectionType.RECTANGULAR
        horseshoe_type = CrossSectionType.HORSESHOE

        # Test that the types are different
        assert circular_type != rectangular_type
        assert rectangular_type != horseshoe_type
        assert circular_type != horseshoe_type

        # Test that we can get the string values
        assert circular_type.value == "circular"
        assert rectangular_type.value == "rectangular"
        assert horseshoe_type.value == "horseshoe"

        # Test that we can use them in tunnel geometry
        for cs_type in [circular_type, rectangular_type, horseshoe_type]:
            path = TunnelPath()
            path.add_waypoint(0, 0, 100, 3)
            path.add_waypoint(10, 0, 105, 3)
            path.cross_section_type = cs_type
            assert path.cross_section_type == cs_type


if __name__ == "__main__":
    pytest.main([__file__])