"""
Tunnel geometry models for Terrain Tunneling Calculator.

This module provides models for tunnel path planning, geometry calculation,
and cross-sectional analysis.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple

import numpy as np


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
    """A tunnel path defined by waypoints and geometry parameters."""
    waypoints: List[TunnelWaypoint]
    cross_section_type: CrossSectionType = CrossSectionType.CIRCULAR
    tunnel_length: float = 0.0  # Calculated from waypoints
    material_properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate tunnel length after initialization."""
        if len(self.waypoints) < 2:
            self.tunnel_length = 0.0
            return

        # Calculate total path length
        total_length = 0.0
        for i in range(len(self.waypoints) - 1):
            wp1 = self.waypoints[i]
            wp2 = self.waypoints[i + 1]
            segment_length = np.sqrt(
                (wp2.x - wp1.x)**2 + (wp2.y - wp1.y)**2 + (wp2.elevation - wp1.elevation)**2
            )
            total_length += segment_length

        self.tunnel_length = total_length

    def validate_path(self) -> bool:
        """Validate the tunnel path for geometric consistency."""
        if len(self.waypoints) < 2:
            return False

        # Check for invalid coordinates or radii
        for wp in self.waypoints:
            if not (-1_000_000 <= wp.x <= 1_000_000 and
                   -1_000_000 <= wp.y <= 1_000_000 and
                   -1000 <= wp.elevation <= 10000):
                return False
            if not (1.0 <= wp.radius <= 10.0):
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert path to dictionary for serialization."""
        return {
            'waypoints': [wp.to_dict() for wp in self.waypoints],
            'cross_section_type': self.cross_section_type.value,
            'tunnel_length': self.tunnel_length,
            'material_properties': self.material_properties
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TunnelPath':
        """Create path from dictionary."""
        waypoints = [TunnelWaypoint.from_dict(wp_data) for wp_data in data['waypoints']]
        cross_section_type = CrossSectionType(data.get('cross_section_type', 'circular'))
        material_properties = data.get('material_properties', {})

        return cls(
            waypoints=waypoints,
            cross_section_type=cross_section_type,
            material_properties=material_properties
        )

    def get_position_at_distance(self, distance: float) -> Optional[Tuple[float, float, float, float]]:
        """
        Get position and radius at a specific distance along the tunnel.

        Args:
            distance: Distance from start of tunnel

        Returns:
            Tuple of (x, y, elevation, radius) or None if distance is outside tunnel
        """
        if distance <= 0:
            wp = self.waypoints[0]
            return wp.x, wp.y, wp.elevation, wp.radius

        if distance >= self.tunnel_length:
            wp = self.waypoints[-1]
            return wp.x, wp.y, wp.elevation, wp.radius

        # Find segment containing the distance
        accumulated_distance = 0.0
        for i in range(len(self.waypoints) - 1):
            wp1 = self.waypoints[i]
            wp2 = self.waypoints[i + 1]

            segment_length = np.sqrt(
                (wp2.x - wp1.x)**2 + (wp2.y - wp1.y)**2 + (wp2.elevation - wp1.elevation)**2
            )

            if accumulated_distance + segment_length >= distance:
                # Interpolate position within this segment
                t = (distance - accumulated_distance) / segment_length

                x = wp1.x + t * (wp2.x - wp1.x)
                y = wp1.y + t * (wp2.y - wp1.y)
                elevation = wp1.elevation + t * (wp2.elevation - wp1.elevation)
                radius = wp1.radius + t * (wp2.radius - wp1.radius)

                return x, y, elevation, radius

            accumulated_distance += segment_length

        return None


@dataclass
class TunnelGeometry:
    """Complete tunnel geometry including path, cross-sections, and calculations."""
    path: TunnelPath
    volume: Optional[float] = None
    surface_area: Optional[float] = None
    material_properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize default material properties if not provided."""
        if not self.material_properties:
            self.material_properties = {
                'density': 2500.0,  # kg/m³ (typical rock density)
                'strength': 50.0,   # MPa
                'permeability': 1e-9  # m/s
            }

    def calculate_basic_metrics(self) -> Dict[str, Any]:
        """
        Calculate basic tunnel metrics.

        Returns:
            Dictionary of calculated metrics
        """
        metrics = {
            'tunnel_length': self.path.tunnel_length,
            'waypoint_count': len(self.path.waypoints),
            'cross_section_type': self.path.cross_section_type.value
        }

        # Calculate average radius
        if self.path.waypoints:
            avg_radius = sum(wp.radius for wp in self.path.waypoints) / len(self.path.waypoints)
            metrics['average_radius'] = avg_radius
            metrics['average_cross_section_area'] = self.get_cross_section_area(avg_radius)

        return metrics

    def get_cross_section_area(self, radius: float) -> float:
        """Get cross-sectional area for given radius."""
        if self.path.cross_section_type == CrossSectionType.CIRCULAR:
            return math.pi * radius**2
        
        if self.path.cross_section_type == CrossSectionType.RECTANGULAR:
            return (2 * radius)**2
        
        # HORSESHOE
        return 0.8 * math.pi * radius**2

    def calculate_volume(self) -> float:
        """
        Calculate tunnel volume using cylindrical approximation.

        Returns:
            Calculated volume in cubic meters
        """
        if len(self.path.waypoints) < 2:
            return 0.0

        total_volume = 0.0
        for i in range(len(self.path.waypoints) - 1):
            wp1 = self.path.waypoints[i]
            wp2 = self.path.waypoints[i + 1]

            # Segment length
            segment_length = np.sqrt(
                (wp2.x - wp1.x)**2 + (wp2.y - wp1.y)**2 + (wp2.elevation - wp1.elevation)**2
            )

            # Average radius for this segment
            avg_radius = (wp1.radius + wp2.radius) / 2.0

            # Volume of frustum
            volume = math.pi * avg_radius**2 * segment_length
            total_volume += volume

        self.volume = total_volume
        return total_volume

    def calculate_surface_area(self) -> float:
        """
        Calculate tunnel surface area (excluding ends).

        Returns:
            Calculated surface area in square meters
        """
        if len(self.path.waypoints) < 2:
            return 0.0

        total_area = 0.0
        for i in range(len(self.path.waypoints) - 1):
            wp1 = self.path.waypoints[i]
            wp2 = self.path.waypoints[i + 1]

            # Segment length
            segment_length = np.sqrt(
                (wp2.x - wp1.x)**2 + (wp2.y - wp1.y)**2 + (wp2.elevation - wp1.elevation)**2
            )

            # Average radius for this segment
            avg_radius = (wp1.radius + wp2.radius) / 2.0

            # Surface area of frustum
            if self.path.cross_section_type == CrossSectionType.CIRCULAR:
                area = 2 * math.pi * avg_radius * segment_length
            elif self.path.cross_section_type == CrossSectionType.RECTANGULAR:
                perimeter = 8 * avg_radius
                area = perimeter * segment_length
            else:  # HORSESHOE
                perimeter = 5.5 * avg_radius  # Approximation
                area = perimeter * segment_length

            total_area += area

        self.surface_area = total_area
        return total_area

    def to_dict(self) -> Dict[str, Any]:
        """Convert geometry to dictionary for serialization."""
        data = {
            'path': self.path.to_dict(),
            'volume': self.volume,
            'surface_area': self.surface_area,
            'material_properties': self.material_properties
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TunnelGeometry':
        """Create geometry from dictionary."""
        path = TunnelPath.from_dict(data['path'])
        volume = data.get('volume')
        surface_area = data.get('surface_area')
        material_properties = data.get('material_properties', {})

        return cls(
            path=path,
            volume=volume,
            surface_area=surface_area,
            material_properties=material_properties
        )

    def get_mesh_vertices(
        self, 
        segments_per_section: int = 16, 
        points_per_segment: int = 4
    ) -> Optional[np.ndarray]:
        """
        Generate 3D mesh vertices for the tunnel.

        Args:
            segments_per_section: Number of segments around circular cross-section
            points_per_segment: Number of points along each path segment

        Returns:
            Array of vertices or None if insufficient waypoints
        """
        if len(self.path.waypoints) < 2:
            return None

        vertices = []
        segments_per_section_int = max(3, segments_per_section)  # At least triangle
        points_per_segment_int = max(2, points_per_segment)

        for i in range(len(self.path.waypoints) - 1):
            wp1 = self.path.waypoints[i]
            wp2 = self.path.waypoints[i + 1]

            # Create points along the segment
            for j in range(points_per_segment_int):
                t = j / (points_per_segment_int - 1) if points_per_segment_int > 1 else 0

                # Interpolate position and radius
                x = wp1.x + t * (wp2.x - wp1.x)
                y = wp1.y + t * (wp2.y - wp1.y)
                z = wp1.elevation + t * (wp2.elevation - wp1.elevation)
                radius = wp1.radius + t * (wp2.radius - wp1.radius)

                # Generate circle of points around this position
                for k in range(segments_per_section_int):
                    angle = 2 * np.pi * k / segments_per_section_int
                    vx = x + radius * np.cos(angle)
                    vy = y + radius * np.sin(angle)
                    vz = z
                    vertices.append([vx, vy, vz])

        return np.array(vertices)

    def get_mesh_triangles(self, segments_per_section: int = 16, points_per_segment: int = 4) -> Optional[List[List[int]]]:
        """
        Generate triangle indices for the tunnel mesh.

        Args:
            segments_per_section: Number of segments around circular cross-section
            points_per_segment: Number of points along each path segment

        Returns:
            List of triangles (each triangle is a list of 3 vertex indices)
        """
        if len(self.path.waypoints) < 2:
            return None

        segments_per_section_int = max(3, segments_per_section)
        points_per_segment_int = max(2, points_per_segment)
        triangles = []

        # Generate triangles for each segment
        for segment_idx in range(len(self.path.waypoints) - 1):
            start_idx = segment_idx * segments_per_section_int * points_per_segment_int
            next_start_idx = (segment_idx + 1) * segments_per_section_int * points_per_segment_int

            # Generate triangles for cylindrical surface between segments
            for ring_idx in range(points_per_segment_int - 1):
                # Current ring
                ring_start = start_idx + ring_idx * segments_per_section_int
                next_ring_start = ring_start + segments_per_section_int

                # Next ring (for interpolation)
                # next_ring_next_start = next_start_idx + ring_idx * segments_per_section_int

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

        return triangles

    def get_complete_mesh(self, segments_per_section: int = 16, points_per_segment: int = 4) -> Optional[Dict[str, Any]]:
        """
        Generate complete mesh with vertices and triangles.

        Args:
            segments_per_section: Number of segments around circular cross-section
            points_per_segment: Number of points along each path segment

        Returns:
            Dictionary with 'vertices' and 'triangles' keys or None
        """
        vertices = self.get_mesh_vertices(segments_per_section, points_per_segment)
        triangles = self.get_mesh_triangles(segments_per_section, points_per_segment)

        if vertices is None or triangles is None:
            return None

        return {
            'vertices': vertices,
            'triangles': triangles
        }

    def get_tunnel_centerline(self, num_points: int = 100) -> Optional[np.ndarray]:
        """
        Get points along the tunnel centerline.

        Args:
            num_points: Number of points to generate along the centerline

        Returns:
            Array of centerline points or None if insufficient waypoints
        """
        if len(self.path.waypoints) < 2:
            return None

        if num_points < 2:
            num_points = 2

        points = []
        total_length = self.path.tunnel_length

        for i in range(num_points):
            distance = i * total_length / (num_points - 1)
            pos = self.path.get_position_at_distance(distance)
            if pos:
                points.append([pos[0], pos[1], pos[2]])  # x, y, elevation

        return np.array(points)

    def calculate_intersections_with_terrain(self, terrain_mesh) -> List[Dict[str, Any]]:
        """
        Calculate intersection points between tunnel and terrain mesh.

        Args:
            terrain_mesh: TerrainMesh object to check intersections with

        Returns:
            List of intersection information
        """
        intersections = []

        # Get tunnel centerline points
        centerline = self.get_tunnel_centerline(num_points=200)
        if centerline is None:
            return intersections

        # For each point on the centerline, check if it's below the terrain
        for i, point in enumerate(centerline):
            x, y, z = point
            terrain_elevation = terrain_mesh.get_elevation_at(x, y)

            if terrain_elevation is not None and z < terrain_elevation:
                # Calculate depth below terrain
                depth = terrain_elevation - z
                radius = self.path.get_position_at_distance(
                    i * self.path.tunnel_length / 199
                )[3]  # Get radius at this position

                intersections.append({
                    'position': point,
                    'terrain_elevation': terrain_elevation,
                    'tunnel_elevation': z,
                    'depth': depth,
                    'radius': radius,
                    'distance_from_start': i * self.path.tunnel_length / 199
                })

        return intersections