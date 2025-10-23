"""
Unit tests for volume calculator with numerical validation.

These tests validate the volume calculation accuracy for tunnel excavation,
including tetrahedral decomposition, terrain intersection, and precision validation.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from src.services.volume_calculator import VolumeCalculator
from src.models.volume_calculator import ExcavationZone, MaterialType
from src.models.tunnel_geometry import TunnelGeometry, TunnelPath, VolumeCalculation
from src.models.terrain_mesh import TerrainMesh
from src.models.contour_data import ContourMetadata, ContourLine, CoordinateSystem
from src.utils.exceptions import VolumeCalculationError, ValidationError


class TestVolumeCalculator:
    """Test cases for VolumeCalculator class with focus on numerical accuracy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.volume_calculator = VolumeCalculator()

        # Create simple test terrain
        self.metadata = ContourMetadata(
            name="Test Terrain",
            units="meters",
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Create rectangular terrain
        self.terrain_contour = ContourLine(
            elevation=100.0,
            points=np.array([[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0], [0.0, 0.0]]),
            is_closed=True
        )

        self.terrain_data = ContourData(
            metadata=self.metadata,
            contours=[self.terrain_contour],
            bounds=BoundingBox(min_x=-5, max_x=25, min_y=-5, max_y=25),
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Create simple terrain mesh
        vertices = np.array([
            [0.0, 0.0, 100.0],   # Corners at base elevation
            [20.0, 0.0, 100.0],
            [20.0, 20.0, 100.0],
            [0.0, 20.0, 100.0],
            [10.0, 10.0, 110.0],  # Center peak
        ])

        triangles = [
            Triangle(vertex_indices=[0, 1, 4]),
            Triangle(vertex_indices=[1, 2, 4]),
            Triangle(vertex_indices=[2, 3, 4]),
            Triangle(vertex_indices=[3, 0, 4]),
        ]

        self.terrain_mesh = TerrainMesh(vertices=vertices, triangles=triangles)

    def test_calculate_simple_tunnel_volume_analytical_verification(self):
        """Test volume calculation with analytical verification for simple geometry."""
        # Create a straight tunnel through flat terrain
        tunnel_path = TunnelPath()
        tunnel_path.add_waypoint(5.0, 10.0, 100.0)  # Start point
        tunnel_path.add_waypoint(15.0, 10.0, 100.0)  # End point (same elevation)

        tunnel_geometry = TunnelGeometry(
            path=tunnel_path,
            radius=2.0,  # 2 meter radius
            cross_section_type="circular"
        )

        # Calculate volume
        volume_calc = self.volume_calculator.calculate_tunnel_volume(
            tunnel_geometry, self.terrain_mesh
        )

        # Analytical verification: cylinder volume
        # V = π * r² * h where r=2, h=10 (distance from x=5 to x=15)
        expected_volume = np.pi * 2.0**2 * 10.0  # ≈ 125.66 cubic meters

        # Verify calculation is within 1% accuracy requirement
        relative_error = abs(volume_calc.total_volume - expected_volume) / expected_volume
        assert relative_error < 0.01, f"Volume error: {relative_error:.4f} (should be < 0.01)"

        # Verify calculation details
        assert volume_calc.total_volume > 0
        assert len(volume_calc.excavation_zones) > 0
        assert volume_calc.accuracy_estimate is not None

    def test_calculate_tunnel_volume_terrain_intersection(self):
        """Test volume calculation with terrain intersection."""
        # Create tunnel that goes through varying terrain elevations
        tunnel_path = TunnelPath()
        tunnel_path.add_waypoint(5.0, 10.0, 95.0)   # Below terrain
        tunnel_path.add_waypoint(10.0, 10.0, 105.0)  # Above terrain
        tunnel_path.add_waypoint(15.0, 10.0, 95.0)   # Below terrain again

        tunnel_geometry = TunnelGeometry(
            path=tunnel_path,
            radius=1.5,
            cross_section_type="circular"
        )

        volume_calc = self.volume_calculator.calculate_tunnel_volume(
            tunnel_geometry, self.terrain_mesh
        )

        # Volume should be less than full cylinder due to terrain intersection
        full_cylinder_volume = np.pi * 1.5**2 * 10.0
        assert volume_calc.total_volume < full_cylinder_volume
        assert volume_calc.total_volume > 0

        # Should have intersection information
        assert volume_calc.terrain_intersection_ratio is not None
        assert 0 <= volume_calc.terrain_intersection_ratio <= 1

    def test_tetrahedral_decomposition_accuracy(self):
        """Test tetrahedral decomposition algorithm accuracy."""
        # Create a simple tetrahedron with known volume
        vertices = np.array([
            [0.0, 0.0, 0.0],  # Origin
            [1.0, 0.0, 0.0],  # Unit along x
            [0.0, 1.0, 0.0],  # Unit along y
            [0.0, 0.0, 1.0],  # Unit along z
        ])

        # Volume of unit tetrahedron = 1/6
        expected_volume = 1.0 / 6.0

        # Calculate using tetrahedral decomposition
        calculated_volume = self.volume_calculator._calculate_tetrahedron_volume(vertices)

        # Verify accuracy
        relative_error = abs(calculated_volume - expected_volume) / expected_volume
        assert relative_error < 1e-10, f"Tetrahedron volume error: {relative_error}"

    def test_complex_tunnel_geometry_volume(self):
        """Test volume calculation with complex tunnel geometry."""
        # Create curved tunnel path
        tunnel_path = TunnelPath()

        # Create S-curve tunnel
        for i in range(11):
            t = i / 10.0
            x = 5.0 + 10.0 * t
            y = 10.0 + 5.0 * np.sin(2 * np.pi * t)  # S-curve in y
            z = 100.0 + 2.0 * np.cos(2 * np.pi * t)  # Elevation variation
            tunnel_path.add_waypoint(x, y, z)

        tunnel_geometry = TunnelGeometry(
            path=tunnel_path,
            radius=1.8,
            cross_section_type="circular"
        )

        volume_calc = self.volume_calculator.calculate_tunnel_volume(
            tunnel_geometry, self.terrain_mesh
        )

        # Verify calculation is reasonable
        assert volume_calc.total_volume > 0
        assert len(volume_calc.excavation_zones) > 1  # Should have multiple zones

        # Approximate verification: should be close to cylinder volume
        # with some variation due to curvature
        path_length = tunnel_path.get_total_length()
        approximate_volume = np.pi * 1.8**2 * path_length

        relative_error = abs(volume_calc.total_volume - approximate_volume) / approximate_volume
        assert relative_error < 0.15, f"Complex tunnel volume error: {relative_error:.4f}"

    def test_volume_calculation_precision_validation(self):
        """Test volume calculation precision validation."""
        tunnel_path = TunnelPath()
        tunnel_path.add_waypoint(5.0, 10.0, 100.0)
        tunnel_path.add_waypoint(15.0, 10.0, 100.0)

        tunnel_geometry = TunnelGeometry(
            path=tunnel_path,
            radius=2.0,
            cross_section_type="circular"
        )

        # Calculate volume with different resolution settings
        volume_high_res = self.volume_calculator.calculate_tunnel_volume(
            tunnel_geometry, self.terrain_mesh, resolution='high'
        )

        volume_low_res = self.volume_calculator.calculate_tunnel_volume(
            tunnel_geometry, self.terrain_mesh, resolution='low'
        )

        # High resolution should be more accurate
        assert volume_high_res.accuracy_estimate <= volume_low_res.accuracy_estimate

        # Both should be within reasonable range of each other
        relative_difference = abs(volume_high_res.total_volume - volume_low_res.total_volume) / volume_high_res.total_volume
        assert relative_difference < 0.05, f"Resolution difference too high: {relative_difference:.4f}"

    def test_excavation_zone_classification(self):
        """Test excavation zone classification accuracy."""
        tunnel_path = TunnelPath()
        tunnel_path.add_waypoint(5.0, 10.0, 95.0)   # Below surface
        tunnel_path.add_waypoint(10.0, 10.0, 105.0)  # Above surface
        tunnel_path.add_waypoint(15.0, 10.0, 95.0)   # Below surface

        tunnel_geometry = TunnelGeometry(
            path=tunnel_path,
            radius=2.0,
            cross_section_type="circular"
        )

        volume_calc = self.volume_calculator.calculate_tunnel_volume(
            tunnel_geometry, self.terrain_mesh
        )

        # Should have different excavation zones
        assert len(volume_calc.excavation_zones) >= 2

        # Verify zone classifications
        for zone in volume_calc.excavation_zones:
            assert zone.volume > 0
            assert zone.zone_type in ['cut', 'fill', 'mixed']
            assert zone.start_distance >= 0
            assert zone.end_distance > zone.start_distance

    def test_volume_calculation_error_estimation(self):
        """Test volume calculation error estimation."""
        tunnel_path = TunnelPath()
        tunnel_path.add_waypoint(5.0, 10.0, 100.0)
        tunnel_path.add_waypoint(15.0, 10.0, 100.0)

        tunnel_geometry = TunnelGeometry(
            path=tunnel_path,
            radius=2.0,
            cross_section_type="circular"
        )

        volume_calc = self.volume_calculator.calculate_tunnel_volume(
            tunnel_geometry, self.terrain_mesh
        )

        # Should provide error estimate
        assert volume_calc.accuracy_estimate is not None
        assert volume_calc.accuracy_estimate >= 0
        assert volume_calc.accuracy_estimate <= 1.0  # Should be reasonable percentage

        # Error should be within specification (1% requirement)
        assert volume_calc.accuracy_estimate <= 0.01

    def test_volume_calculation_performance(self):
        """Test volume calculation performance."""
        import time

        # Create longer tunnel for performance testing
        tunnel_path = TunnelPath()
        for i in range(101):  # 100 waypoints
            x = i * 0.5
            y = 10.0 + 2.0 * np.sin(i * 0.1)
            z = 100.0 + np.sin(i * 0.05)
            tunnel_path.add_waypoint(x, y, z)

        tunnel_geometry = TunnelGeometry(
            path=tunnel_path,
            radius=2.0,
            cross_section_type="circular"
        )

        # Measure performance
        start_time = time.time()
        volume_calc = self.volume_calculator.calculate_tunnel_volume(
            tunnel_geometry, self.terrain_mesh
        )
        end_time = time.time()

        calculation_time = end_time - start_time

        # Should complete within reasonable time
        assert calculation_time < 2.0, f"Calculation took too long: {calculation_time:.2f}s"
        assert volume_calc.total_volume > 0

    def test_volume_calculation_boundary_conditions(self):
        """Test volume calculation at boundary conditions."""
        # Test with very small tunnel
        tiny_tunnel_path = TunnelPath()
        tiny_tunnel_path.add_waypoint(10.0, 10.0, 100.0)
        tiny_tunnel_path.add_waypoint(10.1, 10.0, 100.0)

        tiny_tunnel = TunnelGeometry(
            path=tiny_tunnel_path,
            radius=0.1,  # Very small radius
            cross_section_type="circular"
        )

        tiny_volume = self.volume_calculator.calculate_tunnel_volume(
            tiny_tunnel, self.terrain_mesh
        )

        assert tiny_volume.total_volume > 0
        assert tiny_volume.total_volume < 1.0  # Should be very small

        # Test with zero-length tunnel (should handle gracefully)
        zero_tunnel_path = TunnelPath()
        zero_tunnel_path.add_waypoint(10.0, 10.0, 100.0)
        zero_tunnel_path.add_waypoint(10.0, 10.0, 100.0)  # Same point

        zero_tunnel = TunnelGeometry(
            path=zero_tunnel_path,
            radius=2.0,
            cross_section_type="circular"
        )

        with pytest.raises(ValidationError, match="Tunnel path must have positive length"):
            self.volume_calculator.calculate_tunnel_volume(zero_tunnel, self.terrain_mesh)

    def test_volume_calculation_numerical_stability(self):
        """Test numerical stability of volume calculations."""
        # Test with very small elevations differences
        tunnel_path = TunnelPath()
        tunnel_path.add_waypoint(5.0, 10.0, 100.000001)
        tunnel_path.add_waypoint(15.0, 10.0, 100.000002)

        tunnel_geometry = TunnelGeometry(
            path=tunnel_path,
            radius=2.0,
            cross_section_type="circular"
        )

        # Should not suffer from numerical precision issues
        volume_calc = self.volume_calculator.calculate_tunnel_volume(
            tunnel_geometry, self.terrain_mesh
        )

        assert np.isfinite(volume_calc.total_volume)
        assert not np.isnan(volume_calc.total_volume)
        assert volume_calc.total_volume > 0

    def test_volume_calculation_cross_section_types(self):
        """Test volume calculation with different cross-section types."""
        tunnel_path = TunnelPath()
        tunnel_path.add_waypoint(5.0, 10.0, 100.0)
        tunnel_path.add_waypoint(15.0, 10.0, 100.0)

        # Test circular cross-section
        circular_tunnel = TunnelGeometry(
            path=tunnel_path,
            radius=2.0,
            cross_section_type="circular"
        )

        circular_volume = self.volume_calculator.calculate_tunnel_volume(
            circular_tunnel, self.terrain_mesh
        )

        # Test rectangular cross-section (equivalent area)
        # Rectangle with width * height = π * r²
        equivalent_area = np.pi * 2.0**2
        rect_width = np.sqrt(equivalent_area)
        rect_height = equivalent_area / rect_width

        rectangular_tunnel = TunnelGeometry(
            path=tunnel_path,
            width=rect_width,
            height=rect_height,
            cross_section_type="rectangular"
        )

        rectangular_volume = self.volume_calculator.calculate_tunnel_volume(
            rectangular_tunnel, self.terrain_mesh
        )

        # Volumes should be very close for equivalent cross-sectional areas
        relative_difference = abs(circular_volume.total_volume - rectangular_volume.total_volume) / circular_volume.total_volume
        assert relative_difference < 0.05, f"Cross-section volume difference: {relative_difference:.4f}"

    def test_volume_calculation_mesh_quality_impact(self):
        """Test impact of mesh quality on volume calculation accuracy."""
        # Create coarse mesh
        coarse_vertices = np.array([
            [0.0, 0.0, 100.0],
            [20.0, 0.0, 100.0],
            [20.0, 20.0, 100.0],
            [0.0, 20.0, 100.0],
        ])

        coarse_triangles = [
            Triangle(vertex_indices=[0, 1, 2]),
            Triangle(vertex_indices=[0, 2, 3]),
        ]

        coarse_mesh = TerrainMesh(vertices=coarse_vertices, triangles=coarse_triangles)

        # Create fine mesh
        fine_vertices = np.array([
            [0.0, 0.0, 100.0], [10.0, 0.0, 105.0], [20.0, 0.0, 100.0],
            [0.0, 10.0, 105.0], [10.0, 10.0, 110.0], [20.0, 10.0, 105.0],
            [0.0, 20.0, 100.0], [10.0, 20.0, 105.0], [20.0, 20.0, 100.0],
        ])

        fine_triangles = [
            Triangle(vertex_indices=[0, 1, 4]), Triangle(vertex_indices=[1, 2, 4]),
            Triangle(vertex_indices=[3, 4, 1]), Triangle(vertex_indices=[4, 5, 2]),
            Triangle(vertex_indices=[3, 6, 4]), Triangle(vertex_indices=[4, 6, 7]),
            Triangle(vertex_indices=[4, 7, 5]), Triangle(vertex_indices=[5, 7, 8]),
        ]

        fine_mesh = TerrainMesh(vertices=fine_vertices, triangles=fine_triangles)

        tunnel_path = TunnelPath()
        tunnel_path.add_waypoint(5.0, 10.0, 102.0)
        tunnel_path.add_waypoint(15.0, 10.0, 102.0)

        tunnel_geometry = TunnelGeometry(
            path=tunnel_path,
            radius=1.5,
            cross_section_type="circular"
        )

        # Calculate volumes with both meshes
        coarse_volume = self.volume_calculator.calculate_tunnel_volume(
            tunnel_geometry, coarse_mesh
        )

        fine_volume = self.volume_calculator.calculate_tunnel_volume(
            tunnel_geometry, fine_mesh
        )

        # Fine mesh should provide better accuracy
        assert fine_volume.accuracy_estimate <= coarse_volume.accuracy_estimate

        # Volumes should be reasonably close
        relative_difference = abs(coarse_volume.total_volume - fine_volume.total_volume) / fine_volume.total_volume
        assert relative_difference < 0.1, f"Mesh quality impact: {relative_difference:.4f}"

    def test_volume_calculation_export_functionality(self):
        """Test volume calculation data export functionality."""
        tunnel_path = TunnelPath()
        tunnel_path.add_waypoint(5.0, 10.0, 100.0)
        tunnel_path.add_waypoint(15.0, 10.0, 100.0)

        tunnel_geometry = TunnelGeometry(
            path=tunnel_path,
            radius=2.0,
            cross_section_type="circular"
        )

        volume_calc = self.volume_calculator.calculate_tunnel_volume(
            tunnel_geometry, self.terrain_mesh
        )

        # Test export to dictionary
        export_data = volume_calc.to_dict()

        assert 'total_volume' in export_data
        assert 'accuracy_estimate' in export_data
        assert 'excavation_zones' in export_data
        assert 'calculation_method' in export_data

        # Test export to CSV format
        csv_data = volume_calc.to_csv()

        assert isinstance(csv_data, str)
        assert 'total_volume' in csv_data
        assert 'accuracy_estimate' in csv_data

        # Verify numerical precision in export
        assert str(volume_calc.total_volume) in csv_data
        assert str(volume_calc.accuracy_estimate) in csv_data


if __name__ == "__main__":
    pytest.main([__file__])