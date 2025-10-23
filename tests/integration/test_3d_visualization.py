"""
Integration tests for 3D visualization workflow.

These tests validate the complete end-to-end workflow from terrain
loading through 3D visualization and animation for User Story 4.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
import plotly.graph_objects as go
from pathlib import Path
import tempfile

from src.services.visualization_3d import Visualization3DService
from src.services.animation import AnimationService
from src.services.contour_parser import ContourParser
from src.services.triangulation import TriangulationService
from src.models.contour_data import ContourData, ContourLine, ContourMetadata, CoordinateSystem
from src.models.terrain_mesh import TerrainMesh
from src.models.tunnel_geometry import TunnelGeometry
from src.utils.exceptions import VisualizationError, AnimationError


class Test3DVisualizationWorkflow:
    """Integration tests for complete 3D visualization workflow."""

    @pytest.fixture
    def sample_contour_data(self):
        """Create sample contour data for testing."""
        metadata = ContourMetadata(
            name="Test Terrain",
            units="meters",
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Create concentric square contours
        contours = [
            ContourLine(
                elevation=100.0,
                points=np.array([
                    [0, 0], [2, 0], [2, 2], [0, 2], [0, 0]
                ]),
                is_closed=True
            ),
            ContourLine(
                elevation=105.0,
                points=np.array([
                    [0.5, 0.5], [1.5, 0.5], [1.5, 1.5], [0.5, 1.5], [0.5, 0.5]
                ]),
                is_closed=True
            ),
            ContourLine(
                elevation=110.0,
                points=np.array([
                    [0.75, 0.75], [1.25, 0.75], [1.25, 1.25], [0.75, 1.25], [0.75, 0.75]
                ]),
                is_closed=True
            )
        ]

        return ContourData(
            metadata=metadata,
            contours=contours,
            bounds=None,  # Will be calculated
            coordinate_system=CoordinateSystem.LOCAL
        )

    @pytest.fixture
    def sample_tunnel_geometry(self):
        """Create sample tunnel geometry for testing."""
        start_point = np.array([0.3, 0.3])
        end_point = np.array([1.7, 1.7])
        radius = 0.15

        return TunnelGeometry(
            start_point=start_point,
            end_point=end_point,
            radius=radius,
            cross_section_type="semicircular",
            path_points=None,
            mesh_vertices=None,
            mesh_triangles=None
        )

    def test_complete_3d_visualization_workflow(self, sample_contour_data, sample_tunnel_geometry):
        """Test complete workflow from contour data to 3D visualization."""
        # Initialize services
        contour_parser = ContourParser()
        triangulation_service = TriangulationService()
        viz_3d_service = Visualization3DService()

        # Step 1: Triangulate terrain
        terrain_mesh = triangulation_service.generate_terrain_mesh(sample_contour_data)

        assert isinstance(terrain_mesh, TerrainMesh)
        assert terrain_mesh.vertex_count > 0
        assert len(terrain_mesh.triangles) > 0

        # Step 2: Create 3D terrain visualization
        terrain_fig = viz_3d_service.create_terrain_plot(
            terrain_mesh,
            title="3D Terrain Visualization"
        )

        assert isinstance(terrain_fig, go.Figure)
        assert len(terrain_fig.data) >= 1

        # Step 3: Create integrated terrain+tunnel visualization
        with patch.object(sample_tunnel_geometry, 'get_mesh_vertices',
                         return_value=np.array([[1.0, 1.0, 1.0]])), \
             patch.object(sample_tunnel_geometry, 'get_mesh_triangles', return_value=[]):

            integrated_fig = viz_3d_service.create_tunnel_overlay(
                terrain_mesh=terrain_mesh,
                tunnel_geometry=sample_tunnel_geometry,
                title="Terrain with Tunnel"
            )

            assert isinstance(integrated_fig, go.Figure)
            # Should have both terrain and tunnel traces
            assert len(integrated_fig.data) >= 1

    def test_3d_animation_workflow(self, sample_contour_data, sample_tunnel_geometry):
        """Test complete workflow including animation."""
        # Initialize services
        triangulation_service = TriangulationService()
        viz_3d_service = Visualization3DService()
        animation_service = AnimationService()

        # Generate terrain mesh
        terrain_mesh = triangulation_service.generate_terrain_mesh(sample_contour_data)

        # Create 3D visualization
        with patch.object(sample_tunnel_geometry, 'get_mesh_vertices',
                         return_value=np.array([[1.0, 1.0, 1.0]])), \
             patch.object(sample_tunnel_geometry, 'get_mesh_triangles', return_value=[]):

            base_fig = viz_3d_service.create_tunnel_overlay(
                terrain_mesh=terrain_mesh,
                tunnel_geometry=sample_tunnel_geometry
            )

            # Create animation
            animation_fig = animation_service.create_animation_figure(
                terrain_mesh=terrain_mesh,
                tunnel_geometry=sample_tunnel_geometry,
                duration=2.0
            )

            assert isinstance(animation_fig, go.Figure)
            assert hasattr(animation_fig, 'frames')
            assert len(animation_fig.frames) > 0

    def test_export_workflow_3d_scene(self, sample_contour_data, sample_tunnel_geometry):
        """Test exporting 3D scenes to various formats."""
        triangulation_service = TriangulationService()
        viz_3d_service = Visualization3DService()

        # Generate terrain mesh and visualization
        terrain_mesh = triangulation_service.generate_terrain_mesh(sample_contour_data)
        fig = viz_3d_service.create_terrain_plot(terrain_mesh)

        # Test HTML export
        html_output = viz_3d_service.export_scene_to_html(fig)
        assert isinstance(html_output, str)
        assert '<!DOCTYPE html>' in html_output

        # Test image export (mocked)
        with patch('plotly.graph_objects.Figure.write_image') as mock_write:
            viz_3d_service.export_scene_to_image(fig, filename='test_scene.png')
            mock_write.assert_called_once()

    def test_3d_visualization_performance_large_dataset(self):
        """Test 3D visualization performance with larger datasets."""
        # Create larger contour dataset
        metadata = ContourMetadata(
            name="Large Test Terrain",
            units="meters",
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Generate more contours
        contours = []
        for elevation in np.linspace(100, 200, 20):  # 20 contour levels
            # Create irregular polygon for each elevation
            angles = np.linspace(0, 2*np.pi, 12)
            radius = 2.0 + (elevation - 100) * 0.01

            points = []
            for angle in angles:
                noise = np.random.normal(0, 0.05)
                x = radius * np.cos(angle) + noise
                y = radius * np.sin(angle) + noise
                points.append([x, y])
            points.append(points[0])  # Close the contour

            contours.append(ContourLine(
                elevation=elevation,
                points=np.array(points),
                is_closed=True
            ))

        large_contour_data = ContourData(
            metadata=metadata,
            contours=contours,
            bounds=None,
            coordinate_system=CoordinateSystem.LOCAL
        )

        # Test triangulation performance
        triangulation_service = TriangulationService()
        viz_3d_service = Visualization3DService()

        import time
        start_time = time.time()

        terrain_mesh = triangulation_service.generate_terrain_mesh(large_contour_data)
        triangulation_time = time.time() - start_time

        start_time = time.time()
        fig = viz_3d_service.create_terrain_plot(terrain_mesh)
        visualization_time = time.time() - start_time

        # Performance assertions
        assert triangulation_time < 3.0  # Should complete within 3 seconds
        assert visualization_time < 2.0  # Should complete within 2 seconds
        assert isinstance(fig, go.Figure)

    def test_3d_visualization_error_handling(self):
        """Test error handling in 3D visualization workflow."""
        viz_3d_service = Visualization3DService()

        # Test with invalid terrain mesh
        invalid_mesh = TerrainMesh(
            vertices=np.array([]),
            triangles=[],
            elevation_data=np.array([]),
            bounds=None
        )

        with pytest.raises(VisualizationError, match="Terrain mesh has no vertices"):
            viz_3d_service.create_terrain_plot(invalid_mesh)

        # Test with corrupted terrain mesh
        corrupted_mesh = MagicMock()
        corrupted_mesh.vertex_count = 10
        corrupted_mesh.vertices = None

        with pytest.raises(VisualizationError, match="Failed to create terrain plot"):
            viz_3d_service.create_terrain_plot(corrupted_mesh)

    def test_3d_scene_with_custom_materials(self, sample_contour_data, sample_tunnel_geometry):
        """Test 3D scene creation with custom materials and styling."""
        triangulation_service = TriangulationService()

        # Custom material configuration
        custom_config = {
            'terrain_colorscale': 'Plasma',
            'tunnel_color': '#00AAFF',
            'tunnel_opacity': 0.9,
            'mesh_opacity': 0.8,
            'show_mesh_edges': True,
            'background_color': '#1a1a1a',
            'figure_width': 1200,
            'figure_height': 900
        }

        viz_service = Visualization3DService(style_config=custom_config)
        terrain_mesh = triangulation_service.generate_terrain_mesh(sample_contour_data)

        with patch.object(sample_tunnel_geometry, 'get_mesh_vertices',
                         return_value=np.array([[1.0, 1.0, 1.0]])), \
             patch.object(sample_tunnel_geometry, 'get_mesh_triangles', return_value=[]):

            fig = viz_service.create_tunnel_overlay(
                terrain_mesh=terrain_mesh,
                tunnel_geometry=sample_tunnel_geometry,
                title="Custom Materials Scene"
            )

            # Verify custom styling
            assert fig.layout.width == 1200
            assert fig.layout.height == 900
            assert fig.layout.paper_bgcolor == '#1a1a1a'

    def test_animation_workflow_with_camera_controls(self, sample_contour_data, sample_tunnel_geometry):
        """Test animation workflow with different camera control modes."""
        triangulation_service = TriangulationService()
        animation_service = AnimationService()
        terrain_mesh = triangulation_service.generate_terrain_mesh(sample_contour_data)

        # Test camera following mode
        follow_config = {'camera_follow': True, 'camera_distance': 3.0}
        follow_service = AnimationService(config=follow_config)

        with patch.object(sample_tunnel_geometry, 'get_path_points',
                         return_value=np.array([[0.5, 0.5, 1], [1.5, 1.5, 1.2]])):

            follow_frames = follow_service.create_animation_frames(
                tunnel_path=sample_tunnel_geometry,
                duration=1.0
            )

            # Verify camera follows car
            first_distance = np.linalg.norm(
                follow_frames[0].camera_position - follow_frames[0].car_position
            )
            last_distance = np.linalg.norm(
                follow_frames[-1].camera_position - follow_frames[-1].car_position
            )
            assert abs(first_distance - last_distance) < 0.1  # Distance should be consistent

        # Test fixed camera mode
        fixed_config = {'camera_follow': False}
        fixed_service = AnimationService(config=fixed_config)

        with patch.object(sample_tunnel_geometry, 'get_path_points',
                         return_value=np.array([[0.5, 0.5, 1], [1.5, 1.5, 1.2]])):

            fixed_frames = fixed_service.create_animation_frames(
                tunnel_path=sample_tunnel_geometry,
                duration=1.0
            )

            # Verify camera remains fixed
            first_camera = fixed_frames[0].camera_position
            for frame in fixed_frames[1:]:
                assert np.array_equal(frame.camera_position, first_camera)

    def test_end_to_end_workflow_with_file_io(self, sample_contour_data, sample_tunnel_geometry):
        """Test complete workflow including file I/O operations."""
        triangulation_service = TriangulationService()
        viz_3d_service = Visualization3DService()
        animation_service = AnimationService()

        # Generate terrain mesh
        terrain_mesh = triangulation_service.generate_terrain_mesh(sample_contour_data)

        # Create 3D visualization
        with patch.object(sample_tunnel_geometry, 'get_mesh_vertices',
                         return_value=np.array([[1.0, 1.0, 1.0]])), \
             patch.object(sample_tunnel_geometry, 'get_mesh_triangles', return_value=[]):

            fig = viz_3d_service.create_tunnel_overlay(
                terrain_mesh=terrain_mesh,
                tunnel_geometry=sample_tunnel_geometry
            )

            # Test file exports
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Export HTML
                html_file = temp_path / "visualization.html"
                html_content = viz_3d_service.export_scene_to_html(fig)
                html_file.write_text(html_content)
                assert html_file.exists()
                assert html_file.stat().st_size > 1000  # Should have substantial content

                # Create animation and export
                animation_fig = animation_service.create_animation_figure(
                    terrain_mesh=terrain_mesh,
                    tunnel_geometry=sample_tunnel_geometry,
                    duration=1.0
                )

                # Export animation HTML
                anim_html_file = temp_path / "animation.html"
                anim_html_content = animation_service.export_animation_html(animation_fig)
                anim_html_file.write_text(anim_html_content)
                assert anim_html_file.exists()
                assert anim_html_file.stat().st_size > 1000

    def test_3d_visualization_coordinate_consistency(self, sample_contour_data):
        """Test coordinate system consistency between 2D and 3D visualizations."""
        triangulation_service = TriangulationService()
        viz_3d_service = Visualization3DService()

        # Generate terrain mesh
        terrain_mesh = triangulation_service.generate_terrain_mesh(sample_contour_data)

        # Create 3D visualization
        fig_3d = viz_3d_service.create_terrain_plot(terrain_mesh)

        # Verify coordinate bounds consistency
        terrain_bounds = terrain_mesh.get_bounds()
        surface_trace = fig_3d.data[0]

        # Check that 3D visualization uses same coordinate ranges as original data
        assert min(surface_trace.x) >= terrain_bounds.min_x - 0.01
        assert max(surface_trace.x) <= terrain_bounds.max_x + 0.01
        assert min(surface_trace.y) >= terrain_bounds.min_y - 0.01
        assert max(surface_trace.y) <= terrain_bounds.max_y + 0.01

    def test_complex_tunnel_animation_scenario(self, sample_contour_data):
        """Test animation with complex tunnel geometry."""
        triangulation_service = TriangulationService()
        animation_service = AnimationService()

        # Create a curved tunnel path
        start_point = np.array([0.2, 0.2])
        mid_point = np.array([1.0, 1.8])
        end_point = np.array([1.8, 1.0])

        curved_tunnel = TunnelGeometry(
            start_point=start_point,
            end_point=end_point,
            radius=0.12,
            cross_section_type="semicircular",
            path_points=None,
            mesh_vertices=None,
            mesh_triangles=None
        )

        # Mock curved path points
        curved_path_points = np.array([
            [0.2, 0.2, 1.0],
            [0.6, 0.6, 1.1],
            [1.0, 1.8, 1.2],
            [1.4, 1.4, 1.15],
            [1.8, 1.0, 1.1]
        ])

        terrain_mesh = triangulation_service.generate_terrain_mesh(sample_contour_data)

        with patch.object(curved_tunnel, 'get_path_points', return_value=curved_path_points), \
             patch.object(curved_tunnel, 'get_mesh_vertices', return_value=curved_path_points), \
             patch.object(curved_tunnel, 'get_mesh_triangles', return_value=[]):

            # Create animation with realistic car speed
            frames = animation_service.create_animation_frames(
                tunnel_path=curved_tunnel,
                duration=3.0
            )

            # Verify smooth path following
            assert len(frames) == 90  # 30 fps * 3 seconds

            # Check path continuity
            for i in range(1, len(frames)):
                prev_pos = frames[i-1].car_position
                curr_pos = frames[i].car_position

                # Position should change smoothly
                distance = np.linalg.norm(curr_pos - prev_pos)
                assert 0 < distance < 0.2  # Should move but not too far

            # Verify car follows curved path
            path_positions = [frame.car_position for frame in frames]
            assert len(set(tuple(p.round(2)) for p in path_positions)) > 10  # Should visit many positions

    def test_3d_visualization_memory_usage(self, sample_contour_data):
        """Test memory usage during 3D visualization creation."""
        import psutil
        import os

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        triangulation_service = TriangulationService()
        viz_3d_service = Visualization3DService()

        # Create multiple 3D visualizations
        terrain_mesh = triangulation_service.generate_terrain_mesh(sample_contour_data)

        figures = []
        for i in range(5):  # Create 5 visualizations
            fig = viz_3d_service.create_terrain_plot(
                terrain_mesh,
                title=f"Visualization {i+1}"
            )
            figures.append(fig)

        # Check memory usage
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / (1024 * 1024)  # MB

        # Memory increase should be reasonable (less than 200MB for this test)
        assert memory_increase < 200
        assert len(figures) == 5