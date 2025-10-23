"""
3D visualization service for Terrain Tunneling Calculator.

This service handles 3D visualization of terrain meshes and tunnel geometry,
including interactive plots, camera controls, and export capabilities.
"""

import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import List, Tuple, Optional, Dict, Any, Union
from pathlib import Path

from models.terrain_mesh import TerrainMesh, Triangle
# Tunnel geometry will be imported when needed (User Story 2)
from models.contour_data import ContourData
from utils.exceptions import VisualizationError


class Visualization3DService:
    """Service for 3D visualization of terrain and tunnel data."""

    def __init__(self, style_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the 3D visualization service.

        Args:
            style_config: Optional style configuration dictionary
        """
        import logging
        self.logger = logging.getLogger(__name__)

        # Default style configuration
        self.style_config = {
            'figure_width': 800,
            'figure_height': 600,
            'terrain_colorscheme': 'Viridis',
            'terrain_colorscale': 'Earth',
            'tunnel_color': '#FF1493',  # Deep pink for maximum contrast against green terrain
            'tunnel_opacity': 1.0,  # Fully opaque
            'mesh_opacity': 1.0,
            'show_mesh_edges': False,
            'mesh_edge_color': 'black',
            'mesh_edge_width': 0.5,
            'lighting_position': {'x': 100, 'y': 100, 'z': 1000},
            'lighting_ambient': 0.8,  # More ambient light for better visibility
            'lighting_diffuse': 0.8,
            'lighting_specular': 0.2,
            'camera_eye': {'x': 1.5, 'y': 1.5, 'z': 1.5},
            'camera_center': {'x': 0, 'y': 0, 'z': 0},
            'camera_up': {'x': 0, 'y': 0, 'z': 1},
            'show_colorbar': True,
            'colorbar_title': 'Elevation (m)',
            'background_color': 'white',
            'grid_color': 'lightgray',
            'show_axes': True,
            'axes_labels': {'x': 'X (m)', 'y': 'Y (m)', 'z': 'Z (m)'}
        }

        # Update with provided config
        if style_config:
            self.style_config.update(style_config)

    def create_terrain_plot(self, terrain_mesh: TerrainMesh,
                           title: Optional[str] = None,
                           show_wireframe: Optional[bool] = None) -> go.Figure:
        """
        Create a 3D terrain mesh visualization with same settings as improved_semicircular_tunnel.py.

        Args:
            terrain_mesh: TerrainMesh object to visualize
            title: Optional plot title
            show_wireframe: Whether to show mesh wireframe

        Returns:
            plotly Figure object

        Raises:
            VisualizationError: If plot creation fails
        """
        try:
            # Validate mesh
            if terrain_mesh.vertex_count == 0:
                raise VisualizationError("Terrain mesh has no vertices")

            # Extract vertices and triangles
            vertices = terrain_mesh.vertices
            triangles = terrain_mesh.triangles

            # Create figure (same as improved_semicircular_tunnel.py)
            fig = go.Figure()

            # Add terrain with exact same settings as improved_semicircular_tunnel.py
            terrain_trace = go.Mesh3d(
                x=vertices[:, 0],
                y=vertices[:, 1],
                z=vertices[:, 2],
                i=[t.vertex_indices[0] for t in triangles],
                j=[t.vertex_indices[1] for t in triangles],
                k=[t.vertex_indices[2] for t in triangles],
                intensity=vertices[:, 2],
                colorscale=[[0.0, "brown"], [1.0, "white"]],  # Same as improved_semicircular_tunnel.py
                name='Terrain',
                opacity=0.6,  # Same as improved_semicircular_tunnel.py
                showscale=True
            )
            fig.add_trace(terrain_trace)

            # Set layout with same settings as improved_semicircular_tunnel.py
            fig.update_layout(
                title=title or "Improved Semicircular Tunnel with Bottom Support",
                scene=dict(
                    xaxis_title='X (m)',
                    yaxis_title='Y (m)',
                    zaxis_title='Elevation (m)',
                    camera=dict(eye=dict(x=1.5, y=1.5, z=0.5)),  # Same as improved_semicircular_tunnel.py
                    bgcolor='white',
                    aspectmode='data'
                ),
                width=1200,
                height=800,
                legend=dict(
                    x=0.02,
                    y=0.98,
                    bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='black',
                    borderwidth=1
                )
            )

            return fig

        except Exception as e:
            raise VisualizationError(f"Failed to create terrain plot: {e}")

    def create_tunnel_overlay(self, terrain_mesh: TerrainMesh,
                            tunnel_geometry=None,  # Will be TunnelGeometry when User Story 2 is implemented
                            title: Optional[str] = None) -> go.Figure:
        """
        Create a 3D terrain plot with tunnel overlay.

        Args:
            terrain_mesh: TerrainMesh object
            tunnel_geometry: TunnelGeometry object to overlay
            title: Optional plot title

        Returns:
            plotly Figure object
        """
        # Create base terrain plot
        fig = self.create_terrain_plot(terrain_mesh, title)

        # Add tunnel visualization
        tunnel_traces = self._create_tunnel_traces(tunnel_geometry)
        for trace in tunnel_traces:
            fig.add_trace(trace)

        # Update layout for tunnel
        fig.update_layout(
            title=title or "3D Terrain with Tunnel Overlay"
        )

        return fig

    def create_tunnel_only_plot(self, tunnel_geometry=None,  # Will be TunnelGeometry when User Story 2 is implemented
                               title: Optional[str] = None) -> go.Figure:
        """
        Create a 3D plot showing only the tunnel geometry.

        Args:
            tunnel_geometry: TunnelGeometry object
            title: Optional plot title

        Returns:
            plotly Figure object
        """
        try:
            # Create tunnel traces
            tunnel_traces = self._create_tunnel_traces(tunnel_geometry)

            # Create figure
            fig = go.Figure(data=tunnel_traces)

            # Set layout
            self._set_3d_layout(fig, title or "3D Tunnel Visualization")

            return fig

        except Exception as e:
            raise VisualizationError(f"Failed to create tunnel plot: {e}")

    def create_comparison_view(self, mesh_before: TerrainMesh,
                             mesh_after: TerrainMesh,
                             title: Optional[str] = None) -> go.Figure:
        """
        Create side-by-side comparison of two terrain meshes.

        Args:
            mesh_before: Before terrain mesh
            mesh_after: After terrain mesh
            title: Optional plot title

        Returns:
            plotly Figure object with subplots
        """
        try:
            # Create subplots
            fig = make_subplots(
                rows=1, cols=2,
                specs=[[{'type': 'scatter3d'}, {'type': 'scatter3d'}]],
                subplot_titles=('Before', 'After'),
                horizontal_spacing=0.1
            )

            # Add before mesh
            before_trace = self._create_mesh_trace(mesh_before, name='Terrain Before')
            fig.add_trace(before_trace, row=1, col=1)

            # Add after mesh
            after_trace = self._create_mesh_trace(mesh_after, name='Terrain After')
            fig.add_trace(after_trace, row=1, col=2)

            # Update layout
            fig.update_layout(
                title=title or "Terrain Comparison",
                width=self.style_config['figure_width'] * 2,
                height=self.style_config['figure_height']
            )

            # Update scene layouts
            fig.update_layout(
                scene=dict(
                    xaxis_title='X (m)',
                    yaxis_title='Y (m)',
                    zaxis_title='Z (m)',
                    camera=self._get_camera_settings()
                ),
                scene2=dict(
                    xaxis_title='X (m)',
                    yaxis_title='Y (m)',
                    zaxis_title='Z (m)',
                    camera=self._get_camera_settings()
                )
            )

            return fig

        except Exception as e:
            raise VisualizationError(f"Failed to create comparison view: {e}")

    def _create_mesh_trace(self, mesh: TerrainMesh, name: str = 'Terrain') -> go.Mesh3d:
        """Create a mesh trace for plotly."""
        vertices = mesh.vertices
        triangles = mesh.triangles

        x = vertices[:, 0]
        y = vertices[:, 1]
        z = vertices[:, 2]

        # Create triangle indices
        triangle_indices = []
        for triangle in triangles:
            triangle_indices.append([triangle.vertex_indices[0],
                                  triangle.vertex_indices[1],
                                  triangle.vertex_indices[2]])

        triangle_indices = np.array(triangle_indices)

        return go.Mesh3d(
            x=x, y=y, z=z,
            i=triangle_indices[:, 0],
            j=triangle_indices[:, 1],
            k=triangle_indices[:, 2],
            colorscale=self.style_config['terrain_colorscale'],
            intensity=z,
            opacity=self.style_config['mesh_opacity'],
            name=name
        )

    def _create_wireframe_trace(self, vertices: np.ndarray, triangles: List[Triangle]) -> go.Scatter3d:
        """Create wireframe trace for mesh edges."""
        edge_x, edge_y, edge_z = [], [], []

        for triangle in triangles:
            for i in range(3):
                j = (i + 1) % 3
                v1, v2 = triangle.vertex_indices[i], triangle.vertex_indices[j]

                edge_x.extend([vertices[v1, 0], vertices[v2, 0], None])
                edge_y.extend([vertices[v1, 1], vertices[v2, 1], None])
                edge_z.extend([vertices[v1, 2], vertices[v2, 2], None])

        return go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(
                color=self.style_config['mesh_edge_color'],
                width=self.style_config['mesh_edge_width']
            ),
            name='Wireframe'
        )

    def _create_tunnel_traces(self, tunnel_geometry) -> List[go.Scatter3d]:  # TunnelGeometry will be available in User Story 2
        """Create visualization traces for tunnel geometry."""
        traces = []

        # Get tunnel path points
        path_points = []
        for waypoint in tunnel_geometry.path.waypoints:
            path_points.append([waypoint.x, waypoint.y, waypoint.elevation])

        if len(path_points) < 2:
            return traces

        path_points = np.array(path_points)

        # Create tunnel centerline
        centerline_trace = go.Scatter3d(
            x=path_points[:, 0],
            y=path_points[:, 1],
            z=path_points[:, 2],
            mode='lines+markers',
            line=dict(
                color=self.style_config['tunnel_color'],
                width=8
            ),
            marker=dict(
                size=4,
                color=self.style_config['tunnel_color']
            ),
            name='Tunnel Centerline'
        )
        traces.append(centerline_trace)

        # Create tunnel cylinder visualization (simplified)
        if hasattr(tunnel_geometry, 'radius'):
            cylinder_traces = self._create_tunnel_cylinder(
                path_points, tunnel_geometry.radius
            )
            traces.extend(cylinder_traces)

        return traces

    def _create_tunnel_cylinder(self, centerline: np.ndarray, radius: float) -> List[go.Scatter3d]:
        """Create cylinder visualization for tunnel."""
        traces = []

        # Create circular cross-sections at regular intervals
        num_sections = min(20, len(centerline))
        section_indices = np.linspace(0, len(centerline) - 1, num_sections, dtype=int)

        for i in section_indices:
            center_point = centerline[i]

            # Create circle points
            angles = np.linspace(0, 2 * np.pi, 16, endpoint=False)
            circle_x = center_point[0] + radius * np.cos(angles)
            circle_y = center_point[1] + radius * np.sin(angles)
            circle_z = np.full_like(angles, center_point[2])

            # Close the circle
            circle_x = np.append(circle_x, circle_x[0])
            circle_y = np.append(circle_y, circle_y[0])
            circle_z = np.append(circle_z, circle_z[0])

            circle_trace = go.Scatter3d(
                x=circle_x, y=circle_y, z=circle_z,
                mode='lines',
                line=dict(
                    color=self.style_config['tunnel_color'],
                    width=2
                ),
                name=f'Tunnel Section {i}' if i == 0 else None,
                showlegend=(i == 0)
            )
            traces.append(circle_trace)

        return traces

    def _set_3d_layout(self, fig: go.Figure, title: str):
        """Set 3D layout configuration for plot."""
        fig.update_layout(
            title=title,
            width=self.style_config['figure_width'],
            height=self.style_config['figure_height'],
            scene=dict(
                xaxis_title=self.style_config['axes_labels']['x'],
                yaxis_title=self.style_config['axes_labels']['y'],
                zaxis_title=self.style_config['axes_labels']['z'],
                camera=self._get_camera_settings(),
                bgcolor=self.style_config['background_color']
            ),
            paper_bgcolor=self.style_config['background_color']
        )

    def _get_camera_settings(self) -> Dict[str, Dict[str, float]]:
        """Get camera settings for 3D view."""
        return dict(
            eye=self.style_config['camera_eye'],
            center=self.style_config['camera_center'],
            up=self.style_config['camera_up']
        )

    def create_cross_section_view(self, terrain_mesh: TerrainMesh,
                                tunnel_geometry=None,  # Will be TunnelGeometry when User Story 2 is implemented
                                distance_along_tunnel: float = 0.0) -> go.Figure:
        """
        Create a cross-section view at a specific distance along the tunnel.

        Args:
            terrain_mesh: Terrain mesh
            tunnel_geometry: Tunnel geometry
            distance_along_tunnel: Distance along tunnel centerline

        Returns:
            plotly Figure object
        """
        try:
            # Get cross-section data
            cross_section_data = self._extract_cross_section(
                terrain_mesh, tunnel_geometry, distance_along_tunnel
            )

            # Create figure
            fig = go.Figure()

            # Add terrain cross-section
            if cross_section_data['terrain_points'] is not None:
                terrain_points = cross_section_data['terrain_points']
                fig.add_trace(go.Scatter(
                    x=terrain_points[:, 0],
                    y=terrain_points[:, 1],
                    mode='lines+markers',
                    name='Terrain Profile',
                    line=dict(color='brown', width=3),
                    fill='tonexty'
                ))

            # Add tunnel cross-section
            if cross_section_data['tunnel_points'] is not None:
                tunnel_points = cross_section_data['tunnel_points']
                fig.add_trace(go.Scatter(
                    x=tunnel_points[:, 0],
                    y=tunnel_points[:, 1],
                    mode='lines',
                    name='Tunnel Cross-section',
                    line=dict(color='red', width=2)
                ))

            # Set layout
            fig.update_layout(
                title=f"Cross-Section at {distance_along_tunnel:.1f}m",
                xaxis_title="Distance from tunnel centerline (m)",
                yaxis_title="Elevation (m)",
                width=self.style_config['figure_width'],
                height=self.style_config['figure_height'] // 2,
                showlegend=True
            )

            return fig

        except Exception as e:
            raise VisualizationError(f"Failed to create cross-section view: {e}")

    def _extract_cross_section(self, terrain_mesh: TerrainMesh,
                             tunnel_geometry,  # TunnelGeometry will be available in User Story 2
                             distance: float) -> Dict[str, Any]:
        """Extract cross-section data at given distance."""
        # This is a simplified implementation
        # In a real implementation, you would:
        # 1. Find the point on the tunnel centerline at the given distance
        # 2. Determine the cross-section plane (perpendicular to tunnel)
        # 3. Intersect the terrain mesh with this plane
        # 4. Extract tunnel cross-section geometry

        # For now, return dummy data
        return {
            'terrain_points': None,
            'tunnel_points': None,
            'center_point': np.array([0, 0, 0]),
            'normal_vector': np.array([1, 0, 0])
        }

    def save_plot(self, fig: go.Figure, file_path: Union[str, Path],
                  format: str = 'html', **kwargs) -> None:
        """
        Save plot to file.

        Args:
            fig: plotly Figure to save
            file_path: Output file path
            format: Output format ('html', 'png', 'jpg', 'pdf', 'svg')
            **kwargs: Additional arguments for plotly write_image

        Raises:
            VisualizationError: If save operation fails
        """
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            if format.lower() == 'html':
                fig.write_html(str(file_path), **kwargs)
            else:
                fig.write_image(str(file_path), format=format, **kwargs)

        except Exception as e:
            raise VisualizationError(f"Failed to save plot to {file_path}: {e}")

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

    def create_integrated_scene(self, terrain_mesh: TerrainMesh,
                              tunnel_geometry=None,  # Will be TunnelGeometry when User Story 2 is implemented
                              title: Optional[str] = None) -> go.Figure:
        """
        Create a fully integrated 3D scene with exact same rendering as improved_semicircular_tunnel.py.

        This method creates the identical visualization to improved_semicircular_tunnel.py:
        - Terrain with brown-to-white colorscale and 0.6 opacity
        - Semicircular tunnel with gray color scheme
        - Bottom surface with matching gray color
        - Red centerline with yellow markers
        - Yellow dotted road edge indicators
        - Same camera settings and layout

        Args:
            terrain_mesh: TerrainMesh object to visualize
            tunnel_geometry: Optional TunnelGeometry object to overlay
            title: Optional plot title

        Returns:
            plotly Figure object with integrated terrain+tunnel visualization

        Raises:
            VisualizationError: If scene creation fails
        """
        try:
            # Validate terrain mesh
            if terrain_mesh.vertex_count == 0:
                raise VisualizationError("Terrain mesh has no vertices")

            # Create figure (exact same approach as improved_semicircular_tunnel.py)
            fig = go.Figure()

            # Add terrain (exact same as improved_semicircular_tunnel.py)
            terrain_trace = go.Mesh3d(
                x=terrain_mesh.vertices[:, 0],
                y=terrain_mesh.vertices[:, 1],
                z=terrain_mesh.vertices[:, 2],
                i=[t.vertex_indices[0] for t in terrain_mesh.triangles],
                j=[t.vertex_indices[1] for t in terrain_mesh.triangles],
                k=[t.vertex_indices[2] for t in terrain_mesh.triangles],
                intensity=terrain_mesh.vertices[:, 2],
                colorscale=[[0.0, "brown"], [1.0, "white"]],  # Exact same colorscale
                name='Terrain',
                opacity=0.6,  # Exact same opacity
                showscale=True
            )
            fig.add_trace(terrain_trace)

            # Add improved semicircular tunnel visualization (exact same as improved_semicircular_tunnel.py)
            if tunnel_geometry:
                self.logger.info("Adding improved semicircular tunnel geometry to integrated scene")
                tunnel_traces = self._create_tunnel_mesh_traces(tunnel_geometry)
                self.logger.info(f"Generated {len(tunnel_traces)} tunnel traces")
                for i, trace in enumerate(tunnel_traces):
                    self.logger.info(f"Adding tunnel trace {i+1}/{len(tunnel_traces)}: {trace.__class__.__name__}")
                    fig.add_trace(trace)
            else:
                self.logger.info("No tunnel geometry provided for integrated scene")

            # Set layout with exact same settings as improved_semicircular_tunnel.py
            fig.update_layout(
                title=title or "Improved Semicircular Tunnel with Bottom Support",
                scene=dict(
                    xaxis_title='X (m)',
                    yaxis_title='Y (m)',
                    zaxis_title='Elevation (m)',
                    camera=dict(eye=dict(x=1.5, y=1.5, z=0.5)),  # Exact same camera settings
                    bgcolor='white',
                    aspectmode='data'
                ),
                width=1200,  # Exact same dimensions
                height=800,
                legend=dict(
                    x=0.02,
                    y=0.98,
                    bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='black',
                    borderwidth=1
                )
            )

            return fig

        except Exception as e:
            raise VisualizationError(f"Failed to create integrated scene: {e}")

    def _create_tunnel_mesh_traces(self, tunnel_geometry) -> List[go.Mesh3d]:
        """
        Create mesh traces for tunnel geometry using the exact same approach as improved_semicircular_tunnel.py.

        This method replicates the successful rendering from improved_semicircular_tunnel.py:
        - Semicircular tunnel geometry with flat bottom for vehicles
        - Bottom surface with same color for continuity
        - Gray color scheme for tunnel and bottom surface
        - Enhanced lighting and visual settings
        - Road edge indicators with yellow dotted lines

        Args:
            tunnel_geometry: TunnelGeometry object

        Returns:
            List of plotly mesh traces for tunnel visualization
        """
        import logging
        logger = logging.getLogger(__name__)

        traces = []

        try:
            logger.info("Creating improved semicircular tunnel mesh traces...")

            # Create improved semicircular tunnel geometry (same as improved_semicircular_tunnel.py)
            if hasattr(tunnel_geometry, 'path') and hasattr(tunnel_geometry.path, 'waypoints'):
                waypoints = tunnel_geometry.path.waypoints
                logger.info(f"Found {len(waypoints)} waypoints for semicircular tunnel")

                # Create simple waypoint objects for ImprovedSemicircularTunnelGeometry
                class SimpleWaypoint:
                    def __init__(self, x, y, z, radius):
                        self.x = x
                        self.y = y
                        self.z = z
                        self.radius = radius

                simple_waypoints = []
                for wp in waypoints:
                    simple_waypoints.append(SimpleWaypoint(wp.x, wp.y, wp.elevation, wp.radius))

                # Import and use the same ImprovedSemicircularTunnelGeometry class
                import sys
                import os
                sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

                # Create the improved semicircular tunnel geometry
                from improved_semicircular_tunnel import ImprovedSemicircularTunnelGeometry
                tunnel_geom = ImprovedSemicircularTunnelGeometry(simple_waypoints)

                # Generate tunnel mesh with same parameters as improved_semicircular_tunnel.py
                logger.info("Generating semicircular tunnel mesh...")
                tunnel_vertices = tunnel_geom.get_mesh_vertices(
                    segments_per_section=32,
                    points_per_segment=30
                )
                tunnel_triangles = tunnel_geom.get_mesh_triangles(
                    segments_per_section=32,
                    points_per_segment=30
                )

                # Generate bottom surface mesh
                logger.info("Generating bottom surface mesh...")
                bottom_vertices = tunnel_geom.get_bottom_surface_vertices(points_per_segment=30)
                bottom_triangles = tunnel_geom.get_bottom_surface_triangles(points_per_segment=30)

                logger.info(f"Tunnel mesh: {len(tunnel_vertices)} vertices, {len(tunnel_triangles)} triangles")
                logger.info(f"Bottom surface: {len(bottom_vertices)} vertices, {len(bottom_triangles)} triangles")

                # Add bottom surface first (so it appears behind tunnel)
                if bottom_triangles and len(bottom_triangles) > 0:
                    bottom_array = np.array(bottom_triangles)

                    bottom_trace = go.Mesh3d(
                        x=bottom_vertices[:, 0],
                        y=bottom_vertices[:, 1],
                        z=bottom_vertices[:, 2],
                        i=bottom_array[:, 0],
                        j=bottom_array[:, 1],
                        k=bottom_array[:, 2],
                        color='gray',  # Same color as tunnel
                        name='Bottom Surface',
                        opacity=1.0,
                        showscale=False,
                        flatshading=True,
                        lighting=dict(ambient=0.8, diffuse=0.8, specular=0.3, roughness=0.3)
                    )
                    traces.append(bottom_trace)
                    logger.info(f"Added bottom surface trace")

                # Add semicircular tunnel
                if tunnel_triangles and len(tunnel_triangles) > 0:
                    tunnel_array = np.array(tunnel_triangles)

                    tunnel_trace = go.Mesh3d(
                        x=tunnel_vertices[:, 0],
                        y=tunnel_vertices[:, 1],
                        z=tunnel_vertices[:, 2],
                        i=tunnel_array[:, 0],
                        j=tunnel_array[:, 1],
                        k=tunnel_array[:, 2],
                        color='gray',  # Same color as bottom
                        name='Semicircular Tunnel',
                        opacity=1.0,
                        showscale=False,
                        flatshading=True,
                        lighting=dict(ambient=0.8, diffuse=0.8, specular=0.3, roughness=0.3)
                    )
                    traces.append(tunnel_trace)
                    logger.info(f"Added semicircular tunnel trace")

                # Add centerline with semicircular entrance/exit indicators
                centerline_x = [wp.x for wp in simple_waypoints]
                centerline_y = [wp.y for wp in simple_waypoints]
                centerline_z = [wp.z for wp in simple_waypoints]

                centerline = go.Scatter3d(
                    x=centerline_x,
                    y=centerline_y,
                    z=centerline_z,
                    mode='lines',
                    line=dict(color='red', width=10),
                    name='Vehicle Path',
                    showlegend=False
                )
                traces.append(centerline)

                # Removed entrance/exit markers for cleaner visualization
                logger.info(f"Added centerline trace")

                # Add gray road surface covering entire semicircular cross-section with two-lane markings
                road_surface_traces = self._create_road_surface_with_lanes(simple_waypoints)
                traces.extend(road_surface_traces)
                logger.info(f"Added {len(road_surface_traces)} road surface and lane traces")

                logger.info(f"Total traces created: {len(traces)}")

        except Exception as e:
            logger.error(f"Improved semicircular tunnel mesh creation failed: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to simple representation
            traces.extend(self._create_tunnel_traces(tunnel_geometry))

        return traces

    def create_interactive_view(self, terrain_mesh: TerrainMesh,
                              tunnel_geometry=None) -> go.Figure:  # Will be TunnelGeometry when User Story 2 is implemented
        """
        Create an interactive 3D view with enhanced controls.

        Args:
            terrain_mesh: Terrain mesh to visualize
            tunnel_geometry: Optional tunnel geometry

        Returns:
            plotly Figure object with interactive features
        """
        # Create base plot
        if tunnel_geometry:
            fig = self.create_tunnel_overlay(terrain_mesh, tunnel_geometry)
        else:
            fig = self.create_terrain_plot(terrain_mesh)

        # Add interactive features
        fig.update_layout(
            hovermode='closest',
            clickmode='event+select',
            dragmode='orbit'
        )

        # Add distance measurement tool
        # This would require additional implementation in a full version

        return fig

    def export_scene_to_html(self, fig: go.Figure, include_plotlyjs: bool = True) -> str:
        """
        Export 3D scene to HTML format.

        Args:
            fig: plotly Figure to export
            include_plotlyjs: Whether to include plotly.js library

        Returns:
            HTML string representation of the figure
        """
        try:
            html_string = fig.to_html(
                include_plotlyjs=include_plotlyjs,
                div_id="terrain_tunnel_3d_scene"
            )
            return html_string
        except Exception as e:
            raise VisualizationError(f"Failed to export scene to HTML: {e}")

    def export_scene_to_image(self, fig: go.Figure, filename: str,
                             width: Optional[int] = None, height: Optional[int] = None) -> None:
        """
        Export 3D scene to image format.

        Args:
            fig: plotly Figure to export
            filename: Output filename
            width: Optional image width
            height: Optional image height

        Raises:
            VisualizationError: If export fails
        """
        try:
            export_kwargs = {}
            if width:
                export_kwargs['width'] = width
            if height:
                export_kwargs['height'] = height

            fig.write_image(filename, **export_kwargs)
        except Exception as e:
            raise VisualizationError(f"Failed to export scene to image: {e}")

    def _create_road_lane_markings(self, waypoints) -> List[go.Scatter3d]:
        """
        Create road lane markings for the tunnel bottom surface.

        This method creates:
        - Center lane marking (dashed white line)
        - Side lane markings (solid white lines)
        - Arrow markings at entrance/exit

        Args:
            waypoints: List of tunnel waypoints with x, y, z, radius

        Returns:
            List of plotly Scatter3d traces representing lane markings
        """
        traces = []

        if len(waypoints) < 2:
            return traces

        try:
            import logging
            logger = logging.getLogger(__name__)

            # 1. Center line (red solid line down the middle for tunnel alignment reference)
            center_line_x = [wp.x for wp in waypoints]
            center_line_y = [wp.y for wp in waypoints]
            center_line_z = [wp.z for wp in waypoints]

            center_line = go.Scatter3d(
                x=center_line_x,
                y=center_line_y,
                z=center_line_z,
                mode='lines',
                line=dict(
                    color='red',
                    width=4,
                    dash='solid'  # Solid red line for clear tunnel center reference
                ),
                name='Center Line',
                showlegend=True
            )
            traces.append(center_line)
            logger.info("Added center lane marking")

            # 2. Side lane markings (solid white lines at 1/3 and 2/3 positions)
            lane_positions = [0.33, 0.67]  # 1/3 and 2/3 of tunnel width
            lane_names = ['Left Lane Marking', 'Right Lane Marking']

            for i, lane_pos in enumerate(lane_positions):
                side_line_x = []
                side_line_y = []
                side_line_z = []

                for wp in waypoints:
                    side_line_x.append(wp.x)
                    # Calculate offset from center (tunnel center is at wp.y)
                    lane_offset = (lane_pos - 0.5) * 2 * wp.radius  # Convert to actual offset
                    side_line_y.append(wp.y + lane_offset)
                    side_line_z.append(wp.z)

                side_lane = go.Scatter3d(
                    x=side_line_x,
                    y=side_line_y,
                    z=side_line_z,
                    mode='lines',
                    line=dict(
                        color='white',
                        width=2,
                        dash='solid'  # Solid line for side lanes
                    ),
                    name=lane_names[i],
                    showlegend=True
                )
                traces.append(side_lane)
                logger.info(f"Added {lane_names[i]}")

            # 3. Directional arrows at entrance and exit
            if len(waypoints) >= 2:
                # Entrance arrow (at first waypoint)
                entrance_arrow = self._create_directional_arrow(
                    waypoints[0], waypoints[1], 'Entrance'
                )
                if entrance_arrow:
                    traces.append(entrance_arrow)
                    logger.info("Added entrance arrow")

                # Exit arrow (at last waypoint)
                exit_arrow = self._create_directional_arrow(
                    waypoints[-1], waypoints[-2], 'Exit'
                )
                if exit_arrow:
                    traces.append(exit_arrow)
                    logger.info("Added exit arrow")

            logger.info(f"Created {len(traces)} road lane marking traces")

        except Exception as e:
            logger.error(f"Failed to create road lane markings: {e}")

        return traces

    def _create_directional_arrow(self, current_wp, next_wp, arrow_name: str) -> Optional[go.Scatter3d]:
        """
        Create a directional arrow to show traffic flow direction.

        Args:
            current_wp: Current waypoint position
            next_wp: Next waypoint to determine direction
            arrow_name: Name for the legend ('Entrance' or 'Exit')

        Returns:
            plotly Scatter3d trace representing an arrow, or None if creation fails
        """
        try:
            # Calculate direction vector
            dx = next_wp.x - current_wp.x
            dy = next_wp.y - current_wp.y
            dz = next_wp.z - current_wp.z

            # Normalize direction vector
            length = np.sqrt(dx**2 + dy**2 + dz**2)
            if length == 0:
                return None

            dx, dy, dz = dx/length, dy/length, dz/length

            # Arrow parameters
            arrow_length = current_wp.radius * 0.8  # 80% of tunnel radius
            arrow_head_length = current_wp.radius * 0.2  # 20% of tunnel radius
            arrow_width = current_wp.radius * 0.1   # 10% of tunnel radius

            # Arrow base point
            base_x = current_wp.x
            base_y = current_wp.y
            base_z = current_wp.z

            # Arrow tip point
            tip_x = base_x + dx * arrow_length
            tip_y = base_y + dy * arrow_length
            tip_z = base_z + dz * arrow_length

            # Create arrow shaft
            arrow_shaft = go.Scatter3d(
                x=[base_x, tip_x],
                y=[base_y, tip_y],
                z=[base_z, tip_z],
                mode='lines',
                line=dict(
                    color='white',
                    width=4
                ),
                name=f'{arrow_name} Arrow',
                showlegend=True
            )

            return arrow_shaft

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create directional arrow: {e}")
            return None

    def _create_semicircular_marker(self, waypoint, marker_name: str) -> Optional[go.Scatter3d]:
        """
        Create a semicircular marker to match tunnel cross-section shape.

        This creates a semicircular marker (not filled) at the tunnel entrance/exit
        to clearly indicate the tunnel opening shape.

        Args:
            waypoint: Waypoint with x, y, z, radius
            marker_name: Name for the marker legend

        Returns:
            plotly Scatter3d trace representing a semicircular marker
        """
        try:
            # Create semicircle points (top half only)
            angles = np.linspace(0, np.pi, 20)  # 0 to 180 degrees
            semicircle_x = []
            semicircle_y = []
            semicircle_z = []

            for angle in angles:
                # Calculate semicircle points in the vertical plane
                x = waypoint.x
                y = waypoint.y + waypoint.radius * np.cos(angle)
                z = waypoint.z + waypoint.radius * np.sin(angle)

                semicircle_x.append(x)
                semicircle_y.append(y)
                semicircle_z.append(z)

            # Add closing point to complete the semicircle
            semicircle_x.append(x)
            semicircle_y.append(waypoint.y - waypoint.radius)
            semicircle_z.append(waypoint.z)

            semicircle_marker = go.Scatter3d(
                x=semicircle_x,
                y=semicircle_y,
                z=semicircle_z,
                mode='lines',
                line=dict(
                    color='orange',
                    width=3
                ),
                name=marker_name,
                showlegend=True
            )

            return semicircle_marker

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create semicircular marker: {e}")
            return None

    def _create_road_surface_with_lanes(self, waypoints) -> List[go.Scatter3d]:
        """
        Create continuous gray road surface along entire tunnel length
        with four-lane two-way road markings.

        This method creates:
        - Continuous gray road surface along tunnel length
        - Four-lane road markings (solid white lines with markers)
        - Center lane divider (dashed yellow line)
        - Enhanced visibility throughout tunnel

        Args:
            waypoints: List of tunnel waypoints with x, y, z, radius

        Returns:
            List of plotly Scatter3d traces representing road surface and lanes
        """
        import logging
        logger = logging.getLogger(__name__)
        traces = []

        if len(waypoints) < 2:
            return traces

        try:
            # 1. Create continuous gray road surface along entire tunnel length
            # Create road surface for each segment between waypoints
            for segment_idx in range(len(waypoints) - 1):
                wp1 = waypoints[segment_idx]
                wp2 = waypoints[segment_idx + 1]

                # Create multiple road surface lines across tunnel width for this segment
                num_lines = 6  # Multiple parallel lines for better visibility
                for line_idx in range(num_lines):
                    t = line_idx / (num_lines - 1)  # 0 to 1 across width

                    # Interpolate position along segment
                    x_pos = wp1.x + 0.5 * (wp2.x - wp1.x)
                    y_pos1 = wp1.y - wp1.radius + 2 * wp1.radius * t  # Left edge
                    y_pos2 = wp1.y - wp1.radius + 2 * wp2.radius * t  # Right edge (using wp2 radius)
                    z_pos = wp1.z - wp1.radius * 0.1  # Slightly above bottom

                    # Create road surface line from left edge to right edge
                    road_surface = go.Scatter3d(
                        x=[x_pos, x_pos],
                        y=[y_pos1, y_pos2],
                        z=[z_pos, z_pos],
                        mode='lines',
                        line=dict(
                            color='gray',
                            width=12  # Very thick for high visibility
                        ),
                        name=f'Road Surface {segment_idx+1}' if segment_idx == 0 and line_idx == 0 else None,
                        showlegend=False
                    )
                    traces.append(road_surface)

            # 2. Create four-lane road markings for two-way traffic
            # Four lanes: Lane 1, Lane 2 | Lane 3, Lane 4
            # Lane boundaries at: -radius*0.5, -radius*0.167, radius*0.167, radius*0.5
            # Center divider at y=0 (dashed yellow line)
            lane_positions = [-0.5, -0.167, 0.167, 0.5]  # Four lane positions
            lane_names = ['Lane 1 Edge', 'Lane 2 Edge', 'Lane 3 Edge', 'Lane 4 Edge']

            # Create continuous lane edge markings (solid white lines with markers)
            for j, lane_pos in enumerate(lane_positions):
                # Create continuous lane marking line along entire tunnel length
                lane_x = [wp.x for wp in waypoints]
                lane_y = [wp.y + lane_pos * wp.radius for wp in waypoints]
                lane_z = [wp.z - wp.radius * 0.1 for wp in waypoints]  # Slightly above road surface

                lane_marking = go.Scatter3d(
                    x=lane_x,
                    y=lane_y,
                    z=lane_z,
                    mode='lines+markers',  # Use markers for better visibility
                    line=dict(
                        color='white',
                        width=4,
                        dash='solid'  # Solid line for lane edges
                    ),
                    marker=dict(
                        symbol='circle',
                        size=5,
                        color='white',
                        line=dict(width=1, color='white')
                    ),
                    name=f'{lane_names[j]}',
                    showlegend=(j < 2)  # Show legend for first two lanes only
                )
                traces.append(lane_marking)

  
            logger.info(f"Created {len(traces)} continuous road surface and four-lane markings")

        except Exception as e:
            logger.error(f"Failed to create continuous road surface: {e}")

        return traces

  