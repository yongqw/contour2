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

    def get_normal(self, vertices: np.ndarray) -> np.ndarray:
        """
        Calculate the normal vector of the triangle.

        Args:
            vertices: Array of vertices (n, 3)

        Returns:
            Normalized normal vector
        """
        if self.normal is not None:
            return self.normal

        # Get triangle vertices
        v0 = vertices[self.vertex_indices[0]]
        v1 = vertices[self.vertex_indices[1]]
        v2 = vertices[self.vertex_indices[2]]

        # Calculate edge vectors
        edge1 = v1 - v0
        edge2 = v2 - v0

        # Calculate normal using cross product
        normal = np.cross(edge1, edge2)

        # Normalize
        norm = np.linalg.norm(normal)
        if norm > 1e-10:
            normal = normal / norm
        else:
            # Degenerate triangle, use a default normal
            normal = np.array([0, 0, 1])

        return normal

    def get_area(self, vertices: np.ndarray) -> float:
        """
        Calculate the area of the triangle.

        Args:
            vertices: Array of vertices (n, 3)

        Returns:
            Triangle area
        """
        # Get triangle vertices
        v0 = vertices[self.vertex_indices[0]]
        v1 = vertices[self.vertex_indices[1]]
        v2 = vertices[self.vertex_indices[2]]

        # Calculate edge vectors
        edge1 = v1 - v0
        edge2 = v2 - v0

        # Area is half the magnitude of the cross product
        cross = np.cross(edge1, edge2)
        area = 0.5 * np.linalg.norm(cross)

        return area

    def get_center(self, vertices: np.ndarray) -> np.ndarray:
        """
        Get the center point of the triangle.

        Args:
            vertices: Array of vertices (n, 3)

        Returns:
            Center point (3,)
        """
        v0 = vertices[self.vertex_indices[0]]
        v1 = vertices[self.vertex_indices[1]]
        v2 = vertices[self.vertex_indices[2]]

        return (v0 + v1 + v2) / 3.0


