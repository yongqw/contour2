"""
Tests for data models.
"""

import unittest
import numpy as np
from models.terrain_mesh import Triangle, TerrainMesh
from models.tunnel_geometry import TunnelWaypoint, TunnelPath, TunnelGeometry, CrossSectionType


class TestTriangle(unittest.TestCase):
    """Test the Triangle model."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.triangle = Triangle(vertex_indices=[0, 1, 2])
        
    def test_triangle_initialization(self):
        """Test triangle initialization."""
        self.assertEqual(self.triangle.vertex_indices, [0, 1, 2])
        self.assertIsNone(self.triangle.normal)
        
    def test_triangle_validation(self):
        """Test triangle validation."""
        # Valid triangle
        triangle = Triangle(vertex_indices=[0, 1, 2])
        self.assertEqual(triangle.vertex_indices, [0, 1, 2])
        
        # Invalid triangle (too many vertices)
        with self.assertRaises(ValueError):
            Triangle(vertex_indices=[0, 1, 2, 3])
            
        # Invalid triangle (too few vertices)
        with self.assertRaises(ValueError):
            Triangle(vertex_indices=[0, 1])
            
    def test_triangle_normal(self):
        """Test triangle normal calculation."""
        # Create a simple triangle in the XY plane
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0]
        ])
        
        # Normal should point up in the Z direction
        normal = self.triangle.get_normal(vertices)
        expected_normal = np.array([0, 0, 1])
        np.testing.assert_array_almost_equal(normal, expected_normal)
        
    def test_triangle_area(self):
        """Test triangle area calculation."""
        # Create a right triangle with area 0.5
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0]
        ])
        
        area = self.triangle.get_area(vertices)
        self.assertAlmostEqual(area, 0.5, places=5)
        
    def test_triangle_center(self):
        """Test triangle center calculation."""
        vertices = np.array([
            [0, 0, 0],
            [2, 0, 0],
            [0, 2, 0]
        ])
        
        center = self.triangle.get_center(vertices)
        expected_center = np.array([2/3, 2/3, 0])
        np.testing.assert_array_almost_equal(center, expected_center)


class TestTerrainMesh(unittest.TestCase):
    """Test the TerrainMesh model."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a simple triangle mesh (two triangles forming a square)
        self.vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [1, 1, 0]
        ])
        
        self.triangles = [
            Triangle(vertex_indices=[0, 1, 2]),
            Triangle(vertex_indices=[1, 3, 2])
        ]
        
        self.mesh = TerrainMesh(vertices=self.vertices, triangles=self.triangles)
        
    def test_mesh_initialization(self):
        """Test mesh initialization."""
        self.assertEqual(self.mesh.vertex_count, 4)
        self.assertEqual(self.mesh.triangle_count, 2)
        self.assertIsNone(self.mesh.vertex_colors)
        self.assertIsNone(self.mesh.vertex_normals)
        
    def test_mesh_validation(self):
        """Test mesh validation."""
        is_valid, issues = self.mesh.validate_mesh()
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)
        
    def test_invalid_mesh_validation(self):
        """Test validation of invalid mesh."""
        # Invalid vertex index - should raise ValueError during initialization
        invalid_triangles = [
            Triangle(vertex_indices=[0, 1, 5])  # Index 5 doesn't exist
        ]
        
        # Expect ValueError during initialization
        with self.assertRaises(ValueError) as cm:
            invalid_mesh = TerrainMesh(vertices=self.vertices, triangles=invalid_triangles)
        
        self.assertIn("Triangle vertex index 5 exceeds vertex count", str(cm.exception))
        
    def test_mesh_bounds(self):
        """Test mesh bounding box calculation."""
        bounds = self.mesh.get_bounds()
        expected_bounds = (0, 1, 0, 1, 0, 0)  # min_x, max_x, min_y, max_y, min_z, max_z
        self.assertEqual(bounds, expected_bounds)
        
    def test_mesh_serialization(self):
        """Test mesh serialization to/from dict."""
        data = self.mesh.to_dict()
        self.assertIn('vertices', data)
        self.assertIn('triangles', data)
        
        # Recreate mesh from dict
        recreated_mesh = TerrainMesh.from_dict(data)
        
        # Check that vertices and triangles are the same
        np.testing.assert_array_equal(recreated_mesh.vertices, self.mesh.vertices)
        self.assertEqual(len(recreated_mesh.triangles), len(self.mesh.triangles))
        
    def test_mesh_copy(self):
        """Test mesh copying."""
        mesh_copy = self.mesh.copy()
        
        # Check that vertices and triangles are the same but not the same objects
        np.testing.assert_array_equal(mesh_copy.vertices, self.mesh.vertices)
        self.assertNotEqual(id(mesh_copy.vertices), id(self.mesh.vertices))
        
        self.assertEqual(len(mesh_copy.triangles), len(self.mesh.triangles))
        self.assertNotEqual(id(mesh_copy.triangles), id(self.mesh.triangles))


