"""
Export service for Terrain Tunneling Calculator.

This service handles exporting terrain meshes, tunnel geometry, and visualizations
to various formats including STL, OBJ, PNG, SVG, and CSV for User Story 4.
"""

import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
import logging
import csv
from datetime import datetime

from models.terrain_mesh import TerrainMesh, Triangle
from models.tunnel_geometry import TunnelGeometry
from models.contour_data import ContourData
from utils.exceptions import ExportError


class ExportService:
    """Service for exporting terrain and tunnel data to various formats."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the export service.

        Args:
            config: Optional export configuration dictionary
        """
        # Default export configuration
        self.config = {
            'precision': 6,  # Decimal precision for numeric values
            'scale_factor': 1.0,  # Scale factor for exports
            'unit_system': 'meters',  # meters or feet
            'include_metadata': True,  # Include metadata in exports
            'compression': False,  # Enable compression for large files
            'export_directory': 'exports',  # Default export directory
        }

        # Update with provided config
        if config:
            self.config.update(config)

        self.logger = logging.getLogger(__name__)

    def export_stl(self,
                   terrain_mesh: TerrainMesh,
                   file_path: Union[str, Path],
                   tunnel_geometry: Optional[TunnelGeometry] = None) -> str:
        """
        Export terrain mesh and tunnel to STL format.

        Args:
            terrain_mesh: Terrain mesh to export
            tunnel_geometry: Optional tunnel geometry to export
            file_path: Output file path

        Returns:
            Path to exported file

        Raises:
            ExportError: If export fails
        """
        try:
            file_path = Path(file_path)
            if file_path.suffix.lower() != '.stl':
                file_path = file_path.with_suffix('.stl')

            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create STL content
            stl_content = self._create_stl_content(terrain_mesh, tunnel_geometry)

            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(stl_content)

            self.logger.info(f"STL export successful: {file_path}")
            return str(file_path)

        except Exception as e:
            raise ExportError(f"Failed to export STL: {e}")

    def _create_stl_content(self,
                           terrain_mesh: TerrainMesh,
                           tunnel_geometry: Optional[TunnelGeometry] = None) -> str:
        """Create STL file content from terrain and tunnel data."""
        lines = []

        # STL header
        lines.append("solid terrain_tunnel_model")

        # Export terrain triangles
        vertices = terrain_mesh.vertices * self.config['scale_factor']

        for triangle in terrain_mesh.triangles:
            if len(triangle.vertex_indices) == 3:
                v0, v1, v2 = triangle.vertex_indices

                # Get triangle vertices
                p0 = vertices[v0]
                p1 = vertices[v1]
                p2 = vertices[v2]

                # Calculate normal vector
                normal = self._calculate_triangle_normal(p0, p1, p2)

                # Add triangle to STL
                lines.append(f"  facet normal {normal[0]:.6e} {normal[1]:.6e} {normal[2]:.6e}")
                lines.append("    outer loop")
                lines.append(f"      vertex {p0[0]:.6e} {p0[1]:.6e} {p0[2]:.6e}")
                lines.append(f"      vertex {p1[0]:.6e} {p1[1]:.6e} {p1[2]:.6e}")
                lines.append(f"      vertex {p2[0]:.6e} {p2[1]:.6e} {p2[2]:.6e}")
                lines.append("    endloop")
                lines.append("  endfacet")

        # Export tunnel triangles if available
        if tunnel_geometry and hasattr(tunnel_geometry, 'get_mesh_vertices'):
            tunnel_vertices = tunnel_geometry.get_mesh_vertices()
            tunnel_triangles = tunnel_geometry.get_mesh_triangles()

            if tunnel_vertices is not None and tunnel_triangles is not None:
                tunnel_vertices = tunnel_vertices * self.config['scale_factor']

                for triangle in tunnel_triangles:
                    if hasattr(triangle, 'vertex_indices') and len(triangle.vertex_indices) == 3:
                        v0, v1, v2 = triangle.vertex_indices

                        p0 = tunnel_vertices[v0]
                        p1 = tunnel_vertices[v1]
                        p2 = tunnel_vertices[v2]

                        normal = self._calculate_triangle_normal(p0, p1, p2)

                        lines.append(f"  facet normal {normal[0]:.6e} {normal[1]:.6e} {normal[2]:.6e}")
                        lines.append("    outer loop")
                        lines.append(f"      vertex {p0[0]:.6e} {p0[1]:.6e} {p0[2]:.6e}")
                        lines.append(f"      vertex {p1[0]:.6e} {p1[1]:.6e} {p1[2]:.6e}")
                        lines.append(f"      vertex {p2[0]:.6e} {p2[1]:.6e} {p2[2]:.6e}")
                        lines.append("    endloop")
                        lines.append("  endfacet")

        lines.append("endsolid terrain_tunnel_model")
        return '\n'.join(lines)

    def export_obj(self,
                   terrain_mesh: TerrainMesh,
                   file_path: Union[str, Path],
                   tunnel_geometry: Optional[TunnelGeometry] = None) -> str:
        """
        Export terrain mesh and tunnel to OBJ format.

        Args:
            terrain_mesh: Terrain mesh to export
            tunnel_geometry: Optional tunnel geometry to export
            file_path: Output file path

        Returns:
            Path to exported file

        Raises:
            ExportError: If export fails
        """
        try:
            file_path = Path(file_path)
            if file_path.suffix.lower() != '.obj':
                file_path = file_path.with_suffix('.obj')

            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create OBJ content
            obj_content = self._create_obj_content(terrain_mesh, tunnel_geometry)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(obj_content)

            self.logger.info(f"OBJ export successful: {file_path}")
            return str(file_path)

        except Exception as e:
            raise ExportError(f"Failed to export OBJ: {e}")

    def _create_obj_content(self,
                           terrain_mesh: TerrainMesh,
                           tunnel_geometry: Optional[TunnelGeometry] = None) -> str:
        """Create OBJ file content from terrain and tunnel data."""
        lines = []

        # OBJ header comment
        lines.append("# OBJ file exported by Terrain Tunneling Calculator")
        lines.append(f"# Exported on: {datetime.now().isoformat()}")
        lines.append(f"# Scale factor: {self.config['scale_factor']}")
        lines.append(f"# Unit system: {self.config['unit_system']}")
        lines.append("")

        # Scale vertices
        scale = self.config['scale_factor']
        vertices = terrain_mesh.vertices * scale

        # Export terrain vertices
        lines.append("# Terrain vertices")
        vertex_count = 1  # OBJ indexing starts from 1
        for i, vertex in enumerate(vertices):
            lines.append(f"v {vertex[0]:.{self.config['precision']}f} "
                        f"{vertex[1]:.{self.config['precision']}f} "
                        f"{vertex[2]:.{self.config['precision']}f}")

        # Export terrain faces
        lines.append("# Terrain faces")
        for triangle in terrain_mesh.triangles:
            if len(triangle.vertex_indices) == 3:
                v0, v1, v2 = triangle.vertex_indices
                lines.append(f"f {v0+1} {v1+1} {v2+1}")

        # Export tunnel if available
        if tunnel_geometry and hasattr(tunnel_geometry, 'get_mesh_vertices'):
            tunnel_vertices = tunnel_geometry.get_mesh_vertices()
            tunnel_triangles = tunnel_geometry.get_mesh_triangles()

            if tunnel_vertices is not None and tunnel_triangles is not None:
                tunnel_vertices = tunnel_vertices * scale
                tunnel_vertex_offset = len(vertices)

                lines.append("")
                lines.append("# Tunnel vertices")
                for i, vertex in enumerate(tunnel_vertices):
                    lines.append(f"v {vertex[0]:.{self.config['precision']}f} "
                                f"{vertex[1]:.{self.config['precision']}f} "
                                f"{vertex[2]:.{self.config['precision']}f}")

                lines.append("# Tunnel faces")
                for triangle in tunnel_triangles:
                    if hasattr(triangle, 'vertex_indices') and len(triangle.vertex_indices) == 3:
                        v0, v1, v2 = triangle.vertex_indices
                        lines.append(f"f {tunnel_vertex_offset + v0 + 1} "
                                    f"{tunnel_vertex_offset + v1 + 1} "
                                    f"{tunnel_vertex_offset + v2 + 1}")

        return '\n'.join(lines)

    def export_images(self,
                      figure: go.Figure,
                      file_path: Union[str, Path],
                      formats: List[str] = None) -> List[str]:
        """
        Export plotly figure to image formats (PNG, SVG).

        Args:
            figure: Plotly figure to export
            file_path: Base file path (without extension)
            formats: List of formats to export ('png', 'svg')

        Returns:
            List of exported file paths

        Raises:
            ExportError: If export fails
        """
        if formats is None:
            formats = ['png', 'svg']

        try:
            file_path = Path(file_path)
            exported_files = []

            for format_type in formats:
                format_type = format_type.lower().lstrip('.')
                output_path = file_path.with_suffix(f'.{format_type}')

                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Export using plotly
                if format_type == 'png':
                    figure.write_image(
                        str(output_path),
                        width=1200,
                        height=800,
                        scale=2
                    )
                elif format_type == 'svg':
                    figure.write_image(str(output_path))
                elif format_type == 'pdf':
                    figure.write_image(str(output_path))
                elif format_type == 'html':
                    figure.write_html(str(output_path), include_plotlyjs=True)
                else:
                    self.logger.warning(f"Unsupported image format: {format_type}")
                    continue

                exported_files.append(str(output_path))
                self.logger.info(f"Image export successful: {output_path}")

            return exported_files

        except Exception as e:
            raise ExportError(f"Failed to export images: {e}")

    def export_csv(self,
                   data: Union[TerrainMesh, ContourData, List[Dict[str, Any]]],
                   file_path: Union[str, Path],
                   data_type: str = 'auto') -> str:
        """
        Export data to CSV format.

        Args:
            data: Data to export (TerrainMesh, ContourData, or list of dictionaries)
            file_path: Output file path
            data_type: Type of data ('terrain', 'contour', 'animation', 'auto')

        Returns:
            Path to exported file

        Raises:
            ExportError: If export fails
        """
        try:
            file_path = Path(file_path)
            if file_path.suffix.lower() != '.csv':
                file_path = file_path.with_suffix('.csv')

            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Determine data type if auto
            if data_type == 'auto':
                if isinstance(data, TerrainMesh):
                    data_type = 'terrain'
                elif isinstance(data, ContourData):
                    data_type = 'contour'
                elif isinstance(data, list) and len(data) > 0:
                    data_type = 'generic'
                else:
                    data_type = 'generic'

            # Export based on data type
            if data_type == 'terrain':
                self._export_terrain_csv(data, file_path)
            elif data_type == 'contour':
                self._export_contour_csv(data, file_path)
            elif data_type == 'animation':
                self._export_animation_csv(data, file_path)
            else:
                self._export_generic_csv(data, file_path)

            self.logger.info(f"CSV export successful: {file_path}")
            return str(file_path)

        except Exception as e:
            raise ExportError(f"Failed to export CSV: {e}")

    def _export_terrain_csv(self, terrain_mesh: TerrainMesh, file_path: Path):
        """Export terrain mesh data to CSV."""
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            # Write vertices
            csvfile.write("# Terrain Mesh Vertices\n")
            csvfile.write("# X,Y,Z,Elevation\n")

            writer = csv.writer(csvfile)
            vertices = terrain_mesh.vertices * self.config['scale_factor']

            for i, vertex in enumerate(vertices):
                writer.writerow([
                    f"{vertex[0]:.{self.config['precision']}f}",
                    f"{vertex[1]:.{self.config['precision']}f}",
                    f"{vertex[2]:.{self.config['precision']}f}",
                    f"{terrain_mesh.elevation_data[i]:.{self.config['precision']}f}"
                ])

            # Write triangles
            csvfile.write("\n# Terrain Mesh Triangles\n")
            csvfile.write("# Vertex1_Index,Vertex2_Index,Vertex3_Index\n")

            for triangle in terrain_mesh.triangles:
                if len(triangle.vertex_indices) == 3:
                    writer.writerow(triangle.vertex_indices)

    def _export_contour_csv(self, contour_data: ContourData, file_path: Path):
        """Export contour data to CSV."""
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            # Write metadata
            csvfile.write("# Contour Data Export\n")
            csvfile.write(f"# Name: {contour_data.metadata.name}\n")
            csvfile.write(f"# Units: {contour_data.metadata.units}\n")
            csvfile.write(f"# Coordinate System: {contour_data.coordinate_system.value}\n")
            csvfile.write(f"# Export Date: {datetime.now().isoformat()}\n")
            csvfile.write("\n")

            writer = csv.writer(csvfile)

            # Write contour lines
            csvfile.write("# Contour Lines\n")
            csvfile.write("# Elevation,X,Y\n")

            for contour in contour_data.contours:
                for point in contour.points:
                    writer.writerow([
                        f"{contour.elevation:.{self.config['precision']}f}",
                        f"{point[0]:.{self.config['precision']}f}",
                        f"{point[1]:.{self.config['precision']}f}"
                    ])

    def _export_animation_csv(self, animation_data: List[Dict[str, Any]], file_path: Path):
        """Export animation frame data to CSV."""
        if not animation_data:
            return

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            csvfile.write("# Animation Data Export\n")
            csvfile.write(f"# Export Date: {datetime.now().isoformat()}\n")
            csvfile.write("# Scale Factor: {self.config['scale_factor']}\n")
            csvfile.write("\n")

            writer = csv.writer(csvfile)

            # Write header
            csvfile.write("# Frame,Timestamp,Car_X,Car_Y,Car_Z,Camera_X,Camera_Y,Camera_Z,"
                         "Car_Orient_X,Car_Orient_Y,Car_Orient_Z,Tunnel_Progress\n")

            # Write frame data
            for frame in animation_data:
                if isinstance(frame, dict):
                    writer.writerow([
                        frame.get('frame_number', ''),
                        frame.get('timestamp', ''),
                        f"{frame.get('car_position', [0, 0, 0])[0]:.{self.config['precision']}f}",
                        f"{frame.get('car_position', [0, 0, 0])[1]:.{self.config['precision']}f}",
                        f"{frame.get('car_position', [0, 0, 0])[2]:.{self.config['precision']}f}",
                        f"{frame.get('camera_position', [0, 0, 0])[0]:.{self.config['precision']}f}",
                        f"{frame.get('camera_position', [0, 0, 0])[1]:.{self.config['precision']}f}",
                        f"{frame.get('camera_position', [0, 0, 0])[2]:.{self.config['precision']}f}",
                        f"{frame.get('car_orientation', [0, 0, 0])[0]:.{self.config['precision']}f}",
                        f"{frame.get('car_orientation', [0, 0, 0])[1]:.{self.config['precision']}f}",
                        f"{frame.get('car_orientation', [0, 0, 0])[2]:.{self.config['precision']}f}",
                        f"{frame.get('tunnel_progress', 0):.{self.config['precision']}f}"
                    ])

    def _export_generic_csv(self, data: List[Dict[str, Any]], file_path: Path):
        """Export generic tabular data to CSV."""
        if not data:
            return

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            csvfile.write("# Generic Data Export\n")
            csvfile.write(f"# Export Date: {datetime.now().isoformat()}\n")
            csvfile.write("\n")

            # Get all unique keys from all dictionaries
            all_keys = set()
            for item in data:
                all_keys.update(item.keys())

            fieldnames = sorted(all_keys)
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for item in data:
                # Convert numpy arrays to strings for CSV compatibility
                row = {}
                for key, value in item.items():
                    if isinstance(value, np.ndarray):
                        row[key] = ','.join(map(str, value))
                    else:
                        row[key] = value
                writer.writerow(row)

    def _calculate_triangle_normal(self, p0: np.ndarray, p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
        """Calculate normal vector for a triangle."""
        edge1 = p1 - p0
        edge2 = p2 - p0
        normal = np.cross(edge1, edge2)

        # Normalize
        norm = np.linalg.norm(normal)
        if norm > 0:
            normal = normal / norm

        return normal

    def get_supported_formats(self) -> Dict[str, List[str]]:
        """Get dictionary of supported export formats by data type."""
        return {
            'terrain_mesh': ['stl', 'obj', 'csv'],
            'tunnel_geometry': ['stl', 'obj'],
            'visualization': ['png', 'svg', 'pdf', 'html'],
            'animation': ['csv', 'html'],
            'contour_data': ['csv']
        }

    def validate_export_path(self, file_path: Union[str, Path],
                            data_type: str) -> bool:
        """
        Validate export path for given data type.

        Args:
            file_path: Path to validate
            data_type: Type of data being exported

        Returns:
            True if path is valid
        """
        file_path = Path(file_path)

        # Check if file path is writable
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            test_file = file_path.parent / '.write_test'
            test_file.touch()
            test_file.unlink()
        except Exception:
            return False

        # Check if extension is supported for data type
        supported_formats = self.get_supported_formats().get(data_type, [])
        if file_path.suffix.lower().lstrip('.') not in supported_formats:
            return False

        return True