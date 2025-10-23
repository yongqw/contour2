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
            # For TunnelGeometry, we need to interpolate path
            start_2d = tunnel_path.start_point
            end_2d = tunnel_path.end_point

            # Create simple linear interpolation for now
            # This would be enhanced with actual tunnel path calculation
            num_points = 50
            path_2d = np.linspace(start_2d, end_2d, num_points)

            # Estimate elevation (simplified - should use terrain mesh)
            path_points = np.column_stack([
                path_2d[:, 0],
                path_2d[:, 1],
                np.ones(num_points) * 1.0  # Assume elevation of 1.0
            ])

            # Calculate tunnel length
            tunnel_length = np.linalg.norm(end_2d - start_2d)
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
                # Create frame-specific traces
                frame_traces = self._create_frame_traces(frame, terrain_mesh, tunnel_geometry)

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

        # Add tunnel to the figure
        # Note: This would need to be implemented based on tunnel geometry
        # For now, return the terrain figure

        return terrain_fig

    def _create_frame_traces(self,
                             frame: AnimationFrame,
                             terrain_mesh: TerrainMesh,
                             tunnel_geometry: TunnelGeometry) -> List[go.Scatter3d]:
        """
        Create traces for a specific animation frame.

        Args:
            frame: Animation frame data
            terrain_mesh: Terrain mesh
            tunnel_geometry: Tunnel geometry

        Returns:
            List of plotly traces for the frame
        """
        traces = []

        # Add car trace
        car_trace = go.Scatter3d(
            x=[frame.car_position[0]],
            y=[frame.car_position[1]],
            z=[frame.car_position[2]],
            mode='markers',
            marker=dict(
                size=self.config['car_size'] * 100,  # Scale for visibility
                color=self.config['car_color'],
                symbol='diamond'
            ),
            name='Car',
            showlegend=True
        )
        traces.append(car_trace)

        # Add car orientation indicator
        orientation_end = frame.car_position + frame.car_orientation * 0.5
        orientation_trace = go.Scatter3d(
            x=[frame.car_position[0], orientation_end[0]],
            y=[frame.car_position[1], orientation_end[1]],
            z=[frame.car_position[2], orientation_end[2]],
            mode='lines',
            line=dict(color='blue', width=3),
            name='Direction',
            showlegend=False
        )
        traces.append(orientation_trace)

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
            Path(filename).write_text(html_content)

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