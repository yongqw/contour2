"""
Unit tests for animation service.

These tests validate car movement along tunnel path, camera following,
and animation functionality for User Story 4.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
import plotly.graph_objects as go
from pathlib import Path

from src.services.animation import AnimationService, AnimationFrame
from src.models.tunnel_geometry import TunnelGeometry, TunnelPath
from src.models.terrain_mesh import TerrainMesh
from src.utils.exceptions import AnimationError


class TestAnimationService:
    """Test cases for animation service."""

    def test_service_initialization_default_config(self):
        """Test animation service initialization with default configuration."""
        service = AnimationService()

        assert service.config['fps'] == 30
        assert service.config['car_speed'] == 10.0  # m/s
        assert service.config['camera_follow'] == True
        assert service.config['camera_distance'] == 5.0
        assert service.config['camera_height'] == 2.0

    def test_service_initialization_custom_config(self):
        """Test animation service initialization with custom configuration."""
        custom_config = {
            'fps': 60,
            'car_speed': 15.0,
            'camera_distance': 8.0
        }

        service = AnimationService(config=custom_config)

        assert service.config['fps'] == 60
        assert service.config['car_speed'] == 15.0
        assert service.config['camera_distance'] == 8.0
        # Default values should remain for unchanged config
        assert service.config['camera_follow'] == True

    @pytest.fixture
    def sample_tunnel_path(self):
        """Create a sample tunnel path for testing."""
        # Create a curved tunnel path
        waypoints = [
            np.array([0.0, 0.0]),
            np.array([1.0, 0.5]),
            np.array([2.0, 1.0]),
            np.array([3.0, 1.5])
        ]

        return TunnelPath(
            waypoints=waypoints,
            interpolated_points=None,  # Will be calculated
            total_length=None
        )

    @pytest.fixture
    def sample_tunnel_geometry(self):
        """Create a sample tunnel geometry for testing."""
        start_point = np.array([0.0, 0.0])
        end_point = np.array([3.0, 1.5])
        radius = 2.0

        return TunnelGeometry(
            start_point=start_point,
            end_point=end_point,
            radius=radius,
            cross_section_type="semicircular",
            path_points=None,
            mesh_vertices=None,
            mesh_triangles=None
        )

    @pytest.fixture
    def sample_terrain_mesh(self):
        """Create a sample terrain mesh for testing."""
        vertices = np.array([
            [0, 0, 0], [3, 0, 0], [3, 3, 0], [0, 3, 0],  # Base
            [1.5, 0.75, 2]  # Peak
        ])

        triangles = [
            MagicMock(vertex_indices=[0, 1, 4]),
            MagicMock(vertex_indices=[1, 2, 4]),
            MagicMock(vertex_indices=[2, 3, 4]),
            MagicMock(vertex_indices=[3, 0, 4]),
            MagicMock(vertex_indices=[0, 1, 2]),
            MagicMock(vertex_indices=[0, 2, 3])
        ]

        return TerrainMesh(
            vertices=vertices,
            triangles=triangles,
            elevation_data=vertices[:, 2],
            bounds=None
        )

    def test_create_animation_frames_linear_path(self, sample_tunnel_path):
        """Test creating animation frames for a linear tunnel path."""
        service = AnimationService(config={'fps': 10, 'car_speed': 5.0})

        frames = service.create_animation_frames(
            tunnel_path=sample_tunnel_path,
            duration=2.0  # 2 seconds
        )

        assert len(frames) == 20  # 10 fps * 2 seconds = 20 frames
        assert isinstance(frames[0], AnimationFrame)
        assert frames[0].frame_number == 0
        assert frames[0].timestamp == 0.0
        assert frames[-1].frame_number == 19
        assert frames[-1].timestamp == 1.9  # Last frame at 1.9 seconds

        # Check car position progression
        first_position = frames[0].car_position
        last_position = frames[-1].car_position
        assert not np.array_equal(first_position, last_position)

    def test_create_animation_frames_realistic_speed(self, sample_tunnel_geometry):
        """Test animation frames with realistic car speed calculation."""
        service = AnimationService(config={'car_speed': 10.0, 'fps': 30})

        # Mock tunnel length calculation
        with patch.object(sample_tunnel_geometry, 'get_length', return_value=100.0):  # 100m tunnel
            frames = service.create_animation_frames(
                tunnel_path=sample_tunnel_geometry,
                duration=None  # Auto-calculate based on speed
            )

            # Should take 10 seconds to travel 100m at 10 m/s
            expected_duration = 100.0 / 10.0  # distance / speed
            expected_frames = int(expected_duration * 30)  # fps * duration

            assert len(frames) == expected_frames
            assert frames[-1].timestamp == expected_duration - (1/30)  # Last frame timestamp

    def test_camera_following_car(self, sample_tunnel_path, sample_terrain_mesh):
        """Test camera following car motion through tunnel."""
        service = AnimationService(config={'camera_follow': True})

        frames = service.create_animation_frames(
            tunnel_path=sample_tunnel_path,
            duration=1.0
        )

        # Check that camera positions follow car
        for frame in frames:
            car_pos = frame.car_position
            camera_pos = frame.camera_position

            # Camera should be offset from car position
            assert not np.array_equal(car_pos[:2], camera_pos[:2])

            # Camera height should be above car
            assert camera_pos[2] > car_pos[2]

    def test_fixed_camera_position(self, sample_tunnel_path):
        """Test animation with fixed camera position."""
        service = AnimationService(config={'camera_follow': False})

        frames = service.create_animation_frames(
            tunnel_path=sample_tunnel_path,
            duration=1.0
        )

        # Camera should remain fixed
        first_camera_pos = frames[0].camera_position
        for frame in frames[1:]:
            assert np.array_equal(frame.camera_position, first_camera_pos)

    def test_create_animation_figure(self, sample_tunnel_geometry, sample_terrain_mesh):
        """Test creating animated plotly figure."""
        service = AnimationService()

        with patch.object(sample_tunnel_geometry, 'get_mesh_vertices', return_value=np.array([[1.5, 0.75, 1]])), \
             patch.object(sample_tunnel_geometry, 'get_mesh_triangles', return_value=[]):

            animation_fig = service.create_animation_figure(
                terrain_mesh=sample_terrain_mesh,
                tunnel_geometry=sample_tunnel_geometry,
                duration=2.0
            )

            assert isinstance(animation_fig, go.Figure)
            assert hasattr(animation_fig, 'frames')  # Plotly animation frames
            assert len(animation_fig.frames) > 0

    def test_car_position_interpolation(self, sample_tunnel_path):
        """Test smooth interpolation of car position along tunnel."""
        service = AnimationService(config={'fps': 60})

        frames = service.create_animation_frames(
            tunnel_path=sample_tunnel_path,
            duration=1.0
        )

        # Check position continuity
        for i in range(1, len(frames)):
            prev_pos = frames[i-1].car_position
            curr_pos = frames[i].car_position

            # Position should change smoothly (not jump too far)
            distance = np.linalg.norm(curr_pos - prev_pos)
            assert distance < 1.0  # Should not jump more than 1 unit per frame

    def test_tunnel_center_calculation(self, sample_tunnel_geometry, sample_terrain_mesh):
        """Test accurate calculation of tunnel center for car positioning."""
        service = AnimationService()

        # Mock tunnel path as center line
        mock_path_points = np.array([
            [0.0, 0.0, 1.0],
            [1.0, 0.5, 1.2],
            [2.0, 1.0, 1.5],
            [3.0, 1.5, 1.8]
        ])

        with patch.object(sample_tunnel_geometry, 'get_path_points', return_value=mock_path_points):
            frames = service.create_animation_frames(
                tunnel_path=sample_tunnel_geometry,
                duration=1.0
            )

            # First frame should start at first path point
            assert np.allclose(frames[0].car_position, mock_path_points[0])
            # Last frame should end at last path point
            assert np.allclose(frames[-1].car_position, mock_path_points[-1])

    def test_car_orientation_calculation(self, sample_tunnel_path):
        """Test calculation of car orientation (direction) along tunnel."""
        service = AnimationService(config={'fps': 10})

        frames = service.create_animation_frames(
            tunnel_path=sample_tunnel_path,
            duration=1.0
        )

        # Check that car orientation points along path direction
        for i in range(1, len(frames)):
            prev_pos = frames[i-1].car_position
            curr_pos = frames[i].car_position

            # Direction vector
            direction = curr_pos - prev_pos
            if np.linalg.norm(direction) > 0.01:  # Only check if moving
                direction_normalized = direction / np.linalg.norm(direction)

                # Car should face forward (positive y direction in local coordinates)
                # This is a simplified check - real implementation would be more complex
                assert direction_normalized[1] >= 0 or direction_normalized[0] >= 0

    def test_animation_speed_control(self, sample_tunnel_path):
        """Test animation speed control and playback options."""
        service = AnimationService()

        # Test different speeds
        slow_frames = service.create_animation_frames(
            tunnel_path=sample_tunnel_path,
            duration=2.0,
            speed_multiplier=0.5  # Half speed
        )

        fast_frames = service.create_animation_frames(
            tunnel_path=sample_tunnel_path,
            duration=2.0,
            speed_multiplier=2.0  # Double speed
        )

        # Should have same number of frames but different speeds
        assert len(slow_frames) == len(fast_frames)

        # Speed should be reflected in frame timestamps
        assert slow_frames[-1].timestamp < fast_frames[-1].timestamp

    def test_animation_export_functionality(self, sample_tunnel_geometry, sample_terrain_mesh):
        """Test exporting animation to various formats."""
        service = AnimationService()

        with patch.object(sample_tunnel_geometry, 'get_mesh_vertices', return_value=np.array([[1.5, 0.75, 1]])), \
             patch.object(sample_tunnel_geometry, 'get_mesh_triangles', return_value=[]):

            animation_fig = service.create_animation_figure(
                terrain_mesh=sample_terrain_mesh,
                tunnel_geometry=sample_tunnel_geometry,
                duration=1.0
            )

            # Test HTML export
            html_output = service.export_animation_html(animation_fig, filename='test_animation.html')
            assert isinstance(html_output, str)
            assert '<!DOCTYPE html>' in html_output

            # Test GIF export (mocked)
            with patch('plotly.graph_objects.Figure.write_image') as mock_write:
                service.export_animation_gif(animation_fig, filename='test_animation.gif')
                mock_write.assert_called_once()

    def test_error_handling_invalid_inputs(self):
        """Test error handling for invalid animation inputs."""
        service = AnimationService()

        # Test with None tunnel path
        with pytest.raises(AnimationError, match="Tunnel path cannot be None"):
            service.create_animation_frames(None, duration=1.0)

        # Test with empty tunnel path
        empty_path = MagicMock()
        empty_path.waypoints = []
        empty_path.get_total_length.return_value = 0.0

        with pytest.raises(AnimationError, match="Tunnel path cannot be empty"):
            service.create_animation_frames(empty_path, duration=1.0)

        # Test with invalid duration
        with pytest.raises(AnimationError, match="Duration must be positive"):
            service.create_animation_frames(sample_tunnel_path, duration=-1.0)

    def test_performance_large_tunnel(self):
        """Test animation performance with large tunnel paths."""
        # Create a long tunnel path (100 waypoints)
        waypoints = [np.array([i * 0.1, i * 0.05, 1.0 + 0.01 * i]) for i in range(100)]

        long_path = TunnelPath(
            waypoints=waypoints,
            interpolated_points=None,
            total_length=None
        )

        service = AnimationService(config={'fps': 30})

        # Should complete within reasonable time
        import time
        start_time = time.time()

        frames = service.create_animation_frames(
            tunnel_path=long_path,
            duration=5.0
        )

        elapsed_time = time.time() - start_time
        assert elapsed_time < 2.0  # Should complete within 2 seconds
        assert len(frames) == 150  # 30 fps * 5 seconds

    def test_animation_frame_class(self):
        """Test AnimationFrame data class functionality."""
        frame = AnimationFrame(
            frame_number=10,
            timestamp=1.5,
            car_position=np.array([1.0, 2.0, 1.0]),
            camera_position=np.array([3.0, 4.0, 5.0]),
            car_orientation=np.array([0.0, 1.0, 0.0])
        )

        assert frame.frame_number == 10
        assert frame.timestamp == 1.5
        assert np.array_equal(frame.car_position, np.array([1.0, 2.0, 1.0]))
        assert np.array_equal(frame.camera_position, np.array([3.0, 4.0, 5.0]))
        assert np.array_equal(frame.car_orientation, np.array([0.0, 1.0, 0.0]))

    def test_camera_view_angles(self, sample_tunnel_path):
        """Test different camera viewing angles and distances."""
        # Test close camera
        close_service = AnimationService(config={'camera_distance': 2.0})
        close_frames = close_service.create_animation_frames(
            tunnel_path=sample_tunnel_path,
            duration=1.0
        )

        # Test far camera
        far_service = AnimationService(config={'camera_distance': 10.0})
        far_frames = far_service.create_animation_frames(
            tunnel_path=sample_tunnel_path,
            duration=1.0
        )

        # Camera distances should be different
        close_distance = np.linalg.norm(close_frames[0].camera_position - close_frames[0].car_position)
        far_distance = np.linalg.norm(far_frames[0].camera_position - far_frames[0].car_position)

        assert far_distance > close_distance

    def test_animation_looping(self, sample_tunnel_path):
        """Test animation looping functionality."""
        service = AnimationService()

        frames = service.create_animation_frames(
            tunnel_path=sample_tunnel_path,
            duration=1.0
        )

        # Create looping frames
        looped_frames = service.create_looping_animation(frames, loop_count=2)

        # Should have twice as many frames
        assert len(looped_frames) == len(frames) * 2

        # First loop should match original
        assert np.array_equal(looped_frames[0].car_position, frames[0].car_position)
        assert np.array_equal(looped_frames[-1].car_position, frames[-1].car_position)

    def test_smooth_camera_transitions(self, sample_tunnel_path):
        """Test smooth camera transitions during animation."""
        service = AnimationService(config={'camera_follow': True, 'fps': 30})

        frames = service.create_animation_frames(
            tunnel_path=sample_tunnel_path,
            duration=1.0
        )

        # Check camera movement smoothness
        for i in range(1, len(frames)):
            prev_camera = frames[i-1].camera_position
            curr_camera = frames[i].camera_position

            # Camera should not jump too far
            camera_movement = np.linalg.norm(curr_camera - prev_camera)
            assert camera_movement < 0.5  # Maximum movement per frame