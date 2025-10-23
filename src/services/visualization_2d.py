"""
2D visualization service for Terrain Tunneling Calculator.

This service handles 2D visualization of contour data, including contour plots,
elevation-based color mapping, and interactive displays.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Polygon as MPLPolygon
from matplotlib.collections import PatchCollection, LineCollection
from typing import List, Tuple, Optional, Dict, Any, Union
from pathlib import Path

from models.contour_data import ContourData, ContourLine
# Tunnel geometry will be imported when needed (User Story 2)
from utils.math_utils import BoundingBox
from utils.exceptions import VisualizationError


class Visualization2DService:
    """Service for 2D visualization of contour and tunnel data."""

    def __init__(self, style_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the 2D visualization service.

        Args:
            style_config: Optional style configuration dictionary
        """
        # Default style configuration
        self.style_config = {
            'figure_size': (12, 8),
            'dpi': 100,
            'contour_colors': 'terrain',
            'contour_alpha': 0.8,
            'contour_linewidths': 1.5,
            'fill_contours': True,
            'show_elevation_labels': True,
            'label_font_size': 8,
            'grid_alpha': 0.3,
            'axis_label_font_size': 10,
            'title_font_size': 14,
            'tunnel_color': '#FF6B6B',
            'tunnel_linewidth': 3,
            'tunnel_alpha': 0.8,
            'background_color': 'white',
            'coordinate_grid': True
        }

        # Update with provided config
        if style_config:
            self.style_config.update(style_config)

        # Set matplotlib style
        plt.style.use('default')

    def create_contour_plot(self, contour_data: ContourData,
                           title: Optional[str] = None,
                           show_grid: Optional[bool] = None) -> plt.Figure:
        """
        Create a 2D contour plot.

        Args:
            contour_data: ContourData object to visualize
            title: Optional plot title
            show_grid: Whether to show coordinate grid

        Returns:
            matplotlib Figure object

        Raises:
            VisualizationError: If plot creation fails
        """
        try:
            # Create figure and axis
            fig, ax = plt.subplots(figsize=self.style_config['figure_size'],
                                 dpi=self.style_config['dpi'])

            # Set background
            ax.set_facecolor(self.style_config['background_color'])

            # Get elevation range for color mapping
            elevations = [contour.elevation for contour in contour_data.contours]
            min_elev, max_elev = min(elevations), max(elevations)

            # Create colormap
            cmap = plt.get_cmap(self.style_config['contour_colors'])
            norm = mcolors.Normalize(vmin=min_elev, vmax=max_elev)

            # Plot contours
            patches = []
            colors = []

            for contour in contour_data.contours:
                if len(contour.points) < 3:
                    continue

                # Create polygon patch
                polygon = MPLPolygon(contour.points[:, :2],
                                    closed=True,
                                    alpha=self.style_config['contour_alpha'])
                patches.append(polygon)
                colors.append(contour.elevation)

                # Plot contour line
                color = cmap(norm(contour.elevation))
                ax.plot(contour.points[:, 0], contour.points[:, 1],
                       color=color,
                       linewidth=self.style_config['contour_linewidths'],
                       alpha=self.style_config['contour_alpha'])

                # Add elevation labels
                if self.style_config['show_elevation_labels']:
                    self._add_elevation_label(ax, contour, color)

            # Add filled contours if enabled
            if self.style_config['fill_contours'] and patches:
                patch_collection = PatchCollection(patches, cmap=cmap, norm=norm)
                patch_collection.set_array(np.array(colors))
                ax.add_collection(patch_collection)

            # Set plot properties
            bounds = contour_data.get_bounds()
            ax.set_xlim(bounds.min_x, bounds.max_x)
            ax.set_ylim(bounds.min_y, bounds.max_y)

            # Add colorbar
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
            sm.set_array([])
            cbar = plt.colorbar(sm, ax=ax, shrink=0.8)
            cbar.set_label('Elevation (m)', fontsize=self.style_config['axis_label_font_size'])

            # Set labels and title
            ax.set_xlabel('X Coordinate (m)', fontsize=self.style_config['axis_label_font_size'])
            ax.set_ylabel('Y Coordinate (m)', fontsize=self.style_config['axis_label_font_size'])

            if title is None:
                title = f"Contour Map - {contour_data.metadata.name}"
            ax.set_title(title, fontsize=self.style_config['title_font_size'])

            # Add grid if enabled
            show_grid = show_grid if show_grid is not None else self.style_config['coordinate_grid']
            if show_grid:
                ax.grid(True, alpha=self.style_config['grid_alpha'])

            # Set aspect ratio
            ax.set_aspect('equal', adjustable='box')

            # Add metadata info
            self._add_metadata_text(ax, contour_data)

            plt.tight_layout()
            return fig

        except Exception as e:
            raise VisualizationError(f"Failed to create contour plot: {e}")

    def create_tunnel_overlay(self, contour_data: ContourData,
                            tunnel_geometry=None,  # Will be TunnelGeometry when User Story 2 is implemented
                            title: Optional[str] = None) -> plt.Figure:
        """
        Create a contour plot with tunnel overlay.

        Args:
            contour_data: ContourData object
            tunnel_geometry: TunnelGeometry object to overlay
            title: Optional plot title

        Returns:
            matplotlib Figure object
        """
        # Create base contour plot
        fig = self.create_contour_plot(contour_data, title)
        ax = fig.gca()

        # Plot tunnel if provided
        if tunnel_geometry is not None:
            self._plot_tunnel(ax, tunnel_geometry)
            self._add_tunnel_legend(ax, tunnel_geometry)

        plt.tight_layout()
        return fig

    def create_elevation_profile(self, tunnel_geometry=None,  # Will be TunnelGeometry when User Story 2 is implemented
                               title: Optional[str] = None) -> plt.Figure:
        """
        Create an elevation profile along the tunnel path.

        Args:
            tunnel_geometry: TunnelGeometry object
            title: Optional plot title

        Returns:
            matplotlib Figure object
        """
        try:
            if tunnel_geometry is None:
                raise VisualizationError("Tunnel geometry not provided")

            # Get elevation profile
            distances, elevations = tunnel_geometry.path.get_elevation_profile()

            if len(distances) < 2:
                raise VisualizationError("Insufficient points for elevation profile")

            # Create figure
            fig, ax = plt.subplots(figsize=self.style_config['figure_size'],
                                 dpi=self.style_config['dpi'])

            # Plot elevation profile
            ax.plot(distances, elevations,
                   color='blue', linewidth=2, label='Tunnel Elevation')

            # Fill area under curve
            ax.fill_between(distances, min(elevations), elevations,
                           alpha=0.3, color='blue')

            # Add tunnel radius indicators
            if hasattr(tunnel_geometry, 'radius'):
                radius = tunnel_geometry.radius
                ax.fill_between(distances,
                              [e - radius for e in elevations],
                              [e + radius for e in elevations],
                              alpha=0.2, color='red', label='Tunnel Cross-section')

            # Set labels and title
            ax.set_xlabel('Distance along tunnel (m)', fontsize=self.style_config['axis_label_font_size'])
            ax.set_ylabel('Elevation (m)', fontsize=self.style_config['axis_label_font_size'])

            if title is None:
                title = "Tunnel Elevation Profile"
            ax.set_title(title, fontsize=self.style_config['title_font_size'])

            # Add grid and legend
            ax.grid(True, alpha=self.style_config['grid_alpha'])
            ax.legend()

            # Add statistics
            self._add_profile_statistics(ax, distances, elevations)

            plt.tight_layout()
            return fig

        except Exception as e:
            raise VisualizationError(f"Failed to create elevation profile: {e}")

    def _add_elevation_label(self, ax: plt.Axes, contour: ContourLine, color: str):
        """Add elevation label to contour."""
        # Find a good position for the label (center of contour)
        center_point = np.mean(contour.points[:-1], axis=0)  # Exclude closing point

        # Create label text
        label_text = f"{contour.elevation:.1f}"

        # Add label
        ax.annotate(label_text,
                   xy=(center_point[0], center_point[1]),
                   fontsize=self.style_config['label_font_size'],
                   color='white' if self.style_config['fill_contours'] else color,
                   ha='center', va='center',
                   bbox=dict(boxstyle='round,pad=0.3',
                            facecolor=color if self.style_config['fill_contours'] else 'white',
                            alpha=0.7))

    def _plot_tunnel(self, ax: plt.Axes, tunnel_geometry):  # TunnelGeometry will be available in User Story 2
        """Plot tunnel geometry on the axis."""
        # Get tunnel path points
        path_points = []
        for waypoint in tunnel_geometry.path.waypoints:
            path_points.append([waypoint.x, waypoint.y])

        if len(path_points) < 2:
            return

        path_points = np.array(path_points)

        # Plot tunnel centerline
        ax.plot(path_points[:, 0], path_points[:, 1],
               color=self.style_config['tunnel_color'],
               linewidth=self.style_config['tunnel_linewidth'],
               alpha=self.style_config['tunnel_alpha'],
               label='Tunnel Path')

        # Plot tunnel waypoints
        ax.scatter(path_points[:, 0], path_points[:, 1],
                  color=self.style_config['tunnel_color'],
                  s=50, zorder=5,
                  label='Waypoints')

        # Add tunnel radius visualization (simplified)
        if hasattr(tunnel_geometry, 'radius'):
            radius = tunnel_geometry.radius
            for point in path_points[::max(1, len(path_points) // 10)]:  # Show every 10th point
                circle = plt.Circle((point[0], point[1]), radius,
                                  color=self.style_config['tunnel_color'],
                                  fill=False, alpha=0.3, linestyle='--')
                ax.add_patch(circle)

    def _add_tunnel_legend(self, ax: plt.Axes, tunnel_geometry):  # TunnelGeometry will be available in User Story 2
        """Add tunnel information to the legend."""
        tunnel_info = []
        if hasattr(tunnel_geometry, 'radius'):
            tunnel_info.append(f"Radius: {tunnel_geometry.radius:.1f}m")

        if hasattr(tunnel_geometry, 'cross_section_type'):
            tunnel_info.append(f"Type: {tunnel_geometry.cross_section_type}")

        # Get tunnel length
        if hasattr(tunnel_geometry.path, 'get_total_length'):
            length = tunnel_geometry.path.get_total_length()
            tunnel_info.append(f"Length: {length:.1f}m")

        # Add info text
        info_text = " | ".join(tunnel_info)
        ax.text(0.02, 0.98, info_text,
               transform=ax.transAxes,
               fontsize=self.style_config['label_font_size'],
               verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    def _add_metadata_text(self, ax: plt.Axes, contour_data: ContourData):
        """Add metadata information to the plot."""
        metadata_lines = [
            f"Name: {contour_data.metadata.name}",
            f"Units: {contour_data.metadata.units}",
            f"Contours: {len(contour_data.contours)}",
        ]

        # Add elevation range
        min_elev, max_elev = contour_data.get_elevation_range()
        metadata_lines.append(f"Elevation: {min_elev:.1f} - {max_elev:.1f}m")

        # Add coordinate system
        metadata_lines.append(f"Coordinate System: {contour_data.coordinate_system.value}")

        # Create info text
        info_text = "\n".join(metadata_lines)

        # Add text box
        ax.text(0.98, 0.02, info_text,
               transform=ax.transAxes,
               fontsize=self.style_config['label_font_size'],
               verticalalignment='bottom',
               horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))

    def _add_profile_statistics(self, ax: plt.Axes, distances: np.ndarray, elevations: np.ndarray):
        """Add statistics to the elevation profile."""
        stats = [
            f"Total Distance: {distances[-1]:.1f}m",
            f"Min Elevation: {np.min(elevations):.1f}m",
            f"Max Elevation: {np.max(elevations):.1f}m",
            f"Elevation Change: {np.max(elevations) - np.min(elevations):.1f}m",
            f"Average Gradient: {(np.max(elevations) - np.min(elevations)) / distances[-1] * 100:.2f}%"
        ]

        stats_text = "\n".join(stats)

        ax.text(0.02, 0.98, stats_text,
               transform=ax.transAxes,
               fontsize=self.style_config['label_font_size'],
               verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))

    def save_plot(self, fig: plt.Figure, file_path: Union[str, Path],
                  dpi: Optional[int] = None, bbox_inches: str = 'tight') -> None:
        """
        Save plot to file.

        Args:
            fig: matplotlib Figure to save
            file_path: Output file path
            dpi: Optional DPI for raster formats
            bbox_inches: Bounding box setting

        Raises:
            VisualizationError: If save operation fails
        """
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            save_dpi = dpi or self.style_config['dpi']

            fig.savefig(file_path, dpi=save_dpi, bbox_inches=bbox_inches)

        except Exception as e:
            raise VisualizationError(f"Failed to save plot to {file_path}: {e}")

    def create_comparison_plot(self, contour_data_before: ContourData,
                              contour_data_after: ContourData,
                              title: Optional[str] = None) -> plt.Figure:
        """
        Create a side-by-side comparison of two contour datasets.

        Args:
            contour_data_before: Before contour data
            contour_data_after: After contour data
            title: Optional plot title

        Returns:
            matplotlib Figure object
        """
        try:
            # Create figure with subplots
            fig, (ax1, ax2) = plt.subplots(1, 2,
                                          figsize=(16, 8),
                                          dpi=self.style_config['dpi'])

            # Plot before data
            self._plot_contours_on_axis(ax1, contour_data_before, "Before")
            ax1.set_title("Before", fontsize=self.style_config['title_font_size'])

            # Plot after data
            self._plot_contours_on_axis(ax2, contour_data_after, "After")
            ax2.set_title("After", fontsize=self.style_config['title_font_size'])

            # Set main title
            if title is None:
                title = "Contour Comparison"
            fig.suptitle(title, fontsize=self.style_config['title_font_size'] + 2)

            plt.tight_layout()
            return fig

        except Exception as e:
            raise VisualizationError(f"Failed to create comparison plot: {e}")

    def _plot_contours_on_axis(self, ax: plt.Axes, contour_data: ContourData, label: str):
        """Plot contours on a specific axis."""
        # Get elevation range
        elevations = [contour.elevation for contour in contour_data.contours]
        if not elevations:
            return

        min_elev, max_elev = min(elevations), max(elevations)

        # Create colormap
        cmap = plt.get_cmap(self.style_config['contour_colors'])
        norm = mcolors.Normalize(vmin=min_elev, vmax=max_elev)

        # Plot contours
        for contour in contour_data.contours:
            if len(contour.points) < 3:
                continue

            color = cmap(norm(contour.elevation))
            ax.fill(contour.points[:, 0], contour.points[:, 1],
                   color=color, alpha=self.style_config['contour_alpha'])
            ax.plot(contour.points[:, 0], contour.points[:, 1],
                   color='black', linewidth=self.style_config['contour_linewidths'])

        # Set plot properties
        bounds = contour_data.get_bounds()
        ax.set_xlim(bounds.min_x, bounds.max_x)
        ax.set_ylim(bounds.min_y, bounds.max_y)
        ax.set_aspect('equal', adjustable='box')
        ax.grid(True, alpha=self.style_config['grid_alpha'])

        # Add colorbar
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, shrink=0.8)
        cbar.set_label('Elevation (m)', fontsize=self.style_config['axis_label_font_size'])

        ax.set_xlabel('X Coordinate (m)', fontsize=self.style_config['axis_label_font_size'])
        ax.set_ylabel('Y Coordinate (m)', fontsize=self.style_config['axis_label_font_size'])

    def get_style_config(self) -> Dict[str, Any]:
        """Get current style configuration."""
        return self.style_config.copy()

    def update_style_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update style configuration.

        Args:
            new_config: New configuration values
        """
        self.style_config.update(new_config)