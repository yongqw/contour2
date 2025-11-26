"""
Python 3D renderer for Terrain Tunneling Calculator.

This service provides native Python 3D rendering capabilities using matplotlib,
allowing for direct window rendering of 3D scenes without requiring HTML export.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from typing import List, Tuple, Optional, Dict, Any, Union
import tkinter as tk
from tkinter import ttk
import threading
import time

from models.terrain_mesh import TerrainMesh
from models.tunnel_geometry import TunnelGeometry
from utils.exceptions import VisualizationError


class Python3DRenderer:
    """Service for native Python 3D rendering using matplotlib."""

    def __init__(self, style_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Python 3D renderer.

        Args:
            style_config: Optional style configuration dictionary
        """
        import logging
        self.logger = logging.getLogger(__name__)

        # Default style configuration
        self.style_config = {
            'figure_width': 10,
            'figure_height': 8,
            'terrain_colorscheme': 'terrain',
            'tunnel_color': '#FF1493',
            'tunnel_alpha': 0.8,
            'terrain_alpha': 0.9,
            'wireframe_color': 'black',
            'wireframe_alpha': 0.3,
            'show_wireframe': False,
            'show_axes': True,
            'axes_labels': {'x': 'X (m)', 'y': 'Y (m)', 'z': 'Z (m)'},
            'grid_alpha': 0.3,
            'background_color': 'white',
            'camera_azim': 45,  # Azimuth angle
            'camera_elev': 30,  # Elevation angle
            'animation_fps': 30,
            'car_color': 'red',
            'car_size': 50,
            'trail_length': 20
        }

        # Update with provided config
        if style_config:
            self.style_config.update(style_config)

        # Rendering state
        self.current_figure = None
        self.current_axes = None
        self.animation = None
        self.canvas = None

    def create_terrain_figure(self, terrain_mesh: TerrainMesh,
                             title: str = "3D Terrain Visualization") -> plt.Figure:
        """
        Create a matplotlib figure with terrain mesh.

        Args:
            terrain_mesh: TerrainMesh object to visualize
            title: Figure title

        Returns:
            matplotlib Figure object

        Raises:
            VisualizationError: If figure creation fails
        """
        try:
            # Validate mesh
            if terrain_mesh.vertex_count == 0:
                raise VisualizationError("Terrain mesh has no vertices")

            # Create figure and 3D axes
            fig = plt.figure(figsize=(self.style_config['figure_width'],
                                    self.style_config['figure_height']))
            ax = fig.add_subplot(111, projection='3d')

            # Extract vertices and triangles
            vertices = terrain_mesh.vertices
            triangles = terrain_mesh.triangles

            # Create surface plot
            if self.style_config['show_wireframe']:
                # Plot as wireframe
                for triangle in triangles:
                    v_indices = triangle.vertex_indices
                    triangle_vertices = vertices[v_indices]

                    # Close the triangle by adding first vertex at end
                    triangle_vertices = np.vstack([triangle_vertices, triangle_vertices[0]])

                    ax.plot(triangle_vertices[:, 0],
                           triangle_vertices[:, 1],
                           triangle_vertices[:, 2],
                           color=self.style_config['wireframe_color'],
                           alpha=self.style_config['wireframe_alpha'],
                           linewidth=0.5)
            else:
                # Plot as surface
                # Prepare triangle data for plot_trisurf
                x = vertices[:, 0]
                y = vertices[:, 1]
                z = vertices[:, 2]

                # Create triangulation
                triangles_array = np.array([[t.vertex_indices[0], t.vertex_indices[1], t.vertex_indices[2]]
                                          for t in triangles])

                # Plot surface
                surf = ax.plot_trisurf(x, y, z, triangles=triangles_array,
                                      cmap=self.style_config['terrain_colorscheme'],
                                      alpha=self.style_config['terrain_alpha'],
                                      edgecolor='none')

                # Add colorbar
                fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5, label='Elevation (m)')

            # Set labels and title
            if self.style_config['show_axes']:
                ax.set_xlabel(self.style_config['axes_labels']['x'])
                ax.set_ylabel(self.style_config['axes_labels']['y'])
                ax.set_zlabel(self.style_config['axes_labels']['z'])

            ax.set_title(title)

            # Set viewing angle
            ax.view_init(elev=self.style_config['camera_elev'],
                        azim=self.style_config['camera_azim'])

            # Set background color
            fig.patch.set_facecolor(self.style_config['background_color'])
            ax.set_facecolor(self.style_config['background_color'])

            # Enable grid
            ax.grid(True, alpha=self.style_config['grid_alpha'])

            return fig

        except Exception as e:
            raise VisualizationError(f"Failed to create terrain figure: {str(e)}")

    def create_integrated_figure(self, terrain_mesh: TerrainMesh,
                                tunnel_geometry: TunnelGeometry,
                                title: str = "3D Terrain and Tunnel Visualization") -> plt.Figure:
        """
        Create integrated figure with terrain and tunnel.

        Args:
            terrain_mesh: TerrainMesh object
            tunnel_geometry: TunnelGeometry object
            title: Figure title

        Returns:
            matplotlib Figure object
        """
        try:
            # Start with terrain figure
            fig = self.create_terrain_figure(terrain_mesh, title)
            ax = fig.gca()

            # Add tunnel visualization
            self._add_tunnel_to_axes(ax, tunnel_geometry)

            return fig

        except Exception as e:
            raise VisualizationError(f"Failed to create integrated figure: {str(e)}")

    def _add_tunnel_to_axes(self, ax: Axes3D, tunnel_geometry: TunnelGeometry):
        """
        Add tunnel visualization to matplotlib 3D axes.

        Args:
            ax: matplotlib 3D axes
            tunnel_geometry: TunnelGeometry object
        """
        try:
            # Get tunnel path points
            if hasattr(tunnel_geometry, 'path') and tunnel_geometry.path.waypoints:
                # Extract waypoint coordinates
                waypoint_coords = []
                for wp in tunnel_geometry.path.waypoints:
                    waypoint_coords.append([wp.x, wp.y, wp.elevation])

                waypoint_coords = np.array(waypoint_coords)

                # Plot tunnel path as thick line
                ax.plot(waypoint_coords[:, 0],
                       waypoint_coords[:, 1],
                       waypoint_coords[:, 2],
                       color=self.style_config['tunnel_color'],
                       linewidth=4,
                       alpha=self.style_config['tunnel_alpha'],
                       label='Tunnel Path')

                # Add tunnel entrance and exit markers
                if len(waypoint_coords) >= 2:
                    # Entrance marker
                    ax.scatter(waypoint_coords[0, 0],
                             waypoint_coords[0, 1],
                             waypoint_coords[0, 2],
                             color='green',
                             s=100,
                             marker='o',
                             label='Entrance')

                    # Exit marker
                    ax.scatter(waypoint_coords[-1, 0],
                             waypoint_coords[-1, 1],
                             waypoint_coords[-1, 2],
                             color='red',
                             s=100,
                             marker='s',
                             label='Exit')

            # Add tunnel tube visualization (simplified)
            self._add_tunnel_tube_visualization(ax, tunnel_geometry)

            # Add legend
            ax.legend()

        except Exception as e:
            self.logger.warning(f"Failed to add tunnel to axes: {str(e)}")

    def _add_tunnel_tube_visualization(self, ax: Axes3D, tunnel_geometry: TunnelGeometry):
        """
        Add simplified tunnel tube visualization.

        Args:
            ax: matplotlib 3D axes
            tunnel_geometry: TunnelGeometry object
        """
        try:
            # This is a simplified tube visualization
            # In a full implementation, you would create actual tube geometry

            if hasattr(tunnel_geometry, 'path') and tunnel_geometry.path.waypoints:
                waypoint_coords = []
                for wp in tunnel_geometry.path.waypoints:
                    waypoint_coords.append([wp.x, wp.y, wp.elevation])

                waypoint_coords = np.array(waypoint_coords)

                # Create multiple parallel lines to simulate tube
                if len(waypoint_coords) >= 2:
                    # Calculate direction vectors
                    directions = np.diff(waypoint_coords, axis=0)
                    directions = directions / np.linalg.norm(directions, axis=1, keepdims=True)

                    # Create perpendicular vectors for tube width
                    tube_radius = 2.0  # Simplified tube radius

                    for i in range(len(waypoint_coords) - 1):
                        # Create circle around each waypoint
                        center = waypoint_coords[i]

                        # Create perpendicular vectors
                        if i < len(directions):
                            direction = directions[i]
                        else:
                            direction = directions[-1]

                        # Find perpendicular vectors
                        if abs(direction[2]) < 0.9:
                            perp1 = np.cross(direction, [0, 0, 1])
                        else:
                            perp1 = np.cross(direction, [1, 0, 0])
                        perp1 = perp1 / np.linalg.norm(perp1) * tube_radius
                        perp2 = np.cross(direction, perp1)
                        perp2 = perp2 / np.linalg.norm(perp2) * tube_radius

                        # Create circle points
                        theta = np.linspace(0, 2*np.pi, 8)
                        circle_points = []
                        for t in theta:
                            point = center + perp1 * np.cos(t) + perp2 * np.sin(t)
                            circle_points.append(point)

                        circle_points = np.array(circle_points)

                        # Plot circle
                        ax.plot(circle_points[:, 0],
                               circle_points[:, 1],
                               circle_points[:, 2],
                               color=self.style_config['tunnel_color'],
                               alpha=0.3,
                               linewidth=1)

        except Exception as e:
            self.logger.warning(f"Failed to add tunnel tube visualization: {str(e)}")

    def embed_in_tkinter(self, fig: plt.Figure, parent_frame) -> FigureCanvasTkAgg:
        """
        Embed matplotlib figure in tkinter frame.

        Args:
            fig: matplotlib Figure object
            parent_frame: tkinter parent frame

        Returns:
            FigureCanvasTkAgg canvas object
        """
        try:
            # Clear any existing canvas
            if self.canvas:
                self.canvas.get_tk_widget().destroy()

            # Create new canvas
            self.canvas = FigureCanvasTkAgg(fig, parent_frame)
            self.canvas.draw()

            # Add toolbar
            toolbar_frame = ttk.Frame(parent_frame)
            toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)

            toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
            toolbar.update()

            # Pack canvas
            self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

            # Store current figure and axes
            self.current_figure = fig
            self.current_axes = fig.gca()

            return self.canvas

        except Exception as e:
            raise VisualizationError(f"Failed to embed figure in tkinter: {str(e)}")

    def create_animation(self, terrain_mesh: TerrainMesh,
                        tunnel_geometry: TunnelGeometry,
                        duration: float = 10.0,
                        fps: int = 30) -> animation.FuncAnimation:
        """
        Create animated car movement through tunnel.

        Args:
            terrain_mesh: TerrainMesh object
            tunnel_geometry: TunnelGeometry object
            duration: Animation duration in seconds
            fps: Frames per second

        Returns:
            matplotlib FuncAnimation object
        """
        try:
            # Create base figure
            fig = self.create_integrated_figure(terrain_mesh, tunnel_geometry, "Tunnel Animation")
            ax = fig.gca()

            # Generate animation frames
            frames = self._generate_animation_frames(tunnel_geometry, duration, fps)

            # Create animation
            anim = animation.FuncAnimation(
                fig,
                lambda frame: self._update_animation_frame(ax, frame, terrain_mesh, tunnel_geometry),
                frames=frames,
                interval=1000/fps,
                blit=False,
                repeat=True
            )

            # Store figure reference for access
            anim._fig = fig
            anim._ax = ax

            self.animation = anim
            return anim

        except Exception as e:
            raise VisualizationError(f"Failed to create animation: {str(e)}")

    def _generate_animation_frames(self, tunnel_geometry: TunnelGeometry,
                                  duration: float, fps: int) -> List[Dict]:
        """Generate animation frame data."""
        frames = []
        total_frames = int(duration * fps)

        # Get tunnel path
        if not (hasattr(tunnel_geometry, 'path') and tunnel_geometry.path.waypoints):
            return frames

        waypoint_coords = []
        for wp in tunnel_geometry.path.waypoints:
            waypoint_coords.append([wp.x, wp.y, wp.elevation])
        waypoint_coords = np.array(waypoint_coords)

        for frame_num in range(total_frames):
            progress = frame_num / (total_frames - 1) if total_frames > 1 else 0

            # Interpolate position
            car_position = self._interpolate_path_position(waypoint_coords, progress)

            frames.append({
                'frame_number': frame_num,
                'progress': progress,
                'car_position': car_position
            })

        return frames

    def _interpolate_path_position(self, waypoint_coords: np.ndarray, progress: float) -> np.ndarray:
        """Interpolate car position along tunnel path."""
        if progress <= 0:
            return waypoint_coords[0]
        if progress >= 1:
            return waypoint_coords[-1]

        # Simple linear interpolation
        total_segments = len(waypoint_coords) - 1
        segment = min(int(progress * total_segments), total_segments - 1)
        segment_progress = (progress * total_segments) - segment

        start_point = waypoint_coords[segment]
        end_point = waypoint_coords[segment + 1]

        return start_point + (end_point - start_point) * segment_progress

    def _update_animation_frame(self, ax: Axes3D, frame_data: Dict,
                               terrain_mesh: TerrainMesh,
                               tunnel_geometry: TunnelGeometry):
        """Update animation frame."""
        try:
            # Clear previous dynamic elements (keep static terrain)
            # Remove only car markers
            collections_to_remove = []
            for collection in ax.collections[:]:
                if hasattr(collection, '_car_marker'):
                    collections_to_remove.append(collection)

            for collection in collections_to_remove:
                collection.remove()

            # Add car at new position
            car_pos = frame_data['car_position']
            car_scatter = ax.scatter(car_pos[0], car_pos[1], car_pos[2],
                                   color=self.style_config['car_color'],
                                   s=self.style_config['car_size'],
                                   marker='o',
                                   label='Car',
                                   alpha=1.0)
            car_scatter._car_marker = True  # Mark for removal

            # Update title with progress
            progress_percent = frame_data['progress'] * 100
            ax.set_title(f"Tunnel Animation - Progress: {progress_percent:.1f}%")

            # Force redraw
            ax.figure.canvas.draw_idle()

        except Exception as e:
            self.logger.warning(f"Failed to update animation frame: {str(e)}")
            # Ensure something is visible even if update fails
            try:
                ax.set_title(f"Tunnel Animation - Frame {frame_data.get('frame_number', 0)}")
            except:
                pass

    def save_animation_gif(self, anim: animation.FuncAnimation,
                          filename: str,
                          duration: float = 10.0) -> None:
        """
        Save animation as GIF file.

        Args:
            anim: matplotlib FuncAnimation object
            filename: Output filename
            duration: Animation duration
        """
        try:
            # Calculate interval for proper duration
            fps = anim.save_count / duration
            interval = 1000 / fps

            anim.save(filename, writer='pillow', fps=fps, interval=interval)

        except Exception as e:
            raise VisualizationError(f"Failed to save animation GIF: {str(e)}")

    def save_figure_image(self, fig: plt.Figure, filename: str,
                         dpi: int = 300) -> None:
        """
        Save figure as image file.

        Args:
            fig: matplotlib Figure object
            filename: Output filename
            dpi: Image resolution
        """
        try:
            fig.savefig(filename, dpi=dpi, bbox_inches='tight',
                       facecolor=self.style_config['background_color'])

        except Exception as e:
            raise VisualizationError(f"Failed to save figure: {str(e)}")

    def set_camera_position(self, azim: float, elev: float):
        """
        Set camera viewing angle.

        Args:
            azim: Azimuth angle in degrees
            elev: Elevation angle in degrees
        """
        self.style_config['camera_azim'] = azim
        self.style_config['camera_elev'] = elev

        if self.current_axes:
            self.current_axes.view_init(elev=elev, azim=azim)
            if self.canvas:
                self.canvas.draw()

    def rotate_camera(self, delta_azim: float = 5, delta_elev: float = 0):
        """
        Rotate camera by specified angles.

        Args:
            delta_azim: Change in azimuth angle
            delta_elev: Change in elevation angle
        """
        new_azim = self.style_config['camera_azim'] + delta_azim
        new_elev = self.style_config['camera_elev'] + delta_elev

        # Keep elevation in reasonable range
        new_elev = max(-90, min(90, new_elev))

        self.set_camera_position(new_azim, new_elev)

    def cleanup(self):
        """Clean up resources."""
        try:
            if self.animation:
                self.animation.event_source.stop()
                self.animation = None

            if self.canvas:
                self.canvas.get_tk_widget().destroy()
                self.canvas = None

            if self.current_figure:
                plt.close(self.current_figure)
                self.current_figure = None
                self.current_axes = None

        except Exception as e:
            self.logger.warning(f"Error during cleanup: {str(e)}")