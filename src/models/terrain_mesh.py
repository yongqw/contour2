"""
Terrain mesh models for Terrain Tunneling Calculator.

This module defines the data structures for representing 3D terrain meshes
generated from contour data through triangulation.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
import numpy as np


@dataclass
class Triangle:
    """Triangle face in the terrain mesh."""
    vertex_indices: List[int]  # Indices into the vertices array
    normal: Optional[np.ndarray] = None  # Face normal vector

    def __post_init__(self):
        """Validate triangle after initialization."""
        if len(self.vertex_indices) != 3:
            raise ValueError("Triangle must have exactly 3 vertex indices")

        # Ensure indices are non-negative integers
        for idx in self.vertex_indices:
            if not isinstance(idx, int) or idx < 0:
                raise ValueError(f"Invalid vertex index: {idx}")

    def get_area(self, vertices: np.ndarray) -> float:
        """
        Calculate the area of the triangle.

        Args:
            vertices: Array of vertex positions (n, 3)

        Returns:
            Triangle area
        """
        if len(self.vertex_indices) != 3:
            return 0.0

        v0, v1, v2 = vertices[self.vertex_indices]

        # Calculate area using cross product
        edge1 = v1 - v0
        edge2 = v2 - v0
        cross = np.cross(edge1, edge2)
        area = 0.5 * np.linalg.norm(cross)

        return float(area)

    def get_normal(self, vertices: np.ndarray) -> np.ndarray:
        """
        Calculate the normal vector of the triangle.

        Args:
            vertices: Array of vertex positions (n, 3)

        Returns:
            Normalized normal vector
        """
        if self.normal is not None:
            return self.normal

        if len(self.vertex_indices) != 3:
            return np.array([0.0, 0.0, 1.0])

        v0, v1, v2 = vertices[self.vertex_indices]

        # Calculate normal using cross product
        edge1 = v1 - v0
        edge2 = v2 - v0
        normal = np.cross(edge1, edge2)

        # Normalize
        norm = np.linalg.norm(normal)
        if norm > 1e-10:
            normal = normal / norm
        else:
            normal = np.array([0.0, 0.0, 1.0])

        self.normal = normal
        return normal

    def get_centroid(self, vertices: np.ndarray) -> np.ndarray:
        """
        Calculate the centroid of the triangle.

        Args:
            vertices: Array of vertex positions (n, 3)

        Returns:
            Centroid position
        """
        if len(self.vertex_indices) != 3:
            return np.array([0.0, 0.0, 0.0])

        triangle_vertices = vertices[self.vertex_indices]
        return np.mean(triangle_vertices, axis=0)


@dataclass
class TerrainMesh:
    """3D terrain mesh generated from contour data."""
    vertices: np.ndarray  # Shape: (n, 3) for [x, y, z] coordinates
    triangles: List[Triangle]
    vertex_colors: Optional[np.ndarray] = None  # Optional vertex colors (n, 3) or (n, 4)
    vertex_normals: Optional[np.ndarray] = None  # Optional vertex normals (n, 3)
    texture_coordinates: Optional[np.ndarray] = None  # Optional UV coordinates (n, 2)

    # Computed properties
    _vertex_count: Optional[int] = field(default=None, init=False)
    _triangle_count: Optional[int] = field(default=None, init=False)
    _bounds: Optional[Tuple[float, float, float, float, float, float]] = field(default=None, init=False)

    def __post_init__(self):
        """Validate mesh after initialization."""
        if self.vertices.shape[1] != 3:
            raise ValueError("Vertices must be a 2D array with shape (n, 3)")

        # Validate triangle indices
        vertex_count = len(self.vertices)
        for triangle in self.triangles:
            for idx in triangle.vertex_indices:
                if idx >= vertex_count:
                    raise ValueError(f"Triangle vertex index {idx} exceeds vertex count {vertex_count}")

        # Compute initial properties
        self._vertex_count = len(self.vertices)
        self._triangle_count = len(self.triangles)
        self._bounds = self._calculate_bounds()

    @property
    def vertex_count(self) -> int:
        """Get the number of vertices in the mesh."""
        return self._vertex_count or len(self.vertices)

    @property
    def triangle_count(self) -> int:
        """Get the number of triangles in the mesh."""
        return self._triangle_count or len(self.triangles)

    @property
    def bounds(self) -> Tuple[float, float, float, float, float, float]:
        """
        Get the bounding box of the mesh.

        Returns:
            Tuple of (min_x, max_x, min_y, max_y, min_z, max_z)
        """
        if self._bounds is None:
            self._bounds = self._calculate_bounds()
        return self._bounds

    def _calculate_bounds(self) -> Tuple[float, float, float, float, float, float]:
        """Calculate the bounding box of the mesh."""
        if len(self.vertices) == 0:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        min_coords = np.min(self.vertices, axis=0)
        max_coords = np.max(self.vertices, axis=0)

        return (
            float(min_coords[0]), float(max_coords[0]),  # x bounds
            float(min_coords[1]), float(max_coords[1]),  # y bounds
            float(min_coords[2]), float(max_coords[2])   # z bounds
        )

    def get_total_area(self) -> float:
        """
        Calculate the total surface area of the mesh.

        Returns:
            Total surface area
        """
        total_area = 0.0
        for triangle in self.triangles:
            total_area += triangle.get_area(self.vertices)
        return total_area

    def get_average_elevation(self) -> float:
        """
        Calculate the average elevation of the mesh.

        Returns:
            Average elevation (z-coordinate)
        """
        if len(self.vertices) == 0:
            return 0.0
        return float(np.mean(self.vertices[:, 2]))

    def get_elevation_range(self) -> Tuple[float, float]:
        """
        Get the minimum and maximum elevation.

        Returns:
            Tuple of (min_elevation, max_elevation)
        """
        if len(self.vertices) == 0:
            return 0.0, 0.0

        min_z = float(np.min(self.vertices[:, 2]))
        max_z = float(np.max(self.vertices[:, 2]))
        return min_z, max_z

    def compute_vertex_normals(self) -> np.ndarray:
        """
        Compute vertex normals by averaging adjacent triangle normals.

        Returns:
            Array of vertex normals (n, 3)
        """
        if self.vertex_normals is not None:
            return self.vertex_normals

        # Initialize normals array
        normals = np.zeros_like(self.vertices)
        counts = np.zeros(len(self.vertices))

        # Accumulate triangle normals
        for triangle in self.triangles:
            triangle_normal = triangle.get_normal(self.vertices)
            triangle_area = triangle.get_area(self.vertices)

            # Weight normals by triangle area
            for idx in triangle.vertex_indices:
                normals[idx] += triangle_normal * triangle_area
                counts[idx] += 1.0

        # Normalize normals
        for i in range(len(normals)):
            if counts[i] > 0:
                normals[i] /= counts[i]
                norm = np.linalg.norm(normals[i])
                if norm > 1e-10:
                    normals[i] /= norm
                else:
                    normals[i] = np.array([0.0, 0.0, 1.0])

        self.vertex_normals = normals
        return normals

    def get_triangle_at_point(self, x: float, y: float) -> Optional[Triangle]:
        """
        Find the triangle that contains the given 2D point.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Triangle containing the point, or None if no triangle found
        """
        point = np.array([x, y])

        for triangle in self.triangles:
            # Get triangle vertices projected to 2D
            triangle_vertices = self.vertices[triangle.vertex_indices][:, :2]

            # Use barycentric coordinates to check if point is inside triangle
            if self._point_in_triangle_2d(point, triangle_vertices):
                return triangle

        return None

    def _point_in_triangle_2d(self, point: np.ndarray, triangle_vertices: np.ndarray) -> bool:
        """
        Check if a 2D point is inside a triangle using barycentric coordinates.

        Args:
            point: 2D point to check
            triangle_vertices: 2D triangle vertices (3, 2)

        Returns:
            True if point is inside triangle
        """
        v0 = triangle_vertices[2] - triangle_vertices[0]
        v1 = triangle_vertices[1] - triangle_vertices[0]
        v2 = point - triangle_vertices[0]

        # Compute dot products
        dot00 = np.dot(v0, v0)
        dot01 = np.dot(v0, v1)
        dot02 = np.dot(v0, v2)
        dot11 = np.dot(v1, v1)
        dot12 = np.dot(v1, v2)

        # Compute barycentric coordinates
        inv_denom = 1.0 / (dot00 * dot11 - dot01 * dot01) if (dot00 * dot11 - dot01 * dot01) != 0 else 0
        if inv_denom == 0:
            return False

        u = (dot11 * dot02 - dot01 * dot12) * inv_denom
        v = (dot00 * dot12 - dot01 * dot02) * inv_denom

        # Check if point is in triangle
        return (u >= 0) and (v >= 0) and (u + v <= 1)

    def get_elevation_at_point(self, x: float, y: float) -> Optional[float]:
        """
        Get interpolated elevation at a 2D point.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Interpolated elevation, or None if point is outside mesh
        """
        triangle = self.get_triangle_at_point(x, y)
        if triangle is None:
            return None

        # Get triangle vertices
        triangle_vertices = self.vertices[triangle.vertex_indices]

        # Use barycentric interpolation for elevation
        return self._interpolate_elevation(x, y, triangle_vertices)

    def _interpolate_elevation(self, x: float, y: float, triangle_vertices: np.ndarray) -> float:
        """
        Interpolate elevation at a point within a triangle.

        Args:
            x: X coordinate
            y: Y coordinate
            triangle_vertices: Triangle vertices (3, 3)

        Returns:
            Interpolated elevation
        """
        # Project to 2D for barycentric coordinates
        points_2d = triangle_vertices[:, :2]
        point_2d = np.array([x, y])

        v0 = points_2d[2] - points_2d[0]
        v1 = points_2d[1] - points_2d[0]
        v2 = point_2d - points_2d[0]

        dot00 = np.dot(v0, v0)
        dot01 = np.dot(v0, v1)
        dot02 = np.dot(v0, v2)
        dot11 = np.dot(v1, v1)
        dot12 = np.dot(v1, v2)

        inv_denom = 1.0 / (dot00 * dot11 - dot01 * dot01) if (dot00 * dot11 - dot01 * dot01) != 0 else 1.0

        u = (dot11 * dot02 - dot01 * dot12) * inv_denom
        v = (dot00 * dot12 - dot01 * dot02) * inv_denom
        w = 1.0 - u - v

        # Interpolate elevation
        elevations = triangle_vertices[:, 2]
        interpolated_elevation = w * elevations[0] + u * elevations[1] + v * elevations[2]

        return float(interpolated_elevation)

    def validate_mesh(self) -> Tuple[bool, List[str]]:
        """
        Validate mesh integrity.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check for degenerate triangles
        for i, triangle in enumerate(self.triangles):
            area = triangle.get_area(self.vertices)
            if area < 1e-10:
                issues.append(f"Triangle {i} has near-zero area (degenerate)")

            # Check for invalid vertex indices
            for idx in triangle.vertex_indices:
                if idx < 0 or idx >= len(self.vertices):
                    issues.append(f"Triangle {i} has invalid vertex index {idx}")

        # Check for isolated vertices
        used_vertices = set()
        for triangle in self.triangles:
            used_vertices.update(triangle.vertex_indices)

        isolated_vertices = set(range(len(self.vertices))) - used_vertices
        if isolated_vertices:
            issues.append(f"Found {len(isolated_vertices)} isolated vertices")

        # Check for NaN or infinite coordinates
        for i, vertex in enumerate(self.vertices):
            if np.any(np.isnan(vertex)):
                issues.append(f"Vertex {i} contains NaN values")
            if np.any(np.isinf(vertex)):
                issues.append(f"Vertex {i} contains infinite values")

        is_valid = len(issues) == 0
        return is_valid, issues

    def simplify_mesh(self, target_reduction: float = 0.5) -> 'TerrainMesh':
        """
        Simplify the mesh by reducing the number of vertices.

        Args:
            target_reduction: Fraction of vertices to remove (0.0 to 0.9)

        Returns:
            Simplified TerrainMesh
        """
        # This is a placeholder implementation
        # In a real implementation, you would use algorithms like
        # edge collapse, quadric error metrics, etc.

        if target_reduction <= 0 or target_reduction >= 1.0:
            raise ValueError("target_reduction must be between 0.0 and 1.0")

        # For now, return a copy of the original mesh
        # Real implementation would simplify the mesh
        return TerrainMesh(
            vertices=self.vertices.copy(),
            triangles=[Triangle(t.vertex_indices.copy()) for t in self.triangles],
            vertex_colors=self.vertex_colors.copy() if self.vertex_colors is not None else None,
            vertex_normals=self.vertex_normals.copy() if self.vertex_normals is not None else None,
            texture_coordinates=self.texture_coordinates.copy() if self.texture_coordinates is not None else None
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert mesh to dictionary format for serialization.

        Returns:
            Dictionary representation of the mesh
        """
        return {
            'vertices': self.vertices.tolist(),
            'triangles': [triangle.vertex_indices for triangle in self.triangles],
            'vertex_colors': self.vertex_colors.tolist() if self.vertex_colors is not None else None,
            'vertex_normals': self.vertex_normals.tolist() if self.vertex_normals is not None else None,
            'texture_coordinates': self.texture_coordinates.tolist() if self.texture_coordinates is not None else None,
            'vertex_count': self.vertex_count,
            'triangle_count': self.triangle_count,
            'bounds': list(self.bounds)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TerrainMesh':
        """
        Create mesh from dictionary format.

        Args:
            data: Dictionary representation of the mesh

        Returns:
            TerrainMesh object
        """
        vertices = np.array(data['vertices'])
        triangles = [Triangle(vertex_indices) for vertex_indices in data['triangles']]

        return cls(
            vertices=vertices,
            triangles=triangles,
            vertex_colors=np.array(data['vertex_colors']) if data.get('vertex_colors') is not None else None,
            vertex_normals=np.array(data['vertex_normals']) if data.get('vertex_normals') is not None else None,
            texture_coordinates=np.array(data['texture_coordinates']) if data.get('texture_coordinates') is not None else None
        )