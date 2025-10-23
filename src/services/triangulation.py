"""
Triangulation service for Terrain Tunneling Calculator.

This service handles Delaunay triangulation of contour data to generate
3D terrain meshes, including point reduction and quality filtering.
"""

import numpy as np
from scipy.spatial import Delaunay
from typing import List, Tuple, Dict, Any, Optional
import time
import warnings

from models.contour_data import ContourData, ContourLine
from models.terrain_mesh import TerrainMesh, Triangle
from utils.math_utils import BoundingBox
from utils.exceptions import TriangulationError, ValidationError


class TriangulationService:
    """Service for triangulating contour data into 3D terrain meshes."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the triangulation service.

        Args:
            config: Optional configuration dictionary
        """
        # Default configuration
        self.config = {
            'point_reduction_tolerance': 0.1,
            'min_triangle_angle': 10.0,  # degrees
            'max_triangle_aspect_ratio': 5.0,
            'max_points_per_contour': 1000,
            'enable_point_reduction': True,
            'enable_quality_filtering': True,
            'triangulation_timeout': 10.0  # seconds
        }

        # Update with provided config
        if config:
            self.config.update(config)

        # Set config properties for easy access
        self.point_reduction_tolerance = self.config['point_reduction_tolerance']
        self.min_triangle_angle = self.config['min_triangle_angle']
        self.max_triangle_aspect_ratio = self.config['max_triangle_aspect_ratio']
        self.max_points_per_contour = self.config['max_points_per_contour']
        self.enable_point_reduction = self.config['enable_point_reduction']
        self.enable_quality_filtering = self.config['enable_quality_filtering']
        self.triangulation_timeout = self.config['triangulation_timeout']

    def triangulate_contours(self, contour_data: ContourData) -> TerrainMesh:
        """
        Triangulate contour data into a 3D terrain mesh.

        Args:
            contour_data: ContourData object to triangulate

        Returns:
            TerrainMesh object with triangulated surface

        Raises:
            TriangulationError: If triangulation fails
        """
        start_time = time.time()

        try:
            # Validate input
            if not contour_data.contours:
                raise TriangulationError("No contours to triangulate")

            # Extract points from all contours
            all_points = self._extract_points_from_contours(contour_data.contours)

            if len(all_points) < 3:
                raise TriangulationError("Insufficient points for triangulation (need at least 3)")

            # Apply point reduction if enabled
            if self.enable_point_reduction:
                all_points = self._apply_point_reduction(all_points)

            # Add interior points for better triangulation
            all_points = self._add_interior_points(all_points, contour_data)

            # Perform Delaunay triangulation
            triangulation = self._perform_delaunay_triangulation(all_points)

            # Filter triangles by quality if enabled
            if self.enable_quality_filtering:
                triangulation = self._filter_triangles_by_quality(
                    triangulation, all_points
                )

            # Create terrain mesh
            mesh = self._create_terrain_mesh(triangulation, all_points, contour_data)

            # Validate mesh
            is_valid, issues = self.validate_mesh(mesh)
            if not is_valid:
                raise TriangulationError(f"Generated mesh validation failed: {issues}")

            # Check timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > self.triangulation_timeout:
                warnings.warn(f"Triangulation took {elapsed_time:.2f}s (exceeds timeout of {self.triangulation_timeout}s)")

            return mesh

        except Exception as e:
            if isinstance(e, TriangulationError):
                raise
            raise TriangulationError(f"Triangulation failed: {e}")

    def _extract_points_from_contours(self, contours: List[ContourLine]) -> np.ndarray:
        """
        Extract and combine points from all contour lines.

        Args:
            contours: List of contour lines

        Returns:
            Array of points (n, 2) for [x, y] coordinates
        """
        all_points = []

        for contour in contours:
            # Remove duplicate closing point if present
            points = contour.points
            if np.allclose(points[0], points[-1]):
                points = points[:-1]

            # Limit points per contour
            if len(points) > self.max_points_per_contour:
                # Uniformly sample points
                indices = np.linspace(0, len(points) - 1, self.max_points_per_contour, dtype=int)
                points = points[indices]

            all_points.append(points)

        # Combine all points
        combined_points = np.vstack(all_points)

        return combined_points

    def _apply_point_reduction(self, points: np.ndarray) -> np.ndarray:
        """
        Apply point reduction algorithm to reduce computational complexity.

        Args:
            points: Array of points (n, 2)

        Returns:
            Reduced array of points
        """
        if len(points) <= 100:
            return points

        # Use Douglas-Peucker algorithm for point reduction
        reduced_points = []

        # Process each contour separately (we'll implement a simplified version)
        # For now, use a simple distance-based reduction
        reduced_points.append(points[0])

        tolerance = self.point_reduction_tolerance
        last_point = points[0]

        for i in range(1, len(points)):
            current_point = points[i]

            # Calculate distance from the line through last_point
            if i > 1:
                prev_point = points[i - 1]
                distance = self._point_to_line_distance(current_point, last_point, prev_point)

                if distance > tolerance:
                    reduced_points.append(current_point)
                    last_point = current_point

        # Always include the last point
        if not np.allclose(reduced_points[-1], points[-1]):
            reduced_points.append(points[-1])

        return np.array(reduced_points)

    def _point_to_line_distance(self, point: np.ndarray, line_start: np.ndarray, line_end: np.ndarray) -> float:
        """
        Calculate distance from a point to a line segment.

        Args:
            point: Point to check
            line_start: Start of line segment
            line_end: End of line segment

        Returns:
            Distance from point to line segment
        """
        line_vec = line_end - line_start
        point_vec = point - line_start
        line_len = np.linalg.norm(line_vec)

        if line_len == 0:
            return np.linalg.norm(point_vec)

        line_unitvec = line_vec / line_len
        proj_length = np.dot(point_vec, line_unitvec)

        if proj_length < 0:
            return np.linalg.norm(point_vec)
        elif proj_length > line_len:
            return np.linalg.norm(point - line_end)
        else:
            proj_point = line_start + proj_length * line_unitvec
            return np.linalg.norm(point - proj_point)

    def _add_interior_points(self, points: np.ndarray, contour_data: ContourData) -> np.ndarray:
        """
        Add interior points to improve triangulation quality.

        Args:
            points: Existing boundary points
            contour_data: Contour data for reference

        Returns:
            Points array with additional interior points
        """
        # Get bounds
        bounds = contour_data.get_bounds()
        min_x, max_x = bounds.min_x, bounds.max_x
        min_y, max_y = bounds.min_y, bounds.max_y

        # Create a grid of interior points
        grid_resolution = 10  # Adjust based on area size
        x_coords = np.linspace(min_x + 1, max_x - 1, grid_resolution)
        y_coords = np.linspace(min_y + 1, max_y - 1, grid_resolution)

        interior_points = []
        for x in x_coords:
            for y in y_coords:
                # Check if point is inside any contour
                inside_contour = False
                for contour in contour_data.contours:
                    if contour.contains_point(x, y):
                        # Get elevation at this point
                        elevation = contour_data.get_elevation_at(x, y)
                        interior_points.append([x, y])
                        inside_contour = True
                        break

        if interior_points:
            interior_array = np.array(interior_points)
            return np.vstack([points, interior_array])
        else:
            return points

    def _perform_delaunay_triangulation(self, points: np.ndarray) -> Delaunay:
        """
        Perform Delaunay triangulation using scipy.

        Args:
            points: Array of points (n, 2)

        Returns:
            scipy.spatial.Delaunay object

        Raises:
            TriangulationError: If triangulation fails
        """
        try:
            # Ensure points are 2D
            if points.shape[1] != 2:
                raise ValueError("Points must be 2D for triangulation")

            # Perform triangulation
            triangulation = Delaunay(points)

            return triangulation

        except Exception as e:
            raise TriangulationError(f"Delaunay triangulation failed: {e}")

    def _filter_triangles_by_quality(self, triangulation: Delaunay, points: np.ndarray) -> Delaunay:
        """
        Filter triangles based on quality metrics.

        Args:
            triangulation: Original Delaunay triangulation
            points: Points array

        Returns:
            Filtered triangulation (as a new object with selected simplices)
        """
        # Get triangle vertices
        triangles = triangulation.simplices

        # Calculate quality metrics for each triangle
        good_triangles = []

        for triangle_indices in triangles:
            triangle_points = points[triangle_indices]

            # Calculate quality metrics
            min_angle, aspect_ratio = self._calculate_triangle_quality(triangle_points)

            # Check if triangle meets quality criteria
            if (min_angle >= self.min_triangle_angle and
                aspect_ratio <= self.max_triangle_aspect_ratio):
                good_triangles.append(triangle_indices)

        # Create new triangulation with only good triangles
        if not good_triangles:
            # If no triangles pass quality filter, return original
            warnings.warn("No triangles passed quality filter, using original triangulation")
            return triangulation

        # Create a filtered version
        filtered_triangles = np.array(good_triangles)

        # Create a new triangulation-like object
        class FilteredTriangulation:
            def __init__(self, points, simplices):
                self.points = points
                self.simplices = simplices

        return FilteredTriangulation(points, filtered_triangles)

    def _calculate_triangle_quality(self, triangle_points: np.ndarray) -> Tuple[float, float]:
        """
        Calculate quality metrics for a triangle.

        Args:
            triangle_points: Triangle vertices (3, 2)

        Returns:
            Tuple of (min_angle_degrees, aspect_ratio)
        """
        if len(triangle_points) != 3:
            return 0.0, float('inf')

        # Calculate side lengths
        edges = []
        for i in range(3):
            j = (i + 1) % 3
            edge_length = np.linalg.norm(triangle_points[j] - triangle_points[i])
            edges.append(edge_length)

        # Sort edges
        edges.sort()

        # Calculate angles using law of cosines
        angles = []
        for i in range(3):
            j = (i + 1) % 3
            k = (i + 2) % 3

            # Angle at vertex i
            a = edges[j]  # Opposite edge
            b = edges[k]  # Adjacent edge
            c = edges[i]  # Adjacent edge

            if b + c > 0:
                cos_angle = (b**2 + c**2 - a**2) / (2 * b * c)
                cos_angle = np.clip(cos_angle, -1.0, 1.0)  # Numerical stability
                angle = np.arccos(cos_angle)
                angles.append(angle)

        min_angle = min(angles) if angles else 0.0
        min_angle_degrees = np.degrees(min_angle)

        # Calculate aspect ratio (longest edge / shortest edge)
        if edges[0] > 1e-10:
            aspect_ratio = edges[2] / edges[0]
        else:
            aspect_ratio = float('inf')

        return min_angle_degrees, aspect_ratio

    def _create_terrain_mesh(self, triangulation, points: np.ndarray, contour_data: ContourData = None) -> TerrainMesh:
        """
        Create a TerrainMesh from triangulation results.

        Args:
            triangulation: Triangulation result (Delaunay or filtered)
            points: Points array (n, 2)
            contour_data: Original contour data for elevation interpolation

        Returns:
            TerrainMesh object
        """
        # Convert 2D points to 3D by adding elevation
        vertices_3d = np.zeros((len(points), 3))
        vertices_3d[:, :2] = points

        # Use proper elevation interpolation if contour data is available
        if contour_data and contour_data.contours:
            vertices_3d[:, 2] = self._interpolate_elevations(points, contour_data)
        else:
            # Fallback to simple elevation model (only for testing without contour data)
            for i, point in enumerate(points):
                x, y = point
                # Simple elevation model based on distance from origin
                elevation = 100.0 + 10.0 * np.sin(x * 0.1) * np.cos(y * 0.1)
                vertices_3d[i, 2] = elevation

        # Create triangle objects
        triangles = []
        for triangle_indices in triangulation.simplices:
            triangle = Triangle(vertex_indices=triangle_indices.tolist())
            triangles.append(triangle)

        # Create terrain mesh
        mesh = TerrainMesh(vertices=vertices_3d, triangles=triangles)

        return mesh

    def _interpolate_elevations(self, points: np.ndarray, contour_data: ContourData) -> np.ndarray:
        """
        Interpolate elevations for points using contour data.

        Args:
            points: Array of points (n, 2) for [x, y] coordinates
            contour_data: Contour data with elevation information

        Returns:
            Array of elevations (n,)
        """
        elevations = np.zeros(len(points))

        for i, point in enumerate(points):
            x, y = point

            # Find the two nearest contours in elevation
            min_distances = []
            contour_elevations = []

            for contour in contour_data.contours:
                # Find minimum distance to this contour
                distances = np.sqrt(np.sum((contour.points - point) ** 2, axis=1))
                min_dist = np.min(distances)
                min_distances.append(min_dist)
                contour_elevations.append(contour.elevation)

            # If point is very close to a contour, use that elevation directly
            min_dist_idx = np.argmin(min_distances)
            if min_distances[min_dist_idx] < 1.0:  # Within 1 unit of contour
                elevations[i] = contour_elevations[min_dist_idx]
            else:
                # Use inverse distance weighting interpolation
                weights = 1.0 / (np.array(min_distances) + 0.1)  # Add small value to avoid division by zero
                elevations[i] = np.sum(weights * np.array(contour_elevations)) / np.sum(weights)

        return elevations

    def validate_mesh(self, mesh: TerrainMesh) -> Tuple[bool, List[str]]:
        """
        Validate the generated mesh.

        Args:
            mesh: TerrainMesh to validate

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        return mesh.validate_mesh()

    def _reduce_points(self, points: np.ndarray, tolerance: float) -> np.ndarray:
        """
        Reduce points using Douglas-Peucker algorithm.

        Args:
            points: Array of points (n, 2)
            tolerance: Distance tolerance for reduction

        Returns:
            Reduced array of points
        """
        if len(points) <= 2:
            return points

        # Find the point with maximum distance from the line
        max_distance = 0
        max_index = 0

        for i in range(1, len(points) - 1):
            distance = self._point_to_line_distance(
                points[i], points[0], points[-1]
            )
            if distance > max_distance:
                max_distance = distance
                max_index = i

        # If max distance is greater than tolerance, recursively simplify
        if max_distance > tolerance:
            # Recursive call
            left_points = self._reduce_points(points[:max_index + 1], tolerance)
            right_points = self._reduce_points(points[max_index:], tolerance)

            # Combine results (avoid duplicate point)
            return np.vstack([left_points[:-1], right_points])
        else:
            # Return only the endpoints
            return np.array([points[0], points[-1]])

    def get_triangulation_statistics(self, contour_data: ContourData) -> Dict[str, Any]:
        """
        Get statistics about the triangulation process.

        Args:
            contour_data: Input contour data

        Returns:
            Dictionary with triangulation statistics
        """
        stats = {
            'input_contours': len(contour_data.contours),
            'input_points': sum(len(contour.points) for contour in contour_data.contours),
            'estimated_triangles': 0,
            'estimated_memory_mb': 0,
            'processing_time_estimate': 0.0
        }

        # Estimate number of points after reduction
        total_points = stats['input_points']
        if self.enable_point_reduction:
            reduced_points = int(total_points * 0.7)  # Rough estimate
        else:
            reduced_points = total_points

        # Estimate triangles (approximately 2x points for Delaunay triangulation)
        stats['estimated_triangles'] = reduced_points * 2

        # Estimate memory usage (rough calculation)
        # Vertices: 3 floats * 4 bytes * point_count
        # Triangles: 3 ints * 4 bytes * triangle_count
        vertex_memory = reduced_points * 3 * 4
        triangle_memory = stats['estimated_triangles'] * 3 * 4
        total_memory_bytes = vertex_memory + triangle_memory
        stats['estimated_memory_mb'] = total_memory_bytes / (1024 * 1024)

        # Estimate processing time (very rough guess)
        stats['processing_time_estimate'] = reduced_points * 0.001  # 1ms per point

        return stats