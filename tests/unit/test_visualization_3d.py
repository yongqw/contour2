"""
Unit tests for 3D visualization service.

These tests validate 3D scene creation, terrain+tunnel integration,
and visualization functionality for User Story 4.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
import plotly.graph_objects as go

from src.services.visualization_3d import Visualization3DService
from src.models.terrain_mesh import TerrainMesh, Triangle
from src.models.tunnel_geometry import TunnelGeometry, TunnelPath
from src.utils.exceptions import VisualizationError


class TestVisualization3DService:
    """Test cases for 3D visualization service."""

    def test_service_initialization_default_config(self):
        """Test service initialization with default configuration."""
        service = Visualization3DService()

        assert service.style_config['figure_width'] == 800
        assert service.style_config['figure_height'] == 600
        assert service.style_config['terrain_colorscheme'] == 'Viridis'
        assert service.style_config['tunnel_color'] == '#FF6B6B'
        assert service.style_config['tunnel_opacity'] == 0.8

    def test_service_initialization_custom_config(self):
        """Test service initialization with custom configuration."""
        custom_config = {
            'figure_width': 1024,
            'figure_height': 768,
            'tunnel_color': '#00FF00'
        }

        service = Visualization3DService(style_config=custom_config)

        assert service.style_config['figure_width'] == 1024
        assert service.style_config['figure_height'] == 768
        assert service.style_config['tunnel_color'] == '#00FF00'
        # Default values should remain for unchanged config
        assert service.style_config['terrain_colorscheme'] == 'Viridis'

    @pytest.fixture
    def sample_terrain_mesh(self):
        """Create a sample terrain mesh for testing."""
        # Create a simple pyramid-like terrain
        vertices = np.array([
            [0, 0, 0],      # Base corner 1
            [1, 0, 0],      # Base corner 2
            [1, 1, 0],      # Base corner 3
            [0, 1, 0],      # Base corner 4
            [0.5, 0.5, 1]   # Peak
        ])

        triangles = [
            Triangle(vertex_indices=[0, 1, 4]),  # Side 1
            Triangle(vertex_indices=[1, 2, 4]),  # Side 2
            Triangle(vertex_indices=[2, 3, 4]),  # Side 3
            Triangle(vertex_indices=[3, 0, 4]),  # Side 4
            Triangle(vertex_indices=[0, 1, 2]),  # Base triangle 1
            Triangle(vertex_indices=[0, 2, 3]),  # Base triangle 2
        ]

        return TerrainMesh(
            vertices=vertices,
            triangles=triangles,
            elevation_data=vertices[:, 2],
            bounds=None  # Will be calculated automatically
        )

    def test_create_terrain_plot_success(self, sample_terrain_mesh):
        """Test successful creation of terrain plot."""
        service = Visualization3DService()

        fig = service.create_terrain_plot(sample_terrain_mesh, title="Test Terrain")

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1  # Should have one surface trace
        assert fig.layout.title.text == "Test Terrain"

        # Check mesh data
        surface_trace = fig.data[0]
        assert len(surface_trace.x) == 5  # 5 vertices
        assert len(surface_trace.y) == 5
        assert len(surface_trace.z) == 5
        assert len(surface_trace.i) == 6   # 6 triangles
        assert len(surface_trace.j) == 6
        assert len(surface_trace.k) == 6

    def test_create_terrain_plot_with_wireframe(self, sample_terrain_mesh):
        """Test terrain plot creation with wireframe overlay."""
        service = Visualization3DService()

        fig = service.create_terrain_plot(sample_terrain_mesh, show_wireframe=True)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # Surface + wireframe traces
        assert fig.data[0].type == 'mesh3d'  # Surface
        assert fig.data[1].type == 'scatter3d'  # Wireframe edges

    def test_create_terrain_plot_empty_mesh(self):
        """Test terrain plot creation with empty mesh."""
        service = Visualization3DService()
        empty_mesh = TerrainMesh(
            vertices=np.array([]),
            triangles=[],
            elevation_data=np.array([]),
            bounds=None
        )

        with pytest.raises(VisualizationError, match="Terrain mesh has no vertices"):
            service.create_terrain_plot(empty_mesh)

    def test_create_terrain_plot_invalid_data(self):
        """Test terrain plot creation with invalid data."""
        service = Visualization3DService()

        # Create mesh with mismatched data
        invalid_mesh = MagicMock()
        invalid_mesh.vertex_count = 1
        invalid_mesh.vertices = np.array([[1, 2]])  # Missing z coordinate

        with pytest.raises(VisualizationError, match="Failed to create terrain plot"):
            service.create_terrain_plot(invalid_mesh)

    @pytest.fixture
    def sample_tunnel_geometry(self):
        """Create a sample tunnel geometry for testing."""
        # Create a simple straight tunnel
        start_point = np.array([0.2, 0.2])
        end_point = np.array([0.8, 0.8])
        radius = 0.1

        return TunnelGeometry(
            start_point=start_point,
            end_point=end_point,
            radius=radius,
            cross_section_type="semicircular",
            path_points=None,  # Will be calculated
            mesh_vertices=None,
            mesh_triangles=None
        )

    def test_create_tunnel_overlay_success(self, sample_terrain_mesh, sample_tunnel_geometry):
        """Test successful creation of terrain+tunnel overlay."""
        service = Visualization3DService()

        # Mock the tunnel mesh creation since it requires complex geometry
        with patch.object(sample_tunnel_geometry, 'get_mesh_vertices', return_value=np.array([[0.5, 0.5, 0.5]])), \
             patch.object(sample_tunnel_geometry, 'get_mesh_triangles', return_value=[]):

            fig = service.create_tunnel_overlay(
                sample_terrain_mesh,
                sample_tunnel_geometry,
                title="Terrain with Tunnel"
            )

            assert isinstance(fig, go.Figure)
            assert fig.layout.title.text == "Terrain with Tunnel"

    def test_create_tunnel_overlay_without_tunnel(self, sample_terrain_mesh):
        """Test terrain overlay creation without tunnel geometry."""
        service = Visualization3DService()

        fig = service.create_tunnel_overlay(sample_terrain_mesh, tunnel_geometry=None)

        assert isinstance(fig, go.Figure)
        # Should still have terrain surface
        assert len(fig.data) >= 1
        assert fig.data[0].type == 'mesh3d'

    def test_create_integrated_scene(self, sample_terrain_mesh, sample_tunnel_geometry):
        """Test creation of fully integrated 3D scene with terrain and tunnel."""
        service = Visualization3DService()

        with patch.object(sample_tunnel_geometry, 'get_mesh_vertices', return_value=np.array([[0.5, 0.5, 0.5]])), \
             patch.object(sample_tunnel_geometry, 'get_mesh_triangles', return_value=[]):

            fig = service.create_integrated_scene(
                terrain_mesh=sample_terrain_mesh,
                tunnel_geometry=sample_tunnel_geometry,
                title="Integrated 3D Scene"
            )

            assert isinstance(fig, go.Figure)
            assert fig.layout.title.text == "Integrated 3D Scene"

            # Should have terrain surface
            terrain_traces = [trace for trace in fig.data if trace.type == 'mesh3d' and trace.name == 'Terrain']
            assert len(terrain_traces) == 1

    def test_scene_camera_controls(self, sample_terrain_mesh):
        """Test camera control configuration in 3D scene."""
        custom_camera_config = {
            'camera_eye': {'x': 2, 'y': 2, 'z': 2},
            'camera_center': {'x': 0.5, 'y': 0.5, 'z': 0.5}
        }

        service = Visualization3DService(style_config=custom_camera_config)
        fig = service.create_terrain_plot(sample_terrain_mesh)

        # Check camera configuration
        scene = fig.layout.scene
        assert scene.camera.eye.x == 2
        assert scene.camera.eye.y == 2
        assert scene.camera.eye.z == 2
        assert scene.camera.center.x == 0.5
        assert scene.camera.center.y == 0.5
        assert scene.camera.center.z == 0.5

    def test_scene_lighting_configuration(self, sample_terrain_mesh):
        """Test lighting configuration in 3D scene."""
        custom_lighting = {
            'lighting_position': {'x': 50, 'y': 50, 'z': 500},
            'lighting_ambient': 0.6,
            'lighting_diffuse': 0.4
        }

        service = Visualization3DService(style_config=custom_lighting)
        fig = service.create_terrain_plot(sample_terrain_mesh)

        # Lighting is applied through plotly's internal system
        # We verify the config was stored correctly
        assert service.style_config['lighting_position']['x'] == 50
        assert service.style_config['lighting_ambient'] == 0.6
        assert service.style_config['lighting_diffuse'] == 0.4

    def test_scene_color_customization(self, sample_terrain_mesh):
        """Test color scheme customization for terrain and tunnel."""
        custom_colors = {
            'terrain_colorscale': 'Blues',
            'tunnel_color': '#FF0000',
            'tunnel_opacity': 0.9,
            'mesh_opacity': 0.7
        }

        service = Visualization3DService(style_config=custom_colors)
        fig = service.create_terrain_plot(sample_terrain_mesh)

        surface_trace = fig.data[0]
        assert surface_trace.colorscale == 'Blues'
        assert surface_trace.opacity == 0.7

    def test_export_scene_to_html(self, sample_terrain_mesh):
        """Test exporting 3D scene to HTML format."""
        service = Visualization3DService()
        fig = service.create_terrain_plot(sample_terrain_mesh)

        html_output = service.export_scene_to_html(fig, include_plotlyjs=True)

        assert isinstance(html_output, str)
        assert '<!DOCTYPE html>' in html_output
        assert 'plotly' in html_output.lower()
        assert '3d' in html_output.lower()

    def test_export_scene_to_image(self, sample_terrain_mesh):
        """Test exporting 3D scene to image format."""
        service = Visualization3DService()
        fig = service.create_terrain_plot(sample_terrain_mesh)

        # Mock the image export since it requires additional dependencies
        with patch('plotly.graph_objects.Figure.write_image') as mock_write:
            service.export_scene_to_image(fig, filename='test_scene.png', width=800, height=600)
            mock_write.assert_called_once_with('test_scene.png', width=800, height=600)

    def test_scene_interaction_settings(self, sample_terrain_mesh):
        """Test interactive settings for 3D scene."""
        interaction_config = {
            'show_axes': True,
            'axes_labels': {'x': 'East (m)', 'y': 'North (m)', 'z': 'Elevation (m)'},
            'background_color': '#F0F0F0'
        }

        service = Visualization3DService(style_config=interaction_config)
        fig = service.create_terrain_plot(sample_terrain_mesh)

        scene = fig.layout.scene
        assert scene.xaxis.title.text == 'East (m)'
        assert scene.yaxis.title.text == 'North (m)'
        assert scene.zaxis.title.text == 'Elevation (m)'
        assert fig.layout.paper_bgcolor == '#F0F0F0'

    def test_large_dataset_performance(self):
        """Test visualization performance with large datasets."""
        # Create a larger terrain mesh
        vertices = []
        triangles = []

        # Generate a 20x20 grid (400 vertices)
        for i in range(20):
            for j in range(20):
                vertices.append([i * 0.1, j * 0.1, np.sin(i * 0.5) * np.cos(j * 0.5)])

        vertices = np.array(vertices)

        # Create triangles for the grid
        for i in range(19):
            for j in range(19):
                idx = i * 20 + j
                # Two triangles per grid cell
                triangles.append(Triangle(vertex_indices=[idx, idx + 1, idx + 20]))
                triangles.append(Triangle(vertex_indices=[idx + 1, idx + 21, idx + 20]))

        large_mesh = TerrainMesh(
            vertices=vertices,
            triangles=triangles,
            elevation_data=vertices[:, 2],
            bounds=None
        )

        service = Visualization3DService()

        # This should complete without timeout
        import time
        start_time = time.time()

        fig = service.create_terrain_plot(large_mesh)

        elapsed_time = time.time() - start_time
        assert elapsed_time < 5.0  # Should complete within 5 seconds
        assert isinstance(fig, go.Figure)
        assert len(fig.data[0].x) == 400  # All vertices included

    def test_error_handling_invalid_terrain_data(self):
        """Test error handling with invalid terrain data."""
        service = Visualization3DService()

        # Test with None input
        with pytest.raises(VisualizationError):
            service.create_terrain_plot(None)

        # Test with corrupted mesh
        corrupted_mesh = MagicMock()
        corrupted_mesh.vertex_count = 10
        corrupted_mesh.vertices = None  # Corrupted data

        with pytest.raises(VisualizationError):
            service.create_terrain_plot(corrupted_mesh)

    def test_distinct_materials_terrain_vs_tunnel(self, sample_terrain_mesh, sample_tunnel_geometry):
        """Test that terrain and tunnel have distinct visual materials."""
        service = Visualization3DService()

        # Configure distinct materials
        material_config = {
            'terrain_colorscale': 'Earth',
            'tunnel_color': '#FF4444',
            'tunnel_opacity': 0.8,
            'mesh_opacity': 1.0
        }

        service_with_materials = Visualization3DService(style_config=material_config)

        with patch.object(sample_tunnel_geometry, 'get_mesh_vertices', return_value=np.array([[0.5, 0.5, 0.5]])), \
             patch.object(sample_tunnel_geometry, 'get_mesh_triangles', return_value=[]):

            fig = service_with_materials.create_integrated_scene(
                terrain_mesh=sample_terrain_mesh,
                tunnel_geometry=sample_tunnel_geometry
            )

            # Verify distinct traces for terrain and tunnel
            terrain_traces = [trace for trace in fig.data if 'Terrain' in trace.name]
            tunnel_traces = [trace for trace in fig.data if 'Tunnel' in trace.name]

            # Should have at least terrain trace
            assert len(terrain_traces) >= 1
            # Terrain should use Earth colorscale
            assert terrain_traces[0].colorscale == 'Earth'