class TestTunnelWaypoint(unittest.TestCase):
    """Test the TunnelWaypoint model."""
    
    def test_waypoint_initialization(self):
        """Test waypoint initialization."""
        waypoint = TunnelWaypoint(x=10.0, y=20.0, elevation=100.0, radius=5.0)
        self.assertEqual(waypoint.x, 10.0)
        self.assertEqual(waypoint.y, 20.0)
        self.assertEqual(waypoint.elevation, 100.0)
        self.assertEqual(waypoint.radius, 5.0)
        
    def test_waypoint_default_radius(self):
        """Test waypoint with default radius."""
        waypoint = TunnelWaypoint(x=10.0, y=20.0, elevation=100.0)
        self.assertEqual(waypoint.radius, 25.0)  # Default value
        
    def test_waypoint_serialization(self):
        """Test waypoint serialization to/from dict."""
        waypoint = TunnelWaypoint(x=10.0, y=20.0, elevation=100.0, radius=5.0)
        
        # Convert to dict
        data = waypoint.to_dict()
        self.assertEqual(data['x'], 10.0)
        self.assertEqual(data['y'], 20.0)
        self.assertEqual(data['elevation'], 100.0)
        self.assertEqual(data['radius'], 5.0)
        
        # Recreate from dict
        recreated_waypoint = TunnelWaypoint.from_dict(data)
        self.assertEqual(recreated_waypoint.x, waypoint.x)
        self.assertEqual(recreated_waypoint.y, waypoint.y)
        self.assertEqual(recreated_waypoint.elevation, waypoint.elevation)
        self.assertEqual(recreated_waypoint.radius, waypoint.radius)


