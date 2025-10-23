"""
Tunnel geometry models for Terrain Tunneling Calculator.

This module provides models for tunnel path planning, geometry calculation,
and cross-sectional analysis.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import numpy as np
import math


class CrossSectionType(Enum):
    """Types of tunnel cross-sections."""
    CIRCULAR = "circular"
    RECTANGULAR = "rectangular"
    HORSESHOE = "horseshoe"


@dataclass
class TunnelWaypoint:
    """A waypoint along a tunnel path."""
    x: float
    y: float
    elevation: float
    radius: float = 25.0  # Default tunnel radius - very large for maximum visibility

    def to_dict(self) -> Dict[str, Any]:
        """Convert waypoint to dictionary."""
        return {
            'x': self.x,
            'y': self.y,
            'elevation': self.elevation,
            'radius': self.radius
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TunnelWaypoint':
        """Create waypoint from dictionary."""
        return cls(
            x=data['x'],
            y=data['y'],
            elevation=data['elevation'],
            radius=data.get('radius', 3.0)
        )


@dataclass
class TunnelPath:
    """Represents a tunnel path with waypoints and interpolated geometry."""

    waypoints: List[TunnelWaypoint] = field(default_factory=list)
    cross_section_type: CrossSectionType = CrossSectionType.CIRCULAR
    name: str = "Tunnel Path"

    def __post_init__(self):
        """Initialize derived attributes."""
        self._cached_path_points: Optional[np.ndarray] = None
        self._cached_elevations: Optional[np.ndarray] = None
        self._cache_dirty = True

    def add_waypoint(self, x: float, y: float, elevation: float, radius: float = 15.0) -> None:
        """Add a waypoint to the path."""
        waypoint = TunnelWaypoint(x, y, elevation, radius)
        self.waypoints.append(waypoint)
        self._cache_dirty = True

    def remove_waypoint(self, index: int) -> None:
        """Remove a waypoint by index."""
        if 0 <= index < len(self.waypoints):
            self.waypoints.pop(index)
            self._cache_dirty = True

    def clear_waypoints(self) -> None:
        """Clear all waypoints."""
        self.waypoints.clear()
        self._cache_dirty = True

    def get_waypoint_count(self) -> int:
        """Get the number of waypoints."""
        return len(self.waypoints)

    def get_waypoint(self, index: int) -> Optional[TunnelWaypoint]:
        """Get a waypoint by index. Supports negative indices like Python lists."""
        if len(self.waypoints) == 0:
            return None

        # Handle negative indices like Python lists
        if index < 0:
            index = len(self.waypoints) + index

        if 0 <= index < len(self.waypoints):
            return self.waypoints[index]
        return None

    def update_waypoint(self, index: int, x: float, y: float, elevation: float, radius: float = 15.0) -> None:
        """Update an existing waypoint."""
        if 0 <= index < len(self.waypoints):
            self.waypoints[index] = TunnelWaypoint(x, y, elevation, radius)
            self._cache_dirty = True

    def get_length(self) -> float:
        """Calculate total length of the tunnel path."""
        if len(self.waypoints) < 2:
            return 0.0

        total_length = 0.0
        for i in range(len(self.waypoints) - 1):
            wp1 = self.waypoints[i]
            wp2 = self.waypoints[i + 1]
            dx = wp2.x - wp1.x
            dy = wp2.y - wp1.y
            dz = wp2.elevation - wp1.elevation
            segment_length = math.sqrt(dx**2 + dy**2 + dz**2)
            total_length += segment_length

        return total_length

    def get_interpolated_path(self, num_points: int = 100) -> np.ndarray:
        """Get interpolated 3D path points."""
        if len(self.waypoints) < 2:
            return np.array([])

        # Check cache
        if not self._cache_dirty and self._cached_path_points is not None:
            if len(self._cached_path_points) == num_points:
                return self._cached_path_points

        # Extract waypoint coordinates
        waypoints_array = np.array([(wp.x, wp.y, wp.elevation) for wp in self.waypoints])

        # Calculate cumulative distances along path
        distances = [0.0]
        for i in range(1, len(waypoints_array)):
            dx = waypoints_array[i, 0] - waypoints_array[i-1, 0]
            dy = waypoints_array[i, 1] - waypoints_array[i-1, 1]
            dz = waypoints_array[i, 2] - waypoints_array[i-1, 2]
            segment_length = math.sqrt(dx**2 + dy**2 + dz**2)
            distances.append(distances[-1] + segment_length)

        distances = np.array(distances)
        total_length = distances[-1]

        if total_length == 0:
            return waypoints_array

        # Create interpolation parameter
        if num_points == 1:
            t_new = np.array([0.0])
        else:
            t_new = np.linspace(0, total_length, num_points)

        # Interpolate each dimension
        x_interp = np.interp(t_new, distances, waypoints_array[:, 0])
        y_interp = np.interp(t_new, distances, waypoints_array[:, 1])
        z_interp = np.interp(t_new, distances, waypoints_array[:, 2])

        # Combine into point array
        path_points = np.column_stack([x_interp, y_interp, z_interp])

        # Cache the result
        self._cached_path_points = path_points
        self._cache_dirty = False

        return path_points

    def get_elevation_profile(self, num_points: int = 100) -> Tuple[np.ndarray, np.ndarray]:
        """Get elevation profile along the path."""
        if len(self.waypoints) < 2:
            return np.array([]), np.array([])

        path_points = self.get_interpolated_path(num_points)
        if len(path_points) == 0:
            return np.array([]), np.array([])

        # Calculate cumulative distances
        distances = [0.0]
        for i in range(1, len(path_points)):
            dx = path_points[i, 0] - path_points[i-1, 0]
            dy = path_points[i, 1] - path_points[i-1, 1]
            dz = path_points[i, 2] - path_points[i-1, 2]
            segment_length = math.sqrt(dx**2 + dy**2 + dz**2)
            distances.append(distances[-1] + segment_length)

        return np.array(distances), path_points[:, 2]  # distances, elevations

    def get_gradient_profile(self, num_points: int = 100) -> np.ndarray:
        """Get gradient (slope) profile along the path."""
        if len(self.waypoints) < 2:
            return np.array([])

        _, elevations = self.get_elevation_profile(num_points)
        if len(elevations) < 2:
            return np.array([])

        # Calculate gradients
        gradients = []
        for i in range(1, len(elevations)):
            dh = elevations[i] - elevations[i-1]
            # Use a small horizontal distance for gradient calculation
            dh_horizontal = 1.0  # This is simplified; in reality should use 3D distance
            gradient = (dh / dh_horizontal) * 100  # Convert to percentage
            gradients.append(gradient)

        # Pad with first value to match length
        gradients = [gradients[0]] + gradients if gradients else []

        return np.array(gradients)

    def validate(self) -> bool:
        """Validate the tunnel path."""
        if len(self.waypoints) < 2:
            return False

        # Check waypoint coordinates
        for wp in self.waypoints:
            if not (-1_000_000 <= wp.x <= 1_000_000 and
                   -1_000_000 <= wp.y <= 1_000_000 and
                   -1000 <= wp.elevation <= 10000):
                return False
            if not (1.0 <= wp.radius <= 10.0):
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert tunnel path to dictionary."""
        return {
            'waypoints': [wp.to_dict() for wp in self.waypoints],
            'cross_section_type': self.cross_section_type.value,
            'name': self.name
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TunnelPath':
        """Create tunnel path from dictionary."""
        waypoints = [TunnelWaypoint.from_dict(wp_data) for wp_data in data['waypoints']]
        cross_section = CrossSectionType(data.get('cross_section_type', 'circular'))
        name = data.get('name', 'Tunnel Path')

        return cls(
            waypoints=waypoints,
            cross_section_type=cross_section,
            name=name
        )


@dataclass
class VolumeCalculation:
    """Volume calculation results for a tunnel."""
    total_volume: float = 0.0
    excavation_volume: float = 0.0
    lining_volume: float = 0.0
    overbreak_volume: float = 0.0
    accuracy_estimate: float = 0.0


@dataclass
class TunnelGeometry:
    """Complete tunnel geometry including path and cross-section."""

    path: TunnelPath
    volume: float = 0.0
    surface_area: float = 0.0
    material_properties: Dict[str, Any] = field(default_factory=dict)
    volume_calculation: Optional[VolumeCalculation] = None

    @property
    def cross_section_type(self) -> CrossSectionType:
        """Get the cross-section type from the path."""
        return self.path.cross_section_type

    @property
    def radius(self) -> float:
        """Get the average radius of the tunnel."""
        if len(self.path.waypoints) == 0:
            return 25.0  # Default radius - very large for maximum visibility
        return sum(wp.radius for wp in self.path.waypoints) / len(self.path.waypoints)

    def __post_init__(self):
        """Calculate derived properties."""
        self.calculate_volume()
        self.calculate_surface_area()

    def calculate_volume(self) -> float:
        """Calculate tunnel volume based on path and cross-section."""
        if len(self.path.waypoints) < 2:
            self.volume = 0.0
            return self.volume

        # Simplified volume calculation
        total_volume = 0.0
        for i in range(len(self.path.waypoints) - 1):
            wp1 = self.path.waypoints[i]
            wp2 = self.path.waypoints[i + 1]

            # Calculate segment length
            dx = wp2.x - wp1.x
            dy = wp2.y - wp1.y
            dz = wp2.elevation - wp1.elevation
            segment_length = math.sqrt(dx**2 + dy**2 + dz**2)

            # Average radius for this segment
            avg_radius = (wp1.radius + wp2.radius) / 2

            # Calculate segment volume based on cross-section type
            if self.path.cross_section_type == CrossSectionType.CIRCULAR:
                segment_volume = math.pi * avg_radius**2 * segment_length
            elif self.path.cross_section_type == CrossSectionType.RECTANGULAR:
                # Assume square cross-section with side = 2 * radius
                segment_volume = (2 * avg_radius)**2 * segment_length
            else:  # HORSESHOE
                # Approximate as 0.8 * circular volume
                segment_volume = 0.8 * math.pi * avg_radius**2 * segment_length

            total_volume += segment_volume

        self.volume = total_volume
        return self.volume

    def calculate_surface_area(self) -> float:
        """Calculate tunnel surface area."""
        if len(self.path.waypoints) < 2:
            self.surface_area = 0.0
            return self.surface_area

        total_area = 0.0
        for i in range(len(self.path.waypoints) - 1):
            wp1 = self.path.waypoints[i]
            wp2 = self.path.waypoints[i + 1]

            # Calculate segment length
            dx = wp2.x - wp1.x
            dy = wp2.y - wp1.y
            dz = wp2.elevation - wp1.elevation
            segment_length = math.sqrt(dx**2 + dy**2 + dz**2)

            # Average radius for this segment
            avg_radius = (wp1.radius + wp2.radius) / 2

            # Calculate segment surface area
            if self.path.cross_section_type == CrossSectionType.CIRCULAR:
                segment_area = 2 * math.pi * avg_radius * segment_length
            elif self.path.cross_section_type == CrossSectionType.RECTANGULAR:
                # Perimeter of square with side = 2 * radius
                perimeter = 8 * avg_radius
                segment_area = perimeter * segment_length
            else:  # HORSESHOE
                # Approximate perimeter
                perimeter = 2 * math.pi * avg_radius * 0.8
                segment_area = perimeter * segment_length

            total_area += segment_area

        self.surface_area = total_area
        return self.surface_area

    def get_cross_section_area(self, radius: float) -> float:
        """Get cross-sectional area for given radius."""
        if self.path.cross_section_type == CrossSectionType.CIRCULAR:
            return math.pi * radius**2
        elif self.path.cross_section_type == CrossSectionType.RECTANGULAR:
            return (2 * radius)**2
        else:  # HORSESHOE
            return 0.8 * math.pi * radius**2

    def get_bounding_box(self) -> Dict[str, float]:
        """Calculate bounding box of the tunnel."""
        if len(self.path.waypoints) == 0:
            return {
                'min_x': 0.0, 'max_x': 0.0,
                'min_y': 0.0, 'max_y': 0.0,
                'min_elevation': 0.0, 'max_elevation': 0.0
            }

        x_coords = [wp.x for wp in self.path.waypoints]
        y_coords = [wp.y for wp in self.path.waypoints]
        elevations = [wp.elevation for wp in self.path.waypoints]

        return {
            'min_x': min(x_coords),
            'max_x': max(x_coords),
            'min_y': min(y_coords),
            'max_y': max(y_coords),
            'min_elevation': min(elevations),
            'max_elevation': max(elevations)
        }

    def get_centerline(self) -> List[Tuple[float, float]]:
        """Extract tunnel centerline coordinates (x, y pairs)."""
        return [(wp.x, wp.y) for wp in self.path.waypoints]

    def to_dict(self) -> Dict[str, Any]:
        """Convert tunnel geometry to dictionary."""
        return {
            'path': self.path.to_dict(),
            'volume': self.volume,
            'surface_area': self.surface_area,
            'material_properties': self.material_properties
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TunnelGeometry':
        """Create tunnel geometry from dictionary."""
        path = TunnelPath.from_dict(data['path'])
        volume = data.get('volume', 0.0)
        surface_area = data.get('surface_area', 0.0)
        material_properties = data.get('material_properties', {})

        return cls(
            path=path,
            volume=volume,
            surface_area=surface_area,
            material_properties=material_properties
        )

    def get_mesh_vertices(self, segments_per_section: int = 16, points_per_segment: int = 4) -> Optional[np.ndarray]:
        """
        Generate 3D mesh vertices for the tunnel.

        Args:
            segments_per_section: Number of segments around circular cross-section
            points_per_segment: Number of points along each tunnel segment

        Returns:
            Array of vertices (n, 3) or None if insufficient waypoints
        """
        if len(self.path.waypoints) < 2:
            return None

        vertices = []

        for i in range(len(self.path.waypoints) - 1):
            wp1 = self.path.waypoints[i]
            wp2 = self.path.waypoints[i + 1]

            # Interpolate between waypoints
            for j in range(points_per_segment):
                t = j / (points_per_segment - 1)

                # Linear interpolation of position
                x = wp1.x + t * (wp2.x - wp1.x)
                y = wp1.y + t * (wp2.y - wp1.y)
                z = wp1.elevation + t * (wp2.elevation - wp1.elevation)
                radius = wp1.radius + t * (wp2.radius - wp1.radius)

                # Create circular cross-section
                for k in range(segments_per_section):
                    angle = 2 * np.pi * k / segments_per_section
                    vx = x + radius * np.cos(angle)
                    vy = y + radius * np.sin(angle)
                    vz = z
                    vertices.append([vx, vy, vz])

        return np.array(vertices)

    def get_mesh_triangles(self, segments_per_section: int = 16, points_per_segment: int = 4) -> Optional[List[List[int]]]:
        """
        Generate triangle indices for tunnel mesh.

        Args:
            segments_per_section: Number of segments around circular cross-section
            points_per_segment: Number of points along each tunnel segment

        Returns:
            List of triangle vertex index lists or None if insufficient waypoints
        """
        if len(self.path.waypoints) < 2:
            return None

        triangles = []
        segments_per_section_int = segments_per_section
        points_per_segment_int = points_per_segment

        for segment_idx in range(len(self.path.waypoints) - 1):
            # Current and next segment offsets
            start_idx = segment_idx * segments_per_section_int * points_per_segment_int
            next_start_idx = (segment_idx + 1) * segments_per_section_int * points_per_segment_int

            # Generate triangles for cylindrical surface between segments
            for ring_idx in range(points_per_segment_int - 1):
                # Current ring
                ring_start = start_idx + ring_idx * segments_per_section_int
                next_ring_start = ring_start + segments_per_section_int

                # Next ring (for interpolation)
                next_ring_next_start = next_start_idx + ring_idx * segments_per_section_int
                next_ring_next_next_start = next_ring_next_start + segments_per_section_int

                for i in range(segments_per_section_int):
                    next_i = (i + 1) % segments_per_section_int

                    # First triangle
                    triangles.append([
                        ring_start + i,
                        ring_start + next_i,
                        next_ring_start + i
                    ])

                    # Second triangle
                    triangles.append([
                        ring_start + next_i,
                        next_ring_start + next_i,
                        next_ring_start + i
                    ])

                    # Triangles for interpolation to next segment
                    if ring_idx < points_per_segment_int - 2:
                        # Third triangle (interpolation)
                        triangles.append([
                            next_ring_start + i,
                            next_ring_start + next_i,
                            next_ring_next_start + i
                        ])

                        # Fourth triangle (interpolation)
                        triangles.append([
                            next_ring_start + next_i,
                            next_ring_next_start + next_i,
                            next_ring_next_start + i
                        ])

        return triangles