"""
Animation service for Terrain Tunneling Calculator.

This service handles car movement animation through tunnels,
camera following, and interactive playback controls for User Story 4.
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Optional, Dict, Any, Union, Tuple
from pathlib import Path
import time

from dataclasses import dataclass, field
from models.tunnel_geometry import TunnelGeometry, TunnelPath
from models.terrain_mesh import TerrainMesh
from utils.exceptions import AnimationError


@dataclass
class AnimationFrame:
    """Represents a single frame of animation data."""
    frame_number: int
    timestamp: float  # Seconds from start
    car_position: np.ndarray  # 3D position [x, y, z]
    camera_position: np.ndarray  # 3D camera position [x, y, z]
    car_orientation: np.ndarray  # Car direction vector [dx, dy, dz]
    tunnel_progress: float = 0.0  # Progress along tunnel (0.0 to 1.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'frame_number': self.frame_number,
            'timestamp': self.timestamp,
            'car_position': self.car_position.tolist(),
            'camera_position': self.camera_position.tolist(),
            'car_orientation': self.car_orientation.tolist(),
            'tunnel_progress': self.tunnel_progress
        }


class AnimationService:
    """Service for creating and managing tunnel traversal animations."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the animation service.

        Args:
            config: Optional animation configuration dictionary
        """
        # Default animation configuration
        self.config = {
            'fps': 30,  # Frames per second
            'car_speed': 10.0,  # m/s - realistic driving speed
            'camera_follow': True,  # Camera follows car movement
            'camera_distance': 5.0,  # Distance behind car
            'camera_height': 2.0,  # Height above car
            'camera_side_offset': 0.0,  # Side offset for camera
            'car_size': 0.3,  # Car visualization size
            'car_color': '#FF0000',  # Red car
            'smooth_transitions': True,  # Smooth camera transitions
            'loop_count': 1,  # Number of animation loops
            'export_format': 'html'  # Default export format
        }

        # Update with provided config
        if config:
            self.config.update(config)

        # Validate configuration
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate animation configuration parameters."""
        if self.config['fps'] <= 0:
            raise AnimationError("FPS must be positive")
        if self.config['car_speed'] <= 0:
            raise AnimationError("Car speed must be positive")
        if self.config['camera_distance'] <= 0:
            raise AnimationError("Camera distance must be positive")
        if self.config['car_size'] <= 0:
            raise AnimationError("Car size must be positive")

    def create_animation_frames(self,
                                tunnel_path: Union[TunnelGeometry, TunnelPath],
                                duration: Optional[float] = None,
                                speed_multiplier: float = 1.0) -> List[AnimationFrame]:
        """
        Create animation frames for car movement through tunnel.

        Args:
            tunnel_path: Tunnel geometry or path object
            duration: Animation duration in seconds (auto-calculated if None)
            speed_multiplier: Speed multiplier for faster/slower animation

        Returns:
            List of AnimationFrame objects

        Raises:
            AnimationError: If input parameters are invalid
        """
        if tunnel_path is None:
            raise AnimationError("Tunnel path cannot be None")

        # Get path points
        if isinstance(tunnel_path, TunnelGeometry):
            # For TunnelGeometry, extract path from waypoints
            if len(tunnel_path.path.waypoints) < 2:
                raise AnimationError("Tunnel must have at least 2 waypoints for animation")

            # Extract waypoint coordinates
            waypoint_coords = []
            for wp in tunnel_path.path.waypoints:
                waypoint_coords.append([wp.x, wp.y, wp.elevation])

            waypoint_coords = np.array(waypoint_coords)

            # Create interpolated path points
            num_points = max(50, len(waypoint_coords) * 5)  # Ensure smooth animation
            path_points = []

            for i in range(num_points):
                t = i / (num_points - 1)  # Normalized position along path (0 to 1)

                # Find segment for interpolation
                segment_count = len(waypoint_coords) - 1
                segment_idx = min(int(t * segment_count), segment_count - 1)
                segment_t = (t * segment_count) - segment_idx

                # Linear interpolation between waypoints
                start_point = waypoint_coords[segment_idx]
                end_point = waypoint_coords[segment_idx + 1]

                interpolated_point = start_point + (end_point - start_point) * segment_t
                path_points.append(interpolated_point)

            path_points = np.array(path_points)

            # Calculate total tunnel length
            tunnel_length = 0.0
            for i in range(1, len(waypoint_coords)):
                segment_length = np.linalg.norm(waypoint_coords[i] - waypoint_coords[i-1])
                tunnel_length += segment_length

        else:
            path_points = tunnel_path.interpolated_points
            tunnel_length = tunnel_path.total_length

        if len(path_points) == 0:
            raise AnimationError("Tunnel path cannot be empty")

        # Calculate animation duration
        if duration is None:
            # Calculate based on car speed and tunnel length
            effective_speed = self.config['car_speed'] * speed_multiplier
            duration = tunnel_length / effective_speed

        if duration <= 0:
            raise AnimationError("Duration must be positive")

        # Calculate frame count
        fps = self.config['fps']
        total_frames = int(duration * fps)
        frame_interval = duration / total_frames

        # Generate frames
        frames = []
        for frame_num in range(total_frames):
            timestamp = frame_num * frame_interval
            progress = timestamp / duration  # 0.0 to 1.0

            # Calculate car position along path
            car_position = self._interpolate_position(path_points, progress)

            # Calculate car orientation (tangent to path)
            car_orientation = self._calculate_orientation(path_points, progress)

            # Calculate camera position
            if self.config['camera_follow']:
                camera_position = self._calculate_camera_position(
                    car_position, car_orientation
                )
            else:
                # Fixed camera position
                camera_position = self._get_fixed_camera_position(path_points)

            frame = AnimationFrame(
                frame_number=frame_num,
                timestamp=timestamp,
                car_position=car_position,
                camera_position=camera_position,
                car_orientation=car_orientation,
                tunnel_progress=progress
            )
            frames.append(frame)

        return frames

    def _interpolate_position(self, path_points: np.ndarray, progress: float) -> np.ndarray:
        """
        Interpolate car position along tunnel path.

        Args:
            path_points: Array of 3D path points
            progress: Progress along path (0.0 to 1.0)

        Returns:
            Interpolated 3D position
        """
        if progress <= 0.0:
            return path_points[0]
        if progress >= 1.0:
            return path_points[-1]

        # Find appropriate segment for interpolation
        total_points = len(path_points)
        segment_index = int(progress * (total_points - 1))

        if segment_index >= total_points - 1:
            return path_points[-1]

        # Local progress within segment
        segment_progress = (progress * (total_points - 1)) - segment_index

        # Linear interpolation between two points
        start_point = path_points[segment_index]
        end_point = path_points[segment_index + 1]

        interpolated = start_point + (end_point - start_point) * segment_progress

        return interpolated

    def _calculate_orientation(self, path_points: np.ndarray, progress: float) -> np.ndarray:
        """
        Calculate car orientation (direction vector) at given progress.

        Args:
            path_points: Array of 3D path points
            progress: Progress along path (0.0 to 1.0)

        Returns:
            Normalized orientation vector
        """
        # Look ahead slightly for better orientation calculation
        look_ahead = min(0.05, 1.0 / len(path_points))

        current_pos = self._interpolate_position(path_points, progress)
        future_pos = self._interpolate_position(path_points, min(1.0, progress + look_ahead))

        direction = future_pos - current_pos

        # Normalize direction vector
        norm = np.linalg.norm(direction)
        if norm > 0:
            direction = direction / norm
        else:
            # Default orientation if direction is zero
            direction = np.array([0, 1, 0])

        return direction

    def _calculate_camera_position(self,
                                  car_position: np.ndarray,
                                  car_orientation: np.ndarray) -> np.ndarray:
        """
        Calculate camera position that follows the car.

        Args:
            car_position: Current 3D car position
            car_orientation: Car orientation vector

        Returns:
            3D camera position
        """
        # Camera position is behind the car
        behind_vector = -car_orientation

        # Add side offset if configured
        if self.config['camera_side_offset'] != 0:
            # Calculate perpendicular vector
            if abs(behind_vector[0]) > abs(behind_vector[1]):
                side_vector = np.array([0, 1, 0])
            else:
                side_vector = np.array([1, 0, 0])

            behind_vector = behind_vector + side_vector * self.config['camera_side_offset']
            behind_vector = behind_vector / np.linalg.norm(behind_vector)

        camera_pos = car_position + behind_vector * self.config['camera_distance']
        camera_pos[2] += self.config['camera_height']  # Add height offset

        return camera_pos

    def _get_fixed_camera_position(self, path_points: np.ndarray) -> np.ndarray:
        """
        Get fixed camera position for non-following mode.

        Args:
            path_points: Array of 3D path points

        Returns:
            Fixed 3D camera position
        """
        # Calculate center of path
        center = np.mean(path_points, axis=0)

        # Position camera to view entire path
        max_extent = np.max(np.abs(path_points - center))

        camera_pos = center.copy()
        camera_pos[0] += max_extent * 2  # Offset on X axis
        camera_pos[1] += max_extent * 2  # Offset on Y axis
        camera_pos[2] += max_extent * 1.5  # Height offset

        return camera_pos

    def create_animation_figure(self,
                               terrain_mesh: TerrainMesh,
                               tunnel_geometry: TunnelGeometry,
                               duration: Optional[float] = None) -> go.Figure:
        """
        Create animated plotly figure with car movement.

        Args:
            terrain_mesh: Terrain mesh object
            tunnel_geometry: Tunnel geometry object
            duration: Animation duration in seconds

        Returns:
            Animated plotly Figure object

        Raises:
            AnimationError: If figure creation fails
        """
        try:
            # Create animation frames
            frames = self.create_animation_frames(
                tunnel_geometry,
                duration=duration
            )

            # Create base figure with terrain and tunnel
            base_figure = self._create_base_figure(terrain_mesh, tunnel_geometry)

            # Create animation frames
            animation_frames = []
            for frame in frames:
                # Start with base figure data (terrain and tunnel)
                frame_traces = list(base_figure.data)

                # Add frame-specific traces (car and indicators)
                additional_traces = self._create_frame_traces(frame, terrain_mesh, tunnel_geometry)
                frame_traces.extend(additional_traces)

                animation_frames.append(go.Frame(
                    data=frame_traces,
                    name=f"Frame {frame.frame_number}"
                ))

            # Create animated figure
            animated_figure = go.Figure(
                data=base_figure.data,
                layout=base_figure.layout,
                frames=animation_frames
            )

            # Add animation controls
            animated_figure.layout.updatemenus = [
                dict(
                    type="buttons",
                    direction="left",
                    pad={"r": 10, "t": 87},
                    showactive=False,
                    x=0.011,
                    xanchor="right",
                    y=0,
                    yanchor="top",
                    buttons=[
                        dict(
                            label="Play",
                            method="animate",
                            args=[None, {"frame": {"duration": 1000/self.config['fps']}, "fromcurrent": True}]
                        ),
                        dict(
                            label="Pause",
                            method="animate",
                            args=[[None], {"frame": {"duration": 0}, "mode": "immediate", "transition": {"duration": 0}}]
                        )
                    ]
                )
            ]

            # Add slider for manual frame control
            animated_figure.layout.sliders = [
                dict(
                    active=0,
                    yanchor="top",
                    xanchor="left",
                    currentvalue=dict(
                        prefix="Frame: ",
                        visible=True,
                        xanchor="right",
                        font=dict(size=14)
                    ),
                    transition=dict(duration=300, easing="cubic-in-out"),
                    pad=dict(t=50, b=10),
                    len=0.9,
                    x=0.1,
                    y=0,
                    steps=[
                        dict(
                            args=[[f"Frame {i}"], [i]],
                            label=str(i),
                            method="animate"
                        )
                        for i in range(len(frames))
                    ]
                )
            ]

            return animated_figure

        except Exception as e:
            raise AnimationError(f"Failed to create animation figure: {e}")

    def _create_base_figure(self,
                           terrain_mesh: TerrainMesh,
                           tunnel_geometry: TunnelGeometry) -> go.Figure:
        """Create base figure with terrain and tunnel (without animation)."""
        from services.visualization_3d import Visualization3DService

        viz_service = Visualization3DService()

        # Create terrain visualization
        terrain_fig = viz_service.create_terrain_plot(terrain_mesh)

        # Add tunnel to the figure using the integrated scene method
        try:
            # Use create_integrated_scene to get both terrain and tunnel
            integrated_fig = viz_service.create_integrated_scene(
                terrain_mesh=terrain_mesh,
                tunnel_geometry=tunnel_geometry,
                title="3D Tunnel Animation"
            )

            # Set better viewing angle for animation
            integrated_fig.update_layout(
                scene=dict(
                    camera=dict(
                        eye=dict(x=1.5, y=1.5, z=0.5)
                    ),
                    aspectmode='data'
                )
            )

            return integrated_fig

        except Exception as e:
            # If integrated scene creation fails, use terrain only
            print(f"Warning: Could not create integrated scene for animation: {e}")

            # Set better viewing angle for animation
            terrain_fig.update_layout(
                scene=dict(
                    camera=dict(
                        eye=dict(x=1.5, y=1.5, z=0.5)
                    ),
                    aspectmode='data'
                ),
                title="3D Tunnel Animation (Terrain Only)"
            )

            return terrain_fig

    def _create_frame_traces(self,
                             frame: AnimationFrame,
                             terrain_mesh: TerrainMesh,
                             tunnel_geometry: TunnelGeometry) -> List[Union[go.Scatter3d, go.Mesh3d]]:
        """
        Create traces for a specific animation frame with realistic car modeling.

        Args:
            frame: Animation frame data
            terrain_mesh: Terrain mesh
            tunnel_geometry: Tunnel geometry

        Returns:
            List of plotly traces for the frame
        """
        traces = []

        # Realistic car dimensions (scaled for tunnel visibility)
        car_length = 0.4    # Length of car body
        car_width = 0.18    # Width of car body
        car_height = 0.12   # Height of car body
        wheel_radius = 0.03 # Wheel radius
        wheel_width = 0.02  # Wheel width

        # Calculate car orientation matrix
        forward = frame.car_orientation
        up = np.array([0, 0, 1])  # Z-axis is up
        right = np.cross(forward, up)
        if np.linalg.norm(right) > 0:
            right = right / np.linalg.norm(right)
        else:
            right = np.array([1, 0, 0])
        up = np.cross(right, forward)

        # Create realistic car body using Mesh3D
        car_body_traces = self._create_car_body_mesh(
            frame.car_position, forward, right, up,
            car_length, car_width, car_height
        )
        traces.extend(car_body_traces)

        # Create wheels
        wheel_traces = self._create_car_wheels(
            frame.car_position, forward, right, up,
            car_length, car_width, wheel_radius, wheel_width
        )
        traces.extend(wheel_traces)

        # Create windows (transparent)
        window_traces = self._create_car_windows(
            frame.car_position, forward, right, up,
            car_length, car_width, car_height
        )
        traces.extend(window_traces)

        # Add headlights
        headlight_traces = self._create_car_headlights(
            frame.car_position, forward, right, up,
            car_length, car_width, car_height
        )
        traces.extend(headlight_traces)

        # Add car path trail (show where car has been)
        trail_length = min(15, frame.frame_number)  # Show last 15 positions
        if trail_length > 1:
            trail_positions = []
            for i in range(max(0, frame.frame_number - trail_length), frame.frame_number + 1):
                # Calculate position for this frame (simplified)
                trail_progress = i / max(1, frame.frame_number) if frame.frame_number > 0 else 0
                trail_pos = frame.car_position * (1 - trail_progress * 0.3)  # Fade trail
                trail_positions.append(trail_pos)

            if len(trail_positions) > 1:
                trail_positions = np.array(trail_positions)
                trail_trace = go.Scatter3d(
                    x=trail_positions[:, 0],
                    y=trail_positions[:, 1],
                    z=trail_positions[:, 2],
                    mode='lines',
                    line=dict(color='cyan', width=3, dash='dot'),
                    name='Trail',
                    showlegend=False
                )
                traces.append(trail_trace)

        return traces

    def _create_car_body_mesh(self, position, forward, right, up, length, width, height):
        """Create realistic car body using multiple Mesh3D objects."""
        traces = []

        # Main car body (lower part)
        body_height = height * 0.6  # Lower body is 60% of total height

        # Define car body vertices (rectangular prism)
        half_length = length / 2
        half_width = width / 2

        # Lower body vertices
        lower_vertices = np.array([
            position + forward * half_length + right * half_width,           # Front right bottom
            position + forward * half_length - right * half_width,           # Front left bottom
            position - forward * half_length - right * half_width,           # Rear left bottom
            position - forward * half_length + right * half_width,           # Rear right bottom
            position + forward * half_length + right * half_width + up * body_height,  # Front right top
            position + forward * half_length - right * half_width + up * body_height,  # Front left top
            position - forward * half_length - right * half_width + up * body_height,  # Rear left top
            position - forward * half_length + right * half_width + up * body_height,  # Rear right top
        ])

        # Define faces for the lower body
        lower_faces = np.array([
            [0, 1, 2], [0, 2, 3],  # Bottom
            [4, 5, 1], [4, 1, 0],  # Front
            [7, 6, 2], [7, 2, 3],  # Back
            [4, 7, 3], [4, 3, 0],  # Right side
            [5, 6, 2], [5, 2, 1],  # Left side
        ])

        lower_body = go.Mesh3d(
            x=lower_vertices[:, 0],
            y=lower_vertices[:, 1],
            z=lower_vertices[:, 2],
            i=lower_faces[:, 0],
            j=lower_faces[:, 1],
            k=lower_faces[:, 2],
            color='red',
            name='Car Body',
            opacity=0.9,
            flatshading=True,
            lighting=dict(ambient=0.4, diffuse=0.8, specular=0.5, roughness=0.3),
            showlegend=True
        )
        traces.append(lower_body)

        # Upper cabin (smaller, higher)
        cabin_length = length * 0.5
        cabin_width = width * 0.85
        cabin_height = height * 0.4  # Upper cabin is 40% of total height
        cabin_base_z = body_height  # Start on top of lower body

        cabin_half_length = cabin_length / 2
        cabin_half_width = cabin_width / 2
        cabin_offset = forward * (length * 0.1)  # Move cabin slightly forward

        # Upper cabin vertices
        upper_vertices = np.array([
            position + cabin_offset + forward * cabin_half_length + right * cabin_half_width + up * cabin_base_z,
            position + cabin_offset + forward * cabin_half_length - right * cabin_half_width + up * cabin_base_z,
            position + cabin_offset - forward * cabin_half_length - right * cabin_half_width + up * cabin_base_z,
            position + cabin_offset - forward * cabin_half_length + right * cabin_half_width + up * cabin_base_z,
            position + cabin_offset + forward * cabin_half_length + right * cabin_half_width + up * (cabin_base_z + cabin_height),
            position + cabin_offset + forward * cabin_half_length - right * cabin_half_width + up * (cabin_base_z + cabin_height),
            position + cabin_offset - forward * cabin_half_length - right * cabin_half_width + up * (cabin_base_z + cabin_height),
            position + cabin_offset - forward * cabin_half_length + right * cabin_half_width + up * (cabin_base_z + cabin_height),
        ])

        # Define faces for the upper cabin
        upper_faces = np.array([
            [0, 1, 2], [0, 2, 3],  # Bottom (connects to lower body)
            [4, 5, 1], [4, 1, 0],  # Front
            [7, 6, 2], [7, 2, 3],  # Back
            [4, 7, 3], [4, 3, 0],  # Right side
            [5, 6, 2], [5, 2, 1],  # Left side
        ])

        upper_body = go.Mesh3d(
            x=upper_vertices[:, 0],
            y=upper_vertices[:, 1],
            z=upper_vertices[:, 2],
            i=upper_faces[:, 0],
            j=upper_faces[:, 1],
            k=upper_faces[:, 2],
            color='darkred',
            name='Car Cabin',
            opacity=0.8,
            flatshading=True,
            lighting=dict(ambient=0.4, diffuse=0.8, specular=0.5, roughness=0.3),
            showlegend=False
        )
        traces.append(upper_body)

        return traces

    def _create_car_wheels(self, position, forward, right, up, length, width, wheel_radius, wheel_width):
        """Create realistic wheels for the car."""
        traces = []

        # Wheel positions (4 wheels)
        wheel_positions = [
            position + forward * (length * 0.3) + right * (width * 0.6),   # Front right
            position + forward * (length * 0.3) - right * (width * 0.6),   # Front left
            position - forward * (length * 0.3) + right * (width * 0.6),   # Rear right
            position - forward * (length * 0.3) - right * (width * 0.6),   # Rear left
        ]

        for i, wheel_pos in enumerate(wheel_positions):
            # Create wheel as a cylinder (approximated with multiple faces)
            theta = np.linspace(0, 2*np.pi, 8)
            wheel_x = []
            wheel_y = []
            wheel_z = []

            for t in theta:
                # Create circle in the plane perpendicular to forward direction
                local_x = wheel_radius * np.cos(t)
                local_y = wheel_radius * np.sin(t)

                # Transform to world coordinates
                world_point = wheel_pos + right * local_x + up * local_y
                wheel_x.append(world_point[0])
                wheel_y.append(world_point[1])
                wheel_z.append(world_point[2])

            # Create front and back faces of wheel
            front_face = [wheel_pos[0] + forward[0] * wheel_width/2,
                         wheel_pos[1] + forward[1] * wheel_width/2,
                         wheel_pos[2] + forward[2] * wheel_width/2]

            back_face = [wheel_pos[0] - forward[0] * wheel_width/2,
                        wheel_pos[1] - forward[1] * wheel_width/2,
                        wheel_pos[2] - forward[2] * wheel_width/2]

            # Combine all wheel vertices
            all_x = wheel_x + [front_face[0], back_face[0]]
            all_y = wheel_y + [front_face[1], back_face[1]]
            all_z = wheel_z + [front_face[2], back_face[2]]

            wheel = go.Scatter3d(
                x=all_x,
                y=all_y,
                z=all_z,
                mode='markers',
                marker=dict(
                    size=4,
                    color='black',
                    opacity=1.0
                ),
                name=f'Wheel {i+1}',
                showlegend=False
            )
            traces.append(wheel)

        return traces

    def _create_car_windows(self, position, forward, right, up, length, width, height):
        """Create transparent windows for the car."""
        traces = []

        # Window positions (front and rear windshields)
        cabin_length = length * 0.5
        cabin_width = width * 0.8
        cabin_height = height * 0.3
        cabin_base_z = height * 0.6

        # Front windshield
        front_center = position + forward * (length * 0.25) + up * (cabin_base_z + cabin_height/2)
        front_vertices = np.array([
            front_center + forward * 0.02 + right * (cabin_width/2),
            front_center + forward * 0.02 - right * (cabin_width/2),
            front_center + forward * 0.02 - right * (cabin_width/2) + up * cabin_height,
            front_center + forward * 0.02 + right * (cabin_width/2) + up * cabin_height,
        ])

        front_windshield = go.Mesh3d(
            x=front_vertices[:, 0],
            y=front_vertices[:, 1],
            z=front_vertices[:, 2],
            i=np.array([0, 0]),
            j=np.array([1, 2]),
            k=np.array([2, 3]),
            color='lightblue',
            name='Front Window',
            opacity=0.3,
            flatshading=True,
            showlegend=False
        )
        traces.append(front_windshield)

        # Rear windshield
        rear_center = position - forward * (length * 0.15) + up * (cabin_base_z + cabin_height/2)
        rear_vertices = np.array([
            rear_center - forward * 0.02 + right * (cabin_width/2),
            rear_center - forward * 0.02 - right * (cabin_width/2),
            rear_center - forward * 0.02 - right * (cabin_width/2) + up * cabin_height,
            rear_center - forward * 0.02 + right * (cabin_width/2) + up * cabin_height,
        ])

        rear_windshield = go.Mesh3d(
            x=rear_vertices[:, 0],
            y=rear_vertices[:, 1],
            z=rear_vertices[:, 2],
            i=np.array([0, 0]),
            j=np.array([1, 2]),
            k=np.array([2, 3]),
            color='lightblue',
            name='Rear Window',
            opacity=0.3,
            flatshading=True,
            showlegend=False
        )
        traces.append(rear_windshield)

        return traces

    def _create_car_headlights(self, position, forward, right, up, length, width, height):
        """Create headlights for the car."""
        traces = []

        # Headlight positions (front of car)
        headlight_y_offset = width * 0.3
        headlight_z_offset = height * 0.3

        headlight_positions = [
            position + forward * (length * 0.48) + right * headlight_y_offset + up * headlight_z_offset,  # Right headlight
            position + forward * (length * 0.48) - right * headlight_y_offset + up * headlight_z_offset,  # Left headlight
        ]

        for i, headlight_pos in enumerate(headlight_positions):
            headlight = go.Scatter3d(
                x=[headlight_pos[0]],
                y=[headlight_pos[1]],
                z=[headlight_pos[2]],
                mode='markers',
                marker=dict(
                    size=6,
                    color='yellow',
                    opacity=1.0,
                    symbol='circle'
                ),
                name=f'Headlight {i+1}',
                showlegend=False
            )
            traces.append(headlight)

        return traces

    def create_looping_animation(self,
                                 frames: List[AnimationFrame],
                                 loop_count: int = 2) -> List[AnimationFrame]:
        """
        Create looping animation by repeating frames.

        Args:
            frames: Original animation frames
            loop_count: Number of times to repeat

        Returns:
            Extended list of frames with looping
        """
        if loop_count <= 1:
            return frames

        looped_frames = []
        for loop in range(loop_count):
            loop_offset = len(frames) * loop

            for frame in frames:
                looped_frame = AnimationFrame(
                    frame_number=frame.frame_number + loop_offset,
                    timestamp=frame.timestamp + (loop * frames[-1].timestamp),
                    car_position=frame.car_position.copy(),
                    camera_position=frame.camera_position.copy(),
                    car_orientation=frame.car_orientation.copy(),
                    tunnel_progress=frame.tunnel_progress
                )
                looped_frames.append(looped_frame)

        return looped_frames

    def export_animation_html(self,
                             figure: go.Figure,
                             filename: str = "animation.html",
                             include_plotlyjs: bool = True) -> str:
        """
        Export animation to HTML format.

        Args:
            figure: Animated plotly figure
            filename: Output filename
            include_plotlyjs: Whether to include plotly.js library

        Returns:
            HTML string content
        """
        html_content = figure.to_html(
            include_plotlyjs=include_plotlyjs,
            div_id="animation-container"
        )

        # Save to file if filename provided
        if filename:
            Path(filename).write_text(html_content, encoding='utf-8')

        return html_content

    def export_animation_gif(self,
                             figure: go.Figure,
                             filename: str = "animation.gif",
                             width: int = 800,
                             height: int = 600) -> None:
        """
        Export animation to GIF format.

        Args:
            figure: Animated plotly figure
            filename: Output filename
            width: Image width
            height: Image height

        Raises:
            AnimationError: If export fails (requires additional dependencies)
        """
        try:
            figure.write_image(
                filename,
                format="gif",
                width=width,
                height=height,
                engine="kaleido"  # Requires kaleido package
            )
        except Exception as e:
            raise AnimationError(f"Failed to export GIF: {e}. Install kaleido package for GIF export.")

    def get_animation_summary(self, frames: List[AnimationFrame]) -> Dict[str, Any]:
        """
        Get summary statistics for animation.

        Args:
            frames: List of animation frames

        Returns:
            Dictionary with animation statistics
        """
        if not frames:
            return {}

        total_duration = frames[-1].timestamp - frames[0].timestamp
        total_distance = 0

        for i in range(1, len(frames)):
            distance = np.linalg.norm(frames[i].car_position - frames[i-1].car_position)
            total_distance += distance

        avg_speed = total_distance / total_duration if total_duration > 0 else 0

        return {
            'total_frames': len(frames),
            'total_duration': total_duration,
            'frame_rate': len(frames) / total_duration if total_duration > 0 else 0,
            'total_distance': total_distance,
            'average_speed': avg_speed,
            'start_position': frames[0].car_position.tolist(),
            'end_position': frames[-1].car_position.tolist(),
            'config': self.config
        }

    def create_integrated_animation_html(self,
                                       terrain_mesh: TerrainMesh,
                                       tunnel_geometry: TunnelGeometry,
                                       duration: Optional[float] = None,
                                       filename: str = "tunnel_animation.html") -> str:
        """
        Create integrated HTML animation with all controls in one page.

        Args:
            terrain_mesh: Terrain mesh object
            tunnel_geometry: Tunnel geometry object
            duration: Animation duration in seconds
            filename: Output HTML filename

        Returns:
            Path to created HTML file

        Raises:
            AnimationError: If creation fails
        """
        try:
            import json

            if duration is None:
                duration = self.config['duration']

            # Create animation frames
            frames = self.create_animation_frames(tunnel_geometry, duration=duration)

            # Create base figure with terrain and tunnel
            base_figure = self._create_base_figure(terrain_mesh, tunnel_geometry)

            # Create animation frames data
            animation_frames = []
            for frame in frames:
                frame_traces = list(base_figure.data)
                additional_traces = self._create_frame_traces(frame, terrain_mesh, tunnel_geometry)
                frame_traces.extend(additional_traces)
                animation_frames.append(go.Frame(
                    data=frame_traces,
                    name=f"Frame {frame.frame_number}"
                ))

            # Create integrated HTML with custom controls
            html_content = self._generate_integrated_html(
                base_figure=base_figure,
                frames=animation_frames,
                duration=duration
            )

            # Write to file with UTF-8 encoding
            Path(filename).write_text(html_content, encoding='utf-8')

            return filename

        except Exception as e:
            raise AnimationError(f"Failed to create integrated animation HTML: {str(e)}")

    def _generate_integrated_html(self,
                                base_figure: go.Figure,
                                frames: List[go.Frame],
                                duration: float) -> str:
        """
        Generate integrated HTML with custom animation controls.

        Args:
            base_figure: Base plotly figure
            frames: Animation frames
            duration: Animation duration

        Returns:
            Complete HTML content as string
        """
        import json
        import numpy as np

        # Custom JSON encoder to handle numpy arrays
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                if isinstance(obj, np.integer):
                    return int(obj)
                if isinstance(obj, np.floating):
                    return float(obj)
                return super(NumpyEncoder, self).default(obj)

        # Convert figure and frames to JSON with custom encoder
        figure_json = base_figure.to_json()
        frames_json = json.dumps([frame.to_plotly_json() for frame in frames], cls=NumpyEncoder)

        # Calculate frame duration
        frame_duration = int(1000 * duration / len(frames))  # milliseconds

        # Generate HTML template
        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>隧道行车动画 - Tunnel Driving Animation</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            overflow: hidden;
        }}

        .container {{
            display: flex;
            height: 100vh;
            flex-direction: column;
        }}

        .header {{
            background: rgba(0, 0, 0, 0.3);
            padding: 15px 20px;
            text-align: center;
            backdrop-filter: blur(10px);
        }}

        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 300;
        }}

        .main-content {{
            display: flex;
            flex: 1;
            overflow: hidden;
        }}

        .plot-container {{
            flex: 1;
            position: relative;
            background: rgba(255, 255, 255, 0.1);
            margin: 10px;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }}

        .controls-panel {{
            width: 300px;
            background: rgba(0, 0, 0, 0.3);
            padding: 20px;
            overflow-y: auto;
            backdrop-filter: blur(10px);
        }}

        .control-group {{
            margin-bottom: 25px;
            padding: 15px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
        }}

        .control-group h3 {{
            margin: 0 0 15px 0;
            font-size: 16px;
            color: #fff;
            border-bottom: 1px solid rgba(255, 255, 255, 0.3);
            padding-bottom: 8px;
        }}

        .btn {{
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 5px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
            min-width: 80px;
        }}

        .btn:hover {{
            background: linear-gradient(45deg, #45a049, #4CAF50);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
        }}

        .btn:disabled {{
            background: #666;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }}

        .btn.play {{ background: linear-gradient(45deg, #2196F3, #1976D2); }}
        .btn.play:hover {{ background: linear-gradient(45deg, #1976D2, #2196F3); }}
        .btn.pause {{ background: linear-gradient(45deg, #FF9800, #F57C00); }}
        .btn.pause:hover {{ background: linear-gradient(45deg, #F57C00, #FF9800); }}
        .btn.stop {{ background: linear-gradient(45deg, #f44336, #d32f2f); }}
        .btn.stop:hover {{ background: linear-gradient(45deg, #d32f2f, #f44336); }}

        .slider-container {{
            margin: 15px 0;
        }}

        .slider {{
            width: 100%;
            height: 6px;
            border-radius: 3px;
            background: rgba(255, 255, 255, 0.3);
            outline: none;
            -webkit-appearance: none;
        }}

        .slider::-webkit-slider-thumb {{
            -webkit-appearance: none;
            appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #4CAF50;
            cursor: pointer;
        }}

        .slider::-moz-range-thumb {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #4CAF50;
            cursor: pointer;
        }}

        .info-panel {{
            background: rgba(255, 255, 255, 0.1);
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
            font-size: 14px;
        }}

        .progress-bar {{
            width: 100%;
            height: 8px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            width: 0%;
            transition: width 0.3s ease;
        }}

        @media (max-width: 768px) {{
            .main-content {{
                flex-direction: column;
            }}
            .controls-panel {{
                width: 100%;
                max-height: 40vh;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚗 隧道行车动画 | Tunnel Driving Animation</h1>
        </div>

        <div class="main-content">
            <div class="plot-container">
                <div id="plot" style="width: 100%; height: 100%;"></div>
            </div>

            <div class="controls-panel">
                <div class="control-group">
                    <h3>🎮 动画控制 | Animation Controls</h3>
                    <div style="text-align: center;">
                        <button id="playBtn" class="btn play">▶ Play</button>
                        <button id="pauseBtn" class="btn pause" disabled>⏸ Pause</button>
                        <button id="stopBtn" class="btn stop" disabled>⏹ Stop</button>
                    </div>
                </div>

                <div class="control-group">
                    <h3>📊 播放进度 | Progress</h3>
                    <div class="progress-bar">
                        <div id="progressFill" class="progress-fill"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 12px;">
                        <span>Frame: <span id="currentFrame">0</span></span>
                        <span>Total: <span id="totalFrames">{len(frames)}</span></span>
                    </div>
                    <div class="slider-container">
                        <input type="range" id="frameSlider" class="slider" min="0" max="{len(frames)-1}" value="0">
                    </div>
                </div>

                <div class="control-group">
                    <h3>⚡ 播放速度 | Speed</h3>
                    <div class="slider-container">
                        <input type="range" id="speedSlider" class="slider" min="0.1" max="3" step="0.1" value="1">
                        <div style="text-align: center; font-size: 14px;">
                            <span id="speedValue">1.0</span>x
                        </div>
                    </div>
                </div>

                <div class="control-group">
                    <h3>📹 视角控制 | Camera</h3>
                    <div style="text-align: center;">
                        <button class="btn" onclick="resetCamera()">🔄 Reset View</button>
                        <button class="btn" onclick="setTopView()">🔽 Top</button>
                        <button class="btn" onclick="setSideView()">➡️ Side</button>
                        <button class="btn" onclick="setIsometricView()">📐 Isometric</button>
                    </div>
                </div>

                <div class="control-group">
                    <h3>📋 信息 | Information</h3>
                    <div class="info-panel">
                        <div>🏔️ 地形点数: {base_figure.data[0].x if base_figure.data else 'N/A'}</div>
                        <div>🚇 隧道长度: ~100m</div>
                        <div>⏱️ 动画时长: {duration:.1f}s</div>
                        <div>🎬 帧数: {len(frames)}</div>
                        <div id="statusText" style="color: #4CAF50; font-weight: bold;">✅ Ready</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Global variables
        let figureData = {figure_json};
        let framesData = {frames_json};
        let currentFrameIndex = 0;
        let isPlaying = false;
        let animationInterval = null;
        let baseFrameDuration = {frame_duration};

        // Initialize plot
        function initPlot() {{
            Plotly.newPlot('plot', figureData.data, figureData.layout, {{
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['pan3d', 'select3d', 'lasso3d'],
                displaylogo: false,
                scrollZoom: true
            }});

            // Update initial frame
            updateFrame(0);
        }}

        // Update frame
        function updateFrame(frameIndex) {{
            if (frameIndex < 0 || frameIndex >= framesData.length) return;

            currentFrameIndex = frameIndex;
            const frame = framesData[frameIndex];

            Plotly.react('plot', frame.data, figureData.layout, {{
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['pan3d', 'select3d', 'lasso3d'],
                displaylogo: false,
                scrollZoom: true
            }});

            // Update UI
            document.getElementById('currentFrame').textContent = frameIndex + 1;
            document.getElementById('frameSlider').value = frameIndex;

            // Update progress bar
            const progress = ((frameIndex + 1) / framesData.length) * 100;
            document.getElementById('progressFill').style.width = progress + '%';
        }}

        // Play animation
        function playAnimation() {{
            if (isPlaying) return;

            isPlaying = true;
            document.getElementById('playBtn').disabled = true;
            document.getElementById('pauseBtn').disabled = false;
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('statusText').textContent = '🎬 Playing...';
            document.getElementById('statusText').style.color = '#2196F3';

            const speed = parseFloat(document.getElementById('speedSlider').value);
            const frameDuration = baseFrameDuration / speed;

            animationInterval = setInterval(() => {{
                if (currentFrameIndex >= framesData.length - 1) {{
                    stopAnimation();
                    return;
                }}
                updateFrame(currentFrameIndex + 1);
            }}, frameDuration);
        }}

        // Pause animation
        function pauseAnimation() {{
            if (!isPlaying) return;

            isPlaying = false;
            clearInterval(animationInterval);

            document.getElementById('playBtn').disabled = false;
            document.getElementById('pauseBtn').disabled = true;
            document.getElementById('statusText').textContent = '⏸ Paused';
            document.getElementById('statusText').style.color = '#FF9800';
        }}

        // Stop animation
        function stopAnimation() {{
            isPlaying = false;
            clearInterval(animationInterval);

            updateFrame(0);

            document.getElementById('playBtn').disabled = false;
            document.getElementById('pauseBtn').disabled = true;
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('statusText').textContent = '⏹ Stopped';
            document.getElementById('statusText').style.color = '#f44336';
        }}

        // Camera controls
        function resetCamera() {{
            Plotly.relayout('plot', {{
                'scene.camera': figureData.layout.scene.camera
            }});
        }}

        function setTopView() {{
            Plotly.relayout('plot', {{
                'scene.camera': {{
                    eye: {{x: 0, y: 0, z: 5}},
                    center: {{x: 0, y: 0, z: 0}},
                    up: {{x: 0, y: 1, z: 0}}
                }}
            }});
        }}

        function setSideView() {{
            Plotly.relayout('plot', {{
                'scene.camera': {{
                    eye: {{x: 5, y: 0, z: 0}},
                    center: {{x: 0, y: 0, z: 0}},
                    up: {{x: 0, y: 0, z: 1}}
                }}
            }});
        }}

        function setIsometricView() {{
            Plotly.relayout('plot', {{
                'scene.camera': {{
                    eye: {{x: 1.5, y: 1.5, z: 1.5}},
                    center: {{x: 0, y: 0, z: 0}},
                    up: {{x: 0, y: 0, z: 1}}
                }}
            }});
        }}

        // Event listeners
        document.getElementById('playBtn').addEventListener('click', playAnimation);
        document.getElementById('pauseBtn').addEventListener('click', pauseAnimation);
        document.getElementById('stopBtn').addEventListener('click', stopAnimation);

        document.getElementById('frameSlider').addEventListener('input', function(e) {{
            pauseAnimation();
            updateFrame(parseInt(e.target.value));
        }});

        document.getElementById('speedSlider').addEventListener('input', function(e) {{
            const speed = parseFloat(e.target.value);
            document.getElementById('speedValue').textContent = speed.toFixed(1);

            // Restart animation with new speed if playing
            if (isPlaying) {{
                pauseAnimation();
                playAnimation();
            }}
        }});

        // Initialize on load
        window.addEventListener('load', function() {{
            initPlot();
        }});

        // Handle window resize
        window.addEventListener('resize', function() {{
            Plotly.Plots.resize('plot');
        }});
    </script>
</body>
</html>
        """
        return html_template