class TestTunnelPath(unittest.TestCase):
    """Test the TunnelPath model."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.waypoints = [
            TunnelWaypoint(x=0, y=0, elevation=100, radius=5),
            TunnelWaypoint(x=100, y=0, elevation=100, radius=5),
            TunnelWaypoint(x=200, y=0, elevation=110, radius=6)
        ]
        self.path = TunnelPath(waypoints=self.waypoints)
        
    def test_path_initialization(self):
        """Test path initialization."""
        self.assertEqual(len(self.path.waypoints), 3)
        self.assertEqual(self.path.cross_section_type, CrossSectionType.CIRCULAR)
        self.assertAlmostEqual(self.path.tunnel_length, 200.5, places=1)  # Approximate length
        
    def test_path_validation(self):
        """Test path validation."""
        # Valid path
        self.assertTrue(self.path.validate_path())
        
        # Path with too few waypoints
        invalid_path = TunnelPath(waypoints=[self.waypoints[0]])
        self.assertFalse(invalid_path.validate_path())
        
        # Path with invalid coordinates
        invalid_waypoint = TunnelWaypoint(x=1e7, y=0, elevation=100, radius=5)  # x coordinate too large
        invalid_path = TunnelPath(waypoints=[self.waypoints[0], invalid_waypoint])
        self.assertFalse(invalid_path.validate_path())
        
    def test_path_serialization(self):
        """Test path serialization to/from dict."""
        data = self.path.to_dict()
        self.assertIn('waypoints', data)
        self.assertEqual(data['cross_section_type'], 'circular')
        
        # Recreate from dict
        recreated_path = TunnelPath.from_dict(data)
        self.assertEqual(len(recreated_path.waypoints), len(self.path.waypoints))
        self.assertEqual(recreated_path.cross_section_type, self.path.cross_section_type)
        
    def test_position_at_distance(self):
        """Test getting position at specific distance along path."""
        # Test at start
        pos = self.path.get_position_at_distance(0)
        self.assertEqual(pos, (0, 0, 100, 5))
        
        # Test at end
        pos = self.path.get_position_at_distance(self.path.tunnel_length)
        self.assertEqual(pos, (200, 0, 110, 6))
        
        # Test in middle
        pos = self.path.get_position_at_distance(100)
        self.assertAlmostEqual(pos[0], 100, places=0)
        self.assertAlmostEqual(pos[1], 0, places=0)
        self.assertGreaterEqual(pos[2], 100)  # Elevation should be between 100 and 110
        self.assertAlmostEqual(pos[3], 5, places=0)  # Radius should be between 5 and 6


class TestTunnelGeometry(unittest.TestCase):
    """Test the TunnelGeometry model."""
    
    def setUp(self):
        """Set up test fixtures."""
        waypoints = [
            TunnelWaypoint(x=0, y=0, elevation=100, radius=5),
            TunnelWaypoint(x=100, y=0, elevation=100, radius=5)
        ]
        path = TunnelPath(waypoints=waypoints)
        self.geometry = TunnelGeometry(path=path)
        
    def test_geometry_initialization(self):
        """Test geometry initialization."""
        # Path was created in setUp method, access through self.geometry
        self.assertIsNotNone(self.geometry.path)
        self.assertEqual(len(self.geometry.path.waypoints), 2)
        self.assertIsNone(self.geometry.volume)
        self.assertIsNone(self.geometry.surface_area)
        self.assertIn('density', self.geometry.material_properties)
        
    def test_cross_section_area(self):
        """Test cross-section area calculation."""
        # Circular cross-section
        area = self.geometry.get_cross_section_area(5.0)
        expected_area = 3.14159 * 5.0**2  # πr²
        self.assertAlmostEqual(area, expected_area, places=2)
        
        # Test with rectangular cross-section
        rectangular_path = TunnelPath(
            waypoints=self.geometry.path.waypoints,
            cross_section_type=CrossSectionType.RECTANGULAR
        )
        rectangular_geometry = TunnelGeometry(path=rectangular_path)
        
        area = rectangular_geometry.get_cross_section_area(5.0)
        expected_area = (2 * 5.0)**2  # (2r)²
        self.assertAlmostEqual(area, expected_area, places=2)
        
    def test_volume_calculation(self):
        """Test volume calculation."""
        volume = self.geometry.calculate_volume()
        expected_volume = 3.14159 * 5.0**2 * 100.0  # πr² × length
        self.assertAlmostEqual(volume, expected_volume, delta=10.0)
        self.assertEqual(self.geometry.volume, volume)
        
    def test_surface_area_calculation(self):
        """Test surface area calculation."""
        area = self.geometry.calculate_surface_area()
        expected_area = 2 * 3.14159 * 5.0 * 100.0  # 2πr × length
        self.assertAlmostEqual(area, expected_area, delta=10.0)
        self.assertEqual(self.geometry.surface_area, area)
        
    def test_mesh_generation(self):
        """Test mesh generation."""
        vertices = self.geometry.get_mesh_vertices(segments_per_section=8, points_per_segment=2)
        self.assertIsNotNone(vertices)
        self.assertGreater(len(vertices), 0)
        
        triangles = self.geometry.get_mesh_triangles(segments_per_section=8, points_per_segment=2)
        self.assertIsNotNone(triangles)
        self.assertGreater(len(triangles), 0)
        
        mesh = self.geometry.get_complete_mesh(segments_per_section=8, points_per_segment=2)
        self.assertIsNotNone(mesh)
        self.assertIn('vertices', mesh)
        self.assertIn('triangles', mesh)
        
    def test_centerline_generation(self):
        """Test centerline generation."""
        centerline = self.geometry.get_tunnel_centerline(num_points=10)
        self.assertIsNotNone(centerline)
        self.assertEqual(len(centerline), 10)
        self.assertEqual(centerline.shape[1], 3)  # 3D coordinates (x, y, elevation)
        
    def test_geometry_serialization(self):
        """Test geometry serialization to/from dict."""
        # Calculate volume and surface area first
        self.geometry.calculate_volume()
        self.geometry.calculate_surface_area()
        
        data = self.geometry.to_dict()
        self.assertIn('path', data)
        self.assertEqual(data['volume'], self.geometry.volume)
        
        # Recreate from dict
        recreated_geometry = TunnelGeometry.from_dict(data)
        self.assertEqual(recreated_geometry.volume, self.geometry.volume)
        self.assertEqual(recreated_geometry.surface_area, self.geometry.surface_area)


if __name__ == '__main__':
    unittest.main()