@dataclass
class TerrainMesh:
    """
    3D terrain mesh representation.

    This class represents a triangulated terrain surface with vertices,
    triangle faces, and optional vertex attributes like colors and normals.
    """
    vertices: np.ndarray  # 3D vertices (n, 3)
    triangles: List[Triangle]  # Triangle faces
    vertex_colors: Optional[np.ndarray] = None  # Vertex colors (n, 3) or (n, 4)
    vertex_normals: Optional[np.ndarray] = None  # Vertex normals (n, 3)
    texture_coordinates: Optional[np.ndarray] = None  # UV coordinates (n, 2)

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

    @property
    def vertex_count(self) -> int:
        """Get the number of vertices in the mesh."""
        if self._vertex_count is None:
            self._vertex_count = len(self.vertices)
        return self._vertex_count

    @property
    def triangle_count(self) -> int:
        """Get the number of triangles in the mesh."""
        if self._triangle_count is None:
            self._triangle_count = len(self.triangles)
        return self._triangle_count

    def get_bounds(self) -> Tuple[float, float, float, float, float, float]:
        """
        Get the bounding box of the mesh.

        Returns:
            Tuple of (min_x, max_x, min_y, max_y, min_z, max_z)
        """
        if self._bounds is None:
            if len(self.vertices) == 0:
                self._bounds = (0, 0, 0, 0, 0, 0)
            else:
                min_coords = np.min(self.vertices, axis=0)
                max_coords = np.max(self.vertices, axis=0)
                self._bounds = (
                    min_coords[0], max_coords[0],
                    min_coords[1], max_coords[1],
                    min_coords[2], max_coords[2]
                )
        return self._bounds

    def calculate_vertex_normals(self) -> np.ndarray:
        """
        Calculate vertex normals by averaging adjacent triangle normals.

        Returns:
            Array of vertex normals (n, 3)
        """
        # Initialize normals array
        normals = np.zeros((len(self.vertices), 3))
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

        return normals

    def ensure_vertex_normals(self) -> None:
        """Ensure vertex normals are calculated and stored."""
        if self.vertex_normals is None:
            self.vertex_normals = self.calculate_vertex_normals()

    def is_point_inside_triangle(self, point: np.ndarray, triangle_idx: int) -> bool:
        """
        Check if a point is inside a triangle using barycentric coordinates.

        Args:
            point: Point to test (2D or 3D)
            triangle_idx: Index of the triangle to test against

        Returns:
            True if point is inside the triangle
        """
        triangle = self.triangles[triangle_idx]
        v0 = self.vertices[triangle.vertex_indices[0]]
        v1 = self.vertices[triangle.vertex_indices[1]]
        v2 = self.vertices[triangle.vertex_indices[2]]

        # For 2D points, use only x,y coordinates
        if len(point) == 2:
            v0 = v0[:2]
            v1 = v1[:2]
            v2 = v2[:2]
            point = point[:2]

        # Compute vectors
        v0v1 = v1 - v0
        v0v2 = v2 - v0
        v0p = point - v0

        # Compute dot products
        dot00 = np.dot(v0v2, v0v2)
        dot01 = np.dot(v0v2, v0v1)
        dot02 = np.dot(v0v2, v0p)
        dot11 = np.dot(v0v1, v0v1)
        dot12 = np.dot(v0v1, v0p)

        # Compute barycentric coordinates
        denom = (dot00 * dot11 - dot01 * dot01)
        inv_denom = 1.0 / denom if denom != 0 else 1.0

        u = (dot11 * dot02 - dot01 * dot12) * inv_denom
        v = (dot00 * dot12 - dot01 * dot02) * inv_denom

        # Check if point is in triangle
        return (u >= 0) and (v >= 0) and (u + v <= 1)

    def get_elevation_at(self, x: float, y: float) -> Optional[float]:
        """
        Get the elevation (z-coordinate) at a specific x,y position.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Elevation at the position, or None if outside mesh
        """
        point = np.array([x, y])

        # Find triangle containing the point
        for i, triangle in enumerate(self.triangles):
            if self.is_point_inside_triangle(point, i):
                # Get triangle vertices
                v0 = self.vertices[triangle.vertex_indices[0]]
                v1 = self.vertices[triangle.vertex_indices[1]]
                v2 = self.vertices[triangle.vertex_indices[2]]

                # Calculate barycentric coordinates
                v0v1 = v1[:2] - v0[:2]
                v0v2 = v2[:2] - v0[:2]
                v0p = point - v0[:2]

                dot00 = np.dot(v0v2, v0v2)
                dot01 = np.dot(v0v2, v0v1)
                dot02 = np.dot(v0v2, v0p)
                dot11 = np.dot(v0v1, v0v1)
                dot12 = np.dot(v0v1, v0p)

                denom = (dot00 * dot11 - dot01 * dot01)
                inv_denom = 1.0 / denom if denom != 0 else 1.0

                u = (dot11 * dot02 - dot01 * dot12) * inv_denom
                v = (dot00 * dot12 - dot01 * dot02) * inv_denom
                w = 1.0 - u - v

                # Interpolate elevation
                elevation = w * v0[2] + u * v1[2] + v * v2[2]
                return elevation

        # Point is outside the mesh
        return None

    def validate_mesh(self) -> Tuple[bool, List[str]]:
        """
        Validate the mesh for common issues.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check for empty mesh
        if len(self.vertices) == 0:
            issues.append("Mesh has no vertices")
            return False, issues

        if len(self.triangles) == 0:
            issues.append("Mesh has no triangles")
            return False, issues

        # Check triangle indices
        vertex_count = len(self.vertices)
        for i, triangle in enumerate(self.triangles):
            for idx in triangle.vertex_indices:
                if idx < 0 or idx >= vertex_count:
                    issues.append(f"Triangle {i} has invalid vertex index {idx}")

        # Check for degenerate triangles
        for i, triangle in enumerate(self.triangles):
            area = triangle.get_area(self.vertices)
            if area < 1e-10:
                issues.append(f"Triangle {i} is degenerate (area ≈ 0)")

        # Check for NaN or infinite vertices
        for i, vertex in enumerate(self.vertices):
            if np.any(np.isnan(vertex)):
                issues.append(f"Vertex {i} contains NaN values")
            if np.any(np.isinf(vertex)):
                issues.append(f"Vertex {i} contains infinite values")

        return len(issues) == 0, issues

    def copy(self) -> 'TerrainMesh':
        """
        Create a deep copy of the mesh.

        Returns:
            Copy of the mesh
        """
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
        data = {
            'vertices': self.vertices.tolist(),
            'triangles': [t.vertex_indices for t in self.triangles]
        }

        if self.vertex_colors is not None:
            data['vertex_colors'] = self.vertex_colors.tolist()

        if self.vertex_normals is not None:
            data['vertex_normals'] = self.vertex_normals.tolist()

        if self.texture_coordinates is not None:
            data['texture_coordinates'] = self.texture_coordinates.tolist()

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TerrainMesh':
        """
        Create a mesh from a dictionary representation